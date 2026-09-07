# EnviroChem Studio v2.23.0 Alpha 3.2.1

Build ID:
`envirochem-studio-v2.23.0-alpha3.2.1-fifra-companion-models-2026-09-07`

## Why this release exists

An external adversarial audit of the delivered Alpha 3.2 ZIP (SHA-256 verified to match exactly)
found real, reproducible gaps. Every claim was independently reproduced against the live app
before being accepted, and every fix below was re-verified against the same live reproduction
afterward.

## Fixed

- **Version identity drift.** `app/version.py` reported alpha3.2 while the launcher, README,
  service worker, web manifest and cache-busting static-asset tags still said alpha3.1 — risking
  the launcher reusing a stale process instead of recognising the new build. All identifiers are
  now synchronised, and `tests/test_release_identity_consistency.py` fails the suite if a future
  version bump misses any of them.
- **Review-acceptance bypass.** The `/review` endpoint's genuine-provenance gate (real execution
  or a hashed original-file import, plus complete recommended outputs) previously applied only to
  the four local-execution-bridge models (PWC, ChemSTEER, CEM, E-FAST). Every other model —
  including the new FIFRA companion models, but also every pre-existing EU FOCUS model — could be
  marked "reviewed" after importing nothing but an arbitrary text paste. Reproduced end to end
  with AgDRIFT: prepared with garbage, imported `nonsense=1`, and the workflow reached
  `status: "reviewed"`. The gate now applies to every model's "accepted" decision, and the
  genuine hashed-file import route (`/import-output-files`) — previously restricted to the same
  four models — is now available to every registered model, since that route is what actually
  produces the provenance the gate requires.
- **No numeric or enumerated validation on model-input forms.** Every field in the PWC/PRZM/
  AgDRIFT/TerrPlant/T-REX/BeeREX forms was a plain text input; the literal string "not-a-number"
  supplied for every numeric field reached workflow status "prepared" with zero missing inputs.
  Numeric fields are now real `<input type="number">` elements with unit/min/max metadata
  (a non-numeric value simply cannot be entered), and enumerated fields (application method, use
  site, waterbody type, etc.) are real `<select>` elements. Backend `require_numeric()` validation
  provides the same guarantee against a direct API call bypassing the form.
- **Misleading configuration advertisement.** The five pesticide-adapter models without a real
  configured executable (PRZM, AgDRIFT, TerrPlant, T-REX, BeeREX) advertised a
  `path_environment_variable` (e.g. `ENVIROCHEM_AGDRIFT_PATH`) that had no matching configuration
  field and no effect if set. Removed rather than fabricate a config field for a capability that
  doesn't exist to test against. These five remain — correctly — manual-handoff-only.

## Verification

- Full suite: 246 passed, 5 skipped (four optional native-RDKit tests, one optional
  `cryptography`-dependent test) — 235 from Alpha 3.2 plus 11 new (7 release-identity, 4
  adversarial regression).
- The exact three live reproductions from the audit were re-run against the patched app and
  confirmed fixed: nonsense-string AgDRIFT prepare now returns `status: "inputs_required"` with
  explicit `"(must be numeric)"` reasons per field; plain-text AgDRIFT import followed by
  `decision: "accepted"` now returns 409; AgDRIFT via `/import-output-files` with genuine
  confirmation now reaches `status: "reviewed"`.
- Confirmed in the rendered guided screen: AgDRIFT's application-method field is a real `<select>`
  with the same enum as the backend; its rate field is a real `<input type="number" min="0">` that
  the browser itself refuses to hold non-numeric text in.

## Not changed

`app/config.py`, `external_execution.py`'s `EPA_EXECUTION_MODEL_KEYS` (still `{PWC, ChemSTEER,
CEM, E-FAST}` — the only four with a real, verifiable executable), `registry.py`, `adapters.py`,
and the native-vs-official TOXSWA separation are all unchanged from Alpha 3.2.
