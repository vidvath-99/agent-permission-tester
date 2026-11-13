import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from gateway import Gateway


def load_suite(path):
    with Path(path).open(encoding="utf-8-sig") as source:
        suite = json.load(source)

    if not isinstance(suite, dict):
        raise ValueError("The scenario file must contain a JSON object.")

    if type(suite.get("schema_version")) is not int:
        raise ValueError("schema_version must be the integer 1.")

    if suite["schema_version"] != 1:
        raise ValueError("Only schema_version 1 is supported.")

    if not isinstance(suite.get("name"), str) or not suite["name"].strip():
        raise ValueError("The suite needs a non-empty name.")

    scenarios = suite.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list.")

    seen_ids = set()

    for index, scenario in enumerate(scenarios, start=1):
        if not isinstance(scenario, dict):
            raise ValueError(f"Scenario {index} must be an object.")

        for field in ("id", "description", "agent", "tool", "ticket"):
            value = scenario.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Scenario {index}: {field} must be a non-empty string."
                )

        scenario_id = scenario["id"]
        if scenario_id in seen_ids:
            raise ValueError(f"Duplicate scenario id: {scenario_id}")
        seen_ids.add(scenario_id)

        expected = scenario.get("expected")
        if not isinstance(expected, dict):
            raise ValueError(f"{scenario_id}: expected must be an object.")

        if set(expected) != {"decision", "reason"}:
            raise ValueError(
                f"{scenario_id}: expected needs exactly decision and reason."
            )

        decision = expected["decision"]
        reason = expected["reason"]

        if decision not in ("allow", "deny"):
            raise ValueError(f"{scenario_id}: invalid expected decision.")

        if decision == "allow" and reason is not None:
            raise ValueError(f"{scenario_id}: allow requires a null reason.")

        if decision == "deny":
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(
                    f"{scenario_id}: deny requires a non-empty reason."
                )

    return suite


def run_suite(suite, *, broken=False):
    results = []

    with TemporaryDirectory(prefix="permission-runner-") as temp_dir:
        for index, scenario in enumerate(suite["scenarios"]):
            gateway = Gateway(
                broken=broken,
                audit_file=Path(temp_dir) / f"{index}.jsonl",
            )

            error = None

            try:
                gateway.call(
                    scenario["agent"],
                    scenario["tool"],
                    scenario["ticket"],
                )
                actual = {"decision": "allow", "reason": None}
            except PermissionError as exc:
                actual = {"decision": "deny", "reason": str(exc)}
            except Exception as exc:
                actual = None
                error = f"{type(exc).__name__}: {exc}"

            passed = error is None and actual == scenario["expected"]

            results.append(
                {
                    "id": scenario["id"],
                    "description": scenario["description"],
                    "expected": scenario["expected"],
                    "actual": actual,
                    "passed": passed,
                    "error": error,
                    "audit": gateway.audit,
                }
            )

    passed_count = sum(result["passed"] for result in results)

    return {
        "report_version": 1,
        "suite": suite["name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "BROKEN" if broken else "SECURE",
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "failed": len(results) - passed_count,
        },
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run JSON permission scenarios against the demo gateway."
    )
    parser.add_argument("scenario_file", type=Path)
    parser.add_argument(
        "--broken",
        action="store_true",
        help="Deliberately disable tenant isolation.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Destination for the JSON results report.",
    )
    args = parser.parse_args()

    try:
        suite = load_suite(args.scenario_file)

        if args.report.resolve() == args.scenario_file.resolve():
            raise ValueError("The report must not overwrite the scenario file.")

        report = run_suite(suite, broken=args.broken)
        report["source"] = str(args.scenario_file)

        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"Runner error: {exc}", file=sys.stderr)
        return 2

    print(f"Suite: {report['suite']}")
    print(f"Mode: {report['mode']}")

    for result in report["results"]:
        label = "PASS" if result["passed"] else "FAIL"
        print(f"{label}: {result['id']}")

        if not result["passed"]:
            print(f"  Expected: {result['expected']}")
            print(f"  Actual:   {result['actual']}")
            if result["error"]:
                print(f"  Error:    {result['error']}")

    summary = report["summary"]
    print(
        f"\nTotal: {summary['total']} | "
        f"Passed: {summary['passed']} | "
        f"Failed: {summary['failed']}"
    )
    print(f"Report: {args.report}")

    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())