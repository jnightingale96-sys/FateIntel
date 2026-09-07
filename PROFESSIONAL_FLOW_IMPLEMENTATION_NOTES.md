# EnviroChem v2.11 — professional tiered-flow implementation

This pass follows the 16 August 2026 product-review notes and makes the guided interface reflect the scientific assessment sequence rather than the order in which modules happened to be developed.

## Assessment order

1. Identify chemical.
2. Define use and application/release.
3. Confirm regulatory pathway.
4. Select one executable emission scenario.
5. Show only compartments relevant to that scenario.
6. Run Tier 1–2 screening models.
7. Present pathway-specific exposure outputs and risk-data gaps.
8. Open EU FOCUS PEARL only when a soil PEC exists.
9. Open EnviroDesign after the exposure story, as an R&D design screen rather than a regulatory shortcut.

## Executable guided emission scenarios

- Municipal wastewater.
- Biosolids land application.
- Wastewater irrigation.

Direct surface-water release, direct-soil release and manufacturing-catchment release are visible as roadmap items but are labelled `Not wired`. The UI refuses to fabricate outputs for them.

## Scenario isolation

Wastewater does not automatically display biosolids, irrigation, crop or groundwater concentrations. Biosolids produces its own repeated-application soil series. Wastewater irrigation produces its own continuous/repeated irrigation soil series and optional crop screen. FOCUS PEARL is not invoked automatically by either soil pathway.

## Regulatory model systems

A top-level EU/US switch is present. EU enables the current FOCUS PEARL refinement. US PWC/PRZM/EXAMS execution is intentionally marked pending until the US scenario rules, inputs, executables and validation cases receive a dedicated implementation pass.

## EnviroDesign communication

The main molecular graphic uses the ordinary RDKit depiction. Fitted BIOWIN terms are separated from non-fitted structure inventory alerts. Human-readable structural regions now include benzene-like aromatic rings and transformation-sensitive motifs. Equation intercept and molecular-weight terms remain available but are demoted from the main scientific story.

## Visual system

The professional override removes rounded-card styling and heavy shadows from the main assessment surfaces. Borders are thin, corners are nominally square (2 px), pathway/model connectors are approximately 1 px, and active states use restrained left-edge indicators instead of large glow effects.
