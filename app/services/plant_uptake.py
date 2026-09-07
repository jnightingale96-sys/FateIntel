from __future__ import annotations

from math import exp, log
from typing import Any


def briggs_tscf(log_kow: float) -> float:
    return 0.784 * exp(-((log_kow - 1.78) ** 2) / 2.44)


def run_plant_uptake_screen(payload: dict[str, Any]) -> dict[str, Any]:
    mode = payload["model_mode"]
    csoil = payload["soil_concentration_mg_kg_dw"]
    kd = payload["kd_l_kg"]
    theta = payload["volumetric_water_content_l_l"]
    rho_b_kg_l = payload["soil_bulk_density_kg_m3"] / 1000.0
    denominator_l_kg = kd + theta / rho_b_kg_l
    if denominator_l_kg <= 0:
        raise ValueError("The soil-water partition denominator must be positive")
    porewater_mg_l = csoil / denominator_l_kg

    warnings: list[str] = []
    if mode == "briggs_neutral":
        if payload["ionisation_class"] != "neutral":
            raise ValueError("Briggs neutral TSCF mode is restricted to neutral compounds")
        tscf = briggs_tscf(payload["log_kow"])
        if not (-0.5 <= payload["log_kow"] <= 4.5):
            warnings.append("logKow is outside the commonly cited Briggs calibration range (-0.5 to 4.5).")
        model_label = "Briggs neutral-organic TSCF screening relationship"
    elif mode == "user_tscf":
        tscf = payload["user_tscf"]
        model_label = "User-supplied TSCF water-flux screen"
    elif mode == "empirical_bcf":
        root = csoil * payload["root_bcf_kg_kg"]
        shoot = csoil * payload["shoot_bcf_kg_kg"]
        edible = csoil * payload["edible_bcf_kg_kg"]
        return {
            "model_key": "ENVIROCHEM_PLANT_UPTAKE",
            "model_version": "1.0.0-screening",
            "model_mode": mode,
            "model_label": "User-supplied empirical crop transfer factors",
            "soil_porewater_concentration_mg_l": porewater_mg_l,
            "root_concentration_mg_kg_fw": root,
            "shoot_concentration_mg_kg_fw": shoot,
            "edible_tissue_concentration_mg_kg_fw": edible,
            "total_chemical_mass_in_plant_mg": None,
            "tscf": None,
            "regulatory_status": "screening / research support; not an official FOCUS crop-residue endpoint",
            "warnings": warnings,
            "assumptions": ["Empirical BCFs were supplied by the user and are not inferred by EnviroChem."],
        }
    else:
        raise ValueError(f"Unsupported plant uptake model_mode: {mode}")

    transpiration = payload["transpiration_l_plant_day"]
    harvest_days = payload["harvest_interval_days"]
    xylem_mg_l = porewater_mg_l * tscf
    uptake_rate_mg_day = xylem_mg_l * transpiration
    half_life = payload.get("plant_loss_dt50_days")
    if half_life:
        k = log(2.0) / half_life
        total_mass = uptake_rate_mg_day / k * (1.0 - exp(-k * harvest_days))
    else:
        k = 0.0
        total_mass = uptake_rate_mg_day * harvest_days

    fractions = {
        "root": payload["root_allocation_fraction"],
        "shoot": payload["shoot_allocation_fraction"],
        "edible": payload["edible_allocation_fraction"],
    }
    total_fraction = sum(fractions.values())
    if abs(total_fraction - 1.0) > 1e-8:
        raise ValueError("Root, shoot and edible allocation fractions must sum to 1")

    root = total_mass * fractions["root"] / payload["root_fresh_mass_kg"]
    shoot = total_mass * fractions["shoot"] / payload["shoot_fresh_mass_kg"]
    edible = total_mass * fractions["edible"] / payload["edible_fresh_mass_kg"]

    warnings.append("Soil pore-water concentration and the resulting uptake rate are held constant over the harvest interval; soil depletion, time-varying exposure and plant-growth feedback are not dynamically coupled.")
    warnings.append("This is not a regulatory crop-residue study or an embedded third-party ionisation-aware mechanistic model; acids, bases and ion trapping require reviewed uptake evidence or an authorised implementation.")
    return {
        "model_key": "ENVIROCHEM_PLANT_UPTAKE",
        "model_version": "1.0.0-screening",
        "model_mode": mode,
        "model_label": model_label,
        "soil_porewater_concentration_mg_l": porewater_mg_l,
        "tscf": tscf,
        "xylem_concentration_mg_l": xylem_mg_l,
        "daily_uptake_mass_mg_plant": uptake_rate_mg_day,
        "total_chemical_mass_in_plant_mg": total_mass,
        "root_concentration_mg_kg_fw": root,
        "shoot_concentration_mg_kg_fw": shoot,
        "edible_tissue_concentration_mg_kg_fw": edible,
        "plant_loss_rate_per_day": k,
        "regulatory_status": "screening / research support; not an official FOCUS crop-residue endpoint",
        "warnings": warnings,
        "assumptions": [
            "Soil porewater concentration is estimated from total dry-soil concentration, Kd, volumetric water content and bulk density.",
            "Soil porewater concentration and uptake rate remain constant over the harvest interval.",
            "Chemical enters the transpiration stream according to TSCF and crop water use.",
            "Plant mass is allocated to root, shoot and edible compartments using explicit user-reviewable fractions.",
            "PEARL passive plant uptake is stored separately as a groundwater-model parameter and must not be presented as a crop-residue prediction.",
        ],
    }
