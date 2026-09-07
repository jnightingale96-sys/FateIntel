# EnviroChem Studio v2.23 Alpha 3.1 progress status

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
