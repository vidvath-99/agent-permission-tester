import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

def read_audit_events(path):
    """Read JSON Lines audit records without modifying the input file."""
    events = []

    with Path(path).open("r", encoding="utf-8") as audit_file:
        for line_number, line in enumerate(audit_file, start=1):
            if not line.strip():
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on audit line {line_number}"
                ) from exc

            if not isinstance(event, dict):
                raise ValueError(
                    f"Audit line {line_number} must be an object"
                )

            events.append(event)

    return events


def evaluate_events(events, *, now=None, threshold=5, window_minutes=5):
    """Evaluate synthetic audit events; does not write or send alerts."""
    if type(threshold) is not int or threshold < 1:
        raise ValueError("threshold must be a positive integer")

    if type(window_minutes) is not int or window_minutes < 1:
        raise ValueError("window_minutes must be a positive integer")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")

    now = now.astimezone(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)
    blocked_calls = 0

    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each event must be an object")

        if event.get("mode") != "SECURE":
            continue

        if event.get("decision") != "deny":
            continue

        try:
            timestamp = datetime.fromisoformat(event["timestamp"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "SECURE deny event must have a valid timestamp"
            ) from exc

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("event timestamp must include a timezone")

        timestamp = timestamp.astimezone(timezone.utc)

        if window_start < timestamp <= now:
            blocked_calls += 1

    return {
        "rule_id": "secure_denials_threshold",
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "threshold": threshold,
        "blocked_calls": blocked_calls,
        "triggered": blocked_calls >= threshold,
    }


def write_alert_once(result, output_path):
    """Append a triggered result once per rule, window, and threshold."""
    if not result["triggered"]:
        return False

    identity_fields = (
        "rule_id",
        "window_start",
        "window_end",
        "threshold",
    )
    identity = tuple(result[field] for field in identity_fields)
    output_path = Path(output_path)
    needs_newline = False

    if output_path.exists():
        existing_alerts = read_audit_events(output_path)

        for alert in existing_alerts:
            if not all(field in alert for field in identity_fields):
                raise ValueError("Existing alert is missing identity fields")

        if any(
            tuple(alert[field] for field in identity_fields) == identity
            for alert in existing_alerts
        ):
            return False

        with output_path.open("rb") as existing_file:
            existing_file.seek(0, 2)
            if existing_file.tell():
                existing_file.seek(-1, 2)
                needs_newline = existing_file.read(1) != b"\n"

    record = json.dumps(result, allow_nan=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("a", encoding="utf-8", newline="\n") as alert_file:
        if needs_newline:
            alert_file.write("\n")
        alert_file.write(record + "\n")

    return True