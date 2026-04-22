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

    return GCSStore, ObjectStore, xr


@app.cell
def _():
    from dask.distributed import Client

    # Spin up a local cluster using all available CPU cores.
    # If you hit memory pressure (swap), reduce n_workers (e.g. n_workers=4).
    client = Client(n_workers=8, threads_per_worker=1)
    print(client)
    return (client,)


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
        chunks={"time": 24}  # 24 hours = 1 day; aligns with daily resample and keeps graph manageable (~10,900 tasks vs ~263k)
        )
    return (ds_historical_full,)


@app.cell
def _():
    VARS = {
          "temp":   "2m_temperature",          # Kelvin                                                     
    }
    return (VARS,)


@app.cell
def _(VARS, ds_historical_full, xr):
    import numpy as np
    import pandas as pd
    import dask

    temp_key = VARS["temp"]
    years    = list(range(1990, 2021))  # 31 years

    # Use a leap year to get all 366 possible calendar days, including Feb 29
    all_month_days = pd.date_range("2000-01-01", "2000-12-31", freq="D").strftime("%m-%d").tolist()
    md_to_idx      = {md: i for i, md in enumerate(all_month_days)}
    n_md           = len(all_month_days)  # 366

    n_lat = ds_historical_full.dims["latitude"]   # 721
    n_lon = ds_historical_full.dims["longitude"]  # 1440
    lat   = ds_historical_full["latitude"].values
    lon   = ds_historical_full["longitude"].values

    # Running accumulators — shape (366, 721, 1440).
    # float32 keeps total memory ~9 GB rather than ~18 GB for float64.
    n_obs       = np.zeros(n_md,                 dtype=np.int32)
    sum_mean    = np.zeros((n_md, n_lat, n_lon), dtype=np.float32)
    sum_min     = np.zeros((n_md, n_lat, n_lon), dtype=np.float32)
    sum_max     = np.zeros((n_md, n_lat, n_lon), dtype=np.float32)
    sum_sq_mean = np.zeros((n_md, n_lat, n_lon), dtype=np.float32)
    sum_sq_min  = np.zeros((n_md, n_lat, n_lon), dtype=np.float32)
    sum_sq_max  = np.zeros((n_md, n_lat, n_lon), dtype=np.float32)

    for year in years:
        print(f"Processing {year}...")
        ds_year = ds_historical_full[[temp_key]].sel(time=str(year))

        # Compute all three daily resamples in one dask call so GCS reads
        # are shared across mean/min/max rather than fetching three times
        dm, di, dx = dask.compute(
            ds_year.resample(time="1D").mean()[temp_key],
            ds_year.resample(time="1D").min()[temp_key],
            ds_year.resample(time="1D").max()[temp_key],
        )
        # dm/di/dx are now in-memory xarray DataArrays: shape (n_days, 721, 1440)

        # Map each day to its slot in the 366-entry calendar-day index.
        # Non-leap years simply never produce a "02-29" entry, so Feb 29
        # accumulates only from the 8 leap years in 1990-2020.
        j = np.array([md_to_idx[md] for md in dm.time.dt.strftime("%m-%d").values])

        # Vectorized accumulation — np.add.at handles repeated indices correctly
        np.add.at(n_obs,       j, 1)
        np.add.at(sum_mean,    j, dm.values)
        np.add.at(sum_min,     j, di.values)
        np.add.at(sum_max,     j, dx.values)
        np.add.at(sum_sq_mean, j, dm.values ** 2)
        np.add.at(sum_sq_min,  j, di.values ** 2)
        np.add.at(sum_sq_max,  j, dx.values ** 2)

    print("Computing final statistics...")

    n = n_obs[:, None, None]  # shape (366, 1, 1) — broadcasts over lat/lon

    # Mean across years, converting Kelvin → °C
    temp_mean = sum_mean / n - 273.15
    temp_min  = sum_min  / n - 273.15
    temp_max  = sum_max  / n - 273.15

    # Population variance: E[X²] - E[X]²
    temp_var_arr     = sum_sq_mean / n - (sum_mean / n) ** 2
    temp_min_var_arr = sum_sq_min  / n - (sum_min  / n) ** 2
    temp_max_var_arr = sum_sq_max  / n - (sum_max  / n) ** 2

    dims   = ["month_day", "latitude", "longitude"]
    coords = {"month_day": all_month_days, "latitude": lat, "longitude": lon}

    hist = xr.Dataset({
        "temp_mean":    (dims, temp_mean),
        "temp_min":     (dims, temp_min),
        "temp_max":     (dims, temp_max),
        "temp_var":     (dims, temp_var_arr),
        "temp_min_var": (dims, temp_min_var_arr),
        "temp_max_var": (dims, temp_max_var_arr),
    }, coords=coords)

    # Shift longitude from −180..180 → 0..360 to match downstream usage
    hist_shifted = hist.assign_coords(longitude=(hist.longitude % 360)).sortby("longitude")

    print("Variables computed:", list(hist_shifted.data_vars))
    return (hist_shifted,)


@app.cell
def _(hist_shifted):
    import sys
    import time
    from dask.diagnostics import ProgressBar

    sys.stdout.reconfigure(line_buffering=True)

    out_path = "../data/era5_historical.zarr"

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Writing to {out_path} ... (attempt {attempt}/{max_attempts})")
            with ProgressBar():
                # Rechunk so there are many output tasks for workers to run in parallel.
                # Output shape is (366 month_days, 721 lat, 1440 lon).
                # This creates ~100 chunks per variable = 600 tasks total across 6 variables.
                hist_shifted.chunk({"month_day": 366, "latitude": 72, "longitude": 144}).to_zarr(out_path, mode="w", zarr_format=2)
            print("Done!")
            break
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            if attempt < max_attempts:
                wait = 30 * attempt  # 30s, 60s, 90s, 120s
                print(f"Retrying in {wait}s ...")
                time.sleep(wait)
            else:
                raise
    return


if __name__ == "__main__":
    app.run()
