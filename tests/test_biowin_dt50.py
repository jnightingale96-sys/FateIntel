"""BIOWIN4 -> screening water DT50, DT50 [days] = 10 ** (5 - BIOWIN4) (project-owner relation, unsourced)."""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.biowin_dt50 import dt50_days_from_biowin4, to_evidence_candidate
from app.services.soil_dt50 import corrections


@pytest.mark.parametrize("score, days", [(5, 1.0), (4, 10.0), (3, 100.0), (2, 1000.0), (1, 10000.0)])
def test_relation_matches_the_survey_scale_by_hand(score, days):
    assert dt50_days_from_biowin4(score)["dt50_days"] == pytest.approx(days, rel=1e-12)


def test_higher_biowin4_means_faster_degradation_everywhere():
    values = [dt50_days_from_biowin4(s / 10)["dt50_days"] for s in range(10, 51)]
    assert all(a > b for a, b in zip(values, values[1:]))


def test_temperature_is_never_assumed():
    plain = dt50_days_from_biowin4(3.0)
    assert plain["temperature_c"] is None and "unspecified" in plain["temperature_basis"] and "dt50_days_at_20c" not in plain


def test_stated_temperature_is_normalised_to_20c_with_the_arrhenius_factor():
    result = dt50_days_from_biowin4(3.0, stated_temperature_c=25.0)
    assert result["dt50_days_at_20c"] == pytest.approx(100.0 * corrections.temperature_factor(25.0), rel=1e-12)
    assert result["dt50_days_at_20c"] > 100.0  # a value measured warm is longer at 20 C
    assert dt50_days_from_biowin4(3.0, stated_temperature_c=0.0)["dt50_days_at_20c"] is None


def test_provenance_is_always_stated_and_the_app_reconstruction_is_flagged():
    epi = dt50_days_from_biowin4(3.5)
    assert "no literature source" in epi["provenance"] and any("unsourced" in w for w in epi["warnings"])
    assert not any("reconstruction" in w for w in epi["warnings"])
    assert any("reconstruction" in w for w in dt50_days_from_biowin4(3.5, score_source="app_reconstruction")["warnings"])


def test_scores_outside_the_scale_warn_and_absurd_ones_are_refused():
    assert any("extrapolated" in w for w in dt50_days_from_biowin4(5.6)["warnings"])
    for bad in (float("nan"), float("inf"), 20, -9, True, "3"):
        with pytest.raises(ValueError):
            dt50_days_from_biowin4(bad)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        dt50_days_from_biowin4(3.0, score_source="guess")


def test_candidate_is_a_reviewable_labelled_estimate_with_no_invented_source():
    candidate = to_evidence_candidate(dt50_days_from_biowin4(3.0), chemical_name="x", cas_number="1-1-1")
    assert candidate["property_code"] == "FATE.WATER_DT50" and candidate["value"] == pytest.approx(100.0) and candidate["unit"] == "days"
    assert candidate["evidence_type"] == "model_prediction" and candidate["needs_professional_review"] is True
    assert candidate["doi"] is None and candidate["publication_title"] is None and "10 ** (5 - BIOWIN4)" in candidate["snippet"]


def test_endpoint_round_trip_and_validation():
    with TestClient(app) as client:
        ok = client.post("/api/providers/biowin-dt50/estimate", json={"biowin4_score": 3.2, "include_evidence_candidate": True, "chemical_name": "x"})
        bad = client.post("/api/providers/biowin-dt50/estimate", json={"biowin4_score": 42})
    assert ok.status_code == 200 and ok.json()["dt50_days"] == pytest.approx(10 ** 1.8)
    assert ok.json()["evidence_candidate"]["property_code"] == "FATE.WATER_DT50"
    assert bad.status_code == 422
