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
- Nine automated API permission and authentication tests.
- Twelve automated scenario-runner tests.
- Nine automated HTML-report tests.
- JSON-defined permission scenarios with expected decisions and denial reasons.
- Secure and deliberately broken scenario runs.
- JSON results and readable HTML reports showing expected versus actual outcomes.
- Tenant isolation between two fictional companies.
- Read-only permissions for the simulated agent.
- Access revocation checks.
- Unknown identity and tool rejection.
- A simulated malicious-instruction scenario.
- Timestamped audit logs in JSON Lines format.
- All four test suites, secure JSON scenarios, and HTML report generation
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
| test_api.py | Nine API permission and authentication tests |
| runner.py | Runs JSON permission scenarios and writes JSON results |
| test_runner.py | Twelve scenario-runner tests |
| scenarios/permissions.json | Five default gateway permission scenarios |
| report_html.py | Converts JSON scenario results into an HTML report |
| test_report_html.py | Nine HTML-report tests |
| requirements.txt | Pinned Python dependencies |
| README.md | Project documentation |
| evidence/secure-tests.txt | Saved passing gateway secure-mode results |
| evidence/broken-tests.txt | Saved intentional broken-mode failure |
| .github/workflows/tests.yml | Runs all four test suites, secure scenarios, and HTML generation |
| .gitignore | Git exclusion rules |
| audit.jsonl | Generated audit log; not tracked by Git |
| reports/ | Generated JSON results and HTML reports |

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
Ran 9 tests in ...

OK
```

These tests use an in-process test client; a separately running
API server is not required.

They cover allowed reads for both companies, cross-company access
blocking in both directions, denied deletion without state changes,
the health endpoint, missing and invalid credentials, matching
responses for missing and cross-company tickets, and access revocation.

Passing these tests does not establish production readiness.

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

GitHub Actions runs all four test suites, the secure JSON scenarios,
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
python -m unittest -v test_runner
python runner.py scenarios/permissions.json --report reports/secure-results.json
python -m unittest -v test_report_html
python report_html.py reports/secure-results.json --output reports/secure-results.html
```

The automated test suites contain 37 tests:

- Seven gateway tests.
- Nine API tests.
- Twelve scenario-runner tests.
- Nine HTML-report tests.

The secure JSON scenario run separately checks five scenarios.

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
Both the seven-test secure gateway suite and the nine-test API
suite have passed in GitHub Actions.

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
- The seven gateway tests and nine API tests cover the listed
  scenarios; they do not establish complete security or
  production readiness.
