from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from .focus_groundwater_scenarios import (
    get_focus_groundwater_scenario,
    list_focus_groundwater_scenarios,
)
from .pearlpy import ApplicationEvent, Chemical, HydrologySeries, PearlLiteModel, SoilProfile
from .pearlpy.swap import SwapImportResult, load_swap_csv


def _positive(name: str, value: Any, *, allow_zero: bool = False) -> float:
    number = float(value)
    if not math.isfinite(number) or (number < 0 if allow_zero else number <= 0):
        comparator = "non-negative" if allow_zero else "greater than zero"
        raise ValueError(f"{name} must be finite and {comparator}")
    return number


def manifest() -> dict[str, Any]:
    return {
        "model_key": "ENVIROCHEM_PEARLPY_GROUNDWATER",
        "display_name": "Tiered PECsoil → FOCUS PEARL groundwater pathway",
        "model_version": "0.2.0",
        "status": "native_tiered_research_screen_and_official_adapter",
        "assessment_sequence": [
            "GAP application rate and crop interception",
            "effective soil loading",
            "PECsoil initial and repeated-application maximum",
            "scenario/profile selection",
            "layer-resolved PEARLpy transport",
            "PECgw at the FOCUS 1 m assessment plane",
            "comparison with the groundwater threshold",
        ],
        "native_processes": [
            "scheduled surface or incorporated applications",
            "equilibrium Freundlich partitioning",
            "temperature/moisture/depth-corrected first-order transformation",
            "aqueous advection, dispersion and diffusion",
            "optional root-water uptake",
            "leaching through a selected assessment plane and the lower boundary",
            "strict mass-balance accounting",
        ],
        "scenario_support": {
            "official_choices": [row["name"] for row in list_focus_groundwater_scenarios()],
            "depth_resolved_native_profile": ["Okehampton"],
            "note": "Other FOCUS locations are selectable for official workflow preparation but remain metadata-only in the native screen until their full profiles are transcribed and validated.",
        },
        "hydrology_modes": ["constant matrix-flow screening", "imported official SWAP user-defined CSV"],
        "official_boundary": (
            "The native engine is a transparent process-aligned reconstruction and is not official, "
            "regulatory-equivalent FOCUS PEARL. Official FOCUS PEARL 5.5.5 remains a separately installed managed workflow."
        ),
        "excluded_processes": [
            "kinetic/non-equilibrium sorption", "metabolites", "macropores/preferential flow",
            "volatilisation and gas-phase transport", "runoff/lateral drainage", "canopy/paddy/greenhouse modules",
        ],
    }


def focus_scenario_manifest() -> list[dict[str, Any]]:
    return list_focus_groundwater_scenarios()


def _resolve_sorption(payload: dict[str, Any], *, default_foc: float | None = None) -> tuple[float, float | None, float | None, list[str], list[dict[str, Any]]]:
    kd = payload.get("kd_l_kg")
    koc = payload.get("koc_l_kg")
    foc = payload.get("organic_carbon_fraction")
    if foc is None:
        foc = default_foc
    warnings: list[str] = []
    conversions: list[dict[str, Any]] = []

    if foc is not None:
        foc = _positive("organic_carbon_fraction", foc)
        if foc > 1:
            raise ValueError("organic_carbon_fraction must be a fraction between 0 and 1")
    if kd is not None:
        kd = _positive("kd_l_kg", kd)
    if koc is not None:
        koc = _positive("koc_l_kg", koc)

    if kd is None and koc is None:
        raise ValueError("Provide Kd or Koc for the PEARL screening run")
    if kd is None:
        if foc is None:
            raise ValueError("organic_carbon_fraction is required to convert Koc to Kd")
        kd = koc * foc
        conversions.append({"name": "Koc to topsoil Kd", "equation": "Kd = Koc × fOC", "value": kd, "unit": "L/kg"})
    if koc is None and foc:
        koc = kd / foc
        conversions.append({"name": "Kd to effective Koc", "equation": "Koc = Kd / fOC", "value": koc, "unit": "L/kgOC"})
    elif koc is not None and foc:
        implied = koc * foc
        relative = abs(implied - kd) / max(kd, 1e-30)
        if relative > 0.2:
            warnings.append(
                f"Supplied Koc × fOC implies topsoil Kd {implied:.4g} L/kg, which differs from supplied Kd {kd:.4g} L/kg. "
                "The native run uses layer Kd from Koc where a FOCUS profile is available; otherwise it uses explicit Kd."
            )

    conversions.append({"name": "PEARLpy Kf unit conversion", "equation": "Kf [m³/kg] = Kd [L/kg] / 1000", "value": kd / 1000.0, "unit": "m³/kg"})
    return float(kd), float(koc) if koc is not None else None, float(foc) if foc is not None else None, warnings, conversions


def _focus_discretisation(horizon: dict[str, Any]) -> list[float]:
    top = float(horizon["top_m"])
    bottom = float(horizon["bottom_m"])
    # FOCUS PEARL uses 0.025 m compartments in the top 0.5 m. If the 0.5 m
    # boundary falls inside a horizon, the whole horizon retains 0.025 m cells.
    if top < 0.5:
        step = 0.025
    elif top < 1.0:
        step = 0.05
    else:
        step = 0.10
    count = max(1, int(round((bottom - top) / step)))
    actual = (bottom - top) / count
    return [actual] * count


