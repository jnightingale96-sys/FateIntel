# EnviroChem Studio v2.23.0 Alpha 1.1

Release name: **Windows Startup Hotfix**  
Build ID: `envirochem-studio-v2.23.0-alpha1.1-windows-startup-hotfix-2026-09-02`

## Outcome

The Windows launcher can now start Uvicorn while the browser-readiness helper
runs in the background. The helper no longer holds `STARTUP_LOG.txt`; Uvicorn
is the sole long-running process redirected to that file.

## Root cause

Alpha 1 redirected both processes into the same file. Windows file-sharing
semantics denied Uvicorn access and printed “The process cannot access the file
because it is being used by another process.” The command shell then reported a
misleading normal stop even though the server had not started.

## Changes

- Redirected the silent `open-when-ready` helper to `NUL`.
- Retained Uvicorn output in `STARTUP_LOG.txt` for diagnosis.
- Added a regression test that fails if the helper shares the server log again.
- Bumped application/build metadata and browser cache keys to Alpha 1.1.
- Updated stale v2.21 labels in the scientific workspace to v2.23.

## Validation

- `193 passed`
- `0 failed`
- `4 skipped`: documented optional native-RDKit tests
- Python compilation passed.
- Guided, expert and service-worker JavaScript syntax checks passed.

## Scope

This hotfix changes startup orchestration and release metadata only. The Alpha 1
identity foundation, scientific calculations, evidence handling and commercial
licence gates are otherwise unchanged.
