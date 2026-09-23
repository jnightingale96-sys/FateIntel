# Norway, UAE, Saudi Arabia — jurisdiction expansion

## Why

User (2026-09-23): "Finish the countries, then back to the 90-day validation plan." The "countries" list
came from an earlier check-in: Brazil, Mexico, Norway, Singapore, Taiwan, Gulf states, South Africa. Three
parallel research agents were dispatched for all seven; two (Brazil/Mexico, Singapore/Taiwan/South Africa)
hit a session rate limit and failed before producing results. Only the Norway/Gulf-states agent completed,
with genuinely strong, primary-sourced findings. This file covers what was implemented from that completed
research. Brazil, Mexico, Singapore, Taiwan and South Africa remain outstanding — the research needs
re-running, not started from scratch (see "Not done" below).

## What shipped: Norway (NO), UAE (AE), Saudi Arabia (SA)

Extended across every place a jurisdiction needs to be registered, following the exact pattern already
established for JP/CN/KR/IN (`REGION_RESEARCH_JP_CN_KR_IN.md`, an earlier session):

- `app/schemas.py` — jurisdiction `Literal` extended (all 5 occurrences) to include `"NO", "AE", "SA"`.
- `app/services/registry.py` — `FRAMEWORKS` gained three new entries (packs, default currency: NOK/AED/SAR)
  and `_regulatory_programme()` gained three new jurisdiction branches, each citing real sources.
- `app/services/workflow_registry.py` — `REGIONS` gained `NO`/`AE`/`SA` entries; Norway's `refinement` is
  `"eu"` (confirmed FOCUS-sharing, not assumed), UAE/Saudi Arabia's is `None` (no confirmed native
  refinement).
- `app/static/index.html` — three new `data-model-system` tabs (the real, live jurisdiction picker) and
  three new `<select id="regions">` options (the secondary, disabled/synced display element).
- `app/static/app.js` — `REGION_SETS`, `REGION_LABELS`, `MODEL_SYSTEM_JURISDICTIONS`, `FOCUS_REGIONS` (NO
  added, since it genuinely shares the FOCUS refinement suite), and `projectModelSystem()`'s free-text
  jurisdiction-name matcher all extended.
- Live-verified in the browser after every change: clicked the Norway and UAE tabs, confirmed no console
  errors, and read back the real rendered regulatory-route text for each (Norway: the DMP/EMA pharmaceutical
  text; UAE: "No dedicated refinement screen is built... yet", correctly not overclaiming FOCUS sharing).

### Norway — confirmed EEA-incorporated EU REACH, the one jurisdiction unlike JP/CN/KR/IN's shape

Primary sources read directly: Miljodirektoratet's own REACH pages, Mattilsynet's own national-requirements
page for plant-protection products (read in full), EUR-Lex for Regulation (EU) 2019/6 and its EEA extension
(Joint Committee Decision No. 371/2021).

- **Industrial chemicals**: genuinely the same REACH regime as the EU, incorporated via the EEA Agreement.
  Routed with its own `NO_REACH_*` keys (own dossiers/timelines, matching how UK REACH gets its own key
  despite the same regulatory origin) but `status: "available"`, not `"partial"` — a real, meaningful
  difference from every other jurisdiction added this session or in the JP/CN/KR/IN pass.
- **Pesticides**: FOCUS scenarios are the shared Northern Zone baseline, **with two confirmed, documented
  national deviations**: FOCUS MACRO 5.5.4 is mandated for groundwater leaching (matching this app's own
  `MACRO` model entry, literally named "FOCUS MACRO 5.5.4a" before this session even started — a striking
  confirmation), and Mattilsynet's own six-scenario (not the standard nine) surface-water selection drops
  D5, D6 and R3. `NO` was added to `PEARL`/`PELMO`/`MACRO`/`SWASH`/`TOXSWA`/`PRZM`'s own `regions` lists and
  to the `{"EU","UK","CH"}` jurisdiction set that selects them in `build_assessment_plan()` — Norway now
  gets the full calculable FOCUS suite, not an "EXTERNAL MODEL REQUIRED" placeholder.
  **Deliberately NOT extended**: the EFSA birds/mammals/bees screens (`ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN`,
  `ENVIROCHEM_EU_BEES_SCREEN`) — their applicability to Norway's own pesticide regime was not researched
  this session, so `jurisdiction != "NO"` explicitly guards that selection (mirroring how AU is excluded
  from the bee screen specifically while inheriting the birds/mammals one on separately-confirmed grounds).
- **Human/veterinary pharmaceuticals**: DMP (Direktoratet for medisinske produkter) applies the EMA
  two-phase environmental risk assessment guideline as-is via the EU/EEA medicines network; veterinary
  medicines additionally sit under Regulation (EU) 2019/6, extended to Norway by EEA Joint Committee
  Decision No. 371/2021. No Norway-specific numeric deviation was found for either.
  **Deliberately NOT extended**: `EPIE` (the EU pharmaceutical spatial exposure model) was NOT added to
  Norway's applicable models — the research confirmed the *method* (EMA guideline) but not that EPIE's own
  spatial population/hydrology dataset actually covers Norwegian catchments, so this stays an open gap
  rather than an assumed extension.

