from datetime import datetime, timedelta, timezone


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
