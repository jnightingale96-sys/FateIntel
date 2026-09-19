# Ecotoxicology database integration + multi-chemical screening — working notes

Started 2026-09-18. This file is the running log for this work package: bringing structured
ecotoxicological evidence (PNEC/NOEC/EC50/LC50/etc, per compartment and trophic level) into
FateIntel's evidence pipeline, and adding multi-chemical (batch) screening. Updated as work
proceeds; not a release-notes file (see `RELEASE_NOTES_v2.23.0-*.md` for those) — this is the
scratch-to-shipped record for this specific package.

## 2026-09-18 — Understanding the current state (no code changed yet)

**Ecotox evidence today is literature text-mining, not structured database access.**
`app/services/evidence_sources.py`'s `ECOTOX_RE` regex extracts LC50/EC50/EC10/NOEC mentions from
PubChem/Europe PMC abstract and full-text snippets — genuinely useful for surfacing candidates a
reviewer can read in context, but it never queries a real ecotoxicology database's structured
records (species, exposure duration, test guideline, effect value with proper units) directly.

**The evidence-source registry already names the right candidates, but none are wired up.**
`app/data/evidence_source_registry.json` has had `epa_ecotox`, `efsa_openfoodtox`, `norman_ecotox`,
`echa_chem`, `epa_comptox` and others cataloged for a while, each with real homepage/docs URLs and
an honest `access_mode`/`integration_status`. But `search_sources()` in `evidence_sources.py` only
has live implementations for two keys (`pubchem`, `europe_pmc`) — every other source falls through
to `"Adapter registered but live search implementation is not yet enabled."` This is the real gap:
cataloging was done, connectors were not built.

**`app/reach/pnec.py`'s `derive_pnec()` already has the right shape to receive real data.** It
takes a reviewer-supplied endpoint value/unit/type and assessment factor and does the arithmetic
transparently — it does not currently source the endpoint value itself. A real ecotox connector
should feed *into* this (and into `canada_pnec.py`/`nz_levels_of_concern.py`/`pmra_pesticides.py`'s
equivalent reviewer-supplied-value pattern), not bypass it. `derive_pnec()` is also still
freshwater-only (`target_compartment != "freshwater"` raises) — see
`fateintel_model_coverage_review.md` memory item 1, the highest-leverage pre-existing gap: sediment,
soil and secondary-poisoning PNEC derivation doesn't exist at all yet. Bringing in real sediment/soil
ecotox data without also building those PNEC pathways would produce numbers with nowhere correct to
go, so the two problems are linked.

**No multi-chemical/batch screening exists.** Every route in `app/main.py` operates on a single
`chemical_id`. There is no "screen this list of 40 chemicals" workflow, endpoint, or UI screen.

## 2026-09-18 — Free/open ecotox database research (live-verified, not recalled)

Verified this session via EPA's own GitHub source (`USEPA/ctxR`, `dev` branch), not documentation
prose alone, since the prose pages were JS-rendered and the R package source has the literal URLs:

- **EPA ECOTOX Knowledgebase**: no general live REST API for arbitrary per-chemical queries.
  Primary access is a full-database ASCII bulk download, refreshed periodically
  (`cfpub.epa.gov/ecotox`), covering both aquatic AND terrestrial species/effects — 1.1M+ test
  records, ~14,000 species, ~13,000 chemicals. Community tooling (`ECOTOXr`, `REcoTox` R packages)
  builds a local SQLite database from this dump. This matches the registry's existing
  `open_download_import` access mode — it was already correctly characterized.
- **EPA CTX Hazard API (ToxValDB)**: a genuine live per-chemical REST API,
  `GET https://api-ccte.epa.gov/hazard/toxval/search/by-dtxsid/{DTXSID}`, header `x-api-key`,
  free API key via `ccte_api@epa.gov`. **Important finding**: the API used to have a pre-filtered
  ecotox-only endpoint (`/hazard/eco/search/by-dtxsid/{DTXSID}`) but it is now **deprecated** as of
  ctxR v1.1.3 ("due to updates and restructuring of the CTX APIs") with no documented direct
  replacement found this session — the current approach is to call the general `/toxval/...`
  endpoint (returns human + eco records together) and filter client-side. The exact field used to
  distinguish eco from human records in a live response was NOT observed this session (would need
  an actual API key + one real call to confirm — same "spike before trusting the shape" discipline
  already used for the enviPath and MassBank connectors). `epa_comptox` is already registered with
  `requires_api_key: true, integration_status: api_key_ready` — someone with a key could verify this
  in minutes.
- **EFSA OpenFoodTox 3.0**: structured ecotoxicology data (plus physchem/fate/human+animal toxicity)
  as an official Excel/IUCLID export, pesticide-and-food-chemical-focused but scoped as
  `all_chemicals` too. Registry already correctly marks this `open_download_import`.
