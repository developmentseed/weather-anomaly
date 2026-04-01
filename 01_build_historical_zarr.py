import marimo

__generated_with = "0.21.1"
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

    store.list_with_delimiter()
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
          "precip": "total_precipitation",     # meters per hour                                                  
          "cloud":  "total_cloud_cover",       # 0–1 fraction
    }
    return (VARS,)


@app.cell
def _(VARS, ds_historical_full):
    ds_raw = ds_historical_full[list(VARS.values())].sel(time=slice("2020-01-01", "2020-12-31"))
    return (ds_raw,)


@app.cell
def _(ds_raw):
    daily_mean = ds_raw.resample(time="1D").mean()
    daily_min  = ds_raw.resample(time="1D").min()  
    daily_max  = ds_raw.resample(time="1D").max()
    daily_sum  = ds_raw.resample(time="1D").sum()   # used only for precip
    return daily_max, daily_mean, daily_min, daily_sum


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
      #   - min:   lowest single-day value seen    (record cold/dry/clear)
      #   - max:   highest single-day value seen   (record hot/wet/cloudy)
      #   - var:   variance across years           (how consistent is this day?)
      #
      # Temperature unit conversion: ERA5 stores in Kelvin → subtract 273.15 for °C
      # Precipitation: ERA5 stores metres/hr → daily sum × 1000 = mm/day

    print("Computing climatological stats...")
    return (by_calendar_day,)


@app.cell
def _(VARS, by_calendar_day, daily_max, daily_mean, daily_min, daily_sum, xr):
    hist = xr.Dataset({
          # Temperature (°C)
          "temp_mean": by_calendar_day(daily_mean[VARS["temp"]]).mean("time") - 273.15,
          "temp_min":  by_calendar_day(daily_min [VARS["temp"]]).mean("time") - 273.15,
          "temp_max":  by_calendar_day(daily_max [VARS["temp"]]).mean("time") - 273.15,
          "temp_var":  by_calendar_day(daily_mean[VARS["temp"]]).var("time"),

          # Precipitation (mm/day)
          "precip_mean": by_calendar_day(daily_sum[VARS["precip"]]).mean("time") * 1000,
          "precip_min":  by_calendar_day(daily_sum[VARS["precip"]]).min("time") * 1000,
          "precip_max":  by_calendar_day(daily_sum[VARS["precip"]]).max("time") * 1000,
          "precip_var":  by_calendar_day(daily_sum[VARS["precip"]]).var("time"),

          # Cloud cover (fraction 0–1)
          "cloud_mean": by_calendar_day(daily_mean[VARS["cloud"]]).mean("time"),
          "cloud_min":  by_calendar_day(daily_mean[VARS["cloud"]]).min("time"),
          "cloud_max":  by_calendar_day(daily_mean[VARS["cloud"]]).max("time"),
          "cloud_var":  by_calendar_day(daily_mean[VARS["cloud"]]).var("time"),
      })                                             
    return (hist,)


@app.cell
def _(hist):
    for var in ["temp_mean", "temp_min", "temp_max"]:
      hist[var].attrs = {"units": "°C", "long_name": f"2m Temperature ({var.split('_')[1]}) climatology"}

    hist["temp_var"].attrs = {"units": "K²", "long_name": "2m Temperature variance across years"}

    for var in ["precip_mean", "precip_min", "precip_max"]:
      hist[var].attrs = {"units": "mm/day", "long_name": f"Total precipitation ({var.split('_')[1]}) climatology"}

    hist["precip_var"].attrs = {"units": "(mm/day)²", "long_name": "Total precipitation variance across years"}

    for var in ["cloud_mean", "cloud_min", "cloud_max"]:
      hist[var].attrs = {"units": "fraction (0–1)", "long_name": f"Total cloud cover ({var.split('_')[1]}) climatology"}

    hist["cloud_var"].attrs = {"units": "fraction²", "long_name": "Total cloud cover variance across years"}

    print("Variables computed:", list(hist.data_vars))
    return


@app.cell
def _(hist, os):
    out_path = "data/era5_historical_test.zarr"        
    os.makedirs("data", exist_ok=True)
                                            
    print(f"Writing to {out_path} ...")
    hist.to_zarr(out_path, mode="w",           
    zarr_format=2)  
    print("Done!")
    return


if __name__ == "__main__":
    app.run()
