"""BIOWIN4 -> screening DT50, DT50 [hours, 25 C] = 10 ** (5 - BIOWIN4) (project-owner relation, unsourced)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.biowin_dt50 import dt50_from_biowin4, to_evidence_candidate
from app.services.veterinary import biowin_manure_dt50_hours


@pytest.mark.parametrize("score, hours", [(5, 1.0), (4, 10.0), (3, 100.0), (2, 1000.0), (1, 10000.0)])
def test_relation_matches_the_hand_formula_in_hours_at_25c(score, hours):
    result = dt50_from_biowin4(score)
    assert result["unit"] == "hours" and result["temperature_c"] == 25.0
    assert result["dt50"] == pytest.approx(hours, rel=1e-12)


def test_hours_reading_is_consistent_with_epa_biowin4_classification_labels():
    # EPI Suite prints: 5 -> hours, 4 -> days, 3 -> weeks, 2 -> months, 1 -> longer. The ends of the scale must fit.
    assert dt50_from_biowin4(5)["dt50"] < 24  # hours
    assert 30 * 24 <= dt50_from_biowin4(2)["dt50"] <= 365 * 24  # order of months
    assert dt50_from_biowin4(1)["dt50"] > 365 * 24 / 2  # longer than months


def test_agrees_with_the_existing_veterinary_manure_relation():
    for score in (1.7, 3.3744, 4.9):
        assert dt50_from_biowin4(score)["dt50"] == pytest.approx(biowin_manure_dt50_hours(score), rel=1e-12)


def test_higher_biowin4_means_faster_degradation_everywhere():
    values = [dt50_from_biowin4(s / 10)["dt50"] for s in range(10, 51)]
    assert all(a > b for a, b in zip(values, values[1:]))


def test_eu_region_uses_10c_and_the_theta_formula_by_hand():
    result = dt50_from_biowin4(3.0, region="EU")
    assert result["temperature_c"] == 10.0 and result["dt50_at_reference"] == pytest.approx(100.0)
    assert result["dt50"] == pytest.approx(100.0 * 1.047 ** 15, rel=1e-12) and result["dt50"] > 100.0  # colder is slower


def test_explicit_temperature_and_theta_override_the_region_and_default():
    result = dt50_from_biowin4(3.0, region="EU", target_temperature_c=15.0, theta=1.08)
    assert result["temperature_c"] == 15.0 and result["dt50"] == pytest.approx(100.0 * 1.08 ** 10, rel=1e-12)
    assert dt50_from_biowin4(3.0, target_temperature_c=25.0)["dt50"] == pytest.approx(100.0)


def test_unrecorded_region_is_refused_not_guessed():
    with pytest.raises(ValueError, match="no reference temperature"):
        dt50_from_biowin4(3.0, region="AU")
    assert dt50_from_biowin4(3.0, region="AU", target_temperature_c=18.0)["temperature_c"] == 18.0


def test_days_switch_is_a_pure_unit_change():
    assert dt50_from_biowin4(3.0, output_unit="days")["dt50"] == pytest.approx(100.0 / 24.0)
    with pytest.raises(ValueError):
        dt50_from_biowin4(3.0, output_unit="weeks")


def test_provenance_is_always_stated_and_the_app_reconstruction_is_flagged():
    epi = dt50_from_biowin4(3.5)
    assert "no literature source" in epi["provenance"] and any("unsourced" in w for w in epi["warnings"])
    assert not any("reconstruction" in w for w in epi["warnings"])
    assert any("reconstruction" in w for w in dt50_from_biowin4(3.5, score_source="app_reconstruction")["warnings"])


def test_scores_outside_the_scale_warn_and_absurd_ones_are_refused():
    assert any("extrapolated" in w for w in dt50_from_biowin4(5.6)["warnings"])
    for bad in (float("nan"), float("inf"), 20, -9, True, "3"):
        with pytest.raises(ValueError):
            dt50_from_biowin4(bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        dt50_from_biowin4(3.0, score_source="guess")


def test_candidate_is_a_reviewable_labelled_estimate_with_no_invented_source():
    est = dt50_from_biowin4(3.0, region="EU")
    candidate = to_evidence_candidate(est, chemical_name="x", cas_number="1-1-1")
    assert candidate["property_code"] == "FATE.MANURE_DT50" and candidate["unit"] == "hours" and candidate["temperature_c"] == 10.0
    assert candidate["value"] == pytest.approx(est["dt50"])
    assert candidate["evidence_type"] == "model_prediction" and candidate["needs_professional_review"] is True
    assert candidate["doi"] is None and "10 ** (5 - BIOWIN4)" in candidate["snippet"]
    assert to_evidence_candidate(est, chemical_name="x", matrix="water")["property_code"] == "FATE.WATER_DT50"


def test_endpoint_round_trip_and_validation():
    with TestClient(app) as client:
        ok = client.post("/api/providers/biowin-dt50/estimate", json={"biowin4_score": 3.2, "region": "EU", "include_evidence_candidate": True})
        bad_region = client.post("/api/providers/biowin-dt50/estimate", json={"biowin4_score": 3.2, "region": "AU"})
        bad = client.post("/api/providers/biowin-dt50/estimate", json={"biowin4_score": 42})
        regions = client.get("/api/providers/biowin-dt50/regions")
    assert ok.status_code == 200 and ok.json()["dt50"] == pytest.approx(10 ** 1.8 * 1.047 ** 15)
    assert ok.json()["evidence_candidate"]["property_code"] == "FATE.MANURE_DT50"
    assert bad_region.status_code == 422 and bad.status_code == 422
    assert regions.json()["region_temperature_c"] == {"EU": 10.0}