- **NORMAN Ecotoxicology Database**: has explicit "Lowest PNEC" values (expert-selected
  prioritization values, not a regulatory selection) alongside raw experimental endpoints. Access is
  CSV linkout, not an API — registry's `manual_linkout_csv` is accurate.
- **ECHA CHEM**: REACH-registered-substance ecotoxicity study results exist but access is manual
  linkout; third-party data rights complicate bulk reuse — registry's caution here is accurate and
  should stay as-is pending a rights review, not be quietly upgraded to a connector.

**Not yet checked this session, flagged as open**: whether ECHA has grown a genuine dissemination
API since the registry was last reviewed (worth one more targeted check before deciding the ECHA
CHEM entry is final); USEtox's own ecotoxicity effect-factor dataset (LCA characterization factors —
different purpose than a regulatory PNEC, previously ruled out as out-of-scope, revisit only if the
work package's framing changes); whether EPA ECOTOX's bulk ASCII download is the right shape to
import into a queryable local table, or whether starting from CompTox's Hazard/ToxValDB API (which
already aggregates ECOTOX among its sources) is a smaller first step with a narrower but still real
payoff.

## 2026-09-19 — Sediment/soil PNEC via equilibrium partitioning (shipped)

Built `app/services/equilibrium_partitioning.py`: `derive_pnec_sediment_from_water()` and
`derive_pnec_soil_from_water()`, both converting an already-derived PNECwater into a PNECsediment
or PNECsoil using the EU TGD's equilibrium partitioning method (EPM). This closes memory item 1
(the single highest-leverage pre-existing gap) for the EPM-derivation case specifically —
`app.reach.pnec.derive_pnec()` remains freshwater-only and continues to hard-reject other
compartments; it was deliberately left alone rather than reworked, since EPM is architecturally a
different kind of derivation (a fixed partitioning conversion from Koc, not a reviewer-chosen
assessment factor applied to toxicity data).

**Verified against a real primary source, not recalled**: read ECETOC Technical Report No. 92
("Soil and Sediment Risk Assessment of Organic Chemicals", Dec 2004) in full — Appendices A and B
reproduce the EU TGD's own equations and worked-example simplifications verbatim. Every constant
in the new module was cross-checked against those worked examples arithmetically before shipping:
soil matched the source's own simplified formula (PNECsoil = Koc × PNECwater / 85) to floating-point
precision; sediment matched the source's *rounded* illustrative formula (PNECsediment ≈ PNECwater ×
(0.783 + 0.0217 × Koc)) to within the rounding error those two constants carry — the module's own
unrounded arithmetic is the more precise, correct form, confirmed by deriving the exact
coefficients (0.9×1000/1150 and 0.1×0.1×2500/1000×1000/1150) independently and getting an exact
match.

**A real, worth-noting finding surfaced by reading the primary source in full**: the TGD applies
an extra ×10 factor to the PEC/PNEC ratio for chemicals with log Kow > 5 (uncertainty about
additional exposure via ingestion of sorbed sediment/soil particles). ECETOC's own Task Force
report is explicitly critical of this factor — it's applied to the wrong side of the ratio by the
TGD's own logic, isn't supported by the data ECETOC reviewed, and their own re-derivation from Di
Toro et al (1991)'s underlying theory puts the correct maximum nearer 2.5, not 10. Given that
documented controversy, the new module never applies this factor automatically — it's exposed as
an optional `high_log_kow_factor` argument a reviewer supplies explicitly, with the controversy
named in the docstring, consistent with FateIntel's reviewer-supplied-not-inferred discipline used
everywhere else (`app.reach.pnec`, `canada_pnec.py`, `pmra_pesticides.py`, etc).

**PNECsediment is returned both wet and dry** (the TGD's own equation produces a wet-sediment
value; the TGD's own fixed 2.6 wet:dry conversion factor, also verified from the same source, is
applied for the dry-weight figure most monitoring/toxicity data are actually reported in).

**Still not covered — named explicitly, not silently skipped**: secondary poisoning PNEC (oral,
for birds/mammals via the food chain) is a structurally different derivation — NOEC/NOAEL from a
feeding study divided by an assessment factor, not an EPM conversion — and was not built this
session; it's the other half of memory item 1 and a natural next step. Direct (non-EPM) PNEC
derivation from real sediment/soil toxicity data (ECETOC TR No. 92 Tables 2/3's own assessment
factors) also wasn't built — a reviewer with that data should currently just use
`app.reach.pnec.derive_pnec`-style explicit-AF arithmetic by hand; a dedicated helper mirroring
`canada_pnec.py`'s pattern would be a reasonable follow-on.

10 new tests, full suite green (427 passed, the one failure is the pre-existing
`test_v223_identity_isolation.py` flake, unrelated — this work touches no database/identity code).

