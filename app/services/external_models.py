from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..config import settings
from .external_execution import EPA_EXECUTION_MODEL_KEYS, external_tool_status

# Matches AssessmentPlanCreate.application_method in app/schemas.py -- kept as
# one shared list so the guided screen's routing enum and the pesticide-model
# input forms' <select> options can never drift apart.
APPLICATION_METHODS = [
    "aerial", "ground_broadcast", "airblast_orchard",
    "soil_incorporated", "seed_treatment", "chemigation", "granular",
]


MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "SPIN": {
        "name": "FOCUS SPIN",
        "official_version": "4.4",
        "role": "FOCUS substance-property and transformation-pathway repository",
        "is_simulation_model": False,
        "official_page": "https://esdac.jrc.ec.europa.eu/projects/spin",
        "path_environment_variable": "ENVIROCHEM_SPIN_PATH",
        "default_path": r"C:\Program Files (x86)\Pesticide Models\SPIN",
        "prerequisites": [],
        "host_workflows": ["PEARL", "SWASH", "MACRO", "TOXSWA"],
        "input_template": {
            "substance_identity": {
                "status": "required", "preferred_name": None, "cas_number": None,
                "molecular_weight_g_mol": None,
            },
            "substance_properties": {
                "status": "required", "koc_or_freundlich": None, "water_solubility_mg_l": None,
                "vapour_pressure_pa": None, "soil_dt50_days": None, "tscf": None,
            },
            "transformation_pathway": {
                "status": "required", "parent_key": None, "metabolites": [], "formation_fractions": [],
            },
            "host_model_targets": {
                "status": "required", "models": ["PEARL", "SWASH", "MACRO", "TOXSWA"],
            },
            "database_version": {"status": "required", "spin_version": "4.4", "record_revision": None},
        },
        "known_constraints": [
            "SPIN is a shared substance database and pathway editor, not a fate simulation model.",
            "Only one SPIN-connected host application should access the database at a time.",
            "SPIN must be installed on a local drive before PEARL or SWASH.",
            "With SPIN 4.4, edit TSCF in standalone SPIN when the PEARL-hosted field is disabled; do not accept 0.5 without a substance-specific basis.",
            "Do not uninstall SPIN 3.3 when an existing substance database must be retained.",
        ],
    },
    "MACRO": {
        "name": "FOCUS MACRO",
        "official_version": "FOCUS_MACRO 5.5.4a (MACRO model 5.2)",
        "role": "Preferential-flow soil transport, groundwater leaching and surface-water drainage loading",
        "is_simulation_model": True,
        "official_page": "https://esdac.jrc.ec.europa.eu/projects/macro",
        "path_environment_variable": "ENVIROCHEM_MACRO_PATH",
        "default_path": r"C:\SWASH\MACRO",
        "prerequisites": ["SPIN", "SWASH for FOCUS surface-water projects"],
        "host_workflows": ["FOCUS groundwater", "SWASH to TOXSWA surface water"],
        "input_template": {
            "execution_route": {"status": "required", "value": "groundwater_leaching", "allowed": ["groundwater_leaching", "surface_water_drainage"]},
            "spin_substance_record": {"status": "required", "substance_key": None, "database_version": "4.4"},
            "focus_scenario": {"status": "required", "scenario_key": None, "scenario_database_version": None},
            "crop_and_application": {"status": "required", "crop": None, "applications": []},
            "soil_profile_and_hydrology": {"status": "required", "profile_source": "official FOCUS scenario", "drainage": None},
            "degradation_and_sorption": {"status": "required", "soil_dt50_days": None, "freundlich_kf": None, "freundlich_exponent": None},
            "weather_and_run_settings": {"status": "required", "weather_series": None, "simulation_years": None, "percentile_method": None},
        },
        "known_constraints": [
            "MACRO represents dual-domain macropore and micropore flow; it must not be substituted by a single-domain screening equation.",
            "The official model is used for the Chateaudun groundwater scenario and for drainage inputs in six FOCUS surface-water scenarios.",
            "FOCUS_MACRO 5.5.4a is the Windows 11-compatible installation package; its installed model is essentially the 5.5.4/MACRO 5.2 implementation.",
            "When the standalone M2T tool is used, the documented output-file case requirement must be checked before generating .m2t lateral-entry files.",
        ],
    },
    "GREATER": {
        "name": "GREAT-ER 4",
        "official_version": "4",
        "role": "GIS-based river-basin exposure from down-the-drain and defined point sources",
        "is_simulation_model": True,
        "official_page": "https://www.erasm.org/wp-content/uploads/2022/07/4.4.1.1GREAT-ER_TechnicalPositioning_DS.161116.pdf",
        "path_environment_variable": "ENVIROCHEM_GREATER_PATH",
        "default_path": None,
        "prerequisites": ["compatible GREAT-ER software", "PostgreSQL", "licensed or authorised basin dataset"],
        "host_workflows": ["REACH river-basin refinement", "Water Framework Directive support", "pharmaceutical and consumer-chemical point sources"],
        "input_template": {
            "basin_database": {"status": "required", "basin_id": None, "database_version": None, "rights_basis": None},
            "georeferenced_river_network": {"status": "required", "dataset": None, "crs": None, "reach_identifier_field": None},
            "reach_hydrology": {"status": "required", "flow_statistic": None, "flow_units": None, "travel_time_source": None},
            "point_sources": {"status": "required", "wwtp_dataset": None, "industrial_sources": [], "coordinate_reference_system": None},
            "emission_loads": {"status": "required", "basis": None, "mass_unit": "kg/day", "source_linkage": None},
            "wwtp_removal": {"status": "required", "basis": None, "fraction_or_model": None},
            "in_stream_fate": {"status": "required", "water_dt50_days": None, "sediment_module": False, "temperature_basis": None},
            "simulation_settings": {"status": "required", "mode": "deterministic", "uncertainty_iterations": None, "output_statistics": []},
        },
        "known_constraints": [
            "GREAT-ER requires a georeferenced river network, point-source inventory and basin hydrology; a generic branched network is not an official GREAT-ER run.",
            "Basin database identity, vintage, coordinate reference system and data rights must be stored with every workflow.",
            "The native EnviroChem catchment screen may prepare inputs and provide a comparison, but its outputs must remain separately labelled.",
            "GREAT-ER 4 is described as open-source software, while usable basin datasets and local deployment remain separate prerequisites.",
        ],
    },
    "PWC": {
        "name": "US EPA Pesticide in Water Calculator",
        "official_version": "3.003 (verify installed build and scenario files)",
        "role": "FIFRA pesticide surface-water, sediment and simple-groundwater exposure modelling",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment",
        "path_environment_variable": "ENVIROCHEM_PWC_PATH",
        "default_path": None,
        "prerequisites": [
            "separately obtained official PWC installation",
            "current EPA scenario and meteorological files",
            "reviewed pesticide application and fate inputs",
        ],
        "host_workflows": ["FIFRA pesticide surface-water assessment", "FIFRA simple-groundwater assessment"],
        "input_template": {
            "contaminant_group": "pesticide",
            "application_pattern": {"status": "required", "application_rate_kg_ha": None, "number_of_applications": None, "application_interval_days": None, "application_method": None},
            "pwc3_us_scenario": {"status": "required", "scenario_id": None, "crop": None},
            "soil_and_crop_inputs": {"status": "required", "crop": None, "canopy_interception_fraction": None},
            "weather_series": {"status": "required", "weather_station_id": None, "simulation_years": None},
            "soil_dt50": {"status": "required", "value_days": None, "source": None},
            "koc_or_kd": {"status": "required", "value": None, "unit": None, "basis": None},
            "aquatic_fate_inputs": {"status": "required", "water_column_dt50_days": None, "benthic_dt50_days": None, "hydrolysis_dt50_days": None},
            "groundwater_and_waterbody_configuration": {"status": "required", "waterbody_type": None, "depth_m": None},
        },
        "field_types": {
            "application_pattern.application_rate_kg_ha": {"type": "number", "unit": "kg/ha", "min": 0, "required": True},
            "application_pattern.number_of_applications": {"type": "number", "min": 1, "step": 1, "required": True},
            "application_pattern.application_interval_days": {"type": "number", "unit": "days", "min": 0},
            "application_pattern.application_method": {"type": "select", "options": APPLICATION_METHODS, "required": True},
            "soil_and_crop_inputs.canopy_interception_fraction": {"type": "number", "min": 0, "max": 1, "step": "any"},
            "weather_series.simulation_years": {"type": "number", "min": 1, "step": 1},
            "soil_dt50.value_days": {"type": "number", "unit": "days", "min": 0, "required": True},
            "koc_or_kd.value": {"type": "number", "min": 0, "required": True},
            "koc_or_kd.unit": {"type": "select", "options": ["L/kg", "L/kg_oc"], "required": True},
            "aquatic_fate_inputs.water_column_dt50_days": {"type": "number", "unit": "days", "min": 0},
            "aquatic_fate_inputs.benthic_dt50_days": {"type": "number", "unit": "days", "min": 0},
            "aquatic_fate_inputs.hydrolysis_dt50_days": {"type": "number", "unit": "days", "min": 0},
            "groundwater_and_waterbody_configuration.waterbody_type": {"type": "select", "options": ["index_reservoir", "index_pond", "farm_pond"], "required": True},
            "groundwater_and_waterbody_configuration.depth_m": {"type": "number", "unit": "m", "min": 0},
        },
        "known_constraints": [
            "PWC is a pesticide model; do not route an industrial chemical to it solely because a soil release exists.",
            "Scenario and meteorological file versions are part of the result provenance.",
            "EnviroChem does not redistribute PWC or represent a prepared manifest as a completed PWC run.",
        ],
    },
    "PRZM": {
        "name": "US EPA Pesticide Root Zone Model (PRZM)",
        "official_version": "PRZM (verify installed build via PWC3 or standalone package)",
        "role": "FIFRA pesticide runoff, erosion and leaching loading from the treated field",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment",
        # No path_environment_variable: no local-execution config field exists for
        # this model (see EPA_EXECUTION_MODEL_KEYS) -- advertising one that has no
        # effect would be misleading. Manual handoff via /import-output-files only.
        "default_path": None,
        "prerequisites": ["authorised local PRZM installation", "reviewed pesticide-use scenario and formulation basis"],
        "host_workflows": ["FIFRA runoff/erosion/leaching loading assessment", "PWC/EXAMS receiving-water follow-on", "FOCUS EU groundwater/surface-water configurations"],
        "input_template": {
            "contaminant_group": "pesticide",
            "application_pattern": {"status": "required", "application_rate_kg_ha": None, "number_of_applications": None, "application_interval_days": None, "application_method": None},
            "soil_and_crop_scenario": {"status": "required", "przm_scenario_id": None, "crop": None},
            "weather_series": {"status": "required", "weather_station_id": None, "simulation_years": None},
            "soil_dt50": {"status": "required", "value_days": None, "source": None},
            "koc_or_kd": {"status": "required", "value": None, "unit": None, "basis": None},
            "runoff_and_erosion_parameters": {"status": "required", "curve_number": None, "usle_k": None, "usle_ls": None, "usle_c": None},
            "root_zone_parameters": {"status": "required", "root_depth_cm": None, "field_capacity": None, "wilting_point": None},
        },
        "field_types": {
            "application_pattern.application_rate_kg_ha": {"type": "number", "unit": "kg/ha", "min": 0, "required": True},
            "application_pattern.number_of_applications": {"type": "number", "min": 1, "step": 1, "required": True},
            "application_pattern.application_interval_days": {"type": "number", "unit": "days", "min": 0},
            "application_pattern.application_method": {"type": "select", "options": APPLICATION_METHODS, "required": True},
            "weather_series.simulation_years": {"type": "number", "min": 1, "step": 1},
            "soil_dt50.value_days": {"type": "number", "unit": "days", "min": 0, "required": True},
            "koc_or_kd.value": {"type": "number", "min": 0, "required": True},
            "koc_or_kd.unit": {"type": "select", "options": ["L/kg", "L/kg_oc"], "required": True},
            "runoff_and_erosion_parameters.curve_number": {"type": "number", "min": 0, "max": 100, "required": True},
            "runoff_and_erosion_parameters.usle_k": {"type": "number", "min": 0, "step": "any", "required": True},
            "runoff_and_erosion_parameters.usle_ls": {"type": "number", "min": 0, "step": "any"},
            "runoff_and_erosion_parameters.usle_c": {"type": "number", "min": 0, "step": "any"},
            "root_zone_parameters.root_depth_cm": {"type": "number", "unit": "cm", "min": 0},
            "root_zone_parameters.field_capacity": {"type": "number", "min": 0, "max": 1, "step": "any"},
            "root_zone_parameters.wilting_point": {"type": "number", "min": 0, "max": 1, "step": "any"},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify PRZM; execution occurs in an authorised external installation.",
            "PRZM outputs (runoff, erosion, leaching loads) are typically a loading input to a receiving-water model (PWC/EXAMS), not a standalone concentration.",
            "Curve number, USLE factors and root-zone parameters must match the selected soil/crop scenario, not generic defaults.",
            "PRZM is used both as a US FIFRA loading model and within EU FOCUS groundwater/surface-water configurations; jurisdiction and scenario database must remain part of provenance.",
        ],
    },
    "AGDRIFT": {
        "name": "AgDRIFT / AGDISP",
        "official_version": "AgDRIFT (verify installed build)",
        "role": "Spray-drift deposition and off-site exposure from agricultural pesticide applications",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment",
        # No path_environment_variable: see the PRZM entry above for why.
        "default_path": None,
        "prerequisites": ["authorised local AgDRIFT/AGDISP installation", "reviewed application method and equipment basis"],
        "host_workflows": ["FIFRA spray-drift deposition assessment"],
        "input_template": {
            "contaminant_group": "pesticide",
            "application_parameters": {"status": "required", "application_method": None, "boom_height_m": None, "droplet_size_category": None, "application_rate_kg_ha": None},
            "meteorological_conditions": {"status": "required", "wind_speed_m_s": None, "temperature_c": None},
            "buffer_and_geometry": {"status": "required", "buffer_distance_m": None, "waterbody_width_m": None},
        },
        "field_types": {
            "application_parameters.application_method": {"type": "select", "options": APPLICATION_METHODS, "required": True},
            "application_parameters.boom_height_m": {"type": "number", "unit": "m", "min": 0, "required": True},
            "application_parameters.droplet_size_category": {"type": "select", "options": ["very_fine", "fine", "medium", "coarse", "very_coarse", "extremely_coarse"], "required": True},
            "application_parameters.application_rate_kg_ha": {"type": "number", "unit": "kg/ha", "min": 0, "required": True},
            "meteorological_conditions.wind_speed_m_s": {"type": "number", "unit": "m/s", "min": 0, "required": True},
            "meteorological_conditions.temperature_c": {"type": "number", "unit": "°C"},
            "buffer_and_geometry.buffer_distance_m": {"type": "number", "unit": "m", "min": 0, "required": True},
            "buffer_and_geometry.waterbody_width_m": {"type": "number", "unit": "m", "min": 0, "required": True},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify AgDRIFT/AGDISP; execution occurs in an authorised external installation.",
            "Only application methods capable of off-site drift (aerial, ground broadcast, airblast) require this model; soil-incorporated, seed-treatment and chemigation methods do not.",
            "Droplet size category and release height materially change the deposition curve and must match the labelled/registered application equipment.",
        ],
    },
    "TERRPLANT": {
        "name": "TerrPlant",
        "official_version": "TerrPlant (verify installed build)",
        "role": "Screening-level terrestrial plant exposure from runoff and drift of pesticide applications",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment",
        # No path_environment_variable: see the PRZM entry above for why.
        "default_path": None,
        "prerequisites": ["authorised local TerrPlant installation", "reviewed seedling emergence / vegetative vigour toxicity endpoints"],
        "host_workflows": ["FIFRA terrestrial plant risk assessment"],
        "input_template": {
            "contaminant_group": "pesticide",
            "application_parameters": {"status": "required", "application_rate_lb_ac": None, "application_method": None},
            "runoff_and_drift_inputs": {"status": "required", "distance_to_habitat_m": None, "soil_type": None},
            "toxicity_endpoints": {"status": "required", "seedling_emergence_ec25": None, "vegetative_vigor_ec25": None},
        },
        "field_types": {
            "application_parameters.application_rate_lb_ac": {"type": "number", "unit": "lb/ac", "min": 0, "required": True},
            "application_parameters.application_method": {"type": "select", "options": APPLICATION_METHODS, "required": True},
            "runoff_and_drift_inputs.distance_to_habitat_m": {"type": "number", "unit": "m", "min": 0, "required": True},
            "runoff_and_drift_inputs.soil_type": {"type": "select", "options": ["sand", "loam", "clay", "silt"]},
            "toxicity_endpoints.seedling_emergence_ec25": {"type": "number", "min": 0, "required": True},
            "toxicity_endpoints.vegetative_vigor_ec25": {"type": "number", "min": 0, "required": True},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify TerrPlant; execution occurs in an authorised external installation.",
            "TerrPlant is a screening-level tool; a risk quotient above the level of concern indicates a need for refined assessment, not automatic non-registration.",
        ],
    },
    "TREX": {
        "name": "T-REX",
        "official_version": "T-REX (verify installed build)",
        "role": "Avian and mammalian dietary exposure and risk quotient from pesticide residues on food items",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment",
        # No path_environment_variable: see the PRZM entry above for why.
        "default_path": None,
        "prerequisites": ["authorised local T-REX installation", "reviewed avian and mammalian toxicity endpoints"],
        "host_workflows": ["FIFRA avian and mammalian dietary risk assessment"],
        "input_template": {
            "contaminant_group": "pesticide",
            "application_parameters": {"status": "required", "application_rate_lb_ac": None, "number_of_applications": None},
            "dietary_inputs": {"status": "required", "food_item_category": None, "body_weight_g": None},
            "toxicity_endpoints": {"status": "required", "avian_lc50_or_ld50": None, "mammalian_ld50": None},
        },
        "field_types": {
            "application_parameters.application_rate_lb_ac": {"type": "number", "unit": "lb/ac", "min": 0, "required": True},
            "application_parameters.number_of_applications": {"type": "number", "min": 1, "step": 1, "required": True},
            "dietary_inputs.food_item_category": {"type": "select", "options": ["short_grass", "tall_grass", "broadleaf_forage", "seeds", "insects", "fruits"], "required": True},
            "dietary_inputs.body_weight_g": {"type": "number", "unit": "g", "min": 0},
            "toxicity_endpoints.avian_lc50_or_ld50": {"type": "number", "min": 0, "required": True},
            "toxicity_endpoints.mammalian_ld50": {"type": "number", "min": 0, "required": True},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify T-REX; execution occurs in an authorised external installation.",
            "Food-item category (e.g. short grass, tall grass, seeds, insects) drives the residue estimate and must match the labelled use site.",
        ],
    },
    "BEEREX": {
        "name": "BeeREX",
        "official_version": "BeeREX (verify installed build)",
        "role": "Screening-level bee exposure and contact/oral risk quotient from pesticide applications",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/models-pesticide-risk-assessment",
        # No path_environment_variable: see the PRZM entry above for why.
        "default_path": None,
        "prerequisites": ["authorised local BeeREX installation", "reviewed contact and oral bee toxicity endpoints"],
        "host_workflows": ["FIFRA pollinator risk assessment"],
        "input_template": {
            "contaminant_group": "pesticide",
            "application_parameters": {"status": "required", "application_rate_lb_ac": None, "application_method": None},
            "exposure_route_inputs": {"status": "required", "contact_or_dietary": None, "crop_bee_attractiveness": None},
            "toxicity_endpoints": {"status": "required", "contact_ld50_bee": None, "oral_ld50_bee": None},
        },
        "field_types": {
            "application_parameters.application_rate_lb_ac": {"type": "number", "unit": "lb/ac", "min": 0, "required": True},
            "application_parameters.application_method": {"type": "select", "options": APPLICATION_METHODS, "required": True},
            "exposure_route_inputs.contact_or_dietary": {"type": "select", "options": ["contact", "dietary", "both"], "required": True},
            "exposure_route_inputs.crop_bee_attractiveness": {"type": "select", "options": ["high", "moderate", "low", "none"], "required": True},
            "toxicity_endpoints.contact_ld50_bee": {"type": "number", "min": 0, "required": True},
            "toxicity_endpoints.oral_ld50_bee": {"type": "number", "min": 0, "required": True},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify BeeREX; execution occurs in an authorised external installation.",
            "Only relevant when the use site/crop is bee-attractive or the application method creates bee contact potential; not every pesticide use triggers a pollinator assessment.",
        ],
    },
    "CHEMSTEER": {
        "name": "US EPA ChemSTEER",
        "official_version": "3.2 (verify installed build)",
        "role": "TSCA screening of industrial environmental releases and occupational exposure",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/tsca-screening-tools/chemsteer-chemical-screening-tool-exposures-and-environmental-releases",
        "path_environment_variable": "ENVIROCHEM_CHEMSTEER_PATH",
        "default_path": None,
        "prerequisites": ["authorised local ChemSTEER installation", "reviewed process/use description", "versioned ESD or scenario basis"],
        "host_workflows": ["TSCA industrial release screening", "TSCA occupational exposure screening"],
        "input_template": {
            "chemical_identity_and_properties": {"status": "required"},
            "production_or_import_volume": {"status": "required"},
            "process_and_use_description": {"status": "required"},
            "days_and_sites": {"status": "required"},
            "release_activity_parameters": {"status": "required"},
            "engineering_controls": {"status": "required"},
            "worker_activity_parameters": {"status": "required"},
            "esd_and_parameter_provenance": {"status": "required"},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify ChemSTEER; execution occurs in an authorised external installation.",
            "An ESD is a scenario basis, not chemical-specific proof. Draft scenarios must be enabled explicitly and remain labelled draft.",
            "Near-field task peaks, control performance and dermal contact require expert review.",
        ],
    },
    "CEM": {
        "name": "US EPA Consumer Exposure Model",
        "official_version": "3.2 (October 2023 guide; verify installed build)",
        "role": "TSCA consumer product and article exposure across inhalation, ingestion and dermal routes",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/tsca-screening-tools/consumer-exposure-model-cem",
        "path_environment_variable": "ENVIROCHEM_CEM_PATH",
        "default_path": None,
        "prerequisites": ["authorised local CEM installation", "reviewed product/article category", "population and life-stage selections"],
        "host_workflows": ["TSCA consumer exposure assessment"],
        "input_template": {
            "chemical_identity_and_properties": {"status": "required"},
            "product_or_article_category": {"status": "required"},
            "chemical_weight_fraction": {"status": "required"},
            "use_frequency_and_duration": {"status": "required"},
            "emission_model_selection": {"status": "required"},
            "inhalation_dermal_ingestion_models": {"status": "required"},
            "population_and_lifestage_factors": {"status": "required"},
            "parameter_provenance": {"status": "required"},
        },
        "known_constraints": [
            "EnviroChem does not reproduce or modify CEM; execution occurs in an authorised external installation.",
            "Category selection, exposed population and life-stage assumptions can dominate results and must be recorded.",
            "Do not infer absent exposure routes from a single selected model.",
        ],
    },
    "EFAST": {
        "name": "US EPA E-FAST",
        "official_version": "2014 (legacy)",
        "role": "Legacy screening of environmental fate, releases, consumer and general-population exposure",
        "is_simulation_model": True,
        "official_page": "https://www.epa.gov/tsca-screening-tools/e-fast-exposure-and-fate-assessment-screening-tool-version-2014",
        "path_environment_variable": "ENVIROCHEM_EFAST_PATH",
        "default_path": None,
        "prerequisites": ["authorised local E-FAST 2014 installation", "documented legacy-use justification"],
        "host_workflows": ["historical TSCA screening reproduction", "legacy landfill, air, water and consumer screening"],
        "input_template": {
            "chemical_identity_and_properties": {"status": "required"},
            "release_or_use_scenario": {"status": "required"},
            "air_water_or_landfill_inputs": {"status": "required"},
            "consumer_and_population_inputs": {"status": "required"},
            "executable_version": {"status": "required"},
            "legacy_use_justification": {"status": "required"},
            "parameter_provenance": {"status": "required"},
        },
        "known_constraints": [
            "E-FAST 2014 is retained as a legacy workflow and must not be represented as a current replacement for programme-specific tools.",
            "EnviroChem does not modify, adapt or redistribute the E-FAST executable.",
            "Imported outputs must preserve executable version, scenario choices and complete raw files.",
        ],
    },
}


