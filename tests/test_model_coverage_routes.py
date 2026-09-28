"""Route-level wiring tests for three reviewer-input calculation modules that existed before this session's
wiring but had no API route: sediment/soil PNEC (equilibrium partitioning), the PBT/vPvB + PMT/vPvM classifier,
and fish/earthworm secondary-poisoning TER (all part of app/services/*). The modules' own arithmetic is already
covered by tests/test_equilibrium_partitioning.py, tests/test_pbt_pmt_classifier.py and
tests/test_eu_birds_mammals.py -- these tests only check the routes call the right function with the right
shape and 422 (not 500) on an invalid reviewer input.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------------------------- equilibrium partitioning

def test_sediment_pnec_route_matches_the_module(client):
    result = client.post("/api/pnec/sediment-from-water", json={"pnec_water_mg_per_l": 1.0, "koc_l_per_kg": 1000.0})
    assert result.status_code == 200
    body = result.json()
    assert body["method"] == "equilibrium_partitioning"
    assert body["pnec_sediment_wet_mg_per_kg"] > 0
    assert body["pnec_sediment_dry_mg_per_kg"] == pytest.approx(body["pnec_sediment_wet_mg_per_kg"] * 2.6)


def test_soil_pnec_route_matches_the_module(client):
    result = client.post("/api/pnec/soil-from-water", json={"pnec_water_mg_per_l": 1.0, "koc_l_per_kg": 1000.0})
    assert result.status_code == 200
    body = result.json()
    assert body["method"] == "equilibrium_partitioning"
    assert body["pnec_soil_mg_per_kg"] > 0


def test_sediment_pnec_route_rejects_a_non_positive_koc_with_422_not_500(client):
    result = client.post("/api/pnec/sediment-from-water", json={"pnec_water_mg_per_l": 1.0, "koc_l_per_kg": -5})
    assert result.status_code == 422


def test_soil_pnec_route_applies_the_optional_high_log_kow_factor(client):
    plain = client.post("/api/pnec/soil-from-water", json={"pnec_water_mg_per_l": 1.0, "koc_l_per_kg": 1000.0}).json()
    boosted = client.post(
        "/api/pnec/soil-from-water",
        json={"pnec_water_mg_per_l": 1.0, "koc_l_per_kg": 1000.0, "high_log_kow_factor": 2.5},
    ).json()
    assert boosted["pnec_soil_mg_per_kg"] == pytest.approx(plain["pnec_soil_mg_per_kg"] * 2.5)


# ----------------------------------------------------------------------------------------------------- PBT / PMT

def test_pbt_pmt_route_returns_both_classifications_from_one_payload(client):
    result = client.post("/api/pbt-pmt/classify", json={
        "half_life_days": {"soil": 150},
        "bcf_l_per_kg": 3000,
        "log_koc": 4.0,
        "noec_or_ec10_mg_l": 0.005,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["pbt_vpvb"]["pbt"] == "CRITERION_MET"
    assert body["pbt_vpvb"]["persistence"]["outcome"] == "CRITERION_MET"
    assert "pmt" in body["pmt_vpvm"] and "mobility" in body["pmt_vpvm"]
    assert "REACH" in body["pbt_vpvb"]["source"]
    assert "CLP" in body["pmt_vpvm"]["source"] or "2023/707" in body["pmt_vpvm"]["source"]


def test_pbt_pmt_route_reports_not_applicable_for_an_inorganic_metal(client):
    result = client.post("/api/pbt-pmt/classify", json={"substance_group": "metal_inorganic"})
    assert result.status_code == 200
    body = result.json()
    assert body["pbt_vpvb"]["pbt"] == "NOT_APPLICABLE_TO_SUBSTANCE_GROUP"
    assert body["pmt_vpvm"]["pmt"] == "NOT_APPLICABLE_TO_SUBSTANCE_GROUP"


def test_pbt_pmt_route_defaults_are_all_optional(client):
    result = client.post("/api/pbt-pmt/classify", json={})
    assert result.status_code == 200


# ----------------------------------------------------------------------------------- secondary poisoning (fish)

def test_fish_secondary_poisoning_route_matches_the_module(client):
    result = client.post("/api/secondary-poisoning/fish", json={
        "log_kow": 6, "relevant_endpoint_mg_kg_bw_day": 1, "food_intake_rate_g_day": 20,
        "body_weight_g": 20, "twa_surface_water_concentration_ug_l": 10,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["triggered"] is True
    assert body["ter"] == pytest.approx(0.002)
    assert body["low_risk"] is False


def test_fish_secondary_poisoning_route_accepts_a_measured_bcf(client):
    result = client.post("/api/secondary-poisoning/fish", json={
        "log_kow": 6, "relevant_endpoint_mg_kg_bw_day": 1, "food_intake_rate_g_day": 20,
        "body_weight_g": 20, "twa_surface_water_concentration_ug_l": 10, "measured_bcf_fish_l_kg": 1234,
    })
    assert result.status_code == 200
    assert result.json()["bcf_source"] == "measured"


def test_fish_secondary_poisoning_route_rejects_a_non_positive_body_weight(client):
    result = client.post("/api/secondary-poisoning/fish", json={
        "log_kow": 6, "relevant_endpoint_mg_kg_bw_day": 1, "food_intake_rate_g_day": 20,
        "body_weight_g": 0, "twa_surface_water_concentration_ug_l": 10,
    })
    assert result.status_code == 422


# ------------------------------------------------------------------------------- secondary poisoning (earthworm)

def test_earthworm_secondary_poisoning_route_matches_the_module(client):
    result = client.post("/api/secondary-poisoning/earthworm", json={
        "log_kow": 4.0, "koc_l_per_kg": 500, "soil_concentration_mg_kg_wwt": 1.0,
        "relevant_endpoint_mg_kg_bw_day": 10, "food_intake_rate_g_day": 20, "body_weight_g": 20,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["bcf_earthworm_l_kg"] == pytest.approx(120.84)
    assert body["within_bcf_validated_range"] is True
    assert body["bcf_source"].startswith("Jager")


def test_earthworm_secondary_poisoning_route_reports_out_of_range_without_refusing(client):
    result = client.post("/api/secondary-poisoning/earthworm", json={
        "log_kow": 0.5, "koc_l_per_kg": 50, "soil_concentration_mg_kg_wwt": 1.0,
        "relevant_endpoint_mg_kg_bw_day": 10, "food_intake_rate_g_day": 20, "body_weight_g": 20,
    })
    assert result.status_code == 200
    assert result.json()["within_bcf_validated_range"] is False


def test_earthworm_secondary_poisoning_route_rejects_a_non_positive_koc(client):
    result = client.post("/api/secondary-poisoning/earthworm", json={
        "log_kow": 4.0, "koc_l_per_kg": -1, "soil_concentration_mg_kg_wwt": 1.0,
        "relevant_endpoint_mg_kg_bw_day": 10, "food_intake_rate_g_day": 20, "body_weight_g": 20,
    })
    assert result.status_code == 422


# ------------------------------------------------------------------------------------------------ Japan CSCL PNEC

def test_japan_cscl_route_matches_the_real_carbamazepine_worked_example(client):
    result = client.post("/api/pnec/japan-cscl", json={"lowest_toxicity_value_ug_per_l": 25, "data_type": "chronic_multi_species"})
    assert result.status_code == 200
    body = result.json()
    assert body["assessment_factor"] == 10
    assert body["pnec_ug_per_l"] == pytest.approx(2.5)
    assert "env.go.jp" in body["guidance_reference"]


def test_japan_cscl_route_rejects_an_unconfirmed_data_type(client):
    result = client.post("/api/pnec/japan-cscl", json={"lowest_toxicity_value_ug_per_l": 25, "data_type": "single_species"})
    assert result.status_code == 422


def test_japan_cscl_route_rejects_a_non_positive_value(client):
    result = client.post("/api/pnec/japan-cscl", json={"lowest_toxicity_value_ug_per_l": 0, "data_type": "acute_multi_species"})
    assert result.status_code == 422


# --------------------------------------------------------------------------------------------- Bee-REX Tier 1 (US/PMRA)

def test_bee_rex_foliar_contact_route_matches_the_module(client):
    result = client.post("/api/bee-rex/foliar-spray/contact", json={"application_rate_kg_ha": 1, "contact_ld50_ug_per_bee": 0.1})
    assert result.status_code == 200
    body = result.json()
    assert body["exposure_estimate"] == pytest.approx(2.4)
    assert body["risk_quotient"] == pytest.approx(24)
    assert body["exceeds_loc"] is True


def test_bee_rex_foliar_dietary_route_uses_the_correct_life_stage_consumption(client):
    result = client.post("/api/bee-rex/foliar-spray/dietary", json={
        "application_rate_kg_ha": 1, "life_stage": "larval", "toxicity_endpoint_ug_per_bee": 12.152, "chronic": True,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["exposure_estimate"] == pytest.approx(12.152)
    assert body["risk_quotient"] == pytest.approx(1.0)
    assert body["loc"] == pytest.approx(1.0)


def test_bee_rex_seed_treatment_route_is_independent_of_application_rate(client):
    result = client.post("/api/bee-rex/seed-treatment/dietary", json={
        "life_stage": "adult", "toxicity_endpoint_ug_per_bee": 0.292, "chronic": False,
    })
    assert result.status_code == 200
    assert result.json()["risk_quotient"] == pytest.approx(1.0)


def test_bee_rex_soil_treatment_route_refuses_outside_the_briggs_domain(client):
    result = client.post("/api/bee-rex/soil-treatment/dietary", json={
        "application_rate_kg_ha": 1, "log_kow": 6, "koc_l_per_kg": 100, "life_stage": "adult",
        "toxicity_endpoint_ug_per_bee": 1, "chronic": False,
    })
    assert result.status_code == 422


def test_bee_rex_soil_treatment_route_within_domain_succeeds(client):
    result = client.post("/api/bee-rex/soil-treatment/dietary", json={
        "application_rate_kg_ha": 1, "log_kow": 2, "koc_l_per_kg": 100, "life_stage": "adult",
        "toxicity_endpoint_ug_per_bee": 1, "chronic": False,
    })
    assert result.status_code == 200
    assert result.json()["exposure_estimate"] > 0


def test_bee_rex_route_rejects_a_non_positive_application_rate(client):
    result = client.post("/api/bee-rex/foliar-spray/contact", json={"application_rate_kg_ha": 0, "contact_ld50_ug_per_bee": 0.1})
    assert result.status_code == 422
