### Tableau Preview

View the interactive dashboard here: [Tableau Dashboard](https://public.tableau.com/views/RideSharingTripDemandPattern/Ride-SharingTravelBehaviorPatterninNYC2025?:language=en-US&publish=yes&:sid=&:redirect=auth&:display_count=n&:origin=viz_share_link)



# Ride-Sharing Travel Behavior Patterns Analysis

## Overview

This project analyzes large-scale ride-sharing trip records to understand travelers’ preferences across time and geographic zones, as well as how these patterns evolve over time. It combines **big data processing**, **data cleaning**, **performance metric design**, and **dashboard-oriented outputs** to support clear, efficient, and accessible insights for a broad audience, including researchers, practitioners, and policymakers.

The original dataset contains **over 100 million trip records spanning 2019–2025**, which introduces nontrivial challenges in data storage, cleaning, and computation. Compared with small-scale datasets, this project emphasizes scalable workflows and reproducible pipelines for handling high-volume, high-frequency mobility data.

This GitHub repository primarily showcases scripts for:

* Large-scale data processing using **PySpark**
* Data cleaning and feature engineering using **Pandas**
* Preparing analysis-ready datasets and summary metrics for downstream analysis and visualization

## Objectives

* Characterize ride-sharing travel behavior across time and space
* Identify temporal dynamics and zone-level heterogeneity in travel patterns
* Demonstrate scalable data engineering practices for transportation analytics
* Enable rapid exploration and communication of results through well-structured outputs

## Data Sources

Depending on the analysis, data may include:

* Ride-sharing trip records and service logs
* Transportation network and service data
* Travel demand and mobility datasets
* Socioeconomic and demographic indicators
* Public-sector administrative and survey data

> **Note:** Some datasets may be restricted or not publicly shareable. All scripts are written to be modular and adaptable so users can apply them to their own data sources.

## Project Structure
<!--
```
├── data/               # Raw and processed data (not tracked if restricted)
├── notebooks/          # Exploratory analysis and experiments
├── src/                # Core data processing and modeling code
├── results/            # Figures, tables, and summary outputs
├── docs/               # Documentation and references
└── README.md           # Project overview
```
-->
## Tools and Technologies

* **Python** (pandas, numpy, PySpark, statsmodels, scikit-learn)
* **R** (tidyverse, fixest, causal inference packages)
* Jupyter Notebooks
* Git & GitHub for version control

## Expected Outputs

* Reproducible and scalable data processing pipelines
* Cleaned, analysis-ready mobility datasets
* Policy- and operations-relevant metrics and KPIs
* Visual summaries of ride-sharing travel behavior patterns
* Research-ready figures and tables

## Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/FTFever/Exploring-Ride-Sharing-Travel-Behavior-Patterns.git
   ```
2. Install required dependencies (Python and/or R environments as needed)
3. Explore the notebooks and scripts for example workflows

## Project Status

🚧 **Active research project** — methods, structure, and scope may evolve as new data and research questions are introduced.

## Contributions

Contributions, feedback, and suggestions are welcome. Please open an issue or submit a pull request.

## Author

**Juan Wang**  
Ph.D. in Transportation Planning and Economics  
Specializing in transportation systems, causal inference, and big data analytics

## License

This project is intended for research and educational purposes. Licensing details will be added as the project matures.
