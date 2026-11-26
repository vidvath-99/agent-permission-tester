import unittest

from report_html import render_report


class APIHTMLReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "report_type": "local_api_permissions",
            "report_version": 1,
            "suite": "API HTML tests",
            "timestamp": "2026-11-19T00:00:00+00:00",
            "mode": "IN_PROCESS",
            "summary": {"total": 1, "passed": 1, "failed": 0},
            "results": [
                {
                    "id": "blocked-read",
                    "description": "Reject cross-company access.",
                    "credential": "company-a",
                    "method": "GET",
                    "path": "/tickets/INC-002",
                    "expected": {"status_code": 404, "body": {}},
                    "actual": {"status_code": 404, "body": {}},
                    "passed": True,
                    "error": None,
                }
            ],
        }

    def test_missing_state_verification_is_not_recorded(self):
        html = render_report(self.report)

        self.assertIn("State verification: Not recorded.", html)
        self.assertNotIn("State verification: Not requested.", html)

    def test_state_verification_labels(self):
        cases = [
            (None, "Not requested"),
            ({"status": "passed"}, "Passed"),
            ({"status": "failed"}, "Failed"),
            ({"status": "error"}, "Error"),
        ]
        result = self.report["results"][0]

        for verification, label in cases:
            with self.subTest(verification=verification):
                result["state_verification"] = verification
                html = render_report(self.report)
                self.assertIn(f"State verification: {label}.", html)
                self.assertNotIn("State verification: Not recorded.", html)

    def test_expected_denial_renders_as_pass(self):
        html = render_report(self.report)

        self.assertIn("Request: GET /tickets/INC-002", html)
        self.assertIn("Credential alias: company-a", html)
        self.assertEqual(html.count("HTTP 404"), 2)
        self.assertIn('class="pass">PASS</td>', html)
        self.assertIn("Checked body fields:", html)
        self.assertIn("including value types", html)
        self.assertNotIn("observed decision and reason", html)

    def test_response_mismatch_renders_as_fail(self):
        result = self.report["results"][0]
        result["actual"] = {
            "status_code": 200,
            "body": {"tenant": "company-b"},
        }
        result["passed"] = False
        self.report["summary"] = {"total": 1, "passed": 0, "failed": 1}

        html = render_report(self.report)

        self.assertIn("HTTP 404", html)
        self.assertIn("HTTP 200", html)
        self.assertIn("company-b", html)
        self.assertIn('class="fail">FAIL</td>', html)

    def test_execution_error_has_no_response(self):
        result = self.report["results"][0]
        result["actual"] = None
        result["passed"] = False
        result["error"] = "Scenario execution failed (RuntimeError)."
        self.report["summary"] = {"total": 1, "passed": 0, "failed": 1}

        html = render_report(self.report)

        self.assertIn("No response", html)
        self.assertIn(result["error"], html)
        self.assertIn('class="fail">FAIL</td>', html)

    def test_api_fields_are_html_escaped(self):
        payload = "<script>alert(1)</script>"
        result = self.report["results"][0]
        for field in ("method", "path", "credential"):
            result[field] = payload
        result["expected"]["body"] = {"value": payload}
        result["actual"]["body"] = {"value": payload}

        html = render_report(self.report)

        self.assertNotIn(payload, html)
        self.assertEqual(
            html.count("&lt;script&gt;alert(1)&lt;/script&gt;"),
            5,
        )



    def test_cli_renders_real_api_runner_report(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        from api_runner import load_suite, run_suite

        root = Path(__file__).resolve().parent
        suite = load_suite(root / "scenarios" / "api-permissions.json")
        report = run_suite(suite)

        self.assertEqual(
            report["summary"],
            {"total": 10, "passed": 10, "failed": 0},
        )

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            input_path = folder / "api-results.json"
            output_path = folder / "nested" / "api-results.html"
            input_path.write_text(
                json.dumps(report),
                encoding="utf-8",
            )
            original = input_path.read_bytes()

            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "report_html.py"),
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output_path.is_file())
            self.assertEqual(input_path.read_bytes(), original)

            html = output_path.read_text(encoding="utf-8")

            self.assertIn("<!doctype html>", html)
            self.assertIn("Mode: IN_PROCESS", html)
            self.assertIn("Total: 10", html)
            self.assertIn("Passed: 10", html)
            self.assertIn("Failed: 0", html)
            self.assertEqual(
                html.count('class="pass">PASS</td>'),
                10,
            )
            self.assertNotIn('class="fail">FAIL</td>', html)
            self.assertIn("Checked body fields:", html)
            self.assertIn("including value types", html)

            verification_counts = {
                "Not requested": 0,
                "Passed": 0,
                "Failed": 0,
                "Error": 0,
            }
            labels = {
                "passed": "Passed",
                "failed": "Failed",
                "error": "Error",
            }
            for scenario in report["results"]:
                self.assertIn("state_verification", scenario)
                verification = scenario["state_verification"]
                if verification is None:
                    verification_counts["Not requested"] += 1
                else:
                    self.assertEqual(set(verification), {"status"})
                    verification_counts[labels[verification["status"]]] += 1

            for label, count in verification_counts.items():
                self.assertEqual(
                    html.count(f"State verification: {label}."),
                    count,
                )

            self.assertEqual(
                html.count("State verification:"),
                len(report["results"]),
            )
            self.assertNotIn("State verification: Not recorded.", html)
            self.assertIn("requested state verification passed.", html)



if __name__ == "__main__":
    unittest.main()
