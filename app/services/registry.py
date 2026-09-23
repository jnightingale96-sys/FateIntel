from __future__ import annotations

from typing import Any

FRAMEWORKS: list[dict[str, Any]] = [
    {
        "key": "EU",
        "name": "European Union",
        "packs": ["REACH", "Biocides", "Plant protection products", "Human pharmaceuticals", "Veterinary pharmaceuticals"],
        "default_currency": "EUR",
    },
    {
        "key": "UK",
        "name": "United Kingdom",
        "packs": ["UK REACH", "GB Biocides", "GB Plant protection products", "MHRA medicines", "VMD veterinary medicines", "COSHH"],
        "default_currency": "GBP",
    },
    {
        "key": "US",
        "name": "United States",
        "packs": ["TSCA", "FIFRA", "FDA medicines", "Hazard Communication", "Laboratory Chemical Hygiene"],
        "default_currency": "USD",
    },
    {
        "key": "CH",
        "name": "Switzerland",
        "packs": ["ChemO", "ORRChem", "Biocidal Products Ordinance", "Plant protection products", "Swissmedic medicines"],
        "default_currency": "CHF",
    },
    {
        "key": "AU",
        "name": "Australia",
        # AICIS (industrial chemicals, Industrial Chemicals Act 2019) is the
        # regulator this jurisdiction's pathway logic is actually built
        # against -- see _regulatory_programme() for what was researched and
        # what was not. Pesticides/veterinary medicines (APVMA) and human
        # medicines (TGA) are named here as the correct Australian regulators
        # for those groups, not because their own environmental fate
        # methodology has been researched and mapped the way AICIS's has.
        "packs": ["AICIS industrial chemicals", "APVMA pesticides (pathway not yet mapped)", "APVMA veterinary medicines (pathway not yet mapped)", "TGA human medicines (pathway not yet mapped)"],
        "default_currency": "AUD",
    },
    {
        "key": "CA",
        "name": "Canada",
        # ECCC (Environment and Climate Change Canada), administering the
        # Canadian Environmental Protection Act 1999 (CEPA) New Substances
        # Notification regime, is the regulator this jurisdiction's pathway
        # is built against -- its own PNEC assessment-factor method (Okonski
        # et al., 2020) is implemented in canada_pnec.py, verified against
        # ECCC's own published worked example. Pesticides sit with the PMRA
        # (Pest Management Regulatory Agency, Health Canada) instead, whose
        # own methodology has not been researched -- named as an explicit
        # gap, not folded into the CEPA pathway. Human/veterinary
        # pharmaceutical environmental assessment (also Health Canada) is
        # likewise not yet mapped.
        "packs": ["CEPA / ECCC industrial chemicals", "PMRA pesticides (pathway not yet mapped)", "Health Canada human/veterinary medicines (pathway not yet mapped)"],
        "default_currency": "CAD",
    },
    {
        "key": "NZ",
        "name": "New Zealand",
        # NZ EPA Te Mana Rauhi Taiao, under the Hazardous Substances and New
        # Organisms (HSNO) Act 1996, is the regulator this jurisdiction's
        # pathway is built against -- read in full this session ("Risk
        # Assessment Methodology for Hazardous Substances", December 2022).
        # Structurally different from AU/CA/EU: HSNO covers industrial
        # chemicals AND agrichemicals/pesticides under the SAME Act and the
        # SAME regulator (no APVMA/PMRA-style split) -- see
        # _regulatory_programme() for how this is reflected. Human medicines
        # are explicitly excluded from HSNO by the Act itself (Ministry of
        # Health regulates them instead); the guidance document also
        # references the separate Agricultural Compounds and Veterinary
        # Medicines Act 1997, so veterinary medicines/agricultural compounds
        # may sit with a different regulator too -- not confirmed, named as
        # an open question rather than asserted either way.
        "packs": [
            "HSNO Act industrial chemicals and agrichemicals/pesticides",
            "Ministry of Health human medicines (excluded from HSNO, pathway not yet mapped)",
            "ACVM Act veterinary medicines/agricultural compounds (regulator not confirmed)",
        ],
        "default_currency": "NZD",
    },
    {
        "key": "JP",
        "name": "Japan",
        # Researched this session (REGION_RESEARCH_JP_CN_KR_IN.md). CSCL (Chemical Substances Control Law, 1973)
        # is jointly administered by METI, MHLW and the Ministry of the Environment for new industrial chemicals
        # -- confirmed via METI's own overview. A 2026-09-22 follow-up fetched a NITE technical presentation that
        # confirms the method's real shape (government-run Hazard/Exposure Class screening matrix, then a PEC vs
        # DNEL/PNEC Risk Assessment for Priority Assessment Chemical Substances) -- current numeric thresholds
        # were not verified (a 2022 revision exists, unread). The Agricultural Chemicals Regulation Act's own
        # criterion (a Predicted Environmental Concentration compared against MoE standards for public waters) was
        # read from the official translation and IS named below, though its calculation method is not encoded
        # either. MHLW's 2016 pharmaceutical environmental risk assessment guidance (PEC/PNEC ratio, 0.01
        # microgram/L action limit) is confirmed only via secondary academic citations, not the MHLW notification.
        "packs": [
            "CSCL industrial chemicals (METI/MHLW/MoE; screening/PEC-DNEL/PNEC structure confirmed, current numeric criteria not verified)",
            "Agricultural Chemicals Regulation Act pesticides (PEC criterion named, calculation not yet mapped)",
            "MHLW pharmaceutical environmental risk assessment (secondary-sourced, not yet mapped)",
            "Soil Contamination Countermeasures Act (2002; contaminated land only)",
        ],
        "default_currency": "JPY",
    },
    {
        "key": "CN",
        "name": "China",
        # Researched this session (REGION_RESEARCH_JP_CN_KR_IN.md). "China REACH" (MEE Order No. 12, 2020) is
        # administered by the Ministry of Ecology and Environment; a comprehensive revision is due to replace it
        # on 15 August 2026. The Soil Pollution Prevention and Control Law (2018/2019) was read in full this
        # session and names both public health and the ecological environment in its own purpose clause. Pesticide
        # registration sits with the Ministry of Agriculture and Rural Affairs, and that same law requires it to
        # assess pesticide/fertiliser impact on the soil environment -- confirmed by statute, not by practice.
        "packs": [
            "China REACH / MEE new-chemical registration (named PEC/PNEC-style guideline confirmed, numeric factors not verified)",
            "Ministry of Agriculture and Rural Affairs pesticide registration (pathway not yet mapped)",
            "Soil Pollution Prevention and Control Law (2018/2019; contaminated land)",
            "Pharmaceutical-manufacturing discharge standards (MEE, GB 219xx series; effluent control, not a "
            "pre-market ERA -- no pre-market pharmaceutical ERA guideline was found)",
        ],
        "default_currency": "CNY",
    },
    {
        "key": "KR",
        "name": "South Korea",
        # Researched this session (REGION_RESEARCH_JP_CN_KR_IN.md). K-REACH (Act on the Registration and
        # Evaluation of Chemical Substances, in force 2015) is administered by the Ministry of Environment with
        # NIER evaluating dossiers. The Agrochemicals Control Act's administering body is now confirmed
        # (2026-09-22 follow-up): the Rural Development Administration (RDA) issues agrochemical registration
        # certificates operationally, under the Ministry of Agriculture, Food and Rural Affairs' (MAFRA) statutory
        # authority over the Act -- corroborated across the KLRI official translation, a USDA FAS country report
        # and a compliance-industry secondary source. The Soil Environment Conservation Act was summarised from a
        # secondary source, not read in full, unlike Japan's and China's soil laws.
        "packs": [
            "K-REACH new-chemical registration (MoE/NIER; quantitative method not yet mapped)",
            "Agrochemicals Control Act pesticides (RDA registration under MAFRA authority; pathway not yet mapped)",
            "Soil Environment Conservation Act (contaminated land; summarised, not primary-verified)",
            "MFDS pharmaceutical environmental-information requirement (real requirement, named guideline not "
            "located; pathway not yet mapped)",
        ],
        "default_currency": "KRW",
    },
    {
        "key": "IN",
        "name": "India",
        # Researched this session (REGION_RESEARCH_JP_CN_KR_IN.md). India has no comprehensive chemicals-
        # registration law in force: the "Chemicals (Management and Safety) Rules" ("India REACH") remains a
        # draft (fifth public draft), so it is NOT named as the industrial-chemicals regime here. The operative
        # regime instead is the Manufacture, Storage and Import of Hazardous Chemicals Rules, 1989 (MSIHC), made
        # under the Environment (Protection) Act 1986 and enforced by CPCB/State PCBs -- confirmed still in force
        # this session but not read in full. Pesticides sit with CIBRC under the Insecticides Act, 1968,
        # confirmed via CIBRC's own government page. The Environment Protection (Management of Contaminated
        # Sites) Rules, 2025 (Notification S.O. 3401(E), 24 July 2025) is India's first codified contaminated-
        # land procedure and, uniquely among this session's four new jurisdictions, its own scope language
        # explicitly names soil, groundwater, surface water and sediment together.
        "packs": [
            "MSIHC 1989 hazardous industrial chemicals (CPCB/MoEFCC; quantitative method not yet mapped)",
            "Insecticides Act 1968 pesticides, CIBRC (pathway not yet mapped)",
            "Chemicals (Management and Safety) Rules / 'India REACH' (still a draft, not enacted -- not a supported pathway)",
            "Environment Protection (Management of Contaminated Sites) Rules 2025 (contaminated land)",
            "CDSCO pharmaceuticals (no environmental risk assessment requirement -- confirmed, not a gap)",
        ],
        "default_currency": "INR",
    },
    {
        "key": "NO",
        "name": "Norway",
        # Researched 2026-09-23. Norway applies EU REACH directly via the EEA Agreement (Miljodirektoratet is
        # the competent authority; confirmed on Miljodirektoratet's own REACH pages) -- the same substantive
        # regime as EU REACH, incorporated through EEA Joint Committee decisions (which can lag behind new EU
        # amendments -- an administrative timing gap, not a methodological one). Pesticides sit in the EU's
        # Northern Zone under Regulation (EC) 1107/2009 with Mattilsynet as the competent authority -- FOCUS
        # scenarios are the shared baseline, but Mattilsynet's own national-requirements page (read in full)
        # confirms real, documented deviations: FOCUS MACRO 5.5.4 is mandated for groundwater leaching, and
        # Mattilsynet's own six-scenario surface-water selection (as of November 2023) drops three of FOCUS's
        # nine standard scenarios (D5, D6, R3). Human and veterinary pharmaceuticals: the EU/EEA medicines
        # network and Regulation (EU) 2019/6 (extended to Norway by EEA Joint Committee Decision No. 371/2021)
        # both apply as-is; no Norway-specific numeric deviation was found.
        "packs": [
            "REACH (via EEA incorporation; Miljodirektoratet; same substantive regime as EU REACH)",
            "Plant protection products (Northern Zone, FOCUS baseline; Mattilsynet mandates FOCUS MACRO 5.5.4 for groundwater and a confirmed six-scenario, not nine-scenario, surface-water selection)",
            "Human pharmaceuticals (EMA two-phase environmental risk assessment guideline, applied via the EU/EEA medicines network)",
            "Veterinary pharmaceuticals (Regulation (EU) 2019/6, extended to Norway via EEA Joint Committee Decision No. 371/2021)",
        ],
        "default_currency": "NOK",
    },
    {
        "key": "AE",
        "name": "United Arab Emirates",
        # Researched 2026-09-23. No REACH-equivalent chemicals registration regime with a PEC/PNEC-style
        # environmental risk assessment was confirmed for the UAE -- an open research gap, not a confirmed
        # absence. Pesticide registration recently transferred from MOCCAE to the Emirates Drug Establishment
        # (EDE); the GCC-wide Pesticides Act (ratified as UAE domestic law, 2007, read in full via FAOLEX)
        # requires registration to confirm a pesticide is "not harmful" to the environment (Article 2), but
        # delegates the actual method to national executive regulations, which were not located -- the Act
        # itself specifies no quantitative method. Human medicines: EDE (established under Federal Decree-Law
        # No. 38 of 2024) is now the registering authority; a GCC-wide "Module 1" dossier structure is
        # referenced regionally and Saudi Arabia's own Module 1.5 (see "SA" entry) plausibly extends here, but
        # this was not confirmed on a UAE primary source. Veterinary medicines: a new Federal Decree-Law No. 21
        # of 2025 on veterinary medical products was enacted; secondary reporting describes an environmental-
        # disposal element, but the primary legislative text was not read and no quantitative method was
        # confirmed.
        "packs": [
            "Chemicals registration (no REACH-equivalent environmental risk assessment regime confirmed; open gap)",
            "Pesticides (GCC Pesticides Act, EDE administered; requires a general environmental-harm check, no quantitative method specified)",
            "Human pharmaceuticals (EDE; GCC Module 1 structure referenced regionally, not confirmed on a UAE primary source)",
            "Veterinary pharmaceuticals (Federal Decree-Law No. 21/2025; environmental element reported, not confirmed from primary text)",
        ],
        "default_currency": "AED",
    },
    {
        "key": "SA",
        "name": "Saudi Arabia",
        # Researched 2026-09-23. No REACH-equivalent chemicals registration regime with a PEC/PNEC-style
        # environmental risk assessment was confirmed -- SASO/SABER governs import conformity, not an
        # environmental risk method; secondary sources claim REACH-like adoption but no primary text was found.
        # Pesticides: the GCC Pesticides Act (ratified as Saudi domestic law, 2006), administered by the
        # Ministry of Environment, Water and Agriculture (MEWA), requires a general environmental-harm check
        # (Article 2) but specifies no quantitative method. Human pharmaceuticals: the SFDA's own "Data
        # Requirements for Human Drugs Submission" (DS-REQ-002-V4.0, read in full) contains Module 1 Section
        # 1.5 "Environmental Risk Assessment", requiring an evaluation of use/storage/disposal risk to the
        # environment -- a real, confirmed, primary-sourced requirement -- but the document does not itself
        # specify a quantitative PEC/PNEC method. Veterinary medicines: SFDA's Drug Sector is confirmed to
        # regulate veterinary medicines through the same Saudi Drug Registration system, but no veterinary-
        # specific data-requirements guideline analogous to DS-REQ-002 was located, so whether the same
        # Section 1.5 requirement applies to veterinary dossiers is not confirmed.
        "packs": [
            "Chemicals registration (no REACH-equivalent environmental risk assessment regime confirmed; open gap)",
            "Pesticides (GCC Pesticides Act, MEWA administered; requires a general environmental-harm check, no quantitative method specified)",
            "Human pharmaceuticals (SFDA DS-REQ-002-V4.0 Module 1 Section 1.5 Environmental Risk Assessment; requirement confirmed from primary text, no quantitative method specified)",
            "Veterinary pharmaceuticals (SFDA Saudi Drug Registration system; whether the human ERA requirement extends to veterinary dossiers not confirmed)",
        ],
        "default_currency": "SAR",
    },
    {
        "key": "BR",
        "name": "Brazil",
        # Researched 2026-09-23. Law 15.022/2024 created the INSQ (Inventario Nacional de Substancias
        # Quimicas), a REACH-like registration/risk-control regime for substances above volume thresholds, in
        # force since 15 November 2024 -- led by the Ministry of Environment and Climate Change (MMA) via its
        # GT Regulacao de Substancias Quimicas under CONASQ. Its implementing decree (dossier format,
        # assessment method) was still in public consultation as of the last search (May-June 2025), with full
        # dossiers due 15 November 2026 -- no quantitative method is therefore available yet. IBAMA's CTF/APP
        # is a separate, longstanding federal registry of potentially-polluting activities, not itself a
        # PEC/PNEC method. Pesticides are the strongest-sourced finding of this whole expansion pass: IBAMA's
        # own 2012 methodology document (read as a real, hosted, primary government PDF, though its equations
        # were not read to implementation depth this session) names a two-part method -- PPA (Potencial de
        # Periculosidade Ambiental, a hazard baseline) and ARA (Avaliacao de Risco Ambiental, which layers
        # exposure/use conditions -- application method, dose, crop, climate -- onto that baseline, with
        # aquatic- and soil-organism scenarios). Human pharmaceuticals: no ANVISA requirement for an
        # environmental risk assessment was found; a secondary, peer-reviewed source states plainly that
        # "Brazil and other Latin American regulators have not integrated ERAs into drug approval" -- a
        # confirmed absence, but sourced secondarily, not from ANVISA's own text. Veterinary pharmaceuticals
        # sit with MAPA, not ANVISA; Normative Instruction 26/2009 (antimicrobial veterinary products)
        # explicitly names protecting "animals, human health, and the environment" as a regulatory concern,
        # confirming intent, but no calculation methodology was found in the text located.
        "packs": [
            "INSQ chemicals registration (Law 15.022/2024, MMA/CONASQ; in force, implementing decree and quantitative method not yet finalised)",
            "IBAMA pesticide environmental risk assessment (PPA hazard baseline + ARA exposure-layered risk assessment; real primary methodology document found, not read to calculation depth)",
            "ANVISA human pharmaceuticals (no environmental risk assessment requirement found -- confirmed absence, secondary-sourced)",
            "MAPA veterinary pharmaceuticals (IN 26/2009 names environmental protection as a concern; no calculation method found)",
        ],
        "default_currency": "BRL",
    },
    {
        "key": "MX",
        "name": "Mexico",
        # Researched 2026-09-23. No REACH-like chemicals registration regime with a PEC/PNEC-style
        # environmental risk assessment was found for general industrial chemicals -- COFEPRIS's "registro
        # sanitario" is a sanitary/security control for toxic/hazardous substances and precursors, not a
        # risk-based environmental registration, and the LGPGIR (SEMARNAT/PROFEPA) governs hazardous-waste
        # management plans, not new-substance assessment. This is a genuine open research gap, not a confirmed
        # absence -- the search was not exhaustive enough to rule out a mechanism under another agency.
        # Pesticides sit with the CICOPLAFEST tripartite system (SSA/COFEPRIS health, SEMARNAT environment,
        # SADER/formerly SAGARPA agriculture); a peer-reviewed academic source (SciELO) states explicitly that
        # registration is based on verifying the submitted dossier is complete, not on running a
        # Mexico-specific risk assessment against local environmental conditions and uses -- a genuine
        # confirmed absence of a quantitative method, though sourced secondarily (a peer-reviewed article, not
        # a primary SEMARNAT/COFEPRIS statement). Human pharmaceuticals: COFEPRIS registers drugs via a
        # CTD-format dossier; a single non-government regulatory-consultancy source lists "Environmental Risk
        # Assessment (if applicable)" as part of the submission package, with no method described -- this
        # sourcing is weak (not a primary COFEPRIS guideline/NOM) and is reported as unconfirmed, not asserted.
        # Veterinary pharmaceuticals sit with SENASICA, a distinct agency from COFEPRIS; nothing was found
        # confirming or denying an environmental-assessment requirement there, and it is deliberately not
        # assumed to inherit the (also unconfirmed) human-pharma pathway.
        "packs": [
            "Industrial chemicals (no REACH-equivalent regime found; open research gap, not confirmed absent)",
            "CICOPLAFEST pesticide registration (SSA/COFEPRIS, SEMARNAT, SADER; confirmed absence of a quantitative environmental risk-assessment step -- dossier completeness only, secondary-sourced)",
            "COFEPRIS human pharmaceuticals (an environmental risk assessment is reported as conditionally required by a weak, non-government secondary source only -- not confirmed)",
            "SENASICA veterinary pharmaceuticals (distinct agency from COFEPRIS; environmental-assessment requirement neither confirmed nor denied)",
        ],
        "default_currency": "MXN",
    },
    {
        "key": "SG",
        "name": "Singapore",
        # Researched 2026-09-23. No REACH-like registration or new-substance notification regime exists;
        # instead NEA (National Environment Agency) runs a Hazardous Substances (HS) Licence system under the
        # Environmental Protection and Management Act (EPMA) and its Hazardous Substances Regulations,
        # licensing a specific listed (Second Schedule) set of controlled substances, not a general "all new
        # chemicals" registration. A new mandatory chemical reporting framework for HS licence holders takes
        # effect 1 January 2026 (chemicals meeting GHS acute toxicity Category 1/2, aquatic toxicity Category
        # 1, or PBT criteria) -- primary-sourced (statute/regulations) for the licensing regime, secondary
        # (trade press) for the 2026 update. No PEC/PNEC methodology was found; only "an environmental impact
        # assessment may be required" language for select high-risk substances, with no calculation method
        # described. Pesticides: SFA (Singapore Food Agency) registers under the Control of Plants Act, with
        # NEA Pollution Control Department approval required first -- no quantitative method found. Human
        # pharmaceuticals: HSA's own guidance-documents index (checked directly) lists no general
        # environmental risk assessment / ecotoxicology requirement for standard drug registration -- a
        # confirmed absence for standard products, from a primary source. A secondary source claims an ERA
        # requirement specifically for cell/tissue/gene therapy products, which could not be confirmed against
        # an HSA primary document and is not asserted here. Veterinary medicines sit with AVS (Animal &
        # Veterinary Service, under NParks); nothing was found either confirming or denying an
        # environmental-assessment requirement, and this is a genuine absence-of-evidence finding, not a
        # confirmed absence.
        "packs": [
            "NEA Hazardous Substances Licence (EPMA; listed-substance licensing, not general new-chemical registration; no quantitative method found)",
            "SFA pesticide registration (Control of Plants Act; NEA approval required first; quantitative method not found)",
            "HSA human pharmaceuticals (no environmental risk assessment requirement found for standard products -- confirmed absence, primary-sourced; a cell/tissue/gene-therapy-specific claim is unconfirmed)",
            "AVS veterinary pharmaceuticals (environmental-assessment requirement neither confirmed nor denied)",
        ],
        "default_currency": "SGD",
    },
    {
        "key": "TW",
        "name": "Taiwan",
        # Researched 2026-09-23. The Toxic and Concerned Chemical Substances Control Act (TCCSCA),
        # administered by the Chemicals Administration under the Ministry of Environment (MOENV -- Taiwan's
        # former EPA was elevated/renamed to a ministry in 2023), is explicitly modelled on EU REACH: new
        # substances require registration 90 days pre-manufacture/import, with Phase 1/Standard registration
        # tiers for existing substances (Regulation on New and Existing Chemical Substances Registration, Nov
        # 2021 revision) -- real structure, confirmed by reading the primary law text directly (law.moj.gov.tw),
        # the same "structure confirmed, method not calculable" shape as Japan's CSCL. No PNEC/PEC calculation
        # methodology was found; data requirements are described, not a specific risk-quotient method.
        # Pesticides sit with the Agriculture and Food Agency (the exact current parent-agency name is not
        # confirmed: the Council of Agriculture was reorganised into a Ministry of Agriculture in 2023, and
        # which name is now current was not verified); registration requires "test reports on... environment"
        # but no Taiwan-specific PEC/PNEC document was located. Human pharmaceuticals: TFDA (Ministry of
        # Health and Welfare) uses a CTD-format dossier; an ERA requirement was claimed only by generic
        # regulatory-consulting sources reading as CTD-module boilerplate, not confirmed against a TFDA
        # primary document. Veterinary medicines are regulated separately under the Veterinary Drugs Control
        # Act, jointly with the agriculture-side Animal and Plant Health Inspection Agency on some
        # cross-cutting rules (e.g. a Feb 2024 joint rule on human drugs used in companion animals, effective
        # July 2026) -- a genuinely distinct agency/act from the human pathway, though no environmental
        # risk-assessment requirement was found for it either.
        "packs": [
            "TCCSCA chemicals registration (Chemicals Administration, MOENV; explicitly REACH-modelled, structure confirmed from primary law text, quantitative method not found)",
            "Pesticide registration (Agriculture and Food Agency; current parent-ministry name not confirmed post-2023 reorganisation; quantitative method not found)",
            "TFDA human pharmaceuticals (an environmental risk assessment claim exists only in generic secondary sources -- not confirmed)",
            "Veterinary Drugs Control Act veterinary medicines (distinct act/agency from human pharma; no environmental requirement found)",
        ],
        "default_currency": "TWD",
    },
    {
        "key": "ZA",
        "name": "South Africa",
        # Researched 2026-09-23. No REACH-like chemicals registration/notification regime exists -- confirmed
        # consistently across multiple secondary sources; NEMA (National Environmental Management Act 107 of
        # 1998) authorises the Department of Forestry, Fisheries and the Environment to prohibit/control
        # substances, but only asbestos and PCBs are confirmed as substances actually controlled under NEMA
        # subsidiary regulations -- a genuine confirmed absence of a general regime, not merely unresearched.
        # Pesticides and (for food-producing animals) veterinary "stock remedies" share the SAME instrument --
        # Act 36 of 1947 (Fertilisers, Farm Feeds, Agricultural Remedies and Stock Remedies Act), administered
        # by DALRRD (Registrar of Act 36) -- a genuine structural finding, not an assumption: veterinarian-
        # administered remedies are separately carved out under the Veterinary Act 16 of 1933. A peer-reviewed
        # 2026 literature review (Environmental Monitoring and Assessment) states explicitly that Act 36 "does
        # not include updated provisions to address contemporary environmental risks, such as mandatory
        # environmental risk assessments" -- a confirmed absence for pesticides, from a peer-reviewed source.
        # The same review states SAHPRA's Medicines and Related Substances Act "does not address the entry of
        # pharmaceuticals into the environment" and that "South Africa lacks binding environmental regulations
        # for pharmacovigilance" -- corroborated by SAHPRA's own ZACTD registration-guidance table of contents
        # (fetched directly, partially corrupted but showing no environment/Module 1.6 entry). Whether the
        # same absence applies to the Act 36 stock-remedies data-requirements guideline specifically was not
        # independently verified (a primary-document fetch failed on a certificate error), so veterinary stays
        # "not mapped" rather than a second confirmed-absence claim.
        "packs": [
            "Chemicals regime (no REACH-equivalent registration found -- confirmed absence, not merely unresearched; only asbestos and PCBs confirmed controlled under NEMA)",
            "Act 36 of 1947 pesticide registration (DALRRD; confirmed absence of a mandatory environmental risk assessment -- peer-reviewed source)",
            "SAHPRA human pharmaceuticals (confirmed absence of environmental risk assessment / pharmacovigilance regulation -- peer-reviewed source, corroborated by SAHPRA's own registration-guidance contents)",
            "Act 36 of 1947 veterinary stock remedies (same Act/DALRRD as pesticides, NOT SAHPRA -- a genuine structural finding; ERA-specific absence not independently verified for this pathway)",
        ],
        "default_currency": "ZAR",
    },
]

