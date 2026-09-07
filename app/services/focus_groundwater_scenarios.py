from __future__ import annotations

from copy import deepcopy
from typing import Any

# Scenario-level values are drawn from the European Commission FOCUS Groundwater
# Generic Guidance v2.4. Only Okehampton currently includes a fully transcribed
# depth-resolved soil profile in the native screen. Other locations remain valid
# official-adapter choices, but use user-defined native soil inputs until their
# depth profiles are independently transcribed and tested.
FOCUS_GROUNDWATER_SCENARIOS: dict[str, dict[str, Any]] = {
    "chateaudun": {
        "code": "C", "name": "Châteaudun", "mean_annual_temperature_c": 11.3,
        "annual_rainfall_mm": 648.0, "topsoil_texture": "silty clay loam",
        "topsoil_organic_matter_percent": 2.4, "irrigation_available": True,
        "lower_boundary": "free drainage", "native_profile_status": "metadata_only",
    },
    "hamburg": {
        "code": "H", "name": "Hamburg", "mean_annual_temperature_c": 9.0,
        "annual_rainfall_mm": 786.0, "topsoil_texture": "sandy loam",
        "topsoil_organic_matter_percent": 2.6, "irrigation_available": False,
        "lower_boundary": "groundwater-level-dependent flux", "native_profile_status": "metadata_only",
    },
    "jokioinen": {
        "code": "J", "name": "Jokioinen", "mean_annual_temperature_c": 4.1,
        "annual_rainfall_mm": 650.0, "topsoil_texture": "loamy sand",
        "topsoil_organic_matter_percent": 7.0, "irrigation_available": False,
        "lower_boundary": "groundwater-level-dependent flux", "native_profile_status": "metadata_only",
    },
    "kremsmunster": {
        "code": "K", "name": "Kremsmünster", "mean_annual_temperature_c": 8.6,
        "annual_rainfall_mm": 899.0, "topsoil_texture": "loam / silt loam",
        "topsoil_organic_matter_percent": 3.6, "irrigation_available": False,
        "lower_boundary": "groundwater-level-dependent flux", "native_profile_status": "metadata_only",
    },
    "okehampton": {
        "code": "N", "name": "Okehampton", "mean_annual_temperature_c": 10.2,
        "annual_rainfall_mm": 1038.0, "topsoil_texture": "loam",
        "topsoil_organic_matter_percent": 3.8, "irrigation_available": False,
        "lower_boundary": "free drainage", "groundwater_depth_context_m": 20.0,
        "native_profile_status": "depth_profile_transcribed",
        "profile_depth_m": 1.5,
        "focus_target_depth_m": 1.0,
        "plant_available_water_top_m_mm": 203.7,
        "crops": [
            "apples", "grass + alfalfa", "potatoes", "sugar beets", "winter cereals",
            "beans (field)", "linseed", "maize", "oilseed rape (summer)",
            "oilseed rape (winter)", "peas (animals)", "spring cereals",
        ],
        "crop_parameters": {
            "apples": {"root_depth_m": 1.0, "max_lai": 2.5},
            "grass + alfalfa": {"root_depth_m": 0.45, "max_lai": 4.5},
            "potatoes": {"root_depth_m": 0.6, "max_lai": 4.0},
            "sugar beets": {"root_depth_m": 0.8, "max_lai": 3.0},
            "winter cereals": {"root_depth_m": 0.8, "max_lai": 7.5},
            "beans (field)": {"root_depth_m": 0.45, "max_lai": 4.0},
            "linseed": {"root_depth_m": 0.6, "max_lai": 3.0},
            "maize": {"root_depth_m": 0.8, "max_lai": 7.0},
            "oilseed rape (summer)": {"root_depth_m": 0.6, "max_lai": 3.0},
            "oilseed rape (winter)": {"root_depth_m": 0.85, "max_lai": 4.5},
            "peas (animals)": {"root_depth_m": 0.45, "max_lai": 4.0},
            "spring cereals": {"root_depth_m": 0.6, "max_lai": 4.5},
        },
        "horizons": [
            {
                "name": "A", "top_m": 0.0, "bottom_m": 0.25, "texture": "loam",
                "ph_h2o": 5.8, "ph_kcl": 5.1, "clay_percent": 18.0,
                "silt_percent": 43.0, "sand_percent": 39.0,
                "organic_matter_percent": 3.8, "organic_carbon_percent": 2.2,
                "bulk_density_kg_m3": 1280.0, "depth_transformation_factor": 1.0,
                "theta_s": 0.4664, "theta_r": 0.0100, "vg_alpha_m1": 3.550,
                "vg_n": 1.1891, "water_content_10kpa": 0.358,
                "water_content_1600kpa": 0.148, "ksat_1e6_m_s": 3.484,
                "vg_lambda": -2.581,
            },
            {
                "name": "Bw1", "top_m": 0.25, "bottom_m": 0.55, "texture": "loam",
                "ph_h2o": 6.3, "ph_kcl": 5.6, "clay_percent": 17.0,
                "silt_percent": 41.0, "sand_percent": 42.0,
                "organic_matter_percent": 1.2, "organic_carbon_percent": 0.7,
                "bulk_density_kg_m3": 1340.0, "depth_transformation_factor": 0.5,
                "theta_s": 0.4602, "theta_r": 0.0100, "vg_alpha_m1": 3.640,
                "vg_n": 1.2148, "water_content_10kpa": 0.340,
                "water_content_1600kpa": 0.125, "ksat_1e6_m_s": 4.887,
                "vg_lambda": -2.060,
            },
            {
                "name": "BC", "top_m": 0.55, "bottom_m": 0.85, "texture": "sandy loam",
                "ph_h2o": 6.5, "ph_kcl": 5.8, "clay_percent": 14.0,
                "silt_percent": 31.0, "sand_percent": 55.0,
                "organic_matter_percent": 0.69, "organic_carbon_percent": 0.4,
                "bulk_density_kg_m3": 1420.0, "depth_transformation_factor": 0.3,
                "theta_s": 0.4320, "theta_r": 0.0100, "vg_alpha_m1": 4.560,
                "vg_n": 1.2526, "water_content_10kpa": 0.290,
                "water_content_1600kpa": 0.090, "ksat_1e6_m_s": 4.838,
                "vg_lambda": -1.527,
            },
            {
                "name": "C", "top_m": 0.85, "bottom_m": 1.0, "texture": "sandy loam",
                "ph_h2o": 6.6, "ph_kcl": 5.9, "clay_percent": 9.0,
                "silt_percent": 22.0, "sand_percent": 69.0,
                "organic_matter_percent": 0.17, "organic_carbon_percent": 0.1,
                "bulk_density_kg_m3": 1470.0, "depth_transformation_factor": 0.3,
                "theta_s": 0.4110, "theta_r": 0.0100, "vg_alpha_m1": 5.620,
                "vg_n": 1.3384, "water_content_10kpa": 0.228,
                "water_content_1600kpa": 0.050, "ksat_1e6_m_s": 4.449,
                "vg_lambda": -0.400,
            },
            {
                "name": "C deep", "top_m": 1.0, "bottom_m": 1.5, "texture": "sandy loam",
                "ph_h2o": 6.6, "ph_kcl": 5.9, "clay_percent": 9.0,
                "silt_percent": 22.0, "sand_percent": 69.0,
                "organic_matter_percent": 0.17, "organic_carbon_percent": 0.1,
                "bulk_density_kg_m3": 1470.0, "depth_transformation_factor": 0.0,
                "theta_s": 0.4110, "theta_r": 0.0100, "vg_alpha_m1": 5.620,
                "vg_n": 1.3384, "water_content_10kpa": 0.228,
                "water_content_1600kpa": 0.050, "ksat_1e6_m_s": 4.449,
                "vg_lambda": -0.400,
            },
        ],
    },
    "piacenza": {
        "code": "P", "name": "Piacenza", "mean_annual_temperature_c": 13.2,
        "annual_rainfall_mm": 857.0, "topsoil_texture": "loam",
        "topsoil_organic_matter_percent": 2.2, "irrigation_available": True,
        "lower_boundary": "time-dependent groundwater position", "native_profile_status": "metadata_only",
    },
    "porto": {
        "code": "O", "name": "Porto", "mean_annual_temperature_c": 14.8,
        "annual_rainfall_mm": 1150.0, "topsoil_texture": "loam",
        "topsoil_organic_matter_percent": 2.5, "irrigation_available": True,
        "lower_boundary": "groundwater-level-dependent flux", "native_profile_status": "metadata_only",
    },
    "sevilla": {
        "code": "S", "name": "Sevilla", "mean_annual_temperature_c": 17.9,
        "annual_rainfall_mm": 493.0, "topsoil_texture": "silt loam",
        "topsoil_organic_matter_percent": 1.6, "irrigation_available": True,
        "lower_boundary": "groundwater-level-dependent flux", "native_profile_status": "metadata_only",
    },
    "thiva": {
        "code": "T", "name": "Thiva", "mean_annual_temperature_c": 16.2,
        "annual_rainfall_mm": 500.0, "topsoil_texture": "loam",
        "topsoil_organic_matter_percent": 1.3, "irrigation_available": True,
        "lower_boundary": "free drainage", "native_profile_status": "metadata_only",
    },
}

