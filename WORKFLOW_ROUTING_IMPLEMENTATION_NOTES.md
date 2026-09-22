# Assessment workflow routing — implementation notes

Running log. Add to it; don't replace it.

## Why

User feedback (2026-09-22): "land contamination should not be in the organic chemical risk assessments... think
about flow, and what can pop up when the chemical group is selected. Same, differing regions should have differing
tabs and workflows — similar to EU but following their risk assessment flow."

Before this, the guided page showed every screen to every assessment regardless of chemical group: a human
pharmaceutical assessment carried the "Contaminated land" nav item and section in its DOM (hidden only by the
site-model's own gating, not by chemical relevance), and Canada/Australia/New Zealand, once added as
`model-system` tabs, fell back to EU or US copy and screens (`state.modelSystem === 'EU' ? ... : ...` patterns
throughout `app.js`) because nothing distinguished "not EU" from "US".

## What was built (2026-09-22, git 7c9bc3e config, f81c578 feature)

- **`app/services/workflow_registry.py`** — new module. For a `(region, chemical_group)` pair it returns:
  - which track(s) apply: `use_release` (identify → use/release → native screen → refine → tools → review),
    `site` (identify → build the site model → regional method → review), or neither for `radionuclide` /
    `contaminated_mixture` (hard-blocked: only the identity card and the regulatory-route card remain);
  - the ordered stages of each track, each carrying a status (`available` / `managed_external` /
    `external_required` / `partial` / `not_built` / `not_established`) and a plain-language detail/note;
  - which of the app's existing screens ("modules": evidence, assessment, plan, results, water_sediment, pearl,
    us_models, envirodesign, identification, kinetics, contaminated_land) belong to the resolved track.
  - It **invents no new regulatory fact**: route text comes from `registry._regulatory_programme()`; the site
    track's regional methods come straight from `conceptual_site_model.EXTERNAL_ROUTES` /
    `NOT_ESTABLISHED`; "native screen applies" is `registry.DISCRETE_ORGANIC_GROUPS`. It only arranges what
    already existed.
  - `FAMILIES`: the chemical-group groupings shown in the chooser, and — this is the one **product decision**
    made here, not a regulatory claim — which families get the `site` track at all: metals, legacy persistent
    organics (PCBs/PAHs/organotins), petroleum hydrocarbons/solvents and PFAS. Everything else (pharma,
    industrial, pesticides, personal care, polymers, UVCBs, mixtures) is `use_release`-only. This list should be
    revisited if the legacy-contaminants expansion adds more site-relevant groups (cyanide, nutrients — see
    `LEGACY_CONTAMINANTS_IMPLEMENTATION_NOTES.md`'s "not built" list).
  - `REGIONS`: EU_UK_CH, US, CA, AU, NZ. Only EU_UK_CH ("eu") and US ("us") have a dedicated refinement screen
    set built; CA/AU/NZ say so plainly (`status: not_built`) rather than borrowing EU or US screens or copy.
  - New routes: `GET /api/workflow/reference` (chooser data), `GET /api/workflow?region=&group=&scenario=`.
- **`app/static/flow-shell.js` / `.css`** — new "Assessment setup" panel between the region tabs and the
  evidence hub: chemical family → group (when a family has more than one) → track chooser, then a stage rail
  built from `resolve_workflow()`. It toggles `.flow-hidden` on the sections/nav-items *not* in the current
  workflow's modules. **Fails open**: if `/api/workflow` errors, nothing is hidden and the note says so — a
  registry bug can never make a screen disappear that a user needs.
  - Two-way sync with the existing use-cards: picking a chemical group clicks the matching use card (so the
    pharma/veterinary panels still work), and clicking a use card updates the group (`onUseCardClicked`).
  - The contaminated-land jurisdiction `<select>` is nudged to stay inside the active region's jurisdictions.
- **`app/main.py`, `app/static/app.js`, `app/static/index.html`** — five region tabs instead of two; `state.flowGroup`
  overrides the use-card-implied group in `regulatoryProductClass()`; every `state.modelSystem === 'EU' ? X : Y`
  fallback pattern that assumed only two regions now branches on EU / US / other (`regionKind()`, `regionName()`)
  so CA/AU/NZ get their own wording, never EU's or US's.

## Verified

- `tests/test_workflow_registry.py`: 69 cases (every group assigned to exactly one family; contaminated land never
  appears for organic-use groups and does appear for the site-relevant ones; blocked groups keep only the route
  card; EU/US refinement screens are exclusive to their own region; CA/AU/NZ state "not built" and name their own
  regulator; site-track methods mirror `EXTERNAL_ROUTES` exactly; unknown region/group → 422; API round-trip).
- Two existing `tests/test_jurisdiction_separation.py` assertions updated for the 5-option region select and the
  `us`-not-`eu` visibility rule (`data-us-only-model` now toggles on `!us`, not `eu`).
- Full suite: 676 passed, 5 skipped (was 607 before this session; +69 new).
- `scripts/browser_check_flow.py` (new): 47/47 checks per engine in Chromium, Firefox and WebKit — region/group/
  track switching, screen and nav visibility per group, the blocked-radionuclide state, use-card ↔ group sync,
  CA/AU/NZ wording and screen absence, the contaminated-land jurisdiction following the active region, no
  horizontal overflow, and the registry-failure fallback (screens stay visible, note explains why).
- `scripts/browser_check_contaminated_land.py` updated: it now picks "Metals and metalloids" before opening the
  section, since Contaminated Land is correctly hidden on first load (human pharmaceutical is the default group).
  67/67 in all three engines. Also fixed in passing: a Windows-console `UnicodeEncodeError` in that script's own
  failure-printing path (cp1252 can't render every page character a failure detail quotes) — unrelated to this
  feature, caught while re-running it after the change above.
- Manually re-checked against the real server (port 8793, real database, read-only — no saves) after the automated
  runs: default load hides contaminated land and shows the assessment flow; choosing "Metals and metalloids" flips
  both and opens on the site track with "No exposure or risk is calculated" in the rail.

## Follow-up (2026-09-22): UK/Switzerland split, Japan/China/South Korea/India added

User: "Split UK and Switzerland into there own tabs, and then get to work on Japan, China, South Korea, and India."
Both done and committed same day (git 673a9f3 UK/CH split, 3b318ad JP/CN/KR/IN). Research for the four new
countries is in `REGION_RESEARCH_JP_CN_KR_IN.md` (sources, retrieval dates, and an explicit "what wasn't verified"
section — read that before extending any of the four).

**UK/CH split** surfaced and fixed a real, separate bug while touching this code:
`registry._regulatory_programme()`'s tail used to be an unguarded default that any jurisdiction other than
US/AU/CA/NZ fell into, so a UK or Switzerland assessment was silently told it was routed through "EU REACH" —
wrong for both. Each jurisdiction now has an explicit branch (EU/UK/CH/US/AU/CA/NZ/JP/CN/KR/IN), and a jurisdiction
with none returns an honest `JURISDICTION_NOT_MAPPED` result instead of inheriting someone else's wording.

**Also found and fixed**: `AssessmentPlanCreate.jurisdiction` in `app/schemas.py` was `Literal["EU","UK","US","CH"]`
— AU/CA/NZ were added to the tabs in an earlier session without this Literal being updated, so `/api/assessment-plan`
(the older "regulatory plan" card) silently 422'd for all three the whole time. Undetected because the newer
"Assessment setup" stage rail calls `_regulatory_programme()` directly, never through this endpoint. Now covers all
eleven regions. **There are four more schemas with the exact same stale `Literal["EU","UK","US","CH"]` pattern**
(`ModelWorkflowCreate`, `JurisdictionalQuantityInput`/`CrossJurisdictionComparisonCreate`,
`OrchestrationModelResultInput`, `OrchestrationPlanCreate`/`OrchestratedAssessmentCreate`) — deliberately NOT
touched this session, because unlike `AssessmentPlanCreate` these are tied to the model-workflow-lifecycle and
Tier-orchestration features, which may be intentionally EU/UK/US/CH-scoped (the cross-jurisdiction comparison
feature in particular reads as designed for exactly those four). Confirm intended scope before touching them.

**Japan/China/South Korea/India**: each gets its own tab, its own regime name, and `refinement: None` (no
dedicated screen suite, same as CA/AU/NZ). None of the four was researched to the quantitative
PEC/PNEC-assessment-factor depth AU's AICIS route or CA's Okonski method were — every `_regulatory_programme`
branch for these four honestly says so (`status: partial`, never `available`), except Japan's pesticide route,
which does name a real mechanism (a Predicted Environmental Concentration criterion under the Agricultural
Chemicals Regulation Act). India's industrial-chemicals branch explicitly does NOT claim the draft "India REACH"
(CMSR, still on its fifth public draft) as an enacted regime — it routes to the currently-in-force MSIHC 1989
instead. Contaminated-land routes (`EXTERNAL_ROUTES`) are receptor-limited to what each source actually named:
Japan and South Korea (human only), China (human + ecological, from its own Article 1), India (all four receptor
classes — the only one of the four whose 2025 Contaminated Sites Rules names soil, groundwater, surface water and
sediment together).

## Not done / open

- The four other stale-Literal schemas noted above (model-workflow lifecycle, cross-jurisdiction comparison,
  orchestration) — not touched, scope not confirmed.
- No quantitative environmental risk-assessment method for JP/CN/KR/IN's industrial chemicals or pesticides
  (beyond Japan's named PEC criterion) — every one of those routes says "not yet mapped", honestly.
- South Korea's Agrochemicals Control Act administering body (Ministry of Agriculture vs. Rural Development
  Administration) was not fully confirmed — see `REGION_RESEARCH_JP_CN_KR_IN.md`.
- Human/veterinary pharmaceutical pathways for China, South Korea and India were not researched at all (Japan's
  was, via secondary academic sources only, not the MHLW notification itself).
- Tier 3/4 jurisdictions beyond these four from the original brief (Switzerland is now done; Brazil, Mexico,
  Norway, Singapore, Taiwan, the Gulf states, South Africa, ...) still have no region tab or workflow.
- No UI test that a *saved* assessment reopens into the workflow matching its own stored `contaminant_group` —
  only that live chooser interactions correctly retarget the screens (unchanged from the original note above).
- The "tools" stage (EnviroDesign / Identification / Applied Environmental Fate) is offered as one stage for every
  native-organic group; it isn't itself broken down by group (e.g. Identification's MS-evidence tools might not be
  equally relevant to every organic group). Not investigated.
- No UI test that a *saved* assessment (an existing project) reopens into the workflow matching its own stored
  `contaminant_group` — only that live chooser interactions correctly retarget the screens. If a stored project has
  a group unset (the common case for existing pre-this-feature projects), the shell just falls back to whatever
  group the use-card implies at that moment, same as before this feature existed.
