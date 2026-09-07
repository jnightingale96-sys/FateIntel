# US Exposure Foundations — implementation and remaining gaps

Release: EnviroChem Studio v2.23.0 Alpha 2  
Build: envirochem-studio-v2.23.0-alpha2-us-exposure-foundations-2026-09-02

## What is now functional

Alpha 2 adds a chemically identity-bound US industrial screening workflow:

1. select one of 12 published EPA exposure-scenario documents, or explicitly
   opt in to a clearly labelled draft/reference-only record;
2. enter daily chemical throughput and operating days;
3. define a non-overlapping process-loss event on that throughput basis;
4. apply an engineering-control efficiency;
5. route post-control mass to air, water and soil and captured material to
   landfill, incineration or off-site treatment;
6. optionally calculate worker inhalation and dermal dose from measured air or
   a time-averaged well-mixed-room screen;
7. check exact mass closure and expose missing conventional assessment domains;
8. persist inputs, outputs, warnings, sources and the immutable identity snapshot.

The screen is registered as ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN version
0.1.0-alpha. It is not ChemSTEER and is never described as EPA-equivalent.

## Equations

For event \(i\), with daily chemical throughput \(M\), event loss fraction
\(f_i\) and control efficiency \(\eta_i\):

\[
M_{event,i}=M f_i
\]

\[
M_{post-control,i}=M_{event,i}(1-\eta_i)
\]

\[
M_{captured,i}=M_{event,i}\eta_i
\]

Post-control mass is allocated across explicit media fractions that must sum to
one. Captured mass is recorded as a managed-waste transfer, not destruction.
All event fractions share the same throughput basis and their sum cannot exceed
one.

For a well-mixed room with generation rate \(G\), volume \(V\), air-change rate
\(\lambda\) and task duration \(T\):

\[
C_{ss}=\frac{G}{V\lambda}
\]

\[
\bar C_T=C_{ss}\left[1-\frac{1-e^{-\lambda T}}{\lambda T}\right]
\]

This omits near-field peaks and is only a screening calculation.

## EPA source catalogue

The application stores metadata and SHA-256 provenance, not copies of the
uploaded guidance or EPA executables.

| Source group | Records | Default status |
| --- | ---: | --- |
| Published exposure-scenario documents | 12 | Enabled |
| Draft exposure-scenario documents | 3 | Reference-only |
| Draft screening scenarios | 45 | Reference-only |
| Exposure Factors Handbook | 1 | Versioned parameter reference |
| ChemSTEER 3.2 | 1 | External managed workflow |
| CEM 3.2 | 1 | External managed workflow |
| E-FAST 2014 | 1 | External legacy workflow |
| Legacy meteorological dataset | 1 | Disabled unless explicitly selected |

The two supplied scenario ZIPs were byte-identical. One archive identity is
recorded: SHA-256
672bb874c573960f8c999adf2ceb674c09af8497a55dee441bb7db945fc7e6ee.

## External-model and licensing boundary

- ChemSTEER 3.2: a managed contract now exists for industrial releases and
  worker exposure. Execution remains in an authorised local EPA installation.
- CEM 3.2: a managed contract records product/article category, route,
  population and life-stage choices before external execution and import.
- E-FAST 2014: a managed legacy contract requires a legacy-use justification
  and retains the exact executable/version and raw output.
- EPA executables are not bundled, modified, adapted or rebranded.
- KEGG xenobiotic pathway data remain linkout-only because commercial use
  requires an appropriate licence.
- enviPath/EAWAG-BBD remains collaboration/permission-gated. An open client
  licence is not treated as permission to commercialise hosted data.
- eChemPortal remains a federated discovery source; underlying provider rights
  and study context remain attached to each record.

## Current capability map

| Assessment area | Alpha 2 status | What is still missing |
| --- | --- | --- |
| Industrial manufacture/processing | Working alpha foundation | Multiple linked events in the UI, batch/unit-operation libraries, near-field model, monitoring import and ChemSTEER end-to-end validation |
| Occupational/laboratory exposure | Generic measured-air and well-mixed screen | Laboratory task library, volatile/liquid/powder source terms, glove/permeation evidence, repeated-shift aggregation and validated ChemSTEER comparison |
| Consumer products/articles | CEM contract only | Native route equations, product/article parameter library, life-stage values with exact EFH citations, aggregate exposure |
| Waste disposal | Mass routing only | Landfill leachate/gas generation, liner/leachate controls, incineration destruction and products, recycling, wastewater receiving route |
| Agriculture/pesticides | PWC3 contract; PRZM/EXAMS metadata | Current scenario database management, executable writers/parsers, spray drift, applicator/bystander/resident exposure and dietary modules |
| Municipal wastewater | Working native screens | Official executable equivalence and broader chemical-class validation |
| Surface water/groundwater | Native screens plus external contracts | US scenario validation and official end-to-end execution |
| Transformation products | Provider-neutral qualitative review | Licensed pathway source, observed-data workflow and independently fitted formation/degradation kinetics |
| Landfill | Not yet a fate model | Source-term-to-leachate/gas mass balance, hydrology, degradation, sorption, collection and receiving-environment chain |

## Conventional risk-assessment domains still required

The completeness control tracks these 15 domains independently:

1. confirmed identity and substance form;
2. uses, sites, volumes and operating pattern;
3. manufacture and processing;
4. worker exposure;
5. consumer exposure where relevant;
6. releases to air, water and soil;
7. landfill, incineration and off-site waste treatment;
8. environmental fate and transport;
9. ecological effects and PNECs/equivalent benchmarks;
10. human-health hazards and points of departure;
11. vulnerable populations and life stages;
12. monitoring/model evaluation or analogue support;
13. uncertainty, variability and sensitivity;
14. exposure-to-hazard risk characterisation; and
15. versioned source, parameter and reviewer provenance.

A complete checklist is not automatically an adequate assessment. Relevance,
quality, tier and legal acceptance remain chemical-, use- and programme-specific.

## Recommended next increments

1. add multi-event industrial unit operations and an ESD parameter-extraction
   review table;
2. validate native source terms against controlled ChemSTEER cases;
3. implement consumer product/article data capture and CEM export/import;
4. implement landfill and incineration mass-flow modules;
5. add US pesticide scenario/version management and PWC3 automation;
6. add applicator, bystander, resident and dietary exposure tracks;
7. add uncertainty/sensitivity execution and monitoring comparison;
8. add authenticated projects, migrations, job workers, backups and deployment
   controls before paid multi-user operation.

