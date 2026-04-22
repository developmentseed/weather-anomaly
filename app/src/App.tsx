import type { MapboxOverlayProps } from "@deck.gl/mapbox";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { GetTileDataOptions } from "@developmentseed/deck.gl-zarr";
import { ZarrLayer } from "@developmentseed/deck.gl-zarr";
import loadEpsg from "@developmentseed/epsg/all";
import epsgCsvUrl from "@developmentseed/epsg/all.csv.gz?url";
import { parseWkt } from "@developmentseed/proj";
import type { Readable } from "@zarrita/storage";
import type { Texture } from "@luma.gl/core";
import "maplibre-gl/dist/maplibre-gl.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { MapRef } from "react-map-gl/maplibre";
import { Map as MaplibreMap, useControl } from "react-map-gl/maplibre";
import * as zarr from "zarrita";
import type { AnomalyTileData } from "./anomaly/get-tile-data.js";
import { getTileData } from "./anomaly/get-tile-data.js";
import {
  ANOMALY_GEOZARR_ATTRS,
  VARIABLES,
  type VariableKey,
} from "./anomaly/metadata.js";
import { makeRenderTile } from "./anomaly/render-tile.js";
import { buildSelection } from "./anomaly/selection.js";
import {
  COLORMAPS,
  createColormapTexture,
  loadColormapSprite,
  type ColormapOption,
} from "./gpu/colormap.js";
import { ControlPanel } from "./ui/control-panel.js";

const ZARR_URL = import.meta.env.VITE_ZARR_URL as string;

const FRAME_DURATION_MS = 400;

async function epsgResolver(epsg: number) {
  const db = await loadEpsg(epsgCsvUrl);
  const wkt = db.get(epsg);
  if (!wkt) throw new Error(`EPSG:${epsg} not found`);
  return parseWkt(wkt);
}

type ClickedCell = { latIdx: number; lonIdx: number; lat: number; lon: number };

function DeckGLOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

