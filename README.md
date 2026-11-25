# AI-Agent Permission Regression Tester

A Python cybersecurity demo that tests permission boundaries for
simulated AI-agent tool calls.

The scenario uses a simulated SOC assistant accessing incident
tickets belonging to two fictional companies.

## Project Goal

Detect security regressions: changes that accidentally weaken
previously working permission checks.

A deliberately broken mode demonstrates how the tests detect
unauthorised cross-company access.

## Features

- Seven automated gateway permission tests.
- Ten automated API permission and authentication tests.
- Twelve automated scenario-runner tests.
- Seventeen automated HTML-report tests, including API rendering and CLI integration.
- Thirty-three automated audit-reader, evaluator, alert-writer, and
  file-processing tests.
- Six automated alert CLI tests.
- Twenty-one automated API scenario validation, execution, and regression tests.
- Five automated API-runner CLI tests.
- Local JSON Lines alerts with exact-evaluation duplicate prevention.
- JSON-defined permission scenarios with expected decisions and denial reasons.
- Secure and deliberately broken scenario runs.
- JSON results and readable HTML reports showing expected versus actual outcomes.
- Tenant isolation between two fictional companies.
- Read-only permissions for the simulated agent.
- Access revocation checks.
- Unknown identity and tool rejection.
- A simulated malicious-instruction scenario.
- Timestamped audit logs in JSON Lines format.
- All eight test suites, secure JSON scenarios, and HTML report generation
  run automatically through GitHub Actions.


## Requirements

- Python 3.13 is used in CI.
- Python dependencies are pinned in requirements.txt.
- No AI model or external AI API key is required.

## Install Dependencies

From the project folder in Windows PowerShell, using the existing
virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

## Project Files

| Path | Purpose |
|---|---|
| gateway.py | Permission checks, synthetic tickets, and audit logging |
| demo.py | Seven gateway tests with secure and deliberately broken modes |
| api.py | FastAPI application factory and bearer-token authentication |
| test_api.py | Ten API permission and authentication tests |
| api_runner.py | Runs local API scenarios with optional JSON reports |
| test_api_runner.py | Twenty-one API scenario validation, execution, and regression tests |
| test_api_runner_cli.py | Five API-runner CLI tests |
| scenarios/api-permissions.json | Seven default API scenarios |
| runner.py | Runs JSON permission scenarios and writes JSON results |
| test_runner.py | Twelve scenario-runner tests |
| scenarios/permissions.json | Five default gateway permission scenarios |
| report_html.py | Converts JSON scenario results into an HTML report |
| test_report_html.py | Ten HTML-report tests |
| test_report_html_api.py | Seven API HTML-rendering and CLI integration tests |
| requirements.txt | Pinned Python dependencies |
| README.md | Project documentation |
| evidence/secure-tests.txt | Saved passing gateway secure-mode results |
| evidence/broken-tests.txt | Saved intentional broken-mode failure |
| .gitignore | Git exclusion rules |
| audit.jsonl | Generated audit log; not tracked by Git |
| reports/ | Generated JSON results and HTML reports |
| alert_evaluator.py | Reads audit records, evaluates denial thresholds, and writes deduplicated local alerts |
| test_alert_evaluator.py | Thirty-three reader, evaluator, writer, and file-processing tests |
| alert_cli.py | Command-line interface for audit evaluation and local alert writing |
| test_alert_cli.py | Six command-line interface tests |
| alerts.jsonl | Default generated alert output; not tracked by Git |
| .github/workflows/tests.yml | Runs all eight test suites, secure scenarios, and HTML generation |

## Run the Secure Version

From the project folder in Windows PowerShell:

```powershell
py -3 demo.py
```

On systems where Python is available as `python`:

```sh
python demo.py
```

Expected summary:

```text
Mode: SECURE
...
Ran 7 tests in ...

OK
```


## Run the API Tests

From the project folder in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_api
```

Expected summary:

```text
Ran 10 tests in ...

OK
```

These tests use an in-process test client; a separately running
API server is not required.

They cover allowed reads for both companies, cross-company access
blocking in both directions, denied deletion without state changes,
the health endpoint, missing and invalid credentials, matching
responses for missing and cross-company tickets, access revocation,
and explicit audit-file selection.

Passing these tests does not establish production readiness.

## Run Local API Scenarios

Run the seven default API scenarios from Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe .\api_runner.py .\scenarios\api-permissions.json
```

