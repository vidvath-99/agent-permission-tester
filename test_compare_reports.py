import json

from compare_reports import build_markdown, main


def report(mode, passed):
    return {
        "mode": mode,
        "timestamp": "t",
        "summary": {"total": 1, "passed": int(passed), "failed": int(not passed)},
        "results": [{
            "id": "cross-company-read",
            "expected": {"decision": "deny", "reason": "tenant_mismatch"},
            "actual": (
                {"decision": "deny", "reason": "tenant_mismatch"} if passed
                else {"decision": "allow", "reason": None}
            ),
            "passed": passed,
        }],
    }


def test_marks_fixed_scenario():
    text = build_markdown(report("BROKEN", False), report("SECURE", True))
    assert "| cross-company-read |" in text
    assert "Fixed" in text


def test_missing_file_returns_error(tmp_path):
    missing = tmp_path / "none.json"
    assert main(["--before", str(missing), "--after", str(missing)]) == 1


def test_writes_report(tmp_path):
    before, after = tmp_path / "b.json", tmp_path / "a.json"
    before.write_text(json.dumps(report("BROKEN", False)), encoding="utf-8")
    after.write_text(json.dumps(report("SECURE", True)), encoding="utf-8")
    out = tmp_path / "out.md"
    assert main(["--before", str(before), "--after", str(after), "--output", str(out)]) == 0
    assert "Fixed" in out.read_text(encoding="utf-8")