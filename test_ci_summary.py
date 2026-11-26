import contextlib
import io
import json
import os
import tempfile
import unittest

from ci_summary import classify, main, render_summary


def make_report(results):
    return {
        "summary": {"total": len(results), "passed": 1, "failed": 1},
        "results": results,
    }


class CiSummaryTests(unittest.TestCase):
    def test_classify_all_cases(self):
        self.assertEqual(classify({}), "Not recorded")
        self.assertEqual(
            classify({"state_verification": None}), "Not requested"
        )
        for status, label in (
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("error", "Error"),
        ):
            self.assertEqual(
                classify({"state_verification": {"status": status}}),
                label,
            )
        self.assertEqual(
            classify({"state_verification": {"status": "odd"}}),
            "Unrecognized",
        )
        self.assertEqual(
            classify({"state_verification": "passed"}), "Unrecognized"
        )

    def test_render_counts_each_status(self):
        report = make_report(
            [
                {"state_verification": {"status": "passed"}},
                {"state_verification": {"status": "passed"}},
                {"state_verification": {"status": "failed"}},
                {"state_verification": None},
            ]
        )
        text = render_summary(report)
        self.assertIn("| Passed | 2 |", text)
        self.assertIn("| Failed | 1 |", text)
        self.assertIn("| Error | 0 |", text)
        self.assertIn("| Not requested | 1 |", text)
        self.assertNotIn("Not recorded", text)
        self.assertNotIn("Unrecognized", text)

    def test_render_shows_not_recorded_for_old_reports(self):
        text = render_summary(make_report([{}]))
        self.assertIn("| Not recorded | 1 |", text)

    def test_main_prints_summary(self):
        report = make_report([{"state_verification": None}])
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "report.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main([path])
        self.assertEqual(code, 0)
        self.assertIn("## API permission results", out.getvalue())

    def test_main_rejects_missing_and_invalid_files(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = os.path.join(folder, "missing.json")
            bad = os.path.join(folder, "bad.json")
            with open(bad, "w", encoding="utf-8") as handle:
                handle.write("[1, 2]")
            for path in (missing, bad):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code = main([path])
                self.assertEqual(code, 1)
                self.assertEqual(
                    err.getvalue().strip(),
                    "Could not read the API results report.",
                )


if __name__ == "__main__":
    unittest.main()