### UAE (AE) and Saudi Arabia (SA) — one real shared instrument, otherwise genuinely distinct and unmapped

Kept as two separate jurisdiction branches, not one merged "GCC" pathway — a merged pathway would overstate
the actual confirmed harmonisation. The one genuinely GCC-wide, primary-sourced instrument is the
**Pesticides Act of the Cooperation Council for the Arab States of the Gulf** (read in full via FAOLEX,
ratified as each state's own domestic law — UAE 2007, Saudi Arabia 2006): Article 2 requires registration
to confirm a pesticide is "not harmful" to the environment, but Article 5(2) delegates the actual method to
national executive regulations, which were not located in either country — the Act itself specifies no
quantitative method. Both pesticide branches are `*_GCC_PESTICIDES_ACT_NOT_MAPPED` accordingly.

Everywhere else, the two countries diverge:

- **UAE**: no REACH-equivalent chemicals regime confirmed (open gap, not a confirmed absence). Pesticide
  registration recently transferred from MOCCAE to the Emirates Drug Establishment (EDE, Federal Decree-Law
  No. 38/2024). Human pharma: EDE is the registering authority; a GCC-wide "Module 1" dossier structure is
  referenced regionally and Saudi Arabia's own confirmed Module 1.5 requirement (below) plausibly extends
  here, but this was **not confirmed on a UAE primary source** — reported as such, not assumed. Veterinary:
  Federal Decree-Law No. 21/2025 was enacted; secondary reporting describes an environmental-disposal
  element, but the primary legislative text was not read.
- **Saudi Arabia**: no REACH-equivalent regime confirmed either (SASO/SABER governs import conformity, not
  environmental risk). Pesticides: MEWA administers the GCC Act. **Human pharmaceuticals — the one genuinely
  confirmed, primary-sourced requirement found for either Gulf state**: the SFDA's own "Data Requirements
  for Human Drugs Submission" (DS-REQ-002-V4.0, read in full) contains Module 1 Section 1.5 "Environmental
  Risk Assessment", quoted directly in the registry docstring — a real requirement, modelled on the EU CTD
  structure, but the document itself specifies no quantitative PEC/PNEC method. Veterinary: SFDA's Drug
  Sector regulates veterinary medicines through the same Saudi Drug Registration system, but no
  veterinary-specific data-requirements guideline analogous to DS-REQ-002 was located, so whether the human
  Section 1.5 requirement extends to veterinary dossiers is explicitly unconfirmed, not assumed either way.

Neither AE nor SA got any calculable native model added (no FOCUS-suite extension, no EFSA screens) —
matching JP/CN/KR/IN's shape, not Norway's.

## Tests

- `tests/test_registry.py`: 4 new cases (Norway gets the full FOCUS suite at tier 3; Norway does NOT get the
  EFSA birds/mammals/bees screens even when `bee_attractive`; UAE and Saudi Arabia get zero calculable
  models for pesticides).
- `tests/test_workflow_registry.py`: region-count assertion updated (11 → 14); 6 new cases (Norway's
  industrial route is `"available"` not `"partial"`, confirming genuine EU-REACH equivalence; Norway's
  pesticide route names MACRO and the six/nine-scenario deviation; Norway's `refinement` is `"eu"`; UAE/Saudi
  pesticide routes name the shared GCC Act but stay `"partial"`; Saudi's confirmed SFDA requirement is named
  and distinguished from UAE's unconfirmed one).
- `tests/test_jurisdiction_separation.py`: extended the existing region round-trip regression tests (the
  ones that caught the JP/CN/KR/IN "stale Literal" bug class in an earlier session) to include NO/AE/SA —
  confirms `/api/assessment-plan` genuinely accepts all three, not just that the HTML tab exists.
- Live-verified in the browser (not just unit tests): clicked the Norway and UAE tabs in the running app,
  confirmed zero console errors, and read back the actual rendered regulatory-route text for each.

Full suite: 849 passed, 5 skipped (was 813, before this session's ecotox-database work; 806 before that).

## Not done — Brazil, Mexico, Singapore, Taiwan, South Africa

Three research agents were dispatched in parallel; two failed on a session rate limit before returning
results (Brazil/Mexico; Singapore/Taiwan/South Africa). These five countries remain unresearched and
unimplemented. Re-running that research (and then implementing it the same way as Norway/UAE/Saudi Arabia
above) is the direct continuation of "finish the countries" once resumed.

## An unrelated mistake made and corrected this session

While setting up a browser preview to verify the Norway/UAE tabs, a `Write` call to `.claude/launch.json`
overwrote a pre-existing file (it had two configured servers, `envirochem31` and `site-preview`) without
reading it first — the file wasn't visible in this session's context before the write. Caught immediately
via the server-not-found error on the first `preview_start` attempt. Restored the `envirochem31` entry
(confirmed correct, matches this project); `site-preview`'s original configuration is not recoverable (not
git-tracked) and was not guessed at — told to the user directly rather than silently reconstructed.
