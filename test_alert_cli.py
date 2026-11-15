import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AlertCliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.audit = self.root / "audit.jsonl"
        self.output = self.root / "alerts.jsonl"
        self.script = Path(__file__).resolve().with_name("alert_cli.py")
        self.timestamp = "2026-11-15T02:00:00+00:00"

        event = {
            "timestamp": self.timestamp,
            "mode": "SECURE",
            "decision": "deny",
        }
        self.audit.write_text(
            json.dumps(event) + "\n",
            encoding="utf-8",
        )

    def invoke(self, *args):
        return subprocess.run(
            [sys.executable, str(self.script), *map(str, args)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=self.root,
        )

    def test_help(self):
        result = self.invoke("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--window-minutes", result.stdout)
        self.assertFalse(self.output.exists())

    def test_triggered_run_and_duplicate_run(self):
        original_audit = self.audit.read_bytes()
        args = (
            self.audit,
            "--output", self.output,
            "--threshold", "1",
            "--now", self.timestamp,
        )

        first = self.invoke(*args)

        self.assertEqual(first.returncode, 0, first.stderr)
        outcome = json.loads(first.stdout)
        self.assertTrue(outcome["evaluation"]["triggered"])
        self.assertTrue(outcome["alert_written"])
        original_output = self.output.read_bytes()

        second = self.invoke(*args)

        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse(json.loads(second.stdout)["alert_written"])
        self.assertEqual(self.output.read_bytes(), original_output)
        self.assertEqual(self.audit.read_bytes(), original_audit)

    def test_invalid_threshold_does_not_create_output(self):
        result = self.invoke(
            self.audit,
            "--output", self.output,
            "--threshold", "0",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("threshold", result.stderr)
        self.assertFalse(self.output.exists())

    def test_same_input_and_output_is_rejected(self):
        original = self.audit.read_bytes()

        result = self.invoke(
            self.audit,
            "--output", self.audit,
            "--threshold", "1",
            "--now", self.timestamp,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("different files", result.stderr)
        self.assertEqual(self.audit.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()