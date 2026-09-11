import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_public_release import PATTERNS, public_files, scan_text, scan_tree, validate, validate_links, validate_data
from refresh_portfolio import build_candidate, production_count
from render_charts import generate
from synthetic_scene import findings, scenes

ROOT = Path(__file__).resolve().parents[1]


def git_fixture(repo, *args, stamp=None):
    env = dict(os.environ)
    env.update(GIT_AUTHOR_NAME='Fixture', GIT_COMMITTER_NAME='Fixture',
               GIT_AUTHOR_EMAIL='fixture' + '@' + 'example.invalid',
               GIT_COMMITTER_EMAIL='fixture' + '@' + 'example.invalid')
    if stamp:
        env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True, text=True, env=env).stdout.strip()


def commit_fixture(repo, stamp):
    git_fixture(repo, 'add', '.')
    git_fixture(repo, 'commit', '-qm', 'Synthetic fixture', stamp=stamp)


def copy_release(root):
    for p in public_files(ROOT):
        dest = root / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)


def public_snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in public_files(root)}


def old_release(root):
    copy_release(root)
    (root / 'data/production-test-growth.csv').write_text('date,test_files\n2000-01-01,1\n')
    (root / 'data/agentic-verification-growth.csv').write_text('date,passing_tests\n2000-01-01,1\n')
    meta = json.loads((root / 'data/snapshot.json').read_text())
    meta['snapshot_date'] = '2000-01-01'
    (root / 'data/snapshot.json').write_text(json.dumps(meta) + '\n')
    for rel, content in generate(root).items():
        (root / rel).write_text(content)


