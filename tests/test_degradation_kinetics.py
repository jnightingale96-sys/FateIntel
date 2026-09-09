import math
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.degradation_kinetics import (
    KineticFitError,
    chi_square_error_percent,
    classify_metabolite_significance,
    dfop_model,
    endpoint_dtx,
    fit_and_select_model,
    fit_kinetic_model,
    hs_model,
    restrict_to_decline_from_maximum,
    run_degradation_kinetics_assessment,
    sfo_model,
)


DAYS = [0, 1, 3, 7, 14, 21, 30, 45, 60, 90, 120]


def sfo_observations(m0: float, k: float, n_replicates: int = 5, noise: float = 0.0):
    rng = np.random.default_rng(7)
    obs = []
    for day in DAYS:
        mean = m0 * math.exp(-k * day)
        values = [max(mean + rng.normal(0, noise), 1e-6) for _ in range(n_replicates)]
        obs.append({"day": day, "replicate_values_percent": values})
    return obs


def test_sfo_recovers_known_rate_constant_from_clean_data():
    obs = sfo_observations(100.0, 0.05, noise=0.0)
    fit = fit_kinetic_model("SFO", *_flatten(obs))
    assert fit["parameters"]["k"] == pytest.approx(0.05, rel=1e-3)
    assert fit["parameters"]["m0"] == pytest.approx(100.0, rel=1e-3)


def test_sfo_dt50_matches_analytical_ln2_over_k():
    obs = sfo_observations(100.0, 0.05, noise=0.0)
    fit = fit_kinetic_model("SFO", *_flatten(obs))
    dt50 = endpoint_dtx("SFO", fit["parameters"], m0_reference=100.0, x=50.0)
    assert dt50 == pytest.approx(math.log(2) / 0.05, rel=1e-2)


def test_sfo_dt90_matches_analytical_ln10_over_k():
    obs = sfo_observations(100.0, 0.05, noise=0.0)
    fit = fit_kinetic_model("SFO", *_flatten(obs))
    dt90 = endpoint_dtx("SFO", fit["parameters"], m0_reference=100.0, x=90.0)
    assert dt90 == pytest.approx(math.log(10) / 0.05, rel=1e-2)


def _flatten(observations):
    t, m = [], []
    for row in observations:
        for value in row["replicate_values_percent"]:
            t.append(float(row["day"]))
            m.append(float(value))
    return np.array(t), np.array(m)


def test_fit_and_select_model_prefers_sfo_for_clean_first_order_data():
    obs = sfo_observations(100.0, 0.05, noise=0.5)
    result = fit_and_select_model(obs)
    assert result["selected_model"] == "SFO"
    assert result["fits"]["SFO"]["chi_square"]["passes_guidance_threshold"] is True


def test_fit_and_select_model_escalates_past_sfo_when_sfo_genuinely_fails_guidance():
    # A sharp early drop followed by a plateau (k2=0) -- a shape no single exponential
    # can describe, verified to push the SFO chi-square error to ~21% (fails the 15%
    # guidance threshold) regardless of noise level.
    rng = np.random.default_rng(3)
    m0, k1, k2, tb = 100.0, 1.0, 0.0, 3.0
    obs = []
    for day in DAYS:
        mean = float(hs_model(np.array([day]), m0, k1, k2, tb)[0])
        obs.append({"day": day, "replicate_values_percent": [max(mean + rng.normal(0, 0.4), 1e-6) for _ in range(5)]})
    result = fit_and_select_model(obs)
    assert result["fits"]["SFO"]["chi_square"]["passes_guidance_threshold"] is False
    assert result["selected_model"] in {"HS", "DFOP", "FOMC"}


