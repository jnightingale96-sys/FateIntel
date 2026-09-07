# EnviroChem Studio v2.23.0 Alpha 3.2

Build ID:
`envirochem-studio-v2.23.0-alpha3.2-fifra-companion-models-2026-09-07`

## Baseline reconciliation

This release merges work that had diverged onto a separate, older lineage
(`2.23.0-alpha2`) back onto the authoritative `2.23.0-alpha3.1` baseline. No
Alpha 3.1 capability was removed, replaced or downgraded: the EPA execution
bridge (`app/services/external_execution.py`), the `POST
/api/model-workflows/{id}/execute` route, `regulatory_programme` plan
metadata, the pesticide-only workflow gate, the native-vs-official TOXSWA
separation, and the US run-state/spinner fixes from Alpha 3.1 are all
unchanged and still covered by their existing tests (`test_epa_execution_
bridge.py`, `test_jurisdiction_separation.py`, and the full pre-existing
suite — every prior test still passes, none were deleted).

## Added

- **FIFRA companion ecological models**, conditionally routed rather than
  shown indiscriminately: **AgDRIFT/AGDISP** (spray drift — only for
  drift-capable application methods), **TerrPlant** and **T-REX** (terrestrial
  plants, birds/mammals — baseline for outdoor pesticide use, dropped for
  enclosed-greenhouse use sites), and **BeeREX** (pollinators — only when the
  use site/crop is marked bee-attractive). Registered end-to-end: model
  registry entry, adapter contract, and a real field-level input template
  (application rate/method, meteorological conditions, toxicity endpoints,
  etc.) — not placeholder status flags.
- **Real per-model input forms.** The guided screen's "Prepare workflow"
  action previously sent a fixed, model-independent `input_data` object
  regardless of which model was selected, so no model — including the
  existing PWC — ever reached a genuinely complete "prepared" state with real
  inputs. A generic, data-driven form now reads the model's actual input
  template and collects real field values for any registered model (PWC,
  PRZM, AgDRIFT, TerrPlant, T-REX, BeeREX, and the existing SPIN/MACRO/
  GREATER/ChemSTEER/CEM/E-FAST), while preserving the existing
  `regulatory_scenario`/`contaminant_group`/`assessment_tier` provenance
  keys the pesticide gate and workflow-matching logic already depend on.
- **PWC's input template enriched** from bare `{"status": "required"}`
  section placeholders to real fields (application rate/method, PWC scenario
  ID, soil DT50, Koc/Kd, groundwater/waterbody configuration, etc.), with
  matching nested-field validation.
- **PRZM given a full model profile** (previously registered only as an
  adapter contract, with no input template or validation at all) — used both
  in its existing EU FOCUS role and the US FIFRA role, both preserved.
- Three new, explicitly agricultural-spray-only routing inputs on
  `/api/assessment-plan`: `application_method`, `use_site_category`,
  `bee_attractive` — typed as enums, not free strings, so an invalid value is
  a 422 rather than a silent no-op.
- The existing pesticide-only 422 gate on workflow creation (previously
  `{PWC, TOXSWA}`) extended to also cover AgDRIFT/TerrPlant/T-REX/BeeREX —
  **not** PRZM, whose applicability legitimately spans multiple contaminant
  groups across its EU and US uses.

## Deliberately not done this release

- **No local-execution support added** for PRZM/AgDRIFT/TerrPlant/T-REX/
  BeeREX. `EPA_EXECUTION_MODEL_KEYS` stays `{PWC, ChemSTEER, CEM, E-FAST}` —
  the only four with a real, operator-configurable executable path. The five
  pesticide-adapter models above are manual-handoff only (prepare → export
  manifest → run officially → import output → review), the same path PRZM
  already used before this release. Claiming `/execute` readiness for a model
  with no verified executable would be exactly the kind of overclaiming this
  project is trying to avoid.
- No changes to `app/config.py`, `external_execution.py`, or
  `toxswa_surface_water.py`.
- Still open: risk-characterisation engine, FDA pharmaceutical pathway, KABAM
  (bioaccumulation) and PFAM/Tier I Rice (flooded-application) models.

## Verification

- Full suite: 235 passed, 5 skipped (four optional native-RDKit tests, one
  optional `cryptography`-dependent test) — 226 pre-existing Alpha 3.1 tests
  unchanged plus 9 new FIFRA-routing tests.
- Manual browser verification: aerial + bee-attractive application routes
  PWC/AgDRIFT/TerrPlant/T-REX/BeeREX; switching to soil-incorporated +
  non-bee-attractive correctly drops AgDRIFT and BeeREX. A real AgDRIFT
  "Prepare workflow" form was filled and submitted end-to-end, reaching
  `status: "prepared"` with zero missing inputs. The pesticide-only gate was
  confirmed to reject a non-pesticide `contaminant_group` with 422.