def _build_focus_soil(payload: dict[str, Any], scenario: dict[str, Any]) -> tuple[SoilProfile, float, float | None, list[str], list[dict[str, Any]], dict[str, Any]]:
    horizons = scenario.get("horizons")
    if not horizons:
        soil, kd, koc, warnings, conversions, meta = _build_uniform_soil(payload)
        warnings.append(
            f"{scenario['name']} is registered as an official scenario choice, but its full depth profile is not transcribed in this build. "
            "The native result therefore uses the editable uniform profile; official FOCUS PEARL should use the locked scenario database."
        )
        meta["scenario_profile_mode"] = "metadata_only_uniform_native_profile"
        return soil, kd, koc, warnings, conversions, meta

    top_foc = float(horizons[0]["organic_carbon_percent"]) / 100.0
    kd, koc, foc, warnings, conversions = _resolve_sorption(payload, default_foc=top_foc)
    freundlich_n = _positive("freundlich_exponent", payload.get("freundlich_exponent", 1.0))
    c_ref_mg_l = _positive("reference_concentration_mg_l", payload.get("reference_concentration_mg_l", 1.0))
    dispersivity = _positive("dispersivity_m", payload.get("dispersivity_m", 0.05), allow_zero=True)
    diffusion = _positive("molecular_diffusion_m2_d", payload.get("molecular_diffusion_m2_d", 1e-5), allow_zero=True)

    thickness: list[float] = []
    bulk: list[float] = []
    kf: list[float] = []
    theta_ref: list[float] = []
    depth_factor: list[float] = []
    horizon_names: list[str] = []
    layer_foc: list[float] = []
    for horizon in horizons:
        cells = _focus_discretisation(horizon)
        hfoc = float(horizon["organic_carbon_percent"]) / 100.0
        layer_kd = (koc * hfoc) if koc is not None else kd
        for cell in cells:
            thickness.append(cell)
            bulk.append(float(horizon["bulk_density_kg_m3"]))
            kf.append(layer_kd / 1000.0)
            theta_ref.append(float(horizon["water_content_10kpa"]))
            depth_factor.append(float(horizon["depth_transformation_factor"]))
            horizon_names.append(str(horizon["name"]))
            layer_foc.append(hfoc)

    soil = SoilProfile(
        thickness_m=np.asarray(thickness),
        bulk_density_kg_m3=np.asarray(bulk),
        freundlich_kf_m3_kg=np.asarray(kf),
        freundlich_n=np.full(len(thickness), freundlich_n),
        freundlich_c_ref_kg_m3=np.full(len(thickness), c_ref_mg_l / 1000.0),
        theta_ref=np.asarray(theta_ref),
        depth_transformation_factor=np.asarray(depth_factor),
        dispersivity_m=np.full(len(thickness), dispersivity),
        molecular_diffusion_m2_d=np.full(len(thickness), diffusion),
    )
    conversions.append({
        "name": f"{scenario['name']} profile",
        "equation": "FOCUS depth discretisation: 2.5 cm to 0.5 m; 5 cm to 1 m; 10 cm below 1 m",
        "value": soil.n_layers,
        "unit": "model layers",
        "basis": "depth-resolved scenario profile",
    })
    return soil, kd, koc, warnings, conversions, {
        "scenario_profile_mode": "depth_resolved_focus_profile",
        "horizon_names": horizon_names,
        "layer_organic_carbon_fraction": layer_foc,
    }


def _build_uniform_soil(payload: dict[str, Any]) -> tuple[SoilProfile, float, float | None, list[str], list[dict[str, Any]], dict[str, Any]]:
    profile_depth = _positive("profile_depth_m", payload.get("profile_depth_m", 1.2))
    n_layers = int(payload.get("n_layers", 12))
    if n_layers < 2 or n_layers > 200:
        raise ValueError("n_layers must be between 2 and 200")
    bulk_density = _positive("bulk_density_kg_m3", payload.get("bulk_density_kg_m3", 1350.0))
    theta_ref_value = _positive("volumetric_water_content", payload.get("volumetric_water_content", 0.25))
    if theta_ref_value >= 1:
        raise ValueError("volumetric_water_content must be below 1")
    kd, koc, foc, warnings, conversions = _resolve_sorption(payload)
    freundlich_n = _positive("freundlich_exponent", payload.get("freundlich_exponent", 1.0))
    c_ref_mg_l = _positive("reference_concentration_mg_l", payload.get("reference_concentration_mg_l", 1.0))
    dispersivity = _positive("dispersivity_m", payload.get("dispersivity_m", 0.02), allow_zero=True)
    diffusion = _positive("molecular_diffusion_m2_d", payload.get("molecular_diffusion_m2_d", 1e-5), allow_zero=True)
    dz = np.full(n_layers, profile_depth / n_layers, dtype=float)
    centres = np.cumsum(dz) - 0.5 * dz
    half_depth = payload.get("depth_transformation_half_depth_m")
    if half_depth is None:
        depth_factor = np.ones(n_layers, dtype=float)
        conversions.append({"name": "Depth transformation", "equation": "disabled; factor = 1 in every layer", "value": 1.0, "unit": "dimensionless"})
    else:
        half_depth = _positive("depth_transformation_half_depth_m", half_depth)
        depth_factor = np.exp(-math.log(2.0) * centres / half_depth)
        conversions.append({"name": "Depth transformation factor", "equation": "exp[-ln(2) × depth / half-depth]", "value": half_depth, "unit": "m half-depth"})

    soil = SoilProfile(
        thickness_m=dz,
        bulk_density_kg_m3=np.full(n_layers, bulk_density),
        freundlich_kf_m3_kg=np.full(n_layers, kd / 1000.0),
        freundlich_n=np.full(n_layers, freundlich_n),
        freundlich_c_ref_kg_m3=np.full(n_layers, c_ref_mg_l / 1000.0),
        theta_ref=np.full(n_layers, theta_ref_value),
        depth_transformation_factor=depth_factor,
        dispersivity_m=np.full(n_layers, dispersivity),
        molecular_diffusion_m2_d=np.full(n_layers, diffusion),
    )
    return soil, kd, koc, warnings, conversions, {"scenario_profile_mode": "user_defined_uniform_profile", "horizon_names": ["user"] * n_layers, "layer_organic_carbon_fraction": [foc] * n_layers}


