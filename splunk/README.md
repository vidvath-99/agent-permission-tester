
# Splunk Integration

This local demonstration monitors the gateway's JSON Lines audit log
with Splunk Enterprise. It uses synthetic permission-test events,
not real customer data.


## Verified Setup

- Input type: File Monitor.
- File: audit.jsonl in the project folder.
- Continuously Monitor: Yes.
- Source type: _json.
- Index: agent_permissions.

Create the agent_permissions Events index before configuring the input.

In Splunk Web, use Settings > Data Inputs > Files & Directories > New.
Select the full path to the project's audit.jsonl file, enable continuous
monitoring, select _json, and choose agent_permissions as the index.

Review the event boundaries and timestamps before submitting the input.

The file must be accessible to the Splunk process. This setup was tested
with Splunk Enterprise and the project on the same Windows computer.

## Verify Collection

Run the secure gateway demonstration from the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe .\demo.py
```

In Splunk Search & Reporting, select All time and run:

```spl
index=agent_permissions sourcetype=_json
| table _time agent tool ticket decision reason mode
| sort - _time
```

Check for new timestamps after running the demonstration. A successful
test run alone does not confirm ingestion; verify the new events in Splunk.

## Blocked Calls Report

Run the query in blocked_calls_by_reason.spl with All time selected.

The query counts denied calls in SECURE mode, grouped by denial reason.
It excludes BROKEN-mode events.

Save the search as a report named:

Agent_Permissions_Blocked_Calls_by_Reason

Enable the time-range picker when saving the report.

## Interpretation and Limitations

- Blocked calls are audit events, not failed tests.
- Expected permission denials are successful security-control outcomes.
- One test can generate multiple audit events.
- Counts accumulate across runs and depend on the selected time range.
- Synthetic test blocks are not evidence of real attacks.
- This report summarizes logged decisions; it does not independently
  prove that every allowed decision was authorized.
- This setup does not configure scheduled alerts or external notifications.
- The SPL file preserves the query but does not automatically install the
  Splunk index, file input, or saved report.