COMMON_FOCUS_CROPS = ["apples", "grass + alfalfa", "potatoes", "sugar beets", "winter cereals"]


def list_focus_groundwater_scenarios() -> list[dict[str, Any]]:
    rows = []
    for key, value in FOCUS_GROUNDWATER_SCENARIOS.items():
        row = deepcopy(value)
        row["key"] = key
        row.setdefault("crops", COMMON_FOCUS_CROPS)
        row["source"] = {
            "title": "FOCUS Groundwater Generic Guidance",
            "version": "2.4",
            "official_url": "https://esdac.jrc.ec.europa.eu/public_path//projects_data/focus/gw/docs/Generic_guidance_FOCUS_GW_V2-4final.pdf",
        }
        rows.append(row)
    return rows


def get_focus_groundwater_scenario(key: str | None) -> dict[str, Any] | None:
    if not key:
        return None
    normalized = key.strip().lower().replace(" ", "_").replace("ä", "a").replace("â", "a")
    aliases = {
        "châteaudun": "chateaudun", "chateaudun": "chateaudun",
        "kremsmünster": "kremsmunster", "kremsmunster": "kremsmunster",
        "okehamption": "okehampton", "okehampton": "okehampton",
    }
    normalized = aliases.get(normalized, normalized)
    scenario = FOCUS_GROUNDWATER_SCENARIOS.get(normalized)
    if scenario is None:
        raise ValueError(f"Unknown FOCUS groundwater scenario: {key}")
    result = deepcopy(scenario)
    result["key"] = normalized
    result.setdefault("crops", COMMON_FOCUS_CROPS)
    return result
