# EnviroChem v2.8.1 startup fix

## What changed

- First-start progress is explicit: the console explains that RDKit makes dependency installation slower.
- All startup output is persisted in `STARTUP_LOG.txt`.
- The browser opens only after `/api/health` responds successfully.
- Python selection supports the Windows `py` launcher and versions 3.10–3.14.
- Damaged virtual environments are detected and rebuilt.
- Runtime imports, including RDKit, are verified before the server starts.
- A diagnostic batch file and a safe virtual-environment reset file are included.
- PostgreSQL and pytest were removed from the default local runtime dependency set.
- RDKit is allowed through the current 2026 release family and installed as a wheel where available.
- A failed RDKit import no longer prevents the rest of EnviroChem from importing; the EnviroDesign API returns a clear, actionable error.
