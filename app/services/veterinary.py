from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "veterinary_animal_profiles.json"
ANIMAL_PROFILES: list[dict[str, Any]] = json.loads(DATA_PATH.read_text(encoding="utf-8"))
PROFILE_BY_KEY = {row["key"]: row for row in ANIMAL_PROFILES}

GUIDANCE = {
    "phase_i": {
        "name": "VICH GL6 Environmental Impact Assessment Phase I",
        "version": "June 2000",
        "logic": "Exposure-led decision tree with terrestrial and aquatic branches.",
        "aquatic_trigger_ug_l": 1.0,
        "soil_trigger_ug_kg": 100.0,
    },
    "phase_ii": {
        "name": "VICH GL38 Environmental Impact Assessment Phase II",
        "version": "October 2004; implementation October 2005",
        "branches": ["aquaculture", "intensive", "pasture"],
        "rq_trigger": 1.0,
        "metabolite_refinement_trigger_fraction": 0.10,
        "bioaccumulation_logkow_trigger": 4.0,
        "bcf_guidance_trigger": 1000.0,
        "persistence_accumulation_example": "DT90 > 1 year under annual application",
    },
    "implementation_warning": (
        "VICH harmonises principles, not every regional parameter. Jurisdiction-specific husbandry, "
        "climate, soil, water and current competent-authority guidance must be confirmed before submission."
    ),
    "outlier_compatibility": (
        "The BIOWIN-to-manure-DT50 and ranked earthworm-LD50 workflow is retained as a transparent "
        "screening/benchmark mode. It is not labelled as an official VICH or EMA calculation."
    ),
    "current_source_register": [
        {"id":"VICH-GL6","title":"Environmental impact assessment for veterinary medicinal products — Phase I","reference":"CVMP/VICH/592/98-FINAL","status":"adopted","effective":"20 July 2000","scope":"All non-biological VMPs; exposure-led Phase I decision tree"},
        {"id":"VICH-GL38","title":"Environmental impact assessment for veterinary medicinal products — Phase II","reference":"CVMP/VICH/790/03-FINAL","status":"adopted","effective":"October 2005","scope":"Aquaculture, intensive and pasture branches; Tier A/B RQ"},
        {"id":"EMA-VICH-SUPPORT","title":"Environmental impact assessment for VMPs in support of VICH GL6 and GL38","reference":"EMEA/CVMP/ERA/418282/2005-Rev.1 Corr.1","status":"current effective","effective":"1 March 2009; page last updated 5 July 2016","scope":"EU parameters, test conditions and default values","official_url":"https://www.ema.europa.eu/en/environmental-impact-assessment-veterinary-medicinal-products-support-vich-guidelines-gl6-gl38-scientific-guideline"},
        {"id":"EMA-MANURE-REV1","title":"Determining the fate of veterinary medicinal products in manure","reference":"EMA/CVMP/ERA/430327/2009 Rev.1","status":"current effective","effective":"last updated 26 July 2024","scope":"Design, execution and interpretation of manure transformation studies","official_url":"https://www.ema.europa.eu/en/determining-fate-veterinary-medicinal-products-manure-scientific-guideline"},
        {"id":"EMA-CAT-DOG-ECTO","title":"Environmental risk assessment of ectoparasiticidal VMPs used in cats and dogs","reference":"EMA/CVMP/ERA/31905/2021","status":"adopted reflection paper","effective":"9 November 2023","scope":"Companion-animal ectoparasiticide concern pathways","official_url":"https://www.ema.europa.eu/en/environmental-risk-assessment-ectoparasiticidal-veterinary-medicinal-products-used-cats-and-dogs"},
        {"id":"EMA-DUNG-FAUNA","title":"Higher-tier testing to investigate effects of parasiticidal VMPs on dung fauna","reference":"EMA/CVMP/ERA/87473/2021","status":"adopted reflection paper","effective":"17 September 2021","scope":"Livestock parasiticides and dung-fauna higher-tier assessment","official_url":"https://www.ema.europa.eu/en/higher-tier-testing-investigate-effects-parasiticidal-veterinary-medicinal-products-dung-fauna"},
        {"id":"EMA-AQUACULTURE-CONCEPT","title":"ERA of veterinary medicinal products intended for aquaculture","reference":"EMA/CVMP/ERA/173026/2021","status":"concept paper; not a final guideline","effective":"consultation closed 31 October 2021","scope":"Aquaculture-specific methodology under development","official_url":"https://www.ema.europa.eu/en/environmental-risk-assessment-veterinary-medicinal-products-intended-be-used-aquaculture-scientific-guideline"},
        {"id":"EMA-IVMP-REV1","title":"Environmental risk assessment for immunological veterinary medicinal products — Revision 1","reference":"EMEA/CVMP/074/95 Rev.1","status":"current effective","effective":"14 July 2026","scope":"Immunological veterinary medicinal products","official_url":"https://www.ema.europa.eu/en/environmental-risk-assessment-immunological-veterinary-medicinal-products-scientific-guideline"},
        {"id":"EMA-ENV-AMR-CONCEPT","title":"Public-health risks from environmental AMR resulting from VMP use","reference":"EMA/CVMP/ERA/75412/2023","status":"concept paper; consultation closed","effective":"consultation closed 31 October 2025","scope":"Food and companion animals; environmental AMR pathway","official_url":"https://www.ema.europa.eu/en/assessment-public-health-risks-related-antimicrobial-resistance-acquired-environment-resulting-use-veterinary-medicinal-product-scientific-guideline"},
        {"id":"EMA-POORLY-EXTRACTABLE","title":"Poorly extractable and/or non-radiolabelled substances","reference":"EMA/CVMP/ERA/349254/2014 Rev.1","status":"current effective reflection paper","effective":"last updated 26 July 2024","scope":"OECD 307 and strongly sorbing/problematic substances","official_url":"https://www.ema.europa.eu/en/poorly-extractable-or-non-radiolabelled-substances-scientific-guideline"}
    ],
}