def test_fit_and_select_model_prefers_sfo_over_a_better_fitting_biphasic_model_when_sfo_passes():
    # FOCUS Kinetics: prefer the simplest model that passes guidance, even if a
    # bi-phasic model fits numerically better -- this is why the UI must show every
    # model's chi-square error, not just the winner, for a reviewer to override.
    rng = np.random.default_rng(3)
    m0, k1, k2, tb = 100.0, 0.15, 0.01, 14.0
    obs = []
    for day in DAYS:
        mean = float(hs_model(np.array([day]), m0, k1, k2, tb)[0])
        obs.append({"day": day, "replicate_values_percent": [max(mean + rng.normal(0, 0.4), 1e-6) for _ in range(5)]})
    result = fit_and_select_model(obs)
    assert result["selected_model"] == "SFO"
    assert result["fits"]["HS"]["chi_square"]["error_percent"] < result["fits"]["SFO"]["chi_square"]["error_percent"]


def test_dfop_has_no_closed_form_but_numeric_dtx_is_consistent_with_curve():
    m0, g, k1, k2 = 100.0, 0.6, 0.2, 0.01
    params = {"m0": m0, "g": g, "k1": k1, "k2": k2}
    dt50 = endpoint_dtx("DFOP", params, m0_reference=m0, x=50.0)
    value_at_dt50 = float(dfop_model(np.array([dt50]), m0, g, k1, k2)[0])
    assert value_at_dt50 == pytest.approx(m0 * 0.5, rel=1e-2)


def test_fit_kinetic_model_raises_with_too_few_points():
    with pytest.raises(KineticFitError):
        fit_kinetic_model("DFOP", np.array([0.0, 10.0]), np.array([100.0, 80.0]))


def test_chi_square_error_percent_reports_guidance_not_hard_cutoff():
    day_means = np.array([100.0, 90.0, 80.0, 70.0])
    day_predicted = np.array([100.0, 90.0, 80.0, 70.0])
    result = chi_square_error_percent(day_means, day_predicted, n_params=2)
    assert result["error_percent"] == pytest.approx(0.0, abs=1e-6)
    assert result["passes_guidance_threshold"] is True
    assert "guidance" in result["note"].lower()


def test_chi_square_error_percent_handles_insufficient_degrees_of_freedom():
    result = chi_square_error_percent(np.array([100.0, 90.0]), np.array([100.0, 90.0]), n_params=3)
    assert result["error_percent"] is None
    assert result["degrees_of_freedom"] < 1


# --- Metabolite significance classification: FOCUS Kinetics Section 8.5.1 ---

def test_focus_metabolite_exactly_at_ten_percent_is_major():
    result = classify_metabolite_significance(10.0, framework="focus_pesticide_kinetics")
    assert result["classification"] == "major"
    assert result["requires_full_kinetic_fit"] is True
    assert result["still_shown_in_pathway"] is True


def test_focus_metabolite_just_under_ten_percent_is_minor():
    result = classify_metabolite_significance(9.999, framework="focus_pesticide_kinetics")
    assert result["classification"] == "minor"
    assert result["requires_full_kinetic_fit"] is False
    assert result["still_shown_in_pathway"] is True


# --- Metabolite significance classification: VICH GL38 ---

def test_vich_metabolite_above_threshold_and_not_biochemical_pathway_is_included():
    result = classify_metabolite_significance(
        15.0, framework="vich_gl38_veterinary", forms_part_of_biochemical_pathway=False,
    )
    assert result["include_in_pec_refinement"] is True


def test_vich_metabolite_above_threshold_but_biochemical_pathway_is_excluded():
    result = classify_metabolite_significance(
        15.0, framework="vich_gl38_veterinary", forms_part_of_biochemical_pathway=True,
    )
    assert result["include_in_pec_refinement"] is False


def test_vich_metabolite_above_threshold_with_unknown_pathway_status_requires_review():
    result = classify_metabolite_significance(15.0, framework="vich_gl38_veterinary")
    assert result["requires_reviewer_judgement"] is True
    assert result["include_in_pec_refinement"] is True


def test_vich_metabolite_below_threshold_is_never_included():
    result = classify_metabolite_significance(
        5.0, framework="vich_gl38_veterinary", forms_part_of_biochemical_pathway=False,
    )
    assert result["meets_dose_threshold"] is False
    assert result["include_in_pec_refinement"] is False


def test_unknown_framework_is_rejected():
    with pytest.raises(ValueError):
        classify_metabolite_significance(50.0, framework="not_a_real_framework")  # type: ignore[arg-type]