Expected output:

```text
API scenarios: 7 total, 7 passed, 0 failed.
```

The scenarios check allowed own-company reads for both companies,
blocked cross-company reads in both directions, rejection of a request
without credentials, a nonexistent-ticket response, and rejection of
deletion with read-only permissions.

The deletion scenario checks both the HTTP rejection status and
preservation of API-visible ticket state using the optional
`verify_unchanged` configuration:

```json
{
  "id": "company-a-delete-denied",
  "description": "A denied deletion leaves API-visible ticket state unchanged.",
  "credential": "company-a",
  "method": "DELETE",
  "path": "/tickets/INC-001",
  "verify_unchanged": {
    "credential": "company-a"
  },
  "expected": {
    "status_code": 403,
    "body": {}
  }
}
```

The runner uses the credential specified in `verify_unchanged` to read
the ticket before and after the DELETE request. It compares the full
JSON responses, rather than only the fields in `expected.body`.
The scenario fails if the ticket becomes unreadable or its API-visible
state changes, even when the DELETE returns the expected rejection status.

This optional check is for DELETE scenarios expecting a 4xx response.
The verification credential must be authorized to read the ticket.

The check compares API-visible state at the two read points. It does
not establish that every internal state or external side effect remained
unchanged.

The runner uses an in-process test client. It does not require a running
API server and does not accept arbitrary URLs. Each scenario gets a
fresh application and a temporary audit file.

Scenario files use credential aliases: company-a, company-b, or none.
The runner generates temporary demo tokens rather than storing tokens
in the scenario file.

Supported requests are GET and DELETE against local /tickets/{id}
paths. An expected HTTP status must match exactly. Each field listed
in expected.body must be present and match its expected value and
top-level type; additional response fields are allowed.

To save a JSON report:

```powershell
New-Item -ItemType Directory -Force .\reports | Out-Null
.\.venv\Scripts\python.exe .\api_runner.py .\scenarios\api-permissions.json --output .\reports\api-results.json
```

The output directory must already exist. An existing output file is
replaced. The reports directory is excluded from version control.

Exit codes:

- 0: All scenarios passed.
- 1: At least one scenario failed.
- 2: Invalid arguments or a handled input/output error.

API reports use a separate format from gateway scenario reports.
The report_html.py converter supports both formats.

### State Verification Results

Every API scenario result includes `state_verification`:

| JSON value | Meaning |
|---|---|
| `null` | State verification was not requested. |
| `{"status": "passed"}` | Verification confirmed unchanged API-visible state. |
| `{"status": "failed"}` | The after-read was unsuccessful or API-visible state changed. |
| `{"status": "error"}` | Requested verification could not be completed because execution encountered an error. |

The verification object contains only `status`, not snapshots or tokens.

API HTML reports display one of these labels:

- State verification: Not requested.
- State verification: Passed.
- State verification: Failed.
- State verification: Error.

Older API results missing the field display
"State verification: Not recorded.", which is distinct from verification
not being requested. Gateway reports omit these labels.

A scenario passes only when the expected HTTP status and checked
response-body fields match and any requested state verification passes.
A passed state verification alone does not establish that the scenario passed.

To convert the saved API JSON report to HTML and open it:

```powershell
.\.venv\Scripts\python.exe .\report_html.py .\reports\api-results.json --output .\reports\api-results.html
Start-Process ".\reports\api-results.html"
```

Generating HTML displays saved results; it does not rerun the scenarios
or state verification.


This is a sequential local demo harness, not a concurrent service or
a production security assessment.

## Demonstrate a Security Regression

```powershell
.\.venv\Scripts\python.exe -u demo.py --broken
```

This disables the tenant-isolation check for that run.
Company A's agent can then read Company B's ticket, INC-002.

Expected summary:

```text
FAIL: test_cross_company_read_blocked
...
FAILED (failures=1)
```

This failure is intentional. The other six gateway tests should pass.
Broken mode exits with a nonzero status because a test fails.

Run without --broken to return to secure mode.
No code changes are required.


## Automated Testing

