# Data sources

## NYC TLC High-Volume For-Hire Vehicle trip records

- Publisher: New York City Taxi and Limousine Commission
- Format: monthly Parquet files
- Filename pattern: `fhvhv_tripdata_YYYY-MM.parquet`
- Raw local archive: configured by `raw_data_dir`
- Observed local coverage: February 2019 through April 2026

The ingestion workflow derives monthly download URLs from the TLC filename
pattern and validates Parquet metadata after download.

## TLC taxi-zone reference data

Reference assets include the taxi-zone lookup table and taxi-zone geometry.
Their local location is configured by `reference_data_dir`. Before a reference
file is committed to Git, confirm and document its redistribution terms.

## Processed analytical products

Processed Spark Parquet outputs are stored outside Git and configured through
`processed_data_dir`. Their meanings and grains are documented in
`DATA_DICTIONARY.md`.
