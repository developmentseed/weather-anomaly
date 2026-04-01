import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    import xarray as xr
    import hvplot.xarray

    return (xr,)


@app.cell
def _(xr):
    forecast = xr.open_zarr(
        "data/forecast_test.zarr"
    )
    forecast
    return (forecast,)


@app.cell
def _(forecast):
    forecast["temp_max"].sel(valid_date="2026-04-01").hvplot(cmap="RdBu_r", height=550, width=1000)
    return


@app.cell
def _(xr):
    historical = xr.open_zarr("data/era5_historical_test.zarr/")
    historical
    return (historical,)


@app.cell
def _(historical):
    historical["temp_var"].sel(month_day="04-01").plot()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