export default function App() {
  const mapRef = useRef<MapRef>(null);
  const [dateIdx, setDateIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [variable, setVariable] = useState<VariableKey>(VARIABLES[0].value);
  const [arrays, setArrays] = useState<Record<
    VariableKey,
    zarr.Array<"float32", Readable>
  > | null>(null);
  const [dates, setDates] = useState<string[]>([]);
  const [colormap, setColormap] = useState<ColormapOption>(COLORMAPS[0]);
  const [filterMin, setFilterMin] = useState<number>(Number.NEGATIVE_INFINITY);
  const [filterMax, setFilterMax] = useState<number>(Number.POSITIVE_INFINITY);
  const [clickedCell, setClickedCell] = useState<ClickedCell | null>(null);
  const [queryValue, setQueryValue] = useState<{
    anom: number;
    std: number;
  } | null>(null);
  const spriteRef = useRef<ImageData | null>(null);
  const colormapRef = useRef<Texture | null>(null);

  // Decode the colormap sprite PNG at startup (async, no GPU needed yet).
  useEffect(() => {
    loadColormapSprite().then((imageData) => {
      spriteRef.current = imageData;
    });
  }, []);

  // Derive current array and rescale range from selected variable.
  const arr = arrays?.[variable] ?? null;
  const varConfig = VARIABLES.find((v) => v.value === variable)!;
  const rescaleMin = varConfig.defaultRescaleMin;
  const rescaleMax = varConfig.defaultRescaleMax;

  // Reset filter to open (no filtering) when variable changes.
  useEffect(() => {
    setFilterMin(Number.NEGATIVE_INFINITY);
    setFilterMax(Number.POSITIVE_INFINITY);
  }, [variable]);

  // Open all variable arrays at startup.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const store = await zarr.withConsolidatedMetadata(
        new zarr.FetchStore(ZARR_URL),
        { format: "v3" },
      );
      const root = await zarr.open.v3(store, { kind: "group" });

      const entries = await Promise.all(
        VARIABLES.map(async ({ value }) => [
          value,
          await zarr.open.v3(root.resolve(value), { kind: "array" }),
        ]),
      );

      // Read the valid_date coordinate array and decode dates from its
      // CF-convention "units" attribute (e.g. "days since 2026-04-20").
      const validDateArr = await zarr.open.v3(root.resolve("valid_date"), {
        kind: "array",
      });
      const validDateData = await zarr.get(validDateArr);
      const units = (validDateArr.attrs?.units as string) ?? "";
      const epochMatch = units.match(/days since (\d{4}-\d{2}-\d{2})/);
      const epoch = epochMatch
        ? new Date(`${epochMatch[1]}T00:00:00Z`)
        : new Date();

      const offsets = validDateData.data as BigInt64Array;
      const parsedDates = Array.from(offsets, (offset) => {
        const d = new Date(epoch);
        d.setUTCDate(d.getUTCDate() + Number(offset));
        return d.toISOString().slice(0, 10);
      });

      if (cancelled) return;
      setArrays(
        Object.fromEntries(entries) as Record<
          VariableKey,
          zarr.Array<"float32", Readable>
        >,
      );
      setDates(parsedDates);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Re-fetch both anom and std for the clicked cell whenever the date, variable, or location changes.
  useEffect(() => {
    if (!clickedCell || !arrays) return;
    let cancelled = false;
    // Derive the base name (e.g. "temp_mean") from whatever variable is selected,
    // then always fetch both the _anom and _std versions for the query panel.
    const base = variable.replace(/_anom$|_std$/, "") as
      | "temp_mean"
      | "temp_min"
      | "temp_max";
    const anomKey = `${base}_anom` as VariableKey;
    const stdKey = `${base}_std` as VariableKey;
    const idx = [dateIdx, clickedCell.latIdx, clickedCell.lonIdx] as const;
    (async () => {
      const [anomResult, stdResult] = await Promise.all([
        zarr.get(arrays[anomKey], idx),
        zarr.get(arrays[stdKey], idx),
      ]);
      if (cancelled) return;
      const anom = anomResult as unknown as number;
      const std = stdResult as unknown as number;
      if (!Number.isNaN(anom) && !Number.isNaN(std))
        setQueryValue({ anom, std });
    })();
    return () => {
      cancelled = true;
    };
  }, [arrays, variable, dateIdx, clickedCell]);

  // Convert a map click to zarr grid indices, derived from the geozarr
  // spatial transform [xScale, xSkew, xOrigin, ySkew, yScale, yOrigin]
  // and shape [latCount, lonCount].
  const handleMapClick = useCallback((lat: number, lon: number) => {
    const [xScale, , xOrigin, , yScale, yOrigin] =
      ANOMALY_GEOZARR_ATTRS["spatial:transform"];
    const [latCount, lonCount] = ANOMALY_GEOZARR_ATTRS["spatial:shape"];
    const latIdx = Math.min(
      latCount - 1,
      Math.max(0, Math.round((lat - yOrigin) / yScale)),
    );
    const lonIdx = Math.min(
      lonCount - 1,
      Math.max(0, Math.round((lon - xOrigin) / xScale)),
    );
    setClickedCell({ latIdx, lonIdx, lat, lon });
  }, []);

  // Animation loop.
  useEffect(() => {
    if (!isPlaying) return;
    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      if (now - last >= FRAME_DURATION_MS) {
        setDateIdx((i) => (i + 1) % (dates.length || 1));
        last = now;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [isPlaying, dates.length]);

  const selection = useMemo(() => buildSelection(), []);

  const getTileDataWithColormap = useCallback(
    async (
      openedArr: zarr.Array<zarr.DataType, Readable>,
      options: GetTileDataOptions,
    ) => {
      if (!colormapRef.current && spriteRef.current) {
        colormapRef.current = createColormapTexture(options.device, spriteRef.current);
      }
      return getTileData(openedArr, options);
    },
    [],
  );

  const renderTile = useCallback(
    (data: AnomalyTileData) => {
      const colormapTexture = colormapRef.current;
      if (!colormapTexture) return { renderPipeline: [] };
      return makeRenderTile({
        dateIdx,
        colormapTexture,
        colormap,
        filterMin,
        filterMax,
        rescaleMin,
        rescaleMax,
      })(data);
    },
    [dateIdx, colormap, filterMin, filterMax, rescaleMin, rescaleMax],
  );

  const layers = arr
    ? [
        new ZarrLayer<Readable, "float32", AnomalyTileData>({
          id: "temp-anomaly-layer",
          source: arr,
          metadata: ANOMALY_GEOZARR_ATTRS,
          selection,
          getTileData: getTileDataWithColormap,
          renderTile,
          updateTriggers: {
            renderTile: [dateIdx, colormap, filterMin, filterMax, rescaleMin, rescaleMax],
          },
          // @ts-expect-error beforeId is injected by @deck.gl/mapbox
          beforeId: "boundary_country_outline",
        }),
      ]
    : [];

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <MaplibreMap
        ref={mapRef}
        initialViewState={{ longitude: 0, latitude: 20, zoom: 2 }}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        onClick={(e) => handleMapClick(e.lngLat.lat, e.lngLat.lng)}
        onLoad={() => {}}
      >
        <DeckGLOverlay layers={layers} interleaved />
      </MaplibreMap>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
          zIndex: 1000,
        }}
      >
        <ControlPanel
          dateIdx={dateIdx}
          dates={dates}
          variable={variable}
          query={
            clickedCell && queryValue !== null
              ? {
                  lat: clickedCell.lat,
                  lon: clickedCell.lon,
                  anom: queryValue.anom,
                  std: queryValue.std,
                }
              : null
          }
          isPlaying={isPlaying}
          colormap={colormap}
          filterMin={filterMin}
          filterMax={filterMax}
          rescaleMin={rescaleMin}
          rescaleMax={rescaleMax}
          onDateIdxChange={setDateIdx}
          onVariableChange={setVariable}
          onColormapChange={setColormap}
          onFilterChange={(min: number, max: number) => { setFilterMin(min); setFilterMax(max); }}
          onPlayPauseToggle={() => setIsPlaying((p) => !p)}
        />
      </div>
    </div>
  );
}
