from pathlib import Path

import numpy as np
import pytest

from app.services.pearl_groundwater import _focus_endpoint, manifest, run_pearl_groundwater_screen
from app.services.pearlpy import (
    Chemical,
    HydrologySeries,
    PearlLiteModel,
    SoilProfile,
    compare_result_to_reference_csv,
    export_normalized_result_csv,
)


def payload(**overrides):
    base = {
        "scenario_name": "test groundwater screen",
        "chemical_name": "Test chemical",
        "initial_soil_concentration_ug_kg": 100.0,
        "initial_mixing_depth_m": 0.2,
        "profile_depth_m": 1.0,
        "n_layers": 10,
        "bulk_density_kg_m3": 1400.0,
        "volumetric_water_content": 0.25,
        "organic_carbon_fraction": 0.02,
        "kd_l_kg": 2.0,
        "koc_l_kg": None,
        "freundlich_exponent": 1.0,
        "reference_concentration_mg_l": 1.0,
        "soil_dt50_days": 1000.0,
        "temperature_c": 20.0,
        "temperature_ref_c": 20.0,
        "activation_energy_kj_mol": 65.4,
        "moisture_exponent": 0.0,
        "simulation_days": 100.0,
        "time_step_days": 1.0,
        "max_transport_substep_days": 0.1,
        "percolation_mm_day": 5.0,
        "dispersivity_m": 0.01,
        "molecular_diffusion_m2_d": 0.0,
        "root_water_uptake_mm_day": 0.0,
        "root_depth_m": 0.2,
        "root_uptake_factor": 0.0,
    }
    base.update(overrides)
    return base


def test_manifest_keeps_official_boundary_explicit():
    data = manifest()
    assert data["status"] == "native_tiered_research_screen_and_official_adapter"
    assert "not official" in data["official_boundary"]


def test_soil_concentration_is_converted_to_correct_initial_mass():
    result = run_pearl_groundwater_screen(payload(simulation_days=1, percolation_mm_day=0, soil_dt50_days=1e12))
    # 100 µg/kg in top 0.2 m; soil mass = 1400*0.2 = 280 kg/m2.
    assert result["summary"]["initial_mass_mg_m2"] == pytest.approx(28.0)
    assert result["resolved_inputs"]["koc_l_kg"] == pytest.approx(100.0)
    assert any(row["name"] == "Kd to effective Koc" for row in result["conversions"])


def test_downward_percolation_produces_bottom_leaching_and_conserves_mass():
    result = run_pearl_groundwater_screen(payload())
    summary = result["summary"]
    assert summary["bottom_leached_fraction"] > 0
    assert summary["groundwater_flux_weighted_average_ug_l"] > 0
    assert abs(summary["mass_balance_relative_error"]) < 1e-9
    assert summary["deepest_detected_depth_m"] > 0.2


def test_no_flow_closed_profile_only_degrades():
    result = run_pearl_groundwater_screen(payload(percolation_mm_day=0, soil_dt50_days=10, simulation_days=10))
    summary = result["summary"]
    assert summary["bottom_leached_fraction"] == pytest.approx(0.0)
    assert summary["remaining_fraction"] == pytest.approx(0.5, rel=5e-3)
    assert summary["degraded_fraction"] == pytest.approx(0.5, rel=5e-3)


def test_swap_csv_can_drive_hydrology(tmp_path: Path):
    csv = tmp_path / "swap.csv"
    csv.write_text(
        "DATE,BOT,WC[1],WC[2],Q[1],Q[2],RWU[1],RWU[2],T[1],T[2]\n"
        "2026-01-01,0,0.25,0.25,0,0,0,0,20,20\n"
        "2026-01-02,0.2,0.25,0.25,0.2,0.2,0,0,20,20\n"
        "2026-01-03,0.2,0.25,0.25,0.2,0.2,0,0,20,20\n",
        encoding="utf-8",
    )
    p = payload(n_layers=2, profile_depth_m=0.4, initial_mixing_depth_m=0.2, simulation_days=2)
    result = run_pearl_groundwater_screen(p, swap_csv_path=csv)
    assert result["resolved_inputs"]["hydrology"]["mode"] == "imported_swap_csv"
    assert result["resolved_inputs"]["hydrology"]["time_step_days"] == 1.0