def _build_soil(payload: dict[str, Any]) -> tuple[SoilProfile, float, float | None, list[str], list[dict[str, Any]], dict[str, Any], dict[str, Any] | None]:
    scenario = get_focus_groundwater_scenario(payload.get("focus_scenario")) if payload.get("focus_scenario") else None
    if payload.get("profile_mode") == "focus_scenario" and scenario:
        soil, kd, koc, warnings, conversions, meta = _build_focus_soil(payload, scenario)
    else:
        soil, kd, koc, warnings, conversions, meta = _build_uniform_soil(payload)
    return soil, kd, koc, warnings, conversions, meta, scenario


def _constant_hydrology(payload: dict[str, Any], soil: SoilProfile, scenario: dict[str, Any] | None) -> tuple[HydrologySeries, dict[str, Any]]:
    assessment_mode = str(payload.get("assessment_horizon_mode", "quick_screen"))
    frequency = int(payload.get("application_frequency_years", 1))
    if assessment_mode == "focus_standard":
        simulation_years = 6 + 20 * frequency
        simulation_days = simulation_years * 365.0
    else:
        simulation_days = _positive("simulation_days", payload.get("simulation_days", 1095.0))
        simulation_years = simulation_days / 365.0
    dt = _positive("time_step_days", payload.get("time_step_days", 1.0))
    n_steps = max(1, int(math.ceil(simulation_days / dt)))
    dt = simulation_days / n_steps

    if payload.get("profile_mode") == "focus_scenario" and scenario and scenario.get("horizons"):
        theta_row = soil.theta_ref.copy()
        temperature = float(payload.get("temperature_c", scenario["mean_annual_temperature_c"]))
    else:
        theta_value = _positive("volumetric_water_content", payload.get("volumetric_water_content", 0.25))
        if theta_value >= 1:
            raise ValueError("volumetric_water_content must be below 1 m³/m³")
        theta_row = np.full(soil.n_layers, theta_value)
        temperature = float(payload.get("temperature_c", scenario["mean_annual_temperature_c"] if scenario else 20.0))
    if temperature <= -273.15:
        raise ValueError("temperature_c must be above absolute zero")

    percolation = payload.get("percolation_mm_day")
    if percolation is None and scenario:
        recharge_fraction = _positive("screening_recharge_fraction", payload.get("screening_recharge_fraction", 0.35))
        if recharge_fraction > 1:
            raise ValueError("screening_recharge_fraction cannot exceed 1")
        percolation = scenario["annual_rainfall_mm"] * recharge_fraction / 365.0
    percolation_mm_day = _positive("percolation_mm_day", 0.5 if percolation is None else percolation, allow_zero=True)
    root_water_mm_day = _positive("root_water_uptake_mm_day", payload.get("root_water_uptake_mm_day", 0.0), allow_zero=True)
    root_depth = _positive("root_depth_m", payload.get("root_depth_m", min(0.4, float(soil.thickness_m.sum()))))

    theta = np.repeat(theta_row[np.newaxis, :], n_steps, axis=0)
    q = np.full((n_steps, soil.n_layers + 1), percolation_mm_day / 1000.0, dtype=float)
    temperatures = np.full((n_steps, soil.n_layers), temperature, dtype=float)
    uptake = np.zeros((n_steps, soil.n_layers), dtype=float)
    if root_water_mm_day > 0:
        active = soil.centre_depth_m <= root_depth
        active_thickness = float(soil.thickness_m[active].sum())
        if active_thickness > 0:
            uptake[:, active] = (root_water_mm_day / 1000.0) / active_thickness

    return HydrologySeries(
        dt_d=dt,
        theta=theta,
        water_flux_interfaces_m_d=q,
        temperature_c=temperatures,
        root_water_uptake_d1=uptake,
    ), {
        "mode": "constant_matrix_flow_screen",
        "assessment_horizon_mode": assessment_mode,
        "simulation_days": simulation_days,
        "simulation_years": simulation_years,
        "time_step_days": dt,
        "percolation_mm_day": percolation_mm_day,
        "root_water_uptake_mm_day": root_water_mm_day,
        "temperature_c": temperature,
        "scenario_recharge_proxy": bool(scenario and payload.get("percolation_mm_day") is None),
    }


