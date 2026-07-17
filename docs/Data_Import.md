# Data Import

The offline import boundary accepts local CSV, CSV.GZ, and Parquet-style file
paths through explicit import roots. Safety checks reject path traversal,
symlinks outside the import root, unsupported file types, and spreadsheet
formula-like CSV cells.

Provider import records preserve source checksums and raw records. Unsupported
or unknown schemas are rejected explicitly; missing provider fields are not
fabricated during normalization.

Example fixtures:

- `examples/provider_datasets/synthetic_options.csv`
- `examples/provider_datasets/synthetic_bad_quotes.csv`
- `examples/provider_datasets/synthetic_manifest.json`
