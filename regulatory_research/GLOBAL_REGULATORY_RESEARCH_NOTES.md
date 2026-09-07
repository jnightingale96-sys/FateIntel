# EnviroChem global regulatory research and implementation notes

**Snapshot:** 30 July 2026  
**Source register:** 139 official-source framework entries extracted from the supplied compendium  
**Purpose:** Convert global chemical-risk regulation into a versioned, auditable decision-support layer for EnviroChem.

## Review boundary

This pack distinguishes five different states that must never be conflated:

1. **Official source registered** — the official URL and framework metadata are stored.
2. **Official source reviewed** — the linked source has been read at source level for this build.
3. **Implementation note curated** — the likely EnviroChem impact has been mapped, but source-level deep reading is still pending.
4. **Ruleset implemented and validated** — regulatory logic has been encoded and scientifically tested.
5. **Jurisdictional/legal confirmation** — current legal applicability has been confirmed for a real submission.

The register is not legal advice. Tier B and Tier C entries require competent-authority or local regulatory verification. Paywalled standards such as ISO documents cannot be treated as fully read without licensed access.

## What the compendium changes in EnviroChem

The platform must no longer have a single generic “EU”, “US” or “global” switch. It needs a regulatory routing engine that begins with:

- product class;
- intended use;
- manufacture/import/use volume;
- exposure or release scenario;
- jurisdiction;
- assessment purpose;
- tier/refinement level.

It then selects:

- international classification and test-method baselines;
- national or regional legal frameworks;
- sector-specific guidance;
- environmental exposure and fate models;
- evidence-quality requirements;
- risk-management and reporting obligations;
- change-watch warnings.

## Global hierarchy encoded in the application

1. UN GHS and nationally adopted hazard-communication rules.
2. OECD Test Guidelines, GLP and Mutual Acceptance of Data.
3. Cross-cutting WHO/FAO/OECD assessment methodology.
4. Regional or national chemical legislation.
5. Product-sector rules for pesticides, biocides, pharmaceuticals, food, cosmetics, medical devices and workplace chemicals.
6. Scenario and model guidance such as FOCUS, EPA OPP, PMRA and APVMA.
7. Decision, mitigation, authorisation, restriction, labelling, monitoring and reassessment.

## Non-negotiable implementation rules

- Store framework version/effective date with every assessment.
- Preserve the official URL and access/review date.
- Treat “living portals” as change-sensitive.
- Do not assume the latest UN GHS edition is the legally adopted national edition.
- Keep OECD guideline number, revision and deviations at study level.
- Keep GLP status separate from scientific reliability.
- Keep measured, read-across and predicted evidence distinct.
- Route by product class before selecting models.
- Treat standard scenarios and site-specific refinements as separate tiers.
- Do not present Tier B/C navigation as legal confirmation.
- Attach change-watch alerts to projects and reports.
- Record why a framework was selected and why another was excluded.
- Distinguish source registration, source review, ruleset implementation and legal confirmation.

## Endpoint architecture

### Identity and composition

CAS/EC identifiers, structure, purity, impurities, formulation, analytical methods and batch representativeness.

**EnviroChem modules:** identity_resolution, product_ingredients, evidence_engine, analytical_methods.


### Physicochemical properties

Solubility, vapour pressure, pKa, log KOW/log D, dissociation, particle size, stability and other sector-relevant properties.

**EnviroChem modules:** property_evidence, speciation, sorption, model_input_selection.


### Environmental fate

Hydrolysis, photolysis, biodegradation, transformation products, adsorption/desorption, soil/water/sediment degradation, bioaccumulation and mobility.

**EnviroChem modules:** dt50_evidence, sorption, wwtp, transformation_products, pbt_pmt_screen.


### Environmental exposure

Emission scenarios, releases, sewage treatment, biosolids, wastewater irrigation, direct discharge, air deposition, soil, groundwater, surface water/sediment and food-chain pathways.

**EnviroChem modules:** emissions, simpletreat, soil_accumulation, model_orchestration, plant_uptake.


### Ecotoxicology

Aquatic and terrestrial organisms, microbes, plants, pollinators, birds/mammals, sediment organisms and higher-tier/community assessments where triggered.

**EnviroChem modules:** ecotox_evidence, pnec_derivation, risk_characterisation.


### Human health

Toxicokinetics, acute and repeated-dose toxicity, irritation/sensitisation, genotoxicity, carcinogenicity, reproductive/developmental toxicity, endocrine and organ-specific effects.

**EnviroChem modules:** sds_coshh, hazard_summary, external_human_health_linkage.


### Exposure and risk characterisation

Consumer, worker, resident/bystander, dietary and environmental exposure; uncertainty; mixture/cumulative considerations; margin/RQ or probabilistic methods.

**EnviroChem modules:** tier_comparison, rq, uncertainty, mixtures, ai_summary.


### Risk management and post-market

Restrictions, use conditions, labels/SDS, PPE/engineering controls, emission limits, monitoring, stewardship, incident reporting and reassessment triggers.

**EnviroChem modules:** reporting, coshh, mitigation, monitoring, change_watch.



## Region-level implementation notes

### International baseline

The international layer should be automatically attached to most professional assessments. GHS supports classification and communication; OECD provides test methods, GLP/MAD, assessment guidance and read-across tools; WHO/FAO provide broader risk-assessment and food/pesticide methodology; VICH supplies veterinary pharmaceutical ERA; treaty systems add POP, waste, trade and mercury controls. These sources should appear as provenance and methodology layers, not as substitutes for national law.

### European Union, United Kingdom and Switzerland

The EU branch needs separate packs for REACH/IR&CSA, CLP, BPR, plant protection/FOCUS, human medicines, veterinary medicines, cosmetics and occupational safety. Great Britain requires autonomous UK REACH, GB product regimes and COSHH. Switzerland is strongly aligned with EU concepts but remains legally autonomous through ChemO, ORRChem and sector ordinances. The platform must therefore support shared scientific calculations while maintaining separate legal and reporting pathways.

### United States and Canada

The United States is programme-led: TSCA, FIFRA, FDA/NEPA, Superfund and OSHA/NIOSH use different assessment contexts. EPA pesticide models and databases must be routed only when the product/use belongs to the relevant programme. Canada requires separate CEPA/new-substances and PMRA pesticide pathways; Canadian guidance and defaults must not be treated as identical to US EPA practice.

### Australia and New Zealand

Australia divides industrial chemicals, agricultural/veterinary chemicals, workplace safety and contaminated sites across separate systems. AICIS categorisation is an early decision gate; APVMA provides environment-specific risk manuals. New Zealand uses national hazardous-substance methodology and approval controls. Both regions need ruleset-effective-date tracking.

### Asia

Japan has comparatively mature official chemical-information and CSCL pathways. China, South Korea and several other systems are change-sensitive and local-language text may control. EnviroChem should provide navigation, evidence organisation and model outputs, but should visibly require local confirmation before filing. Regional generalisation is unsafe.

### Latin America

Pesticide systems are often more developed than industrial-chemical systems. Brazil’s tripartite structure requires separate health, environment and agricultural workstreams. Mexico similarly requires authority-specific routing. Emerging inventories in Colombia and Chile require current-cycle checks. Andean pesticide rules should be treated as regional plus national implementation.

### Africa and Middle East

Many pathways are sectoral or regional and Tier B/C. International OECD/FAO/WHO baselines may support scientific work, but national competent-authority verification is essential. Regional pesticide systems such as CILSS and CPAC/CEMAC should be represented separately from national implementation. GCC standards complement rather than replace national rules.

### Cross-cutting specialist methods

The application must support environmental exposure, PBT/vPvB and PMT/vPvM, endocrine disruption, nanomaterials, ecological risk, exposure factors, NAMs, GLP and weight-of-evidence as triggerable specialist workstreams. These are not universally applicable checkboxes; applicability must be justified and versioned.

## Change watch



### Australia AICIS categorisation guidelines

**Jurisdiction:** Australia  
**Trigger:** Finalised September 2026 guideline changes become effective after the snapshot date.  
**Expected/effective:** September 2026  
**Required action:** Use the September 2025 edition until the effective date, then recheck the AICIS portal.  
**Official source:** https://www.industrialchemicals.gov.au/news-and-notices/changes-categorisation-guidelines-september-2026


### China new chemical registration measures

**Jurisdiction:** China  
**Trigger:** A 2026 revision process has been notified/reported; legal status and effective date must be checked against final MEE publication.  
**Expected/effective:** 2026 - status uncertain at snapshot  
**Required action:** Do not rely on draft or trade-notification summaries for a filing; verify final Chinese MEE text.  
**Official source:** https://www.mee.gov.cn/


### UN GHS national adoption

**Jurisdiction:** Global  
**Trigger:** GHS Rev.11 is the current UN edition, but national systems may still implement Rev.7-10 or selected building blocks.  
**Expected/effective:** Varies by jurisdiction  
**Required action:** Check the jurisdiction-specific CLP/GHS law and transition period.  
**Official source:** https://unece.org/about-ghs


### EU REACH / CLP guidance revisions

**Jurisdiction:** European Union / EEA  
**Trigger:** ECHA guidance chapters and CLP guidance are modular and revised at different times, including for new hazard classes and nanoforms.  
**Expected/effective:** Ongoing  
**Required action:** Check the version/date printed on each downloaded ECHA chapter.  
**Official source:** https://echa.europa.eu/guidance-documents