CONTAMINANT_GROUPS = [
    "industrial_organic",
    "pesticide",
    "biocide",
    "human_pharmaceutical",
    "veterinary_pharmaceutical",
    "personal_care_cosmetic",
    "detergent_cleaner",
    "pfas_persistent_mobile",
    "hydrocarbon_solvent",
    "metal_inorganic",
    "polymer_microplastic",
    "nanomaterial",
    "uvcb_complex_substance",
    "mixture_formulation",
    "emerging_contaminant",
    # Added 2026-09-19 for the legacy-contaminants expansion (research phase
    # documented in LEGACY_CONTAMINANTS_MATRIX_UK/EU/US/TIER234...md at the repo
    # root). These are chemically organic and remain in DISCRETE_ORGANIC_GROUPS
    # below -- their gap versus a pesticide/industrial_organic chemical is
    # missing POPs-regulatory-status and bioaccumulation/food-web/sediment
    # coverage, not an invalid fate-model domain, so native Tier 1-2 screening
    # still applies (see CONTAMINANT_TAXONOMY note below).
    "pah",
    "legacy_pop_organic",
    "organotin",
    # radionuclide and contaminated_mixture are NOT chemically-organic and are
    # excluded from DISCRETE_ORGANIC_GROUPS and hard-blocked in
    # build_assessment_plan() below -- see the taxonomy note.
    "radionuclide",
    "contaminated_mixture",
]

