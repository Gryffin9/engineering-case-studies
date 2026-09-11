# Methodology

This portfolio uses dated evidence snapshots, not live telemetry. Quantitative claims must have persisted support, stable definitions, a safe confidentiality classification and wording that identifies the kind of evidence.

| Label | Meaning here |
|---|---|
| Measured | Directly observed from a persisted artifact, source tree or recorded run. |
| Derived | Arithmetic calculated from recorded values, with units preserved. |
| Recorded benchmark | A measurement in a particular local run/environment; not necessarily production telemetry. |
| Recorded test result | A passing-test count in development records; not a rerun of private tests by public CI. |
| Architecture / design | A structural property or generalized workflow, not a performance outcome. |
| Estimated | A projection or model; excluded from headline results. |

## Measurement contracts

Production test counts are tracked TypeScript / TSX `.test` and `.spec` files at the end of each snapshot date in Asia/Kolkata on the default branch's first-parent history. Count each file once; consistently exclude other extensions. A count does not certify execution, assertion count or coverage.

Agentic counts are passing tests recorded in development evidence. Failed and skipped tests are not silently converted to passing tests. The chart plots passing counts only; the August 13 record also reports an environmental failure. Discovery scope must be reviewed before appending future snapshots.

The startup comparison is a commit-recorded local unchanged-content benchmark. Speedup is `5317 / 155`, rounded to one decimal place. Reduction is `(1 - 155 / 5317) × 100`, also rounded to one decimal place. The raw committed benchmark log is unavailable. No production latency claim follows.

Video calibration separates raw detector findings from calibrated genuine defects and then final blockers. These categories are not interchangeable; they are shown as stages, not a continuous quantitative trend. Delivery evidence is limited to one persisted render and its validated tiers; machine readiness and human ratification remain separate.

## Reproducibility and provenance

Public CSV files contain only approved aggregates. A private local evidence ledger identifies source trees, commit records and persisted artifacts. It is intentionally excluded from this repository. Source values were rechecked before the September 2026 release.

Anyone can reproduce the SVGs, arithmetic and synthetic geometry tests. Public CI validates the portfolio itself; it does not independently verify or run the private systems. The committed aggregates are an author-curated disclosure, not independently inspectable raw experimental data.

Charts use labeled observations on a date-scaled axis. No smooth trend, interpolation or missing run is manufactured. Snapshot dates remain attached to historical claims even when newer observations are added.

[Data dictionary](data/README.md) · [Confidentiality](CONFIDENTIALITY.md) · [Maintenance](MAINTENANCE.md)
