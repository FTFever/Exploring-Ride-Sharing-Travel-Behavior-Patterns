# Verification

Run `python tests/check_publication.py` for syntax, portable paths, empty notebook outputs, scope and document checks. This static check does not execute Spark or fit models. The October 2026 analysis refresh separately executed the descriptive analysis cells on all 60 existing monthly pickup aggregates. CI intentionally uses no source datasets or expensive model training.