def _pecsoil_from_application(payload: dict[str, Any], soil: SoilProfile, dt50_days: float) -> dict[str, Any]:
    rate = _positive("application_rate_kg_ha", payload.get("application_rate_kg_ha", 1.0), allow_zero=True)
    n_apps = int(payload.get("number_applications", 1))
    if n_apps < 1 or n_apps > 50:
        raise ValueError("number_applications must be between 1 and 50")
    interval = _positive("application_interval_days", payload.get("application_interval_days", 0.0), allow_zero=True)
    interception = float(payload.get("crop_interception_percent", 0.0))
    if not 0 <= interception <= 100:
        raise ValueError("crop_interception_percent must lie between 0 and 100")
    mixing_depth = _positive("pecsoil_mixing_depth_m", payload.get("pecsoil_mixing_depth_m", 0.05))
    effective_rate = rate * (1.0 - interception / 100.0)

    interfaces = soil.interface_depth_m
    overlap = np.maximum(0.0, np.minimum(interfaces[1:], mixing_depth) - interfaces[:-1])
    soil_mass_kg_ha = float(np.sum(overlap * soil.bulk_density_kg_m3) * 10000.0)
    if soil_mass_kg_ha <= 0:
        raise ValueError("PECsoil mixing depth does not overlap the soil profile")
    increment_ug_kg = effective_rate * 1e9 / soil_mass_kg_ha
    max_after_last = 0.0
    k = math.log(2.0) / dt50_days
    for idx in range(n_apps):
        if idx:
            max_after_last *= math.exp(-k * interval)
        max_after_last += increment_ug_kg
    return {
        "nominal_application_rate_kg_ha_per_application": rate,
        "crop_interception_percent": interception,
        "effective_soil_application_rate_kg_ha_per_application": effective_rate,
        "number_applications": n_apps,
        "application_interval_days": interval,
        "pecsoil_mixing_depth_m": mixing_depth,
        "soil_mass_kg_ha": soil_mass_kg_ha,
        "pecsoil_initial_after_first_application_ug_kg": increment_ug_kg,
        "pecsoil_max_after_last_application_ug_kg": max_after_last,
        "pecsoil_total_without_degradation_ug_kg": increment_ug_kg * n_apps,
        "calculation_basis": "application rate corrected for interception and mixed into the selected soil depth",
    }


def _application_events(payload: dict[str, Any], soil: SoilProfile, simulation_days: float) -> tuple[list[ApplicationEvent], dict[str, Any]]:
    rate = _positive("application_rate_kg_ha", payload.get("application_rate_kg_ha", 1.0), allow_zero=True)
    n_apps = int(payload.get("number_applications", 1))
    interval = _positive("application_interval_days", payload.get("application_interval_days", 0.0), allow_zero=True)
    interception = float(payload.get("crop_interception_percent", 0.0))
    frequency = int(payload.get("application_frequency_years", 1))
    if frequency not in {1, 2, 3}:
        raise ValueError("application_frequency_years must be 1, 2 or 3")
    first_day = _positive("first_application_day_of_year", payload.get("first_application_day_of_year", 0.0), allow_zero=True)
    if first_day >= 365:
        raise ValueError("first_application_day_of_year must be below 365")
    effective_rate = rate * (1 - interception / 100.0)
    dose_kg_m2 = effective_rate / 10000.0
    method = str(payload.get("application_method", "surface"))
    incorporation_depth = _positive("incorporation_depth_m", payload.get("incorporation_depth_m", 0.0), allow_zero=True)

    if method == "surface" or incorporation_depth == 0:
        distribution = [(0, 1.0)]
    elif method in {"incorporated", "injected"}:
        interfaces = soil.interface_depth_m
        overlap = np.maximum(0.0, np.minimum(interfaces[1:], incorporation_depth) - interfaces[:-1])
        masses = overlap * soil.bulk_density_kg_m3
        total = float(masses.sum())
        if total <= 0:
            raise ValueError("incorporation_depth_m does not overlap the soil profile")
        distribution = [(int(i), float(value / total)) for i, value in enumerate(masses) if value > 0]
    else:
        raise ValueError("application_method must be surface, incorporated or injected")

    events: list[ApplicationEvent] = []
    year = 0
    application_count = 0
    while year * 365.0 < simulation_days:
        if year % frequency == 0:
            for app_index in range(n_apps):
                time_d = year * 365.0 + first_day + app_index * interval
                if time_d >= simulation_days:
                    continue
                for layer, fraction in distribution:
                    events.append(ApplicationEvent(time_d=time_d, dose_kg_m2=dose_kg_m2 * fraction, target_layer=layer))
                application_count += 1
        year += 1
    return events, {
        "application_method": method,
        "incorporation_depth_m": incorporation_depth,
        "application_frequency_years": frequency,
        "first_application_day_of_year": first_day,
        "scheduled_application_count": application_count,
        "dose_kg_m2_per_application": dose_kg_m2,
        "distribution": [{"layer": layer + 1, "fraction": fraction} for layer, fraction in distribution],
    }


