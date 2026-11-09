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

- Seven automated permission tests.
- Tenant isolation between two fictional companies.
- Read-only permissions for the simulated agent.
- Access revocation checks.
- Unknown identity and tool rejection.
- A simulated malicious-instruction scenario.
- Timestamped audit logs in JSON Lines format.
- Automated secure-mode tests through GitHub Actions.

## Requirements

- Python 3.13 is used in CI.
- No additional Python packages.
- No AI model or API key required.

## Project Files

| Path | Purpose |
|---|---|
| demo.py | Permission gateway, synthetic tickets, and tests |
| README.md | Project documentation |
| evidence/secure-tests.txt | Saved passing secure-mode results |
| evidence/broken-tests.txt | Saved intentional broken-mode failure |
| .github/workflows/tests.yml | GitHub Actions test workflow |
| .gitignore | Excludes generated logs, backups, and local files |
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

## Demonstrate a Security Regression

```powershell
py -3 demo.py --broken
```

This disables the tenant-isolation check for that run.
Company A's agent can then read Company B's ticket, INC-002.

Expected summary:

```text
FAIL: test_cross_company_read_blocked
...
FAILED (failures=1)
```

This failure is intentional. The other six tests should pass.
Broken mode exits with a nonzero status because a test fails.

Run without `--broken` to return to secure mode.
No code changes are required.

## Automated Testing

GitHub Actions runs the secure-mode tests on:

- Pushes to main.
- Pull requests targeting main.
- Manual workflow dispatch.

The workflow uses Python 3.13 and runs:

```sh
python -u demo.py
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
A secure-mode run has also passed in GitHub Actions.

## Limitations

- This is an educational simulation, not a production system.
- Agent identities and permissions are hard-coded in memory.
- An agent identifier is supplied directly; the demo does not
  implement authentication or verify the caller's identity.
- No real AI model processes the ticket content.
- The malicious-instruction test checks that ticket text does
  not grant delete permission; it does not evaluate an AI
  model's resistance to prompt injection.
- Audit logs are local append-only writes, not tamper-proof
  storage.
- Seven passing tests cover the listed scenarios; they do not
  establish complete security.