GitHub Actions runs all eight test suites, the secure JSON scenarios,
and HTML report generation on:

- Pushes to main.
- Pull requests targeting main.
- Manual workflow dispatch.

The workflow uses Python 3.13 and runs:

```sh
python -m pip install -r requirements.txt
python -m pip check
python -u demo.py
python -m unittest -v test_api
python -m unittest -v test_api_runner test_api_runner_cli
python -c "from pathlib import Path; Path('reports').mkdir(exist_ok=True)"
python api_runner.py scenarios/api-permissions.json --output reports/api-results.json
python report_html.py reports/api-results.json --output reports/api-results.html
python -m unittest -v test_runner
python -m unittest -v test_alert_evaluator
python -m unittest -v test_alert_cli
python runner.py scenarios/permissions.json --report reports/secure-results.json
python -m unittest -v test_report_html test_report_html_api
python report_html.py reports/secure-results.json --output reports/secure-results.html
```

The HTML renderer supports both gateway and local API permission reports.
API reports display the request method, path, credential alias, expected
and actual HTTP status, and checked response-body fields. The displayed
body contains only fields checked by the scenario, not necessarily the
complete API response. An expected denial can be a passing test.

Permission tests workflow runs attempt to upload available gateway
and API JSON/HTML reports as an artifact named permission-reports,
retained for seven days, even when an earlier step fails, provided
the workflow is not cancelled.

HTML generation runs when the corresponding JSON report exists.
An early failure may prevent some reports from being created.
The upload step fails if none of the configured report files exist.

Open the workflow run in GitHub Actions and download the artifact
from its Artifacts section.

The automated test suites contain 111 tests: 104 discovered by
`python -m unittest discover`, plus seven gateway tests run separately
through `demo.py`:

- Seven gateway tests.
- Ten API tests.
- Twelve scenario-runner tests.
- Seventeen HTML-report tests, including API rendering and CLI integration.
- Thirty-three audit-reader, evaluator, alert-writer, and file-processing tests.
- Six alert CLI tests.
- Twenty-one API scenario validation, execution, and regression tests.
- Five API-runner CLI tests.

The secure gateway JSON scenario run separately checks five scenarios.
The API scenario run separately checks seven scenarios.

Runner tests include checks that deliberately broken mode detects
cross-company access and returns a failure status. However, the workflow
does not run the standalone broken demonstration as a separate step,
because that demonstration intentionally exits with code 1.


## Run JSON Scenarios and Generate HTML Reports

From the project folder in Windows PowerShell, run the secure scenarios:

```powershell
.\.venv\Scripts\python.exe .\runner.py .\scenarios\permissions.json --report .\reports\secure-results.json
.\.venv\Scripts\python.exe .\report_html.py .\reports\secure-results.json --output .\reports\secure-results.html
Start-Process ".\reports\secure-results.html"
```

Expected result: five scenarios pass, with zero failures.

A scenario passes when the actual decision and denial reason match
the expected outcome. An expected denial is therefore a passing result
when the gateway correctly blocks the action.

To demonstrate a tenant-isolation regression, use separate report files:

```powershell
.\.venv\Scripts\python.exe .\runner.py .\scenarios\permissions.json --broken --report .\reports\broken-results.json
$runnerExitCode = $LASTEXITCODE
Write-Output "Broken runner exit code: $runnerExitCode"
.\.venv\Scripts\python.exe .\report_html.py .\reports\broken-results.json --output .\reports\broken-results.html
Start-Process ".\reports\broken-results.html"
```

Expected result: four scenarios pass and cross-company-read fails.
That scenario expects deny with tenant_mismatch, but broken mode
returns allow.

The broken runner exits with code 1 because it detected a regression.
This failure is intentional; the JSON results can still be converted
into an HTML report.

The HTML report shows the mode, scenario totals, expected and actual
outcomes, and any execution errors. Generating HTML does not fix or
rerun the permission checks.

The secure and broken reports use different filenames, so generating
the broken report does not overwrite the secure report.

## Audit Reader and Alert Evaluator

The core reading and evaluation functions in alert_evaluator.py are:

- read_audit_events(path) reads JSON Lines records without modifying the
  input file. Blank lines are skipped. Invalid JSON and non-object records
  are rejected with a line number; a missing file raises an error.
