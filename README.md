# EnviroChem Studio v2.23.0 Alpha 3.4.0 — Applied Environmental Fate

EnviroChem is an evidence-led environmental fate, exposure and regulatory modelling workspace. Alpha 3.4.0 adds an Applied Environmental Fate screen: SFO/FOMC/HS/DFOP degradation-kinetics fitting against raw replicate residue-decline data, a FOCUS Kinetics-style chi-square model comparison, and FOCUS/VICH GL38 metabolite significance classification -- every model equation, threshold and citation verified directly against the primary regulatory guidance documents, not secondary summaries.

## v2.23 Alpha 3.4.0 applied environmental fate

- **New `app/services/degradation_kinetics.py` module.** Fits SFO, FOMC, HS and DFOP to
  parent (and transformation-product) residue-decline data via nonlinear least squares, using
  the exact FOCUS Kinetics (2014, v1.1) chi-square goodness-of-fit formula (Eq. 6-1) and DT50/DT90
  found by numerical root-finding against the fitted curve rather than hand-transcribed closed
  forms. Applies the correct, *separately cited* metabolite significance rule per framework: FOCUS
  Kinetics Section 8.5.1's 10%-of-applied-parent "major vs minor" kinetic-modelling-reliability
  split, or VICH GL38's 10%-of-administered-dose PEC-inclusion rule (which also depends on whether
  the metabolite forms part of a normal biochemical pathway -- a reviewer judgement, not something
  this module determines automatically). These are two different rules that happen to share a
  number; the module never conflates them.
- **Formation-then-decline metabolites are handled correctly.** Fitting a monotonic-decline model
  directly to a transformation product that rises then falls drives every model to a degenerate,
  nonsensical result (verified: an ~745-million-day DT50). The module now detects this and refits
  from the metabolite's own observed maximum instead, per FOCUS Kinetics Section 8.5.1's own
  sanctioned simplified approach -- always labelled in the output as `decline_from_observed_maximum`
  so a DT50 measured from a metabolite's peak is never mistaken for one measured from time of
  parent application.
- **New "Applied Environmental Fate" left-nav screen.** Day-by-replicate observation entry for the
  parent and any number of transformation products, a live decline-curve chart, and a full
  per-model chi-square comparison table so a reviewer can see every candidate model's fit, not just
  the one the guidance-threshold rule selected.
- 28 new tests (`test_degradation_kinetics.py`), including a regression test for the
  formation-then-decline bug found and fixed this cycle; full suite green.
- New base dependency: `scipy` (nonlinear curve fitting and the chi-square distribution) --
  the first genuinely unavoidable addition beyond the existing numpy/fastapi/sqlalchemy core.

## v2.23 Alpha 3.3.0 analytical identification

- **New `app/services/analytical_identification.py` module.** Three sources, kept deliberately
  separate from the scalar-endpoint `evidence_sources.py` pipeline: NORMAN SusDat (OPERA-predicted
  ESI mode, precursor `M+H+`/`M-H-`, chromatographic platform), NORMAN EAWAGTPS (curated
  parent/transformation-product pairs), and a live MassBank Europe REST connector (real, measured
  product-ion spectra plus their recorded retention time, column, mobile phase and ionisation
  mode).
- **`GET /api/chemicals/{id}/identification`** and **`GET /api/analytical-identification/{inchikey}`.**
  The latter needs no stored `Chemical` row, so a known transformation product returned by the
  first lookup can have its own identification profile looked up directly — the Identification
  screen follows parent → TP → that TP's own profile in one click.
- **NORMAN SusDat shipped as an indexed JSONL file, not one in-memory dict.** The slimmed dataset
  still covers ~109k substances and came out to ~44 MB; a small inchikey→byte-offset index
  (`app/data/norman_susdat_index.json`) is the only piece loaded at import time, and a lookup seeks
  straight to its one line.
- **`scripts/convert_norman_references.py`** is the one-off converter from the source NORMAN CSVs
  to the shipped `app/data/*.json`/`*.jsonl` reference files.
