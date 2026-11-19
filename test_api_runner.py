import copy
import json
import tempfile
import unittest
from pathlib import Path

from api_runner import load_suite, run_suite, validate_suite


class APISuiteValidationTests(unittest.TestCase):
    def setUp(self):
        self.suite = {
            "schema_version": 1,
            "name": "API validation tests",
            "scenarios": [
                {
                    "id": "own-read",
                    "description": "Company A reads its own ticket.",
                    "credential": "company-a",
                    "method": "GET",
                    "path": "/tickets/INC-001",
                    "expected": {
                        "status_code": 200,
                        "body": {"tenant": "company-a"},
                    },
                }
            ],
        }

    def test_valid_suite_is_not_modified(self):
        original = copy.deepcopy(self.suite)

        result = validate_suite(self.suite)

        self.assertEqual(result, original)
        self.assertEqual(self.suite, original)

    def test_load_suite_from_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "suite.json"
            path.write_text(
                json.dumps(self.suite),
                encoding="utf-8",
            )

            self.assertEqual(load_suite(path), self.suite)

    def test_invalid_suite_structure_is_rejected(self):
        cases = [
            None,
            [],
            {},
            {**self.suite, "schema_version": True},
            {**self.suite, "schema_version": 2},
            {**self.suite, "name": " "},
            {**self.suite, "scenarios": []},
            {**self.suite, "scenarios": {}},
            {**self.suite, "headers": {}},
        ]

        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    validate_suite(candidate)

    def test_duplicate_ids_are_rejected(self):
        duplicate = copy.deepcopy(self.suite["scenarios"][0])
        self.suite["scenarios"].append(duplicate)

        self.assertEqual(len(self.suite["scenarios"]), 2)
        self.assertEqual(
            self.suite["scenarios"][0]["id"],
            self.suite["scenarios"][1]["id"],
        )

        with self.assertRaises(ValueError):
            validate_suite(self.suite)

    def test_invalid_scenario_fields_are_rejected(self):
        original = self.suite["scenarios"][0]
        cases = [
            None,
            {},
            {**original, "id": " "},
            {**original, "description": None},
            {**original, "credential": "raw-bearer-token"},
            {**original, "method": "POST"},
            {**original, "headers": {"Authorization": "Bearer example"}},
        ]

        for candidate in cases:
            with self.subTest(candidate=candidate):
                suite = copy.deepcopy(self.suite)
                suite["scenarios"] = [candidate]

                with self.assertRaises(ValueError):
                    validate_suite(suite)

    def test_non_local_ticket_paths_are_rejected(self):
        paths = [
            "https://example.com/tickets/INC-001",
            "//example.com/tickets/INC-001",
            "/health",
            "/tickets/",
            "/tickets/../health",
            "/tickets/INC-001?extra=1",
            "/tickets/INC-001#fragment",
            "/tickets/INC%2F001",
        ]

        for path in paths:
            with self.subTest(path=path):
                suite = copy.deepcopy(self.suite)
                suite["scenarios"][0]["path"] = path

                with self.assertRaises(ValueError):
                    validate_suite(suite)

    def test_invalid_expectations_are_rejected(self):
        cases = [
            None,
            {},
            {"status_code": True, "body": {}},
            {"status_code": "200", "body": {}},
            {"status_code": 99, "body": {}},
            {"status_code": 600, "body": {}},
            {"status_code": 200, "body": []},
            {"status_code": 200, "body": {}, "headers": {}},
        ]

        for expected in cases:
            with self.subTest(expected=expected):
                suite = copy.deepcopy(self.suite)
                suite["scenarios"][0]["expected"] = expected

                with self.assertRaises(ValueError):
                    validate_suite(suite)

    def test_supported_credentials_and_methods_are_accepted(self):
        for credential in ("company-a", "company-b", "none"):
            for method in ("GET", "DELETE"):
                with self.subTest(credential=credential, method=method):
                    suite = copy.deepcopy(self.suite)
                    scenario = suite["scenarios"][0]
                    scenario["credential"] = credential
                    scenario["method"] = method

                    self.assertEqual(validate_suite(suite), suite)


class APISuiteExecutionTests(unittest.TestCase):
    def load_demo_suite(self):
        path = (
            Path(__file__).resolve().parent
            / "scenarios"
            / "api-permissions.json"
        )
        return load_suite(path)

    def test_demo_suite_passes_without_modifying_input(self):
        suite = self.load_demo_suite()
        original = copy.deepcopy(suite)

        report = run_suite(suite)

        self.assertEqual(
            report["summary"],
            {"total": 4, "passed": 4, "failed": 0},
        )
        self.assertEqual(report["mode"], "IN_PROCESS")
        self.assertEqual(suite, original)
        self.assertTrue(
            all(result["error"] is None for result in report["results"])
        )
        self.assertEqual(
            report["results"][0]["actual"]["body"],
            {"tenant": "company-a"},
        )

    def test_wrong_expected_status_fails(self):
        suite = self.load_demo_suite()
        suite["scenarios"] = [suite["scenarios"][0]]
        suite["scenarios"][0]["expected"]["status_code"] = 403

        report = run_suite(suite)
        result = report["results"][0]

        self.assertFalse(result["passed"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["actual"]["status_code"], 200)
        self.assertEqual(report["summary"]["failed"], 1)

    def test_missing_expected_field_fails(self):
        suite = self.load_demo_suite()
        suite["scenarios"] = [suite["scenarios"][0]]
        suite["scenarios"][0]["expected"]["body"] = {
            "nonexistent_field": None
        }

        report = run_suite(suite)
        result = report["results"][0]

        self.assertFalse(result["passed"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["actual"]["body"], {})


if __name__ == "__main__":
    unittest.main()
