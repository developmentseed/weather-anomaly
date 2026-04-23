/**
 * GeoZarr-compatible attrs for the anomaly zarr.
 * Same 0.25° global grid as ERA5/ECMWF: 721 lat × 1440 lon, -180→180.
 */
export const ANOMALY_GEOZARR_ATTRS = {
  "spatial:dimensions": ["latitude", "longitude"],
  "spatial:transform": [0.25, 0, -180, 0, -0.25, 90],
  "spatial:shape": [721, 1440],
  "proj:code": "EPSG:4326",
} as const;

export const VARIABLES = [
  { value: "temp_mean_anom", label: "Temp mean anomaly (°C)", unit: "°C", rescaleMin: -10, rescaleMax: 10 },
  { value: "temp_min_anom",  label: "Temp min anomaly (°C)",  unit: "°C", rescaleMin: -10, rescaleMax: 10 },
  { value: "temp_max_anom",  label: "Temp max anomaly (°C)",  unit: "°C", rescaleMin: -10, rescaleMax: 10 },
  { value: "temp_mean_std",  label: "Temp mean anomaly (σ)",  unit: "σ",  rescaleMin: -3,  rescaleMax: 3  },
  { value: "temp_min_std",   label: "Temp min anomaly (σ)",   unit: "σ",  rescaleMin: -3,  rescaleMax: 3  },
  { value: "temp_max_std",   label: "Temp max anomaly (σ)",   unit: "σ",  rescaleMin: -3,  rescaleMax: 3  },
] as const;

export type VariableKey = (typeof VARIABLES)[number]["value"];
