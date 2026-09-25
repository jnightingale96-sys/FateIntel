"""Parent -> transformation-product soil kinetics, checked against independent solutions.

The reference values come from hand formulas and from scipy's ODE solver, never from the module's own closed form.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import minimize_scalar

from app.services.soil_dt50 import corrections
from app.services.tp_soil_fate import TpFateInputError, run_tp_soil_fate


def _payload(**overrides):
    payload = {
        "parent": {"name": "P", "molecular_weight_g_mol": 200.0, "dt50_days": 20.0, "dt50_source": "measured"},
        "products": [{"name": "M1", "molecular_weight_g_mol": 100.0, "formation_fraction": 0.6, "dt50_days": 50.0, "dt50_source": "measured"}],
        "initial_parent_mg_kg": 2.0, "duration_days": 200.0, "n_points": 201,
    }
    payload.update(overrides)
    return payload


def _ode(k_p, k_ms, ffs, t_eval):
    """Moles per mole of parent applied: dP = -kP P, dMj = ffj kP P - kj Mj."""

    def rhs(_t, y):
        out = [-k_p * y[0]]
        out += [ff * k_p * y[0] - k * y[1 + j] for j, (ff, k) in enumerate(zip(ffs, k_ms))]
        return out

    sol = solve_ivp(rhs, (0, t_eval[-1]), [1.0] + [0.0] * len(ffs), t_eval=t_eval, rtol=1e-11, atol=1e-13, method="LSODA")
    return sol.y


def test_parent_and_product_match_an_independent_ode_solution_and_the_molar_mass_ratio():
    result = run_tp_soil_fate(_payload())
    t = np.array(result["times_days"])
    y = _ode(math.log(2) / 20.0, [math.log(2) / 50.0], [0.6], t)
    p0_mol = 2.0 / 200.0
    assert np.allclose(result["parent"]["series_mg_kg"], y[0] * 2.0, rtol=1e-8, atol=1e-12)
    assert np.allclose(result["products"][0]["series_mg_kg"], y[1] * p0_mol * 100.0, rtol=1e-7, atol=1e-12)
    assert np.allclose(result["products"][0]["series_percent_of_applied_molar"], y[1] * 100.0, rtol=1e-7, atol=1e-10)


def test_hand_value_at_one_time_point():
    # kP = ln2/20, kM = ln2/50, ff 0.6: M/P0 = ff*kP*(e^-kP t - e^-kM t)/(kM - kP) at t = 30
    kp, km, t = math.log(2) / 20, math.log(2) / 50, 30.0
    expected = 0.6 * kp * (math.exp(-kp * t) - math.exp(-km * t)) / (km - kp)
    result = run_tp_soil_fate(_payload(duration_days=60.0, n_points=61))
    assert result["products"][0]["series_percent_of_applied_molar"][30] == pytest.approx(expected * 100.0, rel=1e-10)


def test_peak_time_and_height_match_a_numerical_maximiser():
    result = run_tp_soil_fate(_payload())
    kp, km = math.log(2) / 20, math.log(2) / 50

    def neg(t):
        return -0.6 * kp * (math.exp(-kp * t) - math.exp(-km * t)) / (km - kp)

    best = minimize_scalar(neg, bounds=(0.01, 199.0), method="bounded", options={"xatol": 1e-9})
    peak = result["products"][0]["peak"]
    assert peak["time_days"] == pytest.approx(best.x, rel=1e-5)
    assert peak["percent_of_applied_molar"] == pytest.approx(-best.fun * 100.0, rel=1e-9)
    assert peak["concentration_mg_kg"] == pytest.approx(-best.fun * (2.0 / 200.0) * 100.0, rel=1e-9)


def test_equal_rate_constants_use_the_limiting_form_and_agree_with_the_ode():
    payload = _payload()
    payload["products"][0]["dt50_days"] = 20.0
    result = run_tp_soil_fate(payload)
    kp = math.log(2) / 20.0
    t = np.array(result["times_days"])
    y = _ode(kp, [kp], [0.6], t)
    assert np.allclose(result["products"][0]["series_percent_of_applied_molar"], y[1] * 100.0, rtol=1e-6, atol=1e-9)
    assert result["products"][0]["peak"]["time_days"] == pytest.approx(1.0 / kp, rel=1e-9)
    assert result["products"][0]["peak"]["percent_of_applied_molar"] == pytest.approx(0.6 / math.e * 100.0, rel=1e-9)


def test_moles_are_conserved_and_never_negative_for_random_inputs():
    rng = random.Random(20260924)
    for _ in range(40):
        n = rng.randint(1, 3)
        ffs = [rng.uniform(0.05, 1.0 / n) for _ in range(n)]
        products = [
            {"name": f"M{i}", "molecular_weight_g_mol": rng.uniform(80, 400), "formation_fraction": ff,
             "dt50_days": rng.uniform(1, 400), "dt50_source": "user_estimate"}
            for i, ff in enumerate(ffs)
        ]
        payload = _payload(products=products)
        payload["parent"] = {"name": "P", "molecular_weight_g_mol": rng.uniform(100, 500), "dt50_days": rng.uniform(1, 300), "dt50_source": "measured"}
        result = run_tp_soil_fate(payload)
        p_mol = np.array(result["parent"]["series_mg_kg"]) / payload["parent"]["molecular_weight_g_mol"]
        total = p_mol.copy()
        for prod in result["products"]:
            series = np.array(prod["series_mg_kg"])
            assert (series >= -1e-15).all()
            total += series / prod["molecular_weight_g_mol"]
        assert (total <= p_mol[0] * (1 + 1e-9)).all()  # products can only hold what the parent lost


def test_slower_parent_delays_and_lowers_the_peak_of_a_fast_product():
    fast = run_tp_soil_fate(_payload())["products"][0]["peak"]
    payload = _payload()
    payload["parent"]["dt50_days"] = 80.0
    slow = run_tp_soil_fate(payload)["products"][0]["peak"]
    assert slow["time_days"] > fast["time_days"] and slow["percent_of_applied_molar"] < fast["percent_of_applied_molar"]


def test_non_degrading_product_accumulates_to_its_formation_fraction():
    payload = _payload(duration_days=2000.0)
    payload["products"][0]["dt50_days"] = 1e12
    result = run_tp_soil_fate(payload)
    assert result["products"][0]["series_percent_of_applied_molar"][-1] == pytest.approx(60.0, rel=1e-6)


def test_eu_region_moves_both_dt50s_with_the_arrhenius_factor():
    result = run_tp_soil_fate(_payload(region="EU"))
    factor = corrections.temperature_factor(10.0)
    assert result["target_temperature_c"] == 10.0 and "EU" in result["temperature_basis"]
    assert result["parent"]["dt50_days"] == pytest.approx(20.0 / factor, rel=1e-12)  # measured at 20 C default
    assert result["products"][0]["dt50_days"] == pytest.approx(50.0 / factor, rel=1e-12)
    assert 2.5 < result["parent"]["dt50_days"] / 20.0 < 2.7  # Q10 = 2.58 over 10 C, EFSA 2007


def test_explicit_temperature_wins_over_region_and_unrecorded_region_is_refused():
    assert run_tp_soil_fate(_payload(region="EU", temperature_c=15.0))["target_temperature_c"] == 15.0
    with pytest.raises(TpFateInputError, match="no reference temperature"):
        run_tp_soil_fate(_payload(region="AU"))
    default = run_tp_soil_fate(_payload())
    assert default["target_temperature_c"] == 20.0 and "reference" in default["temperature_basis"]


def test_dt50_stated_at_another_temperature_is_normalised():
    payload = _payload(temperature_c=20.0)
    payload["parent"]["dt50_temperature_c"] = 10.0
    result = run_tp_soil_fate(payload)
    assert result["parent"]["dt50_days"] == pytest.approx(20.0 * corrections.temperature_factor(10.0), rel=1e-12)


def test_freezing_target_stops_all_change_and_says_so():
    result = run_tp_soil_fate(_payload(temperature_c=-5.0))
    assert result["parent"]["series_mg_kg"][-1] == pytest.approx(2.0)
    assert all(v == 0.0 for v in result["products"][0]["series_mg_kg"])
    assert any("0 C" in w for w in result["warnings"])


def test_major_transformation_product_flag_uses_the_oecd_10_percent_line():
    big = run_tp_soil_fate(_payload())["products"][0]
    assert big["peak"]["percent_of_applied_molar"] > 10 and big["major_transformation_product"]["flag"] is True
    payload = _payload()
    payload["products"][0]["formation_fraction"] = 0.05
    small = run_tp_soil_fate(payload)["products"][0]
    assert small["major_transformation_product"]["flag"] is False and "para 51" in small["major_transformation_product"]["basis"]


def test_default_formation_fraction_is_one_labelled_and_not_additive():
    payload = _payload()
    del payload["products"][0]["formation_fraction"]
    payload["products"].append({"name": "M2", "molecular_weight_g_mol": 90.0, "dt50_days": 30.0, "dt50_source": "measured"})
    result = run_tp_soil_fate(payload)
    assert [p["formation_fraction"] for p in result["products"]] == [1.0, 1.0]
    assert "EFSA 2017" in result["products"][0]["formation_fraction_basis"]
    assert any("not additive" in w for w in result["warnings"])


def test_supplied_formation_fractions_summing_above_one_are_refused():
    payload = _payload()
    payload["products"][0]["formation_fraction"] = 0.7
    payload["products"].append({"name": "M2", "molecular_weight_g_mol": 90.0, "formation_fraction": 0.5, "dt50_days": 30.0})
    with pytest.raises(TpFateInputError, match="more than 1"):
        run_tp_soil_fate(payload)


def test_biowin_screen_supplies_a_labelled_dt50_at_25c_and_is_normalised_by_arrhenius():
    payload = _payload(temperature_c=20.0)
    payload["products"][0].pop("dt50_days")
    payload["products"][0]["biowin4_score"] = 3.0  # aquatic 10**3 h; soil = 0.5 x = 500 h at 25 C = 500/24 d
    product = run_tp_soil_fate(payload)["products"][0]
    assert product["dt50_source"] == "biowin_screen" and "unsourced" in product["dt50_basis"] and "last resort" in product["dt50_basis"]
    assert product["dt50_days"] == pytest.approx(500.0 / 24.0 * corrections.temperature_factor(25.0), rel=1e-12)


def test_smiles_fills_mw_and_a_flagged_crippen_logp():
    payload = _payload()
    payload["products"][0].pop("molecular_weight_g_mol")
    payload["products"][0]["smiles"] = "CCO"
    product = run_tp_soil_fate(payload)["products"][0]
    assert product["molecular_weight_g_mol"] == pytest.approx(46.069, abs=0.01)
    assert product["log_p"] is not None and any("Crippen" in n for n in product["property_notes"])
    payload["products"][0]["smiles"] = "not a smiles ((("
    with pytest.raises(TpFateInputError, match="could not be parsed"):
        run_tp_soil_fate(payload)


def test_koc_and_clp_mobility_come_from_the_sorption_module_when_soil_and_log_p_are_given():
    payload = _payload(soil={"organic_carbon_fraction": 0.02, "soil_ph": 7.0})
    payload["parent"]["log_p"] = 2.45
    payload["products"][0]["log_p"] = 0.5
    result = run_tp_soil_fate(payload)
    parent_sorption = result["parent"]["sorption"]
    assert parent_sorption["available"] and parent_sorption["log_koc"] == pytest.approx(2.2736, abs=1e-3)  # Li neutral, hand-checked
    assert parent_sorption["mobile_clp"] is True and parent_sorption["very_mobile_clp"] is False
    assert result["products"][0]["sorption"]["log_koc"] < parent_sorption["log_koc"]  # more polar sorbs less
    assert run_tp_soil_fate(_payload())["parent"]["sorption"] is None  # nothing invented without inputs


def test_a_base_without_cec_uses_franco_trapp_rather_than_failing():
    payload = _payload(soil={"organic_carbon_fraction": 0.02, "soil_ph": 6.0})
    payload["products"][0].update(log_p=2.0, pka_b=9.5)
    assert run_tp_soil_fate(payload)["products"][0]["sorption"]["available"] is True


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p.update(products=[]), "at least one"),
    (lambda p: p.update(initial_parent_mg_kg=0), "initial_parent_mg_kg"),
    (lambda p: p.update(duration_days=10_000), "duration_days"),
    (lambda p: p["parent"].update(dt50_days=-3), "dt50_days"),
    (lambda p: p["parent"].pop("dt50_days"), "dt50_days"),
    (lambda p: p["parent"].update(dt50_source="guess"), "dt50_source"),
    (lambda p: p["products"][0].update(formation_fraction=1.5), "formation_fraction"),
    (lambda p: p["products"][0].pop("molecular_weight_g_mol"), "molecular_weight"),
    (lambda p: p.update(temperature_c=90), "temperature_c"),
])
def test_bad_inputs_are_refused_with_a_message(mutation, message):
    payload = _payload()
    mutation(payload)
    with pytest.raises(TpFateInputError, match=message):
        run_tp_soil_fate(payload)


def test_endpoint_runs_reports_options_and_maps_errors_to_422():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        ok = client.post("/api/tp-soil-fate/run", json=_payload(region="EU"))
        frozen = client.post("/api/tp-soil-fate/run", json=_payload(temperature_c=-5.0))
        bad = client.post("/api/tp-soil-fate/run", json=_payload(products=[]))
        options = client.get("/api/tp-soil-fate/options")
    assert ok.status_code == 200 and ok.json()["target_temperature_c"] == 10.0
    assert frozen.status_code == 200 and frozen.json()["parent"]["dt50_days"] is None
    assert bad.status_code == 422 and "at least one" in bad.json()["detail"]
    assert options.json()["region_temperature_c"] == {"EU": 10.0} and options.json()["major_tp_percent"] == 10.0


# ---------------------------------------------------------------- chains and branches ----------------------------------

def _chain_payload(**overrides):
    payload = _payload(duration_days=400.0, n_points=401)
    payload["products"] = [
        {"name": "M1", "molecular_weight_g_mol": 100.0, "formation_fraction": 0.6, "dt50_days": 50.0, "dt50_source": "measured"},
        {"name": "M2", "molecular_weight_g_mol": 80.0, "formation_fraction": 0.5, "dt50_days": 90.0, "dt50_source": "measured", "formed_from": "M1"},
    ]
    payload.update(overrides)
    return payload


def _ode_tree(k_p, ks, ffs, sources, t_eval):
    """Independent solve: source index -1 = parent, else product index."""

    def rhs(_t, y):
        out = [-k_p * y[0]]
        for j, (ff, k, s) in enumerate(zip(ffs, ks, sources)):
            k_src = k_p if s == -1 else ks[s]
            out.append(ff * k_src * y[s + 1] - k * y[j + 1])
        return out

    return solve_ivp(rhs, (0, t_eval[-1]), [1.0] + [0.0] * len(ffs), t_eval=t_eval, rtol=1e-11, atol=1e-13, method="LSODA").y


def _bateman3(a, b, c, t):
    return a * b * (
        math.exp(-a * t) / ((b - a) * (c - a)) + math.exp(-b * t) / ((a - b) * (c - b)) + math.exp(-c * t) / ((a - c) * (b - c))
    )


def test_second_generation_matches_the_three_member_bateman_formula_by_hand():
    result = run_tp_soil_fate(_chain_payload())
    a, b, c = math.log(2) / 20, math.log(2) / 50, math.log(2) / 90
    for i in (40, 150, 400):
        t = result["times_days"][i]
        expected = 0.6 * 0.5 * _bateman3(a, b, c, t)
        assert result["products"][1]["series_percent_of_applied_molar"][i] == pytest.approx(expected * 100.0, rel=1e-9)


def test_chain_and_branch_match_an_independent_ode_solution():
    payload = _chain_payload()
    payload["products"].append({"name": "M3", "molecular_weight_g_mol": 60.0, "formation_fraction": 0.3, "dt50_days": 25.0, "formed_from": "M1"})
    payload["products"].append({"name": "M4", "molecular_weight_g_mol": 120.0, "formation_fraction": 0.2, "dt50_days": 200.0})
    result = run_tp_soil_fate(payload)
    kp = math.log(2) / 20
    ks = [math.log(2) / d for d in (50.0, 90.0, 25.0, 200.0)]
    y = _ode_tree(kp, ks, [0.6, 0.5, 0.3, 0.2], [-1, 0, 0, -1], np.array(result["times_days"]))
    for j, product in enumerate(result["products"], start=1):
        assert np.allclose(product["series_percent_of_applied_molar"], y[j] * 100.0, rtol=1e-7, atol=1e-9), product["name"]
    assert [p["generation"] for p in result["products"]] == [1, 2, 2, 1]
    assert [p["formed_from"] for p in result["products"]] == ["P", "M1", "M1", "P"]


def test_second_generation_peak_is_later_and_matches_a_numerical_maximiser():
    result = run_tp_soil_fate(_chain_payload())
    m1, m2 = result["products"]
    a, b, c = math.log(2) / 20, math.log(2) / 50, math.log(2) / 90
    best = minimize_scalar(lambda t: -0.3 * _bateman3(a, b, c, t), bounds=(1.0, 399.0), method="bounded", options={"xatol": 1e-9})
    assert m2["peak"]["within_simulation_window"] is True
    assert m2["peak"]["time_days"] == pytest.approx(best.x, rel=1e-5)
    assert m2["peak"]["percent_of_applied_molar"] == pytest.approx(-best.fun * 100.0, rel=1e-9)
    assert m2["peak"]["time_days"] > m1["peak"]["time_days"]


def test_equal_rate_constants_along_a_chain_are_handled():
    payload = _chain_payload()
    payload["products"][0]["dt50_days"] = 20.0
    payload["products"][1]["dt50_days"] = 20.0
    result = run_tp_soil_fate(payload)
    kp = math.log(2) / 20
    y = _ode_tree(kp, [kp, kp], [0.6, 0.5], [-1, 0], np.array(result["times_days"]))
    assert np.allclose(result["products"][1]["series_percent_of_applied_molar"], y[2] * 100.0, rtol=1e-6, atol=1e-9)
    idx = 100  # triple-equal-rate limit: M2/P0 = ff1*ff2*(kp t)^2/2 * e^(-kp t)
    tt = result["times_days"][idx]
    assert result["products"][1]["series_percent_of_applied_molar"][idx] == pytest.approx(0.3 * (kp * tt) ** 2 / 2 * math.exp(-kp * tt) * 100.0, rel=1e-6)


def test_moles_are_conserved_for_random_trees():
    rng = random.Random(24092026)
    for _ in range(30):
        n = rng.randint(2, 6)
        products = []
        for j in range(n):
            source = None if j == 0 else rng.choice([None] + [f"M{i}" for i in range(j)])
            entry = {"name": f"M{j}", "molecular_weight_g_mol": rng.uniform(60, 400), "dt50_days": rng.uniform(2, 300), "dt50_source": "user_estimate"}
            if source:
                entry["formed_from"] = source
            products.append(entry)
        for source in {p.get("formed_from") for p in products}:  # supplied fractions per source sum to <= 1
            kids = [p for p in products if p.get("formed_from") == source]
            for kid in kids:
                kid["formation_fraction"] = rng.uniform(0.05, 1.0 / len(kids))
        result = run_tp_soil_fate(_payload(products=products, duration_days=300.0, n_points=61))
        total = np.array(result["parent"]["series_mg_kg"]) / 200.0
        for prod in result["products"]:
            s = np.array(prod["series_mg_kg"])
            assert (s >= 0).all()
            total = total + s / prod["molecular_weight_g_mol"]
        assert (total <= 2.0 / 200.0 * (1 + 1e-9)).all()


def test_formation_fractions_from_one_source_may_not_exceed_one_but_different_sources_may():
    payload = _chain_payload()
    payload["products"].append({"name": "M3", "molecular_weight_g_mol": 60.0, "formation_fraction": 0.6, "dt50_days": 25.0, "formed_from": "M1"})
    with pytest.raises(TpFateInputError, match="from M1 sum to 1.100"):
        run_tp_soil_fate(payload)  # M2 0.5 + M3 0.6 both from M1
    payload["products"][2]["formation_fraction"] = 0.5
    assert len(run_tp_soil_fate(payload)["products"]) == 3


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p["products"][0].update(formed_from="M2"), "loop"),  # M1 <- M2 <- M1
    (lambda p: p["products"][0].update(formed_from="M1"), "loop"),  # self-reference
    (lambda p: p["products"][1].update(formed_from="nowhere"), "not the parent or a listed product"),
    (lambda p: p["products"][1].update(name="M1"), "unique"),
    (lambda p: p["products"][1].update(name="P"), "unique"),
])
def test_bad_chain_definitions_are_refused(mutation, message):
    payload = _chain_payload()
    mutation(payload)
    with pytest.raises(TpFateInputError, match=message):
        run_tp_soil_fate(payload)


def test_a_defaulted_fraction_skips_only_that_source_sum_check():
    payload = _chain_payload()
    del payload["products"][1]["formation_fraction"]  # M2 defaulted to 1.0 from M1
    payload["products"].append({"name": "M3", "molecular_weight_g_mol": 60.0, "formation_fraction": 0.9, "dt50_days": 25.0, "formed_from": "M1"})
    result = run_tp_soil_fate(payload)
    assert result["products"][1]["formation_fraction"] == 1.0 and any("not additive" in w for w in result["warnings"])


def test_a_frozen_soil_stops_a_chain_and_a_slow_upstream_step_lowers_the_end_product():
    frozen = run_tp_soil_fate(_chain_payload(temperature_c=-5.0))
    assert all(v == 0.0 for p in frozen["products"] for v in p["series_mg_kg"])
    slow_first = _chain_payload()
    slow_first["products"][0]["dt50_days"] = 400.0
    assert (run_tp_soil_fate(slow_first)["products"][1]["peak"]["percent_of_applied_molar"]
            < run_tp_soil_fate(_chain_payload())["products"][1]["peak"]["percent_of_applied_molar"])


def test_a_non_degrading_end_product_accumulates_and_reports_no_interior_peak():
    payload = _chain_payload(duration_days=3000.0)
    payload["products"][1]["dt50_days"] = 1e12
    m2 = run_tp_soil_fate(payload)["products"][1]
    assert m2["peak"]["within_simulation_window"] is False and m2["peak"]["time_days"] is None
    assert m2["series_percent_of_applied_molar"][-1] == pytest.approx(0.6 * 0.5 * 100.0, rel=1e-3)


def test_endpoint_serialises_a_chain_to_json():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.post("/api/tp-soil-fate/run", json=_chain_payload(region="EU"))
    assert response.status_code == 200
    body = response.json()
    assert [p["generation"] for p in body["products"]] == [1, 2]
    assert isinstance(body["products"][1]["peak"]["within_simulation_window"], bool)


# ---------------------------------------------------------------- PEPPER-sourced DT50 --------------------------------

class _FakeResult:
    def __init__(self, dt50=40.0, basis="predicted (PEPPER GPR)", confidence="medium", status="ok"):
        self.status = status
        self.recommended = {"DT50_ref_days": dt50, "logDT50": math.log10(dt50), "logDT50_sd": 0.4, "basis": basis, "confidence": confidence}
        self.prediction = {"DT50_mean_90CI_days": [10.0, 160.0], "DT50_single_soil_90PI_days": [8.0, 200.0]}
        self.applicability = {"max_tanimoto": 0.5}
        self.warnings = ["a warning"]


class _FakePredictor:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def predict(self, chemicals):
        self.calls.append(chemicals)
        return [_FakeResult(**self.kwargs)]


def _pepper_payload(**overrides):
    payload = _payload(**overrides)
    payload["parent"] = {"name": "P", "molecular_weight_g_mol": 200.0, "smiles": "CCO", "dt50_from_pepper": True}
    return payload


def test_pepper_dt50_is_taken_at_20c_labelled_normalised_and_carries_its_uncertainty(monkeypatch):
    fake = _FakePredictor(dt50=40.0)
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: fake)
    result = run_tp_soil_fate(_pepper_payload(region="EU"))
    parent = result["parent"]
    assert fake.calls == [[{"smiles": "CCO", "name": "P"}]]
    assert parent["dt50_source"] == "pepper_prediction" and "MODEL ESTIMATE" in parent["dt50_basis"]
    assert parent["dt50_input_days"] == 40.0 and parent["dt50_input_temperature_c"] == 20.0
    assert parent["dt50_days"] == pytest.approx(40.0 / corrections.temperature_factor(10.0), rel=1e-12)
    assert parent["dt50_uncertainty"]["mean_90CI_days"] == [10.0, 160.0] and parent["dt50_uncertainty"]["confidence"] == "medium"


def test_a_measured_eawag_soil_value_is_labelled_measured(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: _FakePredictor(dt50=12.0, basis="measured (EAWAG-SOIL)", confidence="measured"))
    parent = run_tp_soil_fate(_pepper_payload())["parent"]
    assert parent["dt50_source"] == "measured" and "MODEL ESTIMATE" not in parent["dt50_basis"]


def test_a_supplied_dt50_beats_pepper_and_pepper_is_never_called(monkeypatch):
    def boom():
        raise AssertionError("PEPPER must not be called when a DT50 is supplied")

    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", boom)
    payload = _pepper_payload()
    payload["parent"]["dt50_days"] = 20.0
    payload["parent"]["dt50_source"] = "measured"
    assert run_tp_soil_fate(payload)["parent"]["dt50_source"] == "measured"


def test_pepper_refusals_are_clear_when_closed_missing_or_unusable(monkeypatch):
    from app.services import soil_dt50

    payload = _pepper_payload()
    payload["parent"].pop("smiles")
    with pytest.raises(TpFateInputError, match="SMILES is required"):
        run_tp_soil_fate(payload)
    monkeypatch.setattr(soil_dt50, "commercial_gate", lambda *a, **k: (False, "licence_required"))
    with pytest.raises(TpFateInputError, match="closed here"):
        run_tp_soil_fate(_pepper_payload())
    monkeypatch.setattr(soil_dt50, "commercial_gate", lambda *a, **k: (True, "ok"))
    monkeypatch.setattr(soil_dt50, "availability", lambda: {"available": False, "missing": ["java runtime (PaDEL)"]})
    with pytest.raises(TpFateInputError, match="dependencies are missing"):
        run_tp_soil_fate(_pepper_payload())
    monkeypatch.setattr(soil_dt50, "availability", lambda: {"available": True, "missing": []})
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: _FakePredictor(status="outside_domain"))
    with pytest.raises(TpFateInputError, match="could not predict"):
        run_tp_soil_fate(_pepper_payload())


def test_real_pepper_agrees_with_the_provider_when_it_is_installed():
    from app.services import soil_dt50

    if not soil_dt50.availability()["available"] or not soil_dt50.commercial_gate()[0]:
        pytest.skip("PEPPER provider not available in this environment")
    from app.services.soil_dt50.predictor import get_predictor

    smiles = "NC(=O)N1c2ccccc2C=Cc2ccccc21"
    direct = get_predictor().predict([{"smiles": smiles}])[0].recommended["DT50_ref_days"]
    payload = _payload(region="EU")
    payload["parent"] = {"name": "Carbamazepine", "smiles": smiles, "dt50_from_pepper": True}
    result = run_tp_soil_fate(payload)["parent"]
    assert result["dt50_input_days"] == pytest.approx(direct)
    assert result["dt50_days"] == pytest.approx(direct / corrections.temperature_factor(10.0), rel=1e-12)
    assert result["molecular_weight_g_mol"] == pytest.approx(236.27, abs=0.02)


# ---------------------------------------------------------------- uncertainty band ---------------------------------------

def _band_payload(**overrides):
    payload = _payload(duration_days=365.0, n_points=121)
    payload["parent"] = {"name": "P", "molecular_weight_g_mol": 200.0, "dt50_days": 50.0, "dt50_source": "measured", "dt50_range_days": [15.0, 170.0]}
    payload["products"] = [
        {"name": "M1", "molecular_weight_g_mol": 100.0, "formation_fraction": 0.6, "dt50_days": 40.0, "dt50_source": "measured", "dt50_range_days": [10.0, 150.0]},
        {"name": "M2", "molecular_weight_g_mol": 80.0, "formation_fraction": 0.5, "dt50_days": 90.0, "dt50_source": "measured", "formed_from": "M1"},
    ]
    payload.update(overrides)
    return payload


Z90 = 1.6448536269514722


def test_a_user_range_becomes_a_log10_sd_and_the_parent_band_matches_an_independent_calculation():
    payload = _band_payload(uncertainty={"n_samples": 500, "seed": 7})
    result = run_tp_soil_fate(payload)
    band = result["uncertainty_band"]
    sd = (math.log10(170.0) - math.log10(15.0)) / (2 * Z90)
    assert band["available"] and band["sampled"][0] == {"name": "P", "kind": "dt50", "log10_sd": pytest.approx(sd), "source": "user_range"}
    # The parent is the first sampled substance, so its draws are the generator's first 500 standard normals.
    z = np.random.default_rng(7).standard_normal(500)
    dt50 = 50.0 * 10.0 ** (sd * z)  # target = DT50 temperature (20 C), so no temperature scaling
    times = np.array(band["times_days"])
    expected = np.exp(-np.log(2) * times[None, :] / dt50[:, None]) * 100.0
    for q, key in ((5, "p05"), (50, "p50"), (95, "p95")):
        assert np.allclose(band["parent"]["percent_of_applied_molar"][key], np.percentile(expected, q, axis=0), rtol=1e-9, atol=1e-9)


def test_the_median_line_follows_the_central_curve_and_lines_are_ordered():
    band = run_tp_soil_fate(_band_payload(uncertainty={"n_samples": 2000}))["uncertainty_band"]
    central = run_tp_soil_fate(_band_payload(uncertainty=False, duration_days=365.0))["parent"]["series_mg_kg"]
    for entry in (band["parent"], *band["products"]):
        p05, p50, p95 = (np.array(entry["percent_of_applied_molar"][k]) for k in ("p05", "p50", "p95"))
        assert (p05 <= p50 + 1e-12).all() and (p50 <= p95 + 1e-12).all()
    t = band["times_days"][40]
    assert band["parent"]["mg_kg"]["p50"][40] == pytest.approx(2.0 * math.exp(-math.log(2) * t / 50.0), rel=0.05)
    assert central[0] == pytest.approx(2.0)


def test_the_band_is_reproducible_for_a_seed_and_changes_with_another():
    a = run_tp_soil_fate(_band_payload(uncertainty={"seed": 1}))["uncertainty_band"]
    b = run_tp_soil_fate(_band_payload(uncertainty={"seed": 1}))["uncertainty_band"]
    c = run_tp_soil_fate(_band_payload(uncertainty={"seed": 2}))["uncertainty_band"]
    assert a["products"][0]["peak_percent_of_applied_molar"] == b["products"][0]["peak_percent_of_applied_molar"]
    assert a["products"][0]["peak_percent_of_applied_molar"] != c["products"][0]["peak_percent_of_applied_molar"]


def test_substances_without_an_uncertainty_are_named_as_fixed_and_no_uncertainty_means_no_band():
    band = run_tp_soil_fate(_band_payload())["uncertainty_band"]
    assert [s["name"] for s in band["sampled"]] == ["P", "M1"] and band["fixed"] == ["M2"]
    assert any("formation fractions" in note.lower() for note in band["notes"])
    none = run_tp_soil_fate(_payload())["uncertainty_band"]
    assert none["available"] is False and "no DT50 or formation fraction carries an uncertainty" in none["reason"]
    assert run_tp_soil_fate(_band_payload(uncertainty=False))["uncertainty_band"] is None


def test_probability_of_a_major_transformation_product_is_zero_or_one_when_the_answer_is_clear():
    high = _band_payload()
    high["products"][0]["formation_fraction"] = 1.0
    high["products"][0]["dt50_range_days"] = [35.0, 46.0]
    high["parent"]["dt50_range_days"] = [45.0, 56.0]
    assert run_tp_soil_fate(high)["uncertainty_band"]["products"][0]["probability_major_transformation_product"] == 1.0
    low = _band_payload()
    low["products"][0]["formation_fraction"] = 0.02
    assert run_tp_soil_fate(low)["uncertainty_band"]["products"][0]["probability_major_transformation_product"] == 0.0


def test_the_driver_ranking_finds_the_only_uncertain_substance_and_its_direction():
    payload = _band_payload()
    payload["products"][0].pop("dt50_range_days")  # only the parent DT50 is uncertain
    band = run_tp_soil_fate(payload)["uncertainty_band"]
    drivers = band["products"][0]["drivers"]
    assert [d["substance"] for d in drivers] == ["P"]
    assert drivers[0]["spearman_rho"] < -0.95  # a slower parent means a lower, later first-generation peak


def test_the_single_soil_basis_is_wider_than_the_mean_basis_for_pepper(monkeypatch):
    fake = _FakePredictor(dt50=40.0)
    original = _FakeResult.__init__

    def with_sigma(self, **kwargs):
        original(self, **kwargs)
        self.prediction["sigma_between_soils_used"] = 0.3

    monkeypatch.setattr(_FakeResult, "__init__", with_sigma)
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: fake)
    payload = _pepper_payload(uncertainty={"basis": "single_soil"})
    single = run_tp_soil_fate(payload)
    assert single["parent"]["dt50_uncertainty"]["log10_sd_mean"] == 0.4
    assert single["parent"]["dt50_uncertainty"]["log10_sd_single_soil"] == pytest.approx(math.hypot(0.4, 0.3))
    mean = run_tp_soil_fate(_pepper_payload(uncertainty={"basis": "mean"}))
    width = lambda r: r["uncertainty_band"]["products"][0]["peak_percent_of_applied_molar"]["p95"] - r["uncertainty_band"]["products"][0]["peak_percent_of_applied_molar"]["p05"]
    assert single["uncertainty_band"]["sampled"][0]["log10_sd"] > mean["uncertainty_band"]["sampled"][0]["log10_sd"]
    assert width(single) > width(mean)


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p["parent"].update(dt50_range_days=[60.0, 170.0]), "low < DT50 < high"),
    (lambda p: p["parent"].update(dt50_range_days=[15.0]), r"\[low, high\]"),
    (lambda p: p["parent"].update(dt50_range_days=[-1.0, 170.0]), "must be a positive"),
    (lambda p: p.update(uncertainty={"basis": "guess"}), "basis"),
    (lambda p: p.update(uncertainty={"n_samples": 5}), "n_samples"),
    (lambda p: p.update(uncertainty="yes"), "uncertainty must be"),
])
def test_bad_uncertainty_inputs_are_refused(mutation, message):
    payload = _band_payload()
    mutation(payload)
    with pytest.raises(TpFateInputError, match=message):
        run_tp_soil_fate(payload)


def test_a_frozen_soil_has_no_band_and_the_endpoint_serialises_the_band():
    assert run_tp_soil_fate(_band_payload(temperature_c=-5.0))["uncertainty_band"]["available"] is False
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.post("/api/tp-soil-fate/run", json=_band_payload(region="EU"))
    assert response.status_code == 200
    band = response.json()["uncertainty_band"]
    assert band["available"] is True and len(band["times_days"]) == 121 and len(band["products"]) == 2


# ---------------------------------------------------------------- formation-fraction uncertainty --------------------------

def _logit(x):
    return math.log(x / (1 - x))


def _ff_payload(**overrides):
    payload = _payload(duration_days=365.0, n_points=121)
    payload["products"][0].update(formation_fraction=0.4, formation_fraction_range=[0.15, 0.75])
    payload.update(overrides)
    return payload


def test_a_formation_fraction_range_is_drawn_logit_normally_and_matches_an_independent_calculation():
    result = run_tp_soil_fate(_ff_payload(uncertainty={"n_samples": 400, "seed": 11}))
    band = result["uncertainty_band"]
    sd = (_logit(0.75) - _logit(0.15)) / (2 * Z90)
    assert band["available"] and band["sampled"] == [{"name": "M1 formation fraction", "kind": "formation_fraction", "logit_sd": pytest.approx(sd), "source": "user_range", "range": [0.15, 0.75]}]
    z = np.random.default_rng(11).standard_normal(400)  # no DT50 is sampled, so these are the first draws
    ff = 1.0 / (1.0 + np.exp(-(_logit(0.4) + sd * z)))
    t = np.array(band["times_days"])
    kp, km = math.log(2) / 20.0, math.log(2) / 50.0
    unit = kp * (np.exp(-kp * t) - np.exp(-km * t)) / (km - kp)  # M1 per mole of parent, per unit formation fraction
    expected = ff[:, None] * unit[None, :] * 100.0
    for q, key in ((5, "p05"), (50, "p50"), (95, "p95")):
        assert np.allclose(band["products"][0]["percent_of_applied_molar"][key], np.percentile(expected, q, axis=0), rtol=1e-9, atol=1e-12)


def test_the_formation_fraction_is_the_driver_of_its_own_peak():
    band = run_tp_soil_fate(_ff_payload())["uncertainty_band"]
    top = band["products"][0]["drivers"][0]
    assert top["kind"] == "formation_fraction" and top["variable"] == "M1 formation fraction" and top["spearman_rho"] > 0.99
    assert band["products"][0]["peak_percent_of_applied_molar"]["p05"] < band["products"][0]["peak_percent_of_applied_molar"]["p95"]


def test_adding_a_fraction_range_does_not_move_the_dt50_draws():
    with_ff = _band_payload()
    with_ff["products"][0].update(formation_fraction=0.6, formation_fraction_range=[0.3, 0.85])
    a = run_tp_soil_fate(_band_payload())["uncertainty_band"]["parent"]["percent_of_applied_molar"]
    b = run_tp_soil_fate(with_ff)["uncertainty_band"]["parent"]["percent_of_applied_molar"]
    assert a == b  # DT50 draws come first, so the parent (a DT50-only quantity) is untouched


def test_sibling_fractions_are_scaled_down_together_when_a_draw_would_exceed_one():
    payload = _payload(duration_days=365.0)
    payload["products"] = [
        {"name": "A", "molecular_weight_g_mol": 100.0, "formation_fraction": 0.6, "formation_fraction_range": [0.4, 0.9], "dt50_days": 30.0},
        {"name": "B", "molecular_weight_g_mol": 90.0, "formation_fraction": 0.35, "formation_fraction_range": [0.2, 0.6], "dt50_days": 30.0},
    ]
    band = run_tp_soil_fate(payload)["uncertainty_band"]
    assert band["formation_fraction_renormalised_draws"] > 0
    defaulted = _payload(duration_days=365.0)
    defaulted["products"] = [
        {"name": "A", "molecular_weight_g_mol": 100.0, "formation_fraction": 0.6, "formation_fraction_range": [0.4, 0.9], "dt50_days": 30.0},
        {"name": "B", "molecular_weight_g_mol": 90.0, "dt50_days": 30.0},  # defaulted worst case 1.0: never rescaled
    ]
    assert run_tp_soil_fate(defaulted)["uncertainty_band"]["formation_fraction_renormalised_draws"] == 0


def test_without_a_fraction_range_the_notes_say_the_fractions_are_fixed_and_with_one_they_do_not():
    assert any("No formation fraction range was given" in n for n in run_tp_soil_fate(_band_payload())["uncertainty_band"]["notes"])
    assert not any("No formation fraction range was given" in n for n in run_tp_soil_fate(_ff_payload())["uncertainty_band"]["notes"])


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p["products"][0].update(formation_fraction_range=[0.5, 0.75]), "0 < low < formation_fraction < high < 1"),  # median 0.4 below low
    (lambda p: p["products"][0].update(formation_fraction_range=[0.15, 1.0]), "0 < low < formation_fraction < high < 1"),
    (lambda p: p["products"][0].update(formation_fraction_range=[0.0, 0.75]), "0 < low < formation_fraction < high < 1"),
    (lambda p: p["products"][0].update(formation_fraction_range=[0.15]), r"\[low, high\]"),
    (lambda p: p["products"][0].update(formation_fraction_range=["a", "b"]), "must be numbers"),
    (lambda p: p["products"][0].pop("formation_fraction"), "needs a supplied formation_fraction"),
])
def test_bad_formation_fraction_ranges_are_refused(mutation, message):
    payload = _ff_payload()
    mutation(payload)
    with pytest.raises(TpFateInputError, match=message):
        run_tp_soil_fate(payload)


def test_a_major_flag_that_rests_on_the_worst_case_default_says_so():
    payload = _payload()
    del payload["products"][0]["formation_fraction"]
    flagged = run_tp_soil_fate(payload)["products"][0]["major_transformation_product"]
    assert flagged["flag"] is True and flagged["formation_fraction_defaulted"] is True
    supplied = run_tp_soil_fate(_payload())["products"][0]["major_transformation_product"]
    assert supplied["formation_fraction_defaulted"] is False


def test_the_pathway_source_of_each_product_is_kept_and_trimmed():
    payload = _payload()
    payload["products"][0]["pathway_source"] = "  QSAR Toolbox 4.9 (microbial simulator)  "
    payload["products"].append({"name": "M2", "molecular_weight_g_mol": 90.0, "formation_fraction": 0.2, "dt50_days": 30.0, "pathway_source": "x" * 300})
    payload["products"].append({"name": "M3", "molecular_weight_g_mol": 90.0, "formation_fraction": 0.1, "dt50_days": 30.0})
    products = run_tp_soil_fate(payload)["products"]
    assert products[0]["pathway_source"] == "QSAR Toolbox 4.9 (microbial simulator)"
    assert len(products[1]["pathway_source"]) == 120 and products[2]["pathway_source"] is None


# ---------------------------------------------------------------- best-available DT50 ladder (BIOWIN last) ----------------

def _auto_payload(**parent_extra):
    payload = _payload(region="EU")
    payload["parent"] = {"name": "P", "molecular_weight_g_mol": 200.0, "dt50_auto": True, **parent_extra}
    return payload


def test_auto_prefers_a_supplied_dt50_over_everything_and_never_calls_pepper(monkeypatch):
    def boom():
        raise AssertionError("PEPPER must not be called when a DT50 is supplied")

    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", boom)
    payload = _auto_payload(smiles="CCO", biowin4_score=3.0, dt50_days=12.0, dt50_source="measured")
    parent = run_tp_soil_fate(payload)["parent"]
    assert parent["dt50_source"] == "measured" and parent["dt50_input_days"] == 12.0


def test_auto_uses_pepper_before_biowin_even_when_a_biowin_score_is_given(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: _FakePredictor(dt50=40.0))
    parent = run_tp_soil_fate(_auto_payload(smiles="CCO", biowin4_score=3.0))["parent"]
    assert parent["dt50_source"] == "pepper_prediction" and parent["dt50_input_days"] == 40.0 and parent["dt50_ladder"] == []


def test_auto_falls_back_to_biowin_only_last_and_records_why(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: _FakePredictor(status="outside_domain"))
    parent = run_tp_soil_fate(_auto_payload(smiles="CCO", biowin4_score=3.0))["parent"]
    assert parent["dt50_source"] == "biowin_screen" and parent["dt50_input_days"] == pytest.approx(500.0 / 24.0)
    assert len(parent["dt50_ladder"]) == 1 and "PEPPER not used" in parent["dt50_ladder"][0]
    no_smiles = run_tp_soil_fate(_auto_payload(biowin4_score=3.0))["parent"]
    assert no_smiles["dt50_source"] == "biowin_screen" and no_smiles["dt50_ladder"] == ["PEPPER needs a SMILES"]


def test_auto_with_nothing_available_says_what_was_tried(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: _FakePredictor(status="failed"))
    with pytest.raises(TpFateInputError, match="no DT50 could be found automatically.*PEPPER not used"):
        run_tp_soil_fate(_auto_payload(smiles="CCO"))
    with pytest.raises(TpFateInputError, match="no DT50 could be found automatically.*needs a SMILES"):
        run_tp_soil_fate(_auto_payload())


def test_explicit_pepper_still_fails_loudly_rather_than_silently_using_biowin(monkeypatch):
    monkeypatch.setattr("app.services.soil_dt50.predictor.get_predictor", lambda: _FakePredictor(status="failed"))
    payload = _payload()
    payload["parent"] = {"name": "P", "molecular_weight_g_mol": 200.0, "smiles": "CCO", "dt50_from_pepper": True, "biowin4_score": 3.0}
    with pytest.raises(TpFateInputError, match="could not predict"):
        run_tp_soil_fate(payload)
