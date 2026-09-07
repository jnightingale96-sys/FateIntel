# Production foundations decision record — v2.19

The supplied PowerShell scaffold contained several useful architectural ideas, but applying it directly would have overwritten EnviroChem’s working scientific application. v2.19 integrates the viable concepts selectively.

## Integrated

| Supplied idea | v2.19 implementation |
| --- | --- |
| Central configuration | Validated Pydantic v2 settings with recognised environment variables, optional `.env`, precedence rules and no unused secrets |
| Structured logging | Correlated text or JSON logs with UTC timestamps, level, logger, request ID and exception details |
| Common exceptions | Typed safe errors with HTTP status, machine code, details and request ID |
| Health endpoint | Real `SELECT 1` database diagnostic plus separate readiness endpoint |
| Startup/shutdown handling | FastAPI lifespan context initializes data and disposes the database engine |
| API validation tests | Added production-foundation tests while retaining all scientific regressions |
| CI | Multi-version Python, compilation, focused lint, JavaScript syntax and full pytest workflow |
| Development configuration | Black, Ruff and pytest configuration without mechanically reformatting the inherited codebase |

## Not integrated

- **Replacement `app/main.py`:** it would have removed the real API and model workflows.
- **Simulated `/api/assess`:** `asyncio.create_task` is not a durable job system and its output was fabricated demonstration data.
- **Replacement landing page:** it would have removed the guided and scientific workspaces.
- **Proposed Koc function:** it was an undocumented approximation, acid-specific despite a generic name, numerically defective and scientifically inferior to the existing tested sorption service.
- **Unused API-key/secret fields:** configuration should not solicit secrets until a real, authorised integration requires them.
- **Claims of commercial-grade readiness:** v2.19 states remaining authentication, tenancy, queue, migration and security work explicitly.

## Background-work boundary

Long-running work should eventually use a persistent job record and a separate worker/queue with retry, cancellation, timeout, provenance and recovery semantics. An in-process fire-and-forget task can be lost when the server restarts and is therefore not used for scientific model execution.
