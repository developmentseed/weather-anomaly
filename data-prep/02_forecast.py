import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import icechunk
    import icechunk.xarray
    import xarray as xr
    import pandas as pd
    import os

    return icechunk, os, pd, xr


@app.cell
def _(icechunk, xr):
    storage = icechunk.s3_storage(                                
        bucket="dynamical-ecmwf-ifs-ens",                         
        prefix="ecmwf-ifs-ens-forecast-15-day-0-25-degree/v0.1.0.icechunk/",                                                    
        region="us-west-2",                                       
        anonymous=True                                            
    )                                                                
    repo = icechunk.Repository.open(storage)
    session = repo.readonly_session("main")                    
    ds_forecast = xr.open_zarr(session.store, chunks={})
    ds_forecast
    return (ds_forecast,)


@app.cell
def _(ds_forecast):
    """Check variable names and dimensions before proceeding."""
    print("Variables:", list(ds_forecast.data_vars))
    print("Dims:", dict(ds_forecast.dims))
    print("Most recent init_time:", str(ds_forecast.init_time.values[-1])[:16])
    return


@app.cell
def _():
    # Variable names in the ECMWF IFS forecast dataset.
    # Temperature is already in °C (unlike ERA5 which is Kelvin).
    # Confirm names match the check cell above before running.
    VARS = {
        "temp":   "temperature_2m",          # °C
    }
    return (VARS,)


@app.cell
def _(VARS, ds_forecast, pd):
    """Select the most recent init time, ensemble member 0, next 7 days."""
    _today     = pd.Timestamp.now().strftime("%Y-%m-%d")
    _end       = (pd.Timestamp.now() + pd.Timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"Selecting forecast: {_today} → {_end}")

    ds_fc_raw = (
        ds_forecast[list(VARS.values())]
        .sel(init_time=_today, method="nearest", ensemble_member=0)
        .swap_dims({"lead_time": "valid_time"})
        .sel(valid_time=slice(_today, _end))
    )

    print("Selected lead times:", len(ds_fc_raw.valid_time))
    return (ds_fc_raw,)


@app.cell
def _(VARS, ds_fc_raw, xr):
    """Resample 3-hourly forecast steps to daily aggregates."""
    print("Resampling to daily...")

    ds_fc_daily = xr.Dataset({
        # Temperature (°C) — mean/min/max of 3-hourly readings each day
        "temp_mean":    ds_fc_raw[VARS["temp"]].resample(valid_time="1D").mean(),
        "temp_min":     ds_fc_raw[VARS["temp"]].resample(valid_time="1D").min(),
        "temp_max":     ds_fc_raw[VARS["temp"]].resample(valid_time="1D").max(),
    }).rename({
        "valid_time": "valid_date"
    }).drop_vars(
          ["ensemble_member", "expected_forecast_length","ingested_forecast_length", "init_time", "spatial_ref"],
          errors="ignore",                                         
      )

    # Attach units
    ds_fc_daily["temp_mean"].attrs  = {"units": "°C"}
    ds_fc_daily["temp_min"].attrs   = {"units": "°C"}
    ds_fc_daily["temp_max"].attrs   = {"units": "°C"}

    print("Daily forecast ready:", list(ds_fc_daily.data_vars))
    return (ds_fc_daily,)


@app.cell
def _(ds_fc_daily, os):
    """Write today's forecast window (today → today+7) to forecast.zarr."""
    _forecast_path = "../data/forecast.zarr"
    os.makedirs("data", exist_ok=True)

    print("Writing forecast.zarr...")
    ds_fc_daily.to_zarr(_forecast_path, mode="w", safe_chunks=False)
    print("Done!")

    forecast_zarr_path = _forecast_path
    return (forecast_zarr_path,)


@app.cell
def _(forecast_zarr_path, xr):
    """Verify the written zarr."""
    _ds = xr.open_zarr(forecast_zarr_path)
    print("Variables:", list(_ds.data_vars))
    print("Dates:", [str(d)[:10] for d in _ds.valid_date.values])
    print("Dims:", dict(_ds.dims))
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
