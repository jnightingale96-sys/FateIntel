from __future__ import annotations

import math
from typing import Any


def _risk_band(rq: float | None) -> str:
    if rq is None:
        return "not characterised"
    if rq < 0.1:
        return "low"
    if rq < 1:
        return "potential"
    return "high"


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return value


def run_wastewater_irrigation_comparison(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the shared native irrigation screen and prepare EU/US model crosswalks.

    The native calculation follows the continuous-input, first-order loss equation
    described in the supplied Nightingale framework. External pesticide models are
    prepared as comparative adapted-use workflows; the result does not imply that
    reclaimed-wastewater irrigation is an official standard scenario in either system.
    """
    effluent_ug_l = _positive("effluent_concentration_ug_l", payload["effluent_concentration_ug_l"])
    effluent_mg_l = effluent_ug_l / 1000.0
    rate = _positive("irrigation_rate_l_m2_day", payload["irrigation_rate_l_m2_day"])
    area = _positive("irrigated_area_m2", payload["irrigated_area_m2"])
    depth = _positive("soil_depth_m", payload["soil_depth_m"])
    density = _positive("bulk_density_kg_m3", payload["bulk_density_kg_m3"])
    kd = _positive("kd_l_kg", payload["kd_l_kg"])
    years = _positive("duration_years", payload.get("duration_years", 1.0))
    dilution = _positive("receiving_water_dilution_factor", payload.get("receiving_water_dilution_factor", 10.0))
    foc = payload.get("organic_carbon_fraction")
    if foc is not None:
        foc = _positive("organic_carbon_fraction", foc)
        if foc > 1:
            raise ValueError("organic_carbon_fraction must be <=1")

    dt50 = payload.get("soil_dt50_days")
    kdeg_day = payload.get("degradation_rate_per_day")
    if dt50 is not None and kdeg_day is not None:
        raise ValueError("Provide soil_dt50_days or degradation_rate_per_day, not both")
    if dt50 is not None:
        dt50 = _positive("soil_dt50_days", dt50)
        kdeg_day = math.log(2.0) / dt50
        degradation_basis = "derived from DT50 using k = ln(2)/DT50"
    elif kdeg_day is not None:
        kdeg_day = _positive("degradation_rate_per_day", kdeg_day)
        dt50 = math.log(2.0) / kdeg_day
        degradation_basis = "direct first-order rate input"
    else:
        raise ValueError("A soil DT50 or first-order degradation rate is required")

    soil_mass_kg_m2 = depth * density
    annual_irrigation_l_m2 = rate * 365.0
    derived_total_flow_l_day = rate * area
    supplied_total_flow = payload.get("total_irrigation_flow_l_day")
    flow_warning = None
    if supplied_total_flow is not None:
        supplied_total_flow = _positive("total_irrigation_flow_l_day", supplied_total_flow)
        implied_rate = supplied_total_flow / area
        relative_difference = abs(implied_rate - rate) / rate
        if relative_difference > 0.01:
            flow_warning = (
                f"Total flow implies {implied_rate:.6g} L/m²/day, whereas the explicit irrigation rate is "
                f"{rate:.6g} L/m²/day. The native calculation uses the explicit rate and derives a consistent total flow."
            )

    input_mg_kg_year = effluent_mg_l * annual_irrigation_l_m2 / soil_mass_kg_m2
    application_mg_m2_day = effluent_mg_l * rate
    application_kg_ha_day = application_mg_m2_day * 0.01
    application_kg_ha_year = application_kg_ha_day * 365.0
    annual_mass_to_area_kg = effluent_mg_l * derived_total_flow_l_day * 365.0 / 1_000_000.0

    # Workbook logic: annual pore-water replacement divided by Kd.
    k_leach_year = annual_irrigation_l_m2 / (soil_mass_kg_m2 * kd)
    k_deg_year = float(kdeg_day) * 365.0
    k_loss_year = k_leach_year + k_deg_year
    plateau_with_deg_mg_kg = input_mg_kg_year / k_loss_year
    plateau_without_deg_mg_kg = input_mg_kg_year / k_leach_year
    concentration_at_duration_mg_kg = plateau_with_deg_mg_kg * (1.0 - math.exp(-k_loss_year * years))

    series = []
    max_integer_year = max(1, min(100, math.ceil(years)))
    for year in range(1, max_integer_year + 1):
        t = min(float(year), years)
        concentration = plateau_with_deg_mg_kg * (1.0 - math.exp(-k_loss_year * t))
        series.append({"year": t, "soil_concentration_mg_kg": concentration})
        if t >= years:
            break

    surface_water_ug_l = effluent_ug_l / dilution
    aquatic_pnec = payload.get("aquatic_pnec_ug_l")
    aquatic_rq = surface_water_ug_l / aquatic_pnec if aquatic_pnec else None

    koc = kd / foc if foc else None
    shared_inputs = {
        "chemical_name": payload.get("chemical_name", "Assessment chemical"),
        "cas_number": payload.get("cas_number"),
        "smiles": payload.get("smiles"),
        "effluent_concentration_ug_l": effluent_ug_l,
        "irrigation_rate_l_m2_day": rate,
        "irrigated_area_m2": area,
        "derived_total_irrigation_flow_l_day": derived_total_flow_l_day,
        "soil_depth_m": depth,
        "bulk_density_kg_m3": density,
        "soil_mass_kg_m2": soil_mass_kg_m2,
        "kd_l_kg": kd,
        "koc_l_kg": koc,
        "organic_carbon_fraction": foc,
        "soil_dt50_days": dt50,
        "degradation_rate_per_day": kdeg_day,
        "duration_years": years,
    }

    application_pattern = {
        "route": "continuous treated-wastewater irrigation",
        "frequency": "daily",
        "irrigation_rate_l_m2_day": rate,
        "application_kg_ha_day": application_kg_ha_day,
        "application_kg_ha_year": application_kg_ha_year,
        "duration_years": years,
        "adaptation_status": "research crosswalk; not a standard pesticide label-use scenario",
    }
    soil_and_crop = {
        "soil_depth_m": depth,
        "bulk_density_kg_m3": density,
        "kd_l_kg": kd,
        "koc_l_kg": koc,
        "crop": payload.get("crop", "maize"),
        "scenario": payload.get("scenario_name", "wastewater irrigation comparison"),
    }
    fate = {
        "soil_dt50_days": dt50,
        "degradation_rate_per_day": kdeg_day,
        "water_solubility_mg_l": payload.get("water_solubility_mg_l"),
        "vapour_pressure_pa": payload.get("vapour_pressure_pa"),
    }

    adapter_payloads = {
        "PEARL": {
            "application_pattern": application_pattern,
            "soil_dt50": {"value": dt50, "unit": "days"},
            "koc_or_kd": {"kd_l_kg": kd, "koc_l_kg": koc},
            "freundlich_exponent": payload.get("freundlich_exponent"),
            "vapour_pressure": payload.get("vapour_pressure_pa"),
            "water_solubility": payload.get("water_solubility_mg_l"),
            "crop_and_scenario": soil_and_crop,
            "weather_scenario": payload.get("eu_weather_scenario"),
        },
        "PELMO": {
            "application_pattern": application_pattern,
            "soil_dt50": {"value": dt50, "unit": "days"},
            "koc_or_kd": {"kd_l_kg": kd, "koc_l_kg": koc},
            "crop_and_scenario": soil_and_crop,
            "weather_scenario": payload.get("eu_weather_scenario"),
            "metabolite_scheme_if_applicable": payload.get("metabolite_scheme"),
        },
        "MACRO": {
            "application_pattern": application_pattern,
            "soil_dt50": {"value": dt50, "unit": "days"},
            "sorption_parameters": {"kd_l_kg": kd, "koc_l_kg": koc},
            "macropore_scenario": payload.get("eu_macro_scenario"),
            "crop_and_weather_scenario": {"crop": payload.get("crop", "maize"), "weather": payload.get("eu_weather_scenario")},
            "drainage_boundary_conditions": payload.get("drainage_boundary_conditions"),
        },
        "TOXSWA": {
            "substance_properties": fate,
            "entry_routes": ["drainage", "runoff", "direct effluent where relevant"],
            "application_pattern": application_pattern,
            "water_sediment_scenario": payload.get("eu_surface_water_scenario"),
            "drift_runoff_or_drainage_inputs": payload.get("eu_loading_time_series"),
            "degradation_and_sorption": {"soil_dt50_days": dt50, "kd_l_kg": kd},
        },
        "PWC": {
            "application_pattern": application_pattern,
            "us_scenario": payload.get("us_pwc_scenario"),
            "soil_and_crop_inputs": soil_and_crop,
            "weather_series": payload.get("us_weather_series"),
            "soil_dt50": {"value": dt50, "unit": "days"},
            "koc_or_kd": {"kd_l_kg": kd, "koc_l_kg": koc},
            "aquatic_fate_inputs": fate,
        },
        "PRZM": {
            "application_pattern": application_pattern,
            "soil_and_crop_scenario": soil_and_crop,
            "weather_series": payload.get("us_weather_series"),
            "soil_dt50": {"value": dt50, "unit": "days"},
            "koc_or_kd": {"kd_l_kg": kd, "koc_l_kg": koc},
            "runoff_and_erosion_parameters": payload.get("us_runoff_erosion_parameters"),
            "root_zone_parameters": {"depth_m": depth, "bulk_density_kg_m3": density},
        },
        "EXAMS": {
            "waterbody_scenario": payload.get("us_exams_waterbody"),
            "loading_time_series": payload.get("us_loading_time_series"),
            "hydrolysis_photolysis_biodegradation": payload.get("aquatic_degradation_inputs"),
            "water_sediment_partitioning": {"kd_l_kg": kd, "koc_l_kg": koc},
            "volatilisation_inputs": {"vapour_pressure_pa": payload.get("vapour_pressure_pa")},
        },
    }

    differences = [
        {
            "topic": "Groundwater and soil transport",
            "EU": "FOCUS compares standardised scenario/model outputs from PEARL and PELMO, with MACRO added where preferential flow and drainage are relevant.",
            "US": "PWC is the current integrated EPA water-exposure workflow; PRZM provides the terrestrial runoff, erosion and root-zone transport component.",
        },
        {
            "topic": "Surface water and sediment",
            "EU": "MACRO or PRZM loading is passed to TOXSWA, which resolves water and sediment fate and time-weighted concentrations.",
            "US": "PWC integrates land-to-water exposure; PRZM–EXAMS is retained as a legacy reproducibility route for receiving-water fate.",
        },
        {
            "topic": "Wastewater irrigation",
            "EU": "The wastewater source is screened natively, then translated to equivalent application schedules for FOCUS models. It is not a standard FOCUS pesticide-use scenario.",
            "US": "The same wastewater loading is translated to PWC/PRZM application inputs. It is an adapted comparative scenario rather than a standard FIFRA use pattern.",
        },
        {
            "topic": "Interpretation",
            "EU": "Report the spread across model/scenario combinations and identify drainage, preferential-flow and surface-water drivers.",
            "US": "Report PWC surface-water/groundwater endpoints and retain PRZM/EXAMS only for historical comparison where required.",
        },
    ]

    workbook_checks = [
        "The supplied irrigation sheet contains a broken compound reference in A2; the chemical identity is now stored explicitly.",
        "Its total flow of 5,520,000 L/day over 3,680,000 m² implies 1.5 L/m²/day, while the explicit irrigation-rate cell is 0.5 L/m²/day. EnviroChem derives total flow from rate × area and raises a mismatch warning.",
        "The worksheet's final concentration divides annual input by leaching loss only and is labelled 'without degradation'. EnviroChem reports that value separately and uses degradation + leaching for the principal steady-state concentration.",
        "The worksheet labels the partition input kg/L; dimensional analysis and the formula require Kd in L/kg. EnviroChem uses L/kg.",
        "The supplied sheet uses 0.1 m × 1385 kg/m³ = 138.5 kg/m². The published Nightingale scenario used 0.4 m and 1.35 g/cm³; both remain explicit scenario inputs rather than hidden constants.",
    ]

    warnings = [
        "EU and US external-model outputs are not fabricated. EnviroChem prepares separate, auditable input manifests and marks unresolved regulatory scenarios or executables as required.",
        "Wastewater irrigation is compared across the toolchains using equivalent application schedules; framework-specific regulator acceptance requires expert review.",
        "The native soil equation is a screening model with continuous loading, first-order degradation and a Kd-controlled leaching loss term.",
    ]
    if flow_warning:
        warnings.insert(0, flow_warning)
    if foc is None:
        warnings.append("No fOC was supplied, so Koc could not be derived from Kd for adapters that require Koc.")

    return {
        "model_key": "ENVIROCHEM_DUAL_WASTEWATER_IRRIGATION",
        "model_version": "1.0.0",
        "scenario_name": payload.get("scenario_name", "EU–US wastewater irrigation comparison"),
        "shared_inputs": shared_inputs,
        "native_screen": {
            "effluent_concentration_ug_l": effluent_ug_l,
            "effluent_concentration_mg_l": effluent_mg_l,
            "derived_total_irrigation_flow_l_day": derived_total_flow_l_day,
            "annual_irrigation_l_m2": annual_irrigation_l_m2,
            "application_mass_kg_ha_day": application_kg_ha_day,
            "application_mass_kg_ha_year": application_kg_ha_year,
            "annual_mass_to_irrigated_area_kg": annual_mass_to_area_kg,
            "annual_input_mg_kg_soil": input_mg_kg_year,
            "k_leach_per_year": k_leach_year,
            "k_degradation_per_year": k_deg_year,
            "k_total_loss_per_year": k_loss_year,
            "soil_plateau_with_degradation_mg_kg": plateau_with_deg_mg_kg,
            "soil_plateau_without_degradation_mg_kg": plateau_without_deg_mg_kg,
            "soil_concentration_at_duration_mg_kg": concentration_at_duration_mg_kg,
            "soil_concentration_at_duration_ug_kg": concentration_at_duration_mg_kg * 1000.0,
            "surface_water_screen_ug_l": surface_water_ug_l,
            "aquatic_pnec_ug_l": aquatic_pnec,
            "aquatic_rq": aquatic_rq,
            "aquatic_risk_band": _risk_band(aquatic_rq),
            "annual_series": series,
            "degradation_basis": degradation_basis,
        },
        "frameworks": {
            "EU": {
                "toolchain": ["Activity SimpleTreat", "EnviroChem soil screen", "FOCUS PEARL", "FOCUS PELMO", "FOCUS MACRO", "FOCUS TOXSWA"],
                "adapter_model_keys": ["PEARL", "PELMO", "MACRO", "TOXSWA"],
                "primary_comparison_outputs": ["groundwater concentration", "soil profile/residue", "drainage or leaching flux", "surface-water peak/TWA", "sediment concentration"],
            },
            "US": {
                "toolchain": ["Activity SimpleTreat", "EnviroChem soil screen", "EPA PWC", "PRZM", "EXAMS legacy"],
                "adapter_model_keys": ["PWC", "PRZM", "EXAMS"],
                "primary_comparison_outputs": ["surface-water concentration", "groundwater concentration", "runoff/erosion/leaching loads", "legacy receiving-water and sediment fate"],
            },
        },
        "framework_differences": differences,
        "adapter_payloads": adapter_payloads,
        "source_workbook_checks": workbook_checks,
        "warnings": warnings,
    }