### UK REACH policy changes

**Jurisdiction:** United Kingdom (GB)  
**Trigger:** Transitional registration and data-model policy may change through legislation and HSE/Defra notices.  
**Expected/effective:** Ongoing  
**Required action:** Check HSE UK REACH news and the governing statutory instrument before a submission.  
**Official source:** https://www.hse.gov.uk/reach/


### EAEU TR 041 implementation

**Jurisdiction:** EAEU  
**Trigger:** Implementation has experienced delays and depends on supporting acts and member-state readiness.  
**Expected/effective:** Uncertain / member-state dependent  
**Required action:** Verify with the competent authority in the target EAEU state before market access.  
**Official source:** https://eec.eaeunion.org/en/comission/department/deptexreg/tr/


### K-REACH amendments and thresholds

**Jurisdiction:** South Korea  
**Trigger:** Registration thresholds, exemptions and implementation rules are periodically amended.  
**Expected/effective:** Ongoing  
**Required action:** Use the Korean K-REACH portal and current legal text, not an older English summary.  
**Official source:** https://kreach.me.go.kr/repwrt/index.do


### Emerging Latin American inventories

**Jurisdiction:** Colombia / Chile / others  
**Trigger:** Industrial-chemical inventories and notification cycles are being implemented or expanded.  
**Expected/effective:** Country-specific  
**Required action:** Check current inventory window, thresholds and local representative requirements.  
**Official source:** https://quimicos.minambiente.gov.co/


### OECD Test Guideline updates

**Jurisdiction:** Global  
**Trigger:** OECD publishes new and updated Test Guidelines, commonly in annual batches.  
**Expected/effective:** Latest batch 2 July 2026  
**Required action:** Confirm the current TG number/version and whether the receiving regulator accepts it for the endpoint.  
**Official source:** https://www.oecd.org/en/topics/sub-issues/testing-of-chemicals/test-guidelines.html



## Entry-by-entry framework notes

Each entry below records the official source, verification tier, current review depth and the implementation consequence for EnviroChem. “Deep read pending” is deliberate and prevents the platform from overstating regulatory completion.



# International and global bodies


## INT-001 — Globally Harmonized System of Classification and Labelling of Chemicals (GHS), Rev.11

- **Jurisdiction/system:** United Nations
- **Authority/body:** UNECE
- **Chemical domain:** Classification and labelling
- **Version/effective-date note:** 2025 (Rev.11)
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://unece.org/transport/dangerous-goods/ghs-rev11-2025
- **Mapped product classes:** classification_labelling
- **Mapped EnviroChem modules:** classification_labelling, regulatory_navigator, sds, source_provenance

**Implementation note:** Use as the global hazard-communication baseline only. Store the GHS revision and the nationally adopted edition separately; do not assume Rev.11 is legally implemented everywhere.



## INT-002 — OECD Guidelines for the Testing of Chemicals

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD Environment, Health and Safety Programme
- **Chemical domain:** Industrial chemicals; pesticides; biocides; nanomaterials
- **Version/effective-date note:** New and updated TGs published 2 July 2026
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.oecd.org/en/topics/sub-issues/testing-of-chemicals/test-guidelines.html
- **Mapped product classes:** industrial_chemicals, pesticides, biocides, nanomaterials
- **Mapped EnviroChem modules:** applicability_warnings, application_scenario, ecotox, environmental_exposure, groundwater, identity_resolution, model_orchestration, nano_ruleset, particle_properties, property_evidence, regulatory_navigator, risk_report, sediment, simpletreat, source_provenance, surface_water, use_scenario

**Implementation note:** OECD Test Guidelines are the primary cross-border method registry for environmental fate, ecotoxicity and health studies. Store TG number, revision date, deviations, GLP status and receiving-authority acceptance. The registry must be updateable because new and revised TGs are issued regularly.



## INT-003 — OECD Series on Testing and Assessment / Guidance Documents

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD Environment, Health and Safety Programme
- **Chemical domain:** Cross-cutting assessment
- **Version/effective-date note:** Portal current at snapshot
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.oecd.org/en/topics/sub-issues/testing-of-chemicals/publications-on-testing-and-assessment-of-chemicals.html
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Use OECD Series on Testing and Assessment guidance for endpoint interpretation, integrated approaches, reporting and method applicability. Link guidance documents to specific evidence-selection rules rather than treating them as generic references.



## INT-004 — Mutual Acceptance of Data (MAD) and OECD Principles of GLP

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD Council
- **Chemical domain:** GLP and test acceptance
- **Version/effective-date note:** Ongoing
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.oecd.org/en/topics/sub-issues/good-laboratory-practice-and-compliance-monitoring.html
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** evidence_engine, glp_status, regulatory_navigator, source_provenance, study_reliability

**Implementation note:** MAD and GLP determine cross-border acceptability of test data. Evidence records need fields for GLP status, facility/compliance programme, study type, test guideline and whether MAD applies.



## INT-005 — eChemPortal

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD
- **Chemical domain:** Chemical information
- **Version/effective-date note:** Living database
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.echemportal.org/echemportal/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Use eChemPortal as a federated discovery route, not as the final source. Preserve the originating database and study-level citation.



## INT-006 — OECD QSAR Toolbox

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD / ECHA
- **Chemical domain:** Alternative methods
- **Version/effective-date note:** Living software
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://qsartoolbox.org/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** applicability_domain, predicted_data, read_across, regulatory_navigator, source_provenance

**Implementation note:** Use the OECD QSAR Toolbox for read-across/category support and data-gap filling. Predicted/read-across outputs must be labelled, retain the applicability rationale and never silently replace measured evidence.



## INT-007 — WHO Human Health Risk Assessment Toolkit: Chemical Hazards, 2nd edition

- **Jurisdiction/system:** WHO
- **Authority/body:** WHO International Programme on Chemical Safety
- **Chemical domain:** Human health
- **Version/effective-date note:** 2021
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.who.int/publications/i/item/9789240035720
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** The WHO toolkit confirms a context-led workflow: define the assessment context, gather authoritative hazard/exposure information, combine it with locally relevant information, and document uncertainty. This maps well to guided and expert modes.



## INT-008 — EHC 240: Principles and Methods for the Risk Assessment of Chemicals in Food

- **Jurisdiction/system:** WHO / FAO
- **Authority/body:** IPCS / JECFA / JMPR
- **Chemical domain:** Food chemicals
- **Version/effective-date note:** 2009
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.who.int/publications/i/item/9789241572408
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-009 — IPCS Harmonization Project guidance and terminology

- **Jurisdiction/system:** WHO
- **Authority/body:** IPCS Harmonization Project
- **Chemical domain:** Human health
- **Version/effective-date note:** Living collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.who.int/teams/environment-climate-change-and-health/chemical-safety-and-health/health-impacts/chemical-risk-assessment
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for human health. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-010 — IARC Monographs and Preamble

- **Jurisdiction/system:** WHO
- **Authority/body:** International Agency for Research on Cancer (IARC)
- **Chemical domain:** Carcinogenicity
- **Version/effective-date note:** Preamble amended 2019; monographs ongoing
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://monographs.iarc.who.int/iarc-monographs-preamble-preamble-to-the-iarc-monographs/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for carcinogenicity. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-011 — FAO Pesticide Registration Toolkit

- **Jurisdiction/system:** FAO
- **Authority/body:** FAO
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Living toolkit
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.fao.org/pesticide-registration-toolkit/en/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** The FAO toolkit supports product-class-first routing for pesticides, data requirement selection, dossier review, risk mitigation and decision support. EnviroChem should provide a registration pathway rather than one universal pesticide assessment.



## INT-012 — JMPR guidance, reports and evaluations

- **Jurisdiction/system:** FAO / WHO
- **Authority/body:** Joint FAO/WHO Meeting on Pesticide Residues (JMPR)
- **Chemical domain:** Pesticide residues in food
- **Version/effective-date note:** 2025 JMPR outputs available in 2026
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.fao.org/agriculture/crops/thematic-sitemap/theme/pests/jmpr/en/
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticide residues in food. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-013 — JECFA methods, reports and database

- **Jurisdiction/system:** FAO / WHO
- **Authority/body:** Joint FAO/WHO Expert Committee on Food Additives (JECFA)
- **Chemical domain:** Food additives, contaminants and veterinary drug residues
- **Version/effective-date note:** 102nd meeting held June 2026
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.who.int/groups/joint-fao-who-expert-committee-on-food-additives-(jecfa)
- **Mapped product classes:** veterinary_pharmaceuticals, food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food additives, contaminants and veterinary drug residues. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-014 — Codex Procedural Manual and risk-analysis principles

- **Jurisdiction/system:** FAO / WHO
- **Authority/body:** Codex Alimentarius Commission
- **Chemical domain:** Food and feed
- **Version/effective-date note:** 31st edition current at snapshot
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.fao.org/fao-who-codexalimentarius/publications/en/
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food and feed. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-015 — Guidelines for Drinking-water Quality

- **Jurisdiction/system:** WHO
- **Authority/body:** WHO
- **Chemical domain:** Drinking water
- **Version/effective-date note:** 4th edition incorporating addenda
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.who.int/publications/i/item/9789241549950
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for drinking water. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-016 — WHO Global Air Quality Guidelines

