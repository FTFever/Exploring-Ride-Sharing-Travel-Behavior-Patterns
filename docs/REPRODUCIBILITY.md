# Run the workflow

## Installation and directories

Use Python 3.10 or 3.11 for a new environment. The research environment used Python 3.9; a clean installation on a new machine has not been executed as part of publication. From the repository root:

```bash
python -m venv .venv
# Activate the environment using your operating system's command.
python -m pip install -e ".[dev,modeling]"
python -m ipykernel install --user --name rideshare --display-name "Rideshare"
jupyter lab
```

Select the Rideshare kernel. Installing a package into a different interpreter does not make it available to the notebook. Restart the kernel after changing dependencies.

All directory configuration is in the first code cell of each notebook. Defaults are repository-relative. You can edit that cell or supply these environment variables before launching Jupyter:

| Variable | Default | Contents |
|---|---|---|
| RIDESHARE_RAW_DIR | data/raw/fhvhv | TLC monthly HVFHV Parquet files |
| RIDESHARE_PROCESSED_DIR | data/processed | Prepared monthly aggregate directories |
| RIDESHARE_ZONE_DIR | data/reference/taxi_zones | Extracted shapefile and sidecar files |
| RIDESHARE_WEATHER_DIR | data/reference/weather_hourly | Collected weather and zone mapping |
| RIDESHARE_REFERENCE_DIR | data/reference | Parent directory used by weather collection script |

The original source datasets, processed datasets, feature exports and fitted models are not distributed. Existing local datasets can be used by setting the directory variables; copying them into the repository is unnecessary. Spark notebooks require a compatible Java installation and PySpark 3.5; Windows users may need a compatible Hadoop/winutils setup. Configure JAVA_HOME/HADOOP_HOME externally. The scripts should be run from the repository root.

## Notebook order

1. **01_data_ingestion**: inspect/download source records. Inspect configured months before running; downloading consumes disk and bandwidth.
2. **02_data_processing** and **02_data_processing_additions_06_03**: original preparation implementations. These overlap; they are retained for provenance, not intended to be replayed consecutively over existing outputs.
3. **02_data_processing_additions_20261013**: scoped earlier-year hourly preparation (February–December 2019 and 2021–2023; exclude 2020). Read checkpoint contracts before resuming.
4. **02_data_repairs_2024_2025_hourly**: four separate staged repairs, OD March/April 2024 and dropoff August/October 2025. Never promote staged outputs automatically. Run only when the earlier Spark session has stopped, with no concurrent writers.
5. **03_analysis_baseline_demand**: coverage, totals, daily/hourly demand and data limitations.
6. **04_analysis_temporal_patterns**: pickup hour, weekday and seasonal patterns.
7. **05_analysis_spatial_patterns**: zones, boroughs, maps and spatial comparisons.
8. **06_model_hourly_demand_forecasting**: features, tuning, comparison, interpretation and error diagnosis. Notebook 07 (training-history-length experiment) is planned and not included.

Run cells in order within the selected notebook. The 02 notebooks preserve historical cleaning and write behavior; inspect scope and existing output/checkpoints before execution. They are not an unattended orchestration pipeline. Publication does not restart any research execution.

## Weather and test targets

```bash
python pipelines/published_collect_hourly_weather.py
python pipelines/published_aggregate_test_week_2026.py
```

Weather collection caches requests and requires the zone shapefile. The test-target script needs January 2026 raw Parquet and the published preparation notebook; it refuses to overwrite incomplete/existing mismatched results. It prepares January 1–7 only, not a full January aggregate.

## Notebook 06 modes

- `review`: inspect configuration and existing results; published default. Some review cells require previously generated files.
- `features`: generate training and forecast feature exports without fitting models.
- `full`: generate/load features, cross-validate and tune, interpret/ablate, freeze selection, then fit and evaluate the final week. This is computationally expensive.

Outputs are written beneath `outputs/06_zonal_forecasting/<RUN_NAME>/`. Feature exports are under `features/origin_YYYYMMDD/`: train_features.parquet, train_targets_and_metadata.parquet, forecast_features.parquet, forecast_metadata.parquet and quality/manifest JSON. Keep final-week target labels out of feature construction and model selection. The default training sample budget is 100,000 examples; the notebook does not fit every overlapping example in five years.

## Publication verification and status

Run `python tests/check_publication.py` for notebook syntax, cleared output, portable path, and package-file checks. This is a static publication check, not a fresh end-to-end data/model run. Saved figures are listed in reports/published/README.md. At publication inspection, the research fit log contained one successful Random Forest candidate/fold; no complete comparison or winning model is claimed. No model training or data regeneration was performed for publication.
