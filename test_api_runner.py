import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import api_runner
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

    def test_verify_unchanged_is_accepted_without_modifying_input(self):
        for credential in ("company-a", "company-b"):
            with self.subTest(credential=credential):
                suite = copy.deepcopy(self.suite)
                scenario = suite["scenarios"][0]
                scenario["method"] = "DELETE"
                scenario["expected"] = {
                    "status_code": 403,
                    "body": {},
                }
                scenario["verify_unchanged"] = {
                    "credential": credential,
                }
                original = copy.deepcopy(suite)

                self.assertEqual(validate_suite(suite), original)
                self.assertEqual(suite, original)

    def test_invalid_verify_unchanged_is_rejected(self):
        cases = [
            ("DELETE", 403, None),
            ("DELETE", 403, {}),
            ("DELETE", 403, []),
            ("DELETE", 403, {"credential": "none"}),
            ("DELETE", 403, {"credential": "raw-bearer-token"}),
            ("DELETE", 403, {"credential": None}),
            ("DELETE", 403, {"credential": []}),
            (
                "DELETE",
                403,
                {"credential": "company-a", "path": "/tickets/INC-002"},
            ),
            ("GET", 403, {"credential": "company-a"}),
            ("DELETE", 200, {"credential": "company-a"}),
            ("DELETE", 302, {"credential": "company-a"}),
            ("DELETE", 500, {"credential": "company-a"}),
        ]

        for method, status, verification in cases:
            with self.subTest(
                method=method,
                status=status,
                verification=verification,
            ):
                suite = copy.deepcopy(self.suite)
                scenario = suite["scenarios"][0]
                scenario["method"] = method
                scenario["expected"] = {
                    "status_code": status,
                    "body": {},
                }
                scenario["verify_unchanged"] = verification

                with self.assertRaises(ValueError):
                    validate_suite(suite)


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
            {"total": 7, "passed": 7, "failed": 0},
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

    def test_state_verification_outcomes_are_reported(self):
        suite = self.load_demo_suite()

        report = run_suite(suite)

        for result in report["results"]:
            with self.subTest(scenario=result["id"]):
                self.assertIn("state_verification", result)
                if result["id"] == "company-a-delete-denied":
                    self.assertEqual(
                        result["state_verification"],
                        {"status": "passed"},
                    )
                else:
                    self.assertIsNone(result["state_verification"])


