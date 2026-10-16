# Hourly pickup forecasting results

### 12.1 Execution status and experiment coverage
The saved `zonal_week_ahead_v1` run contains complete four-fold cross-validation for **22 candidates** (18 machine-learning configurations, three ARIMA orders and a weekly-naive comparator), feature ablation, SHAP summaries, a frozen selection and final-week evaluation. The fit log records 84 fitted candidate/fold combinations, with no warnings recorded in that log. The final ARIMA log has 263 successful zone fits with no recorded warnings. These observations describe saved artifacts inspected on October 16, 2026; this interpretation update did not rerun training.

Training inputs span **2021–2025**. Each validation origin forecasts 168 hours: April 1, July 1, October 1 and December 1, 2025. The final test is the separate, previously reserved **January 1–7, 2026** week. The audited training grid contains 43,825 local-clock rows and 263 eligible zones, excluding 10 DST clock hours; zone 103 was excluded for zero training activity. Every model is scored on 44,184 final zone-hours (263 × 168), with no missing targets or predictions in the saved metric table.

### 12.2 Validation results and selected model
Metrics below are means across the four validation folds, in trips per zone-hour for MAE/RMSE/bias. MASE is dimensionless. Positive bias means overprediction.

| Selected candidate | MAE | RMSE | MASE | Bias | MAE across folds: min–max |
|---|---:|---:|---:|---:|---:|
| weekly_naive | 22.529 | 44.858 | 1.295 | -2.379 | 14.934–35.322 |
| RandomForest_05 | 15.053 | 29.571 | 0.980 | +0.031 | 12.533–18.633 |
| XGBoost_06 | 14.599 | 28.465 | 3.327 | -0.961 | 12.685–16.494 |
| NeuralNetwork_01 | 15.575 | 29.681 | 11.819 | +1.199 | 13.307–18.529 |
| arima_100 | 44.454 | 77.181 | 2.447 | -11.141 | 37.286–53.364 |

**XGBoost_06 is the frozen validation winner**, with MAE 14.599, a **35.2%** reduction from weekly naive. It uses 400 trees, maximum depth 6, learning rate 0.03 and row/column subsampling 0.8. It is best within this configured search and sampling budget, not a claim of universal optimality. RandomForest_05 is second on validation MAE. ARIMA(1,0,0) is the best of the three tested ARIMA orders but is substantially weaker than weekly naive; a nonseasonal ARIMA baseline does not capture the weekly structure as effectively as the lag-based ML models. Fold-level variation remains material; July and December are more difficult for the selected XGBoost candidate than April and October.

### 12.3 Held-out first week of 2026

| Model | MAE | RMSE | MASE | Bias | MAE improvement over weekly naive |
|---|---:|---:|---:|---:|---:|
| WeeklyNaive | 28.399 | 65.608 | 1.582 | -2.615 | 0.0% |
| RandomForest | 22.174 | 53.543 | 1.256 | +3.430 | 21.9% |
| XGBoost | 19.690 | 46.206 | 2.670 | +3.171 | 30.7% |
| NeuralNetwork | 19.764 | 41.092 | 25.360 | +1.880 | 30.4% |
| ARIMA | 40.396 | 68.639 | 2.189 | +3.079 | -42.2% |

XGBoost retains the lowest test MAE (**19.690**, 30.7% below weekly naive), narrowly ahead of the neural network (19.764). The neural network has the lowest test RMSE (**41.092**, versus XGBoost 46.206), suggesting fewer/lower large errors under squared loss in this week. This does not change the frozen MAE-based selection after seeing test results. XGBoost's test MAE is about 34.9% higher than its mean validation MAE. Its positive test bias (+3.171) reverses the slightly negative mean validation bias (−0.961), showing that aggregate calibration varies over time.

**MASE requires special attention:** RF has lower average scaled error than XGBoost despite higher absolute error. The mean of zone-hour scaled errors gives very small seasonal scales substantial influence. Neural-network test MASE is 25.360; its Unknown-location group has MASE 1493.145 despite bias of about +5.715 trips/hour. XGBoost's Unknown group has MASE 92.493. These small/low-variation-location contributions make pooled MASE unstable relative to MAE/RMSE. Retain the reported values, investigate the training-scale distribution, and do not interpret the MAE winner as a winner on every metric. No metric formula or scored population was changed for this summary.

### 12.4 Where errors concentrate
For the selected XGBoost model, Manhattan has MAE **30.037** (11,088 zone-hours), Brooklyn **24.162** (10,248), Queens **15.781** (11,424), Bronx **12.702** (7,224) and Staten Island **4.880** (3,360). These are unweighted zone-hour averages, so population size and activity level matter; lower error is not necessarily better relative performance.

Airport zones have MAE **65.172** and bias **−21.185** across 504 zone-hours, compared with MAE **19.165** and bias **+3.452** elsewhere (43,680 zone-hours). Airport underprediction coexists with overall overprediction. For actual demand above 200 trips/hour, XGBoost MAE is **65.467** with bias **−19.839** (5,280 zone-hours); for 51–200 trips/hour, MAE is **19.537** with bias **+8.208** (20,637 zone-hours). Thus peaks are still underpredicted while moderate demand tends to be overpredicted. Demand-band diagnosis conditions on observed outcomes and is descriptive, not a forecast-time feature.

The largest average XGBoost error by hour of day occurs at **1** (MAE 30.396); the smallest is at **5** (MAE 10.189). These groups should be read with their support counts and the holiday-week composition.

The largest average XGBoost error by weekday occurs at **Thursday** (MAE 39.817); the smallest is at **Saturday** (MAE 13.002). These groups should be read with their support counts and the holiday-week composition.

### 12.5 Features and ablation
Held-out SHAP summaries for the selected XGBoost candidate are dominated by **same-hour four-week mean demand** (mean absolute SHAP 48.121), followed by 168-hour lag (12.328), 336-hour lag (8.086), 504-hour lag (5.074) and recent seven-day mean (4.051). Weekly persistence carries much more predictive information in this model than individual spatial/weather attributes. SHAP magnitude is a model attribution in prediction units, not causal importance or a significance test; correlated predictors can share/substitute attribution. Only 100 explanation rows per fold and 30 training background rows are configured.

Dropping spatial features increases mean validation MAE by **0.085** (to 14.684); dropping holiday features increases it by **0.317** (to 14.916). Neither ablation is accepted. All 40 predictors remain in the frozen ML specification. Small SHAP values therefore did not justify removing these feature groups under the observed validation evidence.

### 12.6 Limitations and next steps
- Final testing covers one winter/holiday week; it cannot establish year-round accuracy or stability under different shocks. The first-week result must remain a holdout, not another tuning fold.
- A seeded maximum of 100,000 training examples bounds each ML fit. Results reflect this resource budget and small hyperparameter search, not all possible five-year overlapping examples.
- Weather is spatially coarse ERA5 reanalysis mapped through borough reference locations. Forecast-horizon features use past-only climatology rather than actual future weather; evaluate archived issued forecasts separately before operational deployment.
- Sparse-zero assumptions, zone eligibility, unmapped IDs and DST treatment affect the evaluation population. Report these with metrics and inspect low-scale zones before making MASE-based claims.
- Nonseasonal per-zone ARIMA and global ML use cross-zone information differently. Seasonal ARIMA and other temporal architectures remain future comparators, not evaluated results.
- Error associations by borough, holiday and weather do not establish causes. No congestion-pricing causal effect is estimated here.
- Notebook 07 should reuse the frozen selection and a controlled evaluation design for training windows 2021–2025, 2022–2025, 2023–2025, 2024–2025 and 2025. This experiment has not yet been run.
