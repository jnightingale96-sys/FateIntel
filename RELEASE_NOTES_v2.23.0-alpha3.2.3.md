# EnviroChem Studio v2.23.0 Alpha 3.2.3

Build ID:
`envirochem-studio-v2.23.0-alpha3.2.3-trust-release-patch-2026-09-08`

## Why this release exists

A third, independent adversarial audit of the delivered Alpha 3.2.2 ZIP (SHA-256 verified to
match exactly) confirmed every fix from that round genuinely worked, but found four residual gaps.
Every claim was independently reproduced against the live app before being accepted, and every fix
below was re-verified against the same live reproduction afterward.

## Fixed

- **`/review` allowed changing an already-closed decision.** Both import routes rejected an import
  into a `"reviewed"`/`"rejected"` workflow, but `/review` itself did not: a second call (e.g.
  `reviewed` → `rejected`) returned 200 and silently overwrote the reviewer, decision and notes on a
  closed record. `/review` now returns 409 once a workflow is `"reviewed"` or `"rejected"`.
- **A JSON boolean silently satisfied a numeric field.** `bool` is a subclass of `int` in Python, so
  `float(True) == 1.0` succeeds without raising -- the generic field-type validator added in Alpha
  3.2.2 caught `"NaN"`/`"Infinity"` strings but not a bare `true`. Booleans are now explicitly
  rejected before the numeric conversion is attempted.
- **TOXSWA's conditional time-series output blocked acceptance even when never requested.** The
  output-completeness fallback added in Alpha 3.2.2 treated every entry in a model's adapter
  contract `expected_outputs` as unconditionally mandatory, so a genuine TOXSWA run that legitimately
  never produced a time-series export (`time_series_if_requested`) could never be accepted. Adapter
  contracts can now declare an `optional_outputs` list (TOXSWA's is the first); those entries remain
  listed for visibility but no longer block acceptance on their own. `MODEL_PROFILES` members are
  unaffected -- their hand-curated recommended lists were already exactly the required set.
- **The release ZIP shipped pre-existing QA artifacts.** Five files under `data/external_runs/` and
  `data/model_workflows/` had been committed to git before those directories were added to
  `.gitignore`; the ignore rule only stops *new* files from being tracked, so these five kept
  shipping in every release ZIP since. Untracked with `git rm --cached` (the files remain on disk
  locally; only git's tracking of them was removed).

## Verification

- Full suite: 255 passed, 5 skipped (four optional native-RDKit tests, one optional
  `cryptography`-dependent test) -- 252 from Alpha 3.2.2 plus 3 new adversarial regression tests.
- The exact four live reproductions from this round's audit were re-run against the patched app and
  confirmed fixed: a second `/review` call on an already-reviewed AgDRIFT workflow now returns 409
  and leaves the original reviewer/notes/status unchanged; `boom_height_m: true` now returns
  `status: "inputs_required"` with an explicit "must be numeric" reason; a genuine TOXSWA import with
  no time-series output now reaches `status: "reviewed"`; `git ls-files data/` now returns nothing.
- `python -m py_compile` on every changed module, and a fresh `/api/health`/`/api/build` check,
  both confirmed against the patched app reporting the correct Alpha 3.2.3 identity.
- `tests/test_release_identity_consistency.py` was generalised to check every superseded release
  tag (not just the immediately prior one) across every identity-bearing file, so a previously
  fixed reference silently regressing would now be caught the same way this round's badge gap was.

## Not changed

`app/config.py`, `external_execution.py`'s `EPA_EXECUTION_MODEL_KEYS`, `registry.py`, the
native-vs-official TOXSWA separation, and every other adapter contract's `expected_outputs` are all
unchanged from Alpha 3.2.2 -- only TOXSWA gained an `optional_outputs` entry.