# --- Formation-then-decline metabolites: FOCUS Kinetics Section 8.5.1 sanctioned fallback ---

FORMATION_THEN_DECLINE_OBSERVATIONS = [
    {"day": 0, "replicate_values_percent": [0.0, 0.0, 0.0]},
    {"day": 7, "replicate_values_percent": [5.1, 4.9, 5.4]},
    {"day": 14, "replicate_values_percent": [12.1, 11.6, 12.5]},
    {"day": 30, "replicate_values_percent": [18.0, 17.6, 18.4]},
    {"day": 60, "replicate_values_percent": [15.0, 14.6, 15.4]},
    {"day": 90, "replicate_values_percent": [9.0, 8.6, 9.4]},
    {"day": 120, "replicate_values_percent": [5.0, 4.6, 5.4]},
]


def test_restrict_to_decline_from_maximum_rebases_day_to_the_peak():
    restricted, metadata = restrict_to_decline_from_maximum(FORMATION_THEN_DECLINE_OBSERVATIONS)
    assert metadata is not None
    assert metadata["restricted"] is True
    assert metadata["peak_day"] == 30.0
    assert metadata["peak_percent"] == pytest.approx(18.0)
    assert restricted[0]["day"] == 0.0
    assert restricted[-1]["day"] == 90.0  # 120 - 30


def test_restrict_to_decline_from_maximum_is_a_no_op_for_already_declining_data():
    obs = sfo_observations(100.0, 0.05, noise=0.0)
    restricted, metadata = restrict_to_decline_from_maximum(obs)
    assert metadata is None
    assert restricted == obs


def test_direct_fit_of_formation_then_decline_data_is_scientifically_invalid():
    # Documents the bug this module must never regress to: fitting a monotonic-decline
    # model directly to a rise-then-fall series drives every model to a degenerate
    # near-zero rate constant and a nonsensical, effectively-infinite DT50.
    result = fit_and_select_model(FORMATION_THEN_DECLINE_OBSERVATIONS)
    selected = result["fits"][result["selected_model"]]
    assert selected["chi_square"]["error_percent"] > 40  # every model fails badly
    assert selected["dt50_days"] > 1_000_000  # the nonsensical result this module must route around


def test_run_assessment_uses_decline_from_maximum_for_a_forming_metabolite():
    parent_obs = sfo_observations(100.0, 0.03, noise=0.3)
    result = run_degradation_kinetics_assessment(
        regulatory_framework="focus_pesticide_kinetics",
        matrix="soil",
        parent_name="Parent",
        parent_observations=parent_obs,
        metabolites=[{"name": "Forming TP", "observations": FORMATION_THEN_DECLINE_OBSERVATIONS}],
    )
    metabolite = result["metabolites"][0]
    assert metabolite["kinetics"]["fit_basis"] == "decline_from_observed_maximum"
    assert metabolite["kinetics"]["fit_basis_detail"]["peak_day"] == 30.0
    selected = metabolite["kinetics"]["fits"][metabolite["kinetics"]["selected_model"]]
    # A sane, bounded DT50 measured from the peak -- not the degenerate ~745 million days
    # a direct fit to the raw rise-and-fall series produces.
    assert 0 < selected["dt50_days"] < 365


def test_run_assessment_marks_direct_fit_for_a_metabolite_already_declining_from_first_sample():
    parent_obs = sfo_observations(100.0, 0.03, noise=0.3)
    already_declining = [
        {"day": 0, "replicate_values_percent": [20.0, 19.5, 20.5]},
        {"day": 14, "replicate_values_percent": [14.0, 13.6, 14.4]},
        {"day": 30, "replicate_values_percent": [8.0, 7.6, 8.4]},
        {"day": 60, "replicate_values_percent": [3.0, 2.7, 3.3]},
    ]
    result = run_degradation_kinetics_assessment(
        regulatory_framework="focus_pesticide_kinetics",
        matrix="soil",
        parent_name="Parent",
        parent_observations=parent_obs,
        metabolites=[{"name": "Already Declining TP", "observations": already_declining}],
    )
    metabolite = result["metabolites"][0]
    assert metabolite["kinetics"]["fit_basis"] == "direct_fit_from_dose"
    assert "fit_basis_detail" not in metabolite["kinetics"]


