from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .external_models import MODEL_PROFILES, validate_external_model_inputs


ADAPTER_CONTRACTS: dict[str, dict[str, Any]] = {
    "SIMPLETREAT": {
        "execution_mode": "native_and_adapter",
        "required_inputs": [
            "molecular_weight_g_mol", "vapour_pressure_pa", "water_solubility_mg_l",
            "log_kow_or_partition_data", "biodegradation_inputs", "influent_mass_or_concentration",
            "wwtp_flow_m3_day",
        ],
        "expected_outputs": ["effluent", "sludge", "air", "degradation"],
        "workflow_steps": [
            "validate identity and property provenance", "prepare wastewater influent",
            "run native screen or authorised executable", "import compartment fractions",
            "check mass-balance closure", "review and lock output",
        ],
        "accepted_output_formats": ["json", "csv", "txt", "xlsx"],
        "redistribution_note": "Native screening calculations may be bundled. External executables remain version- and licence-controlled.",
    },
    "ACTIVITY_SIMPLETREAT": {
        "execution_mode": "native",
        "required_inputs": [
            "molecular_weight_g_mol", "pka_and_ionisation_type", "log_kow_or_partition_data",
            "sewage_solids_partitioning_inputs", "biodegradation_method", "influent_mass_or_concentration",
        ],
        "expected_outputs": ["effluent", "primary_sludge", "secondary_sludge", "air", "degradation"],
        "workflow_steps": [
            "validate ionisation inputs", "prepare species-specific influent", "solve treatment mass balance",
            "check closure", "review and lock output",
        ],
        "accepted_output_formats": ["json", "csv", "xlsx"],
        "redistribution_note": "EnviroChem stores the equation set, input assumptions, output fractions and audit hash.",
    },
    "SIMPLEBOX": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "regional_emissions_by_compartment", "molecular_weight_and_temperature",
            "vapour_pressure_or_henry_data", "partition_coefficients_and_ionisation",
            "compartment_specific_degradation_rates", "landscape_and_scale_settings",
        ],
        "expected_outputs": [
            "air_concentration", "freshwater_concentration", "marine_concentration",
            "soil_concentrations", "sediment_concentrations", "intermedia_fluxes",
        ],
        "workflow_steps": [
            "verify the SimpleBox version and landscape database", "map reviewed emissions and substance properties",
            "prepare the model input workbook or package", "execute the authorised local model",
            "capture original outputs and settings", "parse compartment concentrations and fluxes",
            "review applicability and lock the result",
        ],
        "accepted_output_formats": ["xlsx", "xlsm", "csv", "txt", "zip"],
        "redistribution_note": "SimpleBox remains an official external RIVM model. EnviroChem manages a versioned input/output workflow and does not label its native multimedia screen as SimpleBox output.",
    },
    "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN": {
        "execution_mode": "native_research_screen",
        "required_inputs": [
            "emissions_by_compartment", "compartment_volumes_and_solid_densities",
            "compartment_half_lives", "advective_loss_rates", "reviewed_intermedia_transfer_rates",
        ],
        "expected_outputs": [
            "compartment_masses", "environmental_concentrations", "intermedia_fluxes", "mass_balance",
        ],
        "workflow_steps": [
            "validate media, units and terminal losses", "assemble the directed transfer matrix",
            "solve the steady-state mass balance", "report concentrations in medium-specific units",
            "check closure and conditioning", "review SimpleBox input readiness and lock output",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "Transparent native first-order mass-balance screen. It is not an execution or reproduction of the SimpleBox fugacity and landscape parameterisation.",
    },
    "EPI_SUITE": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "confirmed_structure_and_identity", "measured_property_overrides_with_provenance",
            "selected_epi_suite_modules", "model_version_and_execution_settings",
        ],
        "expected_outputs": [
            "physical_chemical_estimates", "biowin_outputs", "hydrolysis_and_atmospheric_estimates",
            "bcfbaf_outputs", "level_iii_fugacity", "applicability_warnings",
        ],
        "workflow_steps": [
            "verify EPI Suite 4.11 installation", "prepare the structure and reviewed overrides",
            "execute selected modules", "capture the complete text output",
            "parse each estimate with its model name and version", "store estimates as unselected evidence candidates",
            "review applicability before any modelling value is locked",
        ],
        "accepted_output_formats": ["txt", "csv", "zip"],
        "redistribution_note": "EnviroChem stores EPI Suite estimates as modelled evidence with explicit module/version provenance; estimates never override measured data silently.",
    },
    "SPIN": {
        "execution_mode": "managed_dependency_workspace",
        "required_inputs": [
            "substance_identity", "substance_properties", "transformation_pathway",
            "host_model_targets", "database_version",
        ],
        "expected_outputs": [
            "substance_record_snapshot", "transformation_pathway", "host_model_readiness",
            "spin_database_version", "record_provenance_hash",
        ],
        "workflow_steps": [
            "verify the local FOCUS SPIN 4.4 installation and database version",
            "confirm that no other SPIN-connected host application has the shared database open",
            "map reviewed identity, fate properties and parent/metabolite pathway",
            "enter or review the record in standalone SPIN where host fields are disabled",
            "capture a versioned substance-record and transformation-pathway snapshot",
            "verify readiness for each selected PEARL, SWASH, MACRO or TOXSWA host workflow",
            "review and lock the dependency record without representing it as a fate simulation",
        ],
        "accepted_output_formats": ["json", "csv", "mdb", "zip", "txt"],
        "redistribution_note": "SPIN is the official FOCUS substance-property and transformation-pathway repository, not a simulation model. EnviroChem manages a reviewed record snapshot and does not redistribute the executable or user database.",
    },
    "PEARL": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "application_pattern", "soil_dt50", "koc_or_kd", "freundlich_exponent",
            "vapour_pressure", "water_solubility", "crop_and_scenario", "weather_scenario",
            "plant_uptake_coefficient_tscf",
        ],
        "expected_outputs": ["groundwater_concentration", "soil_profile", "leaching_flux", "passive_plant_uptake_flux"],
        "workflow_steps": [
            "validate FOCUS scenario", "write PEARL input package", "execute authorised local installation",
            "capture logs and raw output", "parse groundwater and profile endpoints", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "prn", "zip"],
        "redistribution_note": "EnviroChem manages inputs and outputs; the authorised PEARL installation is supplied separately where required.",
    },
    "ENVIROCHEM_TOXSWA_PROCESS_SCREEN": {
        "execution_mode": "native_research_screen",
        "required_inputs": [
            "waterbody_geometry_and_flow", "loading_route_and_rate", "water_and_sediment_dt50",
            "koc_or_kd", "sediment_properties", "suspended_solids", "aqueous_diffusion_coefficient",
        ],
        "expected_outputs": [
            "global_max_pecsw", "global_max_pecsed", "twaecsw", "twaecsed",
            "water_and_sediment_mass_balance", "time_series", "official_input_readiness",
        ],
        "workflow_steps": [
            "route chemical group to an explicit release mode", "validate visible geometry and fate inputs",
            "solve segmented water transport and water-sediment exchange", "calculate peak and moving-TWA endpoints",
            "check mass-balance closure", "flag applicability and official-FOCUS boundary",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "Native transparent process screen only. It must not be represented as execution of the official FOCUS_TOXSWA kernel.",
    },
    "TOXSWA": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "contaminant_group", "spin_substance_record", "swash_surface_water_scenario", "application_pattern",
            "drift_deposition", "macro_m2t_or_przm_p2t_when_applicable",
            "water_and_sediment_dt50", "freundlich_sorption_parameters",
            "molar_mass_vapour_pressure_solubility_diffusion", "metabolite_scheme_if_applicable",
        ],
        "expected_outputs": [
            "global_max_pecsw", "global_max_pecsed", "twaecsw", "twaecsed",
            "water_mass_balance", "sediment_mass_balance", "time_series_if_requested"
        ],
        # time_series_if_requested is conditional on the operator actually
        # requesting a time-series export -- it must not block acceptance of a
        # run where no time series was requested. See "optional_outputs" in
        # validate_external_model_output()'s fallback for models outside
        # MODEL_PROFILES.
        "optional_outputs": ["time_series_if_requested"],
        "workflow_steps": [
            "verify SPIN, SWASH and TOXSWA versions", "prepare the official Step 3 project in SWASH",
            "run MACRO drainage or PRZM runoff/erosion when required", "export application edits and drift values",
            "execute authorised local FOCUS_TOXSWA installation", "capture .txw .sum .out and lateral-entry artefacts",
            "parse peak and TWA endpoints", "scientifically review and lock output",
        ],
        "accepted_output_formats": ["sum", "txt", "csv", "out", "txw", "m2t", "p2t", "zip"],
        "redistribution_note": "EnviroChem manages and audits the official external workflow. For non-pesticide chemical groups, applying FOCUS_TOXSWA concepts is labelled adapted/research unless the receiving authority explicitly accepts that use.",
    },
    "GREATER": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "basin_database", "georeferenced_river_network", "reach_hydrology", "point_sources",
            "emission_loads", "wwtp_removal", "in_stream_fate", "simulation_settings",
        ],
        "expected_outputs": [
            "river_reach_concentrations", "catchment_pec_distribution", "sediment_concentrations", "spatial_risk",
        ],
        "workflow_steps": [
            "verify GREAT-ER 4 deployment, PostgreSQL service and authorised basin database",
            "record basin identity, vintage, coordinate reference system and data-rights basis",
            "map reviewed source loads and treatment assumptions",
            "prepare the georeferenced simulation", "execute the external model",
            "capture database, configuration and raw outputs", "parse reach-level PEC distributions",
            "compare against monitoring where available and lock the reviewed result",
        ],
        "accepted_output_formats": ["csv", "json", "sql", "zip", "shp", "gpkg"],
        "redistribution_note": "GREAT-ER 4 is described as open-source software, but deployment and basin datasets remain separate prerequisites. The native catchment screen is intentionally simpler and is never represented as GREAT-ER output.",
    },
    "EPIE": {
        "execution_mode": "managed_research_adapter",
        "required_inputs": [
            "compound_specific_pharmaceutical_use", "population_and_wwtp_locations", "wwtp_removal_and_excretion",
            "european_hydrology_and_river_routing", "in_stream_fate", "model_method_and_data_version",
        ],
        "expected_outputs": [
            "spatial_surface_water_pec", "catchment_distribution", "monitoring_comparison", "uncertainty",
        ],
        "workflow_steps": [
            "confirm access to the method, code and required datasets", "map pharmaceutical influent and treatment outputs",
            "prepare the spatial exposure run", "execute the authorised research workflow",
            "capture inputs, data vintages and raw outputs", "compare predictions with monitoring",
            "label regulatory status and lock the reviewed result",
        ],
        "accepted_output_formats": ["csv", "netcdf", "geotiff", "gpkg", "json", "zip"],
        "redistribution_note": "ePiE is a published pharmaceutical exposure model, not bundled code. EnviroChem records method/data access and never implies an official execution from its native river screen.",
    },
    "ENVIROCHEM_CATCHMENT_RIVER_NETWORK": {
        "execution_mode": "native_research_screen",
        "required_inputs": [
            "directed_river_segments", "segment_flow_and_travel_time", "water_dt50_or_loss_rate",
            "wwtp_effluent_concentrations_and_flows_or_direct_loads", "aquatic_pnec_if_risk_is_required",
        ],
        "expected_outputs": [
            "segment_pecs", "attenuated_loads", "pnec_exceedance", "network_mass_balance",
        ],
        "workflow_steps": [
            "validate the acyclic river network", "convert WWTP concentrations and flows to daily loads",
            "route loads in topological order", "apply first-order in-stream attenuation",
            "calculate inlet, mean and outlet PECs", "check network closure and PNEC exceedance",
            "review GREAT-ER or ePiE refinement readiness and lock output",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "Transparent native point-source river-routing screen. Hydrodynamic, geospatial and official model refinements remain separate workflows.",
    },
    "PELMO": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "application_pattern", "soil_dt50", "koc_or_kd", "crop_and_scenario",
            "weather_scenario", "metabolite_scheme_if_applicable",
        ],
        "expected_outputs": ["groundwater_concentration", "soil_residue", "leaching_flux"],
        "workflow_steps": [
            "validate FOCUS scenario", "write PELMO input package", "execute authorised local installation",
            "capture logs and raw output", "parse groundwater and residue endpoints", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "out", "zip"],
        "redistribution_note": "EnviroChem stores the input deck and result archive without assuming redistribution rights for the executable.",
    },
    "MACRO": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "execution_route", "spin_substance_record", "focus_scenario", "crop_and_application",
            "soil_profile_and_hydrology", "degradation_and_sorption", "weather_and_run_settings",
        ],
        "expected_outputs": ["drainage_concentration", "groundwater_concentration", "soil_profile", "m2t_lateral_entry", "run_log"],
        "workflow_steps": [
            "verify FOCUS_MACRO 5.5.4a and its MACRO 5.2 model/scenario database",
            "validate the SPIN substance record and groundwater or SWASH drainage route",
            "write the official scenario input package", "execute the authorised local installation",
            "capture batch, parameter, log and binary outputs", "generate and retain .m2t when TOXSWA drainage input is required",
            "parse drainage, groundwater and profile endpoints", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "par", "log", "bin", "m2t", "zip"],
        "redistribution_note": "EnviroChem records the exact FOCUS_MACRO package, MACRO model, scenario database and route. It does not reproduce the dual-domain solver or redistribute the official installation.",
    },
    "PRZM": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "application_pattern", "soil_and_crop_scenario", "weather_series", "soil_dt50",
            "koc_or_kd", "runoff_and_erosion_parameters", "root_zone_parameters",
        ],
        "expected_outputs": ["runoff_load", "erosion_load", "leaching_flux"],
        "workflow_steps": [
            "validate PRZM scenario", "write PRZM input package", "execute configured installation",
            "capture logs and time series", "parse runoff erosion and leaching endpoints", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "out", "zip"],
        "redistribution_note": "PRZM may be used as a managed or legacy-compatible adapter depending on the regulatory workflow.",
    },
    "EXAMS": {
        "execution_mode": "legacy_adapter",
        "required_inputs": [
            "waterbody_scenario", "loading_time_series", "hydrolysis_photolysis_biodegradation",
            "water_sediment_partitioning", "volatilisation_inputs",
        ],
        "expected_outputs": ["water_concentration", "sediment_concentration", "persistence"],
        "workflow_steps": [
            "validate legacy EXAMS workflow", "prepare input and loading files", "execute configured legacy installation",
            "capture logs and raw output", "parse water and sediment endpoints", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "out", "zip"],
        "redistribution_note": "The adapter is retained for reproducibility and historical assessments; every run is clearly labelled legacy.",
    },
    "PWC": {
        "execution_mode": "managed_adapter",
        "required_inputs": [
            "contaminant_group", "application_pattern", "pwc3_us_scenario", "soil_and_crop_inputs", "weather_series",
            "soil_dt50", "koc_or_kd", "aquatic_fate_inputs", "groundwater_and_waterbody_configuration",
        ],
        "expected_outputs": ["surface_water_concentration", "sediment_concentration", "groundwater_concentration", "drinking_water_endpoints", "batch_results"],
        "workflow_steps": [
            "verify the current PWC3 build and scenario database", "validate the US pesticide scenario",
            "write the PWC3 project and optional batch package", "execute the configured installation",
            "capture logs and complete raw output", "parse surface-water, sediment, groundwater and drinking-water endpoints",
            "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "zip"],
        "redistribution_note": "EnviroChem manages the current EPA PWC3 workflow and preserves the exact software/scenario version. Legacy PWC, PRZM and EXAMS records remain reproducible but are not presented as current PWC3 runs.",
    },
    "AGDRIFT": {
        "execution_mode": "managed_adapter",
        "required_inputs": ["contaminant_group", "application_parameters", "meteorological_conditions", "buffer_and_geometry"],
        "expected_outputs": ["off_site_deposition_fraction", "downwind_deposition_curve", "model_version", "raw_output_archive"],
        "workflow_steps": [
            "select the applicable AgDRIFT/AGDISP tier and application scenario", "enter application, meteorological and buffer/geometry inputs",
            "execute the configured installation", "capture the deposition curve and off-site fraction", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv", "pdf"],
        "redistribution_note": "EnviroChem does not reproduce or modify AgDRIFT/AGDISP; execution occurs in an authorised external installation.",
    },
    "TERRPLANT": {
        "execution_mode": "managed_adapter",
        "required_inputs": ["contaminant_group", "application_parameters", "runoff_and_drift_inputs", "toxicity_endpoints"],
        "expected_outputs": ["terrestrial_plant_risk_quotient", "model_version", "raw_output_archive"],
        "workflow_steps": [
            "enter application rate/method and distance to habitat", "enter seedling emergence and vegetative vigour endpoints",
            "execute the configured installation", "capture the terrestrial plant risk quotient", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv"],
        "redistribution_note": "EnviroChem does not reproduce or modify TerrPlant; execution occurs in an authorised external installation.",
    },
    "TREX": {
        "execution_mode": "managed_adapter",
        "required_inputs": ["contaminant_group", "application_parameters", "dietary_inputs", "toxicity_endpoints"],
        "expected_outputs": ["avian_dietary_concentration", "avian_risk_quotient", "mammalian_risk_quotient", "model_version", "raw_output_archive"],
        "workflow_steps": [
            "enter application rate and number of applications", "enter dietary food-item category and body-weight inputs",
            "enter avian and mammalian toxicity endpoints", "execute the configured installation", "capture dietary concentration and risk quotients", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv"],
        "redistribution_note": "EnviroChem does not reproduce or modify T-REX; execution occurs in an authorised external installation.",
    },
    "BEEREX": {
        "execution_mode": "managed_adapter",
        "required_inputs": ["contaminant_group", "application_parameters", "exposure_route_inputs", "toxicity_endpoints"],
        "expected_outputs": ["contact_risk_quotient", "oral_risk_quotient", "model_version", "raw_output_archive"],
        "workflow_steps": [
            "enter application rate/method and crop bee-attractiveness basis", "enter contact and oral bee toxicity endpoints",
            "execute the configured installation", "capture contact and oral risk quotients", "review and lock output",
        ],
        "accepted_output_formats": ["txt", "csv"],
        "redistribution_note": "EnviroChem does not reproduce or modify BeeREX; execution occurs in an authorised external installation.",
    },
    "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN": {
        "execution_mode": "native_research_screen",
        "required_inputs": [
            "food_intake_rate_g_day", "body_weight_g", "application_rate_kg_ha",
            "residue_unit_dose_mg_kg", "avian_or_mammalian_toxicity_endpoint",
        ],
        "expected_outputs": [
            "acute_dietary_ter", "reproductive_dietary_ter", "fish_secondary_poisoning_ter", "earthworm_secondary_poisoning_ter",
        ],
        "workflow_steps": [
            "confirm the reviewer-supplied FIR/BW/RUD for the assessed food item(s)",
            "compute the screening or Tier 1 daily dose", "apply fTWA for the reproductive exposure when relevant",
            "compute acute and reproductive TER against the guidance's own thresholds",
            "when log Kow >= 3, compute the fish-eating secondary-poisoning TER",
            "when a soil concentration and Koc are available, compute the earthworm-eating secondary-poisoning TER",
            "scientist reviews the endpoint selection and any Tier 2/3 refinement",
        ],
        "accepted_output_formats": ["json"],
        "redistribution_note": "Transparent native research screen implementing EFSA (2023) Journal 21(2):7790's own dietary/fish-eating formulas. The earthworm-eating pathway is sourced to ECHA's REACH Guidance Chapter R.16 (2012), not the EFSA (2023) text itself, which was never obtained -- see eu_birds_mammals.py's own module docstring for the exact boundary. It is not an official EFSA calculator tool and does not embed the guidance's Annex B Generic Model Species or crop-deposition-value tables, and benthic-invertebrate secondary poisoning is not implemented.",
    },
    "ENVIROCHEM_EU_BEES_SCREEN": {
        "execution_mode": "native_research_screen",
        "required_inputs": [
            "application_rate_g_ha", "spray_direction", "ld50_contact_ug_bee", "ld50_oral_ug_bee",
            "lc50_oral_ug_bee_per_day", "noec_larvae_ug_per_developmental_period",
        ],
        "expected_outputs": [
            "hq_contact", "etr_acute_adult_oral", "etr_chronic_adult_oral", "etr_larvae", "etr_hpg",
        ],
        "workflow_steps": [
            "confirm the spray direction (downwards ground/boom vs. sideward/upwards air-assisted/orchard) so the correct trigger and SV shortcut values apply",
            "compute the contact HQ and the acute/chronic adult oral and larval ETRs against the guidance's own Tier 1 triggers",
            "when the adult chronic toxicity study showed a hypopharyngeal-gland effect, also supply the HPG NOEC and compute the HPG ETR",
            "scientist reviews the endpoint selection and any higher-tier refinement",
        ],
        "accepted_output_formats": ["json"],
        "redistribution_note": "Transparent native research screen implementing the EFSA (2013) Journal 11(7):3295 bee guidance's own Section 3.1.2 Tier 1 spray-screening formulas. It is not an official EFSA calculator tool. Spray applications to honey bees only -- granular/seed-treatment routes and bumble bee/solitary bee assessments are not implemented. A 2023 revision of this guidance exists with a different contact-exposure formulation and updated trigger values that were not confirmed this session and are not what this screen implements -- see eu_bees.py's own module docstring.",
    },
    "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN": {
        "execution_mode": "native_research_screen",
        "required_inputs": [
            "confirmed_identity", "chemical_throughput_kg_day", "operating_days_year",
            "release_events", "worker_tasks_or_explicit_gap", "source_provenance",
        ],
        "expected_outputs": [
            "media_specific_release_mass", "managed_waste_transfers",
            "worker_inhalation_dose", "worker_dermal_dose", "groundwater_leaching_screen", "mass_balance",
            "conventional_assessment_completeness",
        ],
        "workflow_steps": [
            "confirm the chemical identity", "select a published ESD or explicitly enable a reference-only source",
            "define non-overlapping release events on one throughput basis", "apply controls and route captured waste",
            "calculate measured-air or well-mixed worker exposure", "screen soil-to-groundwater leaching when soil release occurs",
            "check mass balance and missing assessment domains",
            "scientist reviews assumptions before external-model refinement",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "Transparent native research screen. It is not ChemSTEER, CEM, E-FAST or an EPA-endorsed calculation.",
    },
    "CHEMSTEER": {
        "execution_mode": "managed_external_adapter",
        "required_inputs": [
            "chemical_identity_and_properties", "production_or_import_volume",
            "process_and_use_description", "days_and_sites", "release_activity_parameters",
            "engineering_controls", "worker_activity_parameters", "esd_and_parameter_provenance",
        ],
        "expected_outputs": [
            "environmental_releases", "worker_inhalation_exposure", "worker_dermal_exposure",
            "engineering_control_basis", "model_version", "raw_output_archive",
        ],
        "workflow_steps": [
            "verify the authorised ChemSTEER installation and version", "map a reviewed EPA ESD and scenario inputs",
            "export a versioned input manifest", "execute ChemSTEER outside EnviroChem",
            "import complete raw and structured outputs", "compare with the native transparent screen",
            "scientist reviews and locks the result",
        ],
        "accepted_output_formats": ["txt", "csv", "xlsx", "zip"],
        "redistribution_note": "External EPA executable only. EnviroChem does not bundle, modify, adapt or imply ownership of ChemSTEER.",
    },
    "CEM": {
        "execution_mode": "managed_external_adapter",
        "required_inputs": [
            "chemical_identity_and_properties", "product_or_article_category",
            "chemical_weight_fraction", "use_frequency_and_duration", "emission_model_selection",
            "inhalation_dermal_ingestion_models", "population_and_lifestage_factors",
            "parameter_provenance",
        ],
        "expected_outputs": [
            "consumer_inhalation_exposure", "consumer_dermal_exposure",
            "consumer_ingestion_exposure", "population_and_lifestage_results",
            "model_version", "raw_output_archive",
        ],
        "workflow_steps": [
            "verify the authorised CEM installation and version", "select a reviewed product or article category",
            "record emission and exposure-model choices", "export a versioned input manifest",
            "execute CEM outside EnviroChem", "import complete raw and structured outputs",
            "scientist reviews population, life-stage and route completeness",
        ],
        "accepted_output_formats": ["txt", "csv", "xlsx", "zip"],
        "redistribution_note": "External EPA executable only. EnviroChem does not bundle, modify, adapt or imply ownership of CEM.",
    },
    "EFAST": {
        "execution_mode": "managed_legacy_adapter",
        "required_inputs": [
            "chemical_identity_and_properties", "release_or_use_scenario",
            "air_water_or_landfill_inputs", "consumer_and_population_inputs",
            "executable_version", "legacy_use_justification", "parameter_provenance",
        ],
        "expected_outputs": [
            "surface_water_exposure", "air_exposure", "landfill_release",
            "consumer_exposure", "general_population_exposure", "model_version",
            "raw_output_archive",
        ],
        "workflow_steps": [
            "confirm that legacy E-FAST is appropriate", "verify the authorised 2014 installation",
            "record scenario and exposure-route selections", "export a versioned input manifest",
            "execute E-FAST outside EnviroChem", "import complete raw and structured outputs",
            "label the result legacy and scientist-review all decisions",
        ],
        "accepted_output_formats": ["txt", "csv", "xlsx", "zip"],
        "redistribution_note": "Legacy external EPA executable only. EnviroChem does not bundle, modify, adapt or create a derivative of E-FAST.",
    },

"SWASH": {
    "execution_mode": "managed_adapter",
    "required_inputs": [
        "spin_substance_record", "crop_and_focus_scenarios", "application_pattern",
        "entry_routes", "macro_or_przm_configuration", "toxswa_configuration",
    ],
    "expected_outputs": ["focus_projects", "spray_drift_inputs", "macro_przm_links", "toxswa_run_set"],
    "workflow_steps": [
        "verify SPIN and SWASH installation", "create and validate the FOCUS project",
        "calculate drift and prepare MACRO or PRZM entries", "save and export application edits",
        "launch TOXSWA after upstream runs", "capture project database and audit manifest",
    ],
    "accepted_output_formats": ["mdb", "txt", "zip", "m2t", "p2t", "txw"],
    "redistribution_note": "SWASH is an official external orchestration shell. EnviroChem manages installation checks and project artefacts but does not redistribute or rebrand the executable.",
},
"ENVIROCHEM_BIOSOLIDS_LAND_APPLICATION": {
    "execution_mode": "native",
    "required_inputs": [
        "chemical_mass_or_biosolids_concentration", "fraction_land_applied", "land_area",
        "soil_depth_and_density", "application_schedule", "soil_dt50_or_no_degradation_assumption",
    ],
    "expected_outputs": ["biosolids_concentration", "annual_loading", "soil_pec", "accumulation_series"],
    "workflow_steps": [
        "link WWTP sludge mass or measured biosolids concentration", "apply storage loss if supported",
        "calculate dry-mass loading", "mix into explicit soil mass", "simulate repeated annual applications",
        "route leaching and runoff screens", "review regulatory context and lock output",
    ],
    "accepted_output_formats": ["json", "csv"],
    "redistribution_note": "Transparent native calculation. Jurisdiction-specific biosolids legal controls remain separate from the chemical fate calculation.",
},
    "ENVIROCHEM_DUAL_WASTEWATER_IRRIGATION": {
        "execution_mode": "native_and_adapter",
        "required_inputs": [
            "effluent_concentration", "irrigation_rate", "irrigated_area",
            "soil_depth_and_density", "soil_dt50_or_rate", "kd_or_koc",
        ],
        "expected_outputs": [
            "annual_irrigation_loading", "soil_plateau_with_degradation",
            "soil_plateau_without_degradation", "surface_water_screen",
            "eu_adapter_manifests", "us_adapter_manifests", "framework_comparison",
        ],
        "workflow_steps": [
            "validate wastewater effluent source", "resolve consistent irrigation rate and area",
            "calculate continuous soil input and degradation/leaching losses",
            "prepare EU FOCUS manifests", "prepare US PWC/PRZM/EXAMS manifests",
            "compare framework assumptions and outputs", "review and lock result",
        ],
        "accepted_output_formats": ["json", "csv", "pdf"],
        "redistribution_note": "The native screen is bundled. External EU and US executables are managed through versioned local adapters subject to their licences.",
    },
    "ENVIROCHEM_SOIL_SCREEN": {
        "execution_mode": "native",
        "required_inputs": [
            "application_mass", "application_frequency", "soil_mixing_depth", "soil_bulk_density",
            "soil_dt50", "interception_or_incorporation_fraction",
        ],
        "expected_outputs": ["soil_pec", "plateau_concentration", "annual_accumulation"],
        "workflow_steps": [
            "validate units and scenario", "calculate initial soil concentration", "simulate repeated application and decay",
            "report plateau and annual series", "review and lock output",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "This is a transparent native EnviroChem calculation with versioned equations.",
    },
    "ENVIROCHEM_PLANT_UPTAKE": {
        "execution_mode": "native",
        "required_inputs": [
            "soil_or_water_concentration", "crop", "root_zone_depth", "transpiration_or_uptake_factor",
            "chemical_speciation", "plant_growth_and_dilution", "harvest_interval",
        ],
        "expected_outputs": ["root_concentration", "shoot_concentration", "edible_tissue_concentration"],
        "workflow_steps": [
            "validate crop and chemical applicability", "select uptake model", "calculate root and shoot transfer",
            "apply growth dilution and harvest timing", "review uncertainty and lock output",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "The native module exposes each equation and distinguishes screening predictions from measured crop-residue evidence.",
    },
    "ENVIRODESIGN_BIOWIN34_ATTRIBUTION": {
        "execution_mode": "native_research_screen",
        "required_inputs": ["smiles", "confirmed_identity"],
        "expected_outputs": ["biowin3_score", "biowin4_score", "fragment_contributions", "structure_alerts", "design_hypotheses"],
        "workflow_steps": [
            "parse and canonicalise structure", "match reconstructed SMARTS terms", "calculate explicit contribution trace",
            "generate non-fitted structure inventory", "separate attribution from causal claims", "store warnings and audit record",
        ],
        "accepted_output_formats": ["json", "svg", "csv"],
        "redistribution_note": "Uses an open approximate BIOWIN 3/4 reconstruction supplied as research inventory. It is not EPA source code or regulatory-equivalent output.",
    },
    "ENVIRODESIGN_PATHWAY_RETENTION": {
        "execution_mode": "native_manual_import",
        "required_inputs": ["parent_smiles", "transformation_products", "observed_or_predicted_status", "matrix", "provenance"],
        "expected_outputs": ["mcs_retention", "retained_fragments", "retained_structure_alerts", "motif_retention_summary"],
        "workflow_steps": [
            "validate parent and product structures", "retain matrix and provenance", "calculate maximum common substructure",
            "test feature retention", "summarise repeatedly retained motifs", "label hypotheses and licensing boundary",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "Direct commercial embedding of external pathway databases is not included. The native workflow analyses user-imported records and preserves provenance.",
    },
    "BIOTRANSFORMER_ENVMICRO": {
        "execution_mode": "remote_api_development_evaluation",
        "required_inputs": ["confirmed_parent_smiles", "parent_name", "one_to_three_generations"],
        "expected_outputs": ["predicted_products", "substrate_product_edges", "reaction_annotations", "provider_query_provenance"],
        "workflow_steps": [
            "submit one confirmed parent to ENVMICRO", "poll the provider query", "normalise products into the provider-neutral pathway graph",
            "mark every product as predicted", "scientist reviews structures and reaction edges", "fit formation and degradation kinetics separately",
        ],
        "accepted_output_formats": ["json"],
        "redistribution_note": "Interim academic/development integration. BioTransformer ENVMICRO uses enviPath/EAWAG-derived data; written commercial permission is required before production use.",
    },
    "ENVIPATH_ENVMICRO": {
        "execution_mode": "remote_api_development_evaluation",
        "required_inputs": ["confirmed_parent_smiles", "parent_name", "package_or_search_scope"],
        "expected_outputs": ["curated_or_predicted_products", "substrate_product_edges", "reaction_annotations", "provider_query_provenance"],
        "workflow_steps": [
            "search enviPath's curated packages for the parent, or submit it for enviPath's own rule-based prediction",
            "normalise results into the provider-neutral pathway graph", "label curated results as database-curated and predicted results as model-predicted",
            "scientist reviews structures and reaction edges", "fit formation and degradation kinetics separately",
        ],
        "accepted_output_formats": ["json"],
        "redistribution_note": "Interim academic/development integration. envipath.org states it is free for academic and non-commercial use only; written commercial permission is required before production use.",
    },
    "ENVIRODESIGN_CANDIDATE_COMPARISON": {
        "execution_mode": "native_user_supplied_candidates",
        "required_inputs": ["original_smiles", "candidate_smiles", "protected_substructures"],
        "expected_outputs": ["score_deltas", "descriptor_tradeoffs", "protected_substructure_check", "comparison_table"],
        "workflow_steps": [
            "validate candidate structures", "verify protected SMARTS in original", "run identical structural screen for every candidate",
            "calculate score and descriptor deltas", "flag multi-objective tradeoffs", "avoid asserting a single winner",
        ],
        "accepted_output_formats": ["json", "csv"],
        "redistribution_note": "Candidates are supplied by the user. The module does not claim preserved efficacy, safety or experimental biodegradability.",
    },
}

for _profile_key, _profile in MODEL_PROFILES.items():
    if _profile_key in ADAPTER_CONTRACTS:
        ADAPTER_CONTRACTS[_profile_key]["input_template"] = _profile["input_template"]
        ADAPTER_CONTRACTS[_profile_key]["official_context"] = {
            "official_name": _profile["name"],
            "official_version": _profile["official_version"],
            "role": _profile["role"],
            "is_simulation_model": _profile["is_simulation_model"],
            "official_page": _profile["official_page"],
            "prerequisites": _profile["prerequisites"],
            "known_constraints": _profile["known_constraints"],
        }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def prepare_workflow_manifest(payload: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    contract = ADAPTER_CONTRACTS[model["key"]]
    supplied = payload.get("input_data") or {}

    def unresolved(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, tuple, set)):
            return len(value) == 0
        if isinstance(value, dict):
            if not value:
                return True
            if str(value.get("status", "")).lower() in {"required", "missing", "unresolved"}:
                return True
        return False

    missing = [
        key for key in contract["required_inputs"]
        if key not in supplied or unresolved(supplied.get(key))
    ]
    model_specific = validate_external_model_inputs(model["key"], supplied)
    if model_specific:
        missing = list(dict.fromkeys([*missing, *model_specific["missing_inputs"]]))
    manifest = {
        "manifest_version": "ENVIROCHEM_MODEL_WORKFLOW_1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "key": model["key"],
            "name": model["name"],
            "implementation": model["implementation"],
            "registry_status": model["status"],
            "domain": model["domain"],
        },
        "assessment": {
            "project_id": payload["project_id"],
            "chemical_id": payload["chemical_id"],
            "jurisdiction": payload["jurisdiction"],
            "tier": payload["tier"],
            "scenario_name": payload["scenario_name"],
        },
        "execution": {
            "mode": contract["execution_mode"],
            "configured_executable_path": payload.get("executable_path"),
            "accepted_output_formats": contract["accepted_output_formats"],
            "redistribution_note": contract["redistribution_note"],
        },
        "model_specific_validation": model_specific,
        "inputs": supplied,
        "required_inputs": contract["required_inputs"],
        "missing_inputs": missing,
        "expected_outputs": contract["expected_outputs"],
        "workflow_steps": contract["workflow_steps"],
    }
    manifest["input_hash"] = sha256_payload({"model_key": model["key"], "inputs": supplied, "assessment": manifest["assessment"]})
    return manifest


def normalise_imported_output(raw_output_text: str | None, structured_outputs: dict[str, Any] | None) -> dict[str, Any]:
    structured = structured_outputs or {}
    if raw_output_text and not structured:
        # Accept simple `key=value` or `key: value` lines as a useful generic import route.
        for line in raw_output_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            separator = "=" if "=" in line else (":" if ":" in line else None)
            if separator is None:
                continue
            key, value = [x.strip() for x in line.split(separator, 1)]
            if not key:
                continue
            try:
                structured[key] = float(value)
            except ValueError:
                structured[key] = value
    record = {
        "raw_output_text": raw_output_text,
        "structured_outputs": structured,
    }
    record["output_hash"] = sha256_payload(record)
    return record
