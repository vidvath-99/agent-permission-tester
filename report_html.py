import argparse
import json
import sys
from html import escape
from pathlib import Path


def text(value):
    if value is None:
        return "—"
    return escape(str(value))


def format_decision(value):
    if value is None:
        return "No decision"

    decision = text(value["decision"])
    reason = text(value["reason"])
    return f"{decision}<br><small>Reason: {reason}</small>"


def render_report(report):
    rows = []

    for result in report["results"]:
        passed = result["passed"]
        status = "PASS" if passed else "FAIL"
        css_class = "pass" if passed else "fail"

        rows.append(
            f"""
            <tr>
              <td>
                <strong>{text(result["id"])}</strong>
                <br><small>{text(result["description"])}</small>
              </td>
              <td class="{css_class}">{status}</td>
              <td>{format_decision(result["expected"])}</td>
              <td>{format_decision(result["actual"])}</td>
              <td>{text(result["error"])}</td>
            </tr>
            """
        )

    summary = report["summary"]
    table_rows = "\n".join(rows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{text(report["suite"])} — Permission Report</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      max-width: 1200px;
      margin: 32px auto;
      padding: 0 20px;
      color: #172033;
      background: #f5f7fb;
    }}
    h1 {{ margin-bottom: 8px; }}
    .metadata {{ line-height: 1.7; overflow-wrap: anywhere; }}
    .summary {{
      padding: 16px;
      margin: 24px 0;
      background: white;
      border: 1px solid #ccd3df;
      border-radius: 8px;
    }}
    .table-wrap {{ overflow-x: auto; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
    }}
    th, td {{
      padding: 14px;
      border: 1px solid #ccd3df;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{ background: #e8edf5; }}
    small {{ color: #465269; line-height: 1.6; }}
    .pass {{ color: #176534; font-weight: bold; }}
    .fail {{ color: #a31515; font-weight: bold; }}
    footer {{ margin-top: 24px; color: #465269; }}
  </style>
</head>
<body>
  <h1>Permission Regression Report</h1>
  <h2>{text(report["suite"])}</h2>

  <div class="metadata">
    <div>Mode: {text(report["mode"])}</div>
    <div>Generated: {text(report["timestamp"])}</div>
    <div>Scenario source: {text(report.get("source"))}</div>
  </div>

  <div class="summary">
    Total: {text(summary["total"])} |
    Passed: {text(summary["passed"])} |
    Failed: {text(summary["failed"])}
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Scenario</th>
          <th>Result</th>
          <th>Expected</th>
          <th>Actual</th>
          <th>Execution error</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

  <footer>
    PASS means the observed decision and reason matched the expectation.
    A denied request can therefore be a passing test.
    This local demo report does not establish production readiness.
  </footer>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(
        description="Convert a runner JSON report into an HTML report."
    )
    parser.add_argument("input_report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.input_report.resolve() == args.output.resolve():
            raise ValueError("Output must not overwrite the input report.")

        with args.input_report.open(encoding="utf-8-sig") as source:
            report = json.load(source)

        if not isinstance(report, dict):
            raise ValueError("The report must contain a JSON object.")

        if type(report.get("report_version")) is not int:
            raise ValueError("report_version must be the integer 1.")

        if report["report_version"] != 1:
            raise ValueError("Only report_version 1 is supported.")

        html = render_report(report)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"HTML report error: {exc}", file=sys.stderr)
        return 2

    print(f"HTML report saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())