from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, Any


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    jurisdiction: str = "UK/EU screening"
    purpose: str = "Environmental risk screening"


class IdentityResolveCreate(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    query_mode: Literal["cas", "smiles", "iupac", "product"] = "cas"


class ChemicalIdentityConfirmCreate(BaseModel):
    project_id: int
    candidate: dict[str, Any]
    user_confirmed: bool

    @model_validator(mode="after")
    def require_confirmation(self):
        if not self.user_confirmed:
            raise ValueError("The resolved identity must be explicitly confirmed")
        required = ["preferred_name", "molecular_formula", "molecular_weight_g_mol", "smiles", "inchikey", "identity_hash"]
        missing = [key for key in required if self.candidate.get(key) in {None, ""}]
        if missing:
            raise ValueError("Resolved identity is incomplete: " + ", ".join(missing))
        return self


class ChemicalAssessmentProfileUpsert(BaseModel):
    ionisation_class: Optional[Literal["neutral", "acid", "base"]] = None
    log_kow: Optional[float] = None
    pkaa: Optional[float] = None
    pkab: Optional[float] = None
    water_solubility_mg_l: Optional[float] = Field(default=None, gt=0)
    vapour_pressure_pa: Optional[float] = Field(default=None, ge=0)
    soil_dt50_days: Optional[float] = Field(default=None, gt=0)
    wwtp_biodegradation_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    wwtp_primary_sludge_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    wwtp_secondary_sludge_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    wwtp_volatilisation_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    source_summary: Optional[str] = Field(default=None, max_length=4000)
    provenance: dict[str, Any] = Field(default_factory=dict)
    reviewer_confirmation: bool = False

    @model_validator(mode="after")
    def validate_reviewed_profile(self):
        fractions = [
            self.wwtp_biodegradation_fraction,
            self.wwtp_primary_sludge_fraction,
            self.wwtp_secondary_sludge_fraction,
            self.wwtp_volatilisation_fraction,
        ]
        if all(value is not None for value in fractions) and sum(float(value) for value in fractions) > 1 + 1e-12:
            raise ValueError("WWTP biodegradation, sludge and air fractions cannot sum to more than 1")
        if self.reviewer_confirmation:
            required = {
                "ionisation_class": self.ionisation_class,
                "log_kow": self.log_kow,
                "wwtp_biodegradation_fraction": self.wwtp_biodegradation_fraction,
                "wwtp_primary_sludge_fraction": self.wwtp_primary_sludge_fraction,
                "wwtp_secondary_sludge_fraction": self.wwtp_secondary_sludge_fraction,
                "wwtp_volatilisation_fraction": self.wwtp_volatilisation_fraction,
                "source_summary": self.source_summary,
            }
            missing = [key for key, value in required.items() if value in {None, ""}]
            if self.ionisation_class == "acid" and self.pkaa is None:
                missing.append("pkaa")
            if self.ionisation_class == "base" and self.pkab is None:
                missing.append("pkab")
            if missing:
                raise ValueError("A reviewed profile is missing: " + ", ".join(missing))
        return self


class SourceCreate(BaseModel):
    source_type: str = "journal_article"
    title: str = Field(min_length=2)
    organisation: Optional[str] = None
    publication_year: Optional[int] = Field(default=None, ge=1800, le=2200)
    identifier: Optional[str] = None
    url: Optional[str] = None
    access_date: Optional[str] = None


class EvidenceCreate(BaseModel):
    project_id: int
    chemical_id: int
    source: SourceCreate
    property_code: str = "FATE.SOIL_DT50"
    evidence_type: str = "measured"
    original_value: float = Field(gt=0)
    original_unit: str = "days"
    soil_type: Optional[str] = None
    soil_texture: Optional[str] = None
    soil_ph: Optional[float] = Field(default=None, ge=0, le=14)
    organic_carbon_percent: Optional[float] = Field(default=None, ge=0)
    temperature_c: Optional[float] = Field(default=None, gt=-273.15)
    moisture_percent_whc: Optional[float] = Field(default=None, gt=0)
    kinetic_model: Optional[str] = None
    endpoint_kind: Optional[str] = "DegT50"
    test_guideline: Optional[str] = None
    reliability_score: Optional[int] = Field(default=None, ge=1, le=4)
    representative_group_key: str = Field(min_length=1)
    include_by_default: bool = True
    notes: Optional[str] = None


class EvidenceSourceSearchCreate(BaseModel):
    chemical_name: str = Field(min_length=1, max_length=250)
    cas_number: Optional[str] = None
    source_keys: list[str] = Field(default_factory=lambda: ["pubchem", "europe_pmc"])
    endpoint_codes: list[str] = Field(default_factory=list)
    limit_per_source: int = Field(default=20, ge=1, le=50)
    include_open_access_full_text: bool = True


class EvidenceCandidateImportCreate(BaseModel):
    project_id: int
    chemical_id: int
    candidate: dict[str, Any]
    scientist_reviewed: bool = False
    rights_asserted: bool = False
    reliability_score: Optional[int] = Field(default=None, ge=1, le=4)
    representative_group_key: Optional[str] = None
    review_notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_candidate(self):
        required = ["source_key", "property_code", "value", "unit"]
        missing = [key for key in required if self.candidate.get(key) in {None, ""}]
        if missing:
            raise ValueError(f"Candidate is missing import fields: {', '.join(missing)}")
        return self


class ReachPnecPreviewCreate(BaseModel):
    endpoint_value: float = Field(gt=0, allow_inf_nan=False)
    endpoint_unit: Literal["ng/L", "ug/L", "µg/L", "μg/L", "mg/L", "g/L"]
    endpoint_type: Literal["LC50", "EC50", "NOEC", "EC10"]
    assessment_factor: float = Field(ge=1, allow_inf_nan=False)
    assessment_factor_rationale: str = Field(min_length=10, max_length=4000)
    guidance_reference: str = Field(min_length=5, max_length=500)
    target_compartment: Literal["freshwater"] = "freshwater"


class ReachEvidencePnecCreate(BaseModel):
    critical_evidence_id: int = Field(gt=0)
    assessment_factor: float = Field(ge=1, allow_inf_nan=False)
    assessment_factor_rationale: str = Field(min_length=10, max_length=4000)
    guidance_reference: str = Field(min_length=5, max_length=500)
    target_compartment: Literal["freshwater"] = "freshwater"


class ReachReviewBundleCreate(BaseModel):
    project_id: int = Field(gt=0)
    chemical_id: int = Field(gt=0)
    assessment_profile_id: int = Field(gt=0)
    selected_evidence_ids: list[int] = Field(min_length=1, max_length=100)
    selected_model_run_ids: list[int] = Field(default_factory=list, max_length=100)
    pnec: ReachEvidencePnecCreate
    reviewer_name: str = Field(min_length=2, max_length=200)
    reviewer_role: str = Field(min_length=2, max_length=200)
    reviewer_confirmation: Literal[True]
    signing_mode: Literal["unsigned", "rsa"] = "unsigned"

    @model_validator(mode="after")
    def validate_reach_review_selection(self):
        if len(self.selected_evidence_ids) != len(set(self.selected_evidence_ids)):
            raise ValueError("selected_evidence_ids must not contain duplicates")
        if len(self.selected_model_run_ids) != len(set(self.selected_model_run_ids)):
            raise ValueError("selected_model_run_ids must not contain duplicates")
        if self.pnec.critical_evidence_id not in self.selected_evidence_ids:
            raise ValueError("The critical PNEC evidence must be included in selected_evidence_ids")
        return self


class SelectionCalculate(BaseModel):
    project_id: int
    chemical_id: int
    target_temperature_c: float = 20.0
    activation_energy_kj_mol: float = Field(default=65.4, gt=0)
    max_reliability_score: int = Field(default=2, ge=1, le=4)


class SelectionLock(BaseModel):
    selection_set_id: int
    rationale: str = Field(min_length=5)


class MetaboliteEmissionInput(BaseModel):
    species_key: Optional[str] = None
    name: str = Field(min_length=1)
    molecular_weight_g_mol: float = Field(gt=0)
    molar_fraction: float = Field(ge=0, le=1)
    source_title: Optional[str] = None
    source_identifier: Optional[str] = None
    evidence_type: Literal["measured", "modelled", "estimated", "read_across"] = "measured"


class PharmaceuticalEmissionRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    scenario_name: str = "Pharmaceutical emission screening"
    emission_mode: Literal[
        "screening_spc", "oecd_class_screen", "refined_annual_use",
        "direct_daily_use", "ema_phase_i", "ema_phase_ii"
    ] = "screening_spc"

    parent_name: str = "Carbamazepine"
    parent_molecular_weight_g_mol: float = Field(default=236.27, gt=0)

    product_name: Optional[str] = "Tegretol 100 mg Tablets"
    formulation: str = "tablet"
    administration_route: Literal[
        "oral", "topical", "ophthalmic", "otic", "oral_rinse",
        "vaginal", "inhaled", "injectable", "other"
    ] = "oral"

    spc_title: Optional[str] = None
    spc_identifier: Optional[str] = None
    spc_url: Optional[str] = None
    spc_access_date: Optional[str] = None
    spc_source_type: Literal[
        "official_regulatory", "peer_reviewed", "secondary_web", "other"
    ] = "official_regulatory"
    consumption_source_title: Optional[str] = None
    consumption_source_identifier: Optional[str] = None

    # Class-use / legacy SPC screening inputs.
    therapeutic_class_ddd_per_1000_day: float = Field(default=196.51, ge=0)
    dose_per_administration: float = Field(default=2_000_000, gt=0)
    dose_unit: Literal["ug", "mg", "g"] = "ug"
    administrations_per_day: float = Field(default=1, gt=0)
    oecd_class_key: Optional[Literal[
        "antihypertensives", "lipid_modifying", "antidiabetics", "antidepressants"
    ]] = None
    oecd_country: Optional[str] = None

    # Site/catchment use inputs. These are total active-substance amounts, not per-patient doses.
    refined_annual_active_kg: Optional[float] = Field(default=None, gt=0)
    daily_active_amount: Optional[float] = Field(default=None, gt=0)
    daily_active_unit: Literal["mg", "g", "kg"] = "mg"
    emitting_days_per_year: int = Field(default=365, ge=1, le=366)

    # Human-medicinal-product ERA inputs.
    maximum_daily_dose_mg: Optional[float] = Field(default=None, gt=0)
    ema_fpen_mode: Literal["default", "user", "prevalence_treatment"] = "default"
    market_penetration_fraction: float = Field(default=0.01, ge=0, le=1)
    prevalence_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    treatment_days: Optional[float] = Field(default=None, gt=0, le=366)
    treatments_per_year: Optional[float] = Field(default=None, gt=0)
    regulatory_stp_capacity_inhabitants: int = Field(default=10_000, ge=1)
    dilution_factor: float = Field(default=10, ge=1)

    # Catchment / WWTP context.
    population: int = Field(default=1000, ge=1)
    wastewater_l_person_day: float = Field(default=200, gt=0)
    wastewater_flow_m3_day_override: Optional[float] = Field(default=None, gt=0)

    direct_to_sewer_fraction: float = Field(default=0, ge=0, le=1)
    systemic_fraction: float = Field(default=1, ge=0, le=1)
    parent_urine_fraction: float = Field(default=0.51, ge=0, le=1)
    parent_faeces_fraction: float = Field(default=0, ge=0, le=1)
    metabolites: list[MetaboliteEmissionInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mode_and_fractions(self):
        if self.emission_mode == "refined_annual_use" and self.refined_annual_active_kg is None:
            raise ValueError("refined_annual_active_kg is required in refined annual-use mode")
        if self.emission_mode == "direct_daily_use" and self.daily_active_amount is None:
            raise ValueError("daily_active_amount is required in direct daily-use mode")
        if self.emission_mode in {"ema_phase_i", "ema_phase_ii"} and self.maximum_daily_dose_mg is None:
            raise ValueError("maximum_daily_dose_mg is required in EMA human-pharmaceutical ERA modes")
        if self.emission_mode == "oecd_class_screen":
            if self.oecd_class_key is None or not self.oecd_country:
                raise ValueError("oecd_class_key and oecd_country are required in OECD class-screen mode")
        if self.ema_fpen_mode == "prevalence_treatment":
            if self.prevalence_fraction is None or self.treatment_days is None or self.treatments_per_year is None:
                raise ValueError("prevalence_fraction, treatment_days and treatments_per_year are required for refined FPEN")
        if self.direct_to_sewer_fraction + self.systemic_fraction > 1 + 1e-12:
            raise ValueError("direct_to_sewer_fraction + systemic_fraction cannot exceed 1")
        metabolite_sum = sum(x.molar_fraction for x in self.metabolites)
        if self.parent_urine_fraction + self.parent_faeces_fraction + metabolite_sum > 1 + 1e-12:
            raise ValueError("parent and metabolite fractions within the systemic route cannot exceed 1")
        return self


class ActivitySimpleTreatRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    assessment_profile_id: Optional[int] = None
    emission_model_run_id: int
    species_key: str = "parent"
    scenario_name: str = "Activity SimpleTreat and receiving-water screening"
    model_mode: Literal["supplied_workbook_9box_preset", "custom_screening"] = "supplied_workbook_9box_preset"

    biodegradation_fraction: float = Field(default=0.07209507243873131, ge=0, le=1)
    primary_sludge_fraction: float = Field(default=0.007868396178849157, ge=0, le=1)
    secondary_sludge_fraction: float = Field(default=0.0028491031300824854, ge=0, le=1)
    volatilisation_fraction: float = Field(default=1.6806982721404515e-8, ge=0, le=1)

    post_wwtp_biodegradation_fraction: float = Field(default=0, ge=0, le=1)
    receiving_water_dilution_factor: float = Field(default=10, ge=1)
    sludge_to_soil_fraction: float = Field(default=0.1, ge=0, le=1)
    mixed_soil_mass_kg: float = Field(default=2_000_000, gt=0)
    aquatic_pnec_ug_l: Optional[float] = Field(default=None, gt=0)
    soil_pnec_ug_kg: Optional[float] = Field(default=None, gt=0)


# Legacy endpoint retained for compatibility with v1.2 tests.
class WWTPRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    scenario_name: str = "Municipal WWTP screening"
    annual_use_kg: float = Field(gt=0)
    release_fraction: float = Field(ge=0, le=1)
    emitting_days_per_year: int = Field(default=365, ge=1, le=366)
    wastewater_flow_m3_day: float = Field(gt=0)
    biodegradation_fraction: float = Field(ge=0, le=1)
    sorption_fraction: float = Field(ge=0, le=1)
    volatilisation_fraction: float = Field(ge=0, le=1)
    receiving_water_dilution_factor: float = Field(default=10, ge=1)
    sludge_to_soil_fraction: float = Field(default=0.1, ge=0, le=1)
    mixed_soil_mass_kg: float = Field(default=2_000_000, gt=0)
    aquatic_pnec_ug_l: Optional[float] = Field(default=None, gt=0)
    soil_pnec_ug_kg: Optional[float] = Field(default=None, gt=0)


class SorptionRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    assessment_profile_id: Optional[int] = None
    scenario_name: str = "Soil sorption screening"
    mode: Literal["auto", "acid", "base", "neutral"] = "auto"
    neutral_variant: Literal["workbook_literal", "publication"] = "workbook_literal"
    base_variant: Literal["droge_goss", "franco_trapp", "ecetoc"] = "droge_goss"
    log_kow: float
    pkaa: Optional[float] = None
    pkab: Optional[float] = None
    soil_ph: float = Field(default=7.2, ge=0, le=14)
    organic_carbon_fraction: float = Field(default=0.016, gt=0, le=1)
    ionic_strength_mol_l: float = Field(default=0.01, ge=0)

    # Droge–Goss cation model. Values reproduce the supplied reviewed workbook.
    molecular_formula: Optional[str] = None
    cec_total_mol_c_kg: Optional[float] = Field(default=None, gt=0)
    electrolyte_system: str = "5 mM CaCl2"
    mcgowan_volume_vx: Optional[float] = Field(default=None, gt=0)
    ring_count: int = Field(default=0, ge=0)
    bond_count: Optional[int] = Field(default=None, ge=0)
    atom_c: Optional[int] = Field(default=None, ge=0)
    atom_h: Optional[int] = Field(default=None, ge=0)
    atom_n: Optional[int] = Field(default=None, ge=0)
    atom_o: Optional[int] = Field(default=None, ge=0)
    atom_cl: Optional[int] = Field(default=None, ge=0)
    atom_f: Optional[int] = Field(default=None, ge=0)
    atom_s: Optional[int] = Field(default=None, ge=0)
    atom_i: Optional[int] = Field(default=None, ge=0)
    atom_b: Optional[int] = Field(default=None, ge=0)
    n_h_attached_to_cationic_n: float = Field(default=0, ge=0)
    oh_groups: float = Field(default=0, ge=0)
    nh2_groups: float = Field(default=0, ge=0)
    ether_groups: float = Field(default=0, ge=0)
    ester_groups: float = Field(default=0, ge=0)
    ketone_groups: float = Field(default=0, ge=0)
    amide_groups: float = Field(default=0, ge=0)
    single_ring_charged_pyridines: float = Field(default=0, ge=0)
    chloro_groups: float = Field(default=0, ge=0)
    carboxamide_groups: float = Field(default=0, ge=0)
    multi_ring_charged_n: float = Field(default=0, ge=0)


class WastewaterIrrigationComparisonCreate(BaseModel):
    project_id: int
    chemical_id: int
    assessment_profile_id: Optional[int] = None
    sorption_model_run_id: Optional[int] = None
    activity_simpletreat_model_run_id: Optional[int] = None
    effluent_concentration_ug_l: Optional[float] = Field(default=None, gt=0)
    scenario_name: str = "EU–US wastewater irrigation comparison"
    chemical_name: str = "Carbamazepine"
    cas_number: Optional[str] = "298-46-4"
    smiles: Optional[str] = None

    irrigation_rate_l_m2_day: float = Field(default=0.5, gt=0)
    irrigated_area_m2: float = Field(default=3_680_000, gt=0)
    total_irrigation_flow_l_day: Optional[float] = Field(default=None, gt=0)
    soil_depth_m: float = Field(default=0.4, gt=0)
    bulk_density_kg_m3: float = Field(default=1350, gt=0)
    kd_l_kg: float = Field(default=4.62, gt=0)
    organic_carbon_fraction: Optional[float] = Field(default=0.0164, gt=0, le=1)
    soil_dt50_days: Optional[float] = Field(default=40, gt=0)
    degradation_rate_per_day: Optional[float] = Field(default=None, gt=0)
    duration_years: float = Field(default=1, gt=0)
    receiving_water_dilution_factor: float = Field(default=10, ge=1)
    aquatic_pnec_ug_l: Optional[float] = Field(default=None, gt=0)
    crop: str = "maize"

    freundlich_exponent: Optional[float] = Field(default=None, gt=0)
    water_solubility_mg_l: Optional[float] = Field(default=None, gt=0)
    vapour_pressure_pa: Optional[float] = Field(default=None, ge=0)
    eu_weather_scenario: Optional[Any] = None
    eu_macro_scenario: Optional[Any] = None
    drainage_boundary_conditions: Optional[Any] = None
    eu_surface_water_scenario: Optional[Any] = None
    eu_loading_time_series: Optional[Any] = None
    us_pwc_scenario: Optional[Any] = None
    us_weather_series: Optional[Any] = None
    us_runoff_erosion_parameters: Optional[Any] = None
    us_exams_waterbody: Optional[Any] = None
    us_loading_time_series: Optional[Any] = None
    aquatic_degradation_inputs: Optional[Any] = None
    metabolite_scheme: Optional[Any] = None

    @model_validator(mode="after")
    def validate_irrigation_inputs(self):
        has_linked = self.activity_simpletreat_model_run_id is not None
        has_direct = self.effluent_concentration_ug_l is not None
        if has_linked == has_direct:
            raise ValueError(
                "Provide exactly one of activity_simpletreat_model_run_id or effluent_concentration_ug_l"
            )
        if self.soil_dt50_days is not None and self.degradation_rate_per_day is not None:
            raise ValueError("Provide soil_dt50_days or degradation_rate_per_day, not both")
        if self.soil_dt50_days is None and self.degradation_rate_per_day is None:
            raise ValueError("A soil DT50 or degradation rate is required")
        return self


class PearlGroundwaterRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    scenario_name: str = "Tiered PECsoil to groundwater assessment"
    chemical_name: str = "Carbamazepine"

    input_mode: Literal["application_rate", "pecsoil"] = "pecsoil"
    profile_mode: Literal["user_defined", "focus_scenario"] = "user_defined"

    # Tier 1 — application and PECsoil
    application_rate_kg_ha: Optional[float] = Field(default=None, ge=0)
    number_applications: int = Field(default=1, ge=1, le=50)
    application_interval_days: float = Field(default=0.0, ge=0)
    crop_interception_percent: float = Field(default=0.0, ge=0, le=100)
    application_frequency_years: Literal[1, 2, 3] = 1
    first_application_day_of_year: float = Field(default=0.0, ge=0, lt=365)
    application_method: Literal["surface", "incorporated", "injected"] = "surface"
    incorporation_depth_m: float = Field(default=0.0, ge=0)
    pecsoil_mixing_depth_m: float = Field(default=0.05, gt=0)

    # Alternative entry from an existing PECsoil or measured soil concentration
    initial_soil_concentration_ug_kg: float = Field(default=0.0337908, ge=0)
    layer_initial_concentrations_ug_kg: Optional[list[float]] = None
    initial_mixing_depth_m: float = Field(default=0.4, gt=0)

    # Tier 2/3 — profile, scenario and groundwater endpoint
    focus_scenario: Optional[str] = None
    focus_crop: Optional[str] = None
    focus_target_depth_m: float = Field(default=1.0, gt=0)
    groundwater_threshold_ug_l: float = Field(default=0.1, gt=0)
    assessment_horizon_mode: Literal["quick_screen", "focus_standard"] = "quick_screen"
    screening_recharge_fraction: float = Field(default=0.35, gt=0, le=1)

    profile_depth_m: float = Field(default=1.2, gt=0)
    n_layers: int = Field(default=12, ge=2, le=200)
    bulk_density_kg_m3: float = Field(default=1350, gt=0)
    volumetric_water_content: float = Field(default=0.25, gt=0, lt=1)
    organic_carbon_fraction: Optional[float] = Field(default=0.0164, gt=0, le=1)

    kd_l_kg: Optional[float] = Field(default=4.62, gt=0)
    koc_l_kg: Optional[float] = Field(default=None, gt=0)
    freundlich_exponent: float = Field(default=1.0, gt=0)
    reference_concentration_mg_l: float = Field(default=1.0, gt=0)

    soil_dt50_days: float = Field(default=40, gt=0)
    temperature_c: float = Field(default=20.0, gt=-273.15)
    temperature_ref_c: float = Field(default=20.0, gt=-273.15)
    activation_energy_kj_mol: float = Field(default=65.4, gt=0)
    moisture_exponent: float = Field(default=0.0, ge=0)
    depth_transformation_half_depth_m: Optional[float] = Field(default=None, gt=0)

    simulation_days: float = Field(default=1095.0, gt=0)
    time_step_days: float = Field(default=1.0, gt=0)
    max_transport_substep_days: float = Field(default=0.25, gt=0)
    percolation_mm_day: Optional[float] = Field(default=0.5, ge=0)
    dispersivity_m: float = Field(default=0.02, ge=0)
    molecular_diffusion_m2_d: float = Field(default=1e-5, ge=0)
    root_water_uptake_mm_day: float = Field(default=0.0, ge=0)
    root_depth_m: float = Field(default=0.4, gt=0)
    root_uptake_factor: float = Field(default=0.0, ge=0)

    molecular_weight_g_mol: Optional[float] = Field(default=None, gt=0)
    water_solubility_mg_l: Optional[float] = Field(default=None, gt=0)
    vapour_pressure_pa: Optional[float] = Field(default=None, ge=0)
    pka: Optional[float] = None
    metabolite_scheme: Optional[Any] = None

    swap_state_sampling: Literal["end", "midpoint"] = "end"
    swap_bottom_flux_sign: float = 1.0
    swap_q_flux_sign: float = 1.0
    swap_drop_initial_row: bool = True

    @model_validator(mode="after")
    def validate_pearl_inputs(self):
        if self.kd_l_kg is None and self.koc_l_kg is None:
            raise ValueError("Provide Kd or Koc")
        if self.kd_l_kg is None and self.koc_l_kg is not None and self.organic_carbon_fraction is None and self.profile_mode != "focus_scenario":
            raise ValueError("fOC is required to convert Koc to Kd outside a depth-resolved FOCUS profile")
        if self.input_mode == "application_rate" and self.application_rate_kg_ha is None:
            raise ValueError("application_rate_kg_ha is required in application-rate mode")
        if self.layer_initial_concentrations_ug_kg is not None and self.profile_mode == "user_defined" and len(self.layer_initial_concentrations_ug_kg) != self.n_layers:
            raise ValueError("Layer initial concentration count must equal n_layers for a user-defined profile")
        return self


class ToxswaSurfaceWaterRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    chemical_name: str = "Carbamazepine"
    scenario_name: str = "TOXSWA surface-water process screen"
    contaminant_group: str = "human_pharmaceutical"
    regulatory_context: str = "Adapted environmental fate assessment"

    # Waterbody geometry/hydrology. Native values are user-defined screening
    # inputs and are never presented as standard FOCUS scenario defaults.
    waterbody_type: Literal["ditch", "stream", "pond", "custom"] = "stream"
    waterbody_length_m: float = Field(default=1000.0, gt=0)
    waterbody_width_m: float = Field(default=20.0, gt=0)
    water_depth_m: float = Field(default=2.0, gt=0)
    receiving_flow_m3_day: float = Field(default=200000.0, ge=0)
    n_segments: int = Field(default=20, ge=2, le=200)

    # Active sediment layer used in the transparent native alpha core.
    sediment_active_depth_m: float = Field(default=0.05, gt=0)
    sediment_bulk_density_kg_m3: float = Field(default=800.0, gt=0)
    sediment_porosity: float = Field(default=0.6, gt=0, lt=1)
    sediment_organic_carbon_fraction: float = Field(default=0.0522, ge=0, le=1)

    suspended_solids_mg_l: float = Field(default=15.0, ge=0)
    suspended_solids_organic_carbon_fraction: float = Field(default=0.2, ge=0, le=1)

    # Substance properties. Direct Kd values can override Koc-derived values.
    molecular_weight_g_mol: Optional[float] = Field(default=236.27, gt=0)
    koc_l_kg: float = Field(default=282.0, ge=0)
    sediment_kd_l_kg: Optional[float] = Field(default=None, ge=0)
    suspended_solids_kd_l_kg: Optional[float] = Field(default=None, ge=0)
    freundlich_exponent: float = Field(default=1.0, gt=0)
    reference_concentration_mg_l: float = Field(default=1.0, gt=0)
    water_dt50_days: float = Field(default=40.0, gt=0)
    sediment_dt50_days: float = Field(default=80.0, gt=0)
    transformation_reference_temperature_c: float = Field(default=20.0, gt=-273.15)
    water_temperature_c: float = Field(default=20.0, gt=-273.15)
    activation_energy_kj_mol: float = Field(default=65.4, ge=0)
    water_transformation_mode: Literal["lumped", "separate_dissolved_only"] = "lumped"
    aqueous_diffusion_coefficient_m2_day: float = Field(default=4.3e-5, ge=0)
    relative_sediment_diffusion: float = Field(default=0.3, ge=0, le=1)
    interface_diffusion_path_m: float = Field(default=0.0005, gt=0)
    volatilisation_half_life_days: Optional[float] = Field(default=None, gt=0)
    water_solubility_mg_l: Optional[float] = Field(default=None, ge=0)
    vapour_pressure_pa: Optional[float] = Field(default=None, ge=0)

    # Loading. The UI changes the visible inputs by route; the API keeps one
    # auditable schema so historical runs remain reproducible.
    loading_mode: Literal[
        "spray_drift", "continuous_point_discharge", "continuous_distributed",
        "pulse_mass", "lateral_drainage", "lateral_runoff",
    ] = "continuous_point_discharge"
    loaded_start_m: float = Field(default=0.0, ge=0)
    loaded_end_m: Optional[float] = Field(default=1000.0, gt=0)

    application_rate_kg_ha: float = Field(default=1.0, ge=0)
    drift_percent: float = Field(default=1.0, ge=0, le=100)
    first_application_day: float = Field(default=1.0, ge=0)
    number_applications: int = Field(default=1, ge=1, le=100)
    application_interval_days: float = Field(default=7.0, ge=0)

    discharge_concentration_ug_l: float = Field(default=0.640775, ge=0)
    discharge_flow_m3_day: float = Field(default=20000.0, ge=0)
    continuous_mass_mg_day: float = Field(default=0.0, ge=0)
    pulse_mass_mg: float = Field(default=0.0, ge=0)
    pulse_day: float = Field(default=1.0, ge=0)
    pulse_distributed: bool = False
    lateral_concentration_ug_l: float = Field(default=0.0, ge=0)
    lateral_water_flux_m3_day: float = Field(default=0.0, ge=0)

    initial_water_concentration_ug_l: float = Field(default=0.0, ge=0)
    initial_sediment_concentration_ug_kg: float = Field(default=0.0, ge=0)
    simulation_days: float = Field(default=120.0, gt=0, le=7300)
    output_interval_days: float = Field(default=1.0 / 24.0, gt=0, le=30)
    max_transport_substep_days: float = Field(default=0.05, gt=0, le=1)

    aquatic_pnec_ug_l: Optional[float] = Field(default=None, gt=0)
    sediment_pnec_ug_kg: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_toxswa_screen(self):
        if self.loaded_end_m is None:
            self.loaded_end_m = self.waterbody_length_m
        if self.loaded_end_m > self.waterbody_length_m + 1e-12:
            raise ValueError("loaded_end_m cannot exceed waterbody_length_m")
        if self.loaded_end_m <= self.loaded_start_m:
            raise ValueError("loaded_end_m must be greater than loaded_start_m")
        if self.loading_mode == "spray_drift" and self.application_rate_kg_ha <= 0:
            raise ValueError("A positive application rate is required for spray-drift loading")
        if self.loading_mode == "continuous_point_discharge" and self.discharge_flow_m3_day <= 0:
            raise ValueError("A positive discharge flow is required for continuous point discharge")
        if self.loading_mode == "continuous_distributed" and self.continuous_mass_mg_day <= 0:
            raise ValueError("A positive continuous mass loading is required")
        if self.loading_mode == "pulse_mass" and self.pulse_mass_mg <= 0:
            raise ValueError("A positive pulse mass is required")
        if self.loading_mode in {"lateral_drainage", "lateral_runoff"} and self.lateral_water_flux_m3_day <= 0:
            raise ValueError("A positive lateral water flux is required for drainage/runoff loading")
        return self


class MultimediaCompartmentInput(BaseModel):
    key: Literal["air", "freshwater", "soil", "sediment"]
    volume_m3: float = Field(gt=0)
    bulk_density_kg_m3: Optional[float] = Field(default=None, gt=0)
    half_life_days: Optional[float] = Field(default=None, gt=0)
    advective_loss_per_day: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def require_density_for_solid_media(self):
        if self.key in {"soil", "sediment"} and self.bulk_density_kg_m3 is None:
            raise ValueError(f"bulk_density_kg_m3 is required for {self.key}")
        return self


class MultimediaTransferInput(BaseModel):
    source: Literal["air", "freshwater", "soil", "sediment"]
    target: Literal["air", "freshwater", "soil", "sediment"]
    rate_per_day: float = Field(ge=0)

    @model_validator(mode="after")
    def prevent_self_transfer(self):
        if self.source == self.target:
            raise ValueError("Intermedia transfer source and target must differ")
        return self


class MultimediaFateRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    scenario_name: str = "Multimedia environmental fate screen"
    emissions_kg_day: dict[str, float]
    compartments: list[MultimediaCompartmentInput] = Field(min_length=2, max_length=4)
    transfers: list[MultimediaTransferInput] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_multimedia_system(self):
        if not any(value > 0 for value in self.emissions_kg_day.values()):
            raise ValueError("At least one positive compartment emission is required")
        if any(value < 0 for value in self.emissions_kg_day.values()):
            raise ValueError("Emissions cannot be negative")
        compartment_keys = {item.key for item in self.compartments}
        unknown = set(self.emissions_kg_day) - compartment_keys
        if unknown:
            raise ValueError(f"Emissions reference unknown compartments: {', '.join(sorted(unknown))}")
        return self


class RiverSegmentInput(BaseModel):
    segment_id: str = Field(min_length=1, max_length=100)
    upstream_ids: list[str] = Field(default_factory=list, max_length=20)
    flow_m3_day: float = Field(gt=0)
    travel_time_days: float = Field(ge=0)
    water_dt50_days: Optional[float] = Field(default=None, gt=0)
    other_loss_rate_per_day: float = Field(default=0.0, ge=0)
    local_load_kg_day: float = Field(default=0.0, ge=0)
    local_effluent_concentration_ug_l: float = Field(default=0.0, ge=0)
    local_effluent_flow_m3_day: float = Field(default=0.0, ge=0)


class CatchmentRiverRunCreate(BaseModel):
    project_id: int
    chemical_id: int
    scenario_name: str = "Catchment river-network exposure screen"
    default_water_dt50_days: Optional[float] = Field(default=None, gt=0)
    aquatic_pnec_ug_l: Optional[float] = Field(default=None, gt=0)
    segments: list[RiverSegmentInput] = Field(min_length=1, max_length=500)


class AssessmentPlanCreate(BaseModel):
    jurisdiction: Literal["EU", "UK", "US", "CH"]
    contaminant_group: str
    scenario: str
    tier: int = Field(default=1, ge=0, le=4)


class USExposureSourceCitation(BaseModel):
    source_key: str = Field(min_length=2, max_length=120)
    reference: str = Field(min_length=2, max_length=500)
    locator: Optional[str] = Field(default=None, max_length=250)
    access_date: Optional[str] = Field(default=None, max_length=30)
    evidence_status: Literal[
        "measured", "modelled", "scenario_default", "user_assumption", "expert_judgement"
    ] = "user_assumption"
    notes: Optional[str] = Field(default=None, max_length=2000)


class USReleaseEventInput(BaseModel):
    event_key: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=250)
    loss_fraction: float = Field(ge=0, le=1)
    control_efficiency_fraction: float = Field(default=0, ge=0, le=1)
    media_fractions: dict[str, float]
    control_destination: Optional[
        Literal["landfill", "incineration", "offsite_treatment"]
    ] = None
    evidence_status: Literal[
        "measured", "modelled", "scenario_default", "user_assumption", "expert_judgement"
    ] = "user_assumption"
    source_reference: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_mass_routing(self):
        allowed = {
            "air", "water", "soil", "landfill", "incineration", "offsite_treatment"
        }
        unknown = set(self.media_fractions) - allowed
        if unknown:
            raise ValueError("Unknown release media: " + ", ".join(sorted(unknown)))
        if not self.media_fractions:
            raise ValueError("At least one release medium is required")
        if any(value < 0 or value > 1 for value in self.media_fractions.values()):
            raise ValueError("Each media fraction must be between 0 and 1")
        if abs(sum(self.media_fractions.values()) - 1.0) > 1e-9:
            raise ValueError("Release-event media fractions must sum to 1")
        if self.control_efficiency_fraction > 0 and self.control_destination is None:
            raise ValueError("A managed-waste control destination is required when control is applied")
        return self


class USWorkerExposureTaskInput(BaseModel):
    task_name: str = Field(min_length=2, max_length=250)
    inhalation_mode: Literal["measured_air", "well_mixed_screen"]
    task_duration_hours: float = Field(gt=0, le=24)
    exposure_days_year: float = Field(gt=0, le=365)
    body_weight_kg: float = Field(default=80, gt=0)
    inhalation_rate_m3_hour: float = Field(default=1.25, gt=0)
    respirator_apf: float = Field(default=1, ge=1)
    inhalation_absorption_fraction: float = Field(default=1, ge=0, le=1)
    measured_air_concentration_mg_m3: Optional[float] = Field(default=None, ge=0)
    chemical_handled_kg_per_shift: Optional[float] = Field(default=None, gt=0)
    airborne_release_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    local_exhaust_control_fraction: float = Field(default=0, ge=0, le=1)
    room_volume_m3: Optional[float] = Field(default=None, gt=0)
    air_exchange_rate_per_hour: Optional[float] = Field(default=None, gt=0)
    dermal_contact_mg_shift: float = Field(default=0, ge=0)
    glove_protection_factor: float = Field(default=1, ge=1)
    dermal_absorption_fraction: float = Field(default=0, ge=0, le=1)
    source_reference: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_inhalation_mode(self):
        if self.inhalation_mode == "measured_air":
            if self.measured_air_concentration_mg_m3 is None:
                raise ValueError("Measured-air mode requires measured_air_concentration_mg_m3")
        else:
            required = {
                "chemical_handled_kg_per_shift": self.chemical_handled_kg_per_shift,
                "airborne_release_fraction": self.airborne_release_fraction,
                "room_volume_m3": self.room_volume_m3,
                "air_exchange_rate_per_hour": self.air_exchange_rate_per_hour,
            }
            missing = [key for key, value in required.items() if value is None]
            if missing:
                raise ValueError("Well-mixed mode is missing: " + ", ".join(missing))
        return self


class USGroundwaterLeachingInput(BaseModel):
    soil_release_area_ha: float = Field(gt=0)
    source_zone_depth_m: float = Field(default=0.2, gt=0, le=5)
    assessment_depth_m: float = Field(default=1.0, gt=0, le=100)
    soil_bulk_density_kg_m3: float = Field(default=1500, gt=0, le=3000)
    volumetric_water_content: float = Field(default=0.25, gt=0, le=0.8)
    annual_recharge_mm: float = Field(gt=0, le=5000)
    koc_l_kg: float = Field(ge=0)
    soil_organic_carbon_fraction: float = Field(default=0.02, gt=0, le=1)
    soil_dt50_days: float = Field(gt=0)
    additional_attenuation_fraction: float = Field(default=1.0, ge=0, le=1)
    parameter_source: str = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def validate_depths(self):
        if self.assessment_depth_m < self.source_zone_depth_m:
            raise ValueError("assessment_depth_m must be at or below the source zone")
        return self


class USIndustrialExposureRunCreate(BaseModel):
    project_id: int = Field(gt=0)
    chemical_id: int = Field(gt=0)
    scenario_name: str = Field(
        default="US industrial release and worker exposure screen",
        min_length=2,
        max_length=250,
    )
    contaminant_group: Literal["industrial_organic"] = "industrial_organic"
    source_scenario_key: Optional[str] = Field(default=None, max_length=120)
    chemical_throughput_kg_day: float = Field(gt=0)
    operating_days_year: float = Field(gt=0, le=365)
    release_events: list[USReleaseEventInput] = Field(min_length=1, max_length=100)
    worker_tasks: list[USWorkerExposureTaskInput] = Field(default_factory=list, max_length=100)
    groundwater_screen: Optional[USGroundwaterLeachingInput] = None
    citations: list[USExposureSourceCitation] = Field(default_factory=list, max_length=100)
    uncertainty_notes: Optional[str] = Field(default=None, max_length=5000)
    scientist_review_confirmed: bool = False
    consumer_exposure_addressed: bool = False
    fate_transport_addressed: bool = False
    ecological_effects_addressed: bool = False
    human_health_hazards_addressed: bool = False
    vulnerable_populations_addressed: bool = False
    monitoring_validation_addressed: bool = False
    risk_characterisation_addressed: bool = False

    @model_validator(mode="after")
    def validate_shared_throughput_basis(self):
        total = sum(event.loss_fraction for event in self.release_events)
        if total > 1 + 1e-12:
            raise ValueError(
                "Release-event loss fractions share one throughput basis and cannot sum to more than 1"
            )
        return self


class USExposureCompletenessCreate(BaseModel):
    identity_confirmed: bool = False
    uses_and_volumes: bool = False
    manufacturing_processing: bool = False
    worker_exposure: bool = False
    consumer_exposure: bool = False
    environmental_releases: bool = False
    waste_disposal: bool = False
    fate_transport: bool = False
    ecological_effects: bool = False
    human_health_hazards: bool = False
    vulnerable_populations: bool = False
    monitoring_validation: bool = False
    uncertainty_characterisation: bool = False
    risk_characterisation: bool = False
    source_provenance: bool = False


class HomeUseSummaryCreate(BaseModel):
    project_id: Optional[int] = Field(default=None, gt=0)
    chemical_id: Optional[int] = Field(default=None, gt=0)
    assessment_profile_id: Optional[int] = Field(default=None, gt=0)
    bind_to_reviewed_profile: bool = False
    product_identifier: Optional[str] = None
    product_name: Optional[str] = None
    chemical_name: Optional[str] = None
    amount_value: float = Field(gt=0)
    amount_unit: Literal["mg", "g", "mL", "L", "kg"] = "mL"
    frequency_value: float = Field(default=1, gt=0)
    frequency_unit: Literal["day", "week", "month", "year", "one_off"] = "week"
    release_route: Literal[
        "down_drain", "outdoor_soil", "outdoor_surface", "spray_air",
        "hazardous_waste", "general_bin"
    ]
    log_kow: Optional[float] = None
    koc_l_kg: Optional[float] = Field(default=None, gt=0)
    soil_dt50_days: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_reviewed_profile_binding(self):
        binding = [self.project_id, self.chemical_id, self.assessment_profile_id]
        if self.bind_to_reviewed_profile and any(value is None for value in binding):
            raise ValueError(
                "project_id, chemical_id and assessment_profile_id are required when binding a reviewed profile"
            )
        if not self.bind_to_reviewed_profile and any(value is not None for value in binding):
            raise ValueError(
                "Set bind_to_reviewed_profile=true when supplying project or profile identifiers"
            )
        return self


class ModelWorkflowCreate(BaseModel):
    project_id: int
    chemical_id: int
    model_key: str
    jurisdiction: Literal["EU", "UK", "US", "CH"]
    tier: int = Field(ge=1, le=4)
    scenario_name: str = Field(min_length=2, max_length=250)
    input_data: dict[str, Any] = Field(default_factory=dict)
    executable_path: Optional[str] = None


class ModelWorkflowExecute(BaseModel):
    operator: str = Field(min_length=2, max_length=200)
    installed_version: str = Field(min_length=1, max_length=100)
    expected_executable_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    confirm_authorised_installation: Literal[True]
    confirm_unmodified_official_software: Literal[True]


class ModelWorkflowOutputImport(BaseModel):
    raw_output_text: Optional[str] = None
    structured_outputs: dict[str, Any] = Field(default_factory=dict)
    model_version: Optional[str] = None
    executable_version: Optional[str] = None
    execution_notes: Optional[str] = None
    execution_method: Optional[Literal["manual_official_installation", "other_external_execution"]] = None
    operator: Optional[str] = Field(default=None, max_length=200)
    confirm_genuine_execution: bool = False

    @model_validator(mode="after")
    def require_output(self):
        if not (self.raw_output_text and self.raw_output_text.strip()) and not self.structured_outputs:
            raise ValueError("Provide raw_output_text or structured_outputs")
        return self


class ModelWorkflowReview(BaseModel):
    reviewer: str = Field(min_length=2, max_length=200)
    decision: Literal["accepted", "revision_required", "rejected"]
    notes: Optional[str] = None


class RegulatoryPathwayCreate(BaseModel):
    jurisdictions: list[str] = Field(default_factory=lambda: ["EU", "US"], min_length=1)
    product_class: str
    scenario: str
    tier: int = Field(default=1, ge=0, le=4)
    include_international: bool = True


class VeterinaryPhaseICreate(BaseModel):
    animal_profile_key: str
    jurisdiction: str = "VICH/EU"
    legally_exempt: bool = False
    natural_substance_no_distribution_change: bool = False
    minor_species_equivalent: bool = False
    small_number_treated: bool = False
    extensively_metabolized: bool = False
    parasiticide: bool = False
    specific_environmental_concern: bool = False
    waste_entry_prevented: bool = False
    aquatic_confined: bool = False
    eic_aquatic_ug_l: Optional[float] = Field(default=None, ge=0)
    pec_soil_ug_kg: Optional[float] = Field(default=None, ge=0)


class VeterinaryAssessmentCreate(BaseModel):
    chemical_name: str = Field(min_length=1)
    animal_profile_key: str
    branch_override: Optional[Literal["intensive", "pasture", "aquaculture", "companion", "special", "custom"]] = None

    dose_value: float = Field(gt=0)
    dose_unit: Literal["mg_per_kg_bw_day", "mg_per_animal_day", "g_per_animal_day"] = "mg_per_kg_bw_day"
    treatment_duration_days: float = Field(default=1, gt=0)
    fraction_treated: float = Field(default=1, ge=0, le=1)
    treatment_events_per_year: float = Field(default=1, gt=0)
    excreted_fraction: float = Field(default=1, ge=0, le=1)
    faecal_excretion_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    excretion_duration_days: Optional[float] = Field(default=None, gt=0)
    parasiticide: bool = False

    body_weight_kg: Optional[float] = Field(default=None, gt=0)
    turnover_per_year: Optional[float] = Field(default=None, gt=0)
    nitrogen_kg_place_year: Optional[float] = Field(default=None, gt=0)
    housing_factor: Optional[float] = Field(default=None, gt=0, le=1)

    nitrogen_spreading_limit_kg_ha: float = Field(default=170, gt=0)
    soil_bulk_density_kg_m3: float = Field(default=1500, gt=0)
    soil_depth_m: float = Field(default=0.05, gt=0)
    stocking_density_animals_ha: Optional[float] = Field(default=None, gt=0)
    dung_output_kg_animal_day: Optional[float] = Field(default=None, gt=0)

    manure_storage_days: float = Field(default=91, ge=0)
    storage_time_basis: Literal["mean_age_half_duration", "full_duration"] = "mean_age_half_duration"
    manure_dt50_value: Optional[float] = Field(default=None, gt=0)
    manure_dt50_unit: Literal["hours", "days"] = "days"
    biowin4_value: Optional[float] = None
    source_temperature_c: float = 25.0
    target_temperature_c: float = 10.0
    temperature_factor_theta: float = Field(default=1.047, gt=0)

    # Soil persistence is separate from manure storage. GL38 section 2.7 refers
    # to DT90 in soil under repeated/annual application.
    soil_dt50_days: Optional[float] = Field(default=None, gt=0)
    soil_dt90_days: Optional[float] = Field(default=None, gt=0)
    soil_accumulation_years: int = Field(default=10, ge=1, le=100)

    treated_biomass_kg: Optional[float] = Field(default=None, gt=0)
    facility_water_volume_l: Optional[float] = Field(default=None, gt=0)
    direct_water_release_fraction: float = Field(default=0, ge=0, le=1)
    uneaten_feed_fraction: float = Field(default=0, ge=0, le=1)
    receiving_water_dilution_factor: float = Field(default=1, ge=1)
    sediment_area_m2: Optional[float] = Field(default=None, gt=0)
    sediment_depth_m: Optional[float] = Field(default=None, gt=0)
    sediment_density_kg_m3: Optional[float] = Field(default=None, gt=0)

    log_kow: Optional[float] = None
    soil_pnec_ug_kg: Optional[float] = Field(default=None, gt=0)
    aquatic_pnec_ug_l: Optional[float] = Field(default=None, gt=0)
    sediment_pnec_ug_kg: Optional[float] = Field(default=None, gt=0)
    dung_pnec_ug_kg: Optional[float] = Field(default=None, gt=0)
    earthworm_ld50_ug_kg: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_branch_fields(self):
        if self.faecal_excretion_fraction is None:
            self.faecal_excretion_fraction = self.excreted_fraction
        return self


class BiosolidsLandApplicationCreate(BaseModel):
    project_id: int
    chemical_id: int
    assessment_profile_id: Optional[int] = None
    activity_simpletreat_model_run_id: Optional[int] = None
    scenario_name: str = "Biosolids land-application screen"
    source_mode: Literal["wwtp_chemical_mass", "biosolids_concentration"] = "wwtp_chemical_mass"
    chemical_mass_to_sludge_kg_day: Optional[float] = Field(default=None, ge=0)
    biosolids_dry_solids_kg_day: Optional[float] = Field(default=None, gt=0)
    biosolids_concentration_mg_kg_dw: Optional[float] = Field(default=None, ge=0)
    biosolids_application_t_dw_ha_year: Optional[float] = Field(default=None, gt=0)
    operating_days_per_year: int = Field(default=365, ge=1, le=366)
    fraction_sludge_land_applied: float = Field(default=1, ge=0, le=1)
    land_application_area_ha: float = Field(default=100, gt=0)
    storage_days: float = Field(default=0, ge=0)
    storage_dt50_days: Optional[float] = Field(default=None, gt=0)
    soil_mixing_depth_m: float = Field(default=0.2, gt=0)
    soil_bulk_density_kg_m3: float = Field(default=1500, gt=0)
    soil_dt50_days: Optional[float] = Field(default=40, gt=0)
    assessment_years: int = Field(default=10, ge=1, le=100)
    runoff_fraction: float = Field(default=0, ge=0, le=1)
    leaching_fraction: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_mode == "wwtp_chemical_mass" and self.chemical_mass_to_sludge_kg_day is None:
            raise ValueError("chemical_mass_to_sludge_kg_day is required for WWTP sludge-mass mode")
        if self.source_mode == "biosolids_concentration":
            if self.biosolids_concentration_mg_kg_dw is None or self.biosolids_application_t_dw_ha_year is None:
                raise ValueError("biosolids concentration and dry application rate are required")
        return self


class PlantUptakeScreenCreate(BaseModel):
    project_id: int
    chemical_id: int
    assessment_profile_id: Optional[int] = None
    sorption_model_run_id: Optional[int] = None
    scenario_name: str = "Plant uptake screening"
    model_mode: Literal["briggs_neutral", "user_tscf", "empirical_bcf"] = "briggs_neutral"
    ionisation_class: Literal["neutral", "acid", "base", "zwitterion"] = "neutral"
    soil_concentration_mg_kg_dw: float = Field(ge=0)
    kd_l_kg: float = Field(gt=0)
    volumetric_water_content_l_l: float = Field(default=0.25, gt=0, le=1)
    soil_bulk_density_kg_m3: float = Field(default=1350, gt=0)
    log_kow: Optional[float] = 2.45
    user_tscf: Optional[float] = Field(default=None, ge=0)
    transpiration_l_plant_day: float = Field(default=1.5, gt=0)
    harvest_interval_days: float = Field(default=90, gt=0)
    plant_loss_dt50_days: Optional[float] = Field(default=None, gt=0)
    root_allocation_fraction: float = Field(default=0.2, ge=0, le=1)
    shoot_allocation_fraction: float = Field(default=0.5, ge=0, le=1)
    edible_allocation_fraction: float = Field(default=0.3, ge=0, le=1)
    root_fresh_mass_kg: float = Field(default=0.5, gt=0)
    shoot_fresh_mass_kg: float = Field(default=3.0, gt=0)
    edible_fresh_mass_kg: float = Field(default=0.5, gt=0)
    root_bcf_kg_kg: Optional[float] = Field(default=None, ge=0)
    shoot_bcf_kg_kg: Optional[float] = Field(default=None, ge=0)
    edible_bcf_kg_kg: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_plant_mode(self):
        if self.model_mode == "briggs_neutral" and self.log_kow is None:
            raise ValueError("log_kow is required for Briggs neutral mode")
        if self.model_mode == "user_tscf" and self.user_tscf is None:
            raise ValueError("user_tscf is required for user TSCF mode")
        if self.model_mode == "empirical_bcf" and any(v is None for v in [self.root_bcf_kg_kg, self.shoot_bcf_kg_kg, self.edible_bcf_kg_kg]):
            raise ValueError("root, shoot and edible BCFs are required for empirical mode")
        if abs(self.root_allocation_fraction + self.shoot_allocation_fraction + self.edible_allocation_fraction - 1) > 1e-8:
            raise ValueError("plant allocation fractions must sum to 1")
        return self


class EnviroDesignProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    smiles: str = Field(min_length=1)
    status: Literal["observed", "predicted", "hypothetical"] = "predicted"
    matrix: Optional[str] = None
    source: Optional[str] = None
    dt50_days: Optional[float] = Field(default=None, gt=0)


class EnviroDesignAnalyseCreate(BaseModel):
    smiles: str = Field(min_length=1)
    name: Optional[str] = Field(default=None, max_length=200)
    project_id: Optional[int] = None
    chemical_id: Optional[int] = None
    scenario_name: str = "EnviroDesign structural attribution"
    include_svg: bool = True

    @model_validator(mode="after")
    def validate_persistence_ids(self):
        if (self.project_id is None) != (self.chemical_id is None):
            raise ValueError("Provide both project_id and chemical_id to persist the analysis, or neither")
        return self


class EnviroDesignCandidateInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    smiles: str = Field(min_length=1)


class EnviroDesignCompareCreate(BaseModel):
    original_smiles: str = Field(min_length=1)
    candidates: list[EnviroDesignCandidateInput] = Field(min_length=1, max_length=20)
    protected_smarts: list[str] = Field(default_factory=list, max_length=20)
    project_id: Optional[int] = None
    chemical_id: Optional[int] = None
    scenario_name: str = "EnviroDesign candidate comparison"

    @model_validator(mode="after")
    def validate_persistence_ids(self):
        if (self.project_id is None) != (self.chemical_id is None):
            raise ValueError("Provide both project_id and chemical_id to persist the comparison, or neither")
        return self


class EnviroDesignPathwayCreate(BaseModel):
    parent_smiles: str = Field(min_length=1)
    products: list[EnviroDesignProductInput] = Field(min_length=1, max_length=100)
    project_id: Optional[int] = None
    chemical_id: Optional[int] = None
    scenario_name: str = "EnviroDesign transformation-pathway retention"

    @model_validator(mode="after")
    def validate_persistence_ids(self):
        if (self.project_id is None) != (self.chemical_id is None):
            raise ValueError("Provide both project_id and chemical_id to persist the pathway analysis, or neither")
        return self


class TransformationPathwayPredictCreate(BaseModel):
    provider: Literal["biotransformer"] = "biotransformer"
    parent_smiles: str = Field(min_length=1, max_length=5000)
    parent_name: str = Field(default="Parent", min_length=1, max_length=200)
    number_of_steps: int = Field(default=1, ge=1, le=3)
    project_id: Optional[int] = None
    chemical_id: Optional[int] = None
    scenario_name: str = Field(default="BioTransformer environmental pathway prediction", max_length=250)

    @model_validator(mode="after")
    def validate_persistence_ids(self):
        if (self.project_id is None) != (self.chemical_id is None):
            raise ValueError("Provide both project_id and chemical_id to persist the pathway prediction, or neither")
        return self
