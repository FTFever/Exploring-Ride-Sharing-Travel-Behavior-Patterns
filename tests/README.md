# Publication verification

Run `python tests/check_publication.py`. Checks cover Python syntax, the six canonical notebook files, the consolidated 71-month scope, execution counts and absence of error outputs in every non-02 notebook, cleared notebook 02 outputs, embedded plots, portable paths, source/model artifact separation and README links. CI never runs Spark, downloads data or fits models. The research revision separately executed 01/03/04/05 and 06 reporting against local inputs and saved modeling evidence.
