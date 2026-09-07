# EnviroChem Studio v2.23.0 Alpha 2

Build ID:
envirochem-studio-v2.23.0-alpha2-us-exposure-foundations-2026-09-02

## Added

- Typed industrial release-event, source-citation and worker-task schemas.
- Native US industrial source-term and occupational exposure screen with exact
  mass closure.
- Measured-air and time-averaged well-mixed-room inhalation routes plus explicit
  dermal contact, absorption and PPE factors.
- EPA source catalogue with 12 published ESDs enabled and 48 draft records
  disabled by default.
- Conventional 15-domain assessment completeness control.
- Managed external workflow profiles and contracts for ChemSTEER 3.2, CEM 3.2
  and E-FAST 2014.
- Rights-aware evidence-source entries for EPA exposure tools and guidance,
  enviPath/EAWAG-BBD and KEGG xenobiotic pathways.
- Professional US Exposure Foundations workbench in the guided interface.
- US industrial, consumer and disposal routing in the assessment planner.

## Preserved boundaries

- Native output is not an EPA model result.
- EPA executables are not bundled, modified or redistributed.
- E-FAST is labelled legacy.
- Draft scenarios require explicit opt-in and remain labelled draft.
- Managed waste is a transfer and is not reported as destruction.
- Transformation pathways remain qualitative and licence-gated.

## Startup

The Alpha 1.1 Windows file-handle fix is retained. The browser-readiness helper
does not share STARTUP_LOG.txt with Uvicorn, and an occupied configured port is
resolved or safely replaced.