- **Jurisdiction/system:** WHO
- **Authority/body:** WHO
- **Chemical domain:** Air pollutants
- **Version/effective-date note:** 2021
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.who.int/publications/i/item/9789240034228
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for air pollutants. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-017 — IOMC Toolbox for Decision Making in Chemicals Management

- **Jurisdiction/system:** IOMC
- **Authority/body:** Inter-Organization Programme for the Sound Management of Chemicals
- **Chemical domain:** National chemicals management
- **Version/effective-date note:** Living toolkit
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://iomctoolbox.org/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for national chemicals management. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-018 — Global Framework on Chemicals - For a Planet Free of Harm from Chemicals and Waste

- **Jurisdiction/system:** UNEP / GFC partners
- **Authority/body:** Global Framework on Chemicals
- **Chemical domain:** Lifecycle chemicals management
- **Version/effective-date note:** Adopted 2023
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.chemicalsframework.org/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for lifecycle chemicals management. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-019 — Convention guidance and POPs review/evaluation documents

- **Jurisdiction/system:** UN treaty
- **Authority/body:** Stockholm Convention
- **Chemical domain:** Persistent organic pollutants
- **Version/effective-date note:** Living annexes and guidance
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.pops.int/
- **Mapped product classes:** pops
- **Mapped EnviroChem modules:** bioaccumulation, mobility, pbt_pmt_screen, persistence, regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for persistent organic pollutants. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-020 — Decision guidance documents and prior informed consent procedure

- **Jurisdiction/system:** UN treaty
- **Authority/body:** Rotterdam Convention
- **Chemical domain:** Hazardous chemicals and pesticides in trade
- **Version/effective-date note:** Living annexes and guidance
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.pic.int/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for hazardous chemicals and pesticides in trade. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-021 — Technical guidelines under the Basel Convention

- **Jurisdiction/system:** UN treaty
- **Authority/body:** Basel Convention
- **Chemical domain:** Hazardous waste
- **Version/effective-date note:** Living technical-guideline collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.basel.int/Implementation/TechnicalMatters/DevelopmentofTechnicalGuidelines/Overview/tabid/2374/Default.aspx
- **Mapped product classes:** waste
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for hazardous waste. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-022 — Minamata Convention guidance documents

- **Jurisdiction/system:** UN treaty
- **Authority/body:** Minamata Convention
- **Chemical domain:** Mercury
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://minamataconvention.org/en/resources/guidance-documents
- **Mapped product classes:** metals
- **Mapped EnviroChem modules:** applicability_domain, predicted_data, read_across, regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for mercury. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-023 — VICH GL6: Environmental Impact Assessment Phase I

- **Jurisdiction/system:** VICH
- **Authority/body:** International Cooperation on Harmonisation of Technical Requirements for Registration of Veterinary Medicinal Products
- **Chemical domain:** Veterinary pharmaceuticals
- **Version/effective-date note:** June 2000
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://vichsec.org/en/guidelines/pharmaceuticals/pharma-safety/environmental-safety/gl6.html
- **Mapped product classes:** veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** VICH GL6 supplies the Phase I veterinary medicine environmental screen. Implement a dedicated veterinary pharmaceutical ruleset and Phase I trigger logic.



## INT-024 — VICH GL38: Environmental Impact Assessment Phase II

- **Jurisdiction/system:** VICH
- **Authority/body:** VICH
- **Chemical domain:** Veterinary pharmaceuticals
- **Version/effective-date note:** October 2004
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://vichsec.org/en/guidelines/pharmaceuticals/pharma-safety/environmental-safety/gl38.html
- **Mapped product classes:** veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** VICH GL38 supplies Phase II veterinary environmental assessment. Parent, metabolites, manure/soil pathways and species-specific use scenarios need explicit records.



## INT-025 — ICH Q9(R1) Quality Risk Management

- **Jurisdiction/system:** ICH
- **Authority/body:** International Council for Harmonisation
- **Chemical domain:** Pharmaceutical quality
- **Version/effective-date note:** R1 adopted 2023
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.ich.org/page/quality-guidelines
- **Mapped product classes:** human_pharmaceuticals, veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** Register this official pathway for pharmaceutical quality. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-026 — ICH Q3C: Residual Solvents

- **Jurisdiction/system:** ICH
- **Authority/body:** ICH
- **Chemical domain:** Pharmaceutical impurities
- **Version/effective-date note:** Current revision on ICH portal
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.ich.org/page/quality-guidelines
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** Register this official pathway for pharmaceutical impurities. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-027 — ICH Q3D: Elemental Impurities

- **Jurisdiction/system:** ICH
- **Authority/body:** ICH
- **Chemical domain:** Pharmaceutical impurities
- **Version/effective-date note:** Current revision on ICH portal
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.ich.org/page/quality-guidelines
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** Register this official pathway for pharmaceutical impurities. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-028 — ISO 31000 Risk management - Guidelines

- **Jurisdiction/system:** ISO
- **Authority/body:** International Organization for Standardization
- **Chemical domain:** Enterprise risk management
- **Version/effective-date note:** ISO 31000:2018
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.iso.org/iso-31000-risk-management.html
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for enterprise risk management. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-029 — ISO 14971:2019 Medical devices - Application of risk management to medical devices

- **Jurisdiction/system:** ISO
- **Authority/body:** ISO
- **Chemical domain:** Medical devices
- **Version/effective-date note:** 2019
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.iso.org/standard/72704.html
- **Mapped product classes:** medical_devices
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for medical devices. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-030 — ISO 10993-17:2023 Biological evaluation of medical devices - Toxicological risk assessment of medical device constituents

- **Jurisdiction/system:** ISO
- **Authority/body:** ISO
- **Chemical domain:** Medical devices toxicology
- **Version/effective-date note:** 2023
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.iso.org/standard/75323.html
- **Mapped product classes:** medical_devices
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for medical devices toxicology. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-031 — International Chemical Safety Cards (ICSCs)

- **Jurisdiction/system:** ILO / WHO
- **Authority/body:** International Labour Organization
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** Living collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://chemicalsafety.ilo.org/dyn/icsc/showcard.home
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## INT-032 — UNEP Chemicals and Pollution Action portal

- **Jurisdiction/system:** UNEP
- **Authority/body:** UN Environment Programme
- **Chemical domain:** Chemicals and waste
- **Version/effective-date note:** Living portal
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.unep.org/explore-topics/chemicals-waste
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for chemicals and waste. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.




# Europe: EU/EEA, UK and neighbouring systems


## EUR-001 — REACH Guidance Documents

- **Jurisdiction/system:** European Union / EEA
- **Authority/body:** European Chemicals Agency (ECHA)
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Living collection
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/guidance-documents/guidance-on-reach
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** EU REACH is a living modular framework. Build versioned guidance packs and never label a run simply 'REACH' without the chapter/version and tonnage/use context.



## EUR-002 — Guidance on Information Requirements and Chemical Safety Assessment (IR&CSA)

- **Jurisdiction/system:** European Union / EEA
- **Authority/body:** ECHA
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Modular chapters; check each chapter version
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/guidance-documents/guidance-on-information-requirements-and-chemical-safety-assessment
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** IR&CSA is the core source for EU chemical safety assessment. Map each chapter to data requirements, exposure scenarios, PEC/PNEC, risk characterisation and uncertainty.



## EUR-003 — Guidance on the Application of the CLP Criteria

- **Jurisdiction/system:** European Union / EEA
- **Authority/body:** ECHA
- **Chemical domain:** Classification and labelling
- **Version/effective-date note:** Living guidance; verify part/version
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/guidance-documents/guidance-on-clp
- **Mapped product classes:** classification_labelling
- **Mapped EnviroChem modules:** classification_labelling, regulatory_navigator, sds, source_provenance

**Implementation note:** CLP guidance controls classification interpretation. Keep hazard classification and environmental exposure calculations separate but linked.



## EUR-004 — Guidance on the Biocidal Products Regulation

- **Jurisdiction/system:** European Union / EEA
- **Authority/body:** ECHA
- **Chemical domain:** Biocides
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/guidance-documents/guidance-on-biocides-legislation
- **Mapped product classes:** biocides
- **Mapped EnviroChem modules:** ecotox, environmental_exposure, regulatory_navigator, simpletreat, source_provenance, use_scenario

**Implementation note:** Biocides require product-type/use-specific environmental assessment. Add BPR product type, use pattern and release scenario fields.



## EUR-005 — Environmental risk assessment of pesticides

- **Jurisdiction/system:** European Union
- **Authority/body:** EFSA / European Commission
- **Chemical domain:** Plant protection products
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.efsa.europa.eu/en/topics/environmental-risk-assessment-pesticides
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Plant protection assessments require EFSA/Commission guidance plus FOCUS exposure models. The pesticide workflow must be crop, application, scenario and tier specific.



## EUR-006 — FOCUS fate models and guidance

- **Jurisdiction/system:** European Union
- **Authority/body:** European Commission JRC / FOCUS
- **Chemical domain:** Pesticide environmental exposure
- **Version/effective-date note:** Portal refreshed in 2026; individual documents have own versions
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://esdac.jrc.ec.europa.eu/projects/focus-dg-sante
- **Mapped product classes:** pesticides, environmental_exposure
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, scenario_registry, sediment, source_provenance, surface_water, tier_comparison

