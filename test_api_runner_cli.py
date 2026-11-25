import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from api_runner import load_suite, main


class APIRunnerCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.directory)
        demo_path = (
            Path(__file__).resolve().parent
            / "scenarios"
            / "api-permissions.json"
        )
        self.suite = load_suite(demo_path)
        self.suite_path = self.root / "suite.json"
        self.write_suite(self.suite)

    def write_suite(self, suite):
        self.suite_path.write_text(
            json.dumps(suite),
            encoding="utf-8",
        )

    def invoke(self, *arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(arguments))

        return code, stdout.getvalue(), stderr.getvalue()

    def test_passing_suite_writes_report(self):
        output_path = self.root / "report.json"

        code, stdout, stderr = self.invoke(
            str(self.suite_path),
            "--output",
            str(output_path),
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("7 total, 7 passed, 0 failed", stdout)

        report = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(
            report["summary"],
            {"total": 7, "passed": 7, "failed": 0},
        )

    def test_failing_suite_returns_one(self):
        suite = copy.deepcopy(self.suite)
        suite["scenarios"] = [suite["scenarios"][0]]
        suite["scenarios"][0]["expected"]["status_code"] = 403
        self.write_suite(suite)

        code, stdout, stderr = self.invoke(str(self.suite_path))

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertIn("1 total, 0 passed, 1 failed", stdout)
        self.assertIn("FAIL company-a-own-read:", stdout)

    def test_report_records_state_verification_status(self):
        output_path = self.root / "report.json"

        code, _, stderr = self.invoke(
            str(self.suite_path),
            "--output",
            str(output_path),
        )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")

        report = json.loads(output_path.read_text(encoding="utf-8"))
        statuses = {
            result["id"]: result["state_verification"]
            for result in report["results"]
        }
        self.assertEqual(
            statuses["company-a-delete-denied"],
            {"status": "passed"},
        )
        others = [
            value
            for key, value in statuses.items()
            if key != "company-a-delete-denied"
        ]
        self.assertEqual(len(others), 6)
        self.assertTrue(all(value is None for value in others))

    def test_unreadable_before_state_returns_one_and_reports_error(self):
        suite = copy.deepcopy(self.suite)
        scenario = next(
            item
            for item in suite["scenarios"]
            if item["id"] == "company-a-delete-denied"
        )
        scenario["path"] = "/tickets/DOES-NOT-EXIST"
        suite["scenarios"] = [scenario]
        self.write_suite(suite)
        output_path = self.root / "report.json"

        code, stdout, stderr = self.invoke(
            str(self.suite_path),
            "--output",
            str(output_path),
        )

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        self.assertIn("1 total, 0 passed, 1 failed", stdout)
        self.assertIn("FAIL company-a-delete-denied:", stdout)

        report = json.loads(output_path.read_text(encoding="utf-8"))
        result = report["results"][0]
        self.assertEqual(result["state_verification"], {"status": "error"})
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["error"],
            "Scenario execution failed (ValueError).",
        )
    def test_invalid_suite_returns_two(self):
        self.write_suite({})

        code, stdout, stderr = self.invoke(str(self.suite_path))

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Could not load or run", stderr)

    def test_missing_suite_returns_two(self):
        code, stdout, stderr = self.invoke(
            str(self.root / "missing.json")
        )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Could not load or run", stderr)

    def test_unwritable_report_target_returns_two(self):
        code, stdout, stderr = self.invoke(
            str(self.suite_path),
            "--output",
            str(self.root),
        )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Could not write", stderr)


if __name__ == "__main__":
    unittest.main()
