# Ecotox databases — coverage review and CompTox connector

## Why

User (2026-09-23): "include all ecotox databases available online, and then move on please." This is a
review-and-close-gaps pass over every ecotoxicology data source this app already catalogues in
`app/data/evidence_source_registry.json`, not a request to build a new registry from scratch — that
registry already names essentially every major public ecotox database (US EPA ECOTOX/CompTox, EFSA
OpenFoodTox, NORMAN Ecotoxicology DB, OECD eChemPortal, ECHA CHEM, AERU VSDB/PPDB, PREMIER, UBA PHARMS,
FASS, Janusinfo, NIHS Japan) with an honest `access_mode`/`integration_status` for each. The work here was
finding which of the not-yet-`search_enabled` entries could honestly become live, and building the one that
could.

## What was already there (no action needed)

- **`epa_ecotox` (US EPA ECOTOX Knowledgebase)** — already the most comprehensive live ecotox source in the
  app: a local bulk-import connector (`app/services/ecotox_local.py`) reading a 203 MB JSONL the user
  already imported from EPA's own ASCII bulk export (`data/ecotox_reference.jsonl`, `data/ecotox_index.json`
  — confirmed present, 725,600+ tests / 1,250,600+ results / 18,550+ chemicals at import time). Aquatic-medium
  LC50/EC50/NOEC/EC10 only, by design (see `scripts/import_ecotox.py`'s own docstring) — already
  `search_enabled: true`. Nothing to add here; this remains the authoritative source, confirmed again below.
- **`pubchem`, `europe_pmc`** — already live, already `search_enabled: true`.

## What was correctly left gated (checked, not changed)

- **`aeru_vsdb`, `aeru_ppdb` (AERU VSDB/PPDB)**, **`premier`**, **`kegg_xenobiotics`** — commercial licence /
  formal letter of access required. Not something this session can resolve; still `licence_gate_ready` /
  `rights_gate_ready`, correctly.
- **`norman_ecotox` (NORMAN Ecotoxicology Database)** — genuinely CSV/manual-download only, no live REST API
  (matches the same finding already made for NORMAN SusDat/EAWAGTPS in the analytical-identification work).
  A local bulk-import connector following the exact `ecotox_local.py` pattern is a legitimate, low-risk
  future addition, but needs the user to obtain the export first and confirm reuse terms
  (`commercial_status: reuse_terms_to_confirm`) — flagged as a follow-up (see below), not built this session
  to respect "move on."
- **`oecd_echemportal`, `echa_chem`** — discovery/linkout only; eChemPortal has no confirmed machine-readable
  search API, and ECHA CHEM's note already flags third-party rights review as outstanding. Left as-is.
- **`ecodrug_plus`** — real `open_live_api`, no key required, but its actual data (mechanism of action,
  cross-species target conservation) isn't concentration-response ecotox data — a different kind of evidence
  than "ecotox database" implies. Left `search_enabled: false` for now; a real candidate for a future,
  separate connector, not part of this pass.

## What was built: the EPA CompTox / CTX Hazard API connector

**New file**: `app/services/epa_comptox.py`, wired into `evidence_sources.search_sources()`. Closes a
standing gap named in memory ("EPA CTX API key stored in local gitignored .env, no connector built yet") —
the key (received by email 2026-09-21) had been sitting configured but unused.

**Endpoints, confirmed live against the real OpenAPI specs** (read directly via the built-in browser —
`https://comptox.epa.gov/ctx-api/docs/chemical.json` and `.../hazard.json`, piercing the RapiDoc web
component's shadow DOM to fetch the spec JSON rather than trusting rendered/summarised text):
- `GET /chemical/search/equal/{word}` — resolves a CAS number, name, DTXSID or InChIKey to a DTXSID.
  Live-verified: CAS `1912-24-9` → `DTXSID9020112` ("Atrazine").
- `GET /hazard/toxval/search/by-dtxsid/{dtxsid}` — returns the full ToxValDB record set for that substance.
  Auth: header `x-api-key` (confirmed from the spec's `securitySchemes`).

**The finding that matters most**: live-tested against seven real chemicals (atrazine, permethrin, PFOS,
bisphenol A, copper, tributyltin oxide, phenol) — 1,832 ToxValDB records total, **every single one**
`humanEco == "human health"` with `speciesSupercategory == "Mammals"`. This includes 448 atrazine records
whose `source` field is literally `"ECOTOX"` — confirming EPA's own ECOTOX Knowledgebase also curates
mammalian lab-animal studies used for human-health risk assessment, and that this API endpoint surfaces
*those*, not ECOTOX's aquatic/avian/invertebrate side. Direct comparison: the same atrazine CAS number has
**4,414** aquatic LC50/EC50/NOEC/EC10 records in this app's own local ECOTOX bulk import — **zero** of which
came back through this API. EPA's own landing page describes "Hazard APIs" as covering "human and
ecotoxicology data," and the `ToxValDb` schema genuinely has `humanEco`/`speciesSupercategory` fields built
to carry non-mammalian records — but as publicly deployed today, this was not observed once across seven
chemicals and 1,832 records.

**What the connector does about it, honestly**: it still filters for `humanEco == "eco"` (not abandoned or
faked) — correctly matching the real schema — so any eco-classified record EPA publishes here in the future
surfaces automatically without another code change. The expected, correctly-filtered status for most
chemicals today is `no_eco_records_found`, not `ok`, and every result carries the live-tested caveat in its
warnings. The module docstring and the `evidence_source_registry.json` note both say plainly: **do not rely
on this source for aquatic/avian ecotoxicity coverage; `epa_ecotox`'s local bulk import remains
comprehensive for that.**

**Field mapping discipline**: `toxvalType` values that are themselves literal endpoint codes this app's
`ENDPOINT_CATALOG` already has slots for (`LC50`, `EC50`, `NOEC`, `EC10` — confirmed as literal `toxvalType`
values in the real data; e.g. eight real `"LD50"` records were observed) map to the matching property code.
Any other eco record is still surfaced, never dropped, with `property_code: null` and a note — the same
"don't force an unmapped value into an existing slot" rule `ecotox_local.py` already follows. ToxValDB's `"-"`
string sentinel (its own "not populated" marker, not null) is normalised to `None` throughout, so a doi/
guideline/riskAssessmentClass of `"-"` is never surfaced as if it were a real value.

**Registry updated**: `epa_comptox`'s `search_enabled` → `true`, `integration_status` → `"live"`, notes
extended with the live-tested finding. `app/config.py`'s `comptox_api_key` field comment updated to point at
the module instead of saying "no live connector reads it yet."

**Tests**: `tests/test_epa_comptox.py`, 7 new cases (`httpx.MockTransport`-injected, matching the established
`test_envipath.py` pattern — no live network calls in the suite) — api-key-missing, no-match, the real
live-observed all-human-health shape correctly reported as `no_eco_records_found` (not `ok`), a synthetic
eco record correctly mapped to `ECOTOX.AQUATIC.LC50` (built to the real confirmed schema, explicitly labelled
synthetic in the test file's own docstring since no real eco record was ever observed), an eco record with an
unmapped `toxvalType` still surfaced rather than dropped, the `"-"` sentinel normalised to `None`, endpoint-
code filtering, and the `limit` cap. One assertion added to `tests/test_evidence_sources.py`'s existing
registry test. Full suite: 813 passed, 5 skipped (was 806).

## Follow-up not done this session (respecting "move on")

A NORMAN Ecotoxicology Database local-import connector, mirroring `ecotox_local.py`/`scripts/import_ecotox.py`
exactly, would be a legitimate next ecotox-database addition — but needs the user to obtain NORMAN's export
and confirm reuse terms first (`commercial_status: reuse_terms_to_confirm` in the registry), so it wasn't
started here.
