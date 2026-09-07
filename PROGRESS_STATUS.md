# EnviroChem Studio v2.23 Alpha 3.2.3 progress status

## Alpha 3.2.3 trust release patch

- Closed the last review-mutability gap: `/review` itself now rejects a second call on a workflow
  already `"reviewed"` or `"rejected"` with 409, matching the guard already on both import routes.
- Fixed a bool/numeric confusion: `bool` is a subclass of `int` in Python, so `float(True)` silently
  succeeded as `1.0` past the generic field-type validator. Booleans are now explicitly rejected
  before the numeric conversion is attempted.
- Adapter contracts can now declare `optional_outputs` (used for TOXSWA's conditional
  `time_series_if_requested`) so the output-completeness fallback no longer blocks acceptance of a
  genuine run that legitimately never produced a conditional output.
- Untracked five pre-existing QA artifact files under `data/external_runs/` and
  `data/model_workflows/` that had been committed before those paths were added to `.gitignore`,
  so the ignore rule never stopped them shipping in the release ZIP.
- Full clean-database regression result: see `RELEASE_NOTES_v2.23.0-alpha3.2.3.md`.

## Alpha 3.2.2 trust-and-validation hotfix

- Replaced the hand-picked `require_numeric()` subset with one generic pass driven from every
  `field_types` declaration: invalid enum options, non-finite (`"NaN"`/`"Infinity"`) numbers,
  fractional values in whole-number-only fields and out-of-range *optional* numeric fields are now
  all rejected uniformly, for every field the profile declares typed, not just the previously
  hand-picked ones.
- Extended `validate_external_model_output()` with a fallback for every genuinely
  externally-managed model outside the 12-key hand-curated set: its own adapter contract's
  `expected_outputs` becomes the completeness requirement, closing the gap that let PEARL (and
  PELMO/SWASH/TOXSWA/EXAMS/EPIE/SimpleBox/EPI Suite and others) reach "reviewed" after importing
  an unrelated file. Native EnviroChem screens remain excluded.
- Added an immutability guard to both import routes: a workflow already `"reviewed"` or
  `"rejected"` now rejects a further import with 409 instead of silently reverting to
  `output_imported`.
- Fixed the two release-identity references the previous round's consistency test missed:
  `START_ENVIROCHEM.bat` (a distinct launcher file from `START_ENVIROCHEM_CONSOLE.cmd`) and this
  README's own H1/intro. The test now checks both.
- Full clean-database regression result: see `RELEASE_NOTES_v2.23.0-alpha3.2.2.md`.

## Alpha 3.2.1 trust-and-release hotfix

- Synchronised the version identity (launcher, README, service worker, web manifest and
  cache-busting query strings) with `app/version.py` across the whole package, and added an
  automated consistency test so this cannot silently drift again.
- Closed a real review-acceptance bypass: the `/review` endpoint's genuine-provenance gate
  previously applied only to the four local-execution-bridge models; every other model
  (including the new FIFRA companion models) could be marked "reviewed" from an arbitrary
  plain-text import. The gate now applies to every model, and the hashed-file import route is
  available to every model, not just the execution-bridge four.
- Replaced free-text input fields with typed numeric/select fields plus matching backend
  validation for the pesticide-model forms (PWC, PRZM, AgDRIFT, TerrPlant, T-REX, BeeREX) —
  non-numeric values can no longer reach a "prepared" workflow status.
- Removed the advertised `path_environment_variable` entries for the five pesticide-adapter
  models that have no matching configuration field and no verified executable, rather than
  leave a documented setting that silently does nothing.
- Full clean-database regression result: see `RELEASE_NOTES_v2.23.0-alpha3.2.1.md`.

## Alpha 3.1 guided-run recovery

- Guided calculation failures now terminate visibly instead of leaving an animated loading state.
- The persistent recovery panel reports the scientific stage and safe request diagnostics and offers retry.
- Jurisdiction/use/release changes are locked while a guided run is active.
- The US benchmark calculation path was replayed end-to-end at the API boundary.
- Full clean-database regression result: 226 passed; five optional tests skipped.

See `RELEASE_NOTES_v2.23.0-alpha3.1.md`.

## Alpha 3 execution and routing increment

- PWC, ChemSTEER, CEM and E-FAST now share a controlled external execution,
  handoff, original-file import and independent-review lifecycle.
- Official software remains separately installed and is never bundled.
- US industrial soil releases can be screened explicitly for groundwater
  leaching, with all equations and limitations exposed.
- The industrial workbench is use-class gated; the EU water–sediment workbench
  and official FOCUS_TOXSWA controls are tier and programme gated.
- Full regression result: 225 passed, five optional tests skipped.