def _unresolved(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set)):
        return not value
    if isinstance(value, dict):
        if not value:
            return True
        return str(value.get("status", "")).lower() in {"required", "missing", "unresolved"}
    return False


def validate_external_model_inputs(model_key: str, input_data: dict[str, Any]) -> dict[str, Any] | None:
    profile = MODEL_PROFILES.get(model_key)
    if profile is None:
        return None
    missing = [key for key in profile["input_template"] if _unresolved(input_data.get(key))]
    warnings = list(profile["known_constraints"])

    def require_nested(section_name: str, fields: list[str]) -> None:
        section = input_data.get(section_name)
        if not isinstance(section, dict) or str(section.get("status", "")).lower() in {"required", "missing", "unresolved"}:
            return
        for field in fields:
            if _unresolved(section.get(field)):
                missing.append(f"{section_name}.{field}")

    field_types = profile.get("field_types", {})

    def validate_field_types() -> None:
        # Generic, defense-in-depth pass over every declared field_types entry
        # (not a hand-picked subset): a direct API call bypassing the form
        # cannot submit an invalid enum option, a non-finite ("NaN"/"Infinity")
        # or non-numeric value, a fractional value in an integer-only field, or
        # an out-of-range value for ANY field the profile declares typed --
        # required or optional. Presence/requiredness for fields without a
        # field_types entry is still handled by require_nested() below.
        for path, meta in field_types.items():
            section_name, field = path.split(".", 1)
            section = input_data.get(section_name)
            if not isinstance(section, dict) or str(section.get("status", "")).lower() in {"required", "missing", "unresolved"}:
                continue
            raw = section.get(field)
            if _unresolved(raw):
                if meta.get("required"):
                    missing.append(f"{path} (required)")
                continue
            field_type = meta.get("type")
            if field_type == "select":
                if raw not in (meta.get("options") or []):
                    missing.append(f"{path} (invalid option)")
            elif field_type == "number":
                try:
                    numeric_value = float(raw)
                except (TypeError, ValueError):
                    missing.append(f"{path} (must be numeric)")
                    continue
                if not math.isfinite(numeric_value):
                    missing.append(f"{path} (must be a finite number)")
                    continue
                if meta.get("step") == 1 and not numeric_value.is_integer():
                    missing.append(f"{path} (must be a whole number)")
                    continue
                minimum = meta.get("min")
                maximum = meta.get("max")
                if (minimum is not None and numeric_value < minimum) or (maximum is not None and numeric_value > maximum):
                    missing.append(f"{path} (out of range)")

    validate_field_types()

    if model_key == "SPIN":
        require_nested("substance_identity", ["preferred_name", "molecular_weight_g_mol"])
        require_nested("substance_properties", ["koc_or_freundlich", "water_solubility_mg_l", "vapour_pressure_pa", "soil_dt50_days"])
        require_nested("transformation_pathway", ["parent_key"])
        require_nested("host_model_targets", ["models"])
        require_nested("database_version", ["spin_version", "record_revision"])
        properties = input_data.get("substance_properties") or {}
        if properties.get("tscf") == 0.5:
            warnings.append("The entered TSCF is 0.5; confirm a relevant substance-specific basis or replace it with zero, as instructed for the current SPIN/PEARL combination.")
    elif model_key == "MACRO":
        require_nested("execution_route", ["value"])
        require_nested("spin_substance_record", ["substance_key", "database_version"])
        require_nested("focus_scenario", ["scenario_key", "scenario_database_version"])
        require_nested("crop_and_application", ["crop", "applications"])
        require_nested("soil_profile_and_hydrology", ["profile_source", "drainage"])
        require_nested("degradation_and_sorption", ["soil_dt50_days", "freundlich_kf", "freundlich_exponent"])
        require_nested("weather_and_run_settings", ["weather_series", "simulation_years", "percentile_method"])
        route = (input_data.get("execution_route") or {}).get("value")
        if route not in {None, "groundwater_leaching", "surface_water_drainage"}:
            missing.append("execution_route.valid_value")
        if route == "surface_water_drainage":
            warnings.append("Surface-water drainage execution must retain the SWASH project linkage and generated .m2t file for downstream TOXSWA review.")
    elif model_key == "GREATER":
        require_nested("basin_database", ["basin_id", "database_version", "rights_basis"])
        require_nested("georeferenced_river_network", ["dataset", "crs", "reach_identifier_field"])
        require_nested("reach_hydrology", ["flow_statistic", "flow_units", "travel_time_source"])
        require_nested("point_sources", ["wwtp_dataset", "coordinate_reference_system"])
        require_nested("emission_loads", ["basis", "mass_unit", "source_linkage"])
        require_nested("wwtp_removal", ["basis", "fraction_or_model"])
        require_nested("in_stream_fate", ["water_dt50_days", "temperature_basis"])
        require_nested("simulation_settings", ["mode", "output_statistics"])
        basin = input_data.get("basin_database") or {}
        if basin and not basin.get("rights_basis") and basin.get("status") != "required":
            missing.append("basin_database.rights_basis")
        network = input_data.get("georeferenced_river_network") or {}
        if network and not network.get("crs") and network.get("status") != "required":
            missing.append("georeferenced_river_network.crs")
    elif model_key == "PWC":
        require_nested("application_pattern", ["application_rate_kg_ha", "number_of_applications", "application_method"])
        require_nested("pwc3_us_scenario", ["scenario_id", "crop"])
        require_nested("soil_dt50", ["value_days", "source"])
        require_nested("koc_or_kd", ["value", "unit"])
        require_nested("groundwater_and_waterbody_configuration", ["waterbody_type"])
    elif model_key == "PRZM":
        require_nested("application_pattern", ["application_rate_kg_ha", "number_of_applications", "application_method"])
        require_nested("soil_and_crop_scenario", ["przm_scenario_id", "crop"])
        require_nested("soil_dt50", ["value_days", "source"])
        require_nested("koc_or_kd", ["value", "unit"])
        require_nested("runoff_and_erosion_parameters", ["curve_number", "usle_k"])
    elif model_key == "AGDRIFT":
        require_nested("application_parameters", ["application_method", "boom_height_m", "droplet_size_category", "application_rate_kg_ha"])
        require_nested("meteorological_conditions", ["wind_speed_m_s"])
        require_nested("buffer_and_geometry", ["buffer_distance_m", "waterbody_width_m"])
    elif model_key == "TERRPLANT":
        require_nested("application_parameters", ["application_rate_lb_ac", "application_method"])
        require_nested("runoff_and_drift_inputs", ["distance_to_habitat_m"])
        require_nested("toxicity_endpoints", ["seedling_emergence_ec25", "vegetative_vigor_ec25"])
    elif model_key == "TREX":
        require_nested("application_parameters", ["application_rate_lb_ac", "number_of_applications"])
        require_nested("dietary_inputs", ["food_item_category"])
        require_nested("toxicity_endpoints", ["avian_lc50_or_ld50", "mammalian_ld50"])
    elif model_key == "BEEREX":
        require_nested("application_parameters", ["application_rate_lb_ac", "application_method"])
        require_nested("exposure_route_inputs", ["contact_or_dietary", "crop_bee_attractiveness"])
        require_nested("toxicity_endpoints", ["contact_ld50_bee", "oral_ld50_bee"])

    return {
        "official_name": profile["name"],
        "official_version": profile["official_version"],
        "role": profile["role"],
        "is_simulation_model": profile["is_simulation_model"],
        "official_page": profile["official_page"],
        "prerequisites": profile["prerequisites"],
        "host_workflows": profile["host_workflows"],
        "missing_inputs": list(dict.fromkeys(missing)),
        "warnings": warnings,
    }


