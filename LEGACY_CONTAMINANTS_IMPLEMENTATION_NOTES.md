# Legacy contaminants: implementation notes (running log)

Research basis: `LEGACY_CONTAMINANTS_MATRIX_UK.md`, `_EU.md`, `_US.md`, `_TIER234_AND_RADIONUCLIDES.md`.
Rule throughout: never invent thresholds, PNECs, EQSs, factors or regulatory acceptance. Missing means MISSING.

## 2026-09-19 - Slice 1: contaminant taxonomy and routing guards (shipped, uncommitted)

**Finding from inspecting the code first:** `contaminant_group` (a plain string validated against
`CONTAMINANT_GROUPS`) is the existing routing key, and `metal_inorganic` and `hydrocarbon_solvent`
already existed and were already kept out of organic-only models via `DISCRETE_ORGANIC_GROUPS`, with a
generic "outside applicability domain" warning. So this slice extends that mechanism rather than adding a
parallel classifier.

**Changes**
- `app/services/registry.py`
  - New groups: `pah`, `legacy_pop_organic`, `organotin`, `radionuclide`, `contaminated_mixture`.
  - `CONTAMINANT_TAXONOMY`: maps every group onto the requested A-I taxonomy (single best routing letter
    per group; real substances can span several).
  - `pah` / `legacy_pop_organic` / `organotin` stay in `DISCRETE_ORGANIC_GROUPS`: they are chemically
    organic, so Koc/DT50 screening is valid. They get a "SCREENING / COMPARATIVE USE" warning because
    POPs status, bioaccumulation/food-web and sediment endpoints are not implemented.
  - `radionuclide` / `contaminated_mixture` are hard-blocked (`NO_NATIVE_PATHWAY_GROUPS`): no models
    selected, `regulatory_programme.key == "NOT_YET_IMPLEMENTED"`, explicit warning
    (EXTERNAL MODEL REQUIRED / REGULATORY APPLICABILITY NOT ESTABLISHED).
- `app/services/toxswa_surface_water.py`: route-matrix entries for the five new groups (required by
  `test_toxswa_ui_exposes_all_registered_contaminant_groups`).
- `app/static/index.html`, `app/static/app.js`: new groups in the TOXSWA selector; radionuclide and
  mixture excluded from the water-sediment workbench eligibility.
- `tests/test_registry.py`: 5 new tests (taxonomy completeness, hard blocks in all jurisdictions,
  radionuclide external-route warning, legacy organics keep screening, metals stay out of organic-only models).
- Suite: 442 passed, 5 skipped.

**Not done / deliberately not claimed**
- No metals engine, PCB/POP pathway, contaminated-land CSM, groundwater/sediment pathway, bioavailability
  routing or POPs regulatory flagging yet. `metal_inorganic` still only warns; SimpleTreat is still
  selectable for it in wastewater scenarios (its internals were not verified, so not changed).
- Radionuclide guard is a global block. Research showed the US runs radionuclides through the CERCLA
  risk-range framework (with radionuclide slope factors), unlike the UK/Canada/EU, so a per-jurisdiction
  refinement is needed later.
- `hydrocarbon_solvent` was left as-is (covers petroleum hydrocarbons and chlorinated solvents; cyanide and
  nutrients have no group yet).

## 2026-09-19 - Slice 2: metals/inorganic data model with fail-closed basis handling (shipped, uncommitted)

**Changes**
- `app/services/metals.py` (new). No SMILES/Kow assumed. `MetalMeasurement` is a frozen, validated record:
  element (starter set of 23 metals/metalloids), value, unit, basis (total / dissolved / particulate /
  bioavailable / free ion / unknown), medium, mandatory source, origin (measured / estimated / modelled),
  plus oxidation state, species, method, date, jurisdiction, confidence, applicability, assumptions.
  - Water units (ng/L to g/L) standardise to ug/L; solid/biota units to mg/kg. Solids MUST state dry or wet
    weight basis; it is never assumed. Original value and unit stay on the record.
  - `check_basis_for_criterion`: reports OK / BASIS_MISMATCH / BASIS_UNKNOWN, never converts.
  - `derive_dissolved_from_total`: the only conversion, explicit, needs a sourced fraction, result labelled
    "estimated" with the assumption recorded.
  - `incremental_over_background`: measured, background and incremental side by side; refuses mixed
    element, basis, medium or weight basis; below background gives no incremental value.
  - `bioavailability_context`: which sourced frameworks exist (UK M-BAT/bioavailable EQS for Cu/Ni/Pb/Mn,
    US 2007 freshwater copper BLM, EU Directive 2013/39 discretionary clause). Frameworks only, NO numeric
    criteria encoded (the UK matrix flagged that its full EQS table was not exhaustively transcribed).
    Elements without a confirmed framework return REGULATORY APPLICABILITY NOT ESTABLISHED.
