from __future__ import annotations

from typing import Any


WORKBOOK_9BOX_CARBAMAZEPINE_FRACTIONS = {
    "air": 1.6806982721404515e-8,
    "effluent": 0.9171874114453539,
    "primary_sludge": 0.007868396178849157,
    "biodegraded": 0.07209507243873131,
    "secondary_sludge": 0.0028491031300824854,
}

CARBAMAZEPINE_CAS = "298-46-4"
CARBAMAZEPINE_INCHIKEY = "FFGPTBGBLSHEPO-UHFFFAOYSA-N"


def _normalise_identity(value: Any) -> str:
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def _is_carbamazepine_parent(payload: dict[str, Any]) -> bool:
    """Return whether the workbook fixture is attached to its verified identity.

    API callers provide the stored chemical identifiers.  The species-name fallback
    keeps the calculation function convenient for its direct regression tests.
    """
    if payload.get("species_key") != "parent":
        return False
    supplied_identity = any(
        payload.get(key) for key in ("chemical_name", "chemical_cas_number", "chemical_inchikey")
    )
    if supplied_identity:
        return any((
            _normalise_identity(payload.get("chemical_name")) == "carbamazepine",
            str(payload.get("chemical_cas_number") or "").strip() == CARBAMAZEPINE_CAS,
            str(payload.get("chemical_inchikey") or "").strip().upper() == CARBAMAZEPINE_INCHIKEY,
        ))
    return _normalise_identity(payload.get("species_name")) == "carbamazepine"


def risk_band(rq: float | None) -> str:
    if rq is None:
        return "insufficient evidence"
    if rq < 0.1:
        return "low"
    if rq < 1:
        return "potential"
    return "high"


