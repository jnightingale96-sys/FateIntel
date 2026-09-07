# EnviroChem Studio v2.23.0 Alpha 1

Release name: **Identity Foundation**  
Build ID: `envirochem-studio-v2.23.0-alpha1-identity-foundation-2026-09-02`

## Outcome

EnviroChem now starts with no chemical selected. Carbamazepine remains a
protected verification fixture, but it is loaded only when the user chooses the
demo or opens an exact project/chemical workspace link.

## Changes

- Added neutral guided-startup state and disabled the calculation profile until
  a candidate identity is explicitly confirmed.
- Removed the automatic first-chemical/Carbamazepine fallback from
  `ensureWorkspace()`.
- Added exact URL scoping with both `project_id` and `chemical_id`.
- Blocked ambiguous UI selection when a project contains multiple chemicals.
- Added source-independent molecular identity hashing and explicit conflict
  checks for InChIKey, CAS, formula, molecular weight and substance form.
- Added `model_run_identity_bindings`, a one-to-one immutable identity record
  created automatically for every new `ModelRun`.
- Added safe startup backfill for historical model runs where a complete local
  identity snapshot exists.
- Added `GET /api/model-runs/{model_run_id}/identity-binding`.
- Added a 20-chemical succession regression and deliberate cross-record
  identifier-conflict test.
- Corrected legacy launcher assertions to test the v2.22.1 visible-console
  launcher where the relevant logic now lives.

## Validation

- `192 passed`
- `0 failed`
- `4 skipped`: the documented optional native-RDKit tests; RSA signing was exercised
- Python compilation passed.
- Guided and expert JavaScript syntax checks passed.

## Preserved scientific and commercial boundaries

- BioTransformer remains provider-neutral, qualitative and licence-gated.
- A predicted pathway does not supply or imply formation fraction, rate constant,
  DT50 or transformation-product concentration.
- No native screen is relabelled as an official FOCUS, SimpleTreat, EUSES or US
  regulatory model.
- REACH review bundles remain distinct from official IUCLID dossiers.

## Next increment

Implement the shared typed-quantity and `UseScenario`/`ReleaseEvent` spine,
followed by a reconciled parent/transformation-product mass and molar ledger.