def _initial_mass(payload: dict[str, Any], soil: SoilProfile) -> tuple[np.ndarray, list[float], list[dict[str, Any]]]:
    explicit = payload.get("layer_initial_concentrations_ug_kg")
    if explicit is not None:
        concentrations = np.asarray(explicit, dtype=float)
        if concentrations.shape != (soil.n_layers,):
            raise ValueError(f"layer_initial_concentrations_ug_kg must contain {soil.n_layers} values")
        if np.any(concentrations < 0) or not np.all(np.isfinite(concentrations)):
            raise ValueError("Layer concentrations must be finite and non-negative")
        source = "user-supplied layer profile"
    else:
        initial = _positive("initial_soil_concentration_ug_kg", payload.get("initial_soil_concentration_ug_kg", 0.0), allow_zero=True)
        mixing_depth = _positive("initial_mixing_depth_m", payload.get("initial_mixing_depth_m", 0.4))
        concentrations = np.where(soil.centre_depth_m <= mixing_depth, initial, 0.0)
        source = f"uniform concentration to {mixing_depth:g} m"
    soil_mass_kg_m2 = soil.bulk_density_kg_m3 * soil.thickness_m
    mass_kg_m2 = concentrations * soil_mass_kg_m2 / 1e9
    conversions = [{
        "name": "Soil concentration to layer mass",
        "equation": "mass [kg/m²] = Csoil [µg/kg] × bulk density [kg/m³] × layer thickness [m] × 10⁻⁹",
        "value": float(mass_kg_m2.sum()),
        "unit": "kg/m²",
        "basis": source,
    }]
    return mass_kg_m2, concentrations.tolist(), conversions


def _profile_rows(result, soil: SoilProfile, index: int, horizon_names: list[str] | None = None) -> list[dict[str, float | str]]:
    mass = result.layer_mass_kg_m2[index]
    soil_mass = soil.bulk_density_kg_m3 * soil.thickness_m
    total_ug_kg = np.divide(mass * 1e9, soil_mass, out=np.zeros_like(mass), where=soil_mass > 0)
    liquid_ug_l = result.liquid_concentration_kg_m3[index] * 1e6
    sorbed_ug_kg = result.sorbed_content_kg_kg[index] * 1e9
    interfaces = soil.interface_depth_m
    return [
        {
            "layer": int(i + 1),
            "horizon": horizon_names[i] if horizon_names else "user",
            "top_depth_m": float(interfaces[i]),
            "bottom_depth_m": float(interfaces[i + 1]),
            "centre_depth_m": float(soil.centre_depth_m[i]),
            "total_soil_concentration_ug_kg": float(total_ug_kg[i]),
            "liquid_concentration_ug_l": float(liquid_ug_l[i]),
            "sorbed_concentration_ug_kg": float(sorbed_ug_kg[i]),
            "mass_kg_m2": float(mass[i]),
        }
        for i in range(soil.n_layers)
    ]


def _target_interface(soil: SoilProfile, target_depth_m: float) -> tuple[int, float]:
    interfaces = soil.interface_depth_m
    index = int(np.argmin(np.abs(interfaces - target_depth_m)))
    index = max(1, min(index, soil.n_layers))
    return index, float(interfaces[index])


def _focus_endpoint(
    cumulative_mass: np.ndarray,
    q_target_m_d: np.ndarray,
    dt_d: float,
    frequency_years: int,
) -> dict[str, Any]:
    increments = np.diff(cumulative_mass, prepend=0.0)
    water = np.concatenate(([0.0], np.maximum(q_target_m_d, 0.0) * dt_d))
    warmup_days = 6 * 365
    cycle_days = frequency_years * 365
    values: list[float] = []
    for cycle in range(20):
        start = warmup_days + cycle * cycle_days
        end = start + cycle_days
        start_idx = int(round(start / dt_d)) + 1
        end_idx = min(int(round(end / dt_d)) + 1, increments.size)
        if end_idx <= start_idx:
            break
        cycle_mass = float(increments[start_idx:end_idx].sum())
        cycle_water = float(water[start_idx:end_idx].sum())
        values.append(cycle_mass / cycle_water * 1e6 if cycle_water > 0 else 0.0)
    endpoint = None
    if len(values) == 20:
        ranked = sorted(values)
        endpoint = 0.5 * (ranked[15] + ranked[16])
    return {
        "assessment_cycle_years": frequency_years,
        "warmup_years": 6,
        "annual_or_cycle_average_concentrations_ug_l": values,
        "focus_style_80th_percentile_ug_l": endpoint,
        "endpoint_status": "calculated_native_screen" if endpoint is not None else "insufficient_simulation_horizon",
        "calculation": "average of the 16th and 17th ranked values from 20 assessment cycles",
    }


