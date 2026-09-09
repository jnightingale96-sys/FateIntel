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
]

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
    }
]

MODELS: list[dict[str, Any]] = [
    {
        "key": "SIMPLETREAT",
        "name": "SimpleTreat",
        "domain": "municipal wastewater treatment",
        "regions": ["EU", "UK", "CH", "US"],
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
        "regions": ["EU", "UK", "CH", "US"],
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
        "regions": ["EU", "UK", "CH", "US"],
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
        "regions": ["EU", "UK", "CH", "US"],
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
        "regions": ["US", "EU", "UK", "CH"],
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
        "regions": ["EU", "UK", "CH"],
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
        "regions": ["EU", "UK", "CH"],
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
        "regions": ["EU", "UK", "US", "CH"],
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
        "regions": ["EU", "UK", "CH", "US"],
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
        "regions": ["EU", "UK", "CH"],
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
        "regions": ["EU", "UK", "CH"],
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
        "regions": ["US", "EU", "UK", "CH"],
        "groups": ["pesticide", "biocide", "industrial_organic", "emerging_contaminant"],
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
        "regions": ["EU", "UK", "US", "CH"],
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
        "regions": ["EU", "UK", "US", "CH"],
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
    "regions": ["EU", "UK", "US", "CH"],
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
    "regions": ["EU", "UK", "CH"],
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
        "regions": ["EU", "UK", "US", "CH"],
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
        "regions": ["EU", "UK", "US", "CH"],
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
        "regions": ["EU", "UK", "US", "CH"],
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
        "regions": ["EU", "UK", "US", "CH", "AU"],
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
        "regions": ["EU", "UK", "US", "CH", "AU"],
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
        "regions": ["EU", "UK", "US", "CH"],
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

    if jurisdiction in {"EU", "UK", "CH"} and tier >= 2:
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
    if group == "pfas_persistent_mobile":
        warnings.append(
            "Hydrophobicity-only partitioning and conventional biodegradation defaults are not sufficient for many PFAS; chain-length and ionic-state specific evidence is required."
        )
    if tier >= 4:
        required += ["monitoring data", "site-specific hydrology", "calibration record", "uncertainty distribution"]

    if jurisdiction in {"EU", "UK", "CH"} and scenario == "household_use":
        warnings.append(
            "This plan currently routes environmental releases and fate. A complete REACH consumer human-exposure assessment is not implemented in the guided screen."
        )
    if jurisdiction in {"EU", "UK", "CH"} and scenario == "product_disposal":
        warnings.append(
            "Waste-stage routing is a planning workflow; landfill, incineration and treatment emissions require reviewed waste-specific inputs before a quantitative result."
        )
    if jurisdiction in {"EU", "UK", "CH"} and scenario in {"industrial_effluent", "laboratory_use"}:
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
