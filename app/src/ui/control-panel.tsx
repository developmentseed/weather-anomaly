import * as Slider from "@radix-ui/react-slider";
import {
  COLORMAPS,
  type ColormapOption,
} from "../gpu/colormap.js";
import {
  DATE_COUNT,
  VARIABLES,
  type VariableKey,
} from "../anomaly/metadata.js";

type QueryInfo = { lat: number; lon: number; anom: number; std: number };

export type ControlPanelProps = {
  dateIdx: number;
  dates: string[];
  variable: VariableKey;
  colormap: ColormapOption;
  query: QueryInfo | null;
  isPlaying: boolean;
  filterMin: number;
  filterMax: number;
  rescaleMin: number;
  rescaleMax: number;
  onDateIdxChange: (idx: number) => void;
  onVariableChange: (v: VariableKey) => void;
  onColormapChange: (c: ColormapOption) => void;
  onFilterChange: (min: number, max: number) => void;
  onPlayPauseToggle: () => void;
};

export function ControlPanel(props: ControlPanelProps) {
  const {
    dateIdx,
    dates,
    variable,
    colormap,
    query,
    isPlaying,
    filterMin,
    filterMax,
    rescaleMin,
    rescaleMax,
    onDateIdxChange,
    onVariableChange,
    onColormapChange,
    onFilterChange,
    onPlayPauseToggle,
  } = props;
  const currentDate = dates[dateIdx] ?? "—";

  // Step size for the filter slider — 0.1 for anomaly (°C), 0.05 for std (σ)
  const isStd = variable.endsWith("_std");
  const step = isStd ? 0.05 : 0.1;

  return (
    <div
      style={{
        position: "absolute",
        top: "20px",
        left: "20px",
        background: "white",
        padding: "16px",
        borderRadius: "8px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        width: "300px",
        pointerEvents: "auto",
      }}
    >
      <div
        style={{ fontSize: "16px", fontWeight: "bold", marginBottom: "4px" }}
      >
        Temperature Anomaly
      </div>
      <div style={{ fontSize: "12px", color: "#666", marginBottom: "12px" }}>
        vs 1990–2020 climatology · {currentDate}
      </div>
      <select
        value={variable}
        onChange={(e) => onVariableChange(e.target.value as VariableKey)}
        style={{ width: "100%", marginBottom: "8px", padding: "4px", cursor: "pointer" }}
      >
        {VARIABLES.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>
      <select
        value={colormap.label}
        onChange={(e) => {
          const selected = COLORMAPS.find((c) => c.label === e.target.value);
          if (selected) onColormapChange(selected);
        }}
        style={{ width: "100%", marginBottom: "12px", padding: "4px", cursor: "pointer" }}
      >
        {COLORMAPS.map((c) => (
          <option key={c.label} value={c.label}>
            {c.label}
          </option>
        ))}
      </select>

      {/* Filter range slider — hides pixels outside the chosen value range */}
      <div style={{ marginBottom: "12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#666", marginBottom: "4px" }}>
          <span>Filter range</span>
          <span>
            {!isFinite(filterMin) && !isFinite(filterMax)
              ? "all"
              : `${isFinite(filterMin) ? filterMin.toFixed(isStd ? 2 : 1) : "−∞"} – ${isFinite(filterMax) ? filterMax.toFixed(isStd ? 2 : 1) : "+∞"} ${isStd ? "σ" : "°C"}`}
          </span>
        </div>
        <Slider.Root
          min={rescaleMin}
          max={rescaleMax}
          step={step}
          value={[
            Math.max(rescaleMin, filterMin),
            Math.min(rescaleMax, filterMax),
          ]}
          onValueChange={(values: number[]) => {
            // Snap to ±Infinity when the thumb is at the slider edge (full range = no filter).
            const min = values[0] <= rescaleMin ? Number.NEGATIVE_INFINITY : values[0];
            const max = values[1] >= rescaleMax ? Number.POSITIVE_INFINITY : values[1];
            onFilterChange(min, max);
          }}
          style={{ position: "relative", display: "flex", alignItems: "center", height: "20px", cursor: "pointer" }}
        >
          <Slider.Track
            style={{
              position: "relative",
              flexGrow: 1,
              height: "4px",
              background: "#ddd",
              borderRadius: "2px",
            }}
          >
            <Slider.Range
              style={{
                position: "absolute",
                height: "100%",
                background: "#555",
                borderRadius: "2px",
              }}
            />
          </Slider.Track>
          <Slider.Thumb
            style={{
              display: "block",
              width: "14px",
              height: "14px",
              background: "white",
              border: "2px solid #555",
              borderRadius: "50%",
              outline: "none",
            }}
          />
          <Slider.Thumb
            style={{
              display: "block",
              width: "14px",
              height: "14px",
              background: "white",
              border: "2px solid #555",
              borderRadius: "50%",
              outline: "none",
            }}
          />
        </Slider.Root>
      </div>

      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <button
          type="button"
          onClick={onPlayPauseToggle}
          style={{ padding: "4px 10px", cursor: "pointer" }}
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
        <input
          type="range"
          min={0}
          max={DATE_COUNT - 1}
          value={dateIdx}
          onChange={(e) => onDateIdxChange(Number(e.target.value))}
          style={{ flex: 1, cursor: "pointer" }}
        />
      </div>
      {query !== null && (
        <div
          style={{
            marginTop: "12px",
            paddingTop: "12px",
            borderTop: "1px solid #eee",
            fontSize: "12px",
          }}
        >
          <div style={{ color: "#666", marginBottom: "6px" }}>
            {query.lat.toFixed(2)}°, {query.lon.toFixed(2)}°
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ color: "#666" }}>Anomaly</span>
            <span style={{ fontWeight: "bold" }}>{query.anom.toFixed(2)} °C</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#666" }}>Std dev</span>
            <span style={{ fontWeight: "bold" }}>{query.std.toFixed(2)} σ</span>
          </div>
        </div>
      )}
    </div>
  );
}