class APISuiteRegressionTests(unittest.TestCase):
    def test_unsuccessful_after_read_reports_verification_failure(self):
        suite = self.load_demo_suite()
        scenario = next(
            scenario
            for scenario in suite["scenarios"]
            if scenario["id"] == "company-a-delete-denied"
        )
        suite["scenarios"] = [scenario]
        scenario["verify_unchanged"] = {"credential": "company-a"}

        with patch("api_runner.TestClient") as client_class:
            client = client_class.return_value.__enter__.return_value
            before = unittest.mock.Mock()
            before.status_code = 200
            before.json.return_value = {"id": "INC-001"}
            after = unittest.mock.Mock()
            after.status_code = 500
            client.get.side_effect = [before, after]
            response = client.request.return_value
            response.status_code = scenario["expected"]["status_code"]
            response.json.return_value = dict(scenario["expected"]["body"])

            report = run_suite(suite)

            self.assertEqual(client.get.call_count, 2)
            client.request.assert_called_once()

        result = report["results"][0]
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["state_verification"],
            {"status": "failed"},
        )
        self.assertEqual(
            result["error"],
            "State preservation check failed.",
        )

    def test_unsuccessful_before_read_reports_verification_error(self):
        suite = self.load_demo_suite()
        scenario = next(
            scenario
            for scenario in suite["scenarios"]
            if scenario["id"] == "company-a-delete-denied"
        )
        suite["scenarios"] = [scenario]
        scenario["verify_unchanged"] = {"credential": "company-a"}

        with patch("api_runner.TestClient") as client_class:
            client = client_class.return_value.__enter__.return_value
            client.get.return_value.status_code = 403

            report = run_suite(suite)

            client.get.assert_called_once()
            client.request.assert_not_called()

        result = report["results"][0]
        self.assertFalse(result["passed"])
        self.assertIsNone(result["actual"])
        self.assertEqual(
            result["state_verification"],
            {"status": "error"},
        )
        self.assertEqual(
            result["error"],
            "Scenario execution failed (ValueError).",
        )

    def test_denied_delete_that_changes_visible_state_fails(self):
        suite = self.load_demo_suite()
        scenario = next(
            scenario
            for scenario in suite["scenarios"]
            if scenario["id"] == "company-a-delete-denied"
        )
        suite["scenarios"] = [scenario]
        scenario["verify_unchanged"] = {"credential": "company-a"}
        original_suite = copy.deepcopy(suite)

        original_factory = api_runner.create_app
        calls = []

        def create_faulty_app(*, audit_file=None):
            app = original_factory(audit_file=audit_file)
            gateway = app.state.gateway
            original_call = gateway.call
            visible_state = {"revision": 0}

            def faulty_call(agent_id, tool, ticket_id):
                calls.append((agent_id, tool, ticket_id))

                if tool == "tickets:delete":
                    visible_state["revision"] += 1

                result = original_call(agent_id, tool, ticket_id)

                if tool == "tickets:read":
                    result = dict(result)
                    result["regression_revision"] = visible_state["revision"]

                return result

            gateway.call = faulty_call
            return app

        with patch(
            "api_runner.create_app",
            side_effect=create_faulty_app,
        ) as factory:
            report = run_suite(suite)

        factory.assert_called_once()
        self.assertEqual(
            calls,
            [
                ("soc-agent", "tickets:read", "INC-001"),
                ("soc-agent", "tickets:delete", "INC-001"),
                ("soc-agent", "tickets:read", "INC-001"),
            ],
        )
        self.assertEqual(
            report["summary"],
            {"total": 1, "passed": 0, "failed": 1},
        )

        result = report["results"][0]
        self.assertEqual(result["actual"]["status_code"], 403)
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["state_verification"],
            {"status": "failed"},
        )
        self.assertEqual(
            result["error"],
            "State preservation check failed.",
        )
        self.assertEqual(suite, original_suite)
        self.assertNotIn("regression_revision", json.dumps(report))

    def load_demo_suite(self):
        path = (
            Path(__file__).resolve().parent
            / "scenarios"
            / "api-permissions.json"
        )
        return load_suite(path)

    def test_each_scenario_gets_a_fresh_app_and_audit_path(self):
        suite = self.load_demo_suite()
        applications = []
        audit_paths = []
        original_factory = api_runner.create_app

        def capture_app(*, audit_file=None):
            app = original_factory(audit_file=audit_file)
            applications.append(app)
            audit_paths.append(Path(audit_file))
            return app

        with patch("api_runner.create_app", side_effect=capture_app):
            report = run_suite(suite)

        count = len(suite["scenarios"])
        self.assertEqual(report["summary"]["passed"], count)
        self.assertEqual(len(applications), count)
        self.assertEqual(len({id(app) for app in applications}), count)
        self.assertEqual(len(set(audit_paths)), count)
        self.assertTrue(all(path.is_absolute() for path in audit_paths))
        self.assertTrue(all(not path.exists() for path in audit_paths))

    def test_demo_token_environment_is_restored(self):
        suite = self.load_demo_suite()
        suite["scenarios"] = [suite["scenarios"][0]]

        for initially_present in (False, True):
            with self.subTest(initially_present=initially_present):
                with patch.dict(os.environ):
                    if initially_present:
                        os.environ["DEMO_TOKEN_A"] = "original-a-" + "a" * 32
                        os.environ["DEMO_TOKEN_B"] = "original-b-" + "b" * 32
                    else:
                        os.environ.pop("DEMO_TOKEN_A", None)
                        os.environ.pop("DEMO_TOKEN_B", None)

                    before = dict(os.environ)

                    report = run_suite(suite)

                    self.assertEqual(report["summary"]["failed"], 0)
                    self.assertEqual(dict(os.environ), before)

    def test_factory_error_fails_one_scenario_and_continues(self):
        suite = self.load_demo_suite()
        original_factory = api_runner.create_app
        calls = 0

        def fail_first_app(*, audit_file=None):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("private diagnostic marker")
            return original_factory(audit_file=audit_file)

        before = dict(os.environ)

        with patch("api_runner.create_app", side_effect=fail_first_app):
            report = run_suite(suite)

        self.assertEqual(dict(os.environ), before)
        self.assertEqual(calls, 7)
        self.assertEqual(
            report["summary"],
            {"total": 7, "passed": 6, "failed": 1},
        )

        first = report["results"][0]
        self.assertFalse(first["passed"])
        self.assertIsNone(first["actual"])
        self.assertEqual(
            first["error"],
            "Scenario execution failed (RuntimeError).",
        )
        self.assertNotIn("private diagnostic marker", json.dumps(report))
        self.assertTrue(
            all(result["passed"] for result in report["results"][1:])
        )

    def test_wrong_expected_body_value_or_type_fails(self):
        for expected_tenant in ("company-b", 123):
            with self.subTest(expected_tenant=expected_tenant):
                suite = self.load_demo_suite()
                suite["scenarios"] = [suite["scenarios"][0]]
                suite["scenarios"][0]["expected"]["body"] = {
                    "tenant": expected_tenant
                }

                report = run_suite(suite)
                result = report["results"][0]

                self.assertEqual(report["summary"]["failed"], 1)
                self.assertFalse(result["passed"])
                self.assertIsNone(result["error"])
                self.assertEqual(result["actual"]["status_code"], 200)
                self.assertEqual(
                    result["actual"]["body"],
                    {"tenant": "company-a"},
                )


if __name__ == "__main__":
     unittest.main()