- evaluate_events(events, ...) counts SECURE-mode deny decisions within a
  configurable time window. The default threshold is five denials in five
  minutes, and reaching the threshold triggers the result.

The evaluator excludes events exactly at the window start and includes
events exactly at the evaluation time. Future events are excluded.
Relevant events must have valid timezone-aware timestamps.

Run the tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_alert_evaluator
```

### Local Alert Writing and CLI

The module also supports writing triggered evaluations to a local JSON
Lines alert file. File-processing tests cover audit-input preservation,
invalid input, duplicate evaluations, and rejection of matching input
and output paths.

The alert_cli.py script provides a command-line interface:

```powershell
.\.venv\Scripts\python.exe .\alert_cli.py --help
```

To evaluate an existing audit log and write triggered alerts:

```powershell
.\.venv\Scripts\python.exe .\alert_cli.py .\audit.jsonl --output .\alerts.jsonl
```

Duplicate prevention applies to an exact evaluation identity, not a
cooldown period. Evaluations with different window boundaries can
produce separate alerts even when their windows overlap.

The default alerts.jsonl output is excluded from version control.

Run the evaluator and CLI tests together:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_alert_evaluator test_alert_cli
```

The combined suite contains 39 tests: 33 reader, evaluator, writer,
and file-processing tests, plus six CLI tests.

This is a local demonstration, separate from the saved Splunk query.
It does not provide a background scheduler, notification delivery,
tamper-proof storage, or guarantees for concurrent alert writers.


## Splunk Integration

The gateway's JSON Lines audit log can be monitored with Splunk Enterprise.

The local demonstration includes verified collection of newly appended
events and a saved report summarizing secure-mode denials by reason.
These are synthetic permission-test events, not confirmed real attacks.

See [Splunk setup and verification](splunk/README.md) for configuration
steps and limitations. The report query is saved in
[splunk/blocked_calls_by_reason.spl](splunk/blocked_calls_by_reason.spl).


## View Audit Logs

```powershell
Get-Content .\audit.jsonl -Tail 9
```

Each entry records:

- UTC timestamp.
- Secure or broken mode.
- Agent identifier.
- Requested tool.
- Ticket identifier.
- Allow or deny decision.
- Denial reason, where applicable.

The log is saved beside demo.py.
Each run appends entries rather than replacing old ones.
The generated log is excluded from version control.

## Test Coverage

| Test | Expected secure behaviour |
|---|---|
| Own-company read | Allowed |
| Cross-company read | Denied |
| Delete with read-only permissions | Denied; tickets unchanged |
| Read after access revocation | Denied |
| Unknown tool | Denied |
| Delete after a simulated malicious instruction | Denied |
| Unknown identity | Denied |

A passing secure-mode run generates nine permission events:
the revocation test and malicious-instruction test each make
two requests; the other five tests each make one.

## Demonstrated Results

Secure mode:

- All seven tests passed.
- Cross-company access was denied with tenant_mismatch.

Broken mode:

- The cross-company test failed.
- The other six tests passed.
- The cross-company read was allowed because tenant isolation
  was deliberately disabled.

The audit log records what the gateway decided.
The tests check those decisions against expected behaviour.

Saved test outputs are available in the evidence directory.
The expanded test suites and report-generation workflow passed in
GitHub Actions in post-merge run #39 for commit 82302da.
The deliberate gateway failure was also verified to leave CI failing
while preserving downloadable reports.

## Limitations

- This is an educational simulation, not a production system.
- Agent identities and permissions are hard-coded in memory.
- Direct gateway calls accept an agent identifier without authentication.
  The API separately authenticates bearer tokens and maps them to
  demo identities.
- API authentication uses two static environment-configured tokens,
  not a production identity provider or token-management system.
- Access revocation is tested by changing in-memory gateway state;
  there is no API endpoint for revoking access.
- No real AI model processes the ticket content.
- The malicious-instruction test checks that ticket text does
  not grant delete permission; it does not evaluate an AI
  model's resistance to prompt injection.
- Audit logs are local append-only writes, not tamper-proof
  storage.
- The seven gateway tests and ten API tests cover the listed
  scenarios; they do not establish complete security or
  production readiness.
