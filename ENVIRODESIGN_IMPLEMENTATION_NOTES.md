# EnviroDesign v0.1 implementation notes

## Source material incorporated

The supplied `BIOWIN_enviPath_fragment_inventory.xlsx` contained:

- 41 reconstructed BIOWIN 3/4 SMARTS patterns;
- model-specific fragment coefficients;
- molecular-weight terms and intercepts;
- explicit coverage gaps for BIOWIN 1, 2, 5, 6 and 7;
- enviPath package identifiers, routes and metadata fields;
- beta-lactam and licensing implementation notes.

The workbook itself is not required at runtime. Its structured inventory was transcribed into versioned JSON files under `app/data/` so the executable calculation remains inspectable.

## Calculation layer

`app/services/envirodesign.py` provides:

1. `analyse_structure()`
   - RDKit parsing and canonicalisation;
   - formula, molecular weight, exact mass, logP, TPSA, rings and H-bond descriptors;
   - SMARTS matching;
   - BIOWIN 3 and 4 contribution trace;
   - structure alerts and cautious design hypotheses;
   - atom-highlighted SVG.

2. `compare_candidates()`
   - user-supplied candidates only;
   - protected SMARTS validation;
   - identical model treatment for original and candidates;
   - score and descriptor deltas;
   - no automatic winner.

3. `pathway_retention()`
   - imported observed/predicted products;
   - maximum common substructure;
   - fitted-fragment and structure-alert retention;
   - matrix and provenance preservation.

## Fitted model versus structural inventory

The UI deliberately distinguishes:

- **fitted contributions:** direct matches to the reconstructed BIOWIN terms;
- **structure inventory:** transparent RDKit alerts with no fitted coefficient;
- **pathway retention:** motifs present in imported products;
- **design hypotheses:** candidate experiments, not established redesign instructions.

This distinction prevents an aromatic scaffold or halogen from being labelled as a proven causal persistence determinant merely because it is chemically plausible.

## Beta-lactam handling

A separate four-membered cyclic-amide detector is included because the general amide fragment does not encode ring strain. The alert tells the user to distinguish:

- parent disappearance;
- beta-lactam ring opening;
- loss of antibacterial activity;
- ultimate degradation of ring-opened products.

## Audit and provenance

When project and chemical identifiers are supplied, each analysis is stored as a `ModelRun` with:

- model key and version;
- original input JSON;
- complete output JSON;
- scientific warnings;
- project audit event.

Model keys:

- `ENVIRODESIGN_BIOWIN34_ATTRIBUTION`
- `ENVIRODESIGN_CANDIDATE_COMPARISON`
- `ENVIRODESIGN_PATHWAY_RETENTION`

## Current limitations

- No claim of exact EPA BIOWIN reproduction.
- No automated chemical generation.
- No pharmacological or performance model.
- No direct enviPath database call.
- No automatic use of restricted external datasets.
- No regulatory-equivalence claim.
- No single composite “green score”; trade-offs stay visible.

## Next scientific work package

1. Validate counts and scores against official EPI Suite detailed output for a diverse benchmark set.
2. Add matched-molecular-pair evidence records with measured biodegradation endpoints.
3. Add pathway evidence import/export templates and transformation-product fate routing.
4. Add user-defined immutable pharmacophore and permitted-edit regions.
5. Connect candidate outputs to full WWTP, soil, groundwater, surface-water and ecotoxicity reassessment.
