# EnviroChem August 2026 delivery plan

## Date reality

The project date is 30 July 2026. A production-ready implementation of every regulatory
framework and every external fate executable cannot be completed and validated by 31 July.
A coherent, pilot-ready MVP by 31 August 2026 is achievable if the scope below is frozen.

## Definition of the 31 August MVP

### Professional software

A user can:

1. identify a chemical by name, CAS, SMILES, InChI or product record;
2. create a use and release scenario;
3. select EU, UK, US or Swiss framework packs;
4. progress from Tier 0 data review to Tier 3 refined assessment;
5. review and lock measured and predicted fate properties;
6. run native emissions, sorption, temperature correction, soil screening and SimpleTreat;
7. prepare managed input/output workflows for PEARL, TOXSWA, PELMO, MACRO, PRZM, EXAMS and PWC;
8. compare worst-case and refined scenarios;
9. generate an auditable technical report and a plain-language AI-assisted summary.

### Home and retail app

A user can:

1. enter or scan a product identifier;
2. resolve or confirm product ingredients;
3. state amount, frequency and release route;
4. receive a friendly fate and disposal summary;
5. see confidence and missing-data warnings;
6. install the web app on a phone as a PWA.

### Laboratory safety

A user can:

1. upload an SDS;
2. describe the actual laboratory task;
3. extract hazard, PPE, first-aid, spill and disposal information;
4. produce a draft COSHH assessment;
5. review, amend and sign through a competent-person workflow.

## What “all models included” means for the MVP

- Native deterministic implementation where technically and legally appropriate.
- Managed adapters that prepare inputs, launch an authorised local executable where available,
  parse outputs, preserve raw files and record model/version hashes.
- Export/import workflow when redistribution or operating-system restrictions prevent bundling.

It does not mean rewriting PEARL, TOXSWA, PELMO, MACRO, PRZM or EXAMS from scratch.

## Delivery sequence

### 30 July–3 August — consolidation

- one repository and one database;
- versioned framework and model registries;
- shared Pro/Home/Lab interface;
- PWA installation;
- automated tests and a single launcher.

### 4–10 August — identity, products and scenarios

- multi-chemical identity and ingredient relationships;
- product/barcode record;
- SDS/label upload;
- exposure scenario schema;
- units and concentration normalisation;
- contaminant-group applicability checks.

### 11–17 August — fate engine and model adapters

- generic emissions engine beyond pharmaceuticals;
- dynamic Activity SimpleTreat translation;
- soil accumulation and repeated-use model;
- adapter contracts for all external models;
- initial PEARL/TOXSWA and PRZM/EXAMS file adapters.

### 18–24 August — reports, COSHH and AI summaries

- technical report generator;
- evidence appendix and model audit package;
- COSHH review/signature workflow;
- audience-specific deterministic summary payloads;
- AI layer restricted to stored evidence and outputs.

### 25–31 August — validation and pilot release

- scientific regression tests;
- representative chemicals from each main contaminant group;
- EU/UK/US/Swiss scenario acceptance tests;
- packaging and deployment;
- three design-partner pilot assessments;
- issue log and post-MVP backlog.

## Explicitly outside the 31 August MVP

- complete regulatory certification;
- legal assurance that every output is submission-ready without expert review;
- full native mobile-store applications;
- universal barcode-to-composition coverage;
- validated applicability for metals, polymers, microplastics, nanomaterials and all UVCBs;
- redistribution of third-party executables without confirmed rights.
