# Executed research notebooks

Read 01 → 02 → 03 → 04 → 05 → 06. Paths and adjustable settings are in each notebook's first code cell. Section notes explain the input, transformation, output and interpretation of the main blocks; notebook 06 includes a method reference for feature generation, training and evaluation.

| Notebook | Published execution | Purpose |
|---|---|---|
| 01_data_ingestion | Executed | Metadata inventory of 71 source months; raw counts and schema availability |
| 02_data_preparation_2019_2025 | Outputs cleared | A fresh one-go preparation workflow, February 2019–2025 excluding 2020 |
| 03_analysis_baseline_demand | Executed | Pickup baseline and hourly/daily trends, 2021–2025 |
| 04_analysis_temporal_patterns | Executed | Calendar/hour profiles and recorded findings, 2021–2025 |
| 05_analysis_spatial_patterns | Executed | Pickup maps and 2021–2024 / 2024–2025 share comparisons |
| 06_model_hourly_demand_forecasting | Executed review | Complete method code plus tables/figures from the completed research run; no new fitting |

The separate 02a/02b/02c files and older overlapping variants are backed up locally and removed from the current GitHub tree. For notebook 02 choose a fresh processed output directory; it refuses existing monthly destinations. Notebook 06 review runs from the small published result artifacts. To reproduce feature generation/training, obtain inputs, select features/full, use a separate run name and execute all cells. See [the full guide](../docs/REPRODUCIBILITY.md).
