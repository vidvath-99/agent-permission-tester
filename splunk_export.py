"""Convert permission-test JSON reports into JSONL events for Splunk."""
import argparse
import json
from pathlib import Path


def events_from_report(report):
    for result in report["results"]:
        base = {
            "suite": report["suite"],
            "run_mode": report["mode"],
            "scenario": result["id"],
            "expected_decision": result["expected"]["decision"],
            "expected_reason": result["expected"]["reason"],
            "passed": result["passed"],
            "error": result["error"],
        }
        for entry in result["audit"]:
            yield {
                "timestamp": entry["timestamp"],
                **base,
                "agent": entry["agent"],
                "tool": entry["tool"],
                "ticket": entry["ticket"],
                "decision": entry["decision"],
                "reason": entry["reason"],
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    count = 0
    with args.output.open("w", encoding="utf-8") as out:
        for path in args.reports:
            report = json.loads(path.read_text(encoding="utf-8"))
            for event in events_from_report(report):
                out.write(json.dumps(event) + "\n")
                count += 1
    print(f"Wrote {count} events to {args.output}")


if __name__ == "__main__":
    main()