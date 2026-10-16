# Hourly zonal pickup forecasting

The target is trips per taxi zone per hour. The final forecast covers all 168 hours of January 1–7, 2026 from a single January 1 origin. Train on 2021–2025; do not randomly split time or let future target values enter lag features.

## Features

The [feature dictionary](../src/forecasting/feature_dictionary.csv) defines 40 predictors across zone identity, spatial attributes, calendar, holidays, lagged demand, recent demand summaries and weather. Categorical variables are encoded within training-fitted preprocessing; imputation/scaling are fitted on training examples. Holiday features use the US federal holiday calendar, not an exhaustive NYC event calendar. Future weather uses past-only month/hour climatology; observed ERA5 future weather is not a deployable forecast.

Weather is assigned by shapefile borough to five borough representative locations plus Newark Airport, not separately measured at every taxi zone. Six reference locations correspond to four ERA5 grid cells. Unmapped zones use an explicit Manhattan proxy and an indicator. This spatial approximation must accompany weather interpretations.

## Selection and evaluation

Expanding-window validation origins are April 1, July 1, October 1 and December 1, 2025, each forecasting seven days. Candidate models include a seasonal-naive comparator, per-zone nonseasonal ARIMA baseline, global Random Forest, XGBoost, and a multilayer perceptron neural network. The implementation searches three ARIMA orders and six sampled configurations per machine-learning family. ARIMA is not automatically a seasonal SARIMA model.

Select using cross-validation MAE; also report RMSE, seasonal MASE (168-hour training scale per zone) and mean error/bias (prediction minus actual). A zero MASE denominator produces an undefined value, not an artificially perfect score. Diagnose errors by zone/borough, airport, horizon, hour/weekday, holidays, weather and demand level using plots and group sample sizes.

SHAP on held-out validation examples explains the leading machine-learning model, grouping encoded columns back to original features. Low SHAP contribution alone is not statistical insignificance. Candidate feature-group removal is validated by refitting; retain it only if cross-validation improves under the notebook's stated tolerance. Freeze choices before consulting final test results. Best overall and best machine-learning models are recorded separately.

Notebook 07 will compare training windows 2021–2025, 2022–2025, 2023–2025, 2024–2025 and 2025 using the same final target and controlled validation design. It has not yet been implemented here.
