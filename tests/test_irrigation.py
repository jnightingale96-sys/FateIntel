import pytest
from app.services.irrigation import run_wastewater_irrigation_comparison


def base_payload():
    return {
        "scenario_name": "validated irrigation screen",
        "chemical_name": "Test chemical",
        "effluent_concentration_ug_l": 1000.0,
        "irrigation_rate_l_m2_day": 0.5,
        "irrigated_area_m2": 3_680_000.0,
        "soil_depth_m": 0.1,
        "bulk_density_kg_m3": 1385.0,
        "kd_l_kg": 3.0,
        "organic_carbon_fraction": 0.0164,
        "degradation_rate_per_day": 0.1,
        "soil_dt50_days": None,
        "duration_years": 1.0,
        "receiving_water_dilution_factor": 10.0,
        "aquatic_pnec_ug_l": None,
        "crop": "maize",
    }


def test_corrected_irrigation_equation_matches_reviewed_calculation():
    result = run_wastewater_irrigation_comparison(base_payload())
    n = result["native_screen"]
    assert n["annual_input_mg_kg_soil"] == pytest.approx(1.3176895306859206)
    assert n["k_leach_per_year"] == pytest.approx(0.4392298435625752)
    assert n["k_degradation_per_year"] == pytest.approx(36.5)
    assert n["soil_plateau_with_degradation_mg_kg"] == pytest.approx(0.03567181909908483)
    assert n["soil_plateau_without_degradation_mg_kg"] == pytest.approx(3.0)


def test_inconsistent_total_flow_is_flagged_and_rate_controls_calculation():
    p = base_payload()
    p["total_irrigation_flow_l_day"] = 5_520_000.0
    result = run_wastewater_irrigation_comparison(p)
    assert any("implies 1.5 L/m²/day" in warning for warning in result["warnings"])
    assert result["native_screen"]["derived_total_irrigation_flow_l_day"] == pytest.approx(1_840_000.0)


def test_dual_framework_payloads_are_prepared_without_fabricated_outputs():
    result = run_wastewater_irrigation_comparison(base_payload())
    assert set(result["adapter_payloads"]) == {"PEARL", "PELMO", "MACRO", "TOXSWA", "PWC", "PRZM", "EXAMS"}
    assert result["frameworks"]["EU"]["adapter_model_keys"] == ["PEARL", "PELMO", "MACRO", "TOXSWA"]
    assert result["frameworks"]["US"]["adapter_model_keys"] == ["PWC", "PRZM", "EXAMS"]
