# EnviroChem Studio v2.23.0 Alpha 2.1

Build ID:
`envirochem-studio-v2.23.0-alpha2.1-jurisdiction-routing-2026-09-04`

## Corrected

- The EU/US switch now changes the regulatory programme and model route rather
  than removing shared real-world exposure scenarios.
- Agricultural spray, manufacturing/processing, household use, product
  disposal, direct surface-water release and soil exposure can be selected in
  either jurisdiction.
- EU-only FOCUS controls and US-only model cards are visibly separated.
- The assessment planner is now used by the guided screen for both jurisdictions
  and returns a named regulatory programme with scenario-specific inputs and
  warnings.
- PWC is selected only for relevant US pesticide-water scenarios. PRZM can occur
  in either FOCUS or US pesticide workflows, with jurisdiction, scenario set and
  version required in provenance.
- Laboratory use now maps to a valid industrial-organic assessment group instead
  of the invalid `workplace` registry value.
- Switching jurisdiction clears stale results and advanced-refinement state but
  preserves the selected exposure scenario.
- Workflow status is read from real `ModelWorkflow` records and filtered by both
  jurisdiction and regulatory scenario.
- EU and US assessment projects are not silently reused across tabs. Native
  guided model-run names include the selected jurisdiction.

## Preserved scientific and regulatory boundary

- A prepared workflow is an input/output/review control record; it is not an
  official model result.
- PWC, ChemSTEER, CEM, E-FAST and official FOCUS executables are not embedded or
  executed by this build. Their output can be represented only after genuine
  external execution, import and review.
- Shared native process calculations are EnviroChem screening results, not EPA,
  ECHA or FOCUS submission outputs.
- Full REACH consumer/worker exposure and waste-stage calculations, and complete
  US consumer, disposal and pesticide model adapters, remain roadmap work.

## Verification

- JavaScript syntax check.
- Focused Python lint check.
- Full automated test suite: **216 passed**, with five optional tests skipped
  (four native-RDKit checks and one RSA check because those optional packages
  were not installed). This includes EU/US leakage, shared-scenario routing,
  project-jurisdiction and workflow-provenance regression checks.
