# AI-Agent Permission Regression Tester

A Python cybersecurity demo that checks whether permission
boundaries work correctly for simulated AI-agent tool calls.

The scenario uses a SOC assistant accessing incident tickets
belonging to two fictional companies.

## Project Goal

Detect security regressions: changes that accidentally weaken
previously working permission checks.

The project includes a deliberately broken mode to demonstrate
how an automated test detects unauthorised cross-company access.

## Features

- Seven automated permission tests.
- Tenant isolation between two fictional companies.
- Read-only tool permissions.
- Access revocation checks.
- Unknown identity and tool rejection.
- Simulated malicious-instruction scenario.
- Timestamped audit logs saved in JSON Lines format.

## Requirements

- Python 3.
- No additional Python packages.
- No AI model or API key required.

## Project Files

- demo.py — permission gateway, synthetic tickets, and tests.
- audit.jsonl — generated audit log, created when tests run.
- README.md — project documentation.

## Run the Secure Version

From the project folder in Windows PowerShell:

```powershell
py -3 demo.py
```

Expected result:

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

This temporarily disables the tenant-isolation check for that run.

Company A's agent can then read Company B's ticket, INC-002.

Expected result:

```text
FAIL: test_cross_company_read_blocked
...
FAILED (failures=1)
```

This failure is intentional. The other six tests should pass.

Run without --broken to return to secure mode.
No code changes are required.

## View Audit Logs

```powershell
Get-Content .\audit.jsonl -Tail 9
```

Each entry records:

- UTC timestamp.
- Secure or broken mode.
- Agent identity.
- Requested tool.
- Ticket identifier.
- Allow or deny decision.
- Denial reason, where applicable.

The log is saved beside demo.py.
Each run appends new entries rather than replacing old ones.

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

Seven tests generate nine permission events because two tests
each make two requests.

## Demonstrated Results

Secure mode:
- All seven tests passed.
- Cross-company access was denied with tenant_mismatch.

Broken mode:
- The cross-company test failed.
- The audit log recorded an allow decision for INC-002.

The audit log records what the gateway decided.
The tests c