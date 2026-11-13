import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runner import load_suite, run_suite


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.scenario_file = Path(self.temp_dir.name) / "scenarios.json"

        self.suite = {
            "schema_version": 1,
            "name": "Runner test suite",
            "scenarios": [
                {
                    "id": "own-company-read",
                    "description": "Read an own-company ticket.",
                    "agent": "soc-agent",
                    "tool": "tickets:read",
                    "ticket": "INC-001",
                    "expected": {
                        "decision": "allow",
                        "reason": None,
                    },
                },
                {
                    "id": "cross-company-read",
                    "description": "Reject a cross-company read.",
                    "agent": "soc-agent",
                    "tool": "tickets:read",
                    "ticket": "INC-002",
                    "expected": {
                        "decision": "deny",
                        "reason": "tenant_mismatch",
                    },
                },
            ],
        }

    def write_suite(self, suite):
        self.scenario_file.write_text(
            json.dumps(suite),
            encoding="utf-8",
        )

    def test_load_valid_suite(self):
        self.write_suite(self.suite)

        loaded = load_suite(self.scenario_file)

        self.assertEqual(loaded, self.suite)

    def test_secure_suite_passes(self):
        report = run_suite(self.suite)

        self.assertEqual(report["mode"], "SECURE")
        self.assertEqual(
            report["summary"],
            {"total": 2, "passed": 2, "failed": 0},
        )
        self.assertTrue(
            all(item["passed"] for item in report["results"])
        )

    def test_broken_suite_detects_cross_company_access(self):
        report = run_suite(self.suite, broken=True)

        self.assertEqual(report["mode"], "BROKEN")
        self.assertEqual(
            report["summary"],
            {"total": 2, "passed": 1, "failed": 1},
        )

        result = report["results"][1]
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["actual"],
            {"decision": "allow", "reason": None},
        )

    def test_wrong_denial_reason_fails(self):
        suite = copy.deepcopy(self.suite)
        suite["scenarios"][1]["expected"]["reason"] = (
            "missing_permission"
        )

        report = run_suite(suite)

        self.assertFalse(report["results"][1]["passed"])
        self.assertEqual(
            report["results"][1]["actual"]["reason"],
            "tenant_mismatch",
        )

    def test_duplicate_ids_rejected(self):
        self.suite["scenarios"][1]["id"] = "own-company-read"
        self.write_suite(self.suite)

        with self.assertRaisesRegex(
            ValueError, "Duplicate scenario id"
        ):
            load_suite(self.scenario_file)

    def test_empty_scenarios_rejected(self):
        self.suite["scenarios"] = []
        self.write_suite(self.suite)

        with self.assertRaisesRegex(ValueError, "non-empty list"):
            load_suite(self.scenario_file)

    def test_unsupported_schema_rejected(self):
        self.suite["schema_version"] = 2
        self.write_suite(self.suite)

        with self.assertRaisesRegex(ValueError, "schema_version 1"):
            load_suite(self.scenario_file)

    def test_allow_with_denial_reason_rejected(self):
        self.suite["scenarios"][0]["expected"]["reason"] = (
            "tenant_mismatch"
        )
        self.write_suite(self.suite)

        with self.assertRaisesRegex(ValueError, "null reason"):
            load_suite(self.scenario_file)

    def test_each_scenario_has_fresh_gateway(self):
        self.suite["scenarios"] = [
            copy.deepcopy(self.suite["scenarios"][0]),
            copy.deepcopy(self.suite["scenarios"][0]),
        ]
        self.suite["scenarios"][1]["id"] = (
            "second-own-company-read"
        )

        report = run_suite(self.suite)

        self.assertEqual(report["summary"]["passed"], 2)
        for result in report["results"]:
            self.assertEqual(len(result["audit"]), 1)

    def run_cli(self, *extra_args):
        self.write_suite(self.suite)
        report_path = (
            Path(self.temp_dir.name) / "reports" / "results.json"
        )

        result = subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().with_name("runner.py")
                ),
                str(self.scenario_file),
                "--report",
                str(report_path),
                *extra_args,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        return result, report_path

    def test_cli_secure_writes_passing_report(self):
        result, report_path = self.run_cli()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report_path.is_file())

        report = json.loads(
            report_path.read_text(encoding="utf-8")
        )

        self.assertEqual(report["mode"], "SECURE")
        self.assertEqual(
            report["summary"],
            {"total": 2, "passed": 2, "failed": 0},
        )
        self.assertIn("Passed: 2", result.stdout)

    def test_cli_broken_returns_failure_and_writes_report(self):
        result, report_path = self.run_cli("--broken")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(report_path.is_file())

        report = json.loads(
            report_path.read_text(encoding="utf-8")
        )

        self.assertEqual(report["mode"], "BROKEN")
        self.assertEqual(
            report["summary"],
            {"total": 2, "passed": 1, "failed": 1},
        )
        self.assertIn(
            "FAIL: cross-company-read",
            result.stdout,
        )

    def test_cli_invalid_suite_returns_input_error(self):
        self.suite["schema_version"] = 2

        result, report_path = self.run_cli()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Runner error:", result.stderr)
        self.assertFalse(report_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)