def _official_readiness(payload: dict[str, Any], kd: float, koc: float | None, scenario: dict[str, Any] | None) -> list[dict[str, Any]]:
    application_mode = (payload.get("input_mode") or ("application_rate" if payload.get("application_rate_kg_ha") is not None else "pecsoil")) == "application_rate"
    fields = [
        ("application_rate", "GAP application rate and schedule", application_mode and payload.get("application_rate_kg_ha") is not None, "required before PECsoil and PEARL"),
        ("crop_interception", "Crop interception correction", application_mode and payload.get("crop_interception_percent") is not None, "effective soil loading"),
        ("pecsoil", "PECsoil calculation", True, "application rate or measured/predicted PECsoil"),
        ("soil_dt50_days", "Reviewed soil DegT50", payload.get("soil_dt50_days") is not None, "required for transformation"),
        ("sorption", "Kd or Koc plus fOC", kd is not None, "required for retardation"),
        ("freundlich_exponent", "Freundlich exponent", payload.get("freundlich_exponent") is not None, "default 1.0 is linear screening"),
        ("water_solubility_mg_l", "Water solubility", payload.get("water_solubility_mg_l") is not None, "official substance dataset"),
        ("vapour_pressure_pa", "Vapour pressure", payload.get("vapour_pressure_pa") is not None, "official volatilisation pathway"),
        ("molecular_weight_g_mol", "Molecular weight", payload.get("molecular_weight_g_mol") is not None, "official substance identity"),
        ("focus_scenario", "FOCUS crop/soil/weather scenario", scenario is not None, "official regulatory scenario required"),
        ("focus_crop", "FOCUS crop", bool(payload.get("focus_crop")), "crop-specific weather and growth inputs"),
        ("swap_hydrology", "SWAP hydrology", bool(payload.get("hydrology_mode") == "swap_csv"), "constant-flow screen should be replaced by official SWAP"),
        ("metabolite_scheme", "Transformation products/metabolites", bool(payload.get("metabolite_scheme")), "needed where relevant"),
    ]
    return [{"key": key, "label": label, "status": "ready" if ready else "missing_or_screening_default", "note": note} for key, label, ready, note in fields]


