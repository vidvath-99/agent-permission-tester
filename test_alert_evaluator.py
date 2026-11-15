import json
import tempfile
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

from alert_evaluator import evaluate_events, read_audit_events

class AuditReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.audit_file = Path(self.temp_dir.name) / "audit.jsonl"

    def test_reads_events_and_skips_blank_lines(self):
        events = [
            {"mode": "SECURE", "decision": "deny"},
            {"mode": "BROKEN", "decision": "allow"},
        ]
        content = "\n\n".join(json.dumps(event) for event in events)
        self.audit_file.write_text(content + "\n", encoding="utf-8")

        self.assertEqual(read_audit_events(self.audit_file), events)
        self.assertEqual(
            self.audit_file.read_text(encoding="utf-8"),
            content + "\n",
        )

    def test_empty_file_returns_empty_list(self):
        self.audit_file.write_text("", encoding="utf-8")

        self.assertEqual(read_audit_events(self.audit_file), [])

    def test_invalid_json_reports_line_number(self):
        self.audit_file.write_text(
            '{}\n{"timestamp":\n',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "line 2"):
            read_audit_events(self.audit_file)

    def test_non_object_record_is_rejected(self):
        self.audit_file.write_text('[]\n', encoding="utf-8")

        with self.assertRaisesRegex(
            ValueError, "line 1 must be an object"
        ):
            read_audit_events(self.audit_file)

    def test_missing_file_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            read_audit_events(self.audit_file)

class AlertEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(
            2026, 11, 15, 2, 0, tzinfo=timezone.utc
        )

    def event(self, *, seconds_ago=0, **changes):
        record = {
            "timestamp": (
                self.now - timedelta(seconds=seconds_ago)
            ).isoformat(),
            "mode": "SECURE",
            "decision": "deny",
        }
        record.update(changes)
        return record

    def evaluate(self, events, **options):
        return evaluate_events(events, now=self.now, **options)

    def test_empty_events_do_not_trigger(self):
        result = self.evaluate([])

        self.assertEqual(result["blocked_calls"], 0)
        self.assertFalse(result["triggered"])

    def test_below_threshold_does_not_trigger(self):
        result = self.evaluate(
            [self.event(seconds_ago=10) for _ in range(4)]
        )

        self.assertEqual(result["blocked_calls"], 4)
        self.assertFalse(result["triggered"])

    def test_exact_threshold_triggers(self):
        result = self.evaluate(
            [self.event(seconds_ago=10) for _ in range(5)]
        )

        self.assertEqual(result["blocked_calls"], 5)
        self.assertTrue(result["triggered"])

    def test_above_threshold_triggers(self):
        result = self.evaluate(
            [self.event(seconds_ago=10) for _ in range(6)]
        )

        self.assertEqual(result["blocked_calls"], 6)
        self.assertTrue(result["triggered"])

    def test_broken_mode_and_allowed_calls_are_excluded(self):
        result = self.evaluate(
            [
                self.event(mode="BROKEN"),
                self.event(decision="allow"),
                self.event(),
            ],
            threshold=2,
        )

        self.assertEqual(result["blocked_calls"], 1)
        self.assertFalse(result["triggered"])

    def test_window_boundaries_and_future_events(self):
        result = self.evaluate(
            [
                self.event(seconds_ago=301),
                self.event(seconds_ago=300),
                self.event(seconds_ago=299),
                self.event(seconds_ago=0),
                self.event(seconds_ago=-1),
            ]
        )

        self.assertEqual(result["blocked_calls"], 2)

    def test_equivalent_timezone_offset_is_counted(self):
        offset = timezone(timedelta(hours=2))
        timestamp = self.now.astimezone(offset).isoformat()

        result = self.evaluate(
            [self.event(timestamp=timestamp)],
            threshold=1,
        )

        self.assertTrue(result["triggered"])

    def test_custom_window_and_threshold(self):
        result = self.evaluate(
            [
                self.event(seconds_ago=30),
                self.event(seconds_ago=90),
            ],
            threshold=1,
            window_minutes=1,
        )

        self.assertEqual(result["blocked_calls"], 1)
        self.assertTrue(result["triggered"])

    def test_invalid_threshold_is_rejected(self):
        for value in (0, -1, True, 1.5, "5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.evaluate([], threshold=value)

    def test_invalid_window_is_rejected(self):
        for value in (0, -1, True, 1.5, "5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.evaluate([], window_minutes=value)

    def test_naive_now_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            evaluate_events(
                [],
                now=datetime(2026, 11, 15, 2, 0),
            )

    def test_invalid_relevant_timestamp_is_rejected(self):
        missing_timestamp = self.event()
        del missing_timestamp["timestamp"]

        records = [
            missing_timestamp,
            self.event(timestamp=None),
            self.event(timestamp="not-a-date"),
            self.event(timestamp="2026-11-15T02:00:00"),
        ]

        for record in records:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    self.evaluate([record])

    def test_non_object_event_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "object"):
            self.evaluate(["invalid"])

    def test_result_contains_rule_and_window(self):
        result = self.evaluate([])

        self.assertEqual(
            result["rule_id"], "secure_denials_threshold"
        )
        self.assertEqual(result["threshold"], 5)
        self.assertEqual(
            result["window_start"],
            (self.now - timedelta(minutes=5)).isoformat(),
        )
        self.assertEqual(
            result["window_end"], self.now.isoformat()
        )


if __name__ == "__main__":
    unittest.main()
