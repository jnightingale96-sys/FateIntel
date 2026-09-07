# Transformation pathways implementation notes

## Scope

EnviroChem v2.22 uses BioTransformer ENVMICRO as an interim provider for predicted environmental microbial transformation products. The adapter accepts one confirmed parent SMILES and one to three transformation generations.

## Architecture

- `app/services/transformation_pathways.py` owns provider submission, polling, error handling and response normalisation.
- `GET /api/transformation-pathways/providers` reports availability, licensing status and scientific boundaries.
- `POST /api/transformation-pathways/predict` returns and optionally persists a provider-neutral graph.
- Graph nodes contain the parent or predicted TP identity. Edges contain provider reaction annotations.
- The browser copies products into an editable review list before EnviroDesign motif-retention analysis.

The internal schema is deliberately provider-neutral so a licensed enviPath adapter or validated local engine can be added later without changing downstream pathway review.

## Scientific boundary

BioTransformer proposes plausible structures and reactions. It does not establish occurrence, yield, formation fraction, rate constant, DT50 or environmental concentration. All returned products are stored as `model_predicted`; users must explicitly relabel products supported by analytical or literature evidence.

BioTransformer's environmental module is generic to soil/water microbiota and may include aerobic and anaerobic reactions. It is not a matrix-specific activated-sludge, soil, sediment or surface-water kinetic study.

## Licensing boundary

BioTransformer ENVMICRO uses enviPath/EAWAG-derived content. Local/test integration is provided for development and academic evaluation under the applicable terms. Staging and production requests fail closed unless an authorised operator explicitly confirms that the required commercial permission is held. No code setting can grant that permission.

## Operational boundary

- The documented public service limit is two POST requests per minute.
- Requests time out and fail visibly; EnviroChem never fabricates a pathway.
- The full provider response is not silently represented as measured evidence.
- A SHA-256 of the raw JSON response is retained with the provider query identifier.
- High-volume or confidential use should move to a licensed local/on-premise deployment or commercial API agreement.
