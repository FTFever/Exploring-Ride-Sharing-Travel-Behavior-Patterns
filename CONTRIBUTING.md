# Contributing

Open an issue describing the notebook, environment and reproducible failure. Keep datasets, private paths, credentials and generated model files out of pull requests. Clear notebook outputs before committing. Explain changes to cleaning rules, date/hour definitions or feature availability explicitly; these affect comparability and leakage. Run `python tests/check_publication.py` before submitting. Do not run large downloads, Spark aggregation or model training in CI. Use separate output directories for experiments and preserve original analytical outputs.
