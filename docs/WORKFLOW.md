# Project workflow

## 1. Data foundation and validation

Establish authoritative datasets, document grain and metrics, reconcile
aggregations, verify temporal and geographic coverage, and record filters or
intentional non-materialization.

**Deliverables:** data dictionary, validation rules, coverage report, and known
limitations.

## 2. Exploratory data analysis

Examine distributions, missingness, zero demand, anomalies, platform
differences, correlations, and structural breaks.

**Deliverables:** reproducible EDA notebook and findings report.

## 3. Spatial and temporal analysis

Analyze hourly, weekly, monthly, seasonal, zone, borough, airport, platform,
and OD patterns. Evaluate congestion-pricing periods with appropriate
normalization and stated assumptions.

**Deliverables:** research-quality figures, maps, tables, and findings.

## 4. Dashboard

Generate dashboard tables from validated analytical products. The dashboard
filters and presents prepared metrics rather than redefining calculations.

**Deliverables:** dashboard data pipeline, application, and methodology page.

## 5. Forecasting dataset construction

Define targets and horizons, construct a complete zone-hour panel, represent
true zero demand, prevent leakage, create lag and rolling features, and define
chronological train/validation/test periods.

**Deliverables:** versioned modeling table and feature documentation.

## 6. Model building and testing

Compare naive and seasonal baselines, regularized regression, tree-based ML,
and appropriate time-series approaches. Add complexity only when evaluation
justifies it.

**Deliverables:** reproducible training runs, predictions, and metadata.

## 7. Model evaluation and error analysis

Evaluate by horizon, zone, demand level, hour, weekday/weekend, geography, and
unusual periods. Primary metrics include MAE and RMSE, with demand-weighted
measures where appropriate.

**Deliverables:** comparison table, diagnostics, and selection rationale.

## 8. Final reproducible reporting

Consolidate methods, results, limitations, dashboard outputs, and model
evidence into a reproducible project release.

## Phase gate

Modeling starts only after the target dataset reconciles to authoritative
zone-hour totals. A phase is complete when its documented outputs can be
regenerated and its validation checks pass.
