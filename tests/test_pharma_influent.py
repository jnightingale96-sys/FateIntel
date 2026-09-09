import pytest
from fastapi.testclient import TestClient

from app.main import app, BUILD_ID
from app.services.emission import run_pharmaceutical_emission
from app.services.pharma_consumption import oecd_2025_lookup, oecd_live_query_url


def payload_base():
    return {
        "scenario_name": "influent test",
        "emission_mode": "direct_daily_use",
        "parent_name": "Carbamazepine",
        "parent_molecular_weight_g_mol": 236.27,
        "product_name": "test",
        "formulation": "tablet",
        "administration_route": "oral",
        "spc_title": "review required",
        "spc_identifier": None,
        "spc_url": None,
        "spc_access_date": None,
        "spc_source_type": "other",
        "consumption_source_title": "user-entered catchment use",
        "consumption_source_identifier": None,
        "therapeutic_class_ddd_per_1000_day": 0.0,
        "dose_per_administration": 1.0,
        "dose_unit": "mg",
        "administrations_per_day": 1.0,
        "oecd_class_key": None,
        "oecd_country": None,
        "refined_annual_active_kg": None,
        "daily_active_amount": 10.0,
        "daily_active_unit": "mg",
        "emitting_days_per_year": 365,
        "maximum_daily_dose_mg": None,
        "ema_fpen_mode": "default",
        "market_penetration_fraction": 0.01,
        "prevalence_fraction": None,
        "treatment_days": None,
        "treatments_per_year": None,
        "regulatory_stp_capacity_inhabitants": 10000,
        "dilution_factor": 10.0,
        "population": 100000,
        "wastewater_l_person_day": 200.0,
        "wastewater_flow_m3_day_override": None,
        "direct_to_sewer_fraction": 0.0,
        "systemic_fraction": 1.0,
        "parent_urine_fraction": 0.51,
        "parent_faeces_fraction": 0.0,
        "metabolites": [],
    }


def test_direct_10_mg_day_is_normalised_before_influent_calculation():
    p = payload_base()
    r = run_pharmaceutical_emission(p)
    assert r["administered"]["mass_kg_day"] == pytest.approx(1e-5)
    assert r["influent"]["parent_mass_kg_day"] == pytest.approx(5.1e-6)
    assert r["wastewater_flow_m3_day"] == pytest.approx(20000.0)
    assert r["influent"]["parent_concentration_ug_l"] == pytest.approx(0.000255)


def test_direct_10_kg_day_remains_10_kg_day_before_excretion():
    p = payload_base()
    p["daily_active_amount"] = 10.0
    p["daily_active_unit"] = "kg"
    r = run_pharmaceutical_emission(p)
    assert r["administered"]["mass_kg_day"] == pytest.approx(10.0)
    assert r["influent"]["parent_mass_kg_day"] == pytest.approx(5.1)
    assert r["influent"]["parent_concentration_ug_l"] == pytest.approx(255.0)


def test_measured_site_flow_override_changes_catchment_influent():
    p = payload_base()
    p["daily_active_amount"] = 1.0
    p["daily_active_unit"] = "kg"
    p["parent_urine_fraction"] = 1.0
    p["wastewater_flow_m3_day_override"] = 10000.0
    r = run_pharmaceutical_emission(p)
    assert r["wastewater_flow_source"] == "user-entered WWTP flow"
    assert r["influent"]["parent_concentration_ug_l"] == pytest.approx(100.0)


def test_ema_phase_i_reference_stp_and_pecsw_equation():
    p = payload_base()
    p.update({
        "emission_mode": "ema_phase_i",
        "maximum_daily_dose_mg": 100.0,
        "parent_urine_fraction": 0.0,  # must be ignored in total-residue Phase I
        "spc_source_type": "official_regulatory",
        "spc_title": "Current SmPC",
        "spc_identifier": "SmPC",
    })
    r = run_pharmaceutical_emission(p)
    assert r["population"] == 10000
    assert r["administered"]["mass_kg_day"] == pytest.approx(0.01)
    assert r["influent"]["parent_mass_kg_day"] == pytest.approx(0.01)
    assert r["influent"]["parent_concentration_ug_l"] == pytest.approx(5.0)
    assert r["regulatory"]["pec_surface_water_ug_l"] == pytest.approx(0.5)
    assert r["regulatory"]["phase_ii_triggered_by_pec"] is True


def test_ema_refined_fpen_uses_prevalence_and_treatment_regimen():
    p = payload_base()
    p.update({
        "emission_mode": "ema_phase_i",
        "maximum_daily_dose_mg": 100.0,
        "ema_fpen_mode": "prevalence_treatment",
        "prevalence_fraction": 0.02,
        "treatment_days": 5.0,
        "treatments_per_year": 2.0,
    })
    r = run_pharmaceutical_emission(p)
    expected = 0.02 * 5 * 2 / 365
    assert r["regulatory"]["fpen"]["fpen"] == pytest.approx(expected)
    assert r["regulatory"]["fpen"]["equation"].startswith("FPEN_refined")


def test_ema_phase_ii_applies_excretion_before_simpletreat_input():
    p = payload_base()
    p.update({
        "emission_mode": "ema_phase_ii",
        "maximum_daily_dose_mg": 100.0,
        "parent_urine_fraction": 0.51,
    })
    r = run_pharmaceutical_emission(p)
    assert r["administered"]["mass_kg_day"] == pytest.approx(0.01)
    assert r["influent"]["parent_mass_kg_day"] == pytest.approx(0.0051)
    assert r["regulatory"]["parent_clocalinf_ug_l"] == pytest.approx(2.55)


def test_oecd_figure_96_static_lookup_preserves_reviewed_values():
    uk_antidepressants = oecd_2025_lookup("antidepressants", "United Kingdom")
    assert uk_antidepressants["ddd_per_1000_people_day"] == pytest.approx(137.0)
    highest = oecd_2025_lookup("antidepressants", "highest_available")
    assert highest["country"] == "Iceland"
    assert highest["ddd_per_1000_people_day"] == pytest.approx(168.0)


def test_oecd_class_screen_is_explicitly_not_compound_specific():
    p = payload_base()
    p.update({
        "emission_mode": "oecd_class_screen",
        "oecd_class_key": "antidepressants",
        "oecd_country": "United Kingdom",
        "dose_per_administration": 100.0,
        "dose_unit": "mg",
        "administrations_per_day": 1.0,
    })
    r = run_pharmaceutical_emission(p)
    assert r["dosage"]["therapeutic_class_ddd_per_1000_day"] == pytest.approx(137.0)
    assert any("not compound-specific" in warning for warning in r["warnings"])


def test_live_oecd_connector_prepares_broader_atc_query_without_selecting_value():
    url = oecd_live_query_url("N03", 2023)
    assert "HEALTH_PHMC@DF_PHMC_CONSUM,1.1" in url
    assert "N03" in url
    assert "startPeriod=2023" in url
    with TestClient(app) as client:
        response = client.get("/api/pharmaceutical-consumption/oecd-live?atc_code=N03&year=2023")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "query_prepared_not_fetched"
        assert body["selection_status"] == "unselected"


def test_v214_ui_exposes_influent_builder_and_daily_kg_units():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    html = (root / "app" / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "v2.24" in BUILD_ID and "8792" not in BUILD_ID
    assert 'id="pharma-influent-panel"' in html
    assert '<option>kg/day</option>' in html
    assert 'id="metric-card-influent"' in html
    assert "buildEmissionPayload" in js
    assert "/api/pharmaceutical-consumption/oecd-2025" in js
