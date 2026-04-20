# weather-anomaly

Compares an 8-day temperature forecast against a 30-year historical climatology to identify anomalies and extremes.

## Notebooks

| Notebook           | Description                                                                                                                                                                                                       |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `01_historical.py` | Downloads ERA5 reanalysis data (1990–2020) and computes daily climatological stats (mean, min, max, variance) by calendar day → `data/era5_historical.zarr` **This is created once and takes a long time to run** |
| `02_forecast.py`   | Downloads the latest ECMWF IFS ensemble forecast from S3 (via Icechunk) and resamples 3-hourly steps to daily temperature aggregates → `data/forecast.zarr`. **This will run daily**                              |
| `03_compare.py`    | Joins forecast and historical data, computes absolute (°C) and standardized (σ) anomalies, and writes a map-ready zarr → `data/anomaly.zarr`. **This will run daily, and currently is committed in this repo**    |

These notebooks can be run with `uv run marimo edit` or run as python scripts with `uv run NOTEBOOK.py`

## Anomaly interpretation

Standardized anomalies (σ) express how unusual a forecast temperature is relative to local year-to-year variability:

- **±2σ** — notable (~5% of years)
- **±3σ** — extreme (~0.3% of years)
- **±4σ+** — exceptional

## Data sources

- **Historical**: [ARCO-ERA5](https://cloud.google.com/storage/docs/public-datasets/era5) — `gs://gcp-public-data-arco-era5`
- **Forecast**: [dynamical.org](https://dynamical.org) ECMWF IFS ensemble — `s3://dynamical-ecmwf-ifs-ens`