# A working classification of every CONTAMINANT_GROUPS value against the
# founder's requested A-I contaminant taxonomy. This is deliberately a mapping
# of the taxonomy onto groups that already drive real routing above, not a
# parallel system -- see LEGACY_CONTAMINANTS_MATRIX_*.md for the regulatory
# research this rests on. Some groups genuinely span more than one letter in
# the real world (e.g. a legacy organochlorine pesticide is both "B" and "E");
# this picks the single most useful routing category per group rather than
# claiming a precise, exhaustive scientific taxonomy.
CONTAMINANT_TAXONOMY: dict[str, dict[str, str]] = {
    "industrial_organic": {"letter": "A", "label": "Organic chemical"},
    "pesticide": {"letter": "A", "label": "Organic chemical (current-use pesticide)"},
    "biocide": {"letter": "A", "label": "Organic chemical"},
    "human_pharmaceutical": {"letter": "A", "label": "Organic chemical"},
    "veterinary_pharmaceutical": {"letter": "A", "label": "Organic chemical"},
    "personal_care_cosmetic": {"letter": "A", "label": "Organic chemical"},
    "detergent_cleaner": {"letter": "A", "label": "Organic chemical"},
    "emerging_contaminant": {"letter": "A", "label": "Organic chemical"},
    "hydrocarbon_solvent": {
        "letter": "F",
        "label": "Industrial legacy contaminant (petroleum hydrocarbon / chlorinated solvent)",
    },
    "pfas_persistent_mobile": {"letter": "G", "label": "Persistent halogenated compound"},
    "pah": {"letter": "D", "label": "Polycyclic aromatic hydrocarbon"},
    "legacy_pop_organic": {
        "letter": "B",
        "label": "Persistent organic pollutant / legacy organic (PCBs, dioxins/furans, legacy organochlorine pesticides)",
    },
    "organotin": {"letter": "G", "label": "Persistent halogenated compound (organotin)"},
    "metal_inorganic": {"letter": "C", "label": "Metal or metalloid"},
    "radionuclide": {"letter": "specialist", "label": "Radionuclide -- not a chemical-fate assessment"},
    "contaminated_mixture": {"letter": "H", "label": "Contaminated mixture (multiple substances, not one defined chemical)"},
    "polymer_microplastic": {"letter": "other", "label": "Polymer / microplastic"},
    "nanomaterial": {"letter": "other", "label": "Nanomaterial"},
    "uvcb_complex_substance": {"letter": "H", "label": "Complex/UVCB substance"},
    "mixture_formulation": {"letter": "H", "label": "Formulated mixture"},
}

SCENARIOS = [
    "municipal_wastewater",
    "industrial_effluent",
    "wastewater_irrigation",
    "biosolids_to_soil",
    "agricultural_spray",
    "soil_incorporation",
    "surface_water_discharge",
    "groundwater_leaching",
    "laboratory_use",
    "household_use",
    "product_disposal",
]

DISCRETE_ORGANIC_GROUPS = [
    group for group in CONTAMINANT_GROUPS
    if group not in {
        "pfas_persistent_mobile", "metal_inorganic", "polymer_microplastic",
        "nanomaterial", "uvcb_complex_substance", "mixture_formulation",
        "radionuclide", "contaminated_mixture",
    }
]

# Groups where NO native or external model in this registry is a valid route:
# a radionuclide needs a dose-based radiological assessment (a separate regime in
# the UK, Canada, EU/Euratom and IAEA guidance -- though US EPA runs radionuclides
# through the same CERCLA risk-range framework as chemicals, see
# LEGACY_CONTAMINANTS_MATRIX_TIER234_AND_RADIONUCLIDES.md), and a contaminated
# mixture is not one defined substance for single-chemical fate math.
NO_NATIVE_PATHWAY_GROUPS = {"radionuclide", "contaminated_mixture"}
LEGACY_ORGANIC_GROUPS = {"pah", "legacy_pop_organic", "organotin"}