**Implementation note:** FOCUS is a model-and-scenario system, not just a list of executables. Preserve scenario versions, weather/crop data, model versions and step/tier.



## EUR-007 — FOCUS Groundwater guidance and models (PEARL, PELMO, MACRO)

- **Jurisdiction/system:** European Union
- **Authority/body:** FOCUS / JRC
- **Chemical domain:** Pesticide groundwater
- **Version/effective-date note:** Generic Tier 1 guidance v2.4 referenced on portal
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://esdac.jrc.ec.europa.eu/projects/ground-water
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, scenario_registry, sediment, source_provenance, surface_water, tier_comparison

**Implementation note:** Groundwater workflow should orchestrate PEARL, PELMO and MACRO with standard FOCUS scenarios and allow refined/site-specific comparison only when permitted.



## EUR-008 — FOCUS Surface Water guidance and models (PRZM, MACRO, TOXSWA, SWASH)

- **Jurisdiction/system:** European Union
- **Authority/body:** FOCUS / JRC
- **Chemical domain:** Pesticide surface water
- **Version/effective-date note:** Individual model/guidance versions vary
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://esdac.jrc.ec.europa.eu/projects/surface-water
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, scenario_registry, sediment, source_provenance, surface_water, tier_comparison

**Implementation note:** Surface-water workflow should orchestrate PRZM/MACRO loading and TOXSWA fate, preserving SWASH/FOCUS scenario assumptions and time-weighted outputs.



## EUR-009 — Pesticide risk-assessment guidance and tools

- **Jurisdiction/system:** European Union
- **Authority/body:** EFSA
- **Chemical domain:** Pesticides; food safety
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.efsa.europa.eu/en/applications/pesticides/tools
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides; food safety. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-010 — Guidance on harmonised methodologies for human health, animal health and ecological risk assessment of combined exposure to multiple chemicals

- **Jurisdiction/system:** European Union
- **Authority/body:** EFSA
- **Chemical domain:** Chemical mixtures
- **Version/effective-date note:** 2019; supporting guidance/tools updated subsequently
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.efsa.europa.eu/en/topics/topic/chemical-mixtures
- **Mapped product classes:** ecological_risk
- **Mapped EnviroChem modules:** mixture_assessment, regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for chemical mixtures. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-011 — EFSA chemicals-in-food methodology and OpenFoodTox

- **Jurisdiction/system:** European Union
- **Authority/body:** EFSA
- **Chemical domain:** Food and feed chemicals
- **Version/effective-date note:** OpenFoodTox 2025 dataset noted by EFSA
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.efsa.europa.eu/en/topics/topic/chemicals-food
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food and feed chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-012 — Food Contact Materials guidance and application procedures

- **Jurisdiction/system:** European Union
- **Authority/body:** EFSA
- **Chemical domain:** Food-contact materials
- **Version/effective-date note:** Application guidance republished 2021; portal current
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.efsa.europa.eu/en/topics/topic/food-contact-materials
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food-contact materials. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-013 — Guideline on the environmental risk assessment of medicinal products for human use

- **Jurisdiction/system:** European Union
- **Authority/body:** European Medicines Agency (EMA)
- **Chemical domain:** Human pharmaceuticals
- **Version/effective-date note:** Effective 1 September 2024
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.ema.europa.eu/en/environmental-risk-assessment-medicinal-products-human-use-scientific-guideline
- **Mapped product classes:** human_pharmaceuticals
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** EMA's current human-medicinal-product ERA guideline is effective from 1 September 2024 and uses Phase I/Phase II, PEC, PBT and risk concepts. Implement as a dedicated versioned pharmaceutical ruleset, not a generic REACH scenario.



## EUR-014 — Environmental risk assessment for veterinary medicines

- **Jurisdiction/system:** European Union
- **Authority/body:** EMA
- **Chemical domain:** Veterinary pharmaceuticals
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.ema.europa.eu/en/veterinary-regulatory-overview/marketing-authorisation-veterinary-medicines/environmental-risk-assessment-veterinary-medicines
- **Mapped product classes:** veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** metabolism_excretion, pnec, regulatory_navigator, simpletreat, soil, source_provenance, spc_emissions, surface_water

**Implementation note:** Register this official pathway for veterinary pharmaceuticals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-015 — SCCS Notes of Guidance for testing cosmetic ingredients and safety evaluation, 12th revision

- **Jurisdiction/system:** European Union
- **Authority/body:** Scientific Committee on Consumer Safety (SCCS)
- **Chemical domain:** Cosmetics
- **Version/effective-date note:** 12th revision May 2023; corrigendum December 2023
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://health.ec.europa.eu/publications/sccs-notes-guidance-testing-cosmetic-ingredients-and-their-safety-evaluation-12th-revision_en
- **Mapped product classes:** cosmetics
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for cosmetics. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-016 — Dangerous substances risk-assessment tools and OSH framework

- **Jurisdiction/system:** European Union
- **Authority/body:** EU-OSHA / national labour authorities
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** E-tool updated in 2026
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://osha.europa.eu/en/themes/dangerous-substances
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-017 — UK REACH guidance and evaluation approach

- **Jurisdiction/system:** United Kingdom (Great Britain)
- **Authority/body:** Health and Safety Executive (HSE)
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Portal updated 2025-2026
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.hse.gov.uk/reach/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** UK REACH is autonomous for Great Britain. Store UK-specific legal status, registration context and current HSE guidance; do not silently reuse EU submission assumptions.



## EUR-018 — GB Biocidal Products Regulation guidance

- **Jurisdiction/system:** United Kingdom
- **Authority/body:** HSE / Environment Agency
- **Chemical domain:** Biocides
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.hse.gov.uk/biocides/applications/index.htm
- **Mapped product classes:** biocides
- **Mapped EnviroChem modules:** ecotox, environmental_exposure, regulatory_navigator, simpletreat, source_provenance, use_scenario

**Implementation note:** Register this official pathway for biocides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-019 — Pesticide registration and risk-assessment guidance

- **Jurisdiction/system:** United Kingdom
- **Authority/body:** HSE Chemicals Regulation Division
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Living guidance portal
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.hse.gov.uk/pesticides/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## EUR-020 — COSHH risk assessment guidance

- **Jurisdiction/system:** United Kingdom
- **Authority/body:** HSE
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** Living guidance portal
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.hse.gov.uk/coshh/basics/assessment.htm
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** COSHH is task-specific. SDS information is an input, not the assessment. The lab module must ask about actual operation, exposure routes, people, quantities, duration, controls and review triggers before drafting.



## EUR-021 — Chemicals Ordinance (ChemO) guidance and notification authority portal

- **Jurisdiction/system:** Switzerland
- **Authority/body:** Federal chemicals authorities (FOEN/FOPH/SECO)
- **Chemical domain:** Industrial chemicals; biocides
- **Version/effective-date note:** Living portal
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.anmeldestelle.admin.ch/en/chemicals-ordinance-chemo
- **Mapped product classes:** industrial_chemicals, biocides
- **Mapped EnviroChem modules:** ecotox, environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, simpletreat, source_provenance, use_scenario

**Implementation note:** Swiss ChemO is substantially harmonised with REACH/CLP but autonomous, with separate notification and restriction mechanisms. Link ChemO, ORRChem and the relevant EU provisions/version.



## EUR-022 — KKDIK (Türkiye REACH) legislation and implementation guidance

- **Jurisdiction/system:** Türkiye
- **Authority/body:** Ministry of Environment, Urbanisation and Climate Change
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify current deadlines and ministry notices
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://kimyasallar.csb.gov.tr/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## EUR-023 — EAEU Technical Regulation 041/2017 on safety of chemical products

- **Jurisdiction/system:** Eurasian Economic Union
- **Authority/body:** Eurasian Economic Commission / member-state authorities
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify in each EAEU member state
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://eec.eaeunion.org/en/comission/department/deptexreg/tr/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## EUR-024 — Ukraine chemicals safety technical regulation / REACH-aligned reforms

- **Jurisdiction/system:** Ukraine
- **Authority/body:** Ministry of Environmental Protection and Natural Resources
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify enactment and transition dates
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://mepr.gov.ua/en/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.




# North America


## NAM-001 — EPA Risk Assessment Guidance portal

- **Jurisdiction/system:** United States
- **Authority/body:** US Environmental Protection Agency (EPA)
- **Chemical domain:** Cross-cutting chemical risk
- **Version/effective-date note:** Updated 8 January 2026
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.gov/risk/risk-assessment-guidance
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** EPA risk-assessment guidance is programme-specific. The US pathway must identify the governing programme before selecting methods or models.



## NAM-002 — TSCA Risk Evaluations for Existing Chemicals

- **Jurisdiction/system:** United States
- **Authority/body:** US EPA Office of Pollution Prevention and Toxics
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Living programme
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/risk-evaluations-existing-chemicals-under-tsca
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** TSCA existing-chemical risk evaluations require condition-of-use, exposure, hazard and risk-characterisation records. Add condition-of-use and potentially exposed population fields.



## NAM-003 — Guidance for Human Health Risk Assessments for Pesticides

