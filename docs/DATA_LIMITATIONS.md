# Definitions, quality and limits

- HVFHV includes all recorded platforms; these results are not exclusively Uber trips.
- Existing cleaning excludes nonpositive fare/pay, distance, duration, invalid request order and extreme distances/speeds. It can exclude real trips and must be interpreted as a cleaned sample.
- Existing 2024/2025 rules deduplicate complete rows before filling CBD fee nulls. Distance is greater than zero and at most 200 miles; calculated duration is greater than zero and at most 10,800 seconds; speed is greater than 1 and at most 120 mph. Speed uses reported trip_time; calculated duration uses pickup/dropoff timestamps.
- Pickup and OD use pickup date/hour. Earlier-year dropoff uses dropoff calendar date/hour. Legacy 2024/2025 dropoff uses pickup date with dropoff hour. Cross-year dropoff comparisons therefore include a definition break. Publication preserves the processing logic.
- January 2019 and 2020 are outside the earlier-year preparation scope. A missing date is not zero demand. February 2019 and January 2021 have boundary limitations recorded in aggregation contracts.
- Several 2019 low-demand dates coincide with cleaning attrition (July 31, August 1–4 and August 19). Extremely low values are not automatically genuine demand collapses. Below-median values are not inherently outliers. Any same-weekday/hour/month replacement is an analytical imputation that must preserve observations and a replacement flag; do not overwrite raw data.
- Hourly pickup/dropoff totals differ because trips cross hours/dates and because of the legacy dropoff definition. Monthly city totals can look similar without hourly equality.
- Taxi-zone shapefiles contain multiple polygons for some IDs. Dissolve by LocationID before expecting unique zone records. Not every observed location has mapped geometry.
- DST produces missing spring local hours and repeated autumn local hours. UTC is the weather key. Local-fold weather values are combined; precipitation is an hourly intensity average, not a two-hour total.
- The four 2024/2025 repairs are staged, separately validated artifacts. Their existence does not imply promotion into original analytical directories.
- The January 2025 policy-date indicator supports descriptive comparisons; these notebooks do not establish a causal policy effect.
- Saved charts are research outputs from existing runs. Their presence does not certify full data validation or completed model tuning. No winning model is claimed until all relevant evaluations finish.