MODELS: list[dict[str, Any]] = [
    {
        "key": "SIMPLETREAT",
        "name": "SimpleTreat",
        "domain": "municipal wastewater treatment",
        "regions": ["EU", "UK", "CH", "US", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native_and_adapter",
        "status": "working_preset",
        "tiers": [1, 2, 3],
        "outputs": ["effluent", "sludge", "air", "degradation"],
    },
    {
        "key": "ACTIVITY_SIMPLETREAT",
        "name": "Activity SimpleTreat",
        "domain": "ionisable chemicals in wastewater treatment",
        "regions": ["EU", "UK", "CH", "US", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native",
        "status": "working_verified_preset",
        "tiers": [2, 3],
        "outputs": ["effluent", "primary_sludge", "secondary_sludge", "air", "degradation"],
    },
    {
        "key": "SIMPLEBOX",
        "name": "SimpleBox 4.0",
        "domain": "regional, continental and global multimedia environmental fate",
        "regions": ["EU", "UK", "CH", "US", "AU", "CA", "NZ"],
        "groups": DISCRETE_ORGANIC_GROUPS,
        "implementation": "managed_adapter",
        "status": "official_adapter_contract",
        "tiers": [2, 3, 4],
        "outputs": ["air_concentration", "water_concentration", "soil_concentration", "sediment_concentration", "intermedia_fluxes"],
    },
    {
        "key": "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN",
        "name": "EnviroChem multimedia fate screen",
        "domain": "transparent steady-state air-water-soil-sediment mass balance",
        "regions": ["EU", "UK", "CH", "US", "AU", "CA", "NZ"],
        "groups": DISCRETE_ORGANIC_GROUPS,
        "implementation": "native_research_screen",
        "status": "working_native_screen",
        "tiers": [1, 2, 3],
        "outputs": ["compartment_masses", "environmental_concentrations", "intermedia_fluxes", "mass_balance"],
    },
    {
        "key": "EPI_SUITE",
        "name": "EPA EPI Suite 4.11",
        "domain": "property, degradation, bioaccumulation and environmental-transport estimation",
        "regions": ["US", "EU", "UK", "CH", "AU", "CA", "NZ"],
        "groups": DISCRETE_ORGANIC_GROUPS,
        "implementation": "managed_adapter",
        "status": "installable_adapter_contract",
        "tiers": [0, 1, 2, 3],
        "outputs": ["physical_chemical_estimates", "biodegradation_estimates", "bioaccumulation_estimates", "level_iii_fugacity", "applicability_warnings"],
    },
    {
        "key": "SPIN",
        "name": "FOCUS SPIN 4.4",
        "domain": "shared FOCUS substance properties and transformation pathways",
        "regions": ["EU", "UK", "CH"],
        "groups": ["pesticide", "biocide", "veterinary_pharmaceutical", "human_pharmaceutical", "emerging_contaminant"],
        "implementation": "managed_dependency_workspace",
        "status": "official_dependency_contract",
        "tiers": [2, 3, 4],
        "outputs": ["substance_record_snapshot", "transformation_pathway", "host_model_readiness", "record_provenance_hash"],
    },
    {
        "key": "PEARL",
        "name": "FOCUS PEARL",
        "domain": "soil and groundwater leaching",
        "regions": ["EU", "UK", "CH", "NO"],
        "groups": ["pesticide", "biocide", "veterinary_pharmaceutical", "human_pharmaceutical", "emerging_contaminant"],
        "implementation": "managed_adapter",
        "status": "installable_adapter",
        "tiers": [2, 3, 4],
        "outputs": ["groundwater_concentration", "soil_profile", "leaching_flux", "passive_plant_uptake_flux"],
    },
    {
        "key": "TOXSWA",
        "name": "FOCUS TOXSWA",
        "domain": "surface water and sediment",
        "regions": ["EU", "UK", "CH", "NO"],
        "groups": ["pesticide"],
        "implementation": "managed_adapter",
        "status": "official_adapter_and_output_parser",
        "tiers": [3, 4],
        "outputs": ["water_concentration", "sediment_concentration", "time_weighted_average", "mass_balance"],
    },
    {
        "key": "ENVIROCHEM_TOXSWA_PROCESS_SCREEN",
        "name": "EnviroChem water–sediment process screen",
        "domain": "surface water and sediment",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native_research_screen",
        "status": "alpha",
        "tiers": [2, 3, 4],
        "outputs": ["peak_water_concentration", "peak_sediment_concentration", "time_weighted_average", "mass_balance", "time_series"],
    },
    {
        "key": "GREATER",
        "name": "GREAT-ER 4",
        "domain": "georeferenced river-basin exposure from WWTP and industrial point sources",
        "regions": ["EU", "UK", "CH", "US"],
        "groups": DISCRETE_ORGANIC_GROUPS,
        "implementation": "managed_adapter",
        "status": "open_source_adapter_contract",
        "tiers": [3, 4],
        "outputs": ["river_reach_concentrations", "catchment_pec_distribution", "sediment_concentrations", "spatial_risk"],
    },
    {
        "key": "EPIE",
        "name": "ePiE pharmaceutical exposure model",
        "domain": "high-resolution spatial exposure to human pharmaceuticals in European surface waters",
        "regions": ["EU", "UK", "CH"],
        "groups": ["human_pharmaceutical"],
        "implementation": "managed_research_adapter",
        "status": "method_and_data_contract",
        "tiers": [3, 4],
        "outputs": ["spatial_surface_water_pec", "catchment_distribution", "monitoring_comparison", "uncertainty"],
    },
    {
        "key": "ENVIROCHEM_CATCHMENT_RIVER_NETWORK",
        "name": "EnviroChem catchment river-network screen",
        "domain": "branched river routing of WWTP and industrial point-source loads",
        "regions": ["EU", "UK", "CH", "US", "AU", "CA", "NZ"],
        "groups": DISCRETE_ORGANIC_GROUPS,
        "implementation": "native_research_screen",
        "status": "working_native_screen",
        "tiers": [1, 2, 3],
        "outputs": ["segment_pecs", "attenuated_loads", "pnec_exceedance", "network_mass_balance"],
    },
    {
        "key": "PELMO",
        "name": "FOCUS PELMO",
        "domain": "soil and groundwater leaching",
        "regions": ["EU", "UK", "CH", "NO"],
        "groups": ["pesticide", "biocide", "veterinary_pharmaceutical", "emerging_contaminant"],
        "implementation": "managed_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["groundwater_concentration", "soil_residue", "leaching_flux"],
    },
    {
        "key": "MACRO",
        "name": "FOCUS MACRO 5.5.4a",
        "domain": "preferential flow and drainage",
        "regions": ["EU", "UK", "CH", "NO"],
        "groups": ["pesticide", "biocide", "veterinary_pharmaceutical", "emerging_contaminant"],
        "implementation": "managed_adapter",
        "status": "official_adapter_contract",
        "tiers": [2, 3, 4],
        "outputs": ["drainage_concentration", "groundwater_concentration", "soil_profile", "m2t_lateral_entry", "run_log"],
    },
    {
        "key": "PRZM",
        "name": "PRZM",
        "domain": "runoff, erosion and root-zone transport",
        "regions": ["US", "EU", "UK", "CH", "NO"],
        "groups": ["pesticide", "biocide", "industrial_organic", "emerging_contaminant", "human_pharmaceutical", "veterinary_pharmaceutical"],
        "implementation": "managed_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["runoff_load", "erosion_load", "leaching_flux"],
    },
    {
        "key": "EXAMS",
        "name": "EXAMS",
        "domain": "receiving-water fate",
        "regions": ["US"],
        "groups": ["pesticide", "biocide", "industrial_organic", "emerging_contaminant"],
        "implementation": "legacy_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["water_concentration", "sediment_concentration", "persistence"],
    },
    {
        "key": "PWC",
        "name": "EPA Pesticide in Water Calculator 3 (PWC3)",
        "domain": "US pesticide water exposure",
        "regions": ["US"],
        "groups": ["pesticide"],
        "implementation": "managed_adapter",
        "status": "current_official_adapter_contract",
        "tiers": [2, 3, 4],
        "outputs": ["surface_water_concentration", "sediment_concentration", "groundwater_concentration", "drinking_water_endpoints", "batch_results"],
    },
    {
        "key": "AGDRIFT",
        "name": "AgDRIFT / AGDISP",
        "domain": "US pesticide spray-drift deposition off the treated site",
        "regions": ["US"],
        "groups": ["pesticide"],
        "implementation": "managed_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["off_site_deposition_fraction", "downwind_deposition_curve"],
    },
    {
        "key": "TERRPLANT",
        "name": "TerrPlant",
        "domain": "US screening-level terrestrial plant exposure from runoff and drift",
        "regions": ["US"],
        "groups": ["pesticide"],
        "implementation": "managed_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["terrestrial_plant_risk_quotient"],
    },
    {
        "key": "TREX",
        "name": "T-REX",
        "domain": "US avian and mammalian dietary exposure from pesticide residues",
        "regions": ["US"],
        "groups": ["pesticide"],
        "implementation": "managed_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["avian_dietary_concentration", "avian_risk_quotient", "mammalian_risk_quotient"],
    },
    {
        "key": "BEEREX",
        "name": "BeeREX",
        "domain": "US screening-level bee exposure and risk quotient",
        "regions": ["US"],
        "groups": ["pesticide"],
        "implementation": "managed_adapter",
        "status": "adapter_planned",
        "tiers": [2, 3, 4],
        "outputs": ["contact_risk_quotient", "oral_risk_quotient"],
    },
    {
        "key": "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN",
        "name": "EnviroChem EU birds & mammals Tier 1 TER screen",
        "domain": "EU plant-protection-product dietary and fish-eating secondary-poisoning risk to birds and mammals",
        # "AU" was added after confirming, directly from APVMA's own Risk
        # Assessment Manual Environment (Appendix A, terrestrial
        # vertebrates), that Australia's pesticide birds/mammals assessment
        # is explicitly "in line with current EFSA (2009) guidance" and uses
        # the same TER >= 10 (acute) / TER >= 5 (reproductive) triggers this
        # module already implements -- see au_apvma.py's own docstring. This
        # is a confirmed methodology match, not the same broad
        # chemistry-is-universal reasoning used for the fully
        # jurisdiction-agnostic native screens elsewhere in this registry.
        "regions": ["EU", "UK", "CH", "AU"],
        "groups": ["pesticide"],
        "implementation": "native_research_screen",
        "status": "working_partial_screen",
        "tiers": [1, 2],
        "outputs": ["acute_dietary_ter", "reproductive_dietary_ter", "fish_secondary_poisoning_ter", "earthworm_secondary_poisoning_ter"],
    },
    {
        "key": "ENVIROCHEM_EU_BEES_SCREEN",
        "name": "EnviroChem EU honey-bee Tier 1 spray screen",
        "domain": "EU plant-protection-product Tier 1 contact/oral/larval/HPG risk screening for honey bees (spray applications only)",
        # Sourced to the EFSA (2013) bee guidance (EFSA Journal 2013;11(7):3295,
        # Section 3.1.2), read in full via an open mirror after
        # efsa.onlinelibrary.wiley.com's Cloudflare bot-detection was not
        # bypassed -- see eu_bees.py's own module docstring. A 2023 revision
        # exists (EFSA Journal 2023;21(5):7989) with a different PEQ-based
        # contact-exposure formulation and updated trigger values tied to a
        # newer specific protection goal; that revision's exact numbers were
        # not confirmed this session and are NOT what this screen implements.
        # Spray applications to honey bees only -- granular and seed-treatment
        # routes, and bumble bee/solitary bee assessments (different trigger
        # values in the same guidance), are NOT implemented.
        "regions": ["EU", "UK", "CH"],
        "groups": ["pesticide"],
        "implementation": "native_research_screen",
        "status": "working_partial_screen",
        "tiers": [1, 2],
        "outputs": ["hq_contact", "etr_acute_adult_oral", "etr_chronic_adult_oral", "etr_larvae", "etr_hpg"],
    },
    {
        "key": "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN",
        "name": "EnviroChem US industrial exposure foundation",
        "domain": "industrial source terms, release routing and worker inhalation/dermal screening",
        "regions": ["US"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native_research_screen",
        "status": "working_alpha_screen",
        "tiers": [1, 2, 3],
        "outputs": [
            "media_specific_release_mass", "managed_waste_transfers",
            "worker_inhalation_dose", "worker_dermal_dose", "groundwater_leaching_screen", "mass_balance",
            "conventional_assessment_completeness",
        ],
    },
    {
        "key": "CHEMSTEER",
        "name": "US EPA ChemSTEER 3.2",
        "domain": "TSCA industrial releases and occupational exposure",
        "regions": ["US"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "managed_external_adapter",
        "status": "official_contract_external_execution",
        "tiers": [2, 3, 4],
        "outputs": [
            "environmental_releases", "worker_inhalation_exposure",
            "worker_dermal_exposure", "engineering_control_basis", "raw_output_archive",
        ],
    },
    {
        "key": "CEM",
        "name": "US EPA Consumer Exposure Model 3.2",
        "domain": "TSCA consumer product and article exposure",
        "regions": ["US"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "managed_external_adapter",
        "status": "official_contract_external_execution",
        "tiers": [2, 3, 4],
        "outputs": [
            "consumer_inhalation_exposure", "consumer_dermal_exposure",
            "consumer_ingestion_exposure", "population_and_lifestage_results",
            "raw_output_archive",
        ],
    },
    {
        "key": "EFAST",
        "name": "US EPA E-FAST 2014",
        "domain": "legacy screening of environmental fate, releases and general-population exposure",
        "regions": ["US"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "managed_legacy_adapter",
        "status": "legacy_contract_external_execution",
        "tiers": [2, 3, 4],
        "outputs": [
            "surface_water_exposure", "air_exposure", "landfill_release",
            "consumer_exposure", "general_population_exposure", "raw_output_archive",
        ],
    },
    {
        "key": "ENVIROCHEM_DUAL_WASTEWATER_IRRIGATION",
        "name": "EnviroChem EU–US wastewater irrigation comparison",
        "domain": "treated-wastewater irrigation, soil accumulation and cross-framework model routing",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native_and_adapter",
        "status": "working_native_screen",
        "tiers": [1, 2, 3, 4],
        "outputs": ["irrigation_loading", "soil_concentration", "surface_water_screen", "eu_workflow_manifests", "us_workflow_manifests", "framework_differences"],
    },
    {
        "key": "ENVIROCHEM_SOIL_SCREEN",
        "name": "EnviroChem soil accumulation screen",
        "domain": "soil mixing, repeat use and accumulation",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native",
        "status": "partial",
        "tiers": [1, 2, 3],
        "outputs": ["soil_pec", "plateau_concentration", "annual_accumulation"],
    },

{
    "key": "ENVIROCHEM_BIOSOLIDS_LAND_APPLICATION",
    "name": "EnviroChem biosolids land application",
    "domain": "WWTP sludge transfer, land loading and repeated soil accumulation",
    "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
    "groups": CONTAMINANT_GROUPS,
    "implementation": "native",
    "status": "working_native_screen",
    "tiers": [1, 2, 3],
    "outputs": ["biosolids_concentration", "chemical_loading", "soil_pec", "repeated_application_series"],
},
{
    "key": "SWASH",
    "name": "FOCUS SWASH",
    "domain": "FOCUS Step 3 surface-water workflow orchestration",
    "regions": ["EU", "UK", "CH", "NO"],
    "groups": ["pesticide", "biocide", "veterinary_pharmaceutical", "human_pharmaceutical", "emerging_contaminant"],
    "implementation": "managed_adapter",
    "status": "installable_orchestrator",
    "tiers": [2, 3, 4],
    "outputs": ["focus_projects", "spray_drift_inputs", "macro_przm_links", "toxswa_run_set"],
},
    {
        "key": "ENVIROCHEM_PLANT_UPTAKE",
        "name": "EnviroChem plant uptake",
        "domain": "root uptake and crop residues",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": ["human_pharmaceutical", "veterinary_pharmaceutical", "pesticide", "emerging_contaminant", "industrial_organic"],
        "implementation": "native",
        "status": "working_screen",
        "tiers": [2, 3, 4],
        "outputs": ["soil_porewater", "tscf", "root_concentration", "shoot_concentration", "edible_tissue_concentration"],
    },
    {
        "key": "ENVIRODESIGN_BIOWIN34_ATTRIBUTION",
        "name": "EnviroDesign structural biodegradation attribution",
        "domain": "explainable structure-to-biodegradation screening",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native",
        "status": "working_research_screen",
        "tiers": [0, 1, 2, 3, 4],
        "outputs": ["biowin3_score", "biowin4_score", "matched_fragments", "structure_alerts", "design_hypotheses"],
    },
    {
        "key": "ENVIRODESIGN_PATHWAY_RETENTION",
        "name": "EnviroDesign transformation-pathway retention",
        "domain": "parent-product motif retention with matrix and provenance",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native_manual_import",
        "status": "working_manual_import",
        "tiers": [1, 2, 3, 4],
        "outputs": ["mcs_retention", "retained_fragments", "retained_alerts", "pathway_hypotheses"],
    },
    {
        "key": "BIOTRANSFORMER_ENVMICRO",
        "name": "BioTransformer environmental microbial pathway prediction",
        "domain": "predicted soil/water microbial transformation products and reaction network",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "remote_api_adapter",
        "status": "development_evaluation_licence_gated",
        "tiers": [0, 1, 2, 3, 4],
        "outputs": ["predicted_products", "pathway_nodes", "reaction_edges", "provider_provenance"],
    },
    {
        "key": "ENVIPATH_ENVMICRO",
        "name": "enviPath curated-pathway search and rule-based pathway prediction",
        "domain": "curated real-world and predicted microbial transformation products and reaction network",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "remote_api_adapter",
        "status": "development_evaluation_licence_gated",
        "tiers": [0, 1, 2, 3, 4],
        "outputs": ["curated_or_predicted_products", "pathway_nodes", "reaction_edges", "provider_provenance"],
    },
    {
        "key": "ENVIRODESIGN_CANDIDATE_COMPARISON",
        "name": "EnviroDesign candidate comparison",
        "domain": "counterfactual safer-by-design comparison",
        "regions": ["EU", "UK", "US", "CH", "AU", "CA", "NZ"],
        "groups": CONTAMINANT_GROUPS,
        "implementation": "native",
        "status": "working_user_supplied_candidates",
        "tiers": [0, 1, 2, 3, 4],
        "outputs": ["score_deltas", "descriptor_tradeoffs", "protected_substructure_check", "candidate_comparison"],
    },
]


def _model(key: str) -> dict[str, Any]:
    return next(m for m in MODELS if m["key"] == key)


def _regulatory_programme(jurisdiction: str, group: str, scenario: str) -> dict[str, str]:
    """Describe the jurisdictional route without claiming an official run occurred."""
    if jurisdiction == "US":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "US_FIFRA",
                "name": "US FIFRA pesticide exposure pathway",
                "scope": "EPA pesticide-use scenarios and water-exposure model workflows",
            }
        if scenario in {"industrial_effluent", "laboratory_use"} and group == "industrial_organic":
            return {
                "key": "US_TSCA_INDUSTRIAL",
                "name": "US TSCA industrial and occupational pathway",
                "scope": "industrial releases, worker tasks and downstream environmental exposure",
            }
        if scenario == "household_use":
            return {
                "key": "US_TSCA_CONSUMER",
                "name": "US TSCA consumer exposure pathway",
                "scope": "consumer product/article use and associated environmental releases",
            }
        if scenario == "product_disposal":
            return {
                "key": "US_TSCA_WASTE",
                "name": "US TSCA waste-stage pathway",
                "scope": "landfill, incineration, treatment and general-population release pathways",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "US_FDA_HUMAN_DRUG",
                "name": "US human-pharmaceutical environmental pathway",
                "scope": "use-to-environment screening; FDA-specific requirements require separate review",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "US_FDA_CVM",
                "name": "US veterinary-pharmaceutical environmental pathway",
                "scope": "animal-use environmental release; FDA/CVM-specific requirements require separate review",
            }
        return {
            "key": "US_TSCA_ENVIRONMENTAL",
            "name": "US environmental exposure pathway",
            "scope": "native screening plus applicable managed EPA workflows",
        }

    if jurisdiction == "AU":
        # AICIS regulates industrial chemicals in Australia (Industrial
        # Chemicals Act 2019) and does not operate a distinct proprietary
        # exposure model the way EU FOCUS or US EPA do -- its published
        # Environment Tier II assessments apply the same core PEC/PNEC
        # risk-quotient method with EU-TGD-style assessment-factor banding
        # (1000/500/100/50 depending on the trophic-level coverage of the
        # available toxicity data), reviewer-selected the same way
        # app/reach/pnec.py already requires. This is therefore native
        # screening plus that reviewer-supplied assessment factor, not a
        # managed hand-off to an AICIS-specific tool -- no such tool was
        # found on research. Pesticides and veterinary medicines in
        # Australia are regulated by the APVMA, not AICIS -- that pathway's
        # own environmental fate methodology has not been researched, so it
        # is named as an explicit gap here rather than silently mislabelled
        # as an AICIS assessment.
        if group == "pesticide" or scenario == "agricultural_spray":
            # PARTIALLY mapped (2026-09-18): APVMA, not AICIS, regulates
            # pesticides in Australia. Its terrestrial-vertebrates TER
            # methodology and its aquatic risk-quotient trigger are now
            # confirmed and implemented (ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN,
            # au_apvma.py) -- but APVMA's spray-drift, runoff, bee,
            # soil-organism and non-target-plant methodology is still
            # unresearched. This is genuinely partial coverage, not full
            # APVMA compliance.
            return {
                "key": "AU_APVMA_PARTIAL",
                "name": "Australian APVMA pesticide pathway (partially mapped)",
                "scope": "APVMA, not AICIS, regulates pesticides in Australia. Confirmed and implemented: terrestrial-vertebrates dietary TER (EFSA-2009-aligned, same triggers as the EU screen) and the aquatic RQ trigger (0.1 acute / 1.0 chronic). Not yet researched: spray drift, runoff, bees, soil organisms, non-target plants -- treat those as an explicit coverage gap",
            }
        if group == "veterinary_pharmaceutical":
            # PARTIALLY mapped (2026-09-18): APVMA also regulates veterinary
            # medicines in Australia, under the SAME "Environment (Part 7)"
            # data-guideline umbrella as pesticides (confirmed live -- the
            # agricultural- and veterinary-data-guideline pages mirror each
            # other) and the same general PEC/PNEC risk-quotient process
            # (hazard -> exposure -> risk characterisation, RQ < 1
            # acceptable). APVMA's aquatic RQ trigger (0.1 acute / 1.0
            # chronic, au_apvma.py) is offered on that basis. The dietary
            # bird/mammal TER screen (ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN) is
            # NOT offered here: it models spray-residue-on-food-item
            # exposure specific to plant-protection products, and veterinary
            # medicines reach the terrestrial environment through a
            # different route (manure/excreta to soil) that has not been
            # verified to use the same model.
            return {
                "key": "AU_APVMA_VETERINARY_PARTIAL",
                "name": "Australian APVMA veterinary-medicine pathway (partially mapped)",
                "scope": "APVMA regulates veterinary medicines in Australia under the same Environment (Part 7) framework and general PEC/PNEC risk-quotient process as pesticides. Confirmed and implemented: the aquatic RQ trigger (0.1 acute / 1.0 chronic). NOT offered: the dietary bird/mammal TER screen, which models spray-residue exposure specific to pesticides, not manure/excreta-route veterinary exposure -- that pathway is still an explicit coverage gap",
            }
        if group == "human_pharmaceutical":
            # CONFIRMED (2026-09-18, live search, current through the
            # 2025-2026 TGA guideline-adoption consultation): the TGA has no
            # environmental risk assessment requirement for human medicines
            # at all. This is not "not yet researched" -- there is
            # genuinely no local ERA methodology to map. Multinational
            # pharma operating in Australia commonly uses EU/EMA-style
            # assessment as a de facto international reference in this
            # situation, which FateIntel's existing EU pharmaceutical
            # pathway already substantially supports.
            return {
                "key": "AU_TGA_NO_ERA_REQUIREMENT",
                "name": "Australian TGA human-medicines pathway (no ERA requirement)",
                "scope": "TGA does not require an environmental risk assessment for human medicines in Australia -- confirmed, not a research gap. Consider FateIntel's EU/EMA-aligned pharmaceutical pathway as a voluntary international reference where a customer wants one anyway",
            }
        return {
            "key": "AU_AICIS_INDUSTRIAL",
            "name": "Australian AICIS industrial-chemical environmental risk pathway",
            "scope": "PEC/PNEC risk-quotient assessment against AICIS's own published assessment-factor banding; AICIS-specific submission and notification requirements need separate review",
        }

    if jurisdiction == "CA":
        # ECCC/CEPA (New Substances Notification) has its own published
        # three-factor PNEC assessment-factor method (FES x FSV x FMOA,
        # Okonski et al. 2020) implemented in canada_pnec.py -- again a
        # PEC/PNEC risk-quotient method, not a distinct proprietary exposure
        # model.
        #
        # PARTIALLY mapped (2026-09-18): PMRA, not ECCC, regulates
        # pesticides in Canada, under the Pest Control Products Act. PMRA's
        # own framework guidance (12 April 2024) confirms a general
        # RQ = exposure/toxicity vs. a default Level of Concern (LOC) of 1
        # for most receptor groups, with "a few validated exceptions" --
        # implemented in pmra_pesticides.py. One exception is confirmed with
        # citable numbers: honey bees, LOC 0.4 acute / 1.0 chronic, from a
        # guidance document PMRA co-authored with US EPA and California DPR
        # (a genuine tri-agency framework, not PMRA deferring to EPA's own
        # numbers). Other receptor-specific PMRA exceptions were not found
        # with citable values this session and are not guessed at -- see
        # pmra_pesticides.py's own docstring. APVMA-style spray-drift,
        # runoff, soil-organism and non-target-plant methodology is not
        # covered here either.
        if group == "pesticide" or scenario == "agricultural_spray":
            return {
                "key": "CA_PMRA_PARTIAL",
                "name": "Canadian PMRA pesticide pathway (partially mapped)",
                "scope": "PMRA, not ECCC, regulates pesticides in Canada. Confirmed and implemented: the general RQ vs. LOC=1 framework and the confirmed bee exception (LOC 0.4 acute / 1.0 chronic, tri-agency PMRA/EPA/CDPR guidance). Not yet researched: spray drift, runoff, soil organisms, non-target plants, and any other receptor-specific LOC exceptions beyond bees -- treat those as an explicit coverage gap",
            }
        if group in {"human_pharmaceutical", "veterinary_pharmaceutical"}:
            # PARTIALLY mapped (2026-09-18): confirmed live that, as of this
            # session, a NEW pharmaceutical active ingredient not already on
            # Canada's Domestic Substances List (DSL) is reviewed under
            # CEPA's New Substances Notification Regulations -- the SAME
            # ECCC/CEPA pathway already implemented above for industrial
            # chemicals (Health Canada's Environmental Assessment Unit
            # assesses it; Environment and Climate Change Canada issues the
            # correspondence). A dedicated Food and Drugs Act environmental
            # risk-assessment regime was enacted in law in June 2023 but its
            # implementing regulations are still under development (Canada
            # Gazette Part I published Dec 2024, comment period closed
            # March 2025) -- not yet in force. Most active pharmaceutical
            # ingredients already on the DSL from prior use trigger no
            # notification at all under this pathway, which is why this is
            # named a conditional/partial pathway, not full coverage.
            return {
                "key": "CA_HEALTH_CANADA_PARTIAL",
                "name": "Canadian human/veterinary medicines pathway (partially mapped, DSL-trigger-conditional)",
                "scope": "A pharmaceutical active ingredient not already on Canada's Domestic Substances List is assessed via the same ECCC/CEPA New Substances Notification pathway as industrial chemicals (canada_pnec.py); DSL-listed ingredients trigger no assessment under this route. A dedicated Food and Drugs Act ERA regime is enacted but its regulations are not yet in force -- revisit when they are",
            }
        return {
            "key": "CA_ECCC_CEPA_INDUSTRIAL",
            "name": "Canadian ECCC/CEPA industrial-chemical environmental risk pathway",
            "scope": "PEC/PNEC risk-quotient assessment using ECCC's own FES x FSV x FMOA assessment-factor method (Okonski et al., 2020); CEPA New Substances Notification submission requirements need separate review",
        }

    if jurisdiction == "NZ":
        # NZ EPA (HSNO Act 1996) is structurally different from AU/CA: it
        # does not split industrial chemicals and pesticides across two
        # regulators -- both sit with the same EPA under the same Act, read
        # in full this session. Its risk-characterisation method is also
        # different in kind from a PEC/PNEC-with-assessment-factor
        # derivation: RQ = PEC / toxicity value is compared directly against
        # a fixed, receptor-specific Level of Concern (LOC) from the
        # guidance's own Table 9 -- implemented in nz_levels_of_concern.py,
        # not folded into app/reach/pnec.py's PNEC-derivation shape because
        # it genuinely isn't one. Human medicines are the one group HSNO
        # itself excludes (Ministry of Health instead) -- named as an
        # explicit gap. Veterinary medicines/agricultural compounds may sit
        # under the separate ACVM Act 1997 -- not confirmed, so treated the
        # same way (gap, not asserted coverage) rather than guessed at.
        if group == "human_pharmaceutical":
            return {
                "key": "NZ_MOH_NOT_MAPPED",
                "name": "New Zealand Ministry of Health medicines pathway (not yet mapped)",
                "scope": "Human medicines are explicitly excluded from the HSNO Act and regulated by the Ministry of Health instead; that pathway's environmental fate methodology has not been researched -- treat as an explicit coverage gap, not a supported pathway",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "NZ_ACVM_NOT_CONFIRMED",
                "name": "New Zealand veterinary-medicines pathway (regulator not confirmed)",
                "scope": "The guidance references a separate Agricultural Compounds and Veterinary Medicines Act 1997; whether HSNO or ACVM governs environmental risk for this group has not been confirmed -- treat as an explicit coverage gap, not a supported pathway",
            }
        return {
            "key": "NZ_EPA_HSNO",
            "name": "New Zealand EPA HSNO environmental risk pathway",
            "scope": "Risk quotient (RQ = PEC / toxicity value) compared against NZ EPA's own fixed Level of Concern per receptor and exposure type (Table 9), with a graded risk-level banding (Table 10) rather than a single RQ>1 trigger; covers industrial chemicals and agrichemicals/pesticides alike under one HSNO pathway",
        }

    # Below here used to be an unguarded tail that any jurisdiction not matched above (US/AU/CA/NZ) fell into --
    # meaning UK and Switzerland silently received "EU REACH" wording even though neither is in EU REACH. Each
    # jurisdiction now has its own explicit branch, using the regime names FRAMEWORKS already declares for it
    # rather than EU's. The native screen suite (FOCUS/SimpleTreat/etc.) stays shared across EU/UK/CH -- only the
    # regulatory-programme label and scope text differ.
    if jurisdiction == "EU":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "EU_PPP_FOCUS",
                "name": "EU plant-protection product exposure pathway",
                "scope": "FOCUS groundwater and surface-water scenario workflows",
            }
        if scenario in {"industrial_effluent", "laboratory_use"}:
            return {
                "key": "EU_REACH_INDUSTRIAL",
                "name": "EU REACH industrial and professional-use pathway",
                "scope": "environmental releases; worker exposure requires a dedicated REACH worker assessment",
            }
        if scenario == "household_use":
            return {
                "key": "EU_REACH_CONSUMER",
                "name": "EU REACH consumer lifecycle pathway",
                "scope": "consumer-use environmental releases; direct human exposure is a separate assessment domain",
            }
        if scenario == "product_disposal":
            return {
                "key": "EU_REACH_WASTE",
                "name": "EU REACH waste-stage pathway",
                "scope": "service-life and waste-stage environmental releases and fate",
            }
        return {
            "key": "EU_ENVIRONMENTAL",
            "name": "EU environmental exposure pathway",
            "scope": "native screening plus applicable managed EU model workflows",
        }

    # UK REACH is the UK's own retained-EU-law chemicals regime (its own dossiers and timelines, separate from EU
    # REACH since Brexit); "GB Plant protection products" and "GB Biocides" are FRAMEWORKS's own declared UK
    # packs, reused here rather than a more specific instrument name that has not been verified.
    if jurisdiction == "UK":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "UK_PPP_FOCUS",
                "name": "UK plant-protection product exposure pathway",
                "scope": "the GB Plant Protection Products regime; FOCUS groundwater and surface-water scenario workflows remain the shared technical basis",
            }
        if scenario in {"industrial_effluent", "laboratory_use"}:
            return {
                "key": "UK_REACH_INDUSTRIAL",
                "name": "UK REACH industrial and professional-use pathway",
                "scope": "environmental releases under UK REACH; worker exposure requires a dedicated UK REACH worker assessment",
            }
        if scenario == "household_use":
            return {
                "key": "UK_REACH_CONSUMER",
                "name": "UK REACH consumer lifecycle pathway",
                "scope": "consumer-use environmental releases; direct human exposure is a separate assessment domain",
            }
        if scenario == "product_disposal":
            return {
                "key": "UK_REACH_WASTE",
                "name": "UK REACH waste-stage pathway",
                "scope": "service-life and waste-stage environmental releases and fate",
            }
        return {
            "key": "UK_ENVIRONMENTAL",
            "name": "UK environmental exposure pathway",
            "scope": "native screening plus applicable managed UK REACH / FOCUS workflows",
        }

    # Switzerland is not an EU/EEA member and is not part of EU REACH: FRAMEWORKS's own declared CH packs
    # (ChemO, ORRChem, Plant protection products) are its actual chemicals and plant-protection regime, not
    # REACH -- reused here rather than a more specific instrument name that has not been verified.
    if jurisdiction == "CH":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "CH_PPP",
                "name": "Swiss plant-protection product exposure pathway",
                "scope": "the Swiss Plant Protection Products regime; FOCUS groundwater and surface-water scenario workflows remain the shared technical basis",
            }
        if scenario in {"industrial_effluent", "laboratory_use"}:
            return {
                "key": "CH_CHEMO_INDUSTRIAL",
                "name": "Swiss ChemO/ORRChem industrial and professional-use pathway",
                "scope": "environmental releases under the Swiss Chemicals Ordinance (ChemO) and Ordinance on Reduction of Risks relating to Chemical products (ORRChem); worker exposure requires a dedicated Swiss worker assessment",
            }
        if scenario == "household_use":
            return {
                "key": "CH_CHEMO_CONSUMER",
                "name": "Swiss ChemO consumer lifecycle pathway",
                "scope": "consumer-use environmental releases; direct human exposure is a separate assessment domain",
            }
        if scenario == "product_disposal":
            return {
                "key": "CH_CHEMO_WASTE",
                "name": "Swiss ChemO waste-stage pathway",
                "scope": "service-life and waste-stage environmental releases and fate",
            }
        return {
            "key": "CH_ENVIRONMENTAL",
            "name": "Swiss environmental exposure pathway",
            "scope": "native screening plus applicable managed Swiss ChemO / FOCUS workflows",
        }

    # Researched 2026-09-22 (REGION_RESEARCH_JP_CN_KR_IN.md). None of these four countries' quantitative
    # risk-assessment methods were read to primary-document depth this session, so unlike AU/CA/NZ above, every
    # branch below is an honest "regime and agency named, method not yet mapped" result -- never a calculated
    # PEC/PNEC. Japan's pesticide PEC criterion is the one exception with a named mechanism, not just an agency.
    if jurisdiction == "JP":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "JP_ACRA_PEC",
                "name": "Japan Agricultural Chemicals Regulation Act pathway",
                "scope": "Registration is refused if the Predicted Environmental Concentration (PEC) of the active "
                         "ingredient in public waters exceeds the Ministry of the Environment's standard, alongside "
                         "Food Sanitation Act residue limits; the PEC calculation method itself has not been mapped "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "JP_MHLW_PHARMA_ERA",
                "name": "Japan MHLW pharmaceutical environmental risk assessment pathway",
                "scope": "MHLW's 2016 guidance assesses a PEC/PNEC ratio against a 0.01 microgram/L action limit; "
                         "confirmed only via secondary academic citation of the guidance, not the MHLW notification "
                         "itself, and not encoded as a calculable method (EXTERNAL MODEL REQUIRED).",
            }
        # 2026-09-22 follow-up research: fetched and read a NITE (Chemical Management Center) technical
        # presentation, "Chemical Risk Assessment under the Chemical Substances Control Law in Japan and
        # comparison with REACH" (SETAC World Congress, Berlin, 23 May 2012), the closest primary-adjacent source
        # located for the actual CSCL method's shape. It describes a real, tiered, two-stage process: government
        # (NITE/CERI, not industry) screens ALL existing substances by cross-tabulating a Hazard Class (1-4, based
        # on repeated-dose toxicity, reproductive toxicity, mutagenicity, carcinogenicity and ecotoxicity data, with
        # class 2 applied by default if no data exists) against an Exposure Class (1-5, based on total estimated
        # national emissions in tonnes/year) in a priority matrix; substances scoring "High" become Priority
        # Assessment Chemical Substances (PACs), which then get a real Risk Assessment (PEC, modelled from notified
        # production/use volume and an emission-factor table, compared against DNEL/PNEC). Production/import volume
        # is also tiered (Tier 1: 1-10 t/y, Tier 2: 10-100 t/y, Tier 3: 100-1,000 t/y, Tier 4: >=1,000 t/y),
        # determining how much hazard/exposure data is required. This is real structure, not a calculable method:
        # the exact 2012 numeric class boundaries may have been superseded by a 2022 CSCL PAC screening/risk-
        # assessment revision (found in search results but not read), so nothing here is asserted as current.
        return {
            "key": "JP_CSCL_PARTIAL",
            "name": "Japan CSCL pathway (structure confirmed, current numeric criteria not verified)",
            "scope": "The Chemical Substances Control Law (METI/MHLW/MoE, government-run, not industry-run) screens "
                     "existing substances via a Hazard Class x Exposure Class priority matrix (exposure class set "
                     "by total national emissions, tiered by production/import volume); substances prioritised "
                     "'High' undergo Risk Assessment comparing a modelled PEC against DNEL/PNEC. Confirmed via a "
                     "2012 NITE technical presentation; current (post-2022-revision) numeric thresholds were not "
                     "verified, so no calculation is offered (EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "CN":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "CN_MARA_PESTICIDE_NOT_MAPPED",
                "name": "Chinese pesticide registration pathway (quantitative method not yet mapped)",
                "scope": "Pesticide registration sits with the Ministry of Agriculture and Rural Affairs, which the "
                         "Soil Pollution Prevention and Control Law itself requires to assess pesticide/fertiliser "
                         "impact on the soil environment; the quantitative method has not been mapped "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        if group in {"human_pharmaceutical", "veterinary_pharmaceutical"}:
            # 2026-09-22 follow-up research: no pre-market pharmaceutical ERA guideline was found under the
            # Ministry of Ecology and Environment or the NMPA. What IS confirmed, and real, is a different kind of
            # control: named, category-specific national discharge standards for pharmaceutical-manufacturing
            # wastewater (MEE's own English pages, e.g. GB 21905-2008 extractive pharmaceutical industry,
            # GB 21906-2008 traditional Chinese medicine category). That is a manufacturing-effluent limit, not a
            # PEC/PNEC risk assessment, and is reported as such rather than conflating the two. Kept for both
            # human and veterinary pharmaceuticals because the standards are keyed to a manufacturing category
            # (fermentation, chemical synthesis, etc.), not to a human/veterinary regulatory review split -- unlike
            # the Korea/India pharma branches below, which are specifically about a human-drug regulator's own
            # review requirement and are NOT extended to veterinary_pharmaceutical for exactly that reason.
            return {
                "key": "CN_PHARMA_DISCHARGE_STANDARDS",
                "name": "China pharmaceutical-manufacturing discharge standards pathway",
                "scope": "No pre-market environmental risk assessment guideline for pharmaceuticals was found. "
                         "Manufacturing wastewater is instead controlled by category-specific national discharge "
                         "standards under the Ministry of Ecology and Environment (e.g. GB 21905-2008 extractive "
                         "pharmaceutical industry, GB 21906-2008 traditional Chinese medicine category) -- a "
                         "manufacturing-effluent limit, not a PEC/PNEC risk assessment (EXTERNAL MODEL REQUIRED).",
            }
        # 2026-09-22 follow-up research: found a real, named guideline -- the Technical Framework Guideline for
        # Environmental Risk Assessment of Chemical Substances (Trial), jointly issued by MEE and the National
        # Health Commission on 3 September 2019 -- covering PEC/PNEC-style risk characterisation via hazard
        # identification, dose-response assessment, exposure assessment and risk characterisation, with aquatic
        # ecotoxicity testing across three trophic levels (algae, fish, daphnia). Some secondary sources also state
        # specific PNEC uncertainty-factor values (100 for acute-only data, 10 additional for chronic), but that
        # attribution could not be confirmed as specific to this guideline rather than a generic international
        # convention appearing in the same search results -- so no numeric factor is asserted here.
        return {
            "key": "CN_MEE_PARTIAL",
            "name": "China REACH (MEE new-chemical registration) pathway (structure confirmed, numeric factors not verified)",
            "scope": "New chemical substances are registered with the Ministry of Ecology and Environment under "
                     "MEE Order No. 12 (revised Measures due 15 August 2026). A named environmental risk-assessment "
                     "guideline exists (MEE/NHC, 3 September 2019): a four-step PEC/PNEC-style method with "
                     "three-trophic-level aquatic ecotoxicity testing; its specific uncertainty-factor values were "
                     "not confirmed this session, so no calculation is offered (EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "KR":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "KR_AGROCHEM_NOT_MAPPED",
                "name": "South Korean Agrochemicals Control Act pathway (quantitative method not yet mapped)",
                "scope": "Pesticides are registered by the Rural Development Administration (RDA) under the "
                         "Agrochemicals Control Act, which falls under the Ministry of Agriculture, Food and Rural "
                         "Affairs' statutory authority; the quantitative risk-assessment method has not been "
                         "mapped (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            # 2026-09-22 follow-up research: multiple secondary sources report that MFDS drug-approval submissions
            # (New Drug Applications and biologics in particular) must include "information on potential
            # environmental risks" as a supporting document, aligned with ICH guidelines -- a real requirement, not
            # nothing. No named MFDS guideline document or quantitative PEC/PNEC method was located this session.
            # MFDS is the human-medicines regulator; veterinary medicines sit with a different body in Korea (not
            # researched this session), so this is deliberately not extended to veterinary_pharmaceutical.
            return {
                "key": "KR_MFDS_PHARMA_NOT_MAPPED",
                "name": "South Korea MFDS pharmaceutical environmental-information pathway (not yet mapped)",
                "scope": "MFDS drug-approval submissions are reported to require environmental-risk information as "
                         "a supporting document, but no named guideline document or quantitative method was "
                         "located this session (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "KR_KREACH_NOT_MAPPED",
            "name": "K-REACH pathway (quantitative method not yet mapped)",
            "scope": "New chemical substances are registered with the Ministry of Environment, evaluated by NIER, "
                     "under the Act on the Registration and Evaluation of Chemical Substances; the quantitative "
                     "risk-assessment method has not been mapped (EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "IN":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "IN_CIBRC_NOT_MAPPED",
                "name": "India Insecticides Act / CIBRC pathway (quantitative method not yet mapped)",
                "scope": "Pesticides are registered centrally by the Central Insecticides Board & Registration "
                         "Committee under the Insecticides Act, 1968; the quantitative environmental-risk method "
                         "has not been mapped (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            # 2026-09-22 follow-up research: a peer-reviewed comparative review (Therapeutic Innovation & Regulatory
            # Science, EMA/FDA/CDSCO guidelines) states plainly that CDSCO has no environmental risk assessment
            # requirement and the Drugs and Cosmetics Act does not address environmental risk -- a confirmed
            # absence, not a research gap, the same shape of finding as Australia's TGA. Summarised from the
            # article's abstract/search snippet only; the article itself is paywalled and was not fetched. CDSCO is
            # the human-medicines regulator; veterinary medicines were not researched this session, so this is
            # deliberately not extended to veterinary_pharmaceutical.
            return {
                "key": "IN_CDSCO_NO_ERA_REQUIREMENT",
                "name": "India CDSCO pathway (no environmental risk assessment requirement)",
                "scope": "CDSCO has no environmental risk assessment requirement for pharmaceuticals; the Drugs and "
                         "Cosmetics Act does not address environmental risk -- confirmed, not a research gap. "
                         "Manufacturing effluent instead falls under the general MoEFCC/CPCB pollution-control "
                         "rules named above (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "IN_MSIHC_NOT_MAPPED",
            "name": "India MSIHC hazardous-chemicals pathway (quantitative method not yet mapped)",
            "scope": "Hazardous industrial chemicals are regulated under the Manufacture, Storage and Import of "
                     "Hazardous Chemicals Rules, 1989 (CPCB/MoEFCC); a comprehensive chemicals-registration regime "
                     "('India REACH', the Chemicals Management and Safety Rules) remains a draft, not enacted, and "
                     "is not named as a supported pathway (EXTERNAL MODEL REQUIRED).",
        }

    # Researched 2026-09-23 (Norway/Gulf-states research pass). Norway is the one new jurisdiction this pass
    # confirmed shares EU REACH's actual substantive regime (via EEA incorporation), so its non-pesticide
    # branches reuse the EU pathway's own scope wording rather than a separately-derived one -- but its own
    # jurisdiction-specific key, since it is still a distinct national dossier/timeline, matching how UK REACH
    # already gets its own key despite originating from the same regulation.
    if jurisdiction == "NO":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "NO_PPP_FOCUS_NORTHERN_ZONE",
                "name": "Norway plant-protection product exposure pathway (Northern Zone, confirmed deviations)",
                "scope": "Mattilsynet (Norwegian Food Safety Authority) administers Regulation (EC) 1107/2009 in the "
                         "EU's Northern Zone. FOCUS groundwater and surface-water scenario workflows are the shared "
                         "technical basis, with two confirmed Norway-specific deviations (Mattilsynet's own national-"
                         "requirements page): FOCUS MACRO 5.5.4 is mandated for groundwater leaching, and a six-"
                         "scenario (not the standard nine-scenario) surface-water selection applies, dropping D5, "
                         "D6 and R3.",
            }
        if scenario in {"industrial_effluent", "laboratory_use"}:
            return {
                "key": "NO_REACH_INDUSTRIAL",
                "name": "Norway REACH industrial and professional-use pathway (EEA-incorporated EU REACH)",
                "scope": "environmental releases under REACH as applied in Norway via the EEA Agreement "
                         "(Miljodirektoratet); worker exposure requires a dedicated REACH worker assessment. EEA "
                         "incorporation runs through Joint Committee decisions, so newly adopted EU amendments can "
                         "lag before taking effect in Norway.",
            }
        if scenario == "household_use":
            return {
                "key": "NO_REACH_CONSUMER",
                "name": "Norway REACH consumer lifecycle pathway (EEA-incorporated EU REACH)",
                "scope": "consumer-use environmental releases; direct human exposure is a separate assessment domain",
            }
        if scenario == "product_disposal":
            return {
                "key": "NO_REACH_WASTE",
                "name": "Norway REACH waste-stage pathway (EEA-incorporated EU REACH)",
                "scope": "service-life and waste-stage environmental releases and fate",
            }
        if group in {"human_pharmaceutical", "veterinary_pharmaceutical"}:
            return {
                "key": "NO_DMP_PHARMA_EMA_ALIGNED",
                "name": "Norway pharmaceutical environmental risk pathway (EMA-aligned)",
                "scope": "Direktoratet for medisinske produkter (DMP) participates in the EU/EEA medicines network "
                         "and applies the EMA two-phase environmental risk assessment guideline (Phase I exposure "
                         "estimate against the 0.01 microgram/L surface-water action limit; Phase II fate-and-"
                         "effects testing if exceeded) as-is; no Norway-specific numeric deviation was found. "
                         "Veterinary medicines additionally sit under Regulation (EU) 2019/6, extended to Norway by "
                         "EEA Joint Committee Decision No. 371/2021.",
            }
        return {
            "key": "NO_ENVIRONMENTAL",
            "name": "Norway environmental exposure pathway",
            "scope": "native screening plus applicable managed EEA-incorporated REACH / FOCUS workflows",
        }

    # Researched 2026-09-23. UAE and Saudi Arabia share one real, confirmed, GCC-wide instrument for pesticides
    # (the Pesticides Act of the Cooperation Council for the Arab States of the Gulf, ratified as each state's own
    # domestic law) but otherwise have distinct national regulators and confirmed findings -- kept as separate
    # jurisdiction branches rather than one merged "GCC" pathway, since a merged pathway would overstate the
    # genuinely confirmed harmonisation (only pesticide registration's environmental-harm check is GCC-wide; the
    # Act itself specifies no quantitative method in either country).
    if jurisdiction == "AE":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "AE_GCC_PESTICIDES_ACT_NOT_MAPPED",
                "name": "UAE pesticides pathway (GCC Pesticides Act, quantitative method not yet mapped)",
                "scope": "Pesticide registration was recently transferred from MOCCAE to the Emirates Drug "
                         "Establishment (EDE). The GCC-wide Pesticides Act (ratified as UAE domestic law, 2007) "
                         "requires registration to confirm a pesticide is not harmful to the environment (Article "
                         "2), but delegates the actual method to national executive regulations, which were not "
                         "located -- the Act itself specifies no quantitative method (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "AE_EDE_PHARMA_NOT_CONFIRMED",
                "name": "UAE human-pharmaceutical pathway (requirement not confirmed)",
                "scope": "The Emirates Drug Establishment (EDE, est. under Federal Decree-Law No. 38 of 2024) is "
                         "the registering authority. A GCC-wide 'Module 1' dossier structure is referenced "
                         "regionally, and Saudi Arabia's own confirmed Module 1.5 Environmental Risk Assessment "
                         "requirement plausibly extends here, but this was not confirmed on a UAE primary source "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "AE_EDE_VETERINARY_NOT_CONFIRMED",
                "name": "UAE veterinary-pharmaceutical pathway (requirement not confirmed)",
                "scope": "Federal Decree-Law No. 21 of 2025 on veterinary medical products was enacted, with EDE as "
                         "the licensing authority. Secondary reporting describes an environmental-disposal element, "
                         "but the primary legislative text was not read and no quantitative method was confirmed "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "AE_CHEMICALS_NOT_MAPPED",
            "name": "UAE chemicals pathway (no REACH-equivalent regime confirmed)",
            "scope": "No REACH-equivalent chemicals registration regime with a PEC/PNEC-style environmental risk "
                     "assessment was confirmed for the UAE -- an open research gap, not a confirmed absence "
                     "(EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "SA":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "SA_GCC_PESTICIDES_ACT_NOT_MAPPED",
                "name": "Saudi Arabia pesticides pathway (GCC Pesticides Act, quantitative method not yet mapped)",
                "scope": "The Ministry of Environment, Water and Agriculture (MEWA) administers the GCC-wide "
                         "Pesticides Act (ratified as Saudi domestic law, 2006), which requires registration to "
                         "confirm a pesticide is not harmful to the environment (Article 2) but specifies no "
                         "quantitative method (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "SA_SFDA_PHARMA_PARTIAL",
                "name": "Saudi Arabia human-pharmaceutical environmental risk pathway (requirement confirmed, method not specified)",
                "scope": "The SFDA's own 'Data Requirements for Human Drugs Submission' (DS-REQ-002-V4.0), read in "
                         "full, contains Module 1 Section 1.5 'Environmental Risk Assessment', requiring an "
                         "evaluation of the risk to the environment from use, storage and disposal -- a real, "
                         "confirmed, primary-sourced requirement modelled on the EU CTD structure. The document "
                         "does not itself specify a quantitative PEC/PNEC method (EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "SA_SFDA_VETERINARY_NOT_CONFIRMED",
                "name": "Saudi Arabia veterinary-pharmaceutical pathway (ERA applicability not confirmed)",
                "scope": "SFDA's Drug Sector regulates veterinary medicines through the same Saudi Drug "
                         "Registration (SDR) system as human medicines, but no veterinary-specific data-"
                         "requirements guideline analogous to DS-REQ-002 was located, so whether the confirmed "
                         "human Section 1.5 Environmental Risk Assessment requirement extends to veterinary "
                         "dossiers is not confirmed (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "SA_CHEMICALS_NOT_MAPPED",
            "name": "Saudi Arabia chemicals pathway (no REACH-equivalent regime confirmed)",
            "scope": "SASO/SABER governs import conformity, not an environmental risk method. Secondary sources "
                     "claim REACH-like adoption but no primary government text describing a quantitative "
                     "environmental risk method was found -- an open research gap, not a confirmed absence "
                     "(EXTERNAL MODEL REQUIRED).",
        }

    # Researched 2026-09-23 (Brazil/Mexico research pass). Brazil's pesticide pathway is the strongest-sourced
    # finding of this whole country-expansion effort -- a real, hosted, primary IBAMA methodology PDF, not a
    # secondary description -- but its equations were not read to implementation depth this session, so it
    # stays "structure confirmed, not calculable" like Japan's CSCL rather than jumping straight to a
    # calculator the way the earthworm/bee work did after reading ECHA/EFSA primary text directly.
    if jurisdiction == "BR":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "BR_IBAMA_PPA_ARA_PARTIAL",
                "name": "Brazil IBAMA pesticide environmental risk pathway (structure confirmed, method not read to calculation depth)",
                "scope": "IBAMA administers the environmental leg of Brazil's tripartite pesticide-registration "
                         "system (MAPA: agronomic efficacy; ANVISA: human toxicology; IBAMA: environment). "
                         "IBAMA's own 2012 methodology document names a two-part method: PPA (Potencial de "
                         "Periculosidade Ambiental, a hazard baseline) and ARA (Avaliacao de Risco Ambiental, "
                         "which layers exposure and use conditions -- application method, dose, crop, climate "
                         "-- onto that baseline, with aquatic- and soil-organism scenarios). The document was "
                         "confirmed as a real, hosted, primary government methodology PDF, but its equations "
                         "were not read to calculation depth this session (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "BR_ANVISA_NO_ERA_REQUIREMENT",
                "name": "Brazil ANVISA human-medicines pathway (no environmental risk assessment requirement found)",
                "scope": "No ANVISA requirement for an environmental risk assessment as a condition of drug "
                         "approval was found. A peer-reviewed comparative-regulatory review states plainly that "
                         "'Brazil and other Latin American regulators have not integrated ERAs into drug "
                         "approval' -- a confirmed absence, but sourced secondarily, not from ANVISA's own text "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "BR_MAPA_VETERINARY_NOT_MAPPED",
                "name": "Brazil MAPA veterinary-medicines pathway (quantitative method not yet mapped)",
                "scope": "Veterinary products are registered by MAPA, not ANVISA. Normative Instruction 26/2009 "
                         "(antimicrobial veterinary products) explicitly names protecting 'animals, human "
                         "health, and the environment' as a regulatory concern, confirming intent, but no "
                         "calculation methodology was found in the text located (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "BR_INSQ_NOT_MAPPED",
            "name": "Brazil INSQ chemicals pathway (in force, quantitative method not yet finalised)",
            "scope": "Law 15.022/2024 created the INSQ (Inventario Nacional de Substancias Quimicas), a "
                     "REACH-like registration/risk-control regime led by the Ministry of Environment and "
                     "Climate Change (MMA) via CONASQ, in force since 15 November 2024. Its implementing "
                     "decree (dossier format, assessment method) was still in public consultation as of the "
                     "last search, with full dossiers due 15 November 2026 -- no quantitative method is "
                     "available yet. IBAMA's CTF/APP is a separate, longstanding registry of "
                     "potentially-polluting activities, not itself a PEC/PNEC method (EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "MX":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "MX_CICOPLAFEST_NOT_MAPPED",
                "name": "Mexico CICOPLAFEST pesticide pathway (confirmed absence of a quantitative risk step)",
                "scope": "Pesticides are reviewed by the CICOPLAFEST tripartite system (SSA/COFEPRIS health, "
                         "SEMARNAT environment, SADER agriculture); environmental-fate and ecotoxicity study "
                         "reports are required, but a peer-reviewed academic source states explicitly that "
                         "registration is based on verifying the submitted dossier is complete, not on running "
                         "a Mexico-specific risk assessment against local environmental conditions and uses -- "
                         "a confirmed absence of a quantitative method, sourced secondarily (a peer-reviewed "
                         "article, not a primary SEMARNAT/COFEPRIS statement) (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "MX_COFEPRIS_PHARMA_NOT_CONFIRMED",
                "name": "Mexico COFEPRIS human-medicines pathway (requirement not confirmed)",
                "scope": "COFEPRIS registers drugs via a CTD-format dossier. A single non-government "
                         "regulatory-consultancy source lists 'Environmental Risk Assessment (if applicable)' "
                         "as part of the submission package, with no method described -- this sourcing is weak "
                         "(not a primary COFEPRIS guideline/NOM) and is reported as unconfirmed, not asserted "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "MX_SENASICA_VETERINARY_NOT_CONFIRMED",
                "name": "Mexico SENASICA veterinary-medicines pathway (requirement not confirmed)",
                "scope": "Veterinary products are registered by SENASICA, a distinct agency from COFEPRIS. "
                         "Nothing was found confirming or denying an environmental-assessment requirement, and "
                         "this is deliberately not assumed to inherit the (also unconfirmed) human-pharma "
                         "pathway above -- a different agency entirely (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "MX_CHEMICALS_NOT_MAPPED",
            "name": "Mexico chemicals pathway (no REACH-equivalent regime found)",
            "scope": "No REACH-like chemicals registration regime with a PEC/PNEC-style environmental risk "
                     "assessment was found for general industrial chemicals -- COFEPRIS's 'registro sanitario' "
                     "is a sanitary/security control for toxic/hazardous substances and precursors, not a "
                     "risk-based environmental registration, and the LGPGIR (SEMARNAT/PROFEPA) governs "
                     "hazardous-waste management plans, not new-substance assessment. An open research gap, "
                     "not a confirmed absence (EXTERNAL MODEL REQUIRED).",
        }

    # Researched 2026-09-23 (Singapore/Taiwan/South Africa research pass, completing the country-expansion
    # list started with Norway/UAE/Saudi Arabia and Brazil/Mexico earlier this session).
    if jurisdiction == "SG":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "SG_SFA_PESTICIDE_NOT_MAPPED",
                "name": "Singapore SFA pesticide pathway (quantitative method not yet mapped)",
                "scope": "SFA (Singapore Food Agency) registers agricultural pesticides under the Control of "
                         "Plants Act, with NEA Pollution Control Department approval required first. No "
                         "quantitative environmental risk-assessment method was found (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "SG_HSA_NO_ERA_REQUIREMENT",
                "name": "Singapore HSA human-medicines pathway (no environmental risk assessment requirement found)",
                "scope": "HSA's own guidance-documents index (checked directly) lists no general environmental "
                         "risk assessment or ecotoxicology requirement for standard drug registration -- a "
                         "confirmed absence for standard products, from a primary source. A secondary source "
                         "claims a requirement specific to cell/tissue/gene therapy products, which could not "
                         "be confirmed against an HSA primary document and is not asserted here "
                         "(EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "SG_AVS_VETERINARY_NOT_CONFIRMED",
                "name": "Singapore AVS veterinary-medicines pathway (requirement not confirmed)",
                "scope": "AVS (Animal & Veterinary Service, under NParks) registers veterinary medicines. "
                         "Nothing was found confirming or denying an environmental-assessment requirement -- a "
                         "genuine absence-of-evidence finding from limited search results, not a confirmed "
                         "absence (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "SG_NEA_HS_NOT_MAPPED",
            "name": "Singapore NEA Hazardous Substances pathway (quantitative method not yet mapped)",
            "scope": "NEA runs a Hazardous Substances (HS) Licence system under the Environmental Protection "
                     "and Management Act, licensing a specific listed (Second Schedule) set of controlled "
                     "substances -- not a general new-chemical registration regime. A mandatory chemical "
                     "reporting framework for HS licence holders takes effect 1 January 2026 (GHS acute "
                     "toxicity Category 1/2, aquatic toxicity Category 1, or PBT criteria). No PEC/PNEC "
                     "methodology was found (EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "TW":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "TW_PESTICIDE_NOT_MAPPED",
                "name": "Taiwan pesticide pathway (quantitative method not yet mapped)",
                "scope": "Pesticides are registered by the Agriculture and Food Agency; the exact current "
                         "parent-ministry name was not confirmed (the Council of Agriculture was reorganised "
                         "into a Ministry of Agriculture in 2023). Registration requires environmental test "
                         "reports, but no Taiwan-specific PEC/PNEC document was located (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "TW_TFDA_PHARMA_NOT_CONFIRMED",
                "name": "Taiwan TFDA human-medicines pathway (requirement not confirmed)",
                "scope": "TFDA (Ministry of Health and Welfare) uses a CTD-format dossier. An environmental "
                         "risk assessment requirement was claimed only by generic regulatory-consulting "
                         "sources reading as standard CTD-module boilerplate, not confirmed against a TFDA "
                         "primary document (EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "TW_VETERINARY_NOT_MAPPED",
                "name": "Taiwan veterinary-medicines pathway (quantitative method not yet mapped)",
                "scope": "Veterinary medicines are regulated separately from human pharmaceuticals, under the "
                         "Veterinary Drugs Control Act with the agriculture-side Animal and Plant Health "
                         "Inspection Agency involved jointly with TFDA on some cross-cutting rules -- a "
                         "genuinely distinct agency/act from the human pathway. No environmental risk-"
                         "assessment requirement was found for it either (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "TW_TCCSCA_PARTIAL",
            "name": "Taiwan TCCSCA chemicals pathway (REACH-modelled structure confirmed, method not yet mapped)",
            "scope": "The Toxic and Concerned Chemical Substances Control Act (TCCSCA), administered by the "
                     "Chemicals Administration under the Ministry of Environment, is explicitly modelled on "
                     "EU REACH: new substances require registration 90 days pre-manufacture/import, with "
                     "Phase 1/Standard registration tiers for existing substances -- confirmed by reading the "
                     "primary law text directly. No PNEC/PEC calculation methodology was found; data "
                     "requirements are described, not a risk-quotient method (EXTERNAL MODEL REQUIRED).",
        }

    if jurisdiction == "ZA":
        if scenario == "agricultural_spray" or group == "pesticide":
            return {
                "key": "ZA_ACT36_NO_ERA_REQUIREMENT",
                "name": "South Africa Act 36 pesticide pathway (no mandatory environmental risk assessment)",
                "scope": "DALRRD (Registrar of Act 36) administers Act 36 of 1947 (Fertilisers, Farm Feeds, "
                         "Agricultural Remedies and Stock Remedies Act). A peer-reviewed 2026 literature "
                         "review states explicitly that Act 36 'does not include updated provisions to "
                         "address contemporary environmental risks, such as mandatory environmental risk "
                         "assessments' -- a confirmed absence, peer-reviewed sourced (EXTERNAL MODEL REQUIRED).",
            }
        if group == "human_pharmaceutical":
            return {
                "key": "ZA_SAHPRA_NO_ERA_REQUIREMENT",
                "name": "South Africa SAHPRA human-medicines pathway (no environmental risk assessment requirement)",
                "scope": "SAHPRA registers medicines under the Medicines and Related Substances Act. The same "
                         "peer-reviewed review states the Act 'does not address the entry of pharmaceuticals "
                         "into the environment' and that South Africa 'lacks binding environmental regulations "
                         "for pharmacovigilance' -- corroborated by SAHPRA's own ZACTD registration-guidance "
                         "table of contents, which shows no environment/Module 1.6 entry (EXTERNAL MODEL REQUIRED).",
            }
        if group == "veterinary_pharmaceutical":
            return {
                "key": "ZA_ACT36_VETERINARY_NOT_MAPPED",
                "name": "South Africa veterinary stock-remedies pathway (quantitative method not yet mapped)",
                "scope": "Food-producing-animal 'stock remedies' are NOT regulated by SAHPRA at all -- they "
                         "fall under the SAME Act 36 of 1947 as pesticides, administered by DALRRD (per its "
                         "own Data Requirements Guidelines for Stock Remedies). Veterinarian-administered "
                         "remedies are separately carved out under the Veterinary Act 16 of 1933. Whether "
                         "Act 36's confirmed pesticide ERA absence also applies here was not independently "
                         "verified this session (EXTERNAL MODEL REQUIRED).",
            }
        return {
            "key": "ZA_NEMA_CHEMICALS_NOT_MAPPED",
            "name": "South Africa chemicals pathway (no REACH-equivalent regime confirmed)",
            "scope": "No REACH-like chemicals registration/notification regime exists -- confirmed consistently "
                     "across multiple secondary sources. NEMA (National Environmental Management Act 107 of "
                     "1998) authorises the environment department to prohibit or control substances, but only "
                     "asbestos and PCBs are confirmed as substances actually controlled under NEMA subsidiary "
                     "regulations -- a genuine confirmed absence of a general regime (EXTERNAL MODEL REQUIRED).",
        }

    # A jurisdiction with no dedicated branch above never inherits another jurisdiction's regulatory-programme
    # text -- that was the exact bug this function had before EU/UK/CH each got an explicit guard.
    return {
        "key": "JURISDICTION_NOT_MAPPED",
        "name": f"{jurisdiction} environmental exposure pathway (not yet mapped)",
        "scope": "This jurisdiction's regulatory-programme routing has not been researched. Native screening may "
                 "still apply where the chemical group supports it; no jurisdiction-specific regime is named or claimed.",
    }