- **Jurisdiction/system:** United States
- **Authority/body:** US EPA
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Updated content through 2026
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/guidance-human-health-risk-assessments-pesticides
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## NAM-004 — Technical Overview of Ecological Risk Assessment for the Pesticide Program

- **Jurisdiction/system:** United States
- **Authority/body:** US EPA
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Living guidance
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/technical-overview-ecological-risk-assessment
- **Mapped product classes:** pesticides, ecological_risk
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** EPA pesticide ecological assessment is tiered. Preserve screening assumptions, refinement triggers, taxa/endpoints and mitigation decisions.



## NAM-005 — Models and databases used in pesticide risk assessment

- **Jurisdiction/system:** United States
- **Authority/body:** US EPA
- **Chemical domain:** Pesticide environmental exposure
- **Version/effective-date note:** Updated 2025-2026
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-and-databases-used-pesticide-risk-assessment
- **Mapped product classes:** pesticides, environmental_exposure
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, scenario_registry, sediment, source_provenance, surface_water, tier_comparison

**Implementation note:** EPA model selection spans aquatic, terrestrial, atmospheric and health models. PWC is current for water exposure; legacy PRZM/EXAMS may be retained for reproducibility with clear status labels.



## NAM-006 — OCSPP Harmonized Test Guidelines

- **Jurisdiction/system:** United States
- **Authority/body:** US EPA
- **Chemical domain:** Test methods
- **Version/effective-date note:** Verify individual guideline revisions
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.gov/test-guidelines-pesticides-and-toxic-substances
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** OCSPP harmonised guidelines should be stored by guideline number and revision, with OECD equivalence/crosswalk where applicable.



## NAM-007 — Risk Assessment Guidance for Superfund (RAGS)

- **Jurisdiction/system:** United States
- **Authority/body:** US EPA Superfund
- **Chemical domain:** Contaminated land
- **Version/effective-date note:** Living portal
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.epa.gov/risk/risk-assessment-guidance-superfund-rags
- **Mapped product classes:** contaminated_sites
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for contaminated land. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## NAM-008 — Food Ingredients and Packaging guidance / premarket submissions

- **Jurisdiction/system:** United States
- **Authority/body:** US Food and Drug Administration (FDA)
- **Chemical domain:** Food chemicals
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.fda.gov/food/food-ingredients-packaging
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## NAM-009 — Environmental assessment under NEPA

- **Jurisdiction/system:** United States
- **Authority/body:** FDA
- **Chemical domain:** Human and veterinary products
- **Version/effective-date note:** 21 CFR Part 25; product-centre guidance varies
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.fda.gov/regulatory-information/search-fda-guidance-documents/environmental-assessment-human-drug-and-biologics-applications
- **Mapped product classes:** human_pharmaceuticals, veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** FDA environmental assessment is governed by NEPA and 21 CFR Part 25, with categorical exclusions for some actions. Build a separate US pharmaceutical pathway and categorical-exclusion decision record.



## NAM-010 — Chemical hazards, permissible exposure limits and NIOSH risk resources

- **Jurisdiction/system:** United States
- **Authority/body:** Occupational Safety and Health Administration / NIOSH
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** Living collections
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.osha.gov/chemical-hazards
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## NAM-011 — Toxicological Profiles and Minimal Risk Levels

- **Jurisdiction/system:** United States
- **Authority/body:** Agency for Toxic Substances and Disease Registry (ATSDR)
- **Chemical domain:** Human health / contaminated sites
- **Version/effective-date note:** Living collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.atsdr.cdc.gov/toxprofiledocs/index.html
- **Mapped product classes:** contaminated_sites
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for human health / contaminated sites. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## NAM-012 — Risk assessment of chemical substances under CEPA

- **Jurisdiction/system:** Canada
- **Authority/body:** Environment and Climate Change Canada / Health Canada
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Overview updated June 2026
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.canada.ca/en/health-canada/services/chemical-substances/canada-approach-chemicals/risk-assessment.html
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Canadian CEPA/CMP assessment combines environment and human health. The platform should support ecological-risk outputs while linking to broader CEPA evidence requirements.



## NAM-013 — Guidance document for the New Substances Notification Regulations (Chemicals and Polymers)

- **Jurisdiction/system:** Canada
- **Authority/body:** Environment and Climate Change Canada / Health Canada
- **Chemical domain:** New industrial chemicals
- **Version/effective-date note:** Living guidance
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.canada.ca/en/environment-climate-change/services/managing-pollution/evaluating-new-substances/chemicals-polymers/guidance.html
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** New Substances Notification requires volume/category-specific information for chemicals and polymers. Add notification category, volume threshold and polymer-specific logic.



## NAM-014 — Framework for risk assessment and risk management of pest control products

- **Jurisdiction/system:** Canada
- **Authority/body:** Health Canada Pest Management Regulatory Agency (PMRA)
- **Chemical domain:** Pesticides
- **Version/effective-date note:** 2023 portal edition
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.canada.ca/en/health-canada/services/consumer-product-safety/reports-publications/pesticides-pest-management/policies-guidelines/risk-management-pest-control-products.html
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** PMRA uses a risk-assessment and risk-management framework for pest control products. Include decision and mitigation records, not just exposure estimates.



## NAM-015 — Health Canada approach to environmental risk assessment for pest control products

- **Jurisdiction/system:** Canada
- **Authority/body:** PMRA
- **Chemical domain:** Pesticides
- **Version/effective-date note:** 2023
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.canada.ca/en/health-canada/services/consumer-product-safety/reports-publications/pesticides-pest-management/policies-guidelines/approach-environmental-risk-assessment.html
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** PMRA environmental risk assessment should be a Canadian ruleset with Canadian exposure scenarios/defaults and not merely a US EPA copy.



## NAM-016 — PMRA policies and guidelines portal

- **Jurisdiction/system:** Canada
- **Authority/body:** PMRA
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Includes SPN2026-01
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.canada.ca/en/health-canada/services/consumer-product-safety/reports-publications/pesticides-pest-management/policies-guidelines.html
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** PMRA policy/guidance is a living collection. Source version and document type must be recorded; harmonisation documents do not eliminate Canadian requirements.



## NAM-017 — WHMIS and workplace chemical risk resources

- **Jurisdiction/system:** Canada
- **Authority/body:** Canadian Centre for Occupational Health and Safety / federal and provincial regulators
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** WHMIS requirements depend on federal/provincial law
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.canada.ca/en/health-canada/services/environmental-workplace-health/occupational-health-safety/workplace-hazardous-materials-information-system.html
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.




# Australia and New Zealand


## OCE-001 — Guide to categorising chemical importation and manufacture

- **Jurisdiction/system:** Australia
- **Authority/body:** Australian Industrial Chemicals Introduction Scheme (AICIS)
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Updated 22 May 2026
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.industrialchemicals.gov.au/help-and-guides/guide-categorising-your-chemical-importation-and-manufacture
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** AICIS categorisation is exposure-and-hazard based and determines introduction category and information obligations. Add import/manufacture volume, introduction circumstances and category decision.



## OCE-002 — Industrial Chemicals Categorisation Guidelines

- **Jurisdiction/system:** Australia
- **Authority/body:** AICIS
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** September 2025 edition; September 2026 changes not yet effective at snapshot
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.industrialchemicals.gov.au/help-and-guides/industrial-chemicals-categorisation-guidelines
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** The AICIS categorisation guideline is version-sensitive, with a September 2026 change watch. Build an effective-date gate and warn against using future rules early.



## OCE-003 — Risk assessment manuals portal

- **Jurisdiction/system:** Australia
- **Authority/body:** Australian Pesticides and Veterinary Medicines Authority (APVMA)
- **Chemical domain:** Agricultural and veterinary chemicals
- **Version/effective-date note:** Manual components have individual dates
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.apvma.gov.au/registrations-and-permits/data-guidelines/risk-assessment-manuals
- **Mapped product classes:** veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** APVMA separates data requirements and risk manuals. Route agricultural and veterinary products by use and product type.



## OCE-004 — Risk Assessment Manual - Environment

- **Jurisdiction/system:** Australia
- **Authority/body:** APVMA
- **Chemical domain:** Agricultural and veterinary chemicals
- **Version/effective-date note:** Portal current; appendices individually updated
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.apvma.gov.au/registrations-and-permits/data-guidelines/risk-assessment-manuals/environment
- **Mapped product classes:** veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** The APVMA environment manual is the core Australian environmental assessment pack. Include Australian scenarios, protection goals, exposure, effects and risk/refinement logic.



## OCE-005 — Model WHS laws and hazardous chemicals guidance

- **Jurisdiction/system:** Australia
- **Authority/body:** Safe Work Australia
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** State/territory adoption varies
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.safeworkaustralia.gov.au/safety-topic/hazards/chemicals
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## OCE-006 — National Environment Protection (Assessment of Site Contamination) Measure

- **Jurisdiction/system:** Australia
- **Authority/body:** National Environment Protection Council
- **Chemical domain:** Contaminated land
- **Version/effective-date note:** 1999, amended 2013; check jurisdictional implementation
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.nepc.gov.au/nepms/assessment-site-contamination
- **Mapped product classes:** contaminated_sites
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for contaminated land. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## OCE-007 — Risk Assessment Methodology for Hazardous Substances

