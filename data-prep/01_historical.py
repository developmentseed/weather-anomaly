import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    import zarr
    from zarr.storage import ObjectStore
    from obstore.store import GCSStore, from_url, HTTPStore
    import xarray as xr
    import os

    return GCSStore, ObjectStore, os, xr


@app.cell
def _(GCSStore):
    store = GCSStore(
        bucket="gcp-public-data-arco-era5/",
        prefix="ar",
        skip_signature=True,
    )
    return


@app.cell
def _(GCSStore, ObjectStore, xr):
    ds_historical_full = xr.open_zarr(
        ObjectStore(
            GCSStore.from_url("gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3",
            skip_signature=True)),
        decode_timedelta=True,
        chunks={}
        )
    return (ds_historical_full,)


@app.cell
def _(ds_historical_full):
    ds_historical_full
    return


@app.cell
def _():
    VARS = {
          "temp":   "2m_temperature",          # Kelvin                                                     
    }
    return (VARS,)


@app.cell
def _(VARS, ds_historical_full):
    ds_raw = ds_historical_full[list(VARS.values())].sel(time=slice("1990-01-01", "2020-12-31"))
    return (ds_raw,)


@app.cell
def _(ds_raw):
    daily_mean = ds_raw.resample(time="1D").mean()
    daily_min  = ds_raw.resample(time="1D").min()  
    daily_max  = ds_raw.resample(time="1D").max()
    return daily_max, daily_mean, daily_min


@app.cell
def _():
    def by_calendar_day(da):
          """
          Tag each daily value with its calendar day (e.g. '01-15' for Jan 15),
          then group all years together so we can compute stats across years.
          """
          return (
              da.assign_coords(
                  month_day=("time", da.time.dt.strftime("%m-%d").data)
              )
              .groupby("month_day")
          )

      # For each variable and each calendar day (MM-DD), compute:
      #   - mean:  average value across all years  (the "normal")
      #   - min:   lowest single-day value seen   
      #   - max:   highest single-day value seen   
      #   - var:   variance across years           
      #
      # Temperature unit conversion: ERA5 stores in Kelvin → subtract 273.15 for °C

    print("Computing climatological stats...")
    return (by_calendar_day,)


@app.cell
def _(VARS, by_calendar_day, daily_max, daily_mean, daily_min, xr):
    hist = xr.Dataset({
        # Temperature (°C)
        "temp_mean": by_calendar_day(daily_mean[VARS["temp"]]).mean("time") - 273.15,
        "temp_min":  by_calendar_day(daily_min [VARS["temp"]]).mean("time") - 273.15,
        "temp_max":  by_calendar_day(daily_max [VARS["temp"]]).mean("time") - 273.15,
        "temp_var":  by_calendar_day(daily_mean[VARS["temp"]]).var("time"),
        "temp_min_var": by_calendar_day(daily_min[VARS["temp"]]).var("time"),
        "temp_max_var": by_calendar_day(daily_max[VARS["temp"]]).var("time"),
    })                                             
    return (hist,)


@app.cell
def _(hist):
    for var in ["temp_mean", "temp_min", "temp_max"]:
      hist[var].attrs = {"units": "°C", "long_name": f"2m Temperature ({var.split('_')[1]}) climatology"}

    hist["temp_var"].attrs = {"units": "K²", "long_name": "2m Temperature variance across years"}

    hist_shifted = hist.assign_coords(longitude=(hist.longitude % 360)).sortby("longitude")

    print("Variables computed:", list(hist.data_vars))
    return (hist_shifted,)


@app.cell
def _(hist_shifted, os):
    out_path = "../data/era5_historical.zarr"        
    os.makedirs("data", exist_ok=True)

    print(f"Writing to {out_path} ...")
    hist_shifted.to_zarr(out_path, mode="w",           
    zarr_format=2)  
    print("Done!")
    return


if __name__ == "__main__":
    app.run()
