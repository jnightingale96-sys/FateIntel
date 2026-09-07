from __future__ import annotations

from typing import Any

from .pharma_consumption import oecd_2025_lookup


DOSE_UNIT_TO_G = {"ug": 1e-6, "mg": 1e-3, "g": 1.0}
DAILY_UNIT_TO_G = {"mg": 1e-3, "g": 1.0, "kg": 1000.0}
EMA_DEFAULT_FPEN = 0.01
EMA_DEFAULT_WASTEWATER_L_INHAB_DAY = 200.0
EMA_DEFAULT_DILUTION = 10.0
EMA_DEFAULT_STP_CAPACITY = 10_000
EMA_PHASE_II_TRIGGER_UG_L = 0.01


def _source_warnings(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    mode = payload.get("emission_mode")
    if mode in {"ema_phase_i", "ema_phase_ii", "screening_spc", "oecd_class_screen"}:
        source_type = payload.get("spc_source_type")
        if source_type != "official_regulatory":
            warnings.append("The dosage source is not marked as an official SPC or regulatory source.")
        text = " ".join(str(payload.get(key) or "").lower() for key in ("spc_title", "spc_url"))
        if "drugs.com" in text or "wikipedia" in text or "mayoclinic" in text:
            warnings.append("A secondary website is present in the dosage source. Confirm the dose against an official SPC.")
        if not payload.get("spc_title"):
            warnings.append("No SPC or product source title was supplied.")
        if not payload.get("spc_url") and not payload.get("spc_identifier"):
            warnings.append("No SPC URL or source identifier was supplied.")
    if mode in {"screening_spc", "oecd_class_screen", "refined_annual_use", "direct_daily_use"} and not payload.get("consumption_source_title"):
        warnings.append("No consumption-data source title was supplied.")
    return warnings


def _route_warnings(payload: dict[str, Any]) -> list[str]:
    route = payload.get("administration_route", "oral")
    direct = payload["direct_to_sewer_fraction"]
    systemic = payload["systemic_fraction"]
    warnings: list[str] = []
    if route != "oral" and direct == 0 and systemic == 1:
        warnings.append("A non-oral route is using the oral-style default of zero direct release and complete systemic availability. Review route-specific fractions.")
    if route in {"topical", "ophthalmic", "otic", "oral_rinse", "vaginal"} and direct == 0:
        warnings.append("The selected formulation may enter wastewater through wash-off or disposal, but direct-to-sewer release is zero.")
    return warnings


def _ema_fpen(payload: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    method = payload.get("ema_fpen_mode", "default")
    if method == "default":
        return EMA_DEFAULT_FPEN, {
            "mode": "default",
            "fpen": EMA_DEFAULT_FPEN,
            "basis": "EMA Phase I default: 1% of the population receives the active substance daily.",
        }
    if method == "user":
        value = float(payload.get("market_penetration_fraction", EMA_DEFAULT_FPEN))
        return value, {"mode": "user", "fpen": value, "basis": "User-supplied market penetration fraction."}
    if method == "prevalence_treatment":
        prevalence = payload.get("prevalence_fraction")
        treatment_days = payload.get("treatment_days")
        treatments_per_year = payload.get("treatments_per_year")
        if prevalence is None or treatment_days is None or treatments_per_year is None:
            raise ValueError("prevalence_fraction, treatment_days and treatments_per_year are required for refined FPEN")
        value = float(prevalence) * float(treatment_days) * float(treatments_per_year) / 365.0
        if value > 1:
            raise ValueError("Refined FPEN cannot exceed 1")
        return value, {
            "mode": "prevalence_treatment",
            "fpen": value,
            "prevalence_fraction": float(prevalence),
            "treatment_days": float(treatment_days),
            "treatments_per_year": float(treatments_per_year),
            "equation": "FPEN_refined = prevalence × treatment_days × treatments_per_year / 365",
        }
    raise ValueError(f"Unsupported EMA FPEN mode: {method}")


def _daily_administered_mass(payload: dict[str, Any]) -> tuple[float, dict[str, Any], dict[str, Any] | None]:
    """Return administered active mass (g/day), dosage detail and optional regulatory metadata."""
    mode = payload["emission_mode"]
    population = payload["population"]

    if mode in {"screening_spc", "oecd_class_screen"}:
        dose_unit = payload["dose_unit"]
        if dose_unit not in DOSE_UNIT_TO_G:
            raise ValueError(f"Unsupported dose unit: {dose_unit}")
        dose_per_administration_g = payload["dose_per_administration"] * DOSE_UNIT_TO_G[dose_unit]
        maximum_daily_dose_g = dose_per_administration_g * payload["administrations_per_day"]
        lookup = None
        ddd_rate = float(payload["therapeutic_class_ddd_per_1000_day"])
        if mode == "oecd_class_screen":
            lookup = oecd_2025_lookup(payload["oecd_class_key"], payload["oecd_country"])
            ddd_rate = lookup["ddd_per_1000_people_day"]
        administered_g_per_1000_day = ddd_rate * maximum_daily_dose_g
        administered_g_day = administered_g_per_1000_day * population / 1000.0
        return administered_g_day, {
            "mode": mode,
            "dose_per_administration_g": dose_per_administration_g,
            "administrations_per_day": payload["administrations_per_day"],
            "maximum_daily_dose_g": maximum_daily_dose_g,
            "therapeutic_class_ddd_per_1000_day": ddd_rate,
            "administered_g_per_1000_day": administered_g_per_1000_day,
            "oecd_2025_lookup": lookup,
        }, None

    if mode == "refined_annual_use":
        administered_g_day = payload["refined_annual_active_kg"] * 1000.0 / payload["emitting_days_per_year"]
        return administered_g_day, {
            "mode": mode,
            "refined_annual_active_kg": payload["refined_annual_active_kg"],
            "emitting_days_per_year": payload["emitting_days_per_year"],
            "administered_g_per_1000_day": administered_g_day * 1000.0 / population,
        }, None

    if mode == "direct_daily_use":
        unit = payload["daily_active_unit"]
        if unit not in DAILY_UNIT_TO_G:
            raise ValueError(f"Unsupported daily active unit: {unit}")
        amount = float(payload["daily_active_amount"])
        administered_g_day = amount * DAILY_UNIT_TO_G[unit]
        return administered_g_day, {
            "mode": mode,
            "original_daily_active_amount": amount,
            "original_daily_active_unit": f"{unit}/day",
            "normalised_g_day": administered_g_day,
            "normalised_kg_day": administered_g_day / 1000.0,
            "administered_g_per_1000_day": administered_g_day * 1000.0 / population,
        }, None

    if mode in {"ema_phase_i", "ema_phase_ii"}:
        fpen, fpen_detail = _ema_fpen(payload)
        dose_mg = float(payload["maximum_daily_dose_mg"])
        stp_capacity = int(payload.get("regulatory_stp_capacity_inhabitants") or EMA_DEFAULT_STP_CAPACITY)
        administered_g_day = dose_mg * fpen * stp_capacity / 1000.0
        regulatory = {
            "framework": "EMA human medicinal product ERA Revision 1 (effective 1 September 2024)",
            "phase": "Phase I" if mode == "ema_phase_i" else "Phase II exposure refinement",
            "maximum_daily_dose_mg_patient_day": dose_mg,
            "fpen": fpen_detail,
            "stp_capacity_inhabitants": stp_capacity,
            "wastewater_l_inhabitant_day": float(payload["wastewater_l_person_day"]),
            "dilution_factor": float(payload.get("dilution_factor", EMA_DEFAULT_DILUTION)),
            "surface_water_action_limit_ug_l": EMA_PHASE_II_TRIGGER_UG_L,
        }
        return administered_g_day, {
            "mode": mode,
            "maximum_daily_dose_mg_patient_day": dose_mg,
            "population_receiving_active_daily": stp_capacity * fpen,
            "administered_g_day_at_reference_stp": administered_g_day,
        }, regulatory

    raise ValueError(f"Unsupported emission mode: {mode}")


def run_pharmaceutical_emission(payload: dict[str, Any]) -> dict[str, Any]:
    """Calculate use -> sewer mass -> untreated wastewater concentration.

    Human pharmaceutical modes keep the regulatory screening route, class-use
    prioritisation route and site/catchment-use route distinct. Parent and named
    metabolites are normally calculated on a molar basis before the WWTP step.
    EMA Phase I deliberately uses the total-residue assumption (100% parent,
    no metabolism, no STP removal) required by that screening calculation.
    """
    mode = payload["emission_mode"]
    parent_mw = payload["parent_molecular_weight_g_mol"]
    days = payload["emitting_days_per_year"]
    catchment_population = payload["population"]
    water_l_person_day = float(payload["wastewater_l_person_day"])
    direct_fraction = payload["direct_to_sewer_fraction"]
    systemic_fraction = payload["systemic_fraction"]
    parent_urine = payload["parent_urine_fraction"]
    parent_faeces = payload["parent_faeces_fraction"]
    metabolites = payload.get("metabolites", [])

    if direct_fraction + systemic_fraction > 1 + 1e-12:
        raise ValueError("Direct-to-sewer and systemic fractions cannot sum to more than 1.")

    parent_systemic_excretion_fraction = parent_urine + parent_faeces
    metabolite_fraction_sum = sum(m["molar_fraction"] for m in metabolites)
    if parent_systemic_excretion_fraction + metabolite_fraction_sum > 1 + 1e-12:
        raise ValueError("Unchanged parent and metabolite molar fractions cannot sum to more than 1 within the systemic fraction.")

    administered_g_day, dosage_details, regulatory = _daily_administered_mass(payload)

    is_ema = mode in {"ema_phase_i", "ema_phase_ii"}
    population_for_flow = int(payload.get("regulatory_stp_capacity_inhabitants") or EMA_DEFAULT_STP_CAPACITY) if is_ema else catchment_population
    flow_override = payload.get("wastewater_flow_m3_day_override")
    if is_ema:
        flow_l_day = population_for_flow * water_l_person_day
        flow_source = "regulatory STP capacity × wastewater per inhabitant"
    elif flow_override is not None:
        flow_l_day = float(flow_override) * 1000.0
        flow_source = "user-entered WWTP flow"
    else:
        flow_l_day = catchment_population * water_l_person_day
        flow_source = "catchment population × wastewater per inhabitant"
    if flow_l_day <= 0:
        raise ValueError("Wastewater flow must be positive")
    flow_m3_day = flow_l_day / 1000.0

    administered_mol_day = administered_g_day / parent_mw

    if mode == "ema_phase_i":
        # EMA Phase I total-residue approach: no patient metabolism, no STP loss.
        direct_parent_mol_day = 0.0
        parent_urine_mol_day = administered_mol_day
        parent_faeces_mol_day = 0.0
        parent_influent_mol_day = administered_mol_day
        parent_influent_g_day = administered_g_day
        species = [{
            "species_key": "parent",
            "name": payload["parent_name"],
            "species_type": "parent_total_residue_screen",
            "molecular_weight_g_mol": parent_mw,
            "moles_day": parent_influent_mol_day,
            "mass_g_day": parent_influent_g_day,
            "mass_kg_day": parent_influent_g_day / 1000.0,
            "influent_concentration_ug_l": parent_influent_g_day * 1e6 / flow_l_day,
            "components": {"ema_total_residue_mol_day": parent_influent_mol_day},
            "evidence_type": "regulatory_default_total_residue",
        }]
        recovered_parent_equivalent_fraction = 1.0
        unallocated_fraction = 0.0
        unrecovered_systemic_fraction = 0.0
    else:
        direct_parent_mol_day = administered_mol_day * direct_fraction
        systemic_parent_equivalent_mol_day = administered_mol_day * systemic_fraction
        parent_urine_mol_day = systemic_parent_equivalent_mol_day * parent_urine
        parent_faeces_mol_day = systemic_parent_equivalent_mol_day * parent_faeces
        parent_influent_mol_day = direct_parent_mol_day + parent_urine_mol_day + parent_faeces_mol_day
        parent_influent_g_day = parent_influent_mol_day * parent_mw

        species = [{
            "species_key": "parent",
            "name": payload["parent_name"],
            "species_type": "parent",
            "molecular_weight_g_mol": parent_mw,
            "moles_day": parent_influent_mol_day,
            "mass_g_day": parent_influent_g_day,
            "mass_kg_day": parent_influent_g_day / 1000.0,
            "influent_concentration_ug_l": parent_influent_g_day * 1e6 / flow_l_day,
            "components": {
                "direct_to_sewer_mol_day": direct_parent_mol_day,
                "urinary_parent_mol_day": parent_urine_mol_day,
                "faecal_parent_mol_day": parent_faeces_mol_day,
            },
            "evidence_type": "mixed_user_and_source_input",
        }]
        for index, metabolite in enumerate(metabolites, start=1):
            metabolite_moles = systemic_parent_equivalent_mol_day * metabolite["molar_fraction"]
            metabolite_mass_g = metabolite_moles * metabolite["molecular_weight_g_mol"]
            species.append({
                "species_key": metabolite.get("species_key") or f"metabolite-{index}",
                "name": metabolite["name"],
                "species_type": "metabolite",
                "molecular_weight_g_mol": metabolite["molecular_weight_g_mol"],
                "molar_fraction_of_systemic_parent": metabolite["molar_fraction"],
                "moles_day": metabolite_moles,
                "mass_g_day": metabolite_mass_g,
                "mass_kg_day": metabolite_mass_g / 1000.0,
                "influent_concentration_ug_l": metabolite_mass_g * 1e6 / flow_l_day,
                "source_title": metabolite.get("source_title"),
                "source_identifier": metabolite.get("source_identifier"),
                "evidence_type": metabolite.get("evidence_type", "measured"),
            })
        recovered_parent_equivalent_fraction = direct_fraction + systemic_fraction * (parent_systemic_excretion_fraction + metabolite_fraction_sum)
        unallocated_fraction = 1.0 - direct_fraction - systemic_fraction
        unrecovered_systemic_fraction = systemic_fraction * (1.0 - parent_systemic_excretion_fraction - metabolite_fraction_sum)

    parent_influent_ug_l = species[0]["influent_concentration_ug_l"]
    warnings = _source_warnings(payload)
    if mode != "ema_phase_i":
        warnings += _route_warnings(payload)
        if unallocated_fraction > 1e-9:
            warnings.append(f"{unallocated_fraction:.1%} of the administered parent-equivalent amount is outside the direct and systemic route fractions.")
        if unrecovered_systemic_fraction > 1e-9:
            warnings.append(f"{unrecovered_systemic_fraction:.1%} of the administered parent-equivalent amount is systemically available but not assigned to unchanged parent or named metabolites.")
        if not metabolites:
            warnings.append("No named metabolite fractions were supplied; only unchanged parent emission is quantified.")

    if mode in {"screening_spc", "oecd_class_screen"}:
        warnings.append("Therapeutic-class DDD consumption is not compound-specific measured use. The class screen intentionally assigns a class-level rate to the selected active and must be labelled as a conservative prioritisation screen.")
    if mode == "oecd_class_screen":
        warnings.append("OECD Health at a Glance 2025 Figure 9.6 contains four selected chronic-condition medicine categories only; use the live OECD Data Explorer or a reviewed alternative source for other ATC classes.")
    if mode == "ema_phase_i":
        warnings.append("EMA Phase I intentionally assumes 100% excretion as parent, no patient metabolism and no STP degradation or retention.")
    if mode in {"ema_phase_i", "ema_phase_ii"}:
        if abs(water_l_person_day - EMA_DEFAULT_WASTEWATER_L_INHAB_DAY) > 1e-12:
            warnings.append("The EMA default wastewater volume is 200 L/inhabitant/day; a different value is being used and must be justified.")
        if population_for_flow != EMA_DEFAULT_STP_CAPACITY:
            warnings.append("The EMA reference STP capacity is 10,000 inhabitants; a different capacity is being used and must be justified.")

    if regulatory is not None:
        dilution = regulatory["dilution_factor"]
        if mode == "ema_phase_i":
            pecsw_ug_l = parent_influent_ug_l / dilution
            regulatory.update({
                "equation": "PECSW = DOSE_AS × FPEN / (WASTEW_INHAB × DILUTION)",
                "untreated_wastewater_screen_ug_l": parent_influent_ug_l,
                "pec_surface_water_ug_l": pecsw_ug_l,
                "phase_ii_triggered_by_pec": pecsw_ug_l >= EMA_PHASE_II_TRIGGER_UG_L,
                "total_residue_assumption": True,
            })
        else:
            regulatory.update({
                "local_release_to_influent_kg_day": sum(s["mass_kg_day"] for s in species),
                "parent_clocalinf_ug_l": parent_influent_ug_l,
                "equation_note": "Phase II local release and ClocalINF are calculated before SimpleTreat; parent/metabolite excretion is applied before the WWTP.",
                "total_residue_assumption": False,
            })

    return {
        "scenario_name": payload["scenario_name"],
        "emission_mode": mode,
        "product": {
            "product_name": payload.get("product_name"),
            "formulation": payload.get("formulation"),
            "administration_route": payload.get("administration_route"),
            "spc_title": payload.get("spc_title"),
            "spc_identifier": payload.get("spc_identifier"),
            "spc_url": payload.get("spc_url"),
            "spc_access_date": payload.get("spc_access_date"),
            "spc_source_type": payload.get("spc_source_type"),
            "consumption_source_title": payload.get("consumption_source_title"),
            "consumption_source_identifier": payload.get("consumption_source_identifier"),
        },
        "dosage": dosage_details,
        "population": population_for_flow,
        "catchment_population": catchment_population,
        "wastewater_l_person_day": water_l_person_day,
        "wastewater_flow_l_day": flow_l_day,
        "wastewater_flow_m3_day": flow_m3_day,
        "wastewater_flow_source": flow_source,
        "administered": {
            "mass_g_day": administered_g_day,
            "mass_kg_day": administered_g_day / 1000.0,
            "mass_kg_year": administered_g_day * days / 1000.0,
            "moles_day": administered_mol_day,
        },
        "influent": {
            "parent_mass_kg_day": species[0]["mass_kg_day"],
            "parent_concentration_ug_l": parent_influent_ug_l,
            "total_quantified_species_mass_kg_day": sum(s["mass_kg_day"] for s in species),
            "flow_m3_day": flow_m3_day,
            "label": "ClocalINF / untreated wastewater" if mode == "ema_phase_ii" else "WWTP influent / untreated wastewater",
        },
        "regulatory": regulatory,
        "route_fractions": {
            "direct_to_sewer": 0.0 if mode == "ema_phase_i" else direct_fraction,
            "systemic": 1.0 if mode == "ema_phase_i" else systemic_fraction,
            "unallocated": unallocated_fraction,
        },
        "systemic_fractions": {
            "unchanged_parent_urine": 1.0 if mode == "ema_phase_i" else parent_urine,
            "unchanged_parent_faeces": 0.0 if mode == "ema_phase_i" else parent_faeces,
            "named_metabolites": 0.0 if mode == "ema_phase_i" else metabolite_fraction_sum,
            "unrecovered_within_systemic": 0.0 if mode == "ema_phase_i" else (1.0 - parent_systemic_excretion_fraction - metabolite_fraction_sum),
        },
        "recovered_parent_equivalent_fraction": recovered_parent_equivalent_fraction,
        "species": species,
        "warnings": warnings,
        "assumptions": [
            "Use, dose, population and wastewater flow are converted into an explicit daily mass and untreated-wastewater concentration before treatment.",
            "Parent and named metabolite fractions are applied before wastewater treatment except in EMA Phase I, which deliberately uses the total-residue assumption.",
            "Metabolite mass is calculated from parent moles and metabolite molecular weight using an assumed 1:1 molar formation relationship unless a reviewed stoichiometry says otherwise.",
            "Population and per-capita wastewater flow scale together unless an explicit site-specific WWTP flow is supplied in a non-regulatory catchment mode.",
            "No sewer degradation or deconjugation is applied in this emission module.",
            "All source-derived use, dose and excretion values require provenance and scientific review before regulatory use.",
        ],
    }
