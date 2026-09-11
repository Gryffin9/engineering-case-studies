"""Fail closed on common disclosures, malformed data, missing links and SVG drift.

This is a release guard, not proof that arbitrary prose is free of confidential
data. Human review of evidence classification remains required before every
public commit. Findings name a category; they never echo the matched value.
"""

import argparse
import csv
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

# Generic categories only. A denylist of private project names would itself be a
# disclosure, so name-specific screening lives outside this public repository.
PATTERNS = {
    "local-machine path": (
        r"/(?:Users|Volumes|home)/[^\s<>\"']+"
        r"|[A-Za-z]:\\(?:Users|Documents)\\"
    ),
    "credential-like value": (
        r"gh[pousr]_[A-Za-z0-9]{20,}"
        r"|github_pat_[A-Za-z0-9_]{20,}"
        r"|sk-[A-Za-z0-9_-]{20,}"
        r"|AKIA[A-Z0-9]{16}"
        r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "email address": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "private endpoint / query": (
        r"/api/[A-Za-z][\w/-]+"
        r"|\bSELECT\s+.+?\s+FROM\s+\w+"
        r"|postgres(?:ql)?://[^\s]+"
    ),
}

IGNORED_PARTS = {".git", "__pycache__", ".venv"}
DATA_SCHEMAS = {
    "production-test-growth.csv": ["date", "test_files"],
    "agentic-verification-growth.csv": ["date", "passing_tests"],
    "video-gate-calibration.csv": ["stage", "findings", "interpretation"],
    "production-sync-benchmark.csv": ["stage", "milliseconds"],
}
DEFINITIONS = {
    "production_definition": "ts-tsx-test-spec-files-v1",
    "agentic_definition": "recorded-passing-tests-v1",
}


def scan_text(text, allowed_emails=()):
    """Return the category labels that match, without the matched values."""
    findings = []
    for label, pattern in PATTERNS.items():
        matches = list(re.finditer(pattern, text, re.I))
        if label == "email address":
            matches = [m for m in matches if m.group() not in allowed_emails]
        if matches:
            findings.append(label)
    return findings


def is_local_config(path):
    return path.name == "portfolio.local.toml" or path.name.endswith(".local.json")


def public_files(root):
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in rel.parts):
            continue
        if is_local_config(path) or path.name == ".DS_Store":
            continue
        if path.is_file() or path.is_symlink():
            yield path


def display_name(path, root):
    """A path is echoed only if the path itself carries no finding."""
    rel = path.relative_to(root).as_posix()
    return rel if not scan_text(rel) else "<redacted filename>"


def scan_tree(root, allowed_emails=()):
    issues = []
    for path in public_files(root):
        rel = path.relative_to(root).as_posix()
        name = display_name(path, root)
        for label in scan_text(rel):
            issues.append(f"{name}: filename contains {label}")
        if path.is_symlink():
            issues.append(f"{name}: symbolic links are not release artifacts")
            continue
        try:
            body = path.read_text()
        except UnicodeError:
            issues.append(f"{name}: binary requires separate manual review")
            continue
        for label in scan_text(body, allowed_emails):
            issues.append(f"{name}: {label}")
    # An ignored configuration must never be tracked accidentally.
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True
    )
    for rel in tracked.stdout.split("\0"):
        if rel and is_local_config(Path(rel)):
            issues.append("Local configuration is tracked; remove it from the public index.")
    return issues


