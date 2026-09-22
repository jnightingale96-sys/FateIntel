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

## Not done / open

- Region tabs UK, CH are still folded into "EU_UK_CH" as one tab, matching the original `modelSystem` design and
  `REGION_SETS`. The user's brief said "differing regions should have differing tabs" — read here as EU/US/CA/AU/NZ
  each getting their own tab (done), not necessarily UK and Switzerland splitting out of the EU tab too. If the user
  wants UK split out, `REGIONS` in `workflow_registry.py` is where that goes (add a `"UK"` key with its own
  `jurisdictions: ["UK"]`), but the existing `MODEL_SYSTEM_JURISDICTIONS` / `projectModelSystem()` detection and the
  `EU_UK_CH` `REGION_SETS` entry in `app.js` would need matching changes — not attempted.
- Tier 3/4 jurisdictions from the original brief (Japan, China, South Korea, India, ...) still have no region tab or
  workflow at all — `REGIONS` only covers the five already-built jurisdictions.
- The "tools" stage (EnviroDesign / Identification / Applied Environmental Fate) is offered as one stage for every
  native-organic group; it isn't itself broken down by group (e.g. Identification's MS-evidence tools might not be
  equally relevant to every organic group). Not investigated.
- No UI test that a *saved* assessment (an existing project) reopens into the workflow matching its own stored
  `contaminant_group` — only that live chooser interactions correctly retarget the screens. If a stored project has
  a group unset (the common case for existing pre-this-feature projects), the shell just falls back to whatever
  group the use-card implies at that moment, same as before this feature existed.