def validate_external_model_output(model_key: str, structured_outputs: dict[str, Any]) -> dict[str, Any] | None:
    if model_key in MODEL_PROFILES:
        recommended = {
            "SPIN": ["substance_record_snapshot", "transformation_pathway", "spin_database_version"],
            "MACRO": ["scenario", "model_version", "groundwater_or_drainage_endpoint", "run_log_reference"],
            "GREATER": ["basin_id", "river_reach_concentrations", "catchment_pec_distribution", "database_version"],
            "PWC": ["model_version", "scenario_file_version", "surface_water_concentration", "sediment_concentration", "groundwater_concentration", "raw_output_archive"],
            "PRZM": ["model_version", "runoff_load", "erosion_load", "leaching_flux", "raw_output_archive"],
            "AGDRIFT": ["model_version", "off_site_deposition_fraction", "downwind_deposition_curve", "raw_output_archive"],
            "TERRPLANT": ["model_version", "terrestrial_plant_risk_quotient", "raw_output_archive"],
            "TREX": ["model_version", "avian_dietary_concentration", "avian_risk_quotient", "mammalian_risk_quotient", "raw_output_archive"],
            "BEEREX": ["model_version", "contact_risk_quotient", "oral_risk_quotient", "raw_output_archive"],
            "CHEMSTEER": ["model_version", "environmental_releases", "worker_inhalation_exposure", "worker_dermal_exposure", "raw_output_archive"],
            "CEM": ["model_version", "product_or_article_category", "consumer_inhalation_exposure", "consumer_dermal_exposure", "consumer_ingestion_exposure", "raw_output_archive"],
            "EFAST": ["model_version", "legacy_use_justification", "release_or_use_scenario", "general_population_exposure", "raw_output_archive"],
        }[model_key]
    else:
        # Fallback for every genuinely externally-managed model outside the
        # hand-curated set above (PEARL, PELMO, SWASH, TOXSWA, EXAMS, EPIE,
        # SIMPLEBOX, EPI_SUITE, ...): its own adapter contract's expected_outputs
        # becomes the completeness requirement, so output-completeness is never
        # silently absent for an official model just because it lacks a
        # hand-picked recommended list. Native EnviroChem screens (execution_mode
        # starting with "native") compute inline and are excluded -- they never
        # go through a genuine-execution import/review gate.
        from .adapters import ADAPTER_CONTRACTS  # deferred: adapters.py imports MODEL_PROFILES from this module

        contract = ADAPTER_CONTRACTS.get(model_key)
        if contract is None or str(contract.get("execution_mode", "")).startswith("native"):
            return None
        recommended = contract["expected_outputs"]
    missing = [key for key in recommended if key not in structured_outputs or _unresolved(structured_outputs.get(key))]
    return {
        "recommended_structured_outputs": recommended,
        "missing_recommended_outputs": missing,
        "review_required": bool(missing),
        "note": "Missing recommended fields do not erase the raw-output record; they remain explicit scientific-review items.",
    }


def integration_catalog() -> list[dict[str, Any]]:
    rows = []
    for key, profile in MODEL_PROFILES.items():
        configured_path = settings.external_model_path(key)
        configured = str(configured_path) if configured_path else None
        candidate = Path(configured or profile["default_path"]) if (configured or profile["default_path"]) else None
        rows.append({
            "key": key,
            **{name: value for name, value in profile.items() if name != "input_template"},
            "configured_path": str(candidate) if candidate else None,
            "path_exists": candidate.exists() if candidate else False,
            "configured_by_environment": bool(configured),
            "input_template": profile["input_template"],
            "execution_bridge": external_tool_status(key) if key in EPA_EXECUTION_MODEL_KEYS else {
                "supported": False,
                "configuration_state": "managed_handoff_only",
                "execution_ready": False,
                "default_route": "manual_official_execution_and_hashed_import",
                "missing_requirements": ["No controlled local-process bridge is defined for this model"],
            },
        })
    return rows


def integration_profile(model_key: str) -> dict[str, Any] | None:
    return next((row for row in integration_catalog() if row["key"] == model_key), None)
