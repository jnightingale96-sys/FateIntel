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
    payload["products"][0]["biowin4_score"] = 3.0  # 100 h at 25 C = 100/24 d
    product = run_tp_soil_fate(payload)["products"][0]
    assert product["dt50_source"] == "biowin_screen" and "unsourced" in product["dt50_basis"]
    assert product["dt50_days"] == pytest.approx(100.0 / 24.0 * corrections.temperature_factor(25.0), rel=1e-12)


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