## 2026-09-19 — EPA ECOTOX bulk import (shipped)

Built the full pipeline: `scripts/import_ecotox.py` (one-off/refresh importer, not a runtime
dependency) + `app/services/ecotox_local.py` (query connector, wired into
`evidence_sources.search_sources()`'s existing dispatch under `epa_ecotox`).

**Verified against the real, live bulk download this session, not a sample or mock**: downloaded
EPA's actual current export (`https://gaftp.epa.gov/ecotox/ecotox_ascii_09_15_2026.zip`, 137MB
zipped / 1.26GB uncompressed), inspected every file header directly (`tests.txt`, `results.txt`,
`validation/chemicals.txt`, `validation/species.txt`, `validation/references.txt`,
`validation/endpoint_codes.txt`, `validation/media_type_codes.txt`) before writing any parsing
code, then ran the importer against the real 55-file archive end-to-end.

**Real output**: 211,477 aquatic-medium LC50/EC50/NOEC/EC10 records across 5,305 chemicals,
written to `data/ecotox_reference.jsonl` + `data/ecotox_index.json` (CAS -> byte-offset index,
same JSONL+index pattern already used for NORMAN SusDat, not a new storage technology). Spot
-checked against a real chemical (formaldehyde, CAS 50-00-0): 263 real records, correct species
(Daphnia magna, Scylla serrata, Macrobrachium rosenbergii), correct values/units, real citations
with DOIs where available.

**Scope decisions, both deliberate and both explained in the script's own docstring**:
- Filtered to `results.endpoint` in {LC50, EC50, NOEC, EC10} -- matches FateIntel's existing
  `ENDPOINT_CATALOG` codes exactly (confirmed these are ECOTOX's own literal string codes, no
  fuzzy mapping needed).
- Filtered to `tests.media_type` in {AQU, FW, SW} (aqueous/fresh water/salt water) -- ECOTOX's
  LC50/EC50/NOEC/EC10 codes span BOTH aquatic and terrestrial studies; without this second
  filter, terrestrial dietary-dose results would get mislabelled as `ECOTOX.AQUATIC.*` evidence,
  a real correctness bug, not a simplification. Confirmed via `validation/media_type_codes.txt`
  and a direct count against the real data (346,979 of 725,636 tests are aquatic-medium).
- Deliberately NOT filtered by concentration unit -- a reviewer may still want to see a record in
  ppm/uM/etc even though `app.reach.units` doesn't auto-convert it yet; unit handling stays a
  review-time decision like every other evidence candidate in this app.

**Neither `data/ecotox_reference.jsonl` nor `data/ecotox_index.json` is committed to git** (added
to `.gitignore` alongside the existing `data/*.sqlite` pattern) -- both are build artifacts a
reviewer regenerates by re-running the import script against a fresh quarterly EPA release, the
same way the project already treats the runtime SQLite database. `app/services/ecotox_local.py`
returns an explicit `"not_imported"` status (never a silent empty result) when they're absent.

**Registry updated honestly**: `epa_ecotox` in `evidence_source_registry.json` flipped from
`search_enabled: false` / `integration_status: "registry_and_download_staging"` to
`search_enabled: true` / `integration_status: "local_import_search"`, with the notes field naming
the exact current scope (aquatic-only, ~211k/~5.3k chemicals as of the 2026-09-15 EPA release) so
nobody mistakes this for full ECOTOX coverage.

9 new tests (fixture-based, not depending on the 137MB download being present), full suite green
(436 passed; the one failure is the same pre-existing `test_v223_identity_isolation.py` flake,
a *different* sub-test failed than the last time it was seen this session -- consistent with the
documented order-dependent-DB-state characterization, not a regression from this work).

**This completes the ecotox database work planned for this session** (PMRA/CTX API is still
blocked on the pending EPA key; EFSA OpenFoodTox and batch/multi-chemical evidence gathering are
still open, queued after the website repositioning work now underway).

## Open questions for the next session

1. Which source to build a real connector for first: EPA ECOTOX bulk import (broadest, aquatic +
   terrestrial, but a bulk-download-and-local-query undertaking) vs. EPA CTX Hazard/ToxValDB live API
   (narrower per-call, needs an API key and a real spike call to confirm eco-vs-human filtering, but
   much less infrastructure)?
2. Does sediment/soil/secondary-poisoning PNEC derivation (memory item 1, `app/reach/pnec.py`) need
   to be built alongside this, or is aquatic-only ecotox evidence the right first slice?
3. For multi-chemical screening: is the ask a batch *evidence-gathering* workflow (run
   ecotox/evidence search across N chemicals), a batch *assessment-plan* workflow (run
   `build_assessment_plan` across N chemicals against one jurisdiction/scenario), or both?
