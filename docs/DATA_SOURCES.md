# Data sources and attribution

Datasets are obtained separately and are not redistributed in this repository. The MIT license applies to project code, not third-party datasets or map geometry.

| Source | Use | Access and reference |
|---|---|---|
| NYC Taxi and Limousine Commission, High Volume FHV trip records | Monthly trip-level pickup/dropoff timestamps, zones, fares, distance, duration and service identifiers | [Official trip record portal](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page); [HVFHV data dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_hvfhs.pdf) |
| NYC TLC taxi-zone boundaries and lookup | LocationID geography, boroughs, maps and weather mapping | Download through the taxi-zone section of the same [TLC portal](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). Extract all shapefile sidecars into the configured zone directory. Original local geometry download date was not recorded. |
| Open-Meteo Historical Weather API, ERA5 reanalysis | Hourly NYC weather, 2021 through January 7, 2026 | [API documentation](https://open-meteo.com/en/docs/historical-weather-api), [license and citation](https://open-meteo.com/en/licence) |
| pandas USFederalHolidayCalendar | Federal holiday dates and observed dates | [Holiday calendar documentation](https://pandas.pydata.org/docs/user_guide/timeseries.html#holidays-holiday-calendars) |

## TLC acquisition

Monthly Parquet URL pattern:

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/fhvhv_tripdata_YYYY-MM.parquet
```

Download the months required by the chosen notebook into RAW_DIR. Earlier-year preparation covers February–December 2019 and all months of 2021–2023; existing 2024–2025 preparation supports analysis/model training. Final testing needs January 2026 raw data but prepares only January 1–7. Availability of additional local months does not mean all are used. TLC/provider records may contain omissions or errors; inspect schemas and validation rather than assuming completeness. Consult [NYC terms](https://www.nyc.gov/main/terms-of-use) for source rights.

## Weather acquisition and transformations

The published weather collector calls `https://archive-api.open-meteo.com/v1/archive` with `models=era5`, UTC, Celsius, millimetres and wind speed in m/s, caching requests and raw responses locally. It requests temperature, humidity, dew point, apparent temperature, precipitation, rain, snowfall, cloud cover, sea-level pressure, wind speed/direction and weather code. Borough representative points plus Newark Airport provide six reference locations (four ERA5 grid cells). Borough membership assigns zones to weather references; this is not fine-resolution measured zone weather.

Open-Meteo API weather is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: Open-Meteo, using Copernicus Climate Change Service / ECMWF ERA5 reanalysis; see provider documentation for upstream attribution/terms. Changes here include selecting points/time windows, UTC-to-New-York conversion, local DST-fold aggregation and zone-reference mapping. Please retain this attribution in derived figures and publications. Suggested Open-Meteo citation: Zippenfenig (2023), Open-Meteo.com Weather API, [doi:10.5281/zenodo.7970649](https://doi.org/10.5281/zenodo.7970649).

ERA5 is retrospective reanalysis, not an archived weather forecast issued at the demand forecast origin. Notebook 06 uses past-only weather climatology for future horizons; actual future reanalysis must not silently enter operational predictions.
