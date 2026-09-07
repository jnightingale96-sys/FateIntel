# EnviroChem Studio v2.13 — Evidence Data Hub implementation

## Purpose

The Evidence Data Hub separates **data discovery** from **data selection**. External databases and literature may supply candidate endpoint values, but no retrieved value becomes a modelling input automatically.

## Live adapters

### PubChem

- CAS/name → PubChem CID via PUG REST.
- Identity snapshot via PUG REST.
- Full PUG View record traversed for environmentally relevant sections.
- Numeric endpoint phrases are extracted with the PubChem reference/annotation context where available.
- PubChem is treated as a secondary aggregator; the original cited source should be reviewed before regulatory use.

### Europe PMC

- Search query combines chemical identifiers with the requested endpoint family.
- Abstracts are mined for candidate values.
- Open Access full-text XML can be mined for a limited number of articles per search.
- DOI, PMID, PMCID, title, journal, publication year and OA status are retained.
- Article-specific reuse licences remain applicable.

## Candidate endpoint families

- manure/slurry degradation DT50
- soil degradation DT50
- water-sediment DT50
- water-phase DT50
- hydrolysis DT50
- photolysis DT50
- biodegradation percentage
- WWTP removal (activated-sludge / sewage-treatment context)
- Koc, Kd and Kf
- BCF
- water solubility, vapour pressure and log Kow (catalogued; extraction expansion pending)
- aquatic LC50, EC50, NOEC and EC10

## Rights-aware source register

- EPA CompTox / CTX APIs — open commercial-use data; API key needed for live CTX requests.
- EFSA OpenFoodTox 3.0 — official open downloadable structured data; import parser staged.
- EPA ECOTOX — public curated ecotoxicity data; bulk-download connector staged.
- UBA PHARMS — human/veterinary measured environmental concentration database; monitoring evidence rather than fate kinetics.
- NORMAN Ecotoxicology — experimental endpoints and Lowest PNECs; link/CSV path registered pending reuse review.
- EcoDrug+ — API registered for mechanism/target conservation/similarity; not a fate-kinetics source.
- OECD eChemPortal — discovery gateway to authoritative underlying sources.
- ECHA CHEM — regulatory-data linkout; bulk/systematic reuse disabled pending rights review.
- FASS environmental information — high-value human-pharmaceutical degradation, sorption, bioaccumulation and ecotoxicity summaries; linkout only pending reuse review.
- Region Stockholm Janusinfo Pharmaceuticals and Environment — human-pharmaceutical persistence/bioaccumulation/toxicity and environmental-risk decision support; linkout registered.
- Japan NIHS Human Pharmaceutical ERA Databases — government-published ecotoxicity Excel and environmental-fate database; official-download/import staging with source attribution and source-specific notices retained.
- AERU VSDB / PPDB — valuable curated fate/ecotox sources, but commercial copying/integration requires a licence.
- PREMIER — high-value human-pharmaceutical ERA source; commercial/marketing-authorisation use requires a formal letter of access from the relevant controlling party.
- Sci-Bot — blocked from integration.

## Import rule

When a candidate is staged:

1. a new source record is created;
2. the exact candidate object is SHA-256 hashed;
3. original value and unit remain unchanged;
4. context and rights status are stored in notes;
5. `include_by_default` is always false;
6. a separate audit event is written;
7. the scientist must review/select it later.

This preserves EnviroChem's rule that automated discovery may accelerate evidence abstraction but may not silently decide the regulatory modelling value.
