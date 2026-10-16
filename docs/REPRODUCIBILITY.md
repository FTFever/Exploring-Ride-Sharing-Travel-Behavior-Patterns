# Reproduce the workflow

## Environment
Use Python 3.10 or 3.11 for a new environment. The research environment used Python 3.9; this release does not claim a fresh end-to-end installation test.

```bash
python -m venv .venv
# Activate .venv for your operating system.
python -m pip install -e ".[dev,modeling]"
python -m ipykernel install --user --name rideshare --display-name "Rideshare"
jupyter lab
```

Select the Rideshare kernel. Restart it after installing dependencies. Spark preparation requires compatible Java and PySpark 3.5; Windows installations may need Hadoop/winutils. Configure JAVA_HOME/HADOOP_HOME externally.

## Configure directories
Every notebook begins with its path configuration. Edit this first code cell or set environment variables before launching Jupyter. Run standalone scripts from the repository root.

| Variable | Default | Contents |
|---|---|---|
| RIDESHARE_RAW_DIR | data/raw/fhvhv | TLC monthly Parquet records |
| RIDESHARE_PROCESSED_DIR | data/processed | Prepared monthly aggregate directories |
| RIDESHARE_ZONE_DIR | data/reference/taxi_zones | Extracted shapefile and sidecars |
| RIDESHARE_WEATHER_DIR | data/reference/weather_hourly | Weather and zone-reference mapping |
| RIDESHARE_REFERENCE_DIR | data/reference | Weather collector's reference parent directory |

Source/processed datasets, feature exports, prediction records and model binaries remain local and are not distributed. See [DATA_SOURCES.md](DATA_SOURCES.md) to obtain inputs. Existing local data can be used in place.

## Notebook sequence

| Notebook | Run purpose |
|---|---|
| 01_data_ingestion | Acquire/inspect source data; choose months before downloading |
| 02a_prepare_hourly_2021_2023 | Prepare the first 36 analysis months, with checkpoint helpers |
| 02b_prepare_hourly_2024_2025 | Prepare the remaining 24 analysis months |
| 02c_validate_selected_repairs | Stage and validate OD March/April 2024 and dropoff August/October 2025; never auto-promote |
| 03_analysis_baseline_demand | Pickup coverage, totals, hourly and daily trends, 2021–2025 |
| 04_analysis_temporal_patterns | Hour/weekday/seasonality and completed findings, 2021–2025 |
| 05_analysis_spatial_patterns | Pickup maps and share changes 2021–2024 and 2024–2025 |
| 06_model_hourly_demand_forecasting | Features, selection, SHAP, diagnostics, held-out evaluation and completed Section 12 |

Run cells sequentially. Use one Spark preparation session at a time and release it with the final spark.stop() cell. Preparation can rewrite selected outputs: use a fresh output directory when reproducing. The old overlapping 02 notebooks are retained locally and removed from the current GitHub tree; no Git history was rewritten. 07 is a future training-history experiment.

## Weather and held-out targets

```bash
python pipelines/published_collect_hourly_weather.py
python pipelines/published_aggregate_test_week_2026.py
```

The weather collector caches API requests and requires the zone shapefile. The target script prepares January 1–7 from January 2026 raw data; it does not create a full January aggregate and refuses mismatched/incomplete existing output. Its source reference is the organized 02b notebook.

## Notebook 06 modes and artifacts
- review: inspect configuration and existing results; publication default. Some cells require saved run artifacts.
- features: create feature exports without training.
- full: feature generation/loading, tuning, SHAP/ablation, frozen selection and final evaluation. Computationally expensive.

Artifacts live under outputs/06_zonal_forecasting/<RUN_NAME>/. Under features/origin_YYYYMMDD/, training features and targets are separate; forecast features/metadata, quality and manifests accompany them. The final-week labels are withheld from feature construction/selection. Default ML training is a seeded sample of at most 100,000 examples per fit, not all overlapping examples.

## What was verified for this revision
All 60 monthly pickup tables were read and checked; notebooks 03–05 analysis/plots were refreshed on those aggregates without rerunning raw-data preparation. Model findings use existing completed CV/final artifacts; no model was retrained. Run `python tests/check_publication.py` for static publication checks. Saved metric summaries and charts are under reports/published; see [MODEL_RESULTS.md](MODEL_RESULTS.md) for the completed model results and limits.