- `app/services/registry.py`: `metal_inorganic` plans now list metal-specific required inputs (element
  identity, stated basis, water chemistry, background, soil/sediment properties) and an EXTERNAL MODEL
  REQUIRED bioavailability warning.
- `tests/test_metals.py`: 22 tests (parametrised cases included).

**Not done**
- No bioavailability modelling (M-BAT's method statement was never read; BLM coefficients not obtained).
- Not persisted to the database and not exposed by an API or UI yet: a pure service layer for now.
- Element set is a starter list; oxidation state/species are recorded but not validated against a list.

## 2026-09-19 - Slice 3: contaminated-land conceptual site model (shipped, uncommitted)

**Changes**
- `app/services/conceptual_site_model.py` (new). Validated, frozen structures: `Source` (9 kinds from the
  brief), `Contaminant` (must be a registered `contaminant_group`), `PathwayLink`, `ConceptualSiteModel`
  (sources, receptors, links, plus which contaminants have measured data in which medium).
  - `PATHWAY_RULES` enforces physical connectivity (e.g. `soil_to_groundwater` can only go soil to groundwater;
    ingestion cannot reach sediment). One addition to the brief's list: `direct_contact_ecological`, otherwise
    ecological receptors cannot be represented.
  - `assess(model, jurisdiction)` enumerates every simple path from each source's release medium to each
    receptor (multi-hop allowed, e.g. soil to groundwater to surface water; releasing straight into a
    protected resource is a zero-hop linkage). Each linkage carries taxonomy letter, missing measurements,
    and the external assessment route.
  - Reports receptors with no linkage (worded "not a finding of no risk"), sources with no linkage, and
    orphan pathway links.
  - Radionuclide and contaminated-mixture contaminants are flagged EXTERNAL MODEL REQUIRED.
  - Quantifies nothing: no exposure, dose, criteria or risk verdict (a test scans the output for verdict words).
  - `EXTERNAL_ROUTES` names only tools the research confirmed: UK CLEA-type (human), RTM/ConSim
    (groundwater), EA/EQS (surface water); US RAGS/RSLs, ERAGS/Eco-SSLs, water-quality criteria; EU
    WFD/EQS plus Member-State frameworks; Canada FCSAP/CCME; Australia ASC NEPM; NZ NES-CS (human only).
    Everything else returns REGULATORY APPLICABILITY NOT ESTABLISHED (e.g. UK ecological receptors: LCRM
    research listed no ecological method; CH and other jurisdictions unresearched).
- `app/main.py`: `GET /api/conceptual-site-model/reference` and `POST /api/conceptual-site-model/assess`
  (422 on unknown jurisdiction or structurally invalid model); added the missing `typing.Any` import.
- `tests/test_conceptual_site_model.py`: 23 tests. Full suite: 486 passed on a clean run.
  **Known pre-existing flake (not from this work):** `tests/test_v223_identity_isolation.py` fails about one
  run in five (409 "Confirmed identity conflicts with stored InChIKey"). Its fixture CAS number uses only the
  first two hex digits of a random UUID (256 values) against the persistent `data/envirochem.sqlite`, which
  already holds 1,162 leftover fixture chemicals covering 50 of the 256 prefixes, so collisions get likelier
  every run. Fix belongs in that test (use the full namespace or a per-run temp database); not changed here.

**Not done**
- Not persisted to the database, no UI, no visual diagram yet (the brief asks for a visual CSM).
- "Potential linkage" is graph reachability only. It does not apply the LCRM/Part 2A legal
  significance tests, and does not check that a pathway is physically plausible for a given contaminant
  (e.g. volatilisation of a non-volatile metal is representable).
- Measured-data flags are names only; they are not yet linked to `MetalMeasurement` or evidence records.
- Zero-hop and multi-source paths are all listed; there is no ranking or de-duplication.

## 2026-09-20 - Slice 4: POPs regulatory-status flag, and the site-model diagram (shipped, uncommitted)

**POPs flag**
- `app/data/pops_reference.json` (38 substances/classes) built from two primary sources fetched 2026-09-20:
  the Stockholm Convention listing table (annexes A/B/C, CAS where shown) and EU Regulation 2019/1021 Annex I
  Part A (ORIGINAL 2019 text, amendments not applied), plus the earlier EU research for Annex III Part A
  (dioxins/furans, PCBs, HCB), PFOA, and the proposed-only MCCP / long-chain PFCA / chlorpyrifos entries.
  - Both pages were read through an automated summariser. CAS numbers cross-checked between sources where
    both gave one; a test runs the CAS check-digit on every number to catch transcription errors.
  - decaBDE CAS left blank on purpose: the two fetches disagreed (Stockholm page showed the hexa/hepta-BDE
    number 68631-49-2 against EUR-Lex 1163-19-5), unresolved, so it matches by name only.
  - Ambiguous aliases removed ("furan", "PCP" would false-match ordinary furan and phencyclidine).
  - EU exemption text is condensed from the 2019 original and may have been amended.
- `app/services/pops.py`: `pops_status(cas_number, name, jurisdiction)` returns POPS_REGULATORY_STATUS_DETECTED
  (with Stockholm annexes and their meaning, EU annex/status/exemptions, waste-management pointer, evidence
  URLs), NOT_DETERMINED (a miss; explicitly "not evidence it is not a POP"), or IDENTITY_CONFLICT (CAS and name
  point at different substances: nothing is resolved for the user). Name-only matches carry a
  confirm-by-CAS warning. National implementation is claimed for the EU only; every other jurisdiction says
  NOT RESEARCHED.
- API: `GET /api/pops/status`, `GET /api/pops/reference`, `GET /api/chemicals/{id}/pops-status`.
- Site model: contaminants take an optional `cas_number`; each linkage carries `pops_status` and the
  assessment lists `contaminant_pops_flags`. Legacy-organic plans now ask for a CAS number.
- Tests: `tests/test_pops.py` (24 cases).

**Diagram**
- `app/services/csm_diagram.py`: `render_svg(model, jurisdiction)`. Sources, then media (longest-path layering,
  neighbour-ordered to limit crossings), then receptors; spread-out edge attachment points; labels near the
  target. Green edge = measured data for at least one contaminant on that pathway, amber = none, grey dashed =
  pathway not connected; POP badge on flagged contaminants; receptors with no linkage dashed and labelled
  "not a finding of no risk". Names are XML-escaped (a hostile-name test parses the output).
- API: `POST /api/conceptual-site-model/diagram` and `GET .../diagram/example` (a fictional site).
- Tests: `tests/test_csm_diagram.py` (8). First render was checked visually and revealed crossing lines,
  overlapping labels, an overflowing badge and an unused amber state, all fixed before this note.
- Suite: 517 passed; the one failure is the known flaky identity-isolation test above.

**Not done**
- Seed list is not exhaustive and covers Stockholm + EU only (no UK, US, CLRTAP, national regimes).
- EU Annex IV waste limits and Annex V rules are not encoded; Annex I text should be re-read from the
  consolidated regulation before any exemption is relied on.
- The diagram is server-side SVG only: no in-app screen, no editing UI, no PNG/PDF export.
- Long edges can pass behind unrelated nodes (no edge routing).

## 2026-09-20 - Slice 5: persistence, and measurements feeding the site model (shipped, uncommitted)

Chosen by me ("up to you"): it turns the pure-logic slices into something a project can keep.

- `app/models.py`: two new tables, `site_models` and `metal_measurements` (added by the existing startup
  `create_all`; no existing table is altered). A measurement stores original value, unit, basis, weight basis,
  source, origin, oxidation state, species, method, date, jurisdiction, confidence, applicability, assumptions
  and an optional `site_medium`.
- `app/services/site_records.py`: payload validation through `MetalMeasurement` (so every rule from slice 2
  applies at the API), and `merge_measured()`.
  - A measurement counts toward a site model's "measured data" flag only when its element matches a
    `metal_inorganic` contaminant in the model AND it states which site-model medium it represents
    (`site_medium`; a bare "water" is ambiguous between groundwater and surface water).
  - Anything that cannot be linked is returned in `measurement_linkage.unlinked_measurements` with the reason.
  - Metal data never marks an organic contaminant as measured. Presence only: the basis is reported per link
    but basis compatibility is not judged here.
- API (all project-scoped, 404 across projects): `POST/GET/DELETE /api/projects/{id}/metal-measurements`,
  `POST/GET/DELETE /api/projects/{id}/site-models`, `GET .../site-models/{sid}` (raw model),
  `.../assessment` (with measurement linkage report) and `.../diagram` (SVG using saved measurements).
  Only models that pass validation are stored; saves and deletes write `AuditEvent` rows.
- `tests/test_site_persistence.py`: 18 tests. They run against a throwaway in-memory database through a
  dependency override, so they never touch `data/envirochem.sqlite` (unlike the flaky identity test).
- Suite: 536 passed on a clean run; the known identity-isolation flake still appears intermittently.

**Not done**
- No UI; no edit/update endpoint (delete and re-create); measurements are not versioned or immutable.
- Only metals are linked. Organic measurements need a separate model and are not stored.
- No basis-aware criterion comparison on the saved data yet.

## 2026-09-20 - Slice 6: "Contaminated land" screen in the app (shipped, uncommitted)

- New left-nav entry and a full section (`#contaminated-land`) in `app/static/index.html`, with its own
  `contaminated-land.js` and `contaminated-land.css` (kept out of the 260 KB `app.js` and the shared stylesheet;
  it reuses `api()`, `escapeHtml()`, `toast()` and `state` from `app.js`).
- Builder: sources (kind, release media, contaminants with group and optional CAS), receptors, pathways (the
  from/to lists are filtered by the server's connectivity rules, so an impossible pathway cannot be picked).
  Metal measurement form: unit list follows the medium, weight basis appears only for solids, `site_medium` says
  which model medium the sample represents, source is required.
- Actions: Analyse (works unsaved; merges the project's saved measurements when a project exists), Save, Open,
  Delete, "Load fictional example". If no project is selected, saving creates "Site: <name>" and remembers it in
  localStorage, without touching the app's global `state.project`.
- Output: diagram (fit-to-width / actual-size toggle, SVG download), summary counts, a full-width linkage table
  with data status, missing data, POPs badge and the external assessment route per receptor, plus warnings for
  receptors with no linkage, unconnected sources/pathways, unlinked measurements and POPs flags. Every dynamic
  string goes through `escapeHtml`; the diagram is shown as an `<img>` from a blob URL, not inlined.
- Backend additions: richer `GET /api/conceptual-site-model/reference` (groups with taxonomy letters, metal
  elements, measurement bases/units), `GET /api/conceptual-site-model/example`, and
  `POST /api/projects/{id}/site-models/analyse` (draft analysis with saved measurements merged, stores nothing).
- Verification: driven in headless Chromium with real clicks against a scratch database (33 checks: rendering,
  unit switching, empty-model error, example, analysis, source-required refusal, measurement clears the gap
  16 -> 8, project created, save / reload / reopen, deletes, hostile-name injection inert, no horizontal overflow
  at 390 px, no page errors). That run found one real bug (`frameworks` out of scope in `init`) and two layout
  problems (results table squeezed, diagram too small), all fixed. The browser script lives in the session
  scratchpad, not the repo; the repo tests are `tests/test_contaminated_land_screen.py` (static wiring) and new
  cases in `tests/test_site_persistence.py`.
- Suite: 544 passed; only the known flaky identity-isolation test fails (it now fails on most runs: its CAS
  prefix space is filling up).

**Not done**
- No editing of a saved model in place (open, change, then save creates a new one); no measurement edit.
- No keyboard-only diagram interaction and no screen-reader description beyond the image alt text and the table.
- The `?v=` cache-busting string is unchanged from the release; `sw.js` needs no change (network-first).
- Not tested in Safari/Firefox; not tested with a real (non-scratch) project database.

## 2026-09-20 - Slice 7: edit saved models and measurements in place (shipped, uncommitted)

- API: `PUT /api/projects/{id}/site-models/{sid}` and `PUT /api/projects/{id}/metal-measurements/{mid}`.
  Both validate exactly like creation (a failed update leaves the saved record untouched), are project-scoped
  (404 across projects), and write an `updated` audit event that keeps the PREVIOUS values (the whole previous
  model, or the previous measurement record) so no provenance is lost. Measurement create/update now share
  `_apply_measurement()`.
- Screen: opening a saved model marks it as being edited (button becomes "Update saved model", plus "Save as
  new copy" and an explanatory line); "New model" resets the builder. Each measurement row has Edit, which
  loads it into the form ("Update measurement" and "Cancel edit", row highlighted). Provenance fields the form
  does not show (species, date, oxidation state, jurisdiction, confidence, applicability, assumptions) are
  carried through an edit instead of being dropped.
- Tests: 6 new API tests (update in place and audited, invalid update leaves the record intact, scoping, a
  corrected measurement changes the analysis) and the static-wiring test extended; the browser script now runs
  45 checks, including edit, cancel, update, update-in-place, reload persistence, save-as-copy and new model.
- Suite: 551 passed on a clean run; the only failure seen is the known flaky identity-isolation test.

**Cross-browser (done, with your go-ahead to download Firefox 153 and WebKit 26.5 via Playwright):**
`scripts/browser_check_contaminated_land.py` starts its own server on a free port against a throwaway SQLite
database, drives the screen with real clicks and prints PASS/FAIL per check. Result: Chromium 45/45, Firefox
45/45, WebKit 45/45. Screenshots in Firefox and WebKit matched Chromium (layout, chip highlighting, diagram,
full-width table). It needs `pip install playwright` and `python -m playwright install chromium firefox webkit`
(neither the venv nor the default suite depends on it); a missing engine is reported as skipped, never a pass.
Run it with `python scripts/browser_check_contaminated_land.py [chromium|firefox|webkit ...] [--screenshots DIR]`.
One Firefox-only failure during development was a bug in my check, not the app: Firefox returns an empty
`innerText` for a `<select>` element, so the check now reads the option texts instead.
Not covered: real Safari on macOS/iOS (WebKit-in-Playwright is close but not identical), older browser
versions, screen readers.

## 2026-09-20 - Slice 8: flaky-test fix, and sourced plausibility prompts (shipped, uncommitted)

**Flaky test fixed.** `tests/test_v223_identity_isolation.py` now runs every test against its own in-memory
database (autouse fixture overriding `get_db`). Cause: its fixture CAS numbers used only 256 possible values
against the persistent `data/envirochem.sqlite`, so they collided with rows left by earlier runs (409), and every
run added ~20 more fixture chemicals. Result: 0 failures in 15 isolated runs and 3 clean full-suite runs, the
real database row count no longer grows (it still holds 1,312 leftover "isolation QA" chemicals from before; not
deleted without your say-so), and the file runs in 2.5 s instead of 7 s.

**Plausibility prompts (`app/services/pathway_plausibility.py`).** Rule: only criteria read in primary text are
encoded; property values are never assumed or converted (each key carries its unit and a value needs a source).
Two rules, each stored with verbatim quote, page, URL and retrieval date, and shown in the UI:
- **V1 volatility** (US EPA vapor-intrusion guide, June 2015, Section 3.1, PDF p.58, read from the PDF text):
  volatile if vapour pressure > 1 mm Hg OR Henry's law constant > 1e-5 atm-m3/mol. Applies to the
  volatilisation pathway and inhalation from soil gas. Above either value: "supports relevance". Below BOTH
  (both must be supplied): "questions relevance", with the guide's own caveat that some less-volatile compounds
  (naphthalene, some PCB congeners, elemental mercury, p.44) can still be of concern, so it is a prompt to review,
  never an exclusion. One property supplied and not exceeding: inconclusive (the definition is "either"). Metals:
  the guide names only elemental mercury (checked across the whole body text) and gives no rule for other metals,
  so no metal is called non-volatile without supplied properties.
- **B1 bioaccumulation** (Stockholm Convention Annex D 1(c)(i), 2021 text, PDF p.68, read from the PDF): BCF/BAF
  in aquatic species > 5,000 or, in the absence of such data, log Kow > 5. Applies to food-chain transfer. Below the
  value is "inconclusive" and never "questions": Annex D lists other reasons for concern. Not applied to metals
  (EPA's Framework for Metals Risk Assessment cautions against generic BCF/BAF; log Kow does not describe metals).
- Outcomes: SUPPORTS_RELEVANCE, QUESTIONS_RELEVANCE, INCONCLUSIVE, PROPERTY_MISSING. A linkage is never removed.
  Radionuclides and mixtures get none. Boundary values are not "greater than" (tested).
- **Not encoded, deliberately:** the EU CLP mobility criterion (log Koc). EUR-Lex text could not be retrieved by
  any route available (HTML, PDF, ELI page all returned empty), and a search only confirmed the regulation exists,
  so no threshold from memory was used. Also no rule for plant uptake, erosion, dermal contact, soil-to-
  groundwater or groundwater-to-surface-water transport.
- Site model: `Contaminant.properties`; `properties` accepted in the site-model JSON (validated: unknown key,
  missing source, non-positive value, NaN/inf all rejected with a 422); saved with the model; `assess()` adds
  `plausibility` per linkage, summary counts, `plausibility_rules` and an updated disclaimer (it previously said
  "no criteria are applied", which stopped being true).
- Screen: per-contaminant collapsible "Properties for plausibility checks" (fixed units, one required source),
  a badge per pathway step, a "Plausibility prompts" panel, a "Properties needed" list, and an expandable panel
  with each rule's quote, page, link and the not-encoded list. The property source string is escaped and a
  hostile one is inert.
- Tests: `tests/test_pathway_plausibility.py` (boundaries, precedence, metals, rule provenance, API), persistence
  and static-wiring tests; the brittle "pec" substring test now uses word boundaries (it matched "species").
  Browser script: 60 checks, passing in Chromium, Firefox and WebKit. Suite: 589 passed, 0 failed (two runs).

**Not done / limits**
- The example site has no property values on purpose: inventing values for real substances would be fake data.
- The EPA definition is a US vapor-intrusion criterion; other jurisdictions use other volatility criteria and are
  not encoded. Units are fixed (mm Hg, atm-m3/mol): no unit conversion is offered, to avoid silent errors.
- The Stockholm criterion is a listing-screening criterion, used only to say bioaccumulation is a supported concern.
- Diagram edges are not marked by plausibility outcome.

## 2026-09-20 - Slice 9: EU CLP mobility rule found and encoded (shipped, uncommitted)

The regulation text that slice 8 could not retrieve WAS retrievable. What failed: EUR-Lex HTML, the plain PDF URL
(empty), the ELI page, web.archive.org (blocked for the tool), lexparency (TLS error). What worked:
`https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023R0707&from=EN` (the `&from=EN` variant returned
a real 33-page PDF), read by extracting the PDF text. Web-search summaries of the criteria gave conflicting numbers
(one said "<= 4 / <= 3"), which is why the primary text was needed.
- **M1** (Commission Delegated Regulation (EU) 2023/707, Annex I 4.4.2.1.2 and 4.4.2.2.2, Official Journal
  L 93, 31.3.2023, pp. 24-25; PDF pages 18-19), verbatim: mobile (M) when log Koc < 3; very mobile (vM) when
  log Koc < 2; for an ionisable substance the lowest log Koc for pH 4 to 9. Also quoted: 4.4.2.3 (classification is
  "a weight of evidence determination using expert judgment") and the log Koc definition (4.4.1.1).
- Applied to `soil_to_groundwater` and `groundwater_to_surface_water`. Below 3: supports relevance (very mobile
  below 2). At or above 3: inconclusive, never "questions", because the regulation classifies by weight of evidence.
  Ionisable caveat attached; not applied to metals (the coefficient is an organic carbon-water one); needs a
  supplied, sourced `log_koc` (Koc in L/kg; the regulation states no unit, so that is flagged as a convention).
- Stated plainly in the rule: this is a hazard-classification criterion, and using it as a prompt for leaching
  relevance is FateIntel's application, not something the regulation says.
- Screen: log Koc field added; rules panel shows M1 with its quotes. Tests: 7 new plus updated assertions (the
  "gap" is gone; "plant uptake, erosion, dermal contact and runoff" remain unencoded). Browser script: 62 checks,
  passing in Chromium, Firefox and WebKit.
- Still open: the EU criteria are for the EU only; other jurisdictions' mobility criteria are not encoded.

**Second flaky test found and fixed.** During this slice's full-suite runs `tests/test_ms_evidence.py::
test_review_endpoint_rejects_unknown_confidence_level` failed once (HTTP 409). Same class of bug as the identity
test: `_unique_rt()` draws from only 10,000 values while the persistent database keeps every imported file's content
hash forever, and the tests also assumed a "Carbamazepine" row existed in real project data. Fixed with the same
per-test in-memory database (seeded with that one chemical); 0 failures in 10 isolated runs; suite 596 passed.

**UPDATE - suite-wide test isolation done (slice 10a).** New `tests/conftest.py`: an autouse fixture gives every
test its own in-memory SQLite database, seeded with the app's own `seed()` (so tests that expect the demo
Carbamazepine record still find it), overrides `get_db`, and repoints every `SessionLocal` reference (the app's
startup seeding and the tests that open sessions directly). The two file-level fixtures added earlier
(identity isolation, MS evidence) were removed as redundant. Measured: 3 consecutive full runs, 596 passed each,
and 0 rows added to `data/envirochem.sqlite` (before, one run added ~29 projects, ~100 audit events and more).
Existing leftover test rows in the real database (over 2,300 projects, 1,300+ chemicals) are still there and were
not deleted without your say-so. The paragraph below describes the state BEFORE this fix.

**Remaining test pollution of the real database (measured, then fixed above).** One full suite run still adds, to
`data/envirochem.sqlite`: 29 projects, ~100 audit events, 22 model workflows, 13 model runs (and identity
bindings), 11 chemical profiles / project-chemical links, 8 evidence records and sources, 2 orchestrated records,
1 chemical, 1 risk assessment. Other test files write there because they use `TestClient(app)` without a database
override. The principled fix is a shared autouse fixture (tests/conftest.py) giving every test its own in-memory
database; it was not attempted because some tests may depend on seeded real data and it would need a suite-wide
pass. Until then, other tests of the "unique value vs persistent database" kind could start failing intermittently.

## 2026-09-21 - Slice 10b: UK mobility and volatility criteria researched and encoded (shipped, uncommitted)

Read from primary text (raw page or PDF text, never a summariser or search snippet alone):
- **UK mobility.** Defra, "Interim approach to the PMT concept to support UK REACH risk management of PFAS",
  4 June 2025 (gov.uk; England, Scotland, Wales). It reproduces the EU CLP criteria (Annex A: mobile log Koc < 3,
  very mobile < 2), calls the UK approach "interim", says it is "currently focused on PFAS risk management actions
  under UK REACH", and (para 26) "Definitive criteria are not being formally adopted in UK REACH, or other
  legislation". Para 15 defines mobility as movement through the terrestrial environment to water bodies (which
  supports applying M1 to soil-to-groundwater transport); para 16 says Koc is "a useful screening measure" but
  "too simplistic to determine the potential mobility of PFAS". So the UK value is the EU one, used non-statutorily.
  M1 now carries that, and every PFAS mobility result (supports OR inconclusive) carries the Koc caution: a test
  caught that the caution was first attached only to "supports", not to a high log Koc, where it matters most.
- **UK bioaccumulation.** UK REACH Annex XIII (legislation.gov.uk, retained EU law): B when BCF in aquatic species
  > 2,000; vB when > 5,000; applies to "all organic substances, including organo-metals". Encoded as rule **B2**
  (needs a BCF; no log Kow alternative, unlike Stockholm B1; not applied to inorganic metals).
- **UK volatility: no UK criterion found.** The Environment Agency's CLEA technical basis (SR3, 2009, PDF p.87) only
  reports that "ITRC (2007) noted that several regulatory agencies have defined volatile chemicals as those with a
  Henry's Law constant greater than 1 x 10-5 atm m3 mol-1 (that is, greater than 1 Pa m3 mol-1)". It states no
  threshold of its own. Recorded as a second (corroborating) quote on V1, with the UK stated as "no UK criterion
  found"; not presented as a UK rule.
- **GB CLP and PMT classes: NOT established.** HSE's GB CLP pages (retrieved) do not mention the new hazard
  classes. Search summaries conflict (one: "no plans to introduce", another: an April 2026 Lords debate about
  legislating by June 2027). Hansard and EUR-Lex-style pages were bot-blocked, so this is listed as an unsourced
  gap rather than asserted either way.
- Each prompt now says whether the criterion is formal in the jurisdiction being assessed or a reference from
  another regime (`in_regime`, `regime_note`), and the rules panel has "Position by jurisdiction" and "Limits" per
  rule, plus per-quote document names and links. Tests: rule B2 boundaries, regime labelling, the UK volatility
  finding recorded as corroboration only, the PFAS caution, jurisdiction-aware site-model output.
  Suite: 606 passed (two runs), 0 real-database writes.

### Slice 10c - screen bug found while hardening the browser check, and what is still unresolved

**Real bug, fixed:** after clicking "Contaminated land" in the nav, the section scrolled to the top of the window
and "Load fictional example" ended up UNDER the sticky top bar (the element at the button's centre was the project
pill), so it could not be clicked until the user scrolled. Every other section in `styles.css` has
`scroll-margin-top: 86px`; this one lacked it. Fixed (`.cl-shell{scroll-margin-top:86px}`) and covered by a new
browser check (the button must receive clicks at its centre once the nav scroll settles).

**Harness bugs fixed (mine):** (1) after clicking Analyse the script waited for the results table, but an earlier
analysis leaves one behind, so it returned at once and read stale results (`analyse_and_wait` now waits for
"Analysis complete", which cannot be stale because the click sets "Analysing..." synchronously); (2) a syntax error
I introduced made one batch of "clean runs" meaningless (they never ran); I re-collected the data.

**App robustness fixed:** overlapping list refreshes could apply out of order (only the latest call may apply now);
a failed refresh silently emptied the lists (it now says so); "Open" and "Delete" silently did nothing when nothing
was selected (they now say so).

**RESOLVED (2026-09-21) - root cause found: smooth scrolling vs Playwright clicks, a test-timing artefact.** The
last failure came with full evidence: at the failing "Open" click the button was enabled, clickable and had a model
selected, the page then scrolled ~326 px within 400 ms, and the app never reacted. The app sets `scroll-behavior:
smooth`; a Playwright click issued while a smooth scroll is still animating is sometimes silently lost. Measured
directly (40 clicks each, issued mid-scroll): WebKit lost 3, Firefox lost 1, Chromium lost 0; with smooth
scrolling forced off, 0 lost in all three engines. That matches every earlier failure (Firefox/WebKit only, rare,
server data and page list correct, click apparently ignored). It is not an app defect: a real user's click lands
where they see the button. Fix in `scripts/browser_check_contaminated_land.py`: CSS smooth scrolling is switched off
in the test pages, and `open_section()` waits for the nav's own explicit smooth scroll to settle before any further
action (used at the initial navigation and after each reload). The app-robustness changes above were still worth
making. Result: 67/67 in all three engines. Confirmation soak: 10 consecutive combined three-engine runs (30
engine runs, 2,010 checks), 0 failures; before the fix roughly 1 combined run in 6 failed.

(Earlier text, superseded:) the three-engine browser check passes in Chromium every time, but Firefox and WebKit
occasionally hang in the reload -> open -> links section. Rates seen after the fixes above: WebKit 3 failures in 49
single-engine runs, and 24 consecutive clean runs on the last batch; Firefox 0 in 18 single-engine runs but 1
failure in a combined run where the three engines share one scratch database. At every failure that was
diagnosed, the server still held the saved model and the page's own list showed it, so the stored data was right
and I could not tell whether the cause is the app or the harness. Not chased further (time-boxed). If it matters,
next step: log the awaited expression and page state at each failure (already in the script's failure report) over
a longer soak and compare.

Suite: 607 passed on two consecutive runs, 0 rows written to the real database.

**Leftover test rows in `data/envirochem.sqlite` (read-only survey, 2026-09-21; NOT cleaned).** 2,323 projects
created 2026-09-07 to 2026-09-20, almost all with test-generated names, for example: 606 "AGDRIFT review-gate QA
<hex>", 150 "EPA bridge CEM <hex>", 78 "PEARL review-gate QA", 76 each of "PWC review-gate QA", "TP pathway QA",
"TOXSWA review-gate QA", "SPIN integration lifecycle", "Twenty-chemical-isolation-<hex>", "Identity-conflict-<hex>",
75 "US-exposure-<hex>", 75 "v<n>.<n> model expansion API test", 72 "enviPath predict QA", 61 "Kinetics QA", 42 "MS
evidence QA". Only about a dozen projects look like real work (for example "Carbamazepine - US guided fate
assessment", the "Carbamazepine-benchmark-..." and "REACH-Diclofenac-..." ones). Of 1,389 chemicals, nearly all are
"<name> - isolation QA <hex>" fixtures or "Toluene US exposure QA <hex>". Cleaning needs cascade deletes across ~15
tables including audit events, so it needs a backup and an explicit go-ahead first.

## Slice 11 (2026-09-21): commit, database cleanup (staged, blocked), website section

**Committed** on `master`: `833bbdb` (research matrices and this notes file), `aa55245` (all code, tests, scripts),
`b1ca6a5` (`data/backups/` added to .gitignore). Suite at commit time: 607 passed, 5 skipped.

**Database cleanup: NOT applied.** The user chose "remove the test data". Done: a backup at
`data/backups/envirochem.pre-cleanup.20260921-130306.sqlite` (byte copy, 24,481,792 bytes) and a dry run of
`cleanup_db.py` (scratchpad; single transaction, rolled back, `PRAGMA foreign_key_check` = 0 problems). Keep set:
projects 1 and 197 (the two "Protected Carbamazepine verification example" projects) with their own rows, and
chemicals 1 (Carbamazepine) and 2 (Diclofenac, the seeded identities). Everything else is test debris, including the
108 non-pattern-matched projects (106 "Alpha4-<uuid>" / "FateIntel orchestration QA"). All 615 evidence records and
615 sources are QA fixtures (source titles such as "Canonical provenance QA", "Aquatic QA evidence"). The dry run
would delete: 2,321 projects, 1,387 chemicals, 1,387 identity snapshots, 615 evidence, 615 sources, 9,078 audit
events, 2,087 profiles, 2,087 project-chemical links, 970 model runs and bindings, 1,659 workflows, 106 orchestrated
records, 74 risk assessments, 164 MS files and features. Result: projects 2, chemicals 2, audit events 11. The real
apply step was refused by the auto-mode permission classifier (mass delete), so the database is UNCHANGED. Files under
`data/model_workflows/` and `data/external_runs/` on disk were not surveyed and would not be touched by the script.

**Website** (artifact QKAfz5MktxxfBNc6FK7VCH) version 17: new "Legacy contaminants & contaminated land" section
(`#legacy`, nav label "Legacy land"): two entry points (substance / site), one-record outcomes, the app's own
site-diagram SVG for a fictional site (UK view), four capability cards, a schematic tile map with the six regions that
have external routes named (UK, EU, US, CA, AU, NZ) and four scoping-only regions (JP, CN, KR, IN), a route table taken
from `EXTERNAL_ROUTES`, and a "Not built yet" box. It is labelled "In development, not part of the Alpha 4 download"
because the Alpha 4 zip on the page does not contain this work. Also fixed in the page: pre-existing wrapped nav labels
and a 51px mobile sideways overflow from the platform feature cards. Verified in Chromium at 1440 to 1041 px and 390 px
(no horizontal overflow). Not verified: Firefox/WebKit rendering of the page. The page's "Verification: 278 tests"
line in the Alpha 4 release box is about the Alpha 4 download and was left alone.

## Candidate next slices
1. (done in slice 8: contaminant-aware pathway plausibility, for two sourced rules) Extend with further sourced
   rules, first retrieving the EU CLP mobility text through an accessible mirror or the ECHA guidance, then
   groundwater relevance for mobile substances. Anything still unsourced stays unencoded.
2. (kept from before) Contaminant-aware pathway plausibility (e.g. flag volatilisation for non-volatile metals, soil gas for
   VOCs) using only sourced properties, plus a visual CSM diagram in the UI.
2. POPs regulatory-status flag from a sourced, non-exhaustive seed list (EU POPs Reg. Annex I, Stockholm).
3. Persist metal measurements and site models (tables + API) and link measured flags to evidence records.
4. Extend `CONTAMINANT_TAXONOMY` with cyanide, nutrients, petroleum sub-families.
