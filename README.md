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
- Tenant isolation between two fictional companies.
- Read-only permissions for the simulated agent.
- Access revocation checks.
- Unknown identity and tool rejection.
- A simulated malicious-instruction scenario.
- Timestamped audit logs in JSON Lines format.
- Both test suites run automatically through GitHub Actions.

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
| requirements.txt | Pinned Python dependencies |
| README.md | Project documentation |
| evidence/secure-tests.txt | Saved passing gateway secure-mode results |
| evidence/broken-tests.txt | Saved intentional broken-mode failure |
| .github/workflows/tests.yml | GitHub Actions workflow running both test suites |
| .gitignore | Git exclusion rules |
| audit.jsonl | Generated audit log; not tracked by Git |

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

GitHub Actions runs both the secure gateway tests and the API tests on:

- Pushes to main.
- Pull requests targeting main.
- Manual workflow dispatch.

The workflow uses Python 3.13 and runs:

```sh
python -m pip install -r requirements.txt
python -m pip check
python -u demo.py
python -m unittest -v test_api
```

Broken mode is not included in the current CI workflow because
its test failure is intentional.

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