- **Jurisdiction/system:** New Zealand
- **Authority/body:** Environmental Protection Authority (EPA NZ)
- **Chemical domain:** Hazardous substances
- **Version/effective-date note:** Updated December 2022
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.govt.nz/assets/Uploads/Documents/Hazardous-Substances/Guidance/Risk-Assessment-Methodology-for-Hazardous-Substances.pdf
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** New Zealand hazardous-substance methodology is a national decision framework. Preserve risk context, uncertainty and controls rather than only numerical outputs.



## OCE-008 — Hazardous substances approvals and guidance

- **Jurisdiction/system:** New Zealand
- **Authority/body:** EPA NZ
- **Chemical domain:** Hazardous substances
- **Version/effective-date note:** Living guidance
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.govt.nz/industry-areas/hazardous-substances/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** EPA NZ approvals are substance/use-specific. Add approval status and controls to the regulatory record.



## OCE-009 — ACVM risk assessment and registration guidance

- **Jurisdiction/system:** New Zealand
- **Authority/body:** Ministry for Primary Industries (MPI)
- **Chemical domain:** Agricultural compounds and veterinary medicines
- **Version/effective-date note:** Living guidance collection
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.mpi.govt.nz/agriculture/agricultural-compounds-vet-medicines/
- **Mapped product classes:** veterinary_pharmaceuticals
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for agricultural compounds and veterinary medicines. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.




# East, South and Southeast Asia


## ASI-001 — Chemical Substances Control Law (CSCL) assessment system

- **Jurisdiction/system:** Japan
- **Authority/body:** METI / MHLW / Ministry of the Environment; NITE
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify annual notices and thresholds
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.nite.go.jp/en/chem/aboutcmc.html
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Japan CSCL requires national classification and evaluation logic. Route by new/existing chemical status and use current notices/thresholds.



## ASI-002 — NITE-CHRIP chemical risk information platform

- **Jurisdiction/system:** Japan
- **Authority/body:** NITE
- **Chemical domain:** Chemical information
- **Version/effective-date note:** Living portal
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.nite.go.jp/en/chem/chrip/chrip_search/systemTop
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** NITE-CHRIP is a discovery and regulatory-information source. Preserve the originating Japanese assessment or legal source.



## ASI-003 — Risk assessment guidelines and evaluation documents

- **Jurisdiction/system:** Japan
- **Authority/body:** Food Safety Commission of Japan
- **Chemical domain:** Food chemicals and pesticides
- **Version/effective-date note:** Living collection
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.fsc.go.jp/english/
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for food chemicals and pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-004 — Measures for the Environmental Management Registration of New Chemical Substances (MEE Order No.12) and supporting guidance

- **Jurisdiction/system:** China
- **Authority/body:** Ministry of Ecology and Environment (MEE)
- **Chemical domain:** New chemical substances
- **Version/effective-date note:** Order No.12 effective 2021; verify 2026 revision status before filing
- **Verification tier:** B
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/gthw/qtxgbz/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** China MEE Order No.12 governs new chemical registration; a 2026 revision is on change watch. Do not automate a filing decision without current Chinese legal verification.



## ASI-005 — National food-safety standards and new food ingredient/additive assessment

- **Jurisdiction/system:** China
- **Authority/body:** National Health Commission / SAMR
- **Chemical domain:** Food chemicals
- **Version/effective-date note:** Standards updated individually
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.nhc.gov.cn/wjw/zcjd/list.shtml
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-006 — K-REACH registration and risk assessment system

- **Jurisdiction/system:** South Korea
- **Authority/body:** Ministry of Environment / Korea Environment Corporation
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Amendments and thresholds change; verify Korean official notices
- **Verification tier:** B
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://kreach.me.go.kr/repwrt/index.do
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** K-REACH thresholds and exemptions are change-sensitive and Korean text controls. Mark calculations as regulatory-navigation support until current local requirements are confirmed.



## ASI-007 — Published chemical risk-assessment reports under K-REACH

- **Jurisdiction/system:** South Korea
- **Authority/body:** National Institute of Environmental Research
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Reports published annually
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://ecolibrary.me.go.kr/nier/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-008 — Toxic and Concerned Chemical Substances Control Act and new/existing chemical registration

- **Jurisdiction/system:** Taiwan
- **Authority/body:** Ministry of Environment / Chemicals Administration
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Living portal
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.cha.gov.tw/mp-1.html
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-009 — Priority Management Chemicals / new chemical registration under occupational law

- **Jurisdiction/system:** Taiwan
- **Authority/body:** Occupational Safety and Health Administration
- **Chemical domain:** Workplace chemicals
- **Version/effective-date note:** Verify current lists and thresholds
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.osha.gov.tw/48110/48417/48419/
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for workplace chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-010 — Guidelines for registration of pesticides

- **Jurisdiction/system:** India
- **Authority/body:** Central Insecticides Board and Registration Committee (CIBRC)
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Guidelines and checklists updated individually
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://ppqs.gov.in/divisions/cib-rc/guidelines
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## ASI-011 — Manufacture, Storage and Import of Hazardous Chemical Rules and chemical accident guidance

- **Jurisdiction/system:** India
- **Authority/body:** Ministry of Environment, Forest and Climate Change / CPCB
- **Chemical domain:** Industrial and hazardous chemicals
- **Version/effective-date note:** Rules amended periodically
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://moef.gov.in/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for industrial and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-012 — Management of Hazardous Substances under EPMA

- **Jurisdiction/system:** Singapore
- **Authority/body:** National Environment Agency (NEA)
- **Chemical domain:** Hazardous substances
- **Version/effective-date note:** Page updated 21 May 2026
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.nea.gov.sg/our-services/pollution-control/chemical-safety/hazardous-substances/management-of-hazardous-substances
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for hazardous substances. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## ASI-013 — Sector-specific safety and product-registration guidance

- **Jurisdiction/system:** Singapore
- **Authority/body:** Singapore Food Agency / Health Sciences Authority
- **Chemical domain:** Food, health products and poisons
- **Version/effective-date note:** Verify product-specific guidance
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.sfa.gov.sg/food-information/risk-at-a-glance/chemical-hazards
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food, health products and poisons. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-014 — A Manual of Recommended Practice on Assessment of the Health Risks Arising from the Use of Chemicals Hazardous to Health at the Workplace (SiRAC)

- **Jurisdiction/system:** Malaysia
- **Authority/body:** Department of Occupational Safety and Health (DOSH)
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** 3rd edition 2019
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.dosh.gov.my/index.php/chemical-management-v/chemical-health-risk-assessment-chra
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## ASI-015 — Industry Code of Practice on Chemicals Classification and Hazard Communication (CLASS ICOP)

- **Jurisdiction/system:** Malaysia
- **Authority/body:** DOSH
- **Chemical domain:** Classification and labelling
- **Version/effective-date note:** Verify current amendment/edition
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.dosh.gov.my/index.php/chemical-management-v/classification-record
- **Mapped product classes:** classification_labelling
- **Mapped EnviroChem modules:** classification_labelling, regulatory_navigator, sds, source_provenance

**Implementation note:** Register this official pathway for classification and labelling. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## ASI-016 — Hazardous Substance Act implementation and sectoral registration guidance

- **Jurisdiction/system:** Thailand
- **Authority/body:** Department of Industrial Works / Food and Drug Administration / Department of Agriculture
- **Chemical domain:** Hazardous substances
- **Version/effective-date note:** Verify responsible agency by product/use
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.diw.go.th/webdiw/en/
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for hazardous substances. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-017 — Sectoral hazardous chemicals, pesticides and food/drug safety requirements

- **Jurisdiction/system:** Indonesia
- **Authority/body:** Ministry of Environment and Forestry / Ministry of Agriculture / BPOM
- **Chemical domain:** Chemicals and pesticides
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.menlhk.go.id/
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for chemicals and pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## ASI-018 — Philippine Inventory of Chemicals and Chemical Substances / Chemical Control Orders

- **Jurisdiction/system:** Philippines
- **Authority/body:** Department of Environment and Natural Resources - Environmental Management Bureau
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify current DENR administrative orders
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://chemical.emb.gov.ph/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-019 — Law on Chemicals and implementing guidance

- **Jurisdiction/system:** Vietnam
- **Authority/body:** Vietnam Chemicals Agency (Vinachemia), Ministry of Industry and Trade
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify current decrees and transition dates
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://vinachemia.gov.vn/en/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## ASI-020 — Agricultural pesticide registration and sectoral environmental controls

- **Jurisdiction/system:** Pakistan
- **Authority/body:** Ministry of National Food Security / Department of Plant Protection; environmental authorities
- **Chemical domain:** Pesticides and hazardous chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://plantprotection.gov.pk/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## ASI-021 — Pesticide registration and environmental-clearance requirements

- **Jurisdiction/system:** Bangladesh
- **Authority/body:** Department of Agricultural Extension / Department of Environment
- **Chemical domain:** Pesticides and hazardous chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://dae.gov.bd/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## ASI-022 — Pesticide registration guidance and national environmental controls

- **Jurisdiction/system:** Sri Lanka
- **Authority/body:** Office of the Registrar of Pesticides / Central Environmental Authority
- **Chemical domain:** Pesticides and hazardous chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://rop.gov.lk/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.




