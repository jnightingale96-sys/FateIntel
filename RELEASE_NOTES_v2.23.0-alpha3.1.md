# EnviroChem Studio v2.23.0 Alpha 3.1

Build ID:  
`envirochem-studio-v2.23.0-alpha3.1-us-run-state-hotfix-2026-09-05`

## Fixed

- A failed guided assessment no longer leaves the progress spinner running with
  the generic “Assessment requires review” message.
- The progress panel closes on failure and a persistent recovery panel reports
  the scientific stage, safe API error, HTTP status, request ID and endpoint.
- FastAPI validation errors are converted into readable field-specific messages.
- A failed calculation can be retried after the displayed input or review issue
  is corrected.
- Jurisdiction, use and release scenario are locked while a calculation is in
  progress, preventing a completed result from being relabelled by an in-run
  context change.
- Switching jurisdiction clears any stale progress or error panel.

## Diagnostic result

The Alpha 3 US backend was not deadlocked. A fresh United States Carbamazepine
project was replayed successfully through confirmed identity, guided readiness,
sorption, emissions and Activity SimpleTreat. The defect was the frontend failure
state concealing the actual request error and continuing to animate.

## Retained boundary

Alpha 3.1 retains the Alpha 3 EPA execution/import and groundwater implementation.
It does not claim that the overall platform is a complete FIFRA or TSCA assessment.

## Verification

- Python compilation, guided/expert/service-worker JavaScript syntax and
  high-confidence Ruff checks passed.
- Full fresh-database suite: 226 passed; five optional tests skipped (four
  native-RDKit tests and one RSA test because optional packages were absent).