class ReleaseTests(unittest.TestCase):
    def test_private_path_is_rejected(self):
        self.assertTrue(scan_text('/' + 'Users' + '/someone/work'))
        self.assertTrue(scan_text('/' + 'Volumes' + '/disk/work'))

    def test_secret_and_email_are_rejected_without_echo(self):
        for value in ['gh' + 'p_' + 'a' * 36, 'someone' + '@' + 'example.org', '-----BEGIN ' + 'PRIVATE KEY-----']:
            result = scan_text(value)
            self.assertTrue(result)
            self.assertNotIn(value, str(result))

    def test_safe_generic_prose(self):
        self.assertEqual(scan_text('Recorded local benchmark; snapshot: 2026-09-10.'), [])

    def test_public_scanner_has_only_generic_categories(self):
        self.assertEqual(set(PATTERNS), {'local-machine path', 'credential-like value',
                                      'email address', 'private endpoint / query'})

    def test_sensitive_filename_is_rejected_without_echo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            filename = 'someone' + '@' + 'example.org.md'
            (root / filename).write_text('[lost](missing.md)')
            issues = scan_tree(root)
            self.assertTrue(issues)
            self.assertNotIn(filename, str(issues))
            self.assertNotIn(filename, str(validate_links(root)))

    def test_tracked_local_configuration_is_rejected_without_echo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            git_fixture(root, 'init', '-q')
            (root / 'portfolio.local.toml').write_text('local_only = true\n')
            git_fixture(root, 'add', 'portfolio.local.toml')
            self.assertIn('Local configuration is tracked', str(scan_tree(root)))

    def test_broken_internal_link(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'README.md').write_text('[lost](missing.md)')
            self.assertTrue(validate_links(root))

    def test_reference_style_links_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for body in ('[lost][ref]\n\n[ref]: missing.md\n',
                         '[lost][]\n\n[lost]: missing.md\n',
                         '[lost]\n\n[lost]: missing.md\n'):
                with self.subTest(body=body):
                    (root / 'README.md').write_text(body)
                    self.assertTrue(validate_links(root))

    def test_formatted_and_duplicate_heading_anchors(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'README.md').write_text(
                '# **Evidence** and `checks`\n\n# Repeat\n\n# Repeat\n\n'
                '[first](#evidence-and-checks)\n[duplicate][ref]\n\n'
                '[ref]: #repeat-1 "Repeated heading"\n')
            self.assertEqual(validate_links(root), [])
            with (root / 'README.md').open('a') as f:
                f.write('\n[missing](#repeat-2)\n')
            self.assertTrue(validate_links(root))

    def test_fixture_detects_real_geometry_failures(self):
        broken, fixed = scenes()
        kinds = {f['kind'] for f in findings(broken)}
        self.assertTrue({'off-canvas', 'overlap', 'safe-zone', 'caption-collision'} <= kinds)
        self.assertEqual(findings(fixed), [])

    def test_committed_data_schema(self):
        self.assertEqual(validate_data(Path(__file__).resolve().parents[1]), [])

    def test_invalid_schema_values_and_order_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old_release(root)
            for body in ('date,wrong\n2000-01-01,1\n',
                         'date,test_files\n2000-01-01,-1\n',
                         'date,test_files\n2000-01-01,1,extra\n',
                         'date,test_files\n2000-01-01,1\n2000-01-01,2\n'):
                with self.subTest(body=body):
                    (root / 'data/production-test-growth.csv').write_text(body)
                    self.assertTrue(validate_data(root))

    def test_stale_generated_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old_release(root)
            with (root / 'assets/dark/hero.svg').open('a') as f:
                f.write('\n')
            self.assertIn('generated asset differs from data', str(validate(root)))

    def test_unicode_and_newline_test_filenames_are_counted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            git_fixture(root, 'init', '-q', '-b', 'main')
            for name in ('normal.test.ts', 'unicode-λ.test.ts', 'line\nbreak.spec.tsx',
                         'ignored.test.js', 'helper.ts'):
                (root / name).write_text('')
            commit_fixture(root, '2000-01-01T23:59:59+0530')
            self.assertEqual(production_count(root, 'main', '2000-01-01'), 3)

    def test_first_parent_and_kolkata_day_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            git_fixture(root, 'init', '-q', '-b', 'main')
            (root / 'a.test.ts').write_text('')
            commit_fixture(root, '2000-01-01T23:59:59+0530')
            git_fixture(root, 'checkout', '-qb', 'feature')
            (root / 'feature.spec.tsx').write_text('')
            commit_fixture(root, '2000-01-02T12:00:00+0530')
            git_fixture(root, 'checkout', '-q', 'main')
            (root / 'b.test.ts').write_text('')
            commit_fixture(root, '2000-01-02T00:00:00+0530')
            git_fixture(root, 'merge', '--no-ff', '-qm', 'Synthetic merge', 'feature',
                        stamp='2000-01-03T12:00:00+0530')
            self.assertEqual(production_count(root, 'main', '2000-01-01'), 1)
            self.assertEqual(production_count(root, 'main', '2000-01-02'), 2)
            self.assertEqual(production_count(root, 'main', '2000-01-03'), 3)
            with self.assertRaises(ValueError):
                production_count(root, 'main', '1999-12-31')

    def test_refresh_cli_dry_run_and_apply(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root, source = base / 'public', base / 'source'
            root.mkdir(); source.mkdir()
            old_release(root)
            git_fixture(root, 'init', '-q')
            git_fixture(source, 'init', '-q', '-b', 'main')
            (source / 'fixture.spec.tsx').write_text('')
            (source / 'unicode-λ.test.ts').write_text('')
            commit_fixture(source, '2000-01-02T12:00:00+0530')
            summary = source / 'portfolio-summary.local.json'
            summary.write_text(json.dumps({'date': '2000-01-02', 'passing_tests': 7,
                                           'definition': 'recorded-passing-tests-v1'}))
            (root / 'portfolio.local.toml').write_text(
                'snapshot_date = "2000-01-02"\n[production]\nrepo = ' + json.dumps(str(source)) +
                '\nref = "main"\ndefinition = "ts-tsx-test-spec-files-v1"\n[agentic]\nrepo = ' +
                json.dumps(str(source)) + '\nsummary = "portfolio-summary.local.json"\n'
                'definition = "recorded-passing-tests-v1"\nscope_reviewed = true\n')
            before = public_snapshot(root)
            command = [sys.executable, str(root / 'scripts/refresh_portfolio.py')]
            dry = subprocess.run(command + ['--dry-run'], capture_output=True, text=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertEqual(public_snapshot(root), before)
            self.assertNotIn(str(source), dry.stdout + dry.stderr)
            applied = subprocess.run(command + ['--apply'], capture_output=True, text=True)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertNotIn(str(source), applied.stdout + applied.stderr)
            self.assertNotEqual(public_snapshot(root), before)
            with (root / 'data/production-test-growth.csv').open() as f:
                self.assertEqual(list(csv.DictReader(f))[-1], {'date': '2000-01-02', 'test_files': '2'})
            with (root / 'data/agentic-verification-growth.csv').open() as f:
                self.assertEqual(list(csv.DictReader(f))[-1], {'date': '2000-01-02', 'passing_tests': '7'})
            self.assertEqual(validate(root), [])
            unchanged = public_snapshot(root)
            retry = subprocess.run(command + ['--apply'], capture_output=True, text=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertEqual(public_snapshot(root), unchanged)
            self.assertNotIn(str(source), retry.stdout + retry.stderr)

    def test_refresh_without_private_configuration(self):
        root = Path(__file__).resolve().parents[1]
        before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
        candidate = build_candidate(root, None)
        self.assertTrue('assets/dark/hero.svg' in candidate)
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == '__main__':
    unittest.main()
