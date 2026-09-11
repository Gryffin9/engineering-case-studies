"""Assemble, validate and diff a refreshed portfolio candidate.

    python3 scripts/refresh_portfolio.py --dry-run   # show the exact diff
    python3 scripts/refresh_portfolio.py --apply     # write validated artifacts

Without an ignored ``portfolio.local.toml`` the candidate is simply the
committed public data re-rendered. With one, allowlisted engineering metrics
are read from locally configured private checkouts and appended as new dated
snapshots. Nothing here commits, pushes or prints private paths.
"""

import argparse
import csv
import difflib
import io
import json
import re
import shutil
import subprocess
import tempfile
import tomllib
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from render_charts import generate
from validate_public_release import DEFINITIONS, public_files, validate

ROOT = Path(__file__).resolve().parents[1]
KOLKATA = timezone(timedelta(hours=5, minutes=30))
TEST_FILE = re.compile(r"\.(?:test|spec)\.tsx?$")
PRODUCTION_DEFINITION = DEFINITIONS["production_definition"]
AGENTIC_DEFINITION = DEFINITIONS["agentic_definition"]


def git(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode:
        raise ValueError("Cannot read configured Git evidence; check the local source and ref.")
    return proc.stdout


def production_count(repo, ref, day):
    """Count test files at the end of ``day`` on the first-parent history of ``ref``.

    Parent headers are read directly so that shallow grafts never turn missing
    history into a false zero: absent ancestry raises instead.
    """
    sha = git(repo, "rev-parse", "--verify", ref + "^{commit}").strip()
    cutoff = datetime.combine(date.fromisoformat(day), time.max, KOLKATA).timestamp()
    seen = set()
    while sha not in seen:
        seen.add(sha)
        headers = git(repo, "cat-file", "-p", sha).split("\n\n", 1)[0].splitlines()
        committer = next(line for line in headers if line.startswith("committer "))
        timestamp = int(committer.rsplit(" ", 2)[1])
        if timestamp <= cutoff:
            # -z keeps unusual filenames (unicode, embedded newlines) intact.
            names = git(repo, "ls-tree", "-r", "-z", "--name-only", sha).split("\0")
            return sum(1 for name in names if TEST_FILE.search(name))
        parents = [line.split()[1] for line in headers if line.startswith("parent ")]
        if not parents:
            raise ValueError("No source snapshot exists on the requested date.")
        sha = parents[0]
    raise ValueError("Invalid source ancestry.")


def append_snapshot(path, day, field, value):
    data = list(csv.DictReader(path.read_text().splitlines()))
    if date.fromisoformat(day) <= date.fromisoformat(data[-1]["date"]):
        raise ValueError(
            "Refresh only appends later snapshots; historical corrections require explicit manual review."
        )
    data.append({"date": day, field: str(value)})
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["date", field], lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    path.write_text(stream.getvalue())


def extract_production(item, day, stage):
    if set(item) != {"repo", "ref", "definition"} or item["definition"] != PRODUCTION_DEFINITION:
        raise ValueError("Production measurement definition must remain unchanged.")
    if not isinstance(item["ref"], str) or item["ref"].startswith("-"):
        raise ValueError("Invalid source ref.")
    count = production_count(Path(item["repo"]).expanduser(), item["ref"], day)
    append_snapshot(stage / "data/production-test-growth.csv", day, "test_files", count)


def extract_agentic(item, day, stage):
    expected = {"repo", "summary", "definition", "scope_reviewed"}
    if set(item) != expected or item["definition"] != AGENTIC_DEFINITION or item["scope_reviewed"] is not True:
        raise ValueError("Agentic suite scope needs explicit local review.")
    repo = Path(item["repo"]).expanduser().resolve()
    summary = (repo / item["summary"]).resolve()
    if not summary.is_relative_to(repo) or not summary.is_file():
        raise ValueError("Summary must exist inside the configured source repository.")
    # Only the allowlisted numeric field is read; logs, prompts and test names never are.
    data = json.loads(summary.read_text())
    if (
        set(data) != {"date", "passing_tests", "definition"}
        or data["date"] != day
        or data["definition"] != item["definition"]
        or type(data["passing_tests"]) is not int
        or data["passing_tests"] < 0
    ):
        raise ValueError("Summary does not match the reviewed metric contract.")
    append_snapshot(stage / "data/agentic-verification-growth.csv", day, "passing_tests", data["passing_tests"])


def extract(config, stage):
    if set(config) - {"snapshot_date", "production", "agentic"}:
        raise ValueError("Unknown local configuration key.")
    day = config.get("snapshot_date")
    if not day:
        raise ValueError("Configured extraction requires an explicit evidence snapshot_date.")
    if str(date.fromisoformat(day)) != day or date.fromisoformat(day) > date.today():
        raise ValueError("Invalid evidence date.")
    if "production" in config:
        extract_production(config["production"], day, stage)
    if "agentic" in config:
        extract_agentic(config["agentic"], day, stage)

    meta_path = stage / "data/snapshot.json"
    meta = json.loads(meta_path.read_text())
    latest = []
    for name in ("production-test-growth.csv", "agentic-verification-growth.csv"):
        rows = list(csv.DictReader((stage / "data" / name).read_text().splitlines()))
        latest.append(rows[-1]["date"])
    meta["snapshot_date"] = max(latest)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")


def build_candidate(root=ROOT, config=None):
    """Return {relative path: content} for a fully validated candidate tree."""
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for path in public_files(root):
            if path.is_symlink():
                raise ValueError("Symbolic links are not permitted in a release candidate.")
            dest = stage / path.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
        if config:
            extract(config, stage)
        for rel, content in generate(stage).items():
            (stage / rel).write_text(content)
        issues = validate(stage)
        if issues:
            raise ValueError("Candidate failed public release checks: " + "; ".join(issues))
        return {p.relative_to(stage).as_posix(): p.read_text() for p in public_files(stage)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="validate and print the diff only")
    mode.add_argument("--apply", action="store_true", help="write the validated candidate")
    parser.add_argument("--config", type=Path, help="explicit local configuration (default: portfolio.local.toml)")
    args = parser.parse_args()
    local = args.config or ROOT / "portfolio.local.toml"

    try:
        if args.config and not local.is_file():
            raise ValueError("Explicit local configuration is unavailable.")
        config = tomllib.loads(local.read_text()) if local.is_file() else None
        candidate = build_candidate(ROOT, config)

        changed = []
        for rel, content in candidate.items():
            old = (ROOT / rel).read_text() if (ROOT / rel).exists() else ""
            if old == content:
                continue
            changed.append((rel, content))
            diff = difflib.unified_diff(
                old.splitlines(True), content.splitlines(True), fromfile="a/" + rel, tofile="b/" + rel
            )
            print("".join(diff), end="")

        if args.apply:
            for rel, content in changed:
                dest = ROOT / rel
                with tempfile.NamedTemporaryFile("w", dir=dest.parent, delete=False) as handle:
                    handle.write(content)
                    tmp = Path(handle.name)
                tmp.replace(dest)
            print(f"Applied {len(changed)} validated artifact changes. Review git diff before publishing.")
        else:
            print(f"Dry run: {len(changed)} candidate changes. No public artifacts written. Use --apply deliberately.")
    except (ValueError, OSError, KeyError, TypeError):
        # Never echo private paths, log excerpts, commands or configuration values.
        parser.exit(1, "Refresh failed safely. Check local source availability, metric definition, schema and snapshot ordering.\n")


if __name__ == "__main__":
    main()