- Full clean-database regression result: see `RELEASE_NOTES_v2.23.0-alpha3.3.0.md`.

## v2.23 Alpha 3.2.3 trust release patch

- **`/review` is now immutable once closed.** A second call to `/review` on a workflow already
  `"reviewed"` or `"rejected"` previously returned 200 and silently overwrote the reviewer, decision
  and notes on a closed record (e.g. `reviewed` → `rejected`). Both import routes already rejected
  this; `/review` itself now does too, returning 409.
- **Booleans no longer satisfy numeric fields.** `bool` is a subclass of `int` in Python, so
  `float(True) == 1.0` succeeds without raising -- a JSON `true` sent for a numeric field (e.g.
  AgDRIFT's `boom_height_m`) silently passed the generic field-type validator added last round. The
  validator now explicitly rejects `bool` values before attempting the numeric conversion.
- **TOXSWA's conditional time-series output no longer blocks acceptance.** The generic
  output-completeness fallback added last round treated every entry in a model's adapter contract
  `expected_outputs` as unconditionally mandatory, so a genuine TOXSWA run that never requested a
  time-series export (`time_series_if_requested`) could not be accepted. Adapter contracts can now
  declare an `optional_outputs` list; those entries stay listed for visibility but never block
  acceptance on their own.
- **The release ZIP no longer ships pre-existing QA artifacts.** Five files under
  `data/external_runs/` and `data/model_workflows/` had been committed to git before those
  directories were added to `.gitignore`, so the ignore rule never stopped them from being tracked
  and shipped in every release ZIP since. They have been untracked (`git rm --cached`); the ignore
  rule now actually keeps new artifacts like them out of every future release.
- Full clean-database regression result: see `RELEASE_NOTES_v2.23.0-alpha3.2.3.md`.

## v2.23 Alpha 3.2.2 trust-and-validation hotfix

- **Generic, `field_types`-driven input validation.** Every PWC/PRZM/AgDRIFT/TerrPlant/T-REX/BeeREX
  field declared as numeric or enumerated is now validated from that single declaration instead of
  a hand-picked subset: invalid enum options (e.g. an application method outside the registered
  list), the literal strings `"NaN"`/`"Infinity"`, fractional values in whole-number-only fields
  (application counts, simulation years) and out-of-range values in *optional* numeric fields are
  all rejected before a workflow can reach "prepared". The browser form now marks the same fields
  `required` and the guided screen calls `form.checkValidity()` before submitting.
- **Output-completeness enforcement extended to every externally-managed model.** Previously only
  the 12 models with a hand-curated recommended-outputs list (SPIN, MACRO, GREATER, PWC, PRZM,
  AgDRIFT, TerrPlant, T-REX, BeeREX, ChemSTEER, CEM, E-FAST) were checked for complete outputs
  before acceptance; every other officially adapted model (PEARL, PELMO, SWASH, TOXSWA, EXAMS,
  EPIE, SimpleBox, EPI Suite and more) now falls back to its own adapter contract's expected
  outputs, so an unrelated file can no longer be imported and accepted as a complete result. Native
  EnviroChem screens, which compute inline and never go through a genuine-execution import, are
  unaffected.
- **Reviewed and rejected workflows are now immutable.** Both import routes reject a further
  import once a workflow has reached `status: "reviewed"` or `"rejected"`, closing a gap where a
  subsequent plain-text import could silently revert an accepted record back to `output_imported`.
- **The remaining stale version-identity references.** `START_ENVIROCHEM.bat` (distinct from
  `START_ENVIROCHEM_CONSOLE.cmd`, fixed last round) and this README's own heading still said Alpha
  3.1; both are now synchronised, and the release-identity consistency test checks the launcher
  `.bat` file and this heading specifically, not just a single embedded build-ID reference anywhere
  in the file.
- Full clean-database regression result: see `RELEASE_NOTES_v2.23.0-alpha3.2.2.md`.

## v2.23 Alpha 3.2.1 trust-and-release hotfix

- Synchronised the version identity (launcher, README, service worker, web manifest and
  cache-busting query strings) with `app/version.py` across the whole package, and added an
  automated consistency test so this cannot silently drift again.
- Closed a review-acceptance bypass: the `/review` endpoint's genuine-provenance gate previously
  applied only to the four local-execution-bridge models; every other model (including the new
  FIFRA companion models) could be marked "reviewed" from an arbitrary plain-text import. The gate
  now applies to every model, and the hashed-file import route is available to every model, not
  just the execution-bridge four.
- Replaced free-text input fields with typed numeric/select fields plus matching backend
  validation for the pesticide-model forms (PWC, PRZM, AgDRIFT, TerrPlant, T-REX, BeeREX).
- Removed the advertised `path_environment_variable` entries for the five pesticide-adapter models
  that have no matching configuration field and no verified executable.
- See `RELEASE_NOTES_v2.23.0-alpha3.2.1.md`.

## v2.23 Alpha 3.1 US run-state hotfix

- A failed guided calculation now stops and removes the spinner instead of remaining on “Assessment requires review”.
- A persistent panel identifies the failed scientific stage, exact safe API message, HTTP status, request ID and endpoint.
- Validation-list details are rendered as readable field messages rather than `[object Object]`.
- The failed run can be retried directly after correcting the reported input.
- Jurisdiction, use and release scenario cannot be changed while a calculation is active.
- The canonical US Carbamazepine wastewater path was replayed successfully through identity, sorption, emissions and Activity SimpleTreat.

## v2.23 Alpha 3 EPA execution bridge

- PWC 3.003, ChemSTEER 3.2, CEM 3.2 and E-FAST 2014 now have a common official-tool control plane.
- Every workflow can export a non-copyrighted handoff ZIP containing the input manifest, expected-output map, execution checklist and checksums.
- Manual/GUI executions require the original output files, model/executable versions, operator, execution notes and explicit authorised/genuine-run confirmations. Every file receives a SHA-256.
- Optional unattended execution is disabled by default. It becomes available only when an administrator configures an exact executable path, fixed argument template and output globs in `.env`; the operator must acknowledge the current executable SHA-256 for each run.
- The bridge invokes no shell, accepts no command from the browser, uses an isolated run folder and fixed timeout, and captures process logs plus output-file hashes.
- A successful process launch is not automatically an accepted scientific result. Required endpoints must be mapped and an independent review decision recorded.
- The native US industrial screen now offers an explicit soil-to-groundwater calculation using source-zone equilibrium partitioning, retarded vertical travel and first-order transformation. Equations, inputs and exclusions are returned with the result; it is not PWC or PRZM.
- The US industrial source-term panel appears only for **US + Industrial + Manufacturing / processing**.
- The native EU water–sediment workbench appears only for a relevant Tier 2+ organic-chemical pathway and is no longer labelled as TOXSWA. Official FOCUS_TOXSWA controls are limited to EU pesticide soil/spray pathways at Tier 3–4.
- See `EPA_EXECUTION_BRIDGE.md` and `RELEASE_NOTES_v2.23.0-alpha3.md` for configuration, validation and remaining boundaries.

Alpha 3 still is not a complete US risk assessment implementation. It executes or records the official four-tool workflows without owning or modifying them; hazard/dose-response integration, programme-specific receptor coverage and additional FIFRA/TSCA models remain separate work.

## v2.23 Alpha 2.1 jurisdiction routing

- Agricultural spray, manufacturing, household use, product disposal, direct surface-water release and soil scenarios are available in both EU and US modes; scenarios are no longer incorrectly treated as US-only.
- EU mode routes relevant work to REACH/FOCUS programmes; US mode routes it to TSCA/FIFRA programmes.
- EU-only controls and US-only model cards are visually gated by the top tabs.
- The guided region selector is locked to the active top tab, and a jurisdiction switch clears stale results without changing the scientist's selected scenario.
- Prepared external workflows are filtered by jurisdiction and scenario. “Prepared” records orchestration only; it never implies that an official model was executed.
- EU and US projects are kept distinct, and native model-run names carry the selected jurisdiction for auditability.
- See `RELEASE_NOTES_v2.23.0-alpha2.1.md` for the tested boundary and remaining gaps.

## v2.23 Alpha 2 US exposure foundations

- Select from 12 published EPA exposure-scenario documents; 48 draft/reference records require explicit opt-in and remain labelled.
- Route a chemical throughput through non-overlapping release events, controls, air/water/soil and managed waste with exact mass closure.
- Screen worker inhalation using measured air or a time-averaged well-mixed room, and retain dermal contact, absorption and PPE factors explicitly.
- Review missing conventional risk-assessment domains before interpreting a result.
- Prepare versioned external workflows for ChemSTEER 3.2, CEM 3.2 and legacy E-FAST 2014 without bundling or modifying EPA executables.
- See `US_EXPOSURE_FOUNDATIONS_IMPLEMENTATION_NOTES.md` for equations, source hashes, rights boundaries and the remaining model roadmap.

## v2.23 Alpha 1.1 Windows startup hotfix

- The background browser-readiness helper no longer inherits or holds `STARTUP_LOG.txt`.
- Uvicorn remains the sole long-running writer to the startup log.
- A launcher regression test protects the separation of those file handles.
- The build identifier, browser cache key and visible release labels distinguish this ZIP from the faulty Alpha 1 package.

## v2.23 Alpha 1 identity foundation

- Normal startup is chemically neutral: no pilot substance, profile or project is selected automatically.
- The Carbamazepine verification fixture remains available only through **Load Carbamazepine example** or an exact project/chemical link.
- Exact workspace links use both `project_id` and `chemical_id`; an ambiguous multi-chemical project is never resolved by silently choosing the first row.
- Confirmation checks InChIKey first, then independently checks CAS, molecular formula, molecular weight and substance form. Cross-record CAS/InChIKey conflicts return HTTP 409.
- Every new model run receives a one-to-one immutable identity binding containing the confirmed snapshot JSON and SHA-256. Historical runs are backfilled where a complete confirmed local identity is available.
- The state-isolation regression confirms 20 chemically varied identities in succession and checks profile, evidence and model-run separation.
- Baseline and release evidence are recorded in `BASELINE_AUDIT.md`, `BASELINE_MANIFEST.json`, the Alpha 1/1.1 notes and the Alpha 2/2.1 release notes.

## Start on Windows

1. Extract the ZIP to a new folder.
2. Double-click `START_ENVIROCHEM.bat`. The visible console remains open so any startup error can be read.
3. Keep the terminal window open while EnviroChem is running.
4. Manual URL (default): `http://127.0.0.1:8792/?build=envirochem-studio-v2.23.0-alpha3.4.0-applied-environmental-fate-2026-09-09`.

The launcher supports folders containing spaces. If the selected port already serves
the same EnviroChem build, a second launch reopens that instance. If another
application owns the port, the launcher selects the next available local port and
reports it before starting.

The first run creates a local Python environment. Native RDKit remains optional; EnviroDesign uses the browser/WASM path when available.

### v2.22.1 Windows startup hotfix retained

- The downloaded launcher no longer starts a hidden PowerShell process.
- Browser readiness polling now runs through the same local Python environment as EnviroChem.
- A short visible wrapper keeps startup failures on screen and opens `STARTUP_LOG.txt` after an error.
- If the internal console launcher is missing, the wrapper explains that the complete ZIP must be extracted before use.
- Windows launch files are packaged with CRLF line endings.

## v2.22 transformation pathway workflow

1. Confirm the parent chemical identity and place its SMILES in EnviroDesign.
2. Choose one to three generations and select **Predict pathway**.
3. EnviroChem submits the single parent to BioTransformer `ENVMICRO`, polls the documented JSON endpoint and normalises the response into nodes and reaction edges.
4. Every returned product is labelled **model predicted** and copied into an editable scientist-review list with matrix and provider provenance.
5. Review, delete, rename or relabel products before running motif-retention analysis or subsequent fate assessment.

BioTransformer does not supply formation fractions, rate constants, DT50 values or measured occurrence. Those fields remain deliberately empty. Quantitative formation and decay must be fitted separately from reviewed parent/TP time-series data.

The remote service documents a limit of two POST requests per minute. `ENVMICRO` uses enviPath/EAWAG-derived data and therefore remains blocked in staging/production unless `BIOTRANSFORMER_COMMERCIAL_LICENSE_CONFIRMED=true` is set by an operator who holds the required written permission. The flag records an operator decision; it does not itself grant a licence.

## v2.21 provenance and Home App workflow retained

- The Expert Dashboard now shows confirmed-identity, reviewed-profile and stored-evidence readiness separately.
- Profile metrics expose **Why this number?** details with status, origin, source summary and update time.
- Evidence can be filtered by text and endpoint; each row opens source, endpoint, reliability, notes and a canonical record hash.
- The Home App can bind to the selected project chemical only when its identity is confirmed and its assessment profile is reviewed.
- The FOCUS PEARL soil–groundwater graphic now uses the same flat technical process language as the SWASH/TOXSWA schematic while retaining live layers, transport paths, assessment plane and endpoint animation.
- Bound identity, log Kow and soil DT50 replace conflicting form text. Koc remains visibly unreviewed because it is not stored in the current assessment profile.
- Home-use output is deliberately qualitative. It reports that active-ingredient mass, PEC, PNEC and risk quotient were not calculated.

Barcode values remain manual references. v2.21 does not infer ingredients from a mock lookup table or silently scale one household use to a treatment-plant population.

## v2.20 REACH preparation workflow retained

The Expert Workspace now includes **REACH Review Bundle**. An export is allowed only when the selected project/chemical has:

1. a confirmed identity snapshot;
2. a reviewed and explicitly confirmed assessment profile;
3. stored aquatic ecotoxicity evidence (`LC50`, `EC50`, `NOEC` or `EC10`);
4. a reviewer-supplied assessment factor with rationale and guidance/decision reference; and
5. explicit reviewer confirmation.

The generated ZIP contains canonical `reach-review.json`, an EnviroChem-native namespaced `reach-review.xml`, an escaped `csr-review.html`, a boundary `README.txt`, and `manifest.json` with the exact size and SHA-256 of every payload. Optional RSA-PSS signs the exact manifest bytes in detached `manifest.sig`. Signing fails closed: a requested RSA export never falls back to HMAC or unsigned output.

This is deliberately **not** an IUCLID `.i6z` archive and must not be renamed or submitted to REACH-IT. Authoritative IUCLID dossier generation requires the applicable current IUCLID format, templates, validation rules and submission workflow.

To enable RSA-PSS signing:

```text
pip install -r requirements-optional-signing.txt
REACH_MANIFEST_PRIVATE_KEY_PATH=C:\secure\envirochem-review-key.pem
```

The PEM must contain an unencrypted RSA private key of at least 2048 bits. Keep it outside the repository. On POSIX systems, group/world-readable key files are rejected. Verify a bundle independently with:

```text
python -m app.reach.cli envirochem-reach-review-diclofenac.zip --public-key trusted-public.pem --require-signature
```

A valid signature establishes integrity relative to the supplied public key; independently verify the reported key fingerprint before trusting signer identity.

## v2.19 production foundations retained

- One validated settings object reads recognised environment variables and an optional project-root `.env` file.
- The Windows launcher resolves the same port configuration used by the application.
- Application logs support human-readable text or newline-delimited JSON.
- Every request receives an `X-Request-ID`; a valid caller-supplied ID is preserved for correlation.
- Typed application errors return a safe human message, machine-readable code and request ID.
- `/api/health` performs a real database query and reports a credential-safe backend/latency check.
- `/api/ready` returns HTTP 503 when the database is unavailable, allowing a launcher or deployment platform to avoid routing traffic prematurely.
- FastAPI lifespan management initializes/seeds the database and disposes the SQLAlchemy engine cleanly on shutdown.
- GitHub Actions validation covers Python 3.12 and 3.14, compilation, high-confidence Ruff checks, JavaScript syntax and the complete test suite.

The pasted simulated assessment service, replacement landing page and undocumented Koc approximation were deliberately not integrated. See `PRODUCTION_FOUNDATIONS_NOTES.md` for the decision record.

## Configuration

Copy `.env.example` to `.env` only when overrides are needed. Operating-system environment variables take precedence over `.env`, and explicit application values take precedence over both.

| Setting | Default | Purpose |
| --- | --- | --- |
| `ENVIROCHEM_PORT` | `8792` | Local HTTP port |
| `ENVIROCHEM_ENVIRONMENT` | `local` | `local`, `test`, `staging` or `production` label |
| `LOG_LEVEL` | `INFO` | `DEBUG` through `CRITICAL` |
| `LOG_FORMAT` | `text` | `text` or `json` |
| `DATABASE_URL` | local SQLite | SQLAlchemy database URL |
| `ENVIROCHEM_*_PATH` | unset/default | Authorised external-model locations |
| `ENVIROCHEM_NATIVE_RDKIT` | `false` | Explicitly enable optional native RDKit |
| `REACH_MANIFEST_PRIVATE_KEY_PATH` | unset | Optional unencrypted RSA private-key PEM path for review-bundle signing |
| `BIOTRANSFORMER_ENABLED` | `true` | Enable the interim pathway adapter |
| `BIOTRANSFORMER_BASE_URL` | `https://biotransformer.ca` | Fixed HTTPS provider base URL |
| `BIOTRANSFORMER_COMMERCIAL_LICENSE_CONFIRMED` | `false` | Operator attestation required before staging/production use |
| `ENVIPATH_ENABLED` | `true` | Enable the enviPath curated-search/prediction adapter |
| `ENVIPATH_BASE_URL` | `https://envipath.org` | Fixed HTTPS provider base URL |
| `ENVIPATH_API_TOKEN` | unset | Bearer API token from your own envipath.org account (recommended auth path) |
| `ENVIPATH_USERNAME` / `ENVIPATH_PASSWORD` | unset | Fallback session-login credentials (unverified against the current envipath.org) |
| `ENVIPATH_COMMERCIAL_LICENSE_CONFIRMED` | `false` | Operator attestation required before staging/production use |

Do not place credentials in source control, diagnostic logs or shared ZIP files. EnviroChem does not request an OpenAI API key because the current rule-based Assessment Explainer does not need one.

## Generic chemical assessment retained from v2.18

1. Resolve a CAS number, preferred/IUPAC name or SMILES.
2. Inspect and explicitly confirm the identity candidate.
3. Search the Evidence Data Hub.
4. Copy relevant evidence candidates into the project/chemical calculation profile.
5. Review units, endpoint applicability and sources, then explicitly confirm the profile.
6. Run the applicable pathway. Sorption, WWTP, biosolids, irrigation and neutral plant-uptake inputs are bound to reviewed profiles and originating runs.

Retrieved evidence remains unselected until review. Diclofenac is covered by the generic-flow regression tests, but QA-only Diclofenac values are not shipped as regulatory selections. The protected Carbamazepine workbook fixture remains restricted to its parent identity (CAS `298-46-4`).

## Scientific and deployment boundaries

The generic WWTP route is a transparent screening mass balance using reviewed pathway fractions; it is not presented as an official SimpleTreat execution. Prepared external workflows are not completed external-model runs.

The production foundations improve local operation and deployment readiness, but they do not add authentication, authorization, multi-user tenancy, a durable background-job queue, encrypted secret storage or public-internet hardening. Those controls are required before exposing EnviroChem beyond a trusted local/private environment. RSA file-path support is appropriate for controlled local/private deployment; production key custody should move to an approved signing service or hardware-backed key store.

See `TRANSFORMATION_PATHWAYS_IMPLEMENTATION_NOTES.md`, `REACH_REVIEW_BUNDLE_IMPLEMENTATION_NOTES.md`, `GENERIC_CHEMICAL_ASSESSMENT_NOTES.md`, `EXTERNAL_MODEL_INTEGRATION_NOTES.md`, `PRODUCTION_FOUNDATIONS_NOTES.md` and `VALIDATION.txt` for detailed boundaries and checks.