def test_application_rate_is_converted_to_pecsoil_before_transport():
    result = run_pearl_groundwater_screen(payload(
        input_mode="application_rate",
        profile_mode="user_defined",
        application_rate_kg_ha=1.0,
        number_applications=1,
        crop_interception_percent=0.0,
        first_application_day_of_year=0.0,
        pecsoil_mixing_depth_m=0.05,
        bulk_density_kg_m3=1500.0,
        simulation_days=1.0,
        percolation_mm_day=0.0,
        soil_dt50_days=1e12,
    ))
    pec = result["tiered_assessment"]["tier_1_pecsoil"]
    # 1 kg/ha = 1e9 ug/ha; 5 cm of soil at 1500 kg/m3 = 750,000 kg/ha.
    assert pec["pecsoil_initial_after_first_application_ug_kg"] == pytest.approx(1333.3333333333333)
    assert result["summary"]["applied_mass_mg_m2"] == pytest.approx(100.0)


def test_crop_interception_reduces_effective_rate_and_pecsoil():
    result = run_pearl_groundwater_screen(payload(
        input_mode="application_rate",
        profile_mode="user_defined",
        application_rate_kg_ha=1.0,
        crop_interception_percent=50.0,
        first_application_day_of_year=0.0,
        pecsoil_mixing_depth_m=0.05,
        bulk_density_kg_m3=1500.0,
        simulation_days=1.0,
        percolation_mm_day=0.0,
        soil_dt50_days=1e12,
    ))
    pec = result["tiered_assessment"]["tier_1_pecsoil"]
    assert pec["effective_soil_application_rate_kg_ha_per_application"] == pytest.approx(0.5)
    assert pec["pecsoil_initial_after_first_application_ug_kg"] == pytest.approx(666.6666666666666)


def test_okehampton_resolves_depth_profile_and_one_metre_target():
    result = run_pearl_groundwater_screen(payload(
        input_mode="application_rate",
        profile_mode="focus_scenario",
        focus_scenario="okehampton",
        focus_crop="winter cereals",
        application_rate_kg_ha=0.1,
        first_application_day_of_year=0.0,
        kd_l_kg=None,
        koc_l_kg=100.0,
        organic_carbon_fraction=0.022,
        focus_target_depth_m=1.0,
        simulation_days=1.0,
        percolation_mm_day=0.0,
        soil_dt50_days=1e12,
    ))
    resolved = result["resolved_inputs"]
    assert resolved["focus_scenario"]["name"] == "Okehampton"
    assert resolved["profile_depth_m"] == pytest.approx(1.5)
    assert resolved["focus_target_depth_m"] == pytest.approx(1.0)
    assert resolved["n_layers"] == 36
    assert resolved["bulk_density_kg_m3"][0] == pytest.approx(1280.0)
    assert resolved["profile_metadata"]["horizon_names"][-1] == "C deep"


def test_focus_style_endpoint_uses_ranked_16th_and_17th_values():
    increments = np.zeros(27)
    increments[7:27] = np.arange(1.0, 21.0)
    cumulative = np.cumsum(increments)
    q_target = np.full(26, 1.0 / 365.0)
    endpoint = _focus_endpoint(cumulative, q_target, 365.0, 1)
    assert endpoint["annual_or_cycle_average_concentrations_ug_l"] == pytest.approx((np.arange(1.0, 21.0) * 1e6).tolist())
    assert endpoint["focus_style_80th_percentile_ug_l"] == pytest.approx(16.5e6)

def test_normalized_reference_self_comparison(tmp_path: Path):
    soil = SoilProfile(
        thickness_m=np.array([0.1, 0.1]),
        bulk_density_kg_m3=np.array([1400.0, 1400.0]),
        freundlich_kf_m3_kg=np.array([0.001, 0.001]),
        freundlich_n=np.array([1.0, 1.0]),
        freundlich_c_ref_kg_m3=np.array([0.001, 0.001]),
        theta_ref=np.array([0.25, 0.25]),
        depth_transformation_factor=np.array([1.0, 1.0]),
        dispersivity_m=np.array([0.0, 0.0]),
        molecular_diffusion_m2_d=np.array([0.0, 0.0]),
    )
    hydro = HydrologySeries(
        dt_d=1.0,
        theta=np.full((2, 2), 0.25),
        water_flux_interfaces_m_d=np.zeros((2, 3)),
        temperature_c=np.full((2, 2), 20.0),
        root_water_uptake_d1=np.zeros((2, 2)),
    )
    model = PearlLiteModel(soil, Chemical(dt50_ref_d=1000), hydro)
    result = model.run(np.array([1e-6, 0.0]))
    path = export_normalized_result_csv(result, soil, tmp_path / "reference.csv")
    report = compare_result_to_reference_csv(result, soil, path)
    assert report.unmatched_reference_rows == 0
    assert report.mass.root_mean_square_error == pytest.approx(0.0)
    assert report.liquid_concentration.root_mean_square_error == pytest.approx(0.0)