def run_pearl_groundwater_screen(payload: dict[str, Any], *, swap_csv_path: str | Path | None = None) -> dict[str, Any]:
    soil, kd, koc, warnings, conversions, profile_meta, scenario = _build_soil(payload)
    dt50 = _positive("soil_dt50_days", payload.get("soil_dt50_days", 40.0))

    swap_import: SwapImportResult | None = None
    if swap_csv_path is not None:
        swap_import = load_swap_csv(
            swap_csv_path,
            soil,
            state_sampling=str(payload.get("swap_state_sampling", "end")),
            bottom_flux_sign=float(payload.get("swap_bottom_flux_sign", 1.0)),
            q_flux_sign=float(payload.get("swap_q_flux_sign", 1.0)),
            drop_initial_row=bool(payload.get("swap_drop_initial_row", True)),
        )
        hydrology = swap_import.hydrology
        hydrology_meta = {
            "mode": "imported_swap_csv",
            "simulation_days": float(hydrology.n_steps * hydrology.dt_d),
            "simulation_years": float(hydrology.n_steps * hydrology.dt_d / 365.0),
            "time_step_days": float(hydrology.dt_d),
            "state_sampling": swap_import.metadata.state_sampling,
            "bottom_flux_column": swap_import.metadata.bottom_flux_column,
            "dates": [d.isoformat() for d in swap_import.metadata.dates],
        }
        warnings.extend(swap_import.metadata.warnings)
        payload = {**payload, "hydrology_mode": "swap_csv"}
    else:
        hydrology, hydrology_meta = _constant_hydrology(payload, soil, scenario)

    input_mode = str(payload.get("input_mode") or ("application_rate" if payload.get("application_rate_kg_ha") is not None else "pecsoil"))
    pecsoil = None
    applications: list[ApplicationEvent] = []
    application_meta = None
    if input_mode == "application_rate":
        initial_mass = np.zeros(soil.n_layers, dtype=float)
        initial_profile = [0.0] * soil.n_layers
        pecsoil = _pecsoil_from_application(payload, soil, dt50)
        applications, application_meta = _application_events(payload, soil, hydrology_meta["simulation_days"])
        conversions.extend([
            {
                "name": "Application rate to land-area dose",
                "equation": "dose [kg/m²] = effective application rate [kg/ha] / 10,000",
                "value": application_meta["dose_kg_m2_per_application"],
                "unit": "kg/m²/application",
            },
            {
                "name": "Application rate to PECsoil",
                "equation": "PECsoil = effective dose / soil mass within mixing depth",
                "value": pecsoil["pecsoil_initial_after_first_application_ug_kg"],
                "unit": "µg/kg",
                "basis": f"{pecsoil['pecsoil_mixing_depth_m']} m mixing depth",
            },
        ])
    elif input_mode == "pecsoil":
        initial_mass, initial_profile, mass_conversions = _initial_mass(payload, soil)
        conversions.extend(mass_conversions)
    else:
        raise ValueError("input_mode must be application_rate or pecsoil")

    target_requested = float(payload.get("focus_target_depth_m", scenario.get("focus_target_depth_m", 1.0) if scenario else 1.0))
    target_index, target_depth = _target_interface(soil, target_requested)

    chemical = Chemical(
        dt50_ref_d=dt50,
        temperature_ref_c=float(payload.get("temperature_ref_c", 20.0)),
        activation_energy_kj_mol=_positive("activation_energy_kj_mol", payload.get("activation_energy_kj_mol", 65.4)),
        moisture_exponent=float(payload.get("moisture_exponent", 0.0)),
        root_uptake_factor=_positive("root_uptake_factor", payload.get("root_uptake_factor", 0.0), allow_zero=True),
    )
    model = PearlLiteModel(
        soil=soil,
        chemical=chemical,
        hydrology=hydrology,
        applications=applications,
        max_transport_substep_d=_positive("max_transport_substep_days", payload.get("max_transport_substep_days", 0.25)),
        monitor_interface_index=target_index,
    )
    result = model.run(initial_mass_kg_m2=initial_mass)

    initial_total = float(initial_mass.sum())
    applied_total = float(result.cumulative_applied_kg_m2[-1])
    total_input = initial_total + applied_total
    final_mass = float(result.layer_mass_kg_m2[-1].sum())
    degraded = float(result.cumulative_degraded_kg_m2[-1])
    uptake = float(result.cumulative_uptake_kg_m2[-1])
    bottom_leached = float(result.cumulative_bottom_leached_kg_m2[-1])
    target_leached = float(result.cumulative_target_leached_kg_m2[-1])
    surface = float(result.cumulative_surface_export_kg_m2[-1])
    mass_balance_error = float(result.mass_balance_error_kg_m2[-1])

    q_target = hydrology.water_flux_interfaces_m_d[:, target_index]
    target_water_depth = float(np.sum(np.maximum(q_target, 0.0) * hydrology.dt_d))
    target_average_ug_l = target_leached / target_water_depth * 1e6 if target_water_depth > 0 else 0.0
    target_increments = np.diff(result.cumulative_target_leached_kg_m2, prepend=0.0)
    water_increments = np.concatenate(([0.0], np.maximum(q_target, 0.0) * hydrology.dt_d))
    target_flux_concentration = np.divide(target_increments * 1e6, water_increments, out=np.zeros_like(target_increments), where=water_increments > 0)
    cumulative_water = np.cumsum(water_increments)
    cumulative_target_concentration = np.divide(result.cumulative_target_leached_kg_m2 * 1e6, cumulative_water, out=np.zeros_like(cumulative_water), where=cumulative_water > 0)

    frequency = int(payload.get("application_frequency_years", 1))
    focus_endpoint = _focus_endpoint(result.cumulative_target_leached_kg_m2, q_target, hydrology.dt_d, frequency)
    endpoint_value = focus_endpoint["focus_style_80th_percentile_ug_l"]
    threshold = _positive("groundwater_threshold_ug_l", payload.get("groundwater_threshold_ug_l", 0.1))
    comparison_value = endpoint_value if endpoint_value is not None else target_average_ug_l
    risk_quotient = comparison_value / threshold if threshold > 0 else None
    risk_status = "below_threshold" if comparison_value <= threshold else "above_threshold"

    profile_conc_all = result.layer_mass_kg_m2 * 1e9 / (soil.bulk_density_kg_m3 * soil.thickness_m)[None, :]
    baseline = max(float(np.max(initial_profile)), pecsoil["pecsoil_initial_after_first_application_ug_kg"] if pecsoil else 0.0)
    detection_threshold = max(baseline * 1e-6, 1e-12)
    detected = np.where(np.max(profile_conc_all, axis=0) > detection_threshold)[0]
    deepest = float(soil.interface_depth_m[detected[-1] + 1]) if detected.size else 0.0

    sample_stride = max(1, int(math.ceil(len(result.time_d) / 241)))
    sampled_indices = list(range(0, len(result.time_d), sample_stride))
    if sampled_indices[-1] != len(result.time_d) - 1:
        sampled_indices.append(len(result.time_d) - 1)
    timeseries = []
    for idx in sampled_indices:
        dynamic_denominator = initial_total + float(result.cumulative_applied_kg_m2[idx])
        denominator = dynamic_denominator if dynamic_denominator > 0 else 1.0
        timeseries.append({
            "time_d": float(result.time_d[idx]),
            "applied_mass_mg_m2": float(result.cumulative_applied_kg_m2[idx] * 1e6),
            "remaining_fraction": float(result.layer_mass_kg_m2[idx].sum() / denominator),
            "degraded_fraction": float(result.cumulative_degraded_kg_m2[idx] / denominator),
            "root_uptake_fraction": float(result.cumulative_uptake_kg_m2[idx] / denominator),
            "target_leached_fraction": float(result.cumulative_target_leached_kg_m2[idx] / denominator),
            "bottom_leached_fraction": float(result.cumulative_bottom_leached_kg_m2[idx] / denominator),
            "surface_export_fraction": float(result.cumulative_surface_export_kg_m2[idx] / denominator),
            "target_flux_concentration_ug_l": float(target_flux_concentration[idx]),
            "cumulative_groundwater_concentration_ug_l": float(cumulative_target_concentration[idx]),
        })

    snapshot_indices = sorted(set(int(round(x)) for x in np.linspace(0, len(result.time_d) - 1, 9)))
    horizons = profile_meta.get("horizon_names")
    snapshots = [{"time_d": float(result.time_d[idx]), "profile": _profile_rows(result, soil, idx, horizons)} for idx in snapshot_indices]
    final_profile = _profile_rows(result, soil, -1, horizons)

    if swap_csv_path is None:
        warnings.append("Constant matrix percolation is a screening hydrology. Official FOCUS scenario runs require the locked daily weather/crop inputs and SWAP hydrology.")
    if hydrology_meta.get("scenario_recharge_proxy"):
        warnings.append("Scenario rainfall was converted to constant percolation with an editable recharge fraction. This is not the official SWAP water balance.")
    warnings.extend([
        "This native PEARLpy result is not an official or regulatory-equivalent FOCUS PEARL output.",
        "The FOCUS-style 80th-percentile endpoint is only an indicative calculation unless driven by the official multi-year SWAP scenario hydrology.",
        "No preferential flow, drainage, volatilisation, metabolites, canopy or non-equilibrium sorption is represented.",
    ])

    readiness = _official_readiness(payload, kd, koc, scenario)
    data_gaps = [row for row in readiness if row["status"] != "ready"]
    return {
        "model_key": "ENVIROCHEM_PEARLPY_GROUNDWATER",
        "model_version": "0.2.0",
        "scenario_name": payload.get("scenario_name", "Tiered PECsoil to groundwater assessment"),
        "chemical_name": payload.get("chemical_name", "Assessment chemical"),
        "tiered_assessment": {
            "tier_1_application": application_meta,
            "tier_1_pecsoil": pecsoil,
            "tier_2_scenario": scenario,
            "tier_3_groundwater": {
                "focus_target_depth_m": target_depth,
                "threshold_ug_l": threshold,
                "comparison_concentration_ug_l": comparison_value,
                "risk_quotient": risk_quotient,
                "status": risk_status,
                "endpoint_basis": "FOCUS-style 80th percentile" if endpoint_value is not None else "whole-run flux-weighted screening average",
            },
        },
        "model_identity": {
            "native_engine": "PEARLpy process-aligned matrix-flow reconstruction",
            "official_focus_pearl": "managed external workflow; not executed by this native result",
            "regulatory_equivalent": False,
        },
        "resolved_inputs": {
            "input_mode": input_mode,
            "focus_scenario": scenario,
            "focus_crop": payload.get("focus_crop"),
            "profile_mode": payload.get("profile_mode", "user_defined"),
            "profile_depth_m": float(soil.thickness_m.sum()),
            "focus_target_depth_m": target_depth,
            "n_layers": soil.n_layers,
            "layer_thickness_m": soil.thickness_m.tolist(),
            "bulk_density_kg_m3": soil.bulk_density_kg_m3.tolist(),
            "initial_layer_concentrations_ug_kg": initial_profile,
            "initial_total_mass_kg_m2": initial_total,
            "applied_total_mass_kg_m2": applied_total,
            "total_input_mass_kg_m2": total_input,
            "kd_l_kg": kd,
            "koc_l_kg": koc,
            "freundlich_exponent": float(soil.freundlich_n[0]),
            "soil_dt50_days": dt50,
            "hydrology": hydrology_meta,
            "profile_metadata": profile_meta,
        },
        "conversions": conversions,
        "summary": {
            "initial_mass_mg_m2": initial_total * 1e6,
            "applied_mass_mg_m2": applied_total * 1e6,
            "total_input_mass_mg_m2": total_input * 1e6,
            "final_remaining_mass_mg_m2": final_mass * 1e6,
            "degraded_mass_mg_m2": degraded * 1e6,
            "root_uptake_mass_mg_m2": uptake * 1e6,
            "target_depth_leached_mass_mg_m2": target_leached * 1e6,
            "bottom_leached_mass_mg_m2": bottom_leached * 1e6,
            "surface_export_mass_mg_m2": surface * 1e6,
            "remaining_fraction": final_mass / total_input if total_input else 0.0,
            "degraded_fraction": degraded / total_input if total_input else 0.0,
            "root_uptake_fraction": uptake / total_input if total_input else 0.0,
            "target_leached_fraction": target_leached / total_input if total_input else 0.0,
            "bottom_leached_fraction": bottom_leached / total_input if total_input else 0.0,
            "groundwater_flux_weighted_average_ug_l": target_average_ug_l,
            "peak_target_flux_concentration_ug_l": float(np.max(target_flux_concentration)),
            "focus_style_80th_percentile_ug_l": endpoint_value,
            "groundwater_threshold_ug_l": threshold,
            "groundwater_risk_quotient": risk_quotient,
            "groundwater_risk_status": risk_status,
            "pecsoil_initial_ug_kg": pecsoil["pecsoil_initial_after_first_application_ug_kg"] if pecsoil else None,
            "pecsoil_max_ug_kg": pecsoil["pecsoil_max_after_last_application_ug_kg"] if pecsoil else float(max(initial_profile) if initial_profile else 0.0),
            "deepest_detected_depth_m": deepest,
            "target_water_depth_m": target_water_depth,
            "mass_balance_error_mg_m2": mass_balance_error * 1e6,
            "mass_balance_relative_error": mass_balance_error / total_input if total_input else 0.0,
        },
        "focus_endpoint": focus_endpoint,
        "timeseries": timeseries,
        "profile_snapshots": snapshots,
        "final_profile": final_profile,
        "official_input_readiness": readiness,
        "data_gaps": data_gaps,
        "warnings": warnings,
        "scope": manifest(),
    }
