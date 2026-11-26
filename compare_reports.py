import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("mode", "timestamp", "summary", "results"):
        if key not in data:
            raise ValueError(f"{path}: missing '{key}'.")
    return data


def fmt(value):
    if value is None:
        return "-"
    reason = value.get("reason")
    return f"{value['decision']} ({reason})" if reason else value["decision"]


def verdict(before, after):
    if after is None:
        return "Missing in after run"
    if not after["passed"]:
        return "Still failing"
    return "Fixed" if not before["passed"] else "Unchanged"


def build_markdown(before, after):
    after_by_id = {r["id"]: r for r in after["results"]}
    b, a = before["summary"], after["summary"]
    lines = [
        "# Before and After: Permission Test Results",
        "",
        f"- Before: {before['mode']} run, {b['passed']}/{b['total']} passed ({before['timestamp']})",
        f"- After: {after['mode']} run, {a['passed']}/{a['total']} passed ({after['timestamp']})",
        "",
        "| Scenario | Expected | Before | After | Result |",
        "|---|---|---|---|---|",
    ]
    for item in before["results"]:
        match = after_by_id.get(item["id"])
        lines.append(
            f"| {item['id']} | {fmt(item['expected'])} | {fmt(item['actual'])} "
            f"| {fmt(match['actual']) if match else '-'} | {verdict(item, match)} |"
        )
    lines += [
        "",
        "## Limitations",
        "",
        "- Covers only the scenarios in these two reports.",
        "- Runs against a simulated gateway, not a production system.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default=ROOT / "reports" / "broken-results.json")
    parser.add_argument("--after", default=ROOT / "reports" / "secure-results.json")
    parser.add_argument("--output", default=ROOT / "reports" / "before-after.md")
    args = parser.parse_args(argv)
    try:
        text = build_markdown(load(args.before), load(args.after))
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    Path(args.output).write_text(text, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())