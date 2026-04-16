import marimo

__generated_with = "0.22.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    import xarray as xr
    import hvplot.xarray

    import pandas as pd
    import time

    return mo, pd, xr


@app.cell
def _(pd):
    today = pd.Timestamp.now(tz="UTC").floor("D")                 
    today_str = today.strftime("%Y-%m-%d")   # e.g. "2026-03-27"                                            
    month_day_str = today.strftime("%m-%d")  # e.g. "03-27"      
    return month_day_str, today_str


@app.cell
def _(xr):
    forecast = xr.open_zarr(
        "data/forecast_test.zarr"
    )
    forecast
    return (forecast,)


@app.cell
def _(forecast, today_str):
    forecast_temp_mean = forecast["temp_mean"].sel(valid_date=today_str)
    return (forecast_temp_mean,)


@app.cell
def _(xr):
    historical = xr.open_zarr("data/era5_historical.zarr/")
    historical
    return (historical,)


@app.cell
def _(historical, month_day_str):
    historical_temp_mean = historical["temp_mean"].sel(month_day=month_day_str).assign_coords(longitude=(historical.longitude - 180) % 360 - 180).sortby("longitude")
    return (historical_temp_mean,)


@app.cell
def _(forecast_temp_mean, historical_temp_mean):
    delta = forecast_temp_mean - historical_temp_mean
    delta.attrs["long_name"] = "Temperature Anomaly"
    delta.attrs["units"] = "°C"
    return (delta,)


@app.cell
def _(delta):
    delta.hvplot(cmap="RdBu_r", height=550, width=1000)
    return


@app.cell
def _(historical, month_day_str):
    historical["temp_var"].sel(month_day=month_day_str).assign_coords(longitude=(historical.longitude - 180) % 360 - 180).sortby("longitude").hvplot(height=550, width=1000)
    return


@app.cell
def _(historical):
    historical
    return


@app.cell
def _(forecast, mo):
    forecast_dates = [str(d)[:10] for d in forecast.valid_date.values]
    date_slider = mo.ui.slider(
          start=1,
          stop=len(forecast_dates) - 1,
          step=1,
          label="Forecast date",
      )
    return date_slider, forecast_dates


@app.cell
def _(date_slider, forecast_dates, mo):
    selector = mo.hstack([date_slider, mo.md(f"**{forecast_dates[date_slider.value]}**")])
    selector
    return (selector,)


@app.cell
def _(date_slider, forecast, forecast_dates):
    forecast["temp_max"].sel(valid_date=forecast_dates[date_slider.value]).hvplot(cmap="RdBu_r", height=550, width=1000)
    return


@app.cell
def _(date_slider, forecast, forecast_dates, historical, month_day_str):
    ((historical["temp_max"].sel(month_day=month_day_str).assign_coords(longitude=(historical.longitude - 180) % 360 - 180).sortby("longitude"))
     - (forecast["temp_max"].sel(valid_date=forecast_dates[date_slider.value]))).hvplot(cmap="RdBu_r", height=550, width=1000)
    return


@app.cell
def _(selector):
    selector
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
