# Veterinary ERA source review and implementation map

## VICH GL6 — Phase I

Implemented decision points:

1. legal/regulatory exemption;
2. natural substance with no material change in environmental concentration or distribution;
3. non-food animals;
4. minor-species equivalence to a major species with an existing EIA;
5. treatment of an individual or small number of animals;
6. extensive metabolism supported by residue/excretion evidence;
7. aquatic versus terrestrial environmental entry;
8. prevention of entry through controlled waste disposal;
9. aquaculture confinement and parasiticide concerns;
10. pasture parasiticide/dung-fauna concern;
11. Phase I aquatic EIC and soil PEC triggers.

The implementation uses the decision-tree values displayed in the GL6 figure: 1 µg/L for the confined-aquaculture EIC and 100 µg/kg for PECsoil. The source text extraction contains unit inconsistencies, so the application stores the source reference and requires expert review rather than silently relying on parsed prose.

## VICH GL38 — Phase II

Implemented logic:

- Tier A conservative total-residue exposure;
- refinement before additional Tier B testing;
- RQ = PEC/PNEC, with RQ ≥ 1 triggering refinement or affected-taxon testing;
- parent assumed at 100% for initial exposure;
- relevant excreted metabolites considered in refinement;
- persistence/accumulation warning;
- logKow ≥ 4 bioaccumulation trigger;
- BCF ≥ 1000 regulatory-guidance trigger;
- aquaculture, intensive and pasture branches;
- soil, surface water, sediment and dung compartments;
- dung fly/beetle concern for pasture parasiticides;
- OECD/ISO Tier A and Tier B study-plan recommendations.

## Outlier benchmark work incorporated

The prior fattening-pig workflow is retained as an explicit compatibility screen:

- g/animal/day → mg/animal/day → mg/kg bw/day;
- fattening pig defaults: 65 kg, turnover 3/year, 7.5 kg N/place/year, fraction treated 0.5, housing factor 1;
- 170 kg N/ha, 1500 kg/m³ soil, 0.05 m mixing depth;
- BIOWIN 4 compatibility equation: `10^(6 - BIOWIN4) / 10` hours at 25 °C;
- correct temperature direction: `DT50_target = DT50_source × 1.047^(source - target)`;
- internal conversion from hours to days;
- default mean manure age of `storage duration / 2`, with full duration available as an explicit alternative;
- excretion and degradation refinement;
- deterministic ranking support.

The previous PEC/earthworm-LD50 quotient is not presented as a VICH regulatory RQ. It is labelled as an Outlier compatibility prioritisation quotient because GL38 defines the regulatory quotient as PEC/PNEC.

## Animal coverage

The 65-profile library is intentionally broader than the old fixed fattening-pig task. It covers:

- pigs;
- poultry and ratites;
- cattle and buffalo;
- sheep and goats;
- equids;
- rabbits;
- deer and game;
- camelids;
- companion animals;
- aquaculture finfish, crustaceans, molluscs and amphibians;
- managed invertebrates;
- laboratory animals;
- zoo and exotic animals;
- a custom/minor-species route.

Only profiles with a registered official numeric default receive an `official_default=true` badge. Every other profile requires body weight and husbandry values to be entered and reviewed.

## Current complementary EMA source register

The application also registers the current EMA VICH-support guideline, the 2024 manure-fate revision, the 2023 cats/dogs ectoparasiticide reflection paper, the 2021 dung-fauna reflection paper, the aquaculture concept paper, the immunological VMP Revision 1 effective July 2026, environmental AMR concept work, and the revised poorly extractable/non-radiolabelled substances reflection paper.

## Remaining scientific work

- encode the full 2016 EMA regional default tables as versioned rulesets rather than one global default set;
- add region-specific animal husbandry and manure-spreading libraries;
- implement metabolite-family exposure records, not only one excreted-parent fraction;
- connect reviewed PNEC evidence and Tier A/B ecotoxicity endpoints;
- implement surface-water and groundwater refinements for livestock scenarios;
- implement cats/dogs ectoparasiticide washing/swimming/household pathways;
- implement environmental AMR assessment when final methodology is available;
- validate against published regulatory examples and independent expert calculations.