def build_assessment_plan(data: dict[str, Any]) -> dict[str, Any]:
    jurisdiction = data["jurisdiction"]
    group = data["contaminant_group"]
    scenario = data["scenario"]
    tier = int(data["tier"])

    selected: list[str] = []
    required: list[str] = [
        "resolved chemical identity",
        "quantity used or emitted",
        "release route and frequency",
        "measured/predicted property provenance",
    ]
    warnings: list[str] = []

    if group in NO_NATIVE_PATHWAY_GROUPS:
        framework = next(f for f in FRAMEWORKS if f["key"] == jurisdiction)
        if group == "radionuclide":
            reason = (
                "Radionuclide contamination is a dose-based radiological assessment, not a concentration-based "
                "chemical PEC/PNEC screen. FateIntel does not model it: route to the jurisdiction's specialist "
                "radiological framework (EXTERNAL MODEL REQUIRED)."
            )
        else:
            reason = (
                "FateIntel assesses one defined substance at a time. Assess each contaminant in the mixture "
                "separately under its own contaminant group; concentrations are not summed and toxicity is not "
                "assumed additive (REGULATORY APPLICABILITY NOT ESTABLISHED for the mixture as a whole)."
            )
        return {
            "jurisdiction": framework,
            "regulatory_programme": {
                "key": "NOT_YET_IMPLEMENTED",
                "name": f"{CONTAMINANT_TAXONOMY[group]['label']}: no native pathway",
                "scope": reason,
            },
            "contaminant_group": group,
            "scenario": scenario,
            "tier": tier,
            "models": [],
            "required_inputs": ["specialist assessment scoping outside FateIntel"],
            "warnings": [reason],
            "plan_summary": (
                f"No FateIntel model workflow is applicable to {group.replace('_', ' ')} under the "
                f"{scenario.replace('_', ' ')} scenario. {reason}"
            ),
        }

    if scenario in {"municipal_wastewater", "household_use", "laboratory_use", "product_disposal"}:
        selected.append("SIMPLETREAT")
        required += ["wastewater flow", "release fraction", "biodegradation", "sorption/partitioning"]
        if tier >= 2:
            selected.append("ACTIVITY_SIMPLETREAT")
            required += ["pKa/speciation", "sewage solids partitioning inputs"]

    point_source_river_scenarios = {
        "municipal_wastewater", "surface_water_discharge", "industrial_effluent",
        "household_use", "laboratory_use", "product_disposal",
    }
    if scenario in point_source_river_scenarios and group in DISCRETE_ORGANIC_GROUPS and tier >= 1:
        selected.append("ENVIROCHEM_CATCHMENT_RIVER_NETWORK")
        required += ["river segment flow", "travel time", "in-stream DT50", "point-source location and load"]
        if tier >= 3:
            selected.append("GREATER")
            required += ["georeferenced river network", "WWTP and industrial source locations"]
            if group == "human_pharmaceutical" and jurisdiction in {"EU", "UK", "CH"}:
                selected.append("EPIE")
                required += ["compound-specific pharmaceutical use", "spatial population and hydrology data"]

    if scenario in {"industrial_effluent", "surface_water_discharge", "product_disposal"} and group in DISCRETE_ORGANIC_GROUPS and tier >= 2:
        selected += ["ENVIROCHEM_MULTIMEDIA_FATE_SCREEN", "SIMPLEBOX"]
        required += ["emissions by compartment", "compartment-specific degradation", "intermedia transfer or fugacity inputs"]

    if tier >= 2 and group in DISCRETE_ORGANIC_GROUPS and scenario in {
        "municipal_wastewater", "surface_water_discharge", "industrial_effluent", "agricultural_spray"
    }:
        # Native transparent research screen, not an official regulatory tool --
        # its own registry entry declares EU/UK/US/CH applicability (see
        # toxswa_surface_water.py's own "not the FOCUS_TOXSWA executable, not
        # regulatory-equivalent" framing), so it must not be gated to EU/UK/CH
        # only; a US assessment is equally entitled to this screen.
        selected.append("ENVIROCHEM_TOXSWA_PROCESS_SCREEN")
        required += ["surface-water loading basis", "waterbody geometry and flow", "water/sediment fate inputs"]

    if scenario in {"biosolids_to_soil", "wastewater_irrigation", "soil_incorporation", "agricultural_spray"}:
        selected.append("ENVIROCHEM_SOIL_SCREEN")
        if scenario == "biosolids_to_soil":
            selected.append("ENVIROCHEM_BIOSOLIDS_LAND_APPLICATION")
        if scenario == "wastewater_irrigation":
            selected.append("ENVIROCHEM_DUAL_WASTEWATER_IRRIGATION")
        required += ["soil bulk density", "mixing depth", "application schedule", "soil DT50", "Koc/Kd"]
        if group in {"human_pharmaceutical", "veterinary_pharmaceutical", "pesticide", "emerging_contaminant", "industrial_organic"} and tier >= 2:
            selected.append("ENVIROCHEM_PLANT_UPTAKE")
            required += ["crop", "root-zone depth", "transpiration or uptake parameters"]

    # "NO" (Norway) joins the FOCUS-model set here -- confirmed 2026-09-23 via Mattilsynet's own national-
    # requirements page: FOCUS MACRO 5.5.4 is mandated for groundwater leaching, and Norway's own six-scenario
    # (not nine) surface-water selection is itself drawn from FOCUS's standard scenario set, implying the
    # standard FOCUS surface-water tools (SWASH/TOXSWA/PRZM) apply too. This is NOT extended to the EFSA birds/
    # mammals/bees screens below -- that methodology's applicability to Norway was not researched this session.
    if jurisdiction in {"EU", "UK", "CH", "NO"} and tier >= 2:
        if scenario in {"groundwater_leaching", "agricultural_spray", "soil_incorporation", "biosolids_to_soil", "wastewater_irrigation"}:
            selected += ["PEARL", "PELMO"]
            if tier >= 3:
                selected.append("MACRO")
        if group == "pesticide" and scenario in {"agricultural_spray", "soil_incorporation"} and tier >= 3:
            selected += ["SWASH", "TOXSWA"]
            # PRZM is used with a FOCUS scenario/configuration here.  The same
            # engine family can also appear in US workflows, so jurisdiction,
            # scenario database and version must remain part of provenance.
            selected.append("PRZM")
        if group == "pesticide" and scenario in {"agricultural_spray", "soil_incorporation"} and jurisdiction != "NO":
            # EU equivalent of the US TERRPLANT/TREX/AGDRIFT/BEEREX ecotox
            # suite -- previously entirely absent for EU pesticide scenarios
            # despite EFSA requiring the equivalent bird/mammal dietary and
            # secondary-poisoning risk assessment (Guidance on the risk
            # assessment for birds and mammals, EFSA Journal 2023;21(2):7790).
            # Acute/reproductive dietary TER and fish-eating AND
            # earthworm-eating secondary-poisoning pathways are implemented --
            # see eu_birds_mammals.py's own module docstring for the exact
            # boundary (no Annex B Generic Model Species tables, no
            # benthic-invertebrate secondary poisoning yet -- no primary
            # source for that pathway's formula was found). Excluded for "NO"
            # (Norway): EFSA birds/mammals methodology applicability to
            # Norway's own pesticide regime was not researched this session,
            # unlike AU's confirmed EFSA-2009 alignment (au_apvma.py).
            selected.append("ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN")
            required += ["reviewer-supplied FIR/BW/RUD/application rate per food item", "avian and mammalian toxicity endpoints (LD50, relevant reproductive endpoint)"]
            # EU equivalent of the US BEEREX gating below: honey-bee Tier 1
            # spray screening only applies when the use site/crop is
            # bee-attractive, mirroring how the US branch reads the same
            # `bee_attractive` flag. AU is deliberately excluded here even
            # though it shares ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN above --
            # APVMA's own bee methodology has not been researched (see the
            # "AU" block below, which explicitly names bee coverage as an
            # unresearched gap), so it must not inherit this EU-sourced screen.
            if bool(data.get("bee_attractive")):
                selected.append("ENVIROCHEM_EU_BEES_SCREEN")
                required += ["contact and oral/larval/HPG bee toxicity endpoints", "spray direction (downwards vs. sideward/upwards)", "crop bee-attractiveness basis"]

    if jurisdiction == "AU" and group == "pesticide" and scenario in {"agricultural_spray", "soil_incorporation"}:
        # APVMA's own guidance confirms its terrestrial-vertebrates TER
        # methodology follows EFSA (2009) with the same acute/reproductive
        # triggers this screen already implements -- see the "AU" note on
        # ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN's own registry entry and
        # au_apvma.py's module docstring. APVMA's aquatic risk-quotient
        # trigger (0.1 acute / 1.0 chronic, au_apvma.py) is a
        # risk-characterisation helper applied to an existing fate model's
        # PEC, not its own registry model, the same way canada_pnec.py and
        # nz_levels_of_concern.py are not their own registry entries either.
        # APVMA's spray-drift/runoff/bee/soil-organism/non-target-plant
        # methodology is NOT covered -- deliberately, see au_apvma.py.
        if "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN" not in selected:
            selected.append("ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN")
            required += ["reviewer-supplied FIR/BW/RUD/application rate per food item", "avian and mammalian toxicity endpoints (LD50, relevant reproductive endpoint)"]

    focus_hosts = {"PEARL", "PELMO", "MACRO", "SWASH", "TOXSWA"}
    if focus_hosts.intersection(selected):
        first_focus_index = min(selected.index(key) for key in focus_hosts.intersection(selected))
        selected.insert(first_focus_index, "SPIN")
        required += ["versioned SPIN substance record", "parent/metabolite transformation pathway"]

    if jurisdiction == "US" and tier >= 2:
        if scenario in {"industrial_effluent", "laboratory_use"} and group == "industrial_organic":
            selected += ["ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN", "CHEMSTEER"]
            required += [
                "process throughput and operating days",
                "activity-specific release events and engineering controls",
                "worker tasks, duration, inhalation and dermal determinants",
                "soil-release area, recharge, Koc, organic carbon and soil DT50 when groundwater may be exposed",
                "published EPA ESD or explicitly enabled draft/reference basis",
            ]
        if scenario == "household_use":
            selected += ["CEM", "EFAST"]
            required += [
                "consumer product or article category",
                "weight fraction, use frequency and duration",
                "population and life-stage exposure factors",
            ]
        if scenario == "product_disposal":
            selected.append("EFAST")
            required += [
                "waste stream, landfill/incineration/off-site treatment split",
                "downstream release and general-population exposure basis",
            ]
        if scenario in {"biosolids_to_soil", "wastewater_irrigation"} and group in {"human_pharmaceutical", "veterinary_pharmaceutical"}:
            # The EU/UK/CH branch above routes the equivalent scenario to PEARL/
            # PELMO/MACRO (dedicated groundwater-leaching models); no US
            # equivalent was registered, leaving these scenarios with zero
            # soil/groundwater-leaching coverage in the US. PRZM is EPA's real
            # root-zone-transport tool and already covers non-pesticide organic
            # groups (industrial_organic); it is not a full groundwater fate
            # model the way PEARL is -- its own outputs are runoff/erosion/
            # leaching_flux only, no groundwater_concentration -- so this is
            # flagged below rather than presented as PEARL-equivalent.
            selected.append("PRZM")
            required += ["soil DT50", "Koc/Kd", "root-zone parameters", "runoff and erosion parameters"]
            warnings.append(
                "PRZM estimates a leaching flux from the root zone; it is not a full groundwater fate model like FOCUS PEARL. Treat its leaching output as a screening-level indicator, not a groundwater concentration."
            )
        if group == "pesticide" and scenario in {
            "agricultural_spray", "soil_incorporation", "groundwater_leaching",
            "surface_water_discharge", "wastewater_irrigation",
        }:
            selected.append("PWC")
            required.append("groundwater/waterbody configuration (mandatory, not optional)")
            if tier >= 3 and scenario == "agricultural_spray":
                selected.append("PRZM")
            if scenario in {"agricultural_spray", "soil_incorporation"}:
                application_method = data.get("application_method")
                use_site_category = data.get("use_site_category")
                bee_attractive = bool(data.get("bee_attractive"))
                # TerrPlant/T-REX are near-universal for outdoor terrestrial pesticide
                # use in real FIFRA reviews -- baseline-selected unless the use site
                # has no terrestrial exposure pathway at all. A soil-incorporated
                # (e.g. granular, in-furrow) pesticide use still triggers the same
                # terrestrial/avian/mammalian and, for systemic active ingredients,
                # bee exposure pathways as a spray application -- it was previously
                # gated to agricultural_spray only, which left this scenario with no
                # ecotox risk-quotient coverage at all. AgDRIFT only applies to
                # application methods capable of off-site drift; BeeREX only when the
                # use site/crop is bee-attractive. See registry.MODELS for the source
                # of truth on each model's region/group/tier eligibility.
                if use_site_category != "enclosed_greenhouse":
                    selected += ["TERRPLANT", "TREX"]
                    required += ["seedling emergence / vegetative vigour endpoints", "avian and mammalian dietary toxicity endpoints"]
                if application_method in {"aerial", "ground_broadcast", "airblast_orchard"}:
                    selected.append("AGDRIFT")
                    required += ["application method, boom height and droplet size", "buffer distance and adjacent waterbody geometry"]
                if bee_attractive:
                    selected.append("BEEREX")
                    required += ["contact and oral bee toxicity endpoints", "crop bee-attractiveness basis"]

    if jurisdiction == "US" and group == "industrial_organic" and scenario in {"industrial_effluent", "laboratory_use"} and tier == 1:
        selected.append("ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN")
        required += [
            "process throughput and operating days",
            "activity-specific release events",
            "worker tasks or an explicit occupational-exposure data gap",
            "groundwater leaching inputs or an explicit groundwater-pathway exclusion",
        ]

    if jurisdiction == "US" and scenario in {"industrial_effluent", "laboratory_use"} and group != "industrial_organic":
        warnings.append(
            "The US industrial source-term workbench is reserved for chemicals classified as industrial organic in the guided workflow. Select Industrial use or prepare a sector-specific source-term assessment."
        )

    if group in DISCRETE_ORGANIC_GROUPS and tier <= 2:
        required.append("measured values preferred; EPI Suite estimates may enter only as reviewed modelled evidence")

    if group in {"metal_inorganic", "polymer_microplastic", "nanomaterial", "uvcb_complex_substance", "mixture_formulation"}:
        warnings.append(
            "Standard organic-chemical partitioning and degradation models may be outside their applicability domain; a group-specific ruleset is required."
        )
    if group == "metal_inorganic":
        required += [
            "element identity (and oxidation state/species where known), not SMILES/Kow",
            "concentration basis stated for every value (total, dissolved, particulate, bioavailable): never converted silently",
            "receiving-water chemistry for bioavailability (pH, dissolved organic carbon, calcium/hardness) where a water criterion applies",
            "natural/regional background concentration",
            "soil or sediment properties (organic matter, pH, clay) for partitioning",
        ]
        warnings.append(
            "Metals need speciation- and bioavailability-aware assessment. FateIntel does not model bioavailability: "
            "EXTERNAL MODEL REQUIRED (e.g. M-BAT/BLM tools) where a bioavailable criterion applies. "
            "Do not call a metal safe because total concentration is below a generic threshold."
        )
    if group in LEGACY_ORGANIC_GROUPS:
        required.append("CAS number for the POPs regulatory-status check (/api/pops/status); names alone can be ambiguous")
        warnings.append(
            "Native Tier 1-2 organic partitioning and degradation screening applies to this class. "
            "Bioaccumulation/food-web, sediment-focused assessment and POPs regulatory-status flagging are not "
            "yet implemented: SCREENING / COMPARATIVE USE only."
        )
    if group == "pfas_persistent_mobile":
        warnings.append(
            "Hydrophobicity-only partitioning and conventional biodegradation defaults are not sufficient for many PFAS; chain-length and ionic-state specific evidence is required."
        )
    if tier >= 4:
        required += ["monitoring data", "site-specific hydrology", "calibration record", "uncertainty distribution"]

    if jurisdiction in {"EU", "UK", "CH", "NO"} and scenario == "household_use":
        warnings.append(
            "This plan currently routes environmental releases and fate. A complete REACH consumer human-exposure assessment is not implemented in the guided screen."
        )
    if jurisdiction in {"EU", "UK", "CH", "NO"} and scenario == "product_disposal":
        warnings.append(
            "Waste-stage routing is a planning workflow; landfill, incineration and treatment emissions require reviewed waste-specific inputs before a quantitative result."
        )
    if jurisdiction in {"EU", "UK", "CH", "NO"} and scenario in {"industrial_effluent", "laboratory_use"}:
        warnings.append(
            "The current EU plan covers environmental release and fate. A dedicated REACH worker-exposure calculation is not yet implemented."
        )

    # Preserve order and remove duplicates.
    selected = list(dict.fromkeys(selected))
    required = list(dict.fromkeys(required))

    applicable = []
    for key in selected:
        model = _model(key)
        region_ok = jurisdiction in model["regions"]
        group_ok = group in model["groups"]
        tier_ok = tier in model["tiers"] or (tier > max(model["tiers"]) and max(model["tiers"]) >= 3)
        applicable.append({
            **model,
            "applicable": region_ok and group_ok and tier_ok,
            "applicability_reasons": {
                "jurisdiction": region_ok,
                "contaminant_group": group_ok,
                "tier": tier_ok,
            },
        })

    framework = next(f for f in FRAMEWORKS if f["key"] == jurisdiction)
    programme = _regulatory_programme(jurisdiction, group, scenario)
    return {
        "jurisdiction": framework,
        "regulatory_programme": programme,
        "contaminant_group": group,
        "scenario": scenario,
        "tier": tier,
        "models": applicable,
        "required_inputs": required,
        "warnings": warnings,
        "plan_summary": (
            f"Tier {tier} {framework['name']} assessment for {group.replace('_', ' ')} under the "
            f"{scenario.replace('_', ' ')} scenario. {len(applicable)} model workflow(s) selected."
        ),
    }
