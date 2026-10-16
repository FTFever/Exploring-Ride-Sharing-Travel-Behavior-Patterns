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
| 01_data_ingestion | Execute a 71-file footer/schema inventory; no whole-file Spark scan |
| 02_data_preparation_2019_2025 | One sequential fresh run: clean/aggregate/validate 71 months across pickup, dropoff and OD; intentionally unexecuted in GitHub |
| 03_analysis_baseline_demand | Pickup coverage, totals, hourly and daily trends, 2021–2025 |
| 04_analysis_temporal_patterns | Hour/weekday/seasonality and completed findings, 2021–2025 |
| 05_analysis_spatial_patterns | Pickup maps and share changes 2021–2024 and 2024–2025 |
| 06_model_hourly_demand_forecasting | Features, selection, SHAP, diagnostics, held-out evaluation and completed Section 12 |

Run cells sequentially. The source series begins in February 2019; the 71 selected months exclude all of 2020. Notebook 02 requires a **fresh OUTPUT_DIR** and stops before expensive work if a selected destination exists. It does not overwrite research outputs, resume checkpoints, or invoke separate repairs. A successful run creates 213 validated monthly aggregate tables and a validation summary. It releases Spark after processing. Point downstream notebooks to this same processed directory; their descriptive scope is 2021–2025. Earlier notebook variants remain local, and Git history is retained.

Notebooks 01 and 03–06 have executed outputs embedded in GitHub. Notebook 01 reads footer metadata, not raw trip samples; its source counts are not cleaned demand. Notebook 06 executes a read-only review of completed training/evaluation artifacts, with saved figures labeled as such. This is distinct from claiming a new full model fit. Notebook 02's consolidated implementation was syntax-checked but was not run on the complete raw archive in this revision.

## Weather and held-out targets

```bash
python pipelines/published_collect_hourly_weather.py
python pipelines/published_aggregate_test_week_2026.py
```

The weather collector caches API requests and requires the zone shapefile. The target script prepares January 1–7 from January 2026 raw data; it does not create a full January aggregate and refuses mismatched/incomplete existing output. Its cleaning source reference is the consolidated notebook 02.

## Notebook 06 modes and artifacts
- review: execute the report from published aggregate metrics and saved research figures; publication default. It does not load raw data, require feature matrices, or fit models.
- features: create feature exports without training.
- full: feature generation/loading, tuning, SHAP/ablation, frozen selection and final evaluation. Computationally expensive.

New artifacts live under outputs/06_zonal_forecasting/<RUN_NAME>/; the revised default reproduction name is zonal_week_ahead_reproduction_v2. Historical summaries/figures are read separately from reports/published/modeling. Cache signatures from the historical training run are not asserted to match the revised source. Under features/origin_YYYYMMDD/, training features and targets are separate; forecast features/metadata, quality and manifests accompany them. The final-week labels are withheld from feature construction/selection. Default ML training is a seeded sample of at most 100,000 examples per fit, not all overlapping examples.

## What was verified for this revision
All 60 monthly pickup tables were read and checked; notebooks 03–05 analysis/plots were refreshed on those aggregates without rerunning raw-data preparation. Model findings use existing completed CV/final artifacts; no model was retrained. Every non-02 code cell has a real execution count. Run `python tests/check_publication.py` to check syntax, executed-output status, no error outputs, portable paths, source scope and links. Saved metric summaries and charts are under reports/published; see [MODEL_RESULTS.md](MODEL_RESULTS.md) for the completed model results and limits.
