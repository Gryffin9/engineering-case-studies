# Maintenance

Review every **8–12 weeks**, or after an important measurable milestone. Do not refresh simply because the calendar changed; add only evidence that improves the portfolio.

## Reproduce without private sources

From the repository root, with Python 3.11 or newer:

```bash
python3 scripts/refresh_portfolio.py --dry-run
python3 scripts/refresh_portfolio.py --apply
```

With no local configuration, these commands regenerate charts from committed public data. Dry-run assembles a temporary candidate, validates it and prints the exact diff without changing public artifacts. `--apply` deliberately writes the validated candidate. Neither command commits or pushes.

## Add a reviewed snapshot

Copy `portfolio.local.example.toml` to ignored `portfolio.local.toml`. Set private checkout paths locally; never commit them. Set an actual evidence date and configure only the source you intend to refresh.

The production reader examines a configured default-branch ref using read-only Git commands. It follows actual first-parent commit headers, including locally available ancestors hidden by shallow grafts; missing history fails instead of inventing a value. Refresh your source ref locally first if you need newer history. It counts only tracked `.test.ts`, `.test.tsx`, `.spec.ts` and `.spec.tsx` files. Date boundaries use Asia/Kolkata, matching the initial series.

The agentic reader accepts a local, reviewed numeric summary inside the configured private repository. Create it from a persisted run record only after confirming equivalent test-discovery scope:

```json
{
  "date": "2026-12-01",
  "passing_tests": 0,
  "definition": "recorded-passing-tests-v1"
}
```

The zero above is a schema example, not a result. Replace it with the evidenced count and actual date. Set `scope_reviewed = true` only after reviewing scope and failures/skips. The tool intentionally does not execute tests, parse arbitrary private logs or infer scope. Private source references belong in your separate local evidence ledger, not this summary or public data.

Snapshots append strictly later dates. Historical corrections require a separate explicit edit and review. Values may decrease; the tool does not enforce an artificial growth story. Completed benchmark/calibration results do not change during routine refreshes.

## Release checklist

1. Run extraction with `--dry-run` and inspect the exact candidate diff.
2. Review candidate metrics against persisted source evidence and confidentiality rules.
3. Confirm the measurement definition and discovery scope are unchanged.
4. Append only a valid new snapshot with deliberate `--apply`.
5. Inspect the regenerated light and dark SVGs and the updated snapshot metadata.
6. Run tests, chart comparison and confidentiality validation:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/render_charts.py --check
python3 scripts/validate_public_release.py
```

7. Inspect `git diff`, including dates and every changed number.
8. Review narrative and profile cards. Old dated snapshots remain true; update prose/profile snapshot text deliberately if promoting the new milestone. The case-study assets update automatically, while the profile preserves its copied, dated assets until reviewed.
9. Scan before committing, open a focused pull request, and publish only after CI passes.
10. Verify the live profile and case-study pages. Keep private repositories private.

No scheduler or public workflow needs private-access credentials. For rollback, revert a release commit with a new commit; never rewrite history or force-push.