# Latin America and Andean framework


## LAT-001 — Tripartite pesticide risk-assessment and registration system

- **Jurisdiction/system:** Brazil
- **Authority/body:** ANVISA / IBAMA / Ministry of Agriculture
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Product and active-ingredient requirements updated individually
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.gov.br/anvisa/en/regulation-of-products/pesticides
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Brazil pesticide assessment is tripartite across ANVISA, IBAMA and agriculture authorities. Split health, environmental and efficacy/registration workstreams and merge them in the dossier view.



## LAT-002 — Environmental evaluation and classification of pesticides

- **Jurisdiction/system:** Brazil
- **Authority/body:** IBAMA
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Normative instructions and manuals updated individually
- **Verification tier:** B
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.gov.br/ibama/pt-br/assuntos/quimicos-e-biologicos/agrotoxicos
- **Mapped product classes:** pesticides, classification_labelling
- **Mapped EnviroChem modules:** application_scenario, classification_labelling, ecotox, groundwater, model_orchestration, regulatory_navigator, sds, sediment, source_provenance, surface_water

**Implementation note:** IBAMA environmental classification requires Brazilian environmental evidence and decision criteria. Add country-specific classification and mitigation outputs.



## LAT-003 — ANVISA toxicological evaluation and sectoral product guidance

- **Jurisdiction/system:** Brazil
- **Authority/body:** ANVISA
- **Chemical domain:** Food and consumer chemicals
- **Version/effective-date note:** Living regulatory portal
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.gov.br/anvisa/pt-br/assuntos/regulamentacao
- **Mapped product classes:** food_feed
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for food and consumer chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## LAT-004 — Joint pesticide registration and sectoral chemical controls

- **Jurisdiction/system:** Mexico
- **Authority/body:** COFEPRIS / SEMARNAT / SENASICA
- **Chemical domain:** Pesticides and hazardous substances
- **Version/effective-date note:** Verify NOMs, regulations and agency criteria for each product
- **Verification tier:** B
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.gob.mx/cofepris/acciones-y-programas/plaguicidas
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Mexico pesticide registration is joint across COFEPRIS, SEMARNAT and SENASICA. Product/use routing must identify the responsible authority and current NOM/criteria.



## LAT-005 — Environmental risk, hazardous materials and contaminated-site rules

- **Jurisdiction/system:** Mexico
- **Authority/body:** SEMARNAT
- **Chemical domain:** Environmental chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** B
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.gob.mx/semarnat/acciones-y-programas/materiales-y-actividades-riesgosas
- **Mapped product classes:** contaminated_sites
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** SEMARNAT covers environmental risk, hazardous materials and contaminated sites. Treat this as a portal-level pathway until the exact product/use instrument is selected.



## LAT-006 — National chemicals-management and industrial-chemical inventory framework

- **Jurisdiction/system:** Colombia
- **Authority/body:** Ministry of Environment and Sustainable Development
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify current decrees and deadlines
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://quimicos.minambiente.gov.co/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## LAT-007 — Chemical substances notification and inventory system

- **Jurisdiction/system:** Chile
- **Authority/body:** Ministry of Environment / Ministry of Health
- **Chemical domain:** Industrial chemicals
- **Version/effective-date note:** Verify current inventory cycle and decrees
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://sqi.mma.gob.cl/
- **Mapped product classes:** industrial_chemicals
- **Mapped EnviroChem modules:** environmental_exposure, identity_resolution, property_evidence, regulatory_navigator, risk_report, source_provenance

**Implementation note:** Register this official pathway for industrial chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## LAT-008 — Sectoral chemical risk-assessment and registration requirements

- **Jurisdiction/system:** Argentina
- **Authority/body:** SENASA / ANMAT / environmental and labour authorities
- **Chemical domain:** Pesticides, food, workplace and hazardous chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.argentina.gob.ar/senasa/programas-sanitarios/productos-veterinarios-fitosanitarios-y-fertilizantes
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, coshh, ecotox, groundwater, model_orchestration, regulatory_navigator, sds, sediment, source_provenance, surface_water, task_risk_assessment

**Implementation note:** Register this official pathway for pesticides, food, workplace and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## LAT-009 — Andean pesticide registration and national sectoral chemical controls

- **Jurisdiction/system:** Peru
- **Authority/body:** SENASA / DIGESA / Ministry of Environment
- **Chemical domain:** Pesticides and hazardous substances
- **Version/effective-date note:** Andean Manual applies to agricultural pesticides
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.gob.pe/senasa
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous substances. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## LAT-010 — Andean Manual for Registration and Control of Chemical Pesticides for Agricultural Use

- **Jurisdiction/system:** Andean Community
- **Authority/body:** CAN member states
- **Chemical domain:** Agricultural pesticides
- **Version/effective-date note:** Verify current manual/resolutions
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.comunidadandina.org/temas/dg1/sanidad-agropecuaria/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for agricultural pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## LAT-011 — Pesticide registration and sectoral chemical controls

- **Jurisdiction/system:** Costa Rica
- **Authority/body:** Ministry of Agriculture / Ministry of Health / Environment Ministry
- **Chemical domain:** Pesticides and hazardous chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.sfe.go.cr/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.




# Africa and regional pesticide systems


## AFR-001 — Chemicals Management in the Environment sector portal

- **Jurisdiction/system:** South Africa
- **Authority/body:** Department of Forestry, Fisheries and the Environment (DFFE)
- **Chemical domain:** Chemicals management
- **Version/effective-date note:** Living programme
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.dffe.gov.za/chemicals-management-environment-sector
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for chemicals management. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## AFR-002 — Hazardous Chemical Agents Regulations, 2021

- **Jurisdiction/system:** South Africa
- **Authority/body:** Department of Employment and Labour
- **Chemical domain:** Occupational chemicals
- **Version/effective-date note:** 2021
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.gov.za/documents/regulations/hazardous-chemical-agents-regulations-2021-29-mar-2021-0000
- **Mapped product classes:** workplace
- **Mapped EnviroChem modules:** coshh, regulatory_navigator, sds, source_provenance, task_risk_assessment

**Implementation note:** Register this official pathway for occupational chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## AFR-003 — Agricultural remedies registration and risk requirements

- **Jurisdiction/system:** South Africa
- **Authority/body:** Department of Agriculture
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Major legislative reform should be checked
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.nda.gov.za/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## AFR-004 — Sectoral chemical registration and environmental standards

- **Jurisdiction/system:** Nigeria
- **Authority/body:** National Agency for Food and Drug Administration and Control (NAFDAC) / NESREA
- **Chemical domain:** Pesticides, food, consumer and environmental chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.nafdac.gov.ng/
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides, food, consumer and environmental chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## AFR-005 — Pest control product registration and environmental assessment

- **Jurisdiction/system:** Kenya
- **Authority/body:** Pest Control Products Board / NEMA
- **Chemical domain:** Pesticides and environmental chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.pcpb.go.ke/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and environmental chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## AFR-006 — Pesticide registration and chemicals-management requirements

- **Jurisdiction/system:** Ghana
- **Authority/body:** Environmental Protection Agency / Pesticides and Fertilizer Regulatory Division
- **Chemical domain:** Pesticides and hazardous chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.epa.gov.gh/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## AFR-007 — Pesticide authorisation and sectoral chemical controls

- **Jurisdiction/system:** Morocco
- **Authority/body:** ONSSA / Ministry of Energy Transition and Sustainable Development
- **Chemical domain:** Pesticides and chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.onssa.gov.ma/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## AFR-008 — Pesticide registration and environmental controls

- **Jurisdiction/system:** Egypt
- **Authority/body:** Agricultural Pesticides Committee / Egyptian Environmental Affairs Agency
- **Chemical domain:** Pesticides and environmental chemicals
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.apc.gov.eg/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and environmental chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.



## AFR-009 — Common pesticide registration system for CILSS member states

- **Jurisdiction/system:** CILSS member states
- **Authority/body:** Sahelian Pesticides Committee (CSP)
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Verify membership and current decisions
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://insah.cilss.int/index.php/csp/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## AFR-010 — Regional harmonised pesticide registration

- **Jurisdiction/system:** Central African Economic and Monetary Community
- **Authority/body:** Interstate Committee of Pesticides of Central Africa (CPAC)
- **Chemical domain:** Pesticides
- **Version/effective-date note:** Verify membership and national implementation
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.cpac-cemac.org/
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.




# Middle East and Gulf systems


## MEA-001 — Sector-specific registration and safety-assessment guidance

- **Jurisdiction/system:** Saudi Arabia
- **Authority/body:** Saudi Food and Drug Authority / Ministry of Environment, Water and Agriculture
- **Chemical domain:** Pesticides, food and health products
- **Version/effective-date note:** Verify SFDA/MEWA product-specific guidance
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.sfda.gov.sa/en
- **Mapped product classes:** pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides, food and health products. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## MEA-002 — Pesticide registration and hazardous-material controls

- **Jurisdiction/system:** United Arab Emirates
- **Authority/body:** Ministry of Climate Change and Environment / Ministry of Health and Prevention
- **Chemical domain:** Pesticides and hazardous chemicals
- **Version/effective-date note:** Emirate-level requirements may also apply
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.moccae.gov.ae/en/services/registration-of-pesticides
- **Mapped product classes:** pesticides
- **Mapped EnviroChem modules:** application_scenario, ecotox, groundwater, model_orchestration, regulatory_navigator, sediment, source_provenance, surface_water

