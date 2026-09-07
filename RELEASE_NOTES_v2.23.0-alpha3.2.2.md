# EnviroChem Studio v2.23.0 Alpha 3.2.2

Build ID:
`envirochem-studio-v2.23.0-alpha3.2.2-trust-and-validation-hotfix-2026-09-07`

## Why this release exists

A second, independent adversarial audit of the delivered Alpha 3.2.1 ZIP (SHA-256 verified to
match exactly) found that the 3.2.1 trust-and-release hotfix was itself incomplete in four ways.
Every claim was independently reproduced against the live app before being accepted, and every fix
below was re-verified against the same live reproduction afterward.

## Fixed

- **Version identity, the two references the previous round's fix missed.** `app/version.py`
  correctly reported alpha3.2.1, and `START_ENVIROCHEM_CONSOLE.cmd` and the cache-busting static
  tags were updated to match -- but `START_ENVIROCHEM.bat` (a distinct wrapper launcher, not the
  same file) and this README's own H1/intro still said Alpha 3.1, and a static release badge in
  `index.html` also still said "v2.23 ALPHA 3.1" in a space-separated prose form that neither the
  hyphenated cache-busting tag check nor a `BUILD_ID`-anywhere-in-file check would ever catch. All
  three are now synchronised, and `tests/test_release_identity_consistency.py` checks both launcher
  files by name, the README heading specifically (not just any embedded reference), and both the
  hyphenated and space-separated forms of every superseded version tag.
- **Enum, non-finite-number and integer-only validation gaps.** `require_numeric()` only checked a
  hand-picked subset of numeric fields per model and had no enum-checking counterpart at all, so an
  application method outside the registered list, or the literal strings `"NaN"`/`"Infinity"`
  (which `float()` accepts without raising) reached workflow status "prepared" untouched.
  `validate_external_model_inputs()` now runs one generic pass over every `field_types` entry a
  profile declares -- required or optional -- rejecting invalid enum options, non-finite numbers
  (`math.isfinite`), fractional values in whole-number-only fields (application counts, simulation
  years), and out-of-range values in optional fields that were never checked before. The guided
  form now marks the same fields `required` and calls `form.checkValidity()` before submitting.
- **Output-completeness enforcement, silently absent for every model outside a 12-key list.**
  `validate_external_model_output()` returned `None` -- not an error, just "no check defined" -- for
  any model outside its hardcoded 12-key `MODEL_PROFILES` set, so the `/review` gate's
  missing-outputs check silently defaulted to empty for PEARL, PELMO, SWASH, TOXSWA and every other
  officially adapted model. Reproduced end to end with PEARL: prepared with valid inputs, imported
  an unrelated file mapping none of PEARL's expected outputs, and reached "reviewed". Every
  genuinely externally-managed model (identified by its adapter contract's `execution_mode` not
  starting with `"native"`) now falls back to its own contract's `expected_outputs` as the
  completeness requirement. Native EnviroChem screens, which compute inline and never go through a
  genuine-execution import, are correctly excluded.
- **No immutability guard on reviewed or rejected workflows.** Neither import route checked
  `row.status` before overwriting the output record, so a workflow that had genuinely reached
  "reviewed" could be silently reverted to "output_imported" by a later plain-text import.
  Reproduced end to end with AgDRIFT: genuine hashed-file import, accepted to "reviewed", then a
  plain `/import-output` call with `nonsense=1` silently reverted the status. Both import routes
  now reject any import into a `"reviewed"` or `"rejected"` workflow with 409.

## Verification

- Full suite: 252 passed, 5 skipped (four optional native-RDKit tests, one optional
  `cryptography`-dependent test) -- 246 from Alpha 3.2.1 plus 8 new (2 release-identity, 4
  adversarial regression) and 2 test fixtures corrected to match intentionally strengthened schema
  (`test_epa_execution_bridge.py`'s PWC fixture used a Koc unit string, `"L/kgOC"`, that never
  matched the declared enum `"L/kg_oc"` -- previously unvalidated, now correctly caught and fixed
  at the source).
- The exact four live reproductions from this round's audit were re-run against the patched app and
  confirmed fixed: an invalid AgDRIFT application method and `"NaN"`/`"Infinity"` values both now
  return `status: "inputs_required"` with explicit reasons; a PEARL workflow imported with an
  unrelated file/output now carries a non-empty `missing_recommended_outputs` list and `/review`
  with `decision: "accepted"` returns 409; re-importing into an already-reviewed AgDRIFT workflow
  now returns 409 and leaves its status and output hash unchanged.
- Confirmed in the rendered guided screen: AgDRIFT's required fields (`application_method`,
  `boom_height_m`, `droplet_size_category`, `application_rate_kg_ha`, `wind_speed_m_s`,
  `buffer_distance_m`, `waterbody_width_m`) all carry the HTML `required` attribute while the
  optional `temperature_c` does not; submitting the empty form fires zero network requests
  (`checkValidity()` blocks it and shows the native browser validation UI); filling all seven
  required fields with valid values and submitting reaches `status: "prepared"` with an empty
  `missing_inputs` list end to end through the real UI form.
- Confirmed the release badge on the guided-assessment welcome screen now reads "NEW · v2.23 ALPHA
  3.2.2 · TRUST AND VALIDATION HOTFIX".

## Not changed

`app/config.py`, `external_execution.py`'s `EPA_EXECUTION_MODEL_KEYS` (still `{PWC, ChemSTEER,
CEM, E-FAST}`), `registry.py`, `adapters.py`'s contract data (only a deferred import of
`ADAPTER_CONTRACTS` was added inside `external_models.py`), and the native-vs-official TOXSWA
separation are all unchanged from Alpha 3.2.1.