def animal_profiles() -> list[dict[str, Any]]:
    return ANIMAL_PROFILES


def get_profile(key: str) -> dict[str, Any]:
    try:
        return PROFILE_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"Unknown veterinary animal profile: {key}") from exc


def correct_dt50_temperature(
    dt50_value: float,
    source_temperature_c: float,
    target_temperature_c: float,
    theta: float = 1.047,
) -> float:
    """Correct a half-life. A colder target increases DT50 when theta > 1."""
    if dt50_value <= 0 or theta <= 0:
        raise ValueError("DT50 and theta must be positive")
    return dt50_value * theta ** (source_temperature_c - target_temperature_c)


def biowin_manure_dt50_hours(biowin4_value: float) -> float:
    """Outlier benchmark compatibility equation, not an official regulatory default."""
    return 10 ** (6.0 - biowin4_value) / 10.0


def _dose_mg_kg_day(payload: dict[str, Any], body_weight_kg: float) -> float:
    value = float(payload["dose_value"])
    unit = payload["dose_unit"]
    if unit == "mg_per_kg_bw_day":
        return value
    if unit == "mg_per_animal_day":
        return value / body_weight_kg
    if unit == "g_per_animal_day":
        return value * 1000.0 / body_weight_kg
    raise ValueError(f"Unsupported dose unit: {unit}")


def _profile_parameters(payload: dict[str, Any], profile: dict[str, Any]) -> dict[str, float]:
    def select(name: str, profile_name: str | None = None) -> float | None:
        raw = payload.get(name)
        if raw is not None:
            return float(raw)
        return profile.get(profile_name or name)

    body_weight = select("body_weight_kg")
    if body_weight is None:
        raise ValueError("body_weight_kg is required for this animal profile")
    return {
        "body_weight_kg": body_weight,
        "turnover_per_year": select("turnover_per_year") or 1.0,
        "nitrogen_kg_place_year": select("nitrogen_kg_place_year") or 0.0,
        "housing_factor": select("housing_factor") or 1.0,
    }


