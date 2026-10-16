# Data quality and interpretation

## Analysis population
The published baseline, temporal and spatial analyses use cleaned pickups for January 2021–December 2025. All recorded HVFHV platforms are included; the results are not exclusively Uber trips. All 60 monthly pickup inputs passed the refreshed key/date/count checks. These checks do not establish that provider records capture every real trip.

## Cleaning and coverage
Cleaning excludes invalid request order, nonpositive fare/pay/distance/duration and extreme distances/speeds. It therefore describes a cleaned sample. Existing rules deduplicate complete rows before CBD-fee null handling. Distance is greater than zero and at most 200 miles; calculated duration is greater than zero and at most 10,800 seconds; speed is greater than 1 and at most 120 mph. Speed uses reported trip_time; calculated duration uses timestamps. Missing source months are not zeros. Low demand is not an outlier merely because it falls below the median; no new imputation was performed for this release.

## Geography and clock time
Taxi-zone polygon records are dissolved by LocationID. Unknown/unmapped locations remain in citywide totals and share denominators but cannot be mapped. Maps show per-day volume or citywide share, not density by land area. Local clock hours include daylight-saving transitions. Weather uses canonical UTC with explicit local-time processing.

## Forecasting
Model training uses 2021–2025, with four 2025 validation weeks and a separate January 1–7, 2026 held-out forecast test. This test week is not part of descriptive trend analysis. Weather resolution, low-variation zones, sampling budgets and single-week testing limit generalization. See [model results](MODEL_RESULTS.md) for metric-specific limitations.

## Causal interpretation
Annual changes and the January 2025 indicator are descriptive. They do not identify the causal effect of congestion pricing. A separate design with appropriate counterfactuals, controls and diagnostics is planned.
