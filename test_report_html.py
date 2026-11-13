import unittest

from report_html import render_report


class HTMLReportTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "report_version": 1,
            "suite": "HTML renderer test suite",
            "timestamp": "2026-11-13T00:00:00+00:00",
            "mode": "SECURE",
            "source": "scenarios/test.json",
            "summary": {
                "total": 1,
                "passed": 1,
                "failed": 0,
            },
            "results": [
                {
                    "id": "cross-company-read",
                    "description": "Reject a cross-company read.",
                    "expected": {
                        "decision": "deny",
                        "reason": "tenant_mismatch",
                    },
                    "actual": {
                        "decision": "deny",
                        "reason": "tenant_mismatch",
                    },
                    "passed": True,
                    "error": None,
                    "audit": [],
                }
            ],
        }

    def test_renders_suite_and_summary(self):
        html = render_report(self.report)

        self.assertIn("HTML renderer test suite", html)
        self.assertIn("Mode: SECURE", html)
        self.assertIn("Total: 1", html)
        self.assertIn("Passed: 1", html)
        self.assertIn("Failed: 0", html)
        self.assertIn("scenarios/test.json", html)

    def test_expected_denial_is_displayed_as_pass(self):
        html = render_report(self.report)

        self.assertIn('class="pass">PASS</td>', html)
        self.assertIn("cross-company-read", html)
        self.assertIn("tenant_mismatch", html)
        self.assertNotIn('class="fail">FAIL</td>', html)

    def test_regression_is_displayed_as_fail(self):
        self.report["mode"] = "BROKEN"
        self.report["summary"] = {
            "total": 1,
            "passed": 0,
            "failed": 1,
        }
        self.report["results"][0]["actual"] = {
            "decision": "allow",
            "reason": None,
        }
        self.report["results"][0]["passed"] = False

        html = render_report(self.report)

        self.assertIn("Mode: BROKEN", html)
        self.assertIn('class="fail">FAIL</td>', html)
        self.assertIn("Failed: 1", html)
        self.assertIn("tenant_mismatch", html)
        self.assertIn("allow", html)

    def test_execution_error_has_no_decision(self):
        result = self.report["results"][0]
        result["actual"] = None
        result["passed"] = False
        result["error"] = "RuntimeError: simulated failure"
        self.report["summary"] = {
            "total": 1,
            "passed": 0,
            "failed": 1,
        }

        html = render_report(self.report)

        self.assertIn("No decision", html)
        self.assertIn("RuntimeError: simulated failure", html)
        self.assertIn('class="fail">FAIL</td>', html)

    def test_report_text_is_html_escaped(self):
        payload = '<script>alert("demo")</script>'
        escaped = (
            "&lt;script&gt;alert(&quot;demo&quot;)&lt;/script&gt;"
        )

        self.report["suite"] = payload
        self.report["timestamp"] = payload
        self.report["mode"] = payload
        self.report["source"] = payload

        result = self.report["results"][0]
        result["id"] = payload
        result["description"] = payload
        result["error"] = payload
        result["expected"] = {
            "decision": payload,
            "reason": payload,
        }
        result["actual"] = {
            "decision": payload,
            "reason": payload,
        }

        html = render_report(self.report)

        self.assertNotIn(payload, html)
        self.assertEqual(html.count(escaped), 12)

    def test_missing_source_is_supported(self):
        del self.report["source"]

        html = render_report(self.report)

        self.assertIn("Scenario source: —", html)
class HTMLReportCLITests(unittest.TestCase):
    def setUp(self):
        import json
        import tempfile
        from pathlib import Path

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.folder = Path(self.temp_dir.name)
        self.input_path = self.folder / "input.json"
        self.output_path = self.folder / "nested" / "report.html"

        self.report = {
            "report_version": 1,
            "suite": "CLI report test",
            "timestamp": "2026-11-13T00:00:00+00:00",
            "mode": "SECURE",
            "summary": {
                "total": 1,
                "passed": 1,
                "failed": 0,
            },
            "results": [
                {
                    "id": "read",
                    "description": "Allowed read.",
                    "expected": {
                        "decision": "allow",
                        "reason": None,
                    },
                    "actual": {
                        "decision": "allow",
                        "reason": None,
                    },
                    "passed": True,
                    "error": None,
                }
            ],
        }

        self.input_path.write_text(
            json.dumps(self.report),
            encoding="utf-8",
        )

    def run_cli(self, output_path):
        import subprocess
        import sys
        from pathlib import Path

        return subprocess.run(
            [
                sys.executable,
                str(
                    Path(__file__).resolve().with_name(
                        "report_html.py"
                    )
                ),
                str(self.input_path),
                "--output",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_cli_creates_html_file(self):
        result = self.run_cli(self.output_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.output_path.is_file())

        html = self.output_path.read_text(encoding="utf-8")

        self.assertIn("<!doctype html>", html)
        self.assertIn("CLI report test", html)
        self.assertIn('class="pass">PASS</td>', html)

    def test_cli_rejects_unsupported_version(self):
        import json

        self.report["report_version"] = 2
        self.input_path.write_text(
            json.dumps(self.report),
            encoding="utf-8",
        )

        result = self.run_cli(self.output_path)

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "Only report_version 1 is supported.",
            result.stderr,
        )
        self.assertFalse(self.output_path.exists())

    def test_cli_preserves_input_when_output_matches(self):
        original = self.input_path.read_bytes()

        result = self.run_cli(self.input_path)

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "Output must not overwrite the input report.",
            result.stderr,
        )
        self.assertEqual(self.input_path.read_bytes(), original)



if __name__ == "__main__":
    unittest.main(verbosity=2)