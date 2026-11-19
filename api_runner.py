import json
import os
import re
import secrets
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import create_app

def validate_suite(suite):
    if not isinstance(suite, dict):
        raise ValueError("The API suite must be a JSON object.")

    if set(suite) != {"schema_version", "name", "scenarios"}:
        raise ValueError(
            "The API suite needs exactly schema_version, name, and scenarios."
        )

    if type(suite["schema_version"]) is not int or suite["schema_version"] != 1:
        raise ValueError("Only integer schema_version 1 is supported.")

    if not isinstance(suite["name"], str) or not suite["name"].strip():
        raise ValueError("The suite needs a non-empty name.")

    scenarios = suite["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list.")

    required = {
        "id", "description", "credential", "method", "path", "expected"
    }
    seen = set()

    for index, scenario in enumerate(scenarios, start=1):
        label = f"Scenario {index}"

        if not isinstance(scenario, dict) or set(scenario) != required:
            raise ValueError(f"{label}: invalid scenario fields.")

        for field in ("id", "description", "credential", "method", "path"):
            value = scenario[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}: {field} must be a non-empty string.")

        if scenario["id"] in seen:
            raise ValueError(f"{label}: duplicate scenario id.")
        seen.add(scenario["id"])

        if scenario["credential"] not in ("company-a", "company-b", "none"):
            raise ValueError(f"{label}: unsupported credential alias.")

        if scenario["method"] not in ("GET", "DELETE"):
            raise ValueError(f"{label}: only GET and DELETE are supported.")

        if re.fullmatch(r"/tickets/[A-Za-z0-9_-]+", scenario["path"]) is None:
            raise ValueError(f"{label}: only local demo ticket paths are supported.")

        expected = scenario["expected"]
        if not isinstance(expected, dict) or set(expected) != {
            "status_code", "body"
        }:
            raise ValueError(f"{label}: expected needs status_code and body.")

        status = expected["status_code"]
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError(f"{label}: invalid expected HTTP status.")

        if not isinstance(expected["body"], dict):
            raise ValueError(f"{label}: expected body must be an object.")

    return suite


def load_suite(path):
    with Path(path).open(encoding="utf-8-sig") as source:
        return validate_suite(json.load(source))


def run_suite(suite):
    validate_suite(suite)
    results = []

    token_a = secrets.token_urlsafe(32)
    token_b = secrets.token_urlsafe(32)
    credentials = {
        "company-a": token_a,
        "company-b": token_b,
        "none": None,
    }

    with TemporaryDirectory(prefix="api-permission-runner-") as directory:
        for index, scenario in enumerate(suite["scenarios"]):
            expected = scenario["expected"]
            actual = None
            error = None
            passed = False

            try:
                with patch.dict(
                    os.environ,
                    {
                        "DEMO_TOKEN_A": token_a,
                        "DEMO_TOKEN_B": token_b,
                    },
                ):
                    app = create_app(
                        audit_file=Path(directory) / f"{index}.jsonl"
                    )

                token = credentials[scenario["credential"]]
                headers = {}
                if token is not None:
                    headers["Authorization"] = f"Bearer {token}"

                with TestClient(app) as client:
                    response = client.request(
                        scenario["method"],
                        scenario["path"],
                        headers=headers,
                        follow_redirects=False,
                    )

                body = response.json()
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object response.")

                body_matches = all(
                    key in body
                    and type(body[key]) is type(value)
                    and body[key] == value
                    for key, value in expected["body"].items()
                )

                actual = {
                    "status_code": response.status_code,
                    "body": {
                        key: body[key]
                        for key in expected["body"]
                        if key in body
                    },
                }
                passed = (
                    response.status_code == expected["status_code"]
                    and body_matches
                )
            except Exception as exc:
                error = f"Scenario execution failed ({type(exc).__name__})."

            results.append(
                {
                    "id": scenario["id"],
                    "description": scenario["description"],
                    "credential": scenario["credential"],
                    "method": scenario["method"],
                    "path": scenario["path"],
                    "expected": {
                        "status_code": expected["status_code"],
                        "body": dict(expected["body"]),
                    },
                    "actual": actual,
                    "passed": passed,
                    "error": error,
                }
            )

    passed_count = sum(result["passed"] for result in results)

    return {
        "report_type": "local_api_permissions",
        "report_version": 1,
        "suite": suite["name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "IN_PROCESS",
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
        },
        "results": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run permission scenarios against the in-process demo API."
    )
    parser.add_argument(
        "suite",
        type=Path,
        help="Path to an API scenario JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the JSON report to this file.",
    )
    args = parser.parse_args(argv)

    try:
        suite = load_suite(args.suite)
        report = run_suite(suite)
    except (OSError, ValueError) as exc:
        print(
            f"Could not load or run the API suite ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 2

    if args.output is not None:
        try:
            args.output.write_text(
                json.dumps(report, indent=2) + "\n",
                encoding="utf-8",
            )
        except (OSError, ValueError) as exc:
            print(
                f"Could not write the API report ({type(exc).__name__}).",
                file=sys.stderr,
            )
            return 2

    summary = report["summary"]
    print(
        f"API scenarios: {summary['total']} total, "
        f"{summary['passed']} passed, "
        f"{summary['failed']} failed."
    )

    for result in report["results"]:
        if not result["passed"]:
            reason = result["error"] or "HTTP expectation mismatch."
            print(f"FAIL {result['id']}: {reason}")

    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
