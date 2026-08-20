# Exploring Ride-Sharing Travel Behavior Patterns

## Overview

This project analyzes NYC high-volume for-hire vehicle activity with two goals:

1. Analyze spatial and temporal travel behavior among ride-sharing users.
2. Forecast hourly ride-sharing pickup demand at the TLC taxi-zone level.

The original dataset contains **over 100 million trip records spanning 2019–2026**, which introduces nontrivial challenges in data storage, cleaning, and computation. Compared with small-scale datasets, this project emphasizes scalable workflows and reproducible pipelines for handling high-volume, high-frequency mobility data.

Large raw and processed datasets remain in external local storage. GitHub
contains code, configuration templates, documentation, tests, and lightweight
results needed to reproduce the workflow.

## Data Sources

Depending on the analysis, data may include:

* Ride-sharing trip records and service logs
* Transportation network and service data
* Travel demand and mobility datasets
* Socioeconomic and demographic indicators
* Public-sector administrative and survey data

> **Note:** Some datasets may be restricted or not publicly shareable. All scripts are written to be modular and adaptable so users can apply them to their own data sources.

## Workflow

1. Data foundation and validation
2. Exploratory data analysis
3. Spatial and temporal analysis
4. Dashboard development
5. Forecasting dataset construction
6. Machine-learning and time-series modeling
7. Model evaluation and error analysis
8. Final reproducible reporting

See [the complete workflow](docs/WORKFLOW.md).

## Repository Structure

```
config/       Configuration templates and project settings
data/         Storage documentation and small reference/sample data
docs/         Scope, workflow, data dictionary, validation, and decisions
notebooks/    Research notebook organization and migration guidance
src/          Reusable Python package
pipelines/    Executable workflow entry points
dashboard/    Dashboard source and data contracts
tests/        Automated unit and integration tests
reports/      Lightweight validation, analysis, and modeling outputs
models/       Model-artifact documentation
```
## Tools and Technologies

* **Python** (pandas, numpy, PySpark, statsmodels, scikit-learn)
* **R** (tidyverse, fixest, causal inference packages)
* Jupyter Notebooks
* Git & GitHub for version control

## Data Configuration

Copy `config/paths.example.yaml` to `config/paths.yaml` and update it for the
local machine. The real configuration is ignored by Git, so machine-specific
paths are not published.

See the [data dictionary](docs/DATA_DICTIONARY.md).

## Development Setup

```bash
python -m pip install -e ".[dev]"
```

```powershell
Copy-Item config/paths.example.yaml config/paths.yaml
```

## Dashboard

View the existing [Tableau dashboard](https://public.tableau.com/views/RideSharingTripDemandPattern/Ride-SharingTravelBehaviorPatterninNYC2025?:language=en-US&publish=yes&:display_count=n).

The current `Dashboard.html` embed and three historical figures remain at the
repository root until their generation workflow is made reproducible.

## Documentation

- [Project scope](docs/PROJECT_SCOPE.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Workflow](docs/WORKFLOW.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)

## Author

**Juan Wang**  
Ph.D. in Transportation Planning and Economics  
Specializing in transportation systems, causal inference, and big data analytics

## License

A project license has not yet been selected. Until one is added, the repository
does not grant an open-source reuse license.
