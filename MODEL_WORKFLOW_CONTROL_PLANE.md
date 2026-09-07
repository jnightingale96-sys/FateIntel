# EnviroChem model workflow control plane

This build incorporates the complete model inventory as governed workflows:

- SimpleTreat
- Activity SimpleTreat
- SimpleBox 4.0 external workflow
- EnviroChem multimedia fate screen
- EPA EPI Suite 4.11
- FOCUS PEARL
- FOCUS TOXSWA
- GREAT-ER
- ePiE pharmaceutical exposure model
- EnviroChem catchment river-network screen
- FOCUS PELMO
- FOCUS MACRO
- PRZM
- EXAMS
- EPA Pesticide in Water Calculator 3 (PWC3)
- EnviroChem EU–US wastewater irrigation comparison
- EnviroChem soil accumulation screen
- EnviroChem plant uptake
- EnviroChem biosolids land application
- EnviroDesign structural biodegradation, pathway-retention and candidate-comparison screens

## What “incorporated” means

For every registered model, EnviroChem now manages:

1. jurisdiction and tier eligibility;
2. a model-specific required-input contract;
3. a canonical input manifest;
4. missing-input disclosure;
5. configured executable location, where applicable;
6. expected outputs and accepted file formats;
7. raw and structured output import;
8. model and executable version recording;
9. SHA-256 input and output hashes;
10. scientific review decision and notes;
11. project audit events;
12. downloadable run manifests.

Native calculations may be executed directly. Managed and legacy adapters still require model-specific writers, launchers and parsers to be completed, and authorised installations where redistribution is restricted.

## Status meanings

- **Working preset**: a functioning, bounded implementation with explicit limitations.
- **Working verified preset**: reproduced against the supplied workbook/example configuration.
- **Partial**: some equations or scenarios operate, but the full intended scope is not complete.
- **Adapter planned**: the control-plane contract exists; model-specific input generation, execution and output parsing remain to be completed.
- **Official adapter contract**: current model scope and versioned input/output boundary are registered; execution remains external.
- **Working native screen**: a directly executable, tested EnviroChem calculation whose boundary from official external models is explicit.

## New workflow

Open **Model Library**, select a model, and choose **Prepare workflow**. EnviroChem creates a versioned manifest and reports every missing input. After running an external model, import its output, record model versions, and complete a scientific review.
