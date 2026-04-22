import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import xarray as xr
    import numpy as np
    import pandas as pd

    import hvplot.xarray

    return np, pd, xr


@app.cell
def _(xr):
    forecast = xr.open_zarr("../data/forecast.zarr")
    historical = xr.open_zarr("../data/era5_historical.zarr")
    return forecast, historical


@app.cell
def _(historical):
    # Align historical longitude from 0-360 → -180-180 to match forecast
    hist = (
        historical
        .assign_coords(longitude=(historical.longitude - 180) % 360 - 180)
        .sortby("longitude")
    )
    return (hist,)


@app.cell
def _(forecast, pd):
    # For testing with a plot at the end
    today = pd.Timestamp.now(tz="UTC").floor("D")                 
    today_str = today.strftime("%Y-%m-%d")

    # Map each forecast valid_date (e.g. 2026-04-20) → "MM-DD" calendar string
    month_days = pd.DatetimeIndex(forecast.valid_date.values).strftime("%m-%d").tolist()
    return month_days, today_str


@app.cell
def _(forecast, hist, month_days):
    # Select matching historical slices and rename dim to align with forecast
    hist_sel = (
        hist[["temp_mean", "temp_min", "temp_max", "temp_var"]]
        .sel(month_day=month_days)
        .assign_coords(month_day=forecast.valid_date.values)
        .rename({"month_day": "valid_date"})
    )
    return (hist_sel,)


@app.cell
def _(forecast, hist_sel):
    # Absolute anomaly (°C): forecast minus 1990-2020 climatology
    temp_mean_anom = forecast["temp_mean"] - hist_sel["temp_mean"]
    temp_min_anom  = forecast["temp_min"]  - hist_sel["temp_min"]
    temp_max_anom  = forecast["temp_max"]  - hist_sel["temp_max"]
    return temp_max_anom, temp_mean_anom, temp_min_anom


@app.cell
def _(hist_sel, np):
    # Standardised anomaly (σ): how unusual relative to local variability.
    # temp_var is variance of daily mean — used as proxy std dev for min/max.
    hist_std = np.sqrt(hist_sel["temp_var"])
    return (hist_std,)


@app.cell
def _(hist_std, temp_max_anom, temp_mean_anom, temp_min_anom, xr):
    anomaly = xr.Dataset({
        "temp_mean_anom": temp_mean_anom,
        "temp_min_anom":  temp_min_anom,
        "temp_max_anom":  temp_max_anom,
        "temp_mean_std":  temp_mean_anom / hist_std,
        "temp_min_std":   temp_min_anom  / hist_std,
        "temp_max_std":   temp_max_anom  / hist_std,
    })
    return (anomaly,)


@app.cell
def _(anomaly):
    anomaly
    return


@app.cell
def _(anomaly):
    # Rechunk for deck.gl tile serving: all dates together per 64x64x spatial tile.
    # This lets JS pack all dates into a Texture2DArray — switching dates is a
    # uniform change only, no refetch needed.
    n_dates = len(anomaly.valid_date)
    (
        anomaly
        .chunk({"valid_date": n_dates, "latitude": 64, "longitude": 64})
        .to_zarr("../data/anomaly.zarr", mode="w", zarr_format=3)
    )
    print(f"Written: data/anomaly.zarr ({n_dates} dates, {len(anomaly.data_vars)} variables)")
    return


@app.cell
def _(anomaly, today_str):
    test = anomaly["temp_min_anom"].sel(valid_date=today_str)
    return (test,)


@app.cell
def _(test):
    test.hvplot(cmap="RdBu_r", height=550, width=1000)
    return


if __name__ == "__main__":
    app.run()
