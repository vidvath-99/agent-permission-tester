import argparse
import json
import sys

LABELS = {
    "passed": "Passed",
    "failed": "Failed",
    "error": "Error",
}
ROWS = [
    "Passed",
    "Failed",
    "Error",
    "Not requested",
    "Not recorded",
    "Unrecognized",
]
HIDDEN_WHEN_ZERO = {"Not recorded", "Unrecognized"}


def classify(result):
    if "state_verification" not in result:
        return "Not recorded"
    verification = result["state_verification"]
    if verification is None:
        return "Not requested"
    status = (
        verification.get("status")
        if isinstance(verification, dict)
        else None
    )
    return LABELS.get(status, "Unrecognized")


def render_summary(report):
    results = report.get("results", [])
    summary = report.get("summary", {})
    counts = dict.fromkeys(ROWS, 0)
    for result in results:
        counts[classify(result)] += 1

    lines = [
        "## API permission results",
        "",
        (
            f"Scenarios: {summary.get('total', len(results))} total, "
            f"{summary.get('passed', 0)} passed, "
            f"{summary.get('failed', 0)} failed."
        ),
        "",
        "| State verification | Scenarios |",
        "| --- | ---: |",
    ]
    for label in ROWS:
        if counts[label] == 0 and label in HIDDEN_WHEN_ZERO:
            continue
        lines.append(f"| {label} | {counts[label]} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a Markdown summary of an API results report."
    )
    parser.add_argument("report", help="Path to the API results JSON.")
    args = parser.parse_args(argv)

    try:
        with open(args.report, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, ValueError):
        print("Could not read the API results report.", file=sys.stderr)
        return 1
    if not isinstance(report, dict):
        print("Could not read the API results report.", file=sys.stderr)
        return 1

    sys.stdout.write(render_summary(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())