# EnviroChem Veterinary ERA — v2.5 implementation notes

## Scope

This build introduces a veterinary environmental-risk workflow based on the VICH GL6 Phase I decision tree and the VICH GL38 Phase II branches:

- aquaculture;
- intensively reared terrestrial animals;
- pasture animals;
- companion/non-food animals and exceptional concern pathways;
- custom/minor species records.

The animal library contains 65 profiles spanning livestock, poultry, pigs, ruminants, equids, rabbits, camelids, deer/game, companion animals, aquaculture, laboratory animals, zoo/exotic animals and managed invertebrates.

## Scientific safeguards

1. **No invented official defaults.** Numeric defaults are flagged as official only for profiles represented in the registered EMA/VICH-support intensive-animal table. Other species require reviewed custom inputs.
2. **Phase I before Phase II.** The interface records the decision path and distinguishes a Phase I stop, Phase II requirement and tailored assessment.
3. **Correct temperature direction.** For theta > 1, correcting from 25 °C to 10 °C lengthens DT50:

   `DT50_target = DT50_source × theta^(source_temperature - target_temperature)`

4. **Transparent Outlier compatibility.** The prior BIOWIN-to-manure-DT50 and ranked earthworm-LD50 workflow is available as a screening/benchmark route. It is not presented as an official VICH or EMA method.
5. **Regulatory RQ is PEC/PNEC.** A PEC/earthworm-LD50 value is retained only as a prioritisation quotient and is clearly separated from the VICH RQ.
6. **Regional parameterisation remains explicit.** VICH harmonises the broad science and decision structure, while husbandry, climate, soil, water and accepted refinements remain jurisdiction-specific.

## Implemented branches

### Intensively reared animals

- total-residue initial PECsoil;
- dose, duration, body weight, turnover, fraction treated, nitrogen production, housing, manure storage and land application;
- mean-storage-age or full-storage-duration basis;
- excretion and manure-degradation refinement;
- persistence/accumulation and Tier B flags.

### Pasture animals

- direct excretion to the upper soil layer;
- stocking density and treatment-event inputs;
- initial and refined PECsoil;
- PECdung initial/refined when dung-output information is available;
- parasiticide/dung-fauna trigger;
- surface-water pathway warnings.

### Aquaculture

- total treatment dose by biomass;
- confined/open-system routing;
- initial and refined water concentration;
- receiving-water dilution;
- uneaten-feed/faecal sediment loading;
- surface-water and sediment RQ fields.

### Companion and other animals

- non-food-animal Phase I stop where appropriate;
- exceptional concern route for ectoparasiticides or another documented concern;
- no generic PEC is invented without a release scenario.

## Confidential source handling

The user's Outlier benchmark files and prior golden-solution material were used as confidential design/QA references. They are not included in this distributable archive. Only the generalised equations, unit checks and transparent compatibility logic needed by the application are implemented.