**Implementation note:** Register this official pathway for pesticides and hazardous chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## MEA-003 — Sectoral chemical risk-assessment and registration systems

- **Jurisdiction/system:** Israel
- **Authority/body:** Ministry of Environmental Protection / Ministry of Health / Ministry of Agriculture
- **Chemical domain:** Industrial chemicals, pesticides, food and workplace
- **Version/effective-date note:** Country-specific verification required
- **Verification tier:** B
- **Source review status:** official_framework_registered_local_detail_required
- **Official source:** https://www.gov.il/en/departments/topics/hazardous_materials/govil-landing-page
- **Mapped product classes:** industrial_chemicals, pesticides, food_feed
- **Mapped EnviroChem modules:** application_scenario, coshh, ecotox, environmental_exposure, groundwater, identity_resolution, model_orchestration, property_evidence, regulatory_navigator, risk_report, sds, sediment, source_provenance, surface_water, task_risk_assessment

**Implementation note:** Register this official pathway for industrial chemicals, pesticides, food and workplace. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier B.



## MEA-004 — GCC/GSO standards and national product-registration systems

- **Jurisdiction/system:** Gulf Cooperation Council
- **Authority/body:** GCC Standardization Organization and national authorities
- **Chemical domain:** Classification, consumer and sector chemicals
- **Version/effective-date note:** Verify national implementation
- **Verification tier:** C
- **Source review status:** international_or_sector_pathway_local_verification_required
- **Official source:** https://www.gso.org.sa/en/
- **Mapped product classes:** classification_labelling
- **Mapped EnviroChem modules:** classification_labelling, regulatory_navigator, sds, source_provenance

**Implementation note:** Register this official pathway for classification, consumer and sector chemicals. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier C.




# Specialist cross-cutting methods


## XCT-001 — ECHA IR&CSA Chapter R.16 - Environmental exposure assessment

- **Jurisdiction/system:** European Union
- **Authority/body:** ECHA
- **Chemical domain:** Environmental exposure
- **Version/effective-date note:** Check ECHA chapter version
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/guidance-documents/guidance-on-information-requirements-and-chemical-safety-assessment
- **Mapped product classes:** environmental_exposure
- **Mapped EnviroChem modules:** model_orchestration, regulatory_navigator, scenario_registry, source_provenance, tier_comparison

**Implementation note:** ECHA R.16 is the core EU environmental-exposure source. Map releases, local/regional scales, STP, air, water, sediment, soil and secondary-poisoning calculations to explicit equations and defaults.



## XCT-002 — ECHA IR&CSA Chapter R.11 and EU hazard guidance

- **Jurisdiction/system:** European Union
- **Authority/body:** ECHA
- **Chemical domain:** PBT/vPvB/PMT/vPvM
- **Version/effective-date note:** Check current chapter and CLP criteria
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/guidance-documents/guidance-on-information-requirements-and-chemical-safety-assessment
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** bioaccumulation, mobility, pbt_pmt_screen, persistence, regulatory_navigator, source_provenance

**Implementation note:** PBT/vPvB and PMT/vPvM screening must use current EU criteria and versioned guidance. Keep screening flags distinct from final regulatory conclusions.



## XCT-003 — OECD Conceptual Framework and endocrine-disruptor test guidance

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD
- **Chemical domain:** Endocrine disruption
- **Version/effective-date note:** Use current TG/GD versions
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.oecd.org/en/topics/sub-issues/testing-of-chemicals/endocrine-disrupter-testing-and-assessment.html
- **Mapped product classes:** endocrine_disruption
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Endocrine-disruption assessment is a testing and weight-of-evidence framework. Trigger specialist review rather than output a simplistic score.



## XCT-004 — OECD work on safety of manufactured nanomaterials

- **Jurisdiction/system:** OECD
- **Authority/body:** OECD
- **Chemical domain:** Nanomaterials
- **Version/effective-date note:** Use latest nano-specific guidance
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.oecd.org/en/topics/sub-issues/safety-of-manufactured-nanomaterials.html
- **Mapped product classes:** nanomaterials
- **Mapped EnviroChem modules:** applicability_warnings, nano_ruleset, particle_properties, regulatory_navigator, source_provenance

**Implementation note:** Nanomaterials need nanoform-specific identity, particle-size, surface and transformation data. Standard dissolved-organic models should raise applicability warnings.



## XCT-005 — Guidelines for Ecological Risk Assessment

- **Jurisdiction/system:** US EPA
- **Authority/body:** US EPA
- **Chemical domain:** Ecological risk
- **Version/effective-date note:** 1998 plus programme-specific updates
- **Verification tier:** A
- **Source review status:** official_source_reviewed
- **Official source:** https://www.epa.gov/risk/guidelines-ecological-risk-assessment
- **Mapped product classes:** ecological_risk
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** EPA ecological risk guidance supports problem formulation, analysis and risk characterisation. Store assessment endpoints, conceptual model and lines of evidence.



## XCT-006 — Guidelines for Carcinogen Risk Assessment

- **Jurisdiction/system:** US EPA
- **Authority/body:** US EPA
- **Chemical domain:** Carcinogenicity
- **Version/effective-date note:** 2005; use current supplements/policies
- **Verification tier:** A
- **Source review status:** official_source_registered_source_deep_read_pending
- **Official source:** https://www.epa.gov/risk/guidelines-carcinogen-risk-assessment
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Register this official pathway for carcinogenicity. Route users by product class and jurisdiction, preserve the source version/effective date, and require local verification where the compendium assigns Tier A.



## XCT-007 — Exposure Factors Handbook and exposure tools

- **Jurisdiction/system:** US EPA
- **Authority/body:** US EPA
- **Chemical domain:** Exposure
- **Version/effective-date note:** 2011 edition with updates; online chapters updated
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.epa.gov/expobox/about-exposure-factors-handbook
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** EPA Exposure Factors Handbook supports scenario inputs and distributions. Store chapter/version and distinguish default from site-specific factors.



## XCT-008 — EU and OECD approaches to new approach methodologies (NAMs)

- **Jurisdiction/system:** European Union
- **Authority/body:** European Commission / ECHA / EFSA
- **Chemical domain:** Alternatives to animal testing
- **Version/effective-date note:** Verify acceptance by endpoint and sector
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://echa.europa.eu/support/registration/how-to-avoid-unnecessary-testing-on-animals
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** applicability_domain, predicted_data, read_across, regulatory_navigator, source_provenance

**Implementation note:** NAM acceptance is endpoint- and sector-specific. The platform may organise evidence but must not state regulatory acceptance without the receiving framework.



## XCT-009 — OECD Principles of GLP and compliance monitoring

- **Jurisdiction/system:** Global
- **Authority/body:** OECD
- **Chemical domain:** Data quality
- **Version/effective-date note:** Revised documents in OECD GLP series
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.oecd.org/en/topics/sub-issues/good-laboratory-practice-and-compliance-monitoring.html
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** evidence_engine, glp_status, regulatory_navigator, source_provenance, study_reliability

**Implementation note:** GLP status is evidence metadata, not a universal quality score. Non-GLP studies may still be scientifically useful; preserve reliability and purpose separately.



## XCT-010 — OECD guidance on data quality, reporting and integrated approaches

- **Jurisdiction/system:** Global
- **Authority/body:** OECD
- **Chemical domain:** Reliability and weight of evidence
- **Version/effective-date note:** Use relevant GD/IATA case studies
- **Verification tier:** A
- **Source review status:** implementation_note_curated_source_deep_read_pending
- **Official source:** https://www.oecd.org/en/topics/sub-issues/assessment-of-chemicals.html
- **Mapped product classes:** cross_cutting
- **Mapped EnviroChem modules:** regulatory_navigator, source_provenance

**Implementation note:** Weight of evidence must be transparent. Store each line of evidence, reliability, relevance, consistency, uncertainty and decision rationale.




## Immediate implementation backlog created from the review

1. Add a versioned framework and guidance database.
2. Add source-review and ruleset-implementation status fields.
3. Add product-class-first regulatory routing.
4. Expand jurisdiction selection beyond EU/UK/US/Switzerland.
5. Add change-watch alerts and effective-date gates.
6. Add endpoint requirement matrices per framework.
7. Add OECD TG and OCSPP crosswalks.
8. Add GLP/MAD and study-acceptance metadata.
9. Add sector-specific templates for pharmaceuticals, veterinary medicines, pesticides, biocides, industrial chemicals and workplace assessments.
10. Add national/regional reporting templates only after source-level review and validation.
11. Preserve a legal-review-required warning for Tier B and Tier C pathways.
12. Build a framework comparison view that explains differences in requirements, models and assumptions.

## Current build status

EnviroChem v2.4 incorporates the complete 139-entry register, official URLs, verification tiers, endpoint checklist, change-watch register, guided pathway selection, searchable framework navigator and API.

It does **not** claim that all 139 legal frameworks are encoded as executable regulatory rules. Source registration, detailed source reading, ruleset implementation and legal confirmation remain separate tracked states.