# --- Full orchestration ---

def test_run_assessment_fits_major_metabolite_and_flags_minor_one():
    parent_obs = sfo_observations(100.0, 0.05, noise=0.3)
    major_metabolite_obs = sfo_observations(30.0, 0.02, noise=0.3)
    minor_metabolite_obs = [
        {"day": 0, "replicate_values_percent": [0.0] * 3},
        {"day": 30, "replicate_values_percent": [4.0, 4.5, 3.8]},
    ]
    result = run_degradation_kinetics_assessment(
        regulatory_framework="focus_pesticide_kinetics",
        matrix="soil",
        parent_name="Test Parent",
        parent_observations=parent_obs,
        metabolites=[
            {"name": "Major TP", "observations": major_metabolite_obs},
            {"name": "Minor TP", "observations": minor_metabolite_obs},
        ],
    )
    assert result["parent"]["kinetics"]["selected_model"] is not None
    major = next(m for m in result["metabolites"] if m["name"] == "Major TP")
    minor = next(m for m in result["metabolites"] if m["name"] == "Minor TP")
    assert major["significance"]["classification"] == "major"
    assert major["kinetics"] is not None
    assert minor["significance"]["classification"] == "minor"
    assert minor["kinetics"] is None
    assert "kinetics_note" in minor


def test_run_assessment_requires_at_least_one_parent_observation():
    with pytest.raises(ValueError):
        run_degradation_kinetics_assessment(
            regulatory_framework="focus_pesticide_kinetics",
            matrix="soil",
            parent_name="Test Parent",
            parent_observations=[],
        )


# --- Route tests ---

def _payload(**overrides):
    obs = sfo_observations(100.0, 0.05, noise=0.3)
    base = {
        "regulatory_framework": "focus_pesticide_kinetics",
        "matrix": "soil",
        "parent_name": "Test Parent",
        "parent_observations": obs,
        "metabolites": [],
    }
    base.update(overrides)
    return base


def test_assess_route_returns_fitted_result_without_persistence():
    with TestClient(app) as client:
        response = client.post("/api/degradation-kinetics/assess", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["model_run_id"] is None
    assert body["outputs"]["parent"]["kinetics"]["selected_model"] == "SFO"


def test_assess_route_rejects_single_observation_day():
    payload = _payload(parent_observations=[{"day": 0, "replicate_values_percent": [100.0, 99.0]}])
    with TestClient(app) as client:
        response = client.post("/api/degradation-kinetics/assess", json=payload)
    assert response.status_code == 422


def test_assess_route_persists_model_run_when_project_and_chemical_given():
    with TestClient(app) as client:
        project = client.post(
            "/api/projects",
            json={"name": f"Kinetics QA {uuid4().hex[:8]}", "jurisdiction": "UK/EU screening"},
        ).json()
        chemical = client.get("/api/chemicals").json()[0]
        response = client.post(
            "/api/degradation-kinetics/assess",
            json=_payload(project_id=project["id"], chemical_id=chemical["id"]),
        )
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["model_run_id"], int)
        audit = client.get(f"/api/projects/{project['id']}/audit").json()
    matching = [row for row in audit if row["action"] == "degradation_kinetics_assessed"]
    assert matching and matching[0]["payload"]["parent_selected_model"] == "SFO"


def test_assess_route_includes_metabolite_significance_and_citations():
    payload = _payload(
        metabolites=[
            {
                "name": "Major TP",
                "observations": sfo_observations(25.0, 0.02, noise=0.2),
            }
        ]
    )
    with TestClient(app) as client:
        response = client.post("/api/degradation-kinetics/assess", json=payload)
    assert response.status_code == 200
    metabolite = response.json()["outputs"]["metabolites"][0]
    assert metabolite["significance"]["classification"] == "major"
    assert "FOCUS" in metabolite["significance"]["citation"]
