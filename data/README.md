# Public evidence data

**Initial evidence snapshot: 2026-09-10.** Source records were independently rechecked locally before publication. Private provenance stays in a separate local ledger.

| File | Fields / unit | Evidence type | Meaning |
|---|---|---|---|
| [production-test-growth.csv](production-test-growth.csv) | date, test_files | Measured from historical Git trees | Tracked TypeScript / TSX unit/browser test files; stable suffix definition. |
| [agentic-verification-growth.csv](agentic-verification-growth.csv) | date, passing_tests | Recorded test results | Passing counts from development records, not total collected tests or always-green runs. |
| [production-sync-benchmark.csv](production-sync-benchmark.csv) | stage, milliseconds | Recorded local benchmark | Unchanged-content startup comparison; raw committed benchmark log unavailable. |
| [video-gate-calibration.csv](video-gate-calibration.csv) | stage, findings, interpretation | Recorded history + measured final artifact | Distinct raw, calibrated and corrected stages. Do not combine as one defect trend. |
| [snapshot.json](snapshot.json) | snapshot_date, definition IDs | Metadata | Latest evolving-series date and stable definitions. |

All numbers in quantitative SVGs come from these files. Derived arithmetic is performed by the renderer. The synthetic fixture's dimensions are original demonstration parameters, not historical measurements.

The test-file series excludes other extensions consistently. No test-case count is plotted on its axis. The passing-test series omits skipped counts for readability, and its August 13 source also reports an environmental failure. It does not establish acceptance rates or output correctness.

Completed video delivery facts in the case-study prose were checked against persisted media and gate metadata: one complete approximately 14.23-minute render; 1080p, 720p and 480p deliveries; 65 → 87 recorded passing checks, with one final skipped check. Private media is not included.

[Methodology](../METHODOLOGY.md) · [Maintenance](../MAINTENANCE.md)
