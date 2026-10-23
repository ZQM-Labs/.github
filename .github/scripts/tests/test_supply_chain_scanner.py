"""Offline regression tests for the vendored supply-chain scanner parsers."""
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import zqm_supply_chain_scanner as scanner


class RequirementParserTests(unittest.TestCase):
    def test_exact_python_pin_is_parsed(self):
        deps = scanner.parse_python_requirements("requests==2.32.3\n")
        self.assertEqual(deps, [{"name": "requests", "version": "2.32.3", "ecosystem": "PyPI"}])

    def test_version_range_is_not_misreported_as_installed_version(self):
        deps = scanner.parse_python_requirements("requests>=2.31,<3\n")
        self.assertEqual(deps[0]["version"], "unknown")

    def test_nested_requirement_include_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported pip option or nested requirement"):
            scanner.parse_python_requirements("# comment\n-r base.txt\nrequests==2.32.3\n")

    def test_vcs_requirement_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported VCS/URL requirement"):
            scanner.parse_python_requirements("git+https://example.invalid/team/package.git")

    def test_named_direct_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported direct-reference requirement"):
            scanner.parse_python_requirements("my-package @ https://example.invalid/pkg.whl")

    def test_go_mod_require_block_is_parsed(self):
        manifest = """
module example.com/app

go 1.22

require (
    github.com/pkg/errors v0.9.1 // indirect
    golang.org/x/text v0.16.0
)

replace example.com/old => ../old
"""
        deps = scanner.parse_go_mod(manifest)
        self.assertEqual(
            deps,
            [
                {"name": "github.com/pkg/errors", "version": "0.9.1", "ecosystem": "Go"},
                {"name": "golang.org/x/text", "version": "0.16.0", "ecosystem": "Go"},
            ],
        )

    def test_go_mod_single_require_does_not_parse_later_directives(self):
        deps = scanner.parse_go_mod("module example.com/app\nrequire example.com/lib v1.2.3\ngo 1.22\n")
        self.assertEqual(
            deps,
            [{"name": "example.com/lib", "version": "1.2.3", "ecosystem": "Go"}],
        )

    def test_malformed_go_mod_require_block_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unterminated go.mod require block"):
            scanner.parse_go_mod("require (\nexample.com/lib v1.2.3\n")

    def test_poetry_lock_reads_resolved_package_versions(self):
        lock = """
[[package]]
name = "requests"
version = "2.32.3"
description = "HTTP library"
optional = false
python-versions = ">=3.8"

[[package]]
name = "urllib3"
version = "2.2.2"
description = "HTTP client"
optional = false
python-versions = ">=3.8"
"""
        deps = scanner.parse_poetry_lock(lock)
        self.assertEqual(
            deps,
            [
                {"name": "requests", "version": "2.32.3", "ecosystem": "PyPI"},
                {"name": "urllib3", "version": "2.2.2", "ecosystem": "PyPI"},
            ],
        )

    def test_malformed_poetry_lock_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid poetry.lock"):
            scanner.parse_poetry_lock("[[package]")

    def test_empty_poetry_lock_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "missing its package array"):
            scanner.parse_poetry_lock('[metadata]\nlock-version = "2.0"\n')

    def test_pipfile_lock_reads_resolved_versions(self):
        lock = {
            "default": {"requests": {"version": "==2.32.3"}},
            "develop": {"pytest": {"version": "==8.3.2"}, "requests": {"version": "==2.32.3"}},
        }
        deps = scanner.parse_pipfile_lock(json.dumps(lock))
        self.assertEqual(
            deps,
            [
                {"name": "requests", "version": "2.32.3", "ecosystem": "PyPI"},
                {"name": "pytest", "version": "8.3.2", "ecosystem": "PyPI"},
            ],
        )

    def test_pipfile_lock_unknown_version_is_not_invented(self):
        lock = {"default": {"private-package": {"git": "https://example.invalid/repo.git"}}}
        deps = scanner.parse_pipfile_lock(json.dumps(lock))
        self.assertEqual(deps[0]["version"], "unknown")

    def test_malformed_pipfile_lock_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid Pipfile.lock"):
            scanner.parse_pipfile_lock("{broken")

    def test_empty_pipfile_lock_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "must contain a default or develop"):
            scanner.parse_pipfile_lock("{}")

    def test_npm_range_is_not_treated_as_resolved_version(self):
        deps = scanner.parse_package_json(json.dumps({"dependencies": {"react": "^18.2.0"}}))
        self.assertEqual(deps[0]["version"], "unknown")

    def test_npm_exact_version_is_parsed(self):
        deps = scanner.parse_package_json(json.dumps({"dependencies": {"react": "18.2.0"}}))
        self.assertEqual(deps[0]["version"], "18.2.0")

    def test_malformed_package_json_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid package.json"):
            scanner.parse_package_json("{broken")

    def test_package_json_dependency_section_must_be_object(self):
        with self.assertRaisesRegex(ValueError, "dependencies must be an object"):
            scanner.parse_package_json(json.dumps({"dependencies": ["requests"]}))

    def test_npm_lockfile_reads_resolved_version(self):
        lock = {"packages": {"": {}, "node_modules/react": {"version": "18.3.1"}}}
        deps = scanner.parse_package_lock(json.dumps(lock))
        self.assertEqual(deps, [{"name": "react", "version": "18.3.1", "ecosystem": "npm"}])

    def test_malformed_package_lock_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid package-lock.json"):
            scanner.parse_package_lock("{broken")

    def test_empty_package_lock_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "must contain packages or dependencies"):
            scanner.parse_package_lock("{}")

    def test_pyproject_pep621_dependency_arrays(self):
        manifest = '''
[project]
name = "fixture"
version = "1.0.0"
dependencies = [
    "requests>=2.31,<3",
    "pydantic==2.8.2",
]

[project.optional-dependencies]
dev = ["pytest>=8", "requests>=2.31,<3"]
'''
        deps = scanner.parse_pyproject_toml(manifest)
        self.assertEqual(
            deps,
            [
                {"name": "requests", "version": "unknown", "ecosystem": "PyPI"},
                {"name": "pydantic", "version": "unknown", "ecosystem": "PyPI"},
                {"name": "pytest", "version": "unknown", "ecosystem": "PyPI"},
            ],
        )

    def test_poetry_dependency_and_dev_groups_are_inventoried(self):
        manifest = """
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31"
private-package = { git = "https://example.invalid/private.git", branch = "main" }

[tool.poetry.dev-dependencies]
mypy = "^1.10"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
requests = "^2.31"
"""
        deps = scanner.parse_pyproject_toml(manifest)
        self.assertEqual(
            deps,
            [
                {"name": "requests", "version": "unknown", "ecosystem": "PyPI"},
                {"name": "private-package", "version": "unknown", "ecosystem": "PyPI"},
                {"name": "mypy", "version": "unknown", "ecosystem": "PyPI"},
                {"name": "pytest", "version": "unknown", "ecosystem": "PyPI"},
            ],
        )

    def test_pyproject_dependency_extras_and_markers(self):
        deps = scanner.parse_pyproject_toml("""
[project]
dependencies = ['uvicorn[standard]>=0.30; python_version >= "3.10"']
""")
        self.assertEqual(deps[0]["name"], "uvicorn")
        self.assertEqual(deps[0]["version"], "unknown")

    def test_malformed_pyproject_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "invalid pyproject.toml"):
            scanner.parse_pyproject_toml("[project\ndependencies = [")

    def test_pyproject_duplicate_declaration_is_deduplicated(self):
        deps = scanner.parse_pyproject_toml('''
[project]
dependencies = ["requests>=2.31"]

[project.optional-dependencies]
test = ["requests>=2.31"]
''')
        self.assertEqual(len(deps), 1)

    def test_yarn_lock_without_supported_npm_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps({"dependencies": {"react": "^18.2.0"}}))
            with open(os.path.join(root, "yarn.lock"), "w", encoding="utf-8") as f:
                f.write('react@^18.2.0:\n  version "18.3.1"\n')
            with (
                patch.object(scanner, "query_osv", return_value=[]),
                patch.object(scanner, "check_license_npm", return_value="MIT"),
                patch.object(scanner, "check_outdated_npm", return_value=None),
                patch.object(scanner, "scan_pip_audit", return_value=[]),
                patch.object(scanner, "scan_safety", return_value=[]),
            ):
                findings, _ = scanner.scan_repo(root, "example/app")
        self.assertTrue(any(f["id"] == "YARN_LOCK_UNSUPPORTED" for f in findings))

    def test_go_transitive_coverage_gap_is_reported_without_go_sum(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "go.mod"), "w", encoding="utf-8") as f:
                f.write("module example.com/app\nrequire example.com/lib v1.2.3\n")
            with (
                patch.object(scanner, "query_osv", return_value=[]),
                patch.object(scanner, "check_license_go", return_value="MIT"),
                patch.object(scanner, "check_outdated_go", return_value=None),
                patch.object(scanner, "scan_pip_audit", return_value=[]),
                patch.object(scanner, "scan_safety", return_value=[]),
            ):
                findings, _ = scanner.scan_repo(root, "example/app")
        self.assertTrue(any(f["id"] == "GO_TRANSITIVE_COVERAGE_INCOMPLETE" for f in findings))

    def test_missing_go_license_metadata_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "go.mod"), "w", encoding="utf-8") as f:
                f.write("module example.com/app\nrequire example.com/lib v1.2.3\n")
            with (
                patch.object(scanner, "query_osv", return_value=[]),
                patch.object(scanner, "check_license_go", return_value=None),
                patch.object(scanner, "check_outdated_go", return_value=None),
                patch.object(scanner, "scan_pip_audit", return_value=[]),
                patch.object(scanner, "scan_safety", return_value=[]),
            ):
                findings, _ = scanner.scan_repo(root, "example/app")
        self.assertTrue(
            any(f["type"] == "license" and f["id"] == "LICENSE-UNKNOWN" for f in findings)
        )

    def test_invalid_lockfile_becomes_scan_finding_and_does_not_abort_report(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps({"dependencies": {"react": "^18.2.0"}}))
            with open(os.path.join(root, "package-lock.json"), "w", encoding="utf-8") as f:
                f.write("{broken")
            with (
                patch.object(scanner, "query_osv", return_value=[]),
                patch.object(scanner, "check_license_npm", return_value="MIT"),
                patch.object(scanner, "check_outdated_npm", return_value=None),
                patch.object(scanner, "scan_pip_audit", return_value=[]),
                patch.object(scanner, "scan_safety", return_value=[]),
            ):
                findings, sarif = scanner.scan_repo(root, "example/app")
        self.assertTrue(any(f["id"] == "MANIFEST_INVALID" for f in findings))
        self.assertTrue(any(r["ruleId"].endswith("-MANIFEST_INVALID") for r in sarif["runs"][0]["results"]))

    def test_malformed_package_and_go_manifests_do_not_abort_report_generation(self):
        fixtures = [
            ("package.json", "{broken"),
            ("go.mod", "module example.com/app\nrequire (\nexample.com/lib v1.2.3\n"),
        ]
        for filename, body in fixtures:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as root:
                with open(os.path.join(root, filename), "w", encoding="utf-8") as f:
                    f.write(body)
                with (
                    patch.object(scanner, "query_osv", return_value=[]),
                    patch.object(scanner, "check_license_npm", return_value="MIT"),
                    patch.object(scanner, "check_license_go", return_value="MIT"),
                    patch.object(scanner, "check_outdated_npm", return_value=None),
                    patch.object(scanner, "check_outdated_go", return_value=None),
                    patch.object(scanner, "scan_pip_audit", return_value=[]),
                    patch.object(scanner, "scan_safety", return_value=[]),
                ):
                    findings, sarif = scanner.scan_repo(root, "example/app")
                self.assertTrue(any(f["id"] == "MANIFEST_INVALID" for f in findings))
                self.assertTrue(sarif["runs"][0]["results"])

    def test_poetry_lock_versions_override_unresolved_pyproject_declarations(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "pyproject.toml"), "w", encoding="utf-8") as f:
                f.write('[tool.poetry.dependencies]\npython = "^3.11"\nrequests = "^2.31"\n')
            with open(os.path.join(root, "poetry.lock"), "w", encoding="utf-8") as f:
                f.write('[[package]]\nname = "requests"\nversion = "2.32.3"\n')
            deps = scanner.discover_deps(root)
        self.assertEqual(
            deps,
            [{"name": "requests", "version": "2.32.3", "ecosystem": "PyPI"}],
        )

    def test_safety_failure_is_reported_as_incomplete_coverage(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("requests>=2.31\n")
            with patch.object(scanner, "shell_cmd", return_value=None):
                findings = scanner.scan_safety(root)
        self.assertTrue(
            any(f["type"] == "scan_error" and f["id"] == "SAFETY_UNAVAILABLE" for f in findings)
        )

    def test_shell_cmd_unwraps_safety_vulnerabilities_object(self):
        payload = {"report_meta": {}, "vulnerabilities": [{"package_name": "requests"}]}
        completed = subprocess.CompletedProcess(
            args=["safety"], returncode=0, stdout=json.dumps(payload), stderr=""
        )
        with patch.object(scanner.subprocess, "run", return_value=completed):
            data = scanner.shell_cmd(["safety", "check", "--json"], ".", list_key="vulnerabilities")
        self.assertEqual(data, [{"package_name": "requests"}])

    def test_scan_safety_maps_vulnerabilities_from_safety_json(self):
        payload = {
            "vulnerabilities": [
                {
                    "package_name": "requests",
                    "vulnerability_id": "90553",
                    "analyzed_version": "2.19.1",
                    "advisory": "Requests before 2.20.0 sends credentials to the wrong host.",
                    "severity": "high",
                }
            ]
        }
        completed = subprocess.CompletedProcess(
            args=["safety"], returncode=1, stdout=json.dumps(payload), stderr=""
        )
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("requests==2.19.1\n")
            with patch.object(scanner.subprocess, "run", return_value=completed):
                findings = scanner.scan_safety(root)
        self.assertTrue(
            any(
                f["type"] == "vulnerability" and f["package"] == "requests" and f["id"] == "90553"
                for f in findings
            )
        )

    def test_scan_safety_without_manifests_scans_nothing(self):
        # No declared Python deps: safety must not fall back to scanning
        # the runner environment (pip/setuptools/wheel advisories are
        # not this repo's findings).
        with tempfile.TemporaryDirectory() as root:
            with patch.object(scanner, "shell_cmd") as mock_shell:
                findings = scanner.scan_safety(root)
        self.assertEqual(findings, [])
        mock_shell.assert_not_called()

    def test_pip_audit_failure_is_reported_as_incomplete_coverage(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = os.path.join(root, "requirements.txt")
            with open(manifest, "w", encoding="utf-8") as f:
                f.write("requests>=2.31\n")
            with patch.object(scanner, "_pip_audit_wheelhouse", return_value=None), \
                 patch.object(scanner.time, "sleep"), \
                 patch.object(scanner, "shell_cmd", return_value=None) as mock_shell:
                findings = scanner.scan_pip_audit(root)
        self.assertTrue(any(f["type"] == "scan_error" and f["id"] == "PIP_AUDIT_UNAVAILABLE" for f in findings))
        self.assertEqual(mock_shell.call_count, 3)  # bounded retries before giving up

    def test_pip_audit_retries_until_transport_recovers(self):
        payload = [{"name": "requests", "version": "2.19.1", "vulns": [
            {"id": "PYSEC-2018-28", "fix_versions": ["2.20.0"], "severity": "high"}]}]
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("requests==2.19.1\n")
            with patch.object(scanner, "_pip_audit_wheelhouse", return_value=None), \
                 patch.object(scanner.time, "sleep"), \
                 patch.object(scanner, "shell_cmd", side_effect=[None, payload]) as mock_shell:
                findings = scanner.scan_pip_audit(root)
        self.assertEqual(mock_shell.call_count, 2)
        self.assertTrue(any(f["type"] == "vulnerability" and f["id"] == "PYSEC-2018-28" for f in findings))
        self.assertFalse(any(f["type"] == "scan_error" for f in findings))

    def test_pip_audit_uses_wheelhouse_env_when_prestaged(self):
        seen = {}
        def capture(cmd, cwd, env=None):
            seen.update(env or {})
            return []
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "requirements.txt"), "w", encoding="utf-8") as f:
                f.write("requests>=2.31\n")
            with patch.object(scanner, "_pip_audit_wheelhouse", return_value="/tmp/wh-test"), \
                 patch.object(scanner, "shell_cmd", side_effect=capture):
                scanner.scan_pip_audit(root)
        self.assertEqual(seen.get("PIP_FIND_LINKS"), "/tmp/wh-test")
        self.assertEqual(seen.get("PIP_NO_INDEX"), "1")

    def test_shell_cmd_forwards_extra_env(self):
        completed = subprocess.CompletedProcess(
            args=["tool"], returncode=0, stdout="[]", stderr=""
        )
        with patch.object(scanner.subprocess, "run", return_value=completed) as mock_run:
            scanner.shell_cmd(["tool"], ".", env={"ZQM_TEST_MARKER": "yes"})
        passed_env = mock_run.call_args.kwargs["env"]
        self.assertEqual(passed_env["ZQM_TEST_MARKER"], "yes")
        self.assertIn("PATH", passed_env)  # merged over os.environ, not replaced


if __name__ == "__main__":
    unittest.main()
