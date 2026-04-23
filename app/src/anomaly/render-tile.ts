import type { RenderTileResult } from "@developmentseed/deck.gl-raster";
import {
  Colormap,
  LinearRescale,
} from "@developmentseed/deck.gl-raster/gpu-modules";
import type { Texture } from "@luma.gl/core";
import { SampleTexture2DArray } from "../gpu/sample-texture-2d-array.js";
import type { AnomalyTileData } from "./get-tile-data.js";

export type MakeRenderTileArgs = {
  /** Current date index (0 .. dates.length-1). */
  dateIdx: number;
  colormapTexture: Texture;
  rescaleMin: number;
  rescaleMax: number;
};

export function makeRenderTile(args: MakeRenderTileArgs) {
  const { dateIdx, colormapTexture, rescaleMin, rescaleMax } = args;
  return function renderTile(data: AnomalyTileData): RenderTileResult {
    // Clamp to actual texture depth — guards against S3 zarr depth mismatches.
    const selectedDate = Math.min(dateIdx, Math.max(0, data.depth - 1));
    return {
      renderPipeline: [
        {
          module: SampleTexture2DArray,
          props: { dataTex: data.texture, layerIndex: selectedDate },
        },
        {
          module: LinearRescale,
          props: { rescaleMin, rescaleMax },
        },
        {
          module: Colormap,
          props: { colormapTexture, colormapIndex: 0 },
        },
      ],
    };
  };
}
