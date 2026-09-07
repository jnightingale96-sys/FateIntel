from __future__ import annotations

from math import exp, log
from typing import Any


def _annual_pulse_series(increment_mg_kg: float, soil_dt50_days: float | None, years: int) -> list[dict[str, float]]:
    if years < 1:
        raise ValueError("years must be at least 1")
    if soil_dt50_days is None:
        return [
            {"year": year, "post_application_mg_kg": increment_mg_kg * year, "pre_next_application_mg_kg": increment_mg_kg * year}
            for year in range(1, years + 1)
        ]
    k_year = log(2.0) * 365.0 / soil_dt50_days
    decay = exp(-k_year)
    rows = []
    post = 0.0
    for year in range(1, years + 1):
        post = post * decay + increment_mg_kg
        rows.append({
            "year": year,
            "post_application_mg_kg": post,
            "pre_next_application_mg_kg": post * decay,
        })
    return rows


def run_biosolids_land_application(payload: dict[str, Any]) -> dict[str, Any]:
    """Transparent sludge/biosolids-to-soil mass balance.

    This is a scenario calculator, not a claim that US Part 503 or ECHA prescribe
    one universal organic-contaminant equation. Regulatory context and the
    selected application rate remain explicit.
    """
    mode = payload["source_mode"]
    area_ha = payload["land_application_area_ha"]
    depth_m = payload["soil_mixing_depth_m"]
    bulk_density = payload["soil_bulk_density_kg_m3"]
    days = payload["operating_days_per_year"]
    land_fraction = payload["fraction_sludge_land_applied"]

    storage_fraction_remaining = 1.0
    if payload.get("storage_dt50_days") and payload.get("storage_days", 0) > 0:
        storage_fraction_remaining = exp(-log(2.0) * payload["storage_days"] / payload["storage_dt50_days"])

    if mode == "wwtp_chemical_mass":
        chemical_to_sludge_kg_day = payload["chemical_mass_to_sludge_kg_day"]
        annual_chemical_kg = chemical_to_sludge_kg_day * days * land_fraction * storage_fraction_remaining
        annual_loading_kg_ha = annual_chemical_kg / area_ha
        biosolids_concentration_mg_kg = None
        if payload.get("biosolids_dry_solids_kg_day"):
            dry_mass = payload["biosolids_dry_solids_kg_day"] * days * land_fraction
            if dry_mass > 0:
                biosolids_concentration_mg_kg = annual_chemical_kg * 1e6 / dry_mass
    elif mode == "biosolids_concentration":
        biosolids_concentration_mg_kg = payload["biosolids_concentration_mg_kg_dw"]
        dry_application_kg_ha = payload["biosolids_application_t_dw_ha_year"] * 1000.0
        annual_loading_kg_ha = biosolids_concentration_mg_kg * dry_application_kg_ha / 1e6
        annual_loading_kg_ha *= storage_fraction_remaining
        annual_chemical_kg = annual_loading_kg_ha * area_ha
    else:
        raise ValueError(f"Unsupported source_mode: {mode}")

    soil_mass_kg_ha = 10_000.0 * depth_m * bulk_density
    increment_mg_kg = annual_loading_kg_ha * 1e6 / soil_mass_kg_ha
    years = payload["assessment_years"]
    series = _annual_pulse_series(increment_mg_kg, payload.get("soil_dt50_days"), years)
    final = series[-1]

    runoff_mass_kg_ha = annual_loading_kg_ha * payload.get("runoff_fraction", 0.0)
    leaching_mass_kg_ha = annual_loading_kg_ha * payload.get("leaching_fraction", 0.0)

    notes = [
        "The calculation preserves the chemical mass transferred to sludge and the fraction of sludge actually applied to land.",
        "Soil concentration is calculated from an explicit dry-soil mixing mass; no hidden hectare, depth or bulk-density default is used.",
        "Repeated application is represented as annual pulses with first-order degradation between applications.",
        "US 40 CFR Part 503 is treated as a land-application management and pollutant-limit framework, not as a universal organic-contaminant PEC equation.",
        "EU/UK/Swiss use is a transparent sludge-to-agricultural-soil exposure calculation that must be paired with the applicable sector and current local sludge rules.",
    ]
    warnings = []
    if payload.get("soil_dt50_days") is None:
        warnings.append("No soil DT50 supplied: the repeated-application series assumes no degradation and is deliberately conservative.")
    if payload.get("runoff_fraction", 0) + payload.get("leaching_fraction", 0) > 1:
        warnings.append("Runoff and leaching screening fractions sum to more than one; review the scenario.")
    if mode == "wwtp_chemical_mass" and not payload.get("biosolids_dry_solids_kg_day"):
        warnings.append("Biosolids dry-solids production was not supplied, so a biosolids concentration cannot be reported; the land-loading calculation remains valid.")

    return {
        "model_key": "ENVIROCHEM_BIOSOLIDS_LAND_APPLICATION",
        "model_version": "1.0.0-screening",
        "source_mode": mode,
        "annual_chemical_mass_land_applied_kg": annual_chemical_kg,
        "annual_chemical_loading_kg_ha": annual_loading_kg_ha,
        "biosolids_concentration_mg_kg_dw": biosolids_concentration_mg_kg,
        "storage_fraction_remaining": storage_fraction_remaining,
        "soil_mass_kg_ha": soil_mass_kg_ha,
        "single_application_increment_mg_kg": increment_mg_kg,
        "final_post_application_mg_kg": final["post_application_mg_kg"],
        "final_pre_next_application_mg_kg": final["pre_next_application_mg_kg"],
        "runoff_screening_mass_kg_ha_year": runoff_mass_kg_ha,
        "leaching_screening_mass_kg_ha_year": leaching_mass_kg_ha,
        "annual_series": series,
        "regulatory_context": {
            "EU_UK_CH": "ECHA/sector sludge-to-soil exposure logic with jurisdiction-specific application and legal controls.",
            "US": "EPA 40 CFR Part 503 land-application context; organic-chemical fate remains a separate scientific assessment.",
        },
        "assumptions": notes,
        "warnings": warnings,
    }