def run_activity_simpletreat(payload: dict[str, Any]) -> dict[str, Any]:
    """Run corrected post-emission WWTP mass balance.

    The input mass is already the mass entering wastewater after route, parent
    excretion and metabolite calculations.
    """
    influent_mass = payload["influent_mass_kg_day"]
    flow_m3_day = payload["wastewater_flow_m3_day"]
    model_mode = payload["model_mode"]

    if model_mode == "supplied_workbook_9box_preset":
        if not _is_carbamazepine_parent(payload):
            raise ValueError(
                "The supplied workbook 9-box preset is a Carbamazepine-parent verification fixture only. "
                "Select the Carbamazepine parent record to reproduce the benchmark, or use custom_screening "
                "with substance- and plant-specific fractions."
            )
        fractions = dict(WORKBOOK_9BOX_CARBAMAZEPINE_FRACTIONS)
        model_label = "Supplied Activity SimpleTreat workbook — verified 9-box Carbamazepine preset"
        limitations = [
            "The pathway fractions reproduce the current supplied workbook result for its bundled Carbamazepine and treatment-plant inputs.",
            "Runtime identity validation restricts this verification fixture to the stored Carbamazepine parent record (CAS 298-46-4).",
            "This preset is not a general reimplementation of official SimpleTreat and must not be transferred to another substance or plant without recalculation.",
            "The hard-coded 78.96% effluent value on the workbook Outputs sheet is rejected; the linked 9-box result of 91.718741% is used.",
        ]
    elif model_mode == "custom_screening":
        bio = payload["biodegradation_fraction"]
        primary = payload["primary_sludge_fraction"]
        secondary = payload["secondary_sludge_fraction"]
        air = payload["volatilisation_fraction"]
        total_removal = bio + primary + secondary + air
        if total_removal > 1 + 1e-12:
            raise ValueError("Custom pathway fractions cannot sum to more than 1.")
        fractions = {
            "air": air,
            "effluent": 1.0 - total_removal,
            "primary_sludge": primary,
            "biodegraded": bio,
            "secondary_sludge": secondary,
        }
        model_label = "EnviroChem transparent custom WWTP screening mass balance"
        limitations = [
            "Custom pathway fractions are user supplied and additive.",
            "This is not an official SimpleTreat execution.",
        ]
    else:
        raise ValueError(f"Unsupported WWTP model mode: {model_mode}")

    closure = sum(fractions.values())
    mass_flows = {key: influent_mass * value for key, value in fractions.items()}

    flow_l_day = flow_m3_day * 1000.0
    influent_ug_l = influent_mass * 1e9 / flow_l_day
    effluent_mass = mass_flows["effluent"]
    effluent_ug_l = effluent_mass * 1e9 / flow_l_day

    post_fraction = payload["post_wwtp_biodegradation_fraction"]
    post_degraded_mass = effluent_mass * post_fraction
    receiving_water_input_mass = effluent_mass - post_degraded_mass
    pre_dilution_ug_l = receiving_water_input_mass * 1e9 / flow_l_day
    surface_water_pec = (
        pre_dilution_ug_l / payload["receiving_water_dilution_factor"]
    )

    sludge_mass = (
        mass_flows["primary_sludge"] + mass_flows["secondary_sludge"]
    )
    annual_sludge_to_soil_kg = (
        sludge_mass
        * payload["emitting_days_per_year"]
        * payload["sludge_to_soil_fraction"]
    )
    soil_pec_ug_kg = (
        annual_sludge_to_soil_kg
        * 1e9
        / payload["mixed_soil_mass_kg"]
    )

    aq_pnec = payload.get("aquatic_pnec_ug_l")
    soil_pnec = payload.get("soil_pnec_ug_kg")
    aquatic_rq = surface_water_pec / aq_pnec if aq_pnec else None
    soil_rq = soil_pec_ug_kg / soil_pnec if soil_pnec else None

    return {
        "model_mode": model_mode,
        "model_label": model_label,
        "species_key": payload["species_key"],
        "species_name": payload["species_name"],
        "influent_mass_kg_day": influent_mass,
        "influent_concentration_ug_l": influent_ug_l,
        "effluent_mass_kg_day": effluent_mass,
        "effluent_concentration_ug_l": effluent_ug_l,
        "post_wwtp_biodegraded_mass_kg_day": post_degraded_mass,
        "receiving_water_input_mass_kg_day": receiving_water_input_mass,
        "pre_dilution_concentration_ug_l": pre_dilution_ug_l,
        "surface_water_pec_ug_l": surface_water_pec,
        "sludge_mass_kg_day": sludge_mass,
        "soil_pec_ug_kg": soil_pec_ug_kg,
        "pathway_fractions": fractions,
        "mass_flows_kg_day": mass_flows,
        "mass_balance_closure_fraction": closure,
        "aquatic_rq": aquatic_rq,
        "soil_rq": soil_rq,
        "aquatic_risk_band": risk_band(aquatic_rq),
        "soil_risk_band": risk_band(soil_rq),
        "limitations": limitations,
        "assumptions": [
            "The WWTP influent mass is taken from a completed Emission & Metabolism run; excretion is not applied after treatment.",
            "The selected emission-run wastewater flow is used, preserving population-flow consistency.",
            "Post-WWTP biodegradation is an explicit scenario fraction and is applied before receiving-water dilution.",
            "Receiving-water dilution is an explicit user input rather than a hidden factor.",
            "Soil PEC assumes uniform mixing of the selected sludge fraction into the specified soil mass.",
            "No transformation-product generation or deconjugation is included in this build.",
        ],
    }


# Legacy compatibility for previous tests and API clients.
def run_wwtp(payload: dict[str, Any]) -> dict[str, Any]:
    annual_release_kg = payload["annual_use_kg"] * payload["release_fraction"]
    daily_release_kg = annual_release_kg / payload["emitting_days_per_year"]
    converted = {
        "influent_mass_kg_day": daily_release_kg,
        "wastewater_flow_m3_day": payload["wastewater_flow_m3_day"],
        "model_mode": "custom_screening",
        "biodegradation_fraction": payload["biodegradation_fraction"],
        "primary_sludge_fraction": payload["sorption_fraction"],
        "secondary_sludge_fraction": 0.0,
        "volatilisation_fraction": payload["volatilisation_fraction"],
        "post_wwtp_biodegradation_fraction": 0.0,
        "receiving_water_dilution_factor": payload["receiving_water_dilution_factor"],
        "sludge_to_soil_fraction": payload["sludge_to_soil_fraction"],
        "mixed_soil_mass_kg": payload["mixed_soil_mass_kg"],
        "emitting_days_per_year": payload["emitting_days_per_year"],
        "aquatic_pnec_ug_l": payload.get("aquatic_pnec_ug_l"),
        "soil_pnec_ug_kg": payload.get("soil_pnec_ug_kg"),
        "species_key": "legacy-parent",
        "species_name": "Legacy screening species",
    }
    result = run_activity_simpletreat(converted)
    result["annual_release_kg"] = annual_release_kg
    result["daily_release_kg"] = daily_release_kg
    result["mass_flows_kg_day"]["sludge"] = result["sludge_mass_kg_day"]
    return result
