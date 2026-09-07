import pytest

from app.services.toxswa_surface_water import manifest, parse_official_summary, run_process_screen


def payload(**overrides):
    base = {
        "contaminant_group": "human_pharmaceutical",
        "regulatory_context": "adapted",
        "waterbody_type": "stream",
        "waterbody_length_m": 10.0,
        "waterbody_width_m": 1.0,
        "water_depth_m": 1.0,
        "receiving_flow_m3_day": 0.0,
        "n_segments": 2,
        "sediment_active_depth_m": 0.05,
        "sediment_bulk_density_kg_m3": 800.0,
        "sediment_porosity": 0.6,
        "sediment_organic_carbon_fraction": 0.05,
        "suspended_solids_mg_l": 0.0,
        "suspended_solids_organic_carbon_fraction": 0.2,
        "molecular_weight_g_mol": 200.0,
        "koc_l_kg": 100.0,
        "sediment_kd_l_kg": None,
        "suspended_solids_kd_l_kg": None,
        "freundlich_exponent": 1.0,
        "reference_concentration_mg_l": 1.0,
        "water_dt50_days": 1e12,
        "sediment_dt50_days": 1e12,
        "transformation_reference_temperature_c": 20.0,
        "water_temperature_c": 20.0,
        "activation_energy_kj_mol": 65.4,
        "water_transformation_mode": "lumped",
        "aqueous_diffusion_coefficient_m2_day": 0.0,
        "relative_sediment_diffusion": 0.0,
        "interface_diffusion_path_m": 0.0005,
        "volatilisation_half_life_days": None,
        "water_solubility_mg_l": None,
        "vapour_pressure_pa": None,
        "loading_mode": "pulse_mass",
        "loaded_start_m": 0.0,
        "loaded_end_m": 10.0,
        "application_rate_kg_ha": 1.0,
        "drift_percent": 1.0,
        "first_application_day": 0.0,
        "number_applications": 1,
        "application_interval_days": 7.0,
        "discharge_concentration_ug_l": 0.0,
        "discharge_flow_m3_day": 0.0,
        "continuous_mass_mg_day": 0.0,
        "pulse_mass_mg": 100.0,
        "pulse_day": 0.0,
        "pulse_distributed": True,
        "lateral_concentration_ug_l": 0.0,
        "lateral_water_flux_m3_day": 0.0,
        "initial_water_concentration_ug_l": 0.0,
        "initial_sediment_concentration_ug_kg": 0.0,
        "simulation_days": 2.0,
        "output_interval_days": 1/24,
        "max_transport_substep_days": 0.05,
        "aquatic_pnec_ug_l": None,
        "sediment_pnec_ug_kg": None,
    }
    base.update(overrides)
    return base


def test_manifest_separates_official_and_native_modes():
    m = manifest()
    assert m["official_stable_version_registered"] == "5.5.3"
    assert "not regulatory-equivalent" in m["separation_of_modes"]["adapted_process_screen"]
    assert "3" in [str(x) for x in m["twa_windows_days"]]


def test_closed_system_pulse_conserves_mass():
    out = run_process_screen(payload())
    mb = out["mass_balance"]
    assert mb["external_input_mg"] == pytest.approx(100.0)
    assert mb["final_water_mass_mg"] == pytest.approx(100.0, rel=1e-8)
    assert abs(mb["closure_error_fraction"]) < 1e-10


def test_drift_conversion_from_kg_ha_and_percent_is_correct():
    out = run_process_screen(payload(
        loading_mode="spray_drift",
        application_rate_kg_ha=1.0,
        drift_percent=1.0,
        first_application_day=0.0,
        waterbody_length_m=10.0,
        loaded_end_m=10.0,
        simulation_days=0.1,
    ))
    # 1 kg/ha and 1% drift = 1 mg/m2; 10 m2 surface = 10 mg.
    assert out["mass_balance"]["external_input_mg"] == pytest.approx(10.0)


def test_continuous_discharge_mass_conversion_is_ug_l_times_m3_day():
    out = run_process_screen(payload(
        loading_mode="continuous_point_discharge",
        discharge_concentration_ug_l=2.0,
        discharge_flow_m3_day=3.0,
        simulation_days=2.0,
    ))
    assert out["mass_balance"]["external_input_mg"] == pytest.approx(12.0, rel=1e-8)


def test_high_koc_generates_official_discretisation_warning():
    out = run_process_screen(payload(koc_l_kg=40000.0))
    assert any("30,000" in warning for warning in out["warnings"])


def test_official_summary_parser_reads_global_and_twa_values():
    text = """
* FOCUS TOXSWA version : 5.5.3
* TOXSWA model version : 3.3.6
Table: PEC in water layer of substance: TEST
Global max 12.5 01-Jan-2000-00h00 1
TWAECsw_1_day 10.0 01-Jan-2000-00h00 1
TWAECsw_3_days 8.0 03-Jan-2000-00h00 3
Exposure concentrations in sediment
Table: PEC in sediment layer of substance: TEST
Global max 42.0 02-Jan-2000-00h00 2
TWAECsed_3_days 30.0 04-Jan-2000-00h00 4
"""
    parsed = parse_official_summary(text)
    assert parsed["focus_toxswa_version"] == "5.5.3"
    assert parsed["toxswa_kernel_version"] == "3.3.6"
    assert parsed["global_max_pecsw_ug_l"] == pytest.approx(12.5)
    assert parsed["global_max_pecsed_reported"] == pytest.approx(42.0)
    assert parsed["twaecsw_ug_l"]["3"] == pytest.approx(8.0)
