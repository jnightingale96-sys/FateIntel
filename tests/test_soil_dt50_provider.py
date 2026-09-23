"""Soil DT50 provider (PEPPER GPR, Fenner Lab): corrections, licence gate, API, evidence conversion, model fidelity.

The corrections are checked against hand formulas. The model tests need scikit-learn, RDKit, padelpy and a Java
runtime; they are skipped (not failed) where those are absent. ``tests/data/demo_output_25C.csv`` was produced by the
provider's author under scikit-learn 1.6.1 and is used as a fidelity reference: this repo runs scikit-learn 1.9.1.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from scipy.stats import norm

from app.config import Settings
from app.main import app
from app.services.soil_dt50 import availability, capabilities, commercial_gate, corrections
from app.services.soil_dt50.evidence import to_evidence_candidate

DATA = Path(__file__).parent / "data"
MODEL_AVAILABLE = availability()["available"]
needs_model = pytest.mark.skipif(not MODEL_AVAILABLE, reason=f"soil DT50 dependencies missing: {availability()['missing']}")


# ---------------------------------------------------------------------------
# FOCUS / EFSA corrections (no dependencies)
# ---------------------------------------------------------------------------


def test_temperature_factor_is_the_arrhenius_expression():
    for temp in (1, 5, 10, 20, 28, 35):
        expected = math.exp(65400 / 8.314 * (1 / 293.15 - 1 / (temp + 273.15)))
        assert corrections.temperature_factor(temp) == pytest.approx(expected, rel=1e-12)


def test_ea_65_4_kj_mol_is_the_efsa_q10_of_2_58_and_warm_soil_roughly_halves_dt50():
    assert corrections.temperature_factor(20) / corrections.temperature_factor(10) == pytest.approx(2.58, abs=0.01)
    # provider README: "at 28 C, DT50 is roughly half the 20 C value"
    assert 1.8 < corrections.temperature_factor(28) < 2.3


def test_no_degradation_at_or_below_freezing():
    dt50, factors = corrections.to_site_conditions(30, temp_c=0)
    assert factors["f_total"] == 0 and math.isinf(dt50)
    assert corrections.temperature_factor(-5) == 0


def test_walker_moisture_factor_and_cap():
    assert corrections.moisture_factor(20, 40) == pytest.approx(0.5 ** 0.7, rel=1e-12)
    assert corrections.moisture_factor(60, 40) == 1.0
    assert corrections.moisture_factor(0, 40) == 0.0
    with pytest.raises(ValueError):
        corrections.moisture_factor(20, 0)


def test_focus_depth_factors_at_the_band_edges():
    assert [corrections.depth_factor(d) for d in (0, 29.9, 30, 59.9, 60, 100, 100.1)] == [1.0, 1.0, 0.5, 0.5, 0.3, 0.3, 0.0]


def test_site_and_reference_normalisation_round_trip():
    site, _ = corrections.to_site_conditions(50.0, temp_c=28, theta=25, theta_ref=35)
    assert corrections.to_reference_conditions(site, temp_c=28, theta=25, theta_ref=35) == pytest.approx(50.0)


def test_combined_factor_is_the_product_of_the_three():
    f = corrections.combined_factor(temp_c=25, theta=30, theta_ref=40, depth_cm=45)
    assert f["f_total"] == pytest.approx(f["f_temperature"] * f["f_moisture"] * 0.5)


# ---------------------------------------------------------------------------
# Licence gate and availability
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("environment, confirmed, expected", [
    ("local", False, True), ("test", False, True), ("staging", False, False), ("production", False, False),
    ("production", True, True), ("staging", True, True),
])
def test_gate_matches_the_enviPath_restriction_shape(environment, confirmed, expected):
    config = Settings(_env_file=None, envirochem_environment=environment, soil_dt50_commercial_license_confirmed=confirmed)
    assert commercial_gate(config)[0] is expected


def test_capabilities_state_what_the_model_is_not():
    caps = capabilities(Settings(_env_file=None, envirochem_environment="production"))
    assert caps["enabled"] is False and "training_data_licence" in caps["licence_status"]
    joined = " ".join(caps["not_provided"])
    assert "QMRF" in joined and "mineralisation" in joined and "field dissipation" in joined


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_correct_endpoint_needs_neither_model_nor_licence(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.api.commercial_gate", lambda: (False, "closed"))
    with TestClient(app) as client:
        response = client.post("/api/providers/soil-dt50/correct", json={"dt50_ref_days": 60, "conditions": {"temperature_c": 28}})
    assert response.status_code == 200
    assert response.json()["DT50_site_days"] == pytest.approx(60 / corrections.temperature_factor(28))


def test_correct_endpoint_warns_when_a_moisture_correction_is_silently_impossible():
    with TestClient(app) as client:
        response = client.post("/api/providers/soil-dt50/correct", json={"dt50_ref_days": 60, "conditions": {"moisture": 25}})
    body = response.json()
    assert body["factors"]["f_moisture"] == 1.0 and any("moisture correction NOT applied" in w for w in body["warnings"])


def test_correct_endpoint_reports_no_degradation_instead_of_infinity():
    with TestClient(app) as client:
        body = client.post("/api/providers/soil-dt50/correct", json={"dt50_ref_days": 60, "conditions": {"temperature_c": -3}}).json()
    assert body["no_degradation"] is True and body["DT50_site_days"] is None


def test_predict_is_refused_when_the_licence_gate_is_closed(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.api.commercial_gate", lambda: (False, "eawag_soil_training_data_licence_required_for_staging_or_production"))
    with TestClient(app) as client:
        predict = client.post("/api/providers/soil-dt50/predict", json={"chemicals": [{"smiles": "CCO"}]})
        card = client.get("/api/providers/soil-dt50/model-card")
    assert predict.status_code == 403 and card.status_code == 403
    assert "licence_required" in predict.json()["detail"]


def test_predict_reports_missing_dependencies_as_503_not_a_crash(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.api.availability", lambda: {"available": False, "missing": ["java runtime (PaDEL)"]})
    with TestClient(app) as client:
        response = client.post("/api/providers/soil-dt50/predict", json={"chemicals": [{"smiles": "CCO"}]})
    assert response.status_code == 503 and "java runtime" in response.json()["detail"]


def test_predict_validates_its_inputs():
    with TestClient(app) as client:
        assert client.post("/api/providers/soil-dt50/predict", json={"chemicals": []}).status_code == 422
        assert client.post("/api/providers/soil-dt50/predict", json={"chemicals": [{"smiles": ""}]}).status_code == 422
        assert client.post("/api/providers/soil-dt50/correct", json={"dt50_ref_days": -1, "conditions": {}}).status_code == 422


# ---------------------------------------------------------------------------
# Evidence-hub conversion (hand-built results, no model)
# ---------------------------------------------------------------------------

_PREDICTED = {
    "status": "ok", "smiles": "CCNc1nc(Cl)nc(NC(C)C)n1", "warnings": ["low-confidence prediction"],
    "recommended": {"DT50_ref_days": 110.59, "basis": "predicted (PEPPER GPR)", "confidence": "high"},
    "prediction": {"DT50_mean_90CI_days": [30.0, 400.0], "DT50_single_soil_90PI_days": [20.0, 600.0]},
    "applicability": {"max_tanimoto": 1.0, "notes": ["perfluoroalkyl moiety - sparse"]}, "persistence": {"p_P": 0.42, "screening_flag_potential_P": True},
}
_MEASURED = {
    **_PREDICTED, "recommended": {"DT50_ref_days": 45.0, "basis": "measured (EAWAG-SOIL)", "confidence": "measured"},
    "experimental": {"n_half_lives": 12, "logDT50_sd_between_soils": 0.31},
}


def test_predicted_value_becomes_a_labelled_model_estimate_needing_review():
    candidate = to_evidence_candidate(_PREDICTED, chemical_name="atrazine", cas_number="1912-24-9")
    assert candidate["property_code"] == "FATE.SOIL_DT50" and candidate["value"] == 110.59 and candidate["unit"] == "days"
    assert candidate["evidence_type"] == "model_prediction" and candidate["needs_professional_review"] is True
    assert "MODEL ESTIMATE" in candidate["notes"] and "not a regulatory" in candidate["notes"].lower()
    assert candidate["doi"] is None  # never invented
    assert candidate["rights_status"] == "training_data_licence_to_confirm"


def test_measured_value_is_labelled_as_a_database_record_not_a_prediction():
    candidate = to_evidence_candidate(_MEASURED, chemical_name="atrazine")
    assert candidate["evidence_type"] == "database_record" and "MODEL ESTIMATE" not in candidate["notes"]
    assert "12 EAWAG-SOIL half-lives" in candidate["snippet"]


@pytest.mark.parametrize("result", [{"status": "outside_domain", "recommended": None}, {"status": "failed"}, {"status": "ok", "recommended": None}])
def test_no_candidate_without_a_value(result):
    assert to_evidence_candidate(result, chemical_name="x") is None


def test_import_allowed_follows_the_gate():
    assert to_evidence_candidate(_PREDICTED, chemical_name="x", import_allowed=False)["import_allowed"] is False


# ---------------------------------------------------------------------------
# Model fidelity and behaviour (needs scikit-learn, RDKit, padelpy, Java)
# ---------------------------------------------------------------------------

DEMO_CONDITIONS = {"temperature_c": 25.0, "moisture": 30.0, "moisture_ref": 40.0}


@pytest.fixture(scope="module")
def batch():
    """One PaDEL run for everything below (a JVM start dominates the cost)."""
    from app.services.soil_dt50.predictor import SoilDT50Predictor

    predictor = SoilDT50Predictor()
    with (DATA / "demo_input.csv").open(encoding="utf-8") as handle:
        demo = list(csv.DictReader(handle))
    chemicals = [{"id": r["id"], "name": r["name"], "smiles": r["SMILES"]} for r in demo]
    chemicals += [
        {"id": "train", "name": "training compound", "smiles": predictor.train["SMILES"].iloc[0]},
        {"id": "inorg", "name": "sulfuric acid", "smiles": "O=S(=O)(O)O"},
        {"id": "bad", "name": "unparseable", "smiles": "not a smiles"},
    ]
    results = {r.id: r for r in predictor.predict(chemicals, conditions=DEMO_CONDITIONS)}
    results["_predicted_only"] = predictor.predict([chemicals[-3]], prefer_experimental=False)[0]
    results["_strict_salt"] = predictor.predict([{"id": "s", "smiles": "CC(=O)[O-].[Na+]"}], strip_counterions=False)[0]
    return predictor, results


@needs_model
def test_predictions_reproduce_the_authors_reference_output_on_a_newer_scikit_learn(batch):
    _predictor, results = batch
    with (DATA / "demo_output_25C.csv").open(encoding="utf-8") as handle:
        reference = {row["id"]: row for row in csv.DictReader(handle)}
    assert len(reference) == 7
    for cid, row in reference.items():
        got = results[cid]
        assert got.prediction["logDT50_mean"] == pytest.approx(float(row["prediction.logDT50_mean"]), abs=1e-9), row["name"]
        assert got.prediction["logDT50_sd_of_mean"] == pytest.approx(float(row["prediction.logDT50_sd_of_mean"]), abs=1e-9)
        assert got.recommended["DT50_ref_days"] == pytest.approx(float(row["recommended.DT50_ref_days"]), abs=1e-9)
        assert got.persistence["p_P"] == pytest.approx(float(row["persistence.p_P"]), abs=1e-9)
        assert got.site["DT50_site_days"] == pytest.approx(float(row["site.DT50_site_days"]), abs=1e-9)


@needs_model
def test_site_dt50_is_the_reference_dt50_divided_by_the_hand_computed_factors(batch):
    _predictor, results = batch
    factor = corrections.temperature_factor(25.0) * (30 / 40) ** 0.7
    for cid in "1234567":
        r = results[cid]
        assert r.site["DT50_site_days"] == pytest.approx(r.recommended["DT50_ref_days"] / factor, rel=5e-3, abs=0.02)  # both values are rounded to 2 d.p.


@needs_model
def test_persistence_probabilities_are_the_normal_tail_of_the_reported_mean_and_sd(batch):
    _predictor, results = batch
    for cid in "1234567":
        r = results[cid]
        mu, sd = r.recommended["logDT50"], r.recommended["logDT50_sd"]
        assert r.persistence["p_P"] == pytest.approx(1 - norm.cdf((math.log10(120) - mu) / sd), abs=2e-3)
        assert r.persistence["p_vP"] == pytest.approx(1 - norm.cdf((math.log10(180) - mu) / sd), abs=2e-3)
        assert r.persistence["p_nP"] == pytest.approx(1 - r.persistence["p_P"], abs=2e-3)


@needs_model
def test_uncertainty_intervals_nest_and_the_single_soil_interval_is_wider(batch):
    _predictor, results = batch
    for cid in "1234567":
        prediction = results[cid].prediction
        ci_lo, ci_hi = prediction["DT50_mean_90CI_days"]
        pi_lo, pi_hi = prediction["DT50_single_soil_90PI_days"]
        assert ci_lo < prediction["DT50_days"] < ci_hi
        assert pi_lo <= ci_lo and pi_hi >= ci_hi


@needs_model
def test_measured_data_win_over_the_prediction_by_default_and_can_be_switched_off(batch):
    _predictor, results = batch
    trained, predicted_only = results["train"], results["_predicted_only"]
    assert trained.experimental is not None and trained.recommended["basis"].startswith("measured")
    assert trained.recommended["confidence"] == "measured"
    assert any("training set" in w for w in trained.warnings)  # a fitted value is never passed off as independent
    assert predicted_only.recommended["basis"].startswith("predicted")


@needs_model
def test_perfluoroalkyl_compounds_are_overridden_to_vp_with_the_numeric_value_flagged(batch):
    _predictor, results = batch
    pfoa = results["5"]
    assert pfoa.persistence["class_central"] == "vP" and "override" in pfoa.persistence
    assert pfoa.persistence["screening_flag_potential_P"] is True
    assert any("perfluoroalkyl" in note for note in pfoa.applicability["notes"])


@needs_model
def test_salts_are_reduced_to_the_organic_parent_with_a_warning_or_refused_when_strict(batch):
    _predictor, results = batch
    assert results["2"].smiles and "Na" not in results["2"].smiles
    assert any("largest organic fragment" in w for w in results["2"].warnings)
    assert results["_strict_salt"].status == "outside_domain"


@needs_model
def test_inorganic_and_unparseable_input_is_reported_not_predicted(batch):
    _predictor, results = batch
    assert results["inorg"].status == "outside_domain" and results["inorg"].recommended is None
    assert results["bad"].status == "outside_domain" and any("could not be parsed" in w for w in results["bad"].warnings)


@needs_model
def test_moisture_without_a_reference_is_warned_about_not_silently_skipped(batch):
    predictor, _ = batch
    result = predictor.predict(["CCNc1nc(Cl)nc(NC(C)C)n1"], conditions={"temperature_c": 25, "moisture": 30})[0]
    assert any("moisture correction NOT applied" in w for w in result.warnings)


@needs_model
def test_provenance_carries_the_citation_and_model_version(batch):
    _predictor, results = batch
    provenance = results["6"].provenance
    assert "Hafner" in provenance["citation"] and "Latino" in provenance["citation"] and provenance["model_version"]


@needs_model
def test_model_card_states_its_own_cross_validation_and_fidelity():
    card = json.loads((Path(__file__).resolve().parents[1] / "app" / "data" / "soil_dt50" / "model_card.json").read_text(encoding="utf-8"))
    assert card["fidelity_vs_pepper_lab"]["max_abs_diff_mean"] == 0.0
    overall = card["cross_validation"]["overall"]
    assert 0.5 < overall["within_factor_3"] < 0.6 and overall["R2"] < 0.35  # moderate performance, stated plainly


@needs_model
def test_predict_endpoint_round_trip_with_an_evidence_candidate():
    with TestClient(app) as client:
        response = client.post("/api/providers/soil-dt50/predict", json={
            "chemicals": [{"id": "x", "name": "ibuprofen", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O", "cas_number": "15687-27-1"}],
            "conditions": {"temperature_c": 28, "moisture": 25, "moisture_ref": 35}, "include_evidence_candidate": True,
        })
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["status"] == "ok" and row["site"]["DT50_site_days"] < row["recommended"]["DT50_ref_days"]
    assert row["evidence_candidate"]["property_code"] == "FATE.SOIL_DT50"
    assert row["evidence_candidate"]["cas_number"] == "15687-27-1"
