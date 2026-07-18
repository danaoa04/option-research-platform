# Data Import

The offline import boundary accepts local CSV, CSV.GZ, and Parquet-style file
paths through explicit import roots.

## Safety checks

- reject path traversal;
- reject symlinks outside the import root;
- reject unsupported file types;
- reject spreadsheet formula-like CSV cells;
- reject unsupported or unknown schemas explicitly.

## Import workflow

1. Choose a local dataset.
2. Detect or confirm the schema.
3. Map source fields to the canonical import model.
4. Normalize identifiers, timestamps, and corporate-action context.
5. Run validation and quarantine invalid records.
6. Preserve raw lineage and checksums.
7. Review the resulting certification state.

Provider import records preserve source checksums and raw records. Missing
provider fields are not fabricated during normalization.

## Synthetic example datasets

- `examples/provider_datasets/synthetic_options.csv`
- `examples/provider_datasets/synthetic_bad_quotes.csv`
- `examples/provider_datasets/synthetic_equity_reference.csv`
- `examples/provider_datasets/synthetic_earnings.csv`
- `examples/provider_datasets/synthetic_dividends.csv`
- `examples/provider_datasets/synthetic_corporate_actions.csv`
- `examples/provider_datasets/synthetic_adjusted_contracts.csv`
- `examples/provider_datasets/synthetic_sparse_quotes.csv`
- `examples/provider_datasets/synthetic_manifest.json`
