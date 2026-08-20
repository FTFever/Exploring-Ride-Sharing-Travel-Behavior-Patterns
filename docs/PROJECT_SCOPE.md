# Project scope

## Objectives

1. Analyze spatial and temporal travel behavior among NYC ride-sharing users.
2. Forecast hourly ride-sharing pickup demand at the TLC taxi-zone level.

## Current analytical period

Processed analytical products currently focus on 2024 and 2025. The raw HVFHV
archive spans February 2019 through April 2026.

## Platforms and geography

- `HV0003`: Uber
- `HV0005`: Lyft
- Principal spatial unit: NYC TLC taxi zone
- Directions: pickup, drop-off, and origin-destination pair

## Policy context

The current processing code labels January 5, 2025 as the start of the
post-policy period for NYC congestion pricing. January 1-4, 2025 requires
explicit treatment in pre/post comparisons.

## Current boundaries

- Large raw and processed data remains outside GitHub.
- Dashboard aggregates are presentation products, not modeling inputs.
- Final forecasting choices are deferred until validation and EDA are complete.
