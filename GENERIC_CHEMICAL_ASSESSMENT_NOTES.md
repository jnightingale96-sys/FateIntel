# Generic chemical assessment notes — v2.18

## Why this change was required

Earlier guided builds could search evidence for another substance while the guided identity card and verified calculation fixture still represented Carbamazepine. That separation was visible, but it was too easy to mistake retrieved evidence for an active chemical-specific assessment.

v2.18 makes chemical identity, reviewed parameters and model execution one explicit chain.

## Data flow

1. **Resolve:** query PubChem by CAS, preferred/IUPAC name or SMILES.
2. **Confirm:** inspect the candidate and explicitly create or reuse the matching chemical.
3. **Snapshot:** store the source record, query, retrieved fields and identity hash.
4. **Attach:** bind the confirmed chemical to the selected project.
5. **Review profile:** enter or copy candidate values, verify units and applicability, document provenance and confirm review.
6. **Gate:** check route-specific completeness before the guided run.
7. **Execute:** bind sorption and WWTP requests to the reviewed profile ID and record its hash.

## What is deliberately not automated

- PubChem synonyms are not treated as definitive CAS adjudication.
- A retrieved property is not automatically selected because the name or endpoint matched.
- Overall WWTP removal is not divided into biodegradation, sludge and volatilisation fractions.
- Soil DT50 is not silently reused as a biosolids-storage DT50.
- Neutral Briggs plant uptake is not silently used for acids or bases.
- The Carbamazepine workbook fixture is not generalized to another identity.

## Generic profile fields

The reviewed profile stores ionisation class, log Kow, pKa, water solubility, vapour pressure, soil DT50, four WWTP pathway fractions, source summary and structured provenance. The four WWTP fractions must sum to no more than one; the remainder is the effluent fraction.

The current custom WWTP calculation is a transparent screening mass balance. Its output should not be described as an official SimpleTreat result.

## Diclofenac regression scenario

Automated tests use a Diclofenac identity candidate and clearly labelled QA-only profile values. They verify that:

- identity resolution does not mutate the database;
- explicit confirmation creates a distinct chemical and draft profile;
- the guided run remains blocked until review;
- sorption, emission and WWTP calculations use the Diclofenac identity/profile;
- Carbamazepine identity or preset substitution is rejected;
- altered log Kow or WWTP fractions are rejected when a reviewed profile ID is supplied;
- Diclofenac evidence cannot be staged against Carbamazepine.

The QA profile values are not shipped as regulatory selections.