def validate_data(root):
    issues = []
    latest = []
    for name, columns in DATA_SCHEMAS.items():
        try:
            with (root / "data" / name).open(newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != columns:
                    raise ValueError("schema")
                data = list(reader)
            if not data:
                raise ValueError("empty")
            previous = None
            for row in data:
                if set(row) != set(columns) or any(v is None for v in row.values()):
                    raise ValueError("row")
                if not re.fullmatch(r"0|[1-9][0-9]*", row[columns[1]]):
                    raise ValueError("integer")
                if columns[0] == "date":
                    day = date.fromisoformat(row["date"])
                    if str(day) != row["date"] or (previous and day <= previous):
                        raise ValueError("date order")
                    previous = day
            if previous:
                latest.append(str(previous))
            stages = [row[columns[0]] for row in data]
            if name == "video-gate-calibration.csv" and stages != ["initial", "calibrated", "corrected"]:
                raise ValueError("stage order")
            if name == "production-sync-benchmark.csv":
                if stages != ["before", "after"] or any(int(r["milliseconds"]) <= 0 for r in data):
                    raise ValueError("benchmark")
        except (OSError, ValueError, KeyError, TypeError):
            issues.append(f"data/{name}: invalid data schema, value or order")
    try:
        meta = json.loads((root / "data/snapshot.json").read_text())
        if set(meta) != {"snapshot_date", *DEFINITIONS}:
            raise ValueError("keys")
        if any(meta[key] != value for key, value in DEFINITIONS.items()):
            raise ValueError("definition")
        if meta["snapshot_date"] != max(latest):
            raise ValueError("snapshot date")
    except (OSError, ValueError, KeyError, TypeError):
        issues.append("data/snapshot.json: invalid definition or snapshot date")
    return issues


INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_LINK = re.compile(r"(?:src|srcset|href)=\"([^\"]+)\"")
REFERENCE_DEFINITION = re.compile(r"^[ ]{0,3}\[([^\]]+)\]:[ \t]*(\S+)(?:[ \t]+\"[^\"]*\")?[ \t]*$", re.M)


def heading_anchors(text):
    """Approximate GitHub's heading slugs, including numbered duplicates."""
    anchors = set()
    seen = {}
    for heading in re.findall(r"^#+\s+(.+?)\s*#*$", text, re.M):
        base = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = seen.get(base, 0)
        seen[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def markdown_targets(text):
    targets = INLINE_LINK.findall(text) + HTML_LINK.findall(text)
    # Reference definitions are checked whether or not a usage resolves to
    # them; an undefined reference is only a literal bracket to GitHub.
    targets += [target for _label, target in REFERENCE_DEFINITION.findall(text)]
    return targets


def validate_links(root):
    issues = []
    for path in root.rglob("*.md"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        name = display_name(path, root)
        body = path.read_text()
        for link in markdown_targets(body):
            target = link.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            dest = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path.resolve()
            inside = dest.is_relative_to(root.resolve())
            if not inside or not dest.is_file():
                issues.append(f"{name}: missing or escaping internal reference")
            elif parsed.fragment and dest.suffix == ".md":
                if unquote(parsed.fragment) not in heading_anchors(dest.read_text()):
                    issues.append(f"{name}: missing heading anchor")
    return issues


def validate_svgs(root):
    issues = []
    for path in (root / "assets").rglob("*.svg"):
        body = path.read_text()
        try:
            tree = ET.fromstring(body)
            if tree.find("{http://www.w3.org/2000/svg}title") is None:
                raise ValueError("title")
            if re.search(r"<script|<foreignObject|(?:href|src)=\"(?:https?:|data:)", body, re.I):
                raise ValueError("external reference")
        except (ET.ParseError, ValueError):
            issues.append(f"{path.relative_to(root)}: unsafe or malformed SVG")
    return issues


def validate(root=ROOT, generated=True):
    issues = scan_tree(root) + validate_data(root) + validate_links(root) + validate_svgs(root)
    if generated:
        from render_charts import generate

        try:
            for rel, content in generate(root).items():
                target = root / rel
                if not target.is_file() or target.read_text() != content:
                    issues.append(f"{rel}: generated asset differs from data")
        except (OSError, ValueError, KeyError, ZeroDivisionError):
            issues.append("Unable to regenerate assets from approved data")
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--scan-only", action="store_true", help="confidentiality scan only")
    parser.add_argument("--allow-email", action="append", default=[], metavar="ADDRESS")
    args = parser.parse_args()

    if args.scan_only:
        issues = scan_tree(args.root, args.allow_email)
    else:
        issues = validate(args.root)
    if issues:
        print("\n".join(issues))
        raise SystemExit(1)
    if args.scan_only:
        print("Confidentiality scan passed; manual evidence review still required.")
    else:
        print("Public release checks passed.")


if __name__ == "__main__":
    main()