See `RELEASE_NOTES_v2.23.0-alpha3.md` and `EPA_EXECUTION_BRIDGE.md`.

## EU / US jurisdiction routing now working

- The top tab drives a real EU or US assessment-plan request.
- Exposure scenarios remain stable while regulatory programmes and applicable
  models change between REACH/FOCUS and TSCA/FIFRA.
- Jurisdiction-specific controls are visually gated and stale results are cleared
  on every switch.
- External workflow records are filtered by jurisdiction and scenario and remain
  explicitly separate from official model execution.
- Project and native-run provenance now retains the active jurisdiction.

## US exposure foundations now working

- Typed industrial release events on a shared, non-overlapping throughput basis
- Air, water, soil, landfill, incineration and off-site treatment routing
- Exact daily and annual mass closure; managed waste remains labelled as transfer
- Measured-air and time-averaged well-mixed worker inhalation screening
- Explicit dermal contact, absorption, respirator and glove protection factors
- 12 published EPA ESDs enabled; 48 draft/reference records require opt-in
- Managed contracts for ChemSTEER 3.2, CEM 3.2 and legacy E-FAST 2014
- Fifteen-domain conventional risk-assessment completeness check
- Professional guided-interface workbench and immutable identity-bound model runs

## Transformation pathway prediction now working

- BioTransformer `ENVMICRO` JSON adapter with one-to-three-generation requests
- Provider-neutral node/edge pathway representation
- Editable scientist-review list carrying predicted status, generic matrix and provider provenance
- Query identifier, retrieval time and raw-response SHA-256 retained in every completed run
- Explicit separation of qualitative pathway prediction from quantitative formation/degradation kinetics
- Rate-limit, timeout, malformed-response and provider-failure handling
- Staging/production licensing gate; local/test use remains development or academic evaluation only

## Provenance and safe Home App binding now working

- Dashboard readiness ladder for identity, reviewed profile and stored evidence
- Profile-level “Why this number?” inspection
- Searchable/filterable source-level evidence table
- Canonical SHA-256 snapshot hash for every returned evidence record
- Optional Home App binding to a confirmed project identity and reviewed profile
- Explicit separation of reviewed profile values from manual/unreviewed Koc
- Qualitative-only Home App scope with no implied PEC, PNEC, RQ or treatment-plant scaling

## REACH review bundles retained

- Browser workflow bound to the active project, confirmed chemical and reviewed profile
- Strict `ng/L`, `µg/L`, `mg/L` and `g/L` normalisation
- Freshwater PNEC arithmetic using an explicit reviewer-supplied assessment factor
- Stored aquatic-ecotoxicity evidence binding and selected model-run snapshots
- Canonical JSON, EnviroChem-native XML, escaped HTML review summary and SHA-256 manifest
- Optional fail-closed RSA-PSS signing with public-key fingerprint metadata
- Hardened in-memory verification endpoint and command-line verifier
- Export audit event with selected IDs, manifest/bundle hashes, signing mode and submission boundary

## Production foundations now working

- Validated centralized configuration with `.env` and environment precedence
- Text/JSON application logging with request correlation
- Typed, machine-readable application errors
- Real database liveness/readiness diagnostics
- FastAPI lifespan startup and graceful SQLAlchemy shutdown
- Windows launcher readiness gate and shared port resolution
- Python 3.12/3.14 CI contract, compilation, focused linting, JavaScript syntax and tests

## Scientific modules retained

- Confirm-before-use chemical identity and immutable provenance snapshots
- Project/chemical-specific reviewed calculation profiles
- Identity-matched evidence retrieval and staging
- Soil degradation selection and evidence hashes
- Ionisation-aware sorption models
- Pharmaceutical use, metabolism, influent and WWTP mass balance
- Identity-locked Carbamazepine Activity SimpleTreat verification fixture
- Reviewed custom WWTP, biosolids and wastewater-irrigation screens
- Neutral-organic plant-uptake research screen with explicit limitations
- Native multimedia fate and catchment river-network screens
- External-model workflow control plane and EU/US adapter manifests
- Veterinary ERA, Home Use, SDS/COSHH and EnviroDesign modules

## Further production work required

- Authentication, authorization and project-level access control
- Durable job queue and worker process for long model executions
- Database migrations and supported PostgreSQL deployment profile
- Secret-manager integration if future authenticated services require credentials
- Rate limiting, security headers, backup/restore and operational monitoring
- Full official input writers, launchers and parsers for configured external models
- Dedicated scientific rulesets for specialist chemical classes
- Controlled official IUCLID format/template adapter and conformance fixtures before any submission-ready claim
- Approved key-management/signing service and signer authorization for regulated operations
