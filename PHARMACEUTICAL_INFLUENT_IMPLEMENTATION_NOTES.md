# EnviroChem Studio v2.14 — Pharmaceutical influent implementation notes

## Purpose

v2.14 adds an explicit human-pharmaceutical use → sewer mass → wastewater flow → WWTP influent concentration workflow. The implementation separates regulatory screening from site-specific/catchment calculations so a user can start from an amount such as `10 mg/day`, `10 kg/day`, or `kg/year` without silently mixing population, wastewater flow, excretion, or treatment assumptions.

## Human pharmaceuticals: four explicit input modes

### 1. Actual / catchment use

Use when a measured, prescribed, sold, dispensed, or otherwise justified active-substance amount is available.

Accepted daily units include mg/day, g/day and kg/day. Annual amounts remain supported through the existing annual-use route.

The mass balance is:

```text
administered active amount
→ direct-to-sewer release + systemic fraction
→ unchanged parent in urine/faeces + quantified metabolites
→ sewer/WWTP influent mass
→ divide by matched WWTP wastewater flow
→ influent concentration
```

For a user-entered WWTP flow:

```text
ClocalINF (µg/L) = sewer mass (g/day) × 1,000,000 / wastewater flow (L/day)
```

If measured flow is unavailable, EnviroChem can derive flow from catchment population × wastewater generation per inhabitant per day. The flow source is always displayed.

### 2. EMA Phase I regulatory screen

The current EMA human-medicinal-product ERA guideline uses a total-residue, pre-treatment screening calculation. EnviroChem implements the current default assumptions as a named/versioned ruleset rather than hiding them:

- fraction of market penetration / population receiving the active daily (`FPEN`) = 0.01 by default;
- wastewater generation = 200 L/inhabitant/day;
- reference STP capacity = 10,000 inhabitants;
- no patient metabolism at Phase I;
- no sewage-treatment removal at Phase I;
- receiving-water dilution = 10.

The Phase I surface-water screen is:

```text
PECSW = DOSE_AS × FPEN / (WASTEW_INHAB × DILUTION)
```

The reference STP population is retained in the audit record and used to show the corresponding daily sewer mass and flow. Under the per-capita default, population cancels from concentration because both emitted mass and wastewater flow scale linearly with inhabitants. Population still determines the absolute mass entering the STP.

### 3. EMA Phase II local influent refinement

The local emission to wastewater and local influent concentration are represented explicitly before SimpleTreat:

```text
ElocalWATER = DOSE_AS × FEXCRETA × FPEN × CAPACITY_STP / CONV

ClocalINF = ElocalWATER × CONV / (WASTEW_INHAB × CAPACITY_STP)
```

EnviroChem applies unchanged-parent/metabolite excretion before wastewater treatment. `ClocalINF` is then the concentration supplied to the treatment model. This prevents the earlier scientific error of applying excretion after the WWTP model.

FPEN can use the EMA default, a reviewed user value, or a prevalence/treatment refinement:

```text
FPEN_refined = prevalence × treatment_days × treatments_per_year / 365
```

### 4. OECD therapeutic-class regional screen

The bundled OECD Health at a Glance 2025 snapshot provides 2023-or-nearest DDD/1,000 people/day values for four selected categories:

- antihypertensives: C02 + C03 + C07 + C08 + C09;
- lipid-modifying agents: C10;
- antidiabetics: A10;
- antidepressants: N06A.

EnviroChem stores these values with source metadata and exposes them as a conservative regional/class prioritisation screen. A DDD is an assumed maintenance dose and the reported value describes a therapeutic class, not the measured use of an individual active substance. Therefore the application never presents a class DDD value as compound-specific consumption without an explicit screening warning.

The current OECD Data Explorer pharmaceutical-consumption flow is broader than the four classes printed in the report. EnviroChem can prepare an auditable SDMX query for other ATC codes (for example N03) and can fetch it when runtime network access permits. Returned rows are review candidates; they are not silently selected as a modelling value.

## Why Carbamazepine is not assigned an OECD Figure 9.6 value

Carbamazepine belongs to ATC N03. N03 is not one of the four classes printed in Figure 9.6 of Health at a Glance 2025. The application therefore keeps the pilot Carbamazepine example on actual/catchment-use logic unless a reviewed N03 or compound-specific source is supplied. It does not fabricate a DDD rate from the antidepressant or other printed categories.

## Human versus veterinary exposure scale

Human pharmaceuticals typically enter municipal wastewater from a catchment population, so human use must be scaled consistently with the population and/or measured flow served by the WWTP.

Veterinary medicines do not use this municipal-population equation by default. The existing veterinary ERA routes remain scenario-specific:

- intensively reared terrestrial animals: farm/housing/manure → land application → soil;
- pasture animals: treated animals/stocking → direct excretion → soil/dung/surface-water concerns;
- aquaculture: treated biomass/system water/sediment;
- companion and special uses: release-specific route, including ectoparasiticide concerns where applicable.

A farm-level conservative exposure calculation is therefore broadly appropriate for intensive/pasture veterinary scenarios, but it is not a universal veterinary equation.

## Unit and provenance safeguards

- Daily input units are normalised deterministically to g/day and kg/day.
- Wastewater flow is stored in L/day and m³/day with its source.
- Concentration is calculated in µg/L; no mg/L shortcut is used.
- Parent and metabolite mass are calculated on a molar basis where molecular weights differ.
- Direct release, systemic availability, unchanged-parent excretion and metabolite fractions are separate fields.
- Regulatory defaults, user measurements and literature values are labelled distinctly.
- The calculation result retains assumptions and warnings.
- No OECD class value or live SDMX row is silently selected as compound-specific measured consumption.

## Regression benchmark

The existing Carbamazepine benchmark remains protected:

```text
10 kg/year administered
× 0.51 unchanged-parent fraction
= 5.1 kg/year parent to sewer

100,000 inhabitants
× 200 L/person/day
= 20,000 m³/day wastewater

parent influent concentration
= 0.6986301369863014 µg/L
```

The historical erroneous mg/L interpretation must not be reintroduced.

## Primary references registered in the implementation

- European Medicines Agency, *Guideline on the environmental risk assessment of medicinal products for human use*, Revision 1, effective 1 September 2024.
- OECD, *Health at a Glance 2025: OECD Indicators*, revised March 2026; Figure 9.6 and accompanying definition/comparability text.
- OECD Data Explorer, Pharmaceutical consumption SDMX dataflow.
- VICH GL6 / GL38 and EMA veterinary ERA supporting guidance for veterinary scenario routing.
