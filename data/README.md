# Data storage

Large trip datasets are not stored in GitHub. The project currently uses:

- Raw HVFHV trips: `D:/Rideshare industry_NYC/fhvhv`
- Processed outputs: `D:/Rideshare industry_NYC/output`
- Reference geography: `Q:/我的云端硬盘/Uber_dataset/TLC_pipeline/data/raw`

Copy `config/paths.example.yaml` to `config/paths.yaml` to configure local
paths. The local file is ignored by Git. The repository's `raw`, `interim`,
and `processed` directories document the logical lifecycle only; do not copy
the full local datasets into them.