def phase_i_decision(payload: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile(payload["animal_profile_key"])
    path: list[dict[str, Any]] = []

    def record(question: str, answer: bool, consequence: str) -> None:
        path.append({"question": question, "answer": answer, "consequence": consequence})

    if payload.get("legally_exempt", False):
        record("Legally exempt?", True, "Stop Phase I; retain jurisdictional documentation")
        return _phase_i_result(profile, "phase_i_stop", "Legal or regulatory exemption", path)
    record("Legally exempt?", False, "Continue")

    if payload.get("natural_substance_no_distribution_change", False):
        record("Natural substance with no altered environmental concentration/distribution?", True, "Stop")
        return _phase_i_result(profile, "phase_i_stop", "Natural substance/no distribution change", path)
    record("Natural substance with no altered environmental concentration/distribution?", False, "Continue")

    if not profile.get("food_animal", False):
        concern = payload.get("parasiticide", False) or payload.get("specific_environmental_concern", False)
        record("Used only in non-food animals?", True, "Normally stop unless a specific concern exists")
        if not concern:
            return _phase_i_result(profile, "phase_i_stop", "Non-food animal with no identified exceptional concern", path)
        path.append({"question": "Specific environmental concern?", "answer": True, "consequence": "Tailored assessment"})
        return _phase_i_result(profile, "tailored_assessment", "Companion-animal concern pathway", path)
    record("Used only in non-food animals?", False, "Continue")

    if payload.get("minor_species_equivalent", False):
        record("Minor species covered by comparable major-species EIA?", True, "Stop if route, rearing and total dose are not greater")
        return _phase_i_result(profile, "phase_i_stop", "Minor-species equivalence accepted subject to documented comparability", path)
    record("Minor species covered by comparable major-species EIA?", False, "Continue")

    if payload.get("small_number_treated", False):
        record("Only an individual or small number treated?", True, "Stop")
        return _phase_i_result(profile, "phase_i_stop", "Small number of animals treated", path)
    record("Only an individual or small number treated?", False, "Continue")

    if payload.get("extensively_metabolized", False):
        record("Extensively metabolised?", True, "Stop if supported by residue/excretion evidence")
        return _phase_i_result(profile, "phase_i_stop", "Extensive metabolism supported", path)
    record("Extensively metabolised?", False, "Continue")

    branch = profile["branch"]
    if payload.get("waste_entry_prevented", False):
        record("Entry prevented through waste-matrix disposal?", True, "Stop with documentation")
        return _phase_i_result(profile, "phase_i_stop", "Environmental entry prevented", path)

    if branch == "aquaculture":
        if not payload.get("aquatic_confined", False):
            return _phase_i_result(profile, "phase_ii", "Open aquaculture system/direct environmental introduction", path)
        if payload.get("parasiticide", False):
            return _phase_i_result(profile, "phase_ii", "Aquaculture ecto/endoparasiticide", path)
        eic = payload.get("eic_aquatic_ug_l")
        if eic is not None and float(eic) < GUIDANCE["phase_i"]["aquatic_trigger_ug_l"]:
            return _phase_i_result(profile, "phase_i_stop", "Confined aquaculture EIC below Phase I trigger", path)
        return _phase_i_result(profile, "phase_ii", "Aquatic exposure exceeds or has not demonstrated the Phase I trigger", path)

    if branch == "pasture" and payload.get("parasiticide", False):
        return _phase_i_result(profile, "phase_ii", "Pasture ecto/endoparasiticide: dung-fauna concern", path)

    pec = payload.get("pec_soil_ug_kg")
    if pec is not None and float(pec) < GUIDANCE["phase_i"]["soil_trigger_ug_kg"]:
        return _phase_i_result(profile, "phase_i_stop", "PECsoil below Phase I trigger", path)
    return _phase_i_result(profile, "phase_ii", "Terrestrial exposure exceeds or has not demonstrated the Phase I trigger", path)


def _phase_i_result(profile: dict[str, Any], outcome: str, reason: str, path: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "animal_profile": profile,
        "outcome": outcome,
        "reason": reason,
        "branch": profile["branch"],
        "decision_path": path,
        "phase_i_triggers": {
            "aquatic_eic_ug_l": GUIDANCE["phase_i"]["aquatic_trigger_ug_l"],
            "soil_pec_ug_kg": GUIDANCE["phase_i"]["soil_trigger_ug_kg"],
        },
        "requires_professional_review": True,
    }


def _study_plan(branch: str, parasiticide: bool, log_kow: float | None, rq_values: dict[str, float | None]) -> dict[str, Any]:
    tier_a = {
        "physicochemical": ["OECD 105 water solubility", "OECD 112 dissociation", "OECD 101 UV/Vis", "OECD 102 melting point", "OECD 104 vapour pressure", "OECD 107/117 logKow/logD as applicable"],
        "fate": ["OECD 106 adsorption/desorption (Kd and Koc across soils)"],
        "effects": [],
    }
    if branch == "aquaculture":
        tier_a["fate"].append("OECD 308 aquatic-sediment transformation")
        tier_a["effects"] = ["OECD 201 algae", "OECD 202 aquatic invertebrate", "OECD 203 fish acute"]
    else:
        tier_a["fate"].append("OECD 307 soil transformation")
        tier_a["effects"] = ["OECD 216 nitrogen transformation", "OECD 208 terrestrial plants", "OECD 220/222 soil invertebrates", "OECD 201 algae", "OECD 202 aquatic invertebrate", "OECD 203 fish acute"]
    if parasiticide and branch == "pasture":
        tier_a["effects"].extend(["Dung fly larvae", "Dung beetle larvae"])

    tier_b: list[str] = []
    if log_kow is not None and log_kow >= 4:
        tier_b.append("Consider OECD 305 bioconcentration")
    if any(v is not None and v >= 1 for v in rq_values.values()):
        tier_b.extend(["Chronic testing only for affected taxonomic levels", "Refine PEC before additional effects testing"])
    return {"tier_a": tier_a, "tier_b_triggers": tier_b}


def _annual_pulse_accumulation_ug_kg(
    annual_increment_ug_kg: float,
    soil_dt50_days: float | None,
    years: int,
) -> list[dict[str, float]]:
    """Annual pulse accumulation in soil with first-order loss between applications.

    This is used only for soil persistence/accumulation. Manure-storage DT50 is
    deliberately not used here because GL38 section 2.7 refers to persistence in soil.
    """
    if annual_increment_ug_kg < 0:
        raise ValueError("annual soil increment cannot be negative")
    if years < 1:
        raise ValueError("soil_accumulation_years must be at least 1")
    if soil_dt50_days is not None and soil_dt50_days <= 0:
        raise ValueError("soil_dt50_days must be positive")
    decay = 1.0 if soil_dt50_days is None else math.exp(-math.log(2.0) * 365.0 / soil_dt50_days)
    rows: list[dict[str, float]] = []
    post = 0.0
    for year in range(1, years + 1):
        post = post * decay + annual_increment_ug_kg
        rows.append({
            "year": year,
            "post_application_ug_kg": post,
            "pre_next_application_ug_kg": post * decay,
        })
    return rows


def run_veterinary_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile(payload["animal_profile_key"])
    params = _profile_parameters(payload, profile)
    bw = params["body_weight_kg"]
    dose = _dose_mg_kg_day(payload, bw)
    duration = float(payload["treatment_duration_days"])
    fraction_treated = float(payload.get("fraction_treated", 1.0))
    excreted_fraction = float(payload.get("excreted_fraction", 1.0))
    branch = payload.get("branch_override") or profile["branch"]

    if not 0 <= fraction_treated <= 1 or not 0 <= excreted_fraction <= 1:
        raise ValueError("Fractions must lie between 0 and 1")

    dt50 = None
    dt50_source = None
    if payload.get("manure_dt50_value") is not None:
        dt50 = float(payload["manure_dt50_value"])
        if payload.get("manure_dt50_unit") == "hours":
            dt50 /= 24.0
        dt50_source = "user_provided"
    elif payload.get("biowin4_value") is not None:
        hours_25 = biowin_manure_dt50_hours(float(payload["biowin4_value"]))
        hours_target = correct_dt50_temperature(
            hours_25,
            float(payload.get("source_temperature_c", 25.0)),
            float(payload.get("target_temperature_c", 10.0)),
            float(payload.get("temperature_factor_theta", 1.047)),
        )
        dt50 = hours_target / 24.0
        dt50_source = "outlier_biowin_screening"
    elif payload.get("manure_storage_days", 0) > 0:
        dt50_source = "not_available"

    # GL38 section 2.7 concerns persistence in SOIL, not manure storage.
    # Keep the two degradation domains separate so a manure DT50 can never
    # silently trigger or parameterise a soil-accumulation calculation.
    soil_dt50_days = float(payload["soil_dt50_days"]) if payload.get("soil_dt50_days") is not None else None
    supplied_soil_dt90 = float(payload["soil_dt90_days"]) if payload.get("soil_dt90_days") is not None else None
    calculated_soil_dt90 = soil_dt50_days * 3.321928094887362 if soil_dt50_days is not None else None
    soil_dt90_days = supplied_soil_dt90 if supplied_soil_dt90 is not None else calculated_soil_dt90
    persistence_flag = bool(soil_dt90_days is not None and soil_dt90_days > 365.0)

    calculations: dict[str, Any]
    if branch == "intensive":
        calculations = _run_intensive(payload, params, dose, duration, fraction_treated, excreted_fraction, dt50)
    elif branch == "pasture":
        calculations = _run_pasture(payload, params, dose, duration, fraction_treated, excreted_fraction)
    elif branch == "aquaculture":
        calculations = _run_aquaculture(payload, params, dose, duration, fraction_treated, excreted_fraction)
    elif branch in {"companion", "special", "custom"}:
        calculations = _run_custom(payload, params, dose, duration, fraction_treated, excreted_fraction)
    else:
        raise ValueError(f"Unsupported veterinary branch: {branch}")

    pecs = calculations.get("pecs", {})

    # Repeated annual soil application is calculated from the branch-specific
    # annual PEC increment. It is a separate fate calculation from manure storage.
    soil_increment = pecs.get("soil_refined_ug_kg", pecs.get("soil_initial_ug_kg"))
    accumulation = None
    if branch in {"intensive", "pasture"} and soil_increment is not None:
        years = int(payload.get("soil_accumulation_years", 10))
        if soil_dt50_days is not None or years > 1:
            series = _annual_pulse_accumulation_ug_kg(float(soil_increment), soil_dt50_days, years)
            accumulation = {
                "annual_increment_ug_kg": float(soil_increment),
                "soil_dt50_days": soil_dt50_days,
                "soil_dt90_days": soil_dt90_days,
                "years": years,
                "series": series,
                "final_post_application_ug_kg": series[-1]["post_application_ug_kg"],
                "final_pre_next_application_ug_kg": series[-1]["pre_next_application_ug_kg"],
                "method": "annual pulse with first-order soil degradation between applications",
            }
            calculations["soil_accumulation"] = accumulation

    p_nec = {
        "soil": payload.get("soil_pnec_ug_kg"),
        "surface_water": payload.get("aquatic_pnec_ug_l"),
        "sediment": payload.get("sediment_pnec_ug_kg"),
        "dung": payload.get("dung_pnec_ug_kg"),
    }
    rq = {
        "soil": _rq(pecs.get("soil_refined_ug_kg", pecs.get("soil_initial_ug_kg")), p_nec["soil"]),
        "surface_water": _rq(pecs.get("surface_water_refined_ug_l", pecs.get("surface_water_initial_ug_l")), p_nec["surface_water"]),
        "sediment": _rq(pecs.get("sediment_ug_kg"), p_nec["sediment"]),
        "dung": _rq(pecs.get("dung_refined_ug_kg", pecs.get("dung_initial_ug_kg")), p_nec["dung"]),
    }
    legacy = None
    if payload.get("earthworm_ld50_ug_kg") and pecs.get("soil_refined_ug_kg") is not None:
        legacy = pecs["soil_refined_ug_kg"] / float(payload["earthworm_ld50_ug_kg"])

    warnings = list(calculations.get("warnings", []))
    if dt50_source == "outlier_biowin_screening":
        warnings.append("BIOWIN-derived manure DT50 is a transparent benchmark/screening estimate, not an official VICH/EMA fate study.")
    if supplied_soil_dt90 is not None and calculated_soil_dt90 is not None:
        relative_difference = abs(supplied_soil_dt90 - calculated_soil_dt90) / supplied_soil_dt90 if supplied_soil_dt90 else 0.0
        if relative_difference > 0.05:
            warnings.append("Supplied soil DT90 is not consistent with first-order DT90 = 3.32193 × DT50; retain the selected kinetic basis and review the inputs.")
    if persistence_flag and branch in {"intensive", "pasture"}:
        warnings.append(
            "Soil DT90 exceeds 1 year (VICH GL38 section 2.7). The multi-year annual-pulse "
            "series is therefore part of the assessment and should be reviewed even when the "
            "single-application RQ is below one."
        )
    if soil_dt50_days is None and branch in {"intensive", "pasture"} and int(payload.get("soil_accumulation_years", 10)) > 1:
        warnings.append("No reviewed soil DT50 was supplied; the multi-year soil series assumes no degradation and is deliberately conservative.")
    if legacy is not None:
        warnings.append("Earthworm LD50 quotient is a prioritisation metric only; it is not the VICH regulatory RQ, which uses PEC/PNEC.")
    if profile.get("custom_required"):
        warnings.append("This profile has no asserted official numeric default. Jurisdiction-specific animal and husbandry inputs must be reviewed.")

    return {
        "chemical_name": payload["chemical_name"],
        "animal_profile": profile,
        "branch": branch,
        "normalised_inputs": {
            "dose_mg_kg_bw_day": dose,
            "body_weight_kg": bw,
            "treatment_duration_days": duration,
            "fraction_treated": fraction_treated,
            "excreted_fraction": excreted_fraction,
            **params,
            "manure_dt50_target_days": dt50,
            "manure_dt50_source": dt50_source,
            "soil_dt50_days": soil_dt50_days,
            "soil_dt90_days": soil_dt90_days,
            "persistence_flag_soil_dt90_over_1_year": persistence_flag,
            "soil_accumulation_years": int(payload.get("soil_accumulation_years", 10)),
        },
        "calculations": calculations,
        "regulatory_rq": rq,
        "outlier_earthworm_ld50_prioritisation_quotient": legacy,
        "decision": _decision(rq),
        "study_plan": _study_plan(branch, bool(payload.get("parasiticide", False)), payload.get("log_kow"), rq),
        "guidance_basis": GUIDANCE,
        "warnings": warnings,
        "requires_professional_review": True,
    }


def _run_intensive(payload, params, dose, duration, fraction_treated, excreted_fraction, dt50_days):
    ny = params["nitrogen_kg_place_year"]
    if ny <= 0:
        raise ValueError("nitrogen_kg_place_year is required and must be positive for intensive-animal PECsoil")
    bw = params["body_weight_kg"]
    p = params["turnover_per_year"]
    h = params["housing_factor"]
    events = float(payload.get("treatment_events_per_year", 1.0))
    n_limit = float(payload.get("nitrogen_spreading_limit_kg_ha", 170.0))
    bulk = float(payload.get("soil_bulk_density_kg_m3", 1500.0))
    depth = float(payload.get("soil_depth_m", 0.05))
    soil_mass = bulk * 10000.0 * depth

    annual_administered_mass_mg_per_place = dose * duration * bw * p * fraction_treated * events
    initial = annual_administered_mass_mg_per_place * n_limit / (soil_mass * ny * h) * 1000.0

    storage_days = float(payload.get("manure_storage_days", 0.0))
    storage_basis = payload.get("storage_time_basis", "mean_age_half_duration")
    effective_storage = storage_days / 2.0 if storage_basis == "mean_age_half_duration" else storage_days
    if storage_days and dt50_days:
        remaining_fraction = math.exp(-math.log(2.0) * effective_storage / dt50_days)
    else:
        remaining_fraction = 1.0

    excreted_mass_before_storage_mg = annual_administered_mass_mg_per_place * excreted_fraction
    remaining_mass_mg = excreted_mass_before_storage_mg * remaining_fraction
    refined = remaining_mass_mg * n_limit / (soil_mass * ny * h) * 1000.0

    return {
        "method": "VICH/EMA-style intensive-animal annual total-residue screen with excretion and manure-storage refinement",
        "pecs": {"soil_initial_ug_kg": initial, "soil_refined_ug_kg": refined},
        "mass_balance": {
            "annual_administered_mass_mg_per_place": annual_administered_mass_mg_per_place,
            "annual_excreted_mass_before_storage_mg_per_place": excreted_mass_before_storage_mg,
            "effective_storage_days": effective_storage,
            "remaining_fraction_after_storage": remaining_fraction,
            "remaining_mass_mg_per_place": remaining_mass_mg,
            "turnover_per_year": p,
            "treatment_events_per_year": events,
        },
        "assumptions": {
            "soil_mass_kg_ha": soil_mass,
            "nitrogen_spreading_limit_kg_ha": n_limit,
            "initial_total_residue_fraction": 1.0,
        },
        "warnings": ([] if dt50_days or storage_days == 0 else ["No manure DT50 was available; storage degradation was not applied."]),
    }

def _run_pasture(payload, params, dose, duration, fraction_treated, excreted_fraction):
    stocking = payload.get("stocking_density_animals_ha")
    if stocking is None:
        raise ValueError("stocking_density_animals_ha is required for pasture PECsoil")
    events = float(payload.get("treatment_events_per_year", 1.0))
    bulk = float(payload.get("soil_bulk_density_kg_m3", 1500.0))
    depth = float(payload.get("soil_depth_m", 0.05))
    soil_mass = bulk * 10000.0 * depth
    total_dose_mg_ha = dose * duration * params["body_weight_kg"] * float(stocking) * fraction_treated * events
    soil_initial = total_dose_mg_ha * 1000.0 / soil_mass
    soil_refined = soil_initial * excreted_fraction
    dung_output = payload.get("dung_output_kg_animal_day")
    dung_initial = dung_refined = None
    if dung_output:
        one_animal_treatment_mg = dose * duration * params["body_weight_kg"]
        dung_initial = one_animal_treatment_mg * 1000.0 / float(dung_output)
        excretion_days = float(payload.get("excretion_duration_days", max(duration, 1.0)))
        faecal_fraction = float(payload.get("faecal_excretion_fraction", excreted_fraction))
        dung_refined = one_animal_treatment_mg * faecal_fraction * 1000.0 / (float(dung_output) * excretion_days)
    return {
        "method": "VICH pasture direct-excretion screen",
        "pecs": {"soil_initial_ug_kg": soil_initial, "soil_refined_ug_kg": soil_refined, "dung_initial_ug_kg": dung_initial, "dung_refined_ug_kg": dung_refined},
        "mass_balance": {"total_dose_mg_ha": total_dose_mg_ha},
        "assumptions": {"soil_mass_kg_ha": soil_mass, "stocking_density_animals_ha": float(stocking), "initial_total_residue_fraction": 1.0},
        "warnings": ["Pasture residues are spatially patchy even though the screening calculation assumes even distribution."],
    }


def _run_aquaculture(payload, params, dose, duration, fraction_treated, excreted_fraction):
    biomass = payload.get("treated_biomass_kg")
    water_volume = payload.get("facility_water_volume_l")
    if biomass is None or water_volume is None:
        raise ValueError("treated_biomass_kg and facility_water_volume_l are required for aquaculture")
    total_dose_mg = dose * float(biomass) * duration * fraction_treated
    initial_eic = total_dose_mg * 1000.0 / float(water_volume)
    directly_released = float(payload.get("direct_water_release_fraction", 0.0))
    uneaten = float(payload.get("uneaten_feed_fraction", 0.0))
    refined_mass_mg = total_dose_mg * (directly_released + excreted_fraction)
    dilution = float(payload.get("receiving_water_dilution_factor", 1.0))
    refined_sw = refined_mass_mg * 1000.0 / float(water_volume) / dilution
    sediment = None
    area = payload.get("sediment_area_m2")
    depth = payload.get("sediment_depth_m")
    density = payload.get("sediment_density_kg_m3")
    if area and depth and density:
        sediment_mass = float(area) * float(depth) * float(density)
        faecal_fraction = float(payload.get("faecal_excretion_fraction", excreted_fraction))
        sediment_input_mg = total_dose_mg * (uneaten + faecal_fraction)
        sediment = sediment_input_mg * 1000.0 / sediment_mass
    return {
        "method": "VICH aquaculture total-residue and refinement screen",
        "pecs": {"surface_water_initial_ug_l": initial_eic, "surface_water_refined_ug_l": refined_sw, "sediment_ug_kg": sediment},
        "mass_balance": {"total_dose_mg": total_dose_mg, "refined_released_mass_mg": refined_mass_mg},
        "assumptions": {"receiving_water_dilution_factor": dilution, "initial_total_residue_fraction": 1.0},
        "warnings": ["Open-system dispersion, currents, tides, salinity and pulse dosing require region- and facility-specific refinement."],
    }


def _run_custom(payload, params, dose, duration, fraction_treated, excreted_fraction):
    total_mg = dose * params["body_weight_kg"] * duration * fraction_treated
    return {
        "method": "Custom veterinary exposure record",
        "pecs": {},
        "mass_balance": {"administered_mass_mg_per_treated_animal": total_mg, "estimated_excreted_mass_mg": total_mg * excreted_fraction},
        "assumptions": {},
        "warnings": ["No generic PEC is calculated for this branch without a documented release scenario."],
    }


def _rq(pec: float | None, pnec: float | None) -> float | None:
    if pec is None or pnec is None:
        return None
    return float(pec) / float(pnec)


def _decision(rq: dict[str, float | None]) -> dict[str, Any]:
    available = {k: v for k, v in rq.items() if v is not None}
    if not available:
        return {"status": "exposure_only", "message": "PECs calculated where possible; reviewed PNECs are required for regulatory RQ."}
    failing = {k: v for k, v in available.items() if v >= 1.0}
    if failing:
        return {"status": "refine_or_test", "message": "At least one RQ is ≥1; refine exposure and consider Tier B for affected compartments.", "failing": failing}
    return {"status": "screen_pass", "message": "All available RQs are <1, subject to persistence/accumulation and professional review."}
