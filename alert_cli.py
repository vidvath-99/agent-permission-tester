import argparse
import json
from datetime import datetime

from alert_evaluator import evaluate_audit_file


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate audit events and write local alerts.",
        allow_abbrev=False,
    )
    parser.add_argument("audit_path", help="Input audit JSON Lines file")
    parser.add_argument(
        "--output",
        default="alerts.jsonl",
        help="Alert JSON Lines output (default: alerts.jsonl)",
    )
    parser.add_argument("--threshold", type=int, default=5)
    parser.add_argument("--window-minutes", type=int, default=5)
    parser.add_argument(
        "--now",
        help="Fixed ISO 8601 evaluation time including a timezone",
    )
    args = parser.parse_args(argv)

    try:
        now = (
            datetime.fromisoformat(args.now)
            if args.now is not None
            else None
        )
        outcome = evaluate_audit_file(
            args.audit_path,
            args.output,
            now=now,
            threshold=args.threshold,
            window_minutes=args.window_minutes,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(outcome))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())