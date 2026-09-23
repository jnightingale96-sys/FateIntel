"""Independent-recalculation and randomised-invariant checks on the native calculation modules.

Every check compares the app against a SEPARATELY written hand formula, a closed form, a different numerical
method (scipy ODE integration / root finding) or a published literature value -- never the module against itself.
Random inputs use fixed seeds so failures are reproducible. No network, no database.

Origin: the "check the science" pass of the 90-day validation plan (2026-09-23). The gold-case doses and
excretion/removal fractions below are ILLUSTRATIVE test inputs (typical labelled maxima recalled from memory, NOT
verified against a current SmPC, and removal fractions that are not measured plant data); what is being verified is
the calculation chain, not the regulatory conclusion.
"""

from __future__ import annotations

import hashlib
import json
import math
import random

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from app.reach.pnec import derive_pnec
from app.services import degradation_kinetics as dk
from app.services import equilibrium_partitioning as ep
from app.services import sorption as so
from app.services.biosolids import run_biosolids_land_application
from app.services.emission import run_pharmaceutical_emission
from app.services.multimedia_fate import run_multimedia_fate_screen
from app.services.plant_uptake import briggs_tscf, run_plant_uptake_screen
from app.services.river_network import run_catchment_river_network
from app.services.wwtp import WORKBOOK_9BOX_CARBAMAZEPINE_FRACTIONS, run_activity_simpletreat


def _ema_payload(name: str, mw: float, dose_mg: float, mode: str = "ema_phase_i") -> dict:
    return {
        "scenario_name": "invariant", "emission_mode": mode, "parent_name": name,
        "parent_molecular_weight_g_mol": mw, "administration_route": "oral",
        "spc_source_type": "official_regulatory", "spc_title": "illustrative", "spc_identifier": "x",
        "consumption_source_title": "n/a", "therapeutic_class_ddd_per_1000_day": 0.0,
        "dose_per_administration": 1.0, "dose_unit": "mg", "administrations_per_day": 1.0,
        "daily_active_amount": 0.0, "daily_active_unit": "mg", "emitting_days_per_year": 365,
        "maximum_daily_dose_mg": dose_mg, "ema_fpen_mode": "default", "market_penetration_fraction": 0.01,
        "regulatory_stp_capacity_inhabitants": 10000, "dilution_factor": 10.0, "population": 100000,
        "wastewater_l_person_day": 200.0, "direct_to_sewer_fraction": 0.0, "systemic_fraction": 1.0,
        "parent_urine_fraction": 0.0, "parent_faeces_fraction": 0.0, "metabolites": [],
    }


# ---------------------------------------------------------------------------
# Pharmaceutical emission (EMA Phase I / molar accounting)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name, mw, dose", [("Carbamazepine", 236.27, 1200.0), ("Diclofenac", 296.15, 150.0), ("Ibuprofen", 206.28, 2400.0)])
def test_ema_phase_i_matches_the_published_equation_by_hand(name, mw, dose):
    result = run_pharmaceutical_emission(_ema_payload(name, mw, dose))
    hand_ug_l = dose * 0.01 / (200.0 * 10.0) * 1000.0  # PECsw = DOSEai x Fpen / (WASTEWinhab x DILUTION)
    assert result["regulatory"]["pec_surface_water_ug_l"] == pytest.approx(hand_ug_l, rel=1e-12)
    assert result["regulatory"]["phase_ii_triggered_by_pec"] is (hand_ug_l >= 0.01)
    assert result["administered"]["moles_day"] * mw == pytest.approx(result["administered"]["mass_g_day"], rel=1e-12)


def test_ema_phase_i_random_inputs_match_the_hand_formula_including_non_default_stp_capacity():
    rng = random.Random(20260923)
    for _ in range(150):
        dose = 10 ** rng.uniform(-1, 4)
        fpen = rng.uniform(0.0005, 0.2)
        wastewater = rng.uniform(80, 400)
        dilution = rng.uniform(2, 100)
        payload = _ema_payload("X", rng.uniform(100, 700), dose)
        payload.update({
            "ema_fpen_mode": "user", "market_penetration_fraction": fpen, "wastewater_l_person_day": wastewater,
            "dilution_factor": dilution, "regulatory_stp_capacity_inhabitants": rng.choice([500, 10000, 50000]),
        })
        got = run_pharmaceutical_emission(payload)["regulatory"]["pec_surface_water_ug_l"]
        assert got == pytest.approx(dose * fpen / (wastewater * dilution) * 1000.0, rel=1e-9)


def test_emission_molar_accounting_never_creates_mass_and_matches_the_hand_split():
    rng = random.Random(11)
    for _ in range(150):
        direct = rng.uniform(0, 0.5)
        systemic = rng.uniform(0, 1 - direct)
        urine, faeces = rng.uniform(0, 0.6), rng.uniform(0, 0.4)
        remaining = 1 - urine - faeces
        metabolites = [{"name": "M1", "molecular_weight_g_mol": rng.uniform(150, 400), "molar_fraction": rng.uniform(0, remaining)}] if remaining > 0.05 and rng.random() < 0.7 else []
        payload = _ema_payload("X", rng.uniform(100, 700), 100.0, mode="direct_daily_use")
        payload.update({
            "daily_active_amount": 10 ** rng.uniform(-3, 2), "daily_active_unit": "g", "direct_to_sewer_fraction": direct,
            "systemic_fraction": systemic, "parent_urine_fraction": urine, "parent_faeces_fraction": faeces, "metabolites": metabolites,
        })
        result = run_pharmaceutical_emission(payload)
        moles_in = result["administered"]["moles_day"]
        parent_out = result["species"][0]["moles_day"]
        expected_parent = moles_in * (direct + systemic * (urine + faeces))
        expected_metabolites = sum(moles_in * systemic * m["molar_fraction"] for m in metabolites)
        total_out = parent_out + sum(s["moles_day"] for s in result["species"][1:])
        assert parent_out == pytest.approx(expected_parent, rel=1e-9, abs=1e-18)
        assert total_out == pytest.approx(expected_parent + expected_metabolites, rel=1e-9, abs=1e-18)
        assert total_out <= moles_in * (1 + 1e-9)


# ---------------------------------------------------------------------------
# Gold-standard chain: emission -> WWTP -> PEC -> RQ, vs an independent hand calculation, and reproducibility
# ---------------------------------------------------------------------------

_GOLD_CASES = [
    # name, MW, illustrative max daily dose mg, urinary parent, faecal parent, WWTP fractions (None = workbook 9-box preset), illustrative PNEC ug/L
    ("Carbamazepine", 236.27, 1200.0, 0.02, 0.28, None, 0.5),
    ("Diclofenac", 296.15, 150.0, 0.05, 0.0, {"air": 0.0, "bio": 0.35, "prim": 0.04, "sec": 0.03}, 0.05),
    ("Ibuprofen", 206.28, 2400.0, 0.01, 0.0, {"air": 0.0, "bio": 0.90, "prim": 0.02, "sec": 0.02}, 1.0),
]


def _run_gold_case(case):
    name, mw, dose, urine, faeces, fractions, pnec = case
    payload = _ema_payload(name, mw, dose, mode="ema_phase_ii")
    payload.update({"parent_urine_fraction": urine, "parent_faeces_fraction": faeces})
    emission = run_pharmaceutical_emission(payload)
    wwtp = {
        "influent_mass_kg_day": emission["influent"]["parent_mass_kg_day"], "wastewater_flow_m3_day": emission["wastewater_flow_m3_day"],
        "post_wwtp_biodegradation_fraction": 0.0, "receiving_water_dilution_factor": 10.0, "sludge_to_soil_fraction": 0.5,
        "mixed_soil_mass_kg": 1e6, "emitting_days_per_year": 365, "aquatic_pnec_ug_l": pnec, "soil_pnec_ug_kg": None,
        "species_key": "parent", "species_name": name, "chemical_name": name,
    }
    if fractions is None:
        wwtp["model_mode"] = "supplied_workbook_9box_preset"
    else:
        wwtp.update(model_mode="custom_screening", biodegradation_fraction=fractions["bio"], primary_sludge_fraction=fractions["prim"],
                    secondary_sludge_fraction=fractions["sec"], volatilisation_fraction=fractions["air"])
    return emission, run_activity_simpletreat(wwtp)


@pytest.mark.parametrize("case", _GOLD_CASES, ids=[c[0] for c in _GOLD_CASES])
def test_gold_case_chain_matches_an_independent_hand_calculation(case):
    name, mw, dose, urine, faeces, fractions, pnec = case
    emission, wwtp = _run_gold_case(case)
    effluent_fraction = WORKBOOK_9BOX_CARBAMAZEPINE_FRACTIONS["effluent"] if fractions is None else 1 - fractions["bio"] - fractions["prim"] - fractions["sec"] - fractions["air"]
    influent_g_day = dose * 0.01 * 10000 / 1000 * (urine + faeces)  # Phase II: excretion applied before treatment
    c_influent = influent_g_day * 1e6 / (10000 * 200)  # ug/L
    c_effluent = c_influent * effluent_fraction
    pec = c_effluent / 10.0
    assert emission["influent"]["parent_concentration_ug_l"] == pytest.approx(c_influent, rel=1e-12)
    assert wwtp["effluent_concentration_ug_l"] == pytest.approx(c_effluent, rel=1e-9)
    assert wwtp["surface_water_pec_ug_l"] == pytest.approx(pec, rel=1e-9)
    assert wwtp["aquatic_rq"] == pytest.approx(pec / pnec, rel=1e-9)
    assert sum(wwtp["mass_flows_kg_day"].values()) == pytest.approx(emission["influent"]["parent_mass_kg_day"], rel=1e-9)


def test_gold_cases_are_bit_for_bit_reproducible_across_runs():
    def digest():
        out = []
        for case in _GOLD_CASES:
            emission, wwtp = _run_gold_case(case)
            out.append(hashlib.sha256(json.dumps([emission["influent"], wwtp["surface_water_pec_ug_l"], wwtp["aquatic_rq"]], sort_keys=True, default=str).encode()).hexdigest())
        return out

    assert digest() == digest()


def test_the_carbamazepine_only_wwtp_preset_refuses_another_substance():
    _emission, _ = _run_gold_case(_GOLD_CASES[0])
    with pytest.raises(ValueError, match="Carbamazepine"):
        run_activity_simpletreat({
            "influent_mass_kg_day": 1.0, "wastewater_flow_m3_day": 1000.0, "model_mode": "supplied_workbook_9box_preset",
            "post_wwtp_biodegradation_fraction": 0.0, "receiving_water_dilution_factor": 10.0, "sludge_to_soil_fraction": 0.5,
            "mixed_soil_mass_kg": 1e6, "emitting_days_per_year": 365, "species_key": "parent", "species_name": "Diclofenac", "chemical_name": "Diclofenac",
        })


# ---------------------------------------------------------------------------
# Multimedia fate: independent linear solve, long-time ODE integration, linearity, closure
# ---------------------------------------------------------------------------


def _random_multimedia_system(rng: random.Random, n: int) -> dict:
    keys = ["air", "freshwater", "soil", "sediment"][:n]
    compartments = []
    for key in keys:
        item = {"key": key, "volume_m3": 10 ** rng.uniform(3, 9)}
        if key in ("soil", "sediment"):
            item["bulk_density_kg_m3"] = rng.uniform(800, 2000)
        if rng.random() < 0.7:
            item["half_life_days"] = 10 ** rng.uniform(-1, 3)
        if rng.random() < 0.5:
            item["advective_loss_per_day"] = 10 ** rng.uniform(-4, 0)
        compartments.append(item)
    compartments[0]["half_life_days"] = compartments[0].get("half_life_days", 30.0)
    transfers = [{"source": a, "target": b, "rate_per_day": 10 ** rng.uniform(-4, 0)} for a in keys for b in keys if a != b and rng.random() < 0.5]
    emissions = {k: 10 ** rng.uniform(-2, 3) for k in keys if rng.random() < 0.6} or {keys[0]: 1.0}
    return {"compartments": compartments, "transfers": transfers, "emissions_kg_day": emissions}


def _rate_matrix(system: dict):
    keys = [c["key"] for c in system["compartments"]]
    index = {k: i for i, k in enumerate(keys)}
    matrix = np.zeros((len(keys), len(keys)))
    for c in system["compartments"]:
        half_life = c.get("half_life_days")
        matrix[index[c["key"]], index[c["key"]]] += (math.log(2) / half_life if half_life else 0.0) + c.get("advective_loss_per_day", 0.0)
    for t in system["transfers"]:
        matrix[index[t["source"]], index[t["source"]]] += t["rate_per_day"]
        matrix[index[t["target"]], index[t["source"]]] -= t["rate_per_day"]
    emissions = np.zeros(len(keys))
    for k, v in system["emissions_kg_day"].items():
        emissions[index[k]] = v
    return keys, matrix, emissions


def test_multimedia_fate_random_systems_match_independent_solvers_and_conserve_mass():
    rng = random.Random(3)
    solved = 0
    for i in range(150):
        system = _random_multimedia_system(rng, rng.choice([2, 3, 4]))
        try:
            result = run_multimedia_fate_screen(system)
        except ValueError:
            continue  # legitimately refused (singular / non-physical) -- refusing is correct behaviour
        solved += 1
        keys, matrix, emissions = _rate_matrix(system)
        masses = np.array([next(c["mass_kg"] for c in result["compartments"] if c["key"] == k) for k in keys])
        assert abs(result["mass_balance"]["relative_closure_error"]) < 1e-8
        assert np.allclose(masses, np.linalg.solve(matrix, emissions), rtol=1e-6, atol=1e-9)
        if np.max(np.abs(np.diag(matrix))) < 2 and i % 8 == 0:  # time-integrate to steady state (different method)
            horizon = 40 / max(np.min(np.linalg.eigvals(matrix).real), 1e-6)
            integrated = solve_ivp(lambda t, m: emissions - matrix @ m, [0, horizon], np.zeros(len(keys)), method="LSODA", rtol=1e-9, atol=1e-12)
            assert np.allclose(integrated.y[:, -1], masses, rtol=1e-3, atol=1e-6)
        doubled = dict(system, emissions_kg_day={k: 2 * v for k, v in system["emissions_kg_day"].items()})
        masses2 = np.array([next(c["mass_kg"] for c in run_multimedia_fate_screen(doubled)["compartments"] if c["key"] == k) for k in keys])
        assert np.allclose(masses2, 2 * masses, rtol=1e-9)
    assert solved > 80  # the generator must actually exercise the solver


# ---------------------------------------------------------------------------
# Degradation kinetics: closed forms, root-finding cross-check, parameter recovery
# ---------------------------------------------------------------------------


def test_sfo_and_fomc_dtx_match_their_closed_forms():
    rng = random.Random(5)
    for _ in range(100):
        k = 10 ** rng.uniform(-3, 0.5)
        assert dk.endpoint_dtx("SFO", {"m0": 100.0, "k": k}, 100.0, 50) == pytest.approx(math.log(2) / k, rel=1e-9)
        assert dk.endpoint_dtx("SFO", {"m0": 100.0, "k": k}, 100.0, 90) == pytest.approx(math.log(10) / k, rel=1e-9)
        alpha, beta, x = rng.uniform(0.3, 3), 10 ** rng.uniform(-1, 3), rng.uniform(10, 95)
        closed = beta * ((1 / (1 - x / 100)) ** (1 / alpha) - 1)  # Gustafson-Holden
        assert dk.endpoint_dtx("FOMC", {"m0": 100.0, "alpha": alpha, "beta": beta}, 100.0, x) == pytest.approx(closed, rel=1e-7)


def test_dfop_dt50_matches_an_independent_root_finder():
    rng = random.Random(6)
    for _ in range(60):
        g, k1 = rng.uniform(0.2, 0.9), 10 ** rng.uniform(-1, 0.5)
        k2 = k1 * 10 ** rng.uniform(-3, -0.5)
        reference = brentq(lambda t: 100 * (g * math.exp(-k1 * t) + (1 - g) * math.exp(-k2 * t)) - 50, 0, 1e6)
        assert dk.endpoint_dtx("DFOP", {"m0": 100.0, "g": g, "k1": k1, "k2": k2}, 100.0, 50) == pytest.approx(reference, rel=1e-8)


def test_sfo_and_fomc_fits_recover_the_true_dt50_from_noisy_synthetic_data():
    rng = random.Random(9)
    t = np.array([0, 1, 3, 7, 14, 21, 28, 42, 56, 90, 120], float)
    hits = {"SFO": 0, "FOMC": 0}
    trials = 25
    for trial in range(trials):
        noise = np.random.default_rng(trial)
        k = 10 ** rng.uniform(-2.3, -0.7)
        sfo_truth = (100.0, k)
        alpha, beta = rng.uniform(0.5, 1.5), 10 ** rng.uniform(0.3, 1.7)
        fomc_truth = (100.0, alpha, beta)
        for model, truth, fn in (("SFO", sfo_truth, dk.sfo_model), ("FOMC", fomc_truth, dk.fomc_model)):
            observed = fn(t, *truth) * (1 + noise.normal(0, 0.01, t.size))  # 1% multiplicative noise
            fit = dk.fit_kinetic_model(model, t, observed)
            names = dk._PARAM_ORDER[model]
            true_dt50 = dk.endpoint_dtx(model, dict(zip(names, truth)), truth[0], 50)
            est_dt50 = dk.endpoint_dtx(model, fit["parameters"], fit["parameters"]["m0"], 50)
            hits[model] += abs(est_dt50 - true_dt50) / true_dt50 < 0.10
    assert hits["SFO"] == trials and hits["FOMC"] >= trials - 1


# ---------------------------------------------------------------------------
# Sorption: published coefficients, limiting behaviour, literature McGowan volumes
# ---------------------------------------------------------------------------


def test_franco_trapp_recovers_the_published_regressions_far_from_the_pka():
    rng = random.Random(4)
    for _ in range(100):
        log_kow, pka, foc = rng.uniform(-1, 6), rng.uniform(4.5, 9.5), rng.uniform(0.001, 0.2)
        for cls, neutral_ph, ion_ph, neutral_line, ion_line in (
            ("acid", pka - 4, pka + 4, 0.54 * log_kow + 1.11, 0.11 * log_kow + 1.54),  # Franco & Trapp (2008)
            ("base", pka + 4, pka - 4, 0.42 * log_kow + 1.34, 0.47 * log_kow + 1.95),
        ):
            neutral = so.franco_trapp(cls, log_kow, pka, neutral_ph, 0.0, foc)
            ion = so.franco_trapp(cls, log_kow, pka, ion_ph, 0.0, foc)
            assert neutral["koc_l_kg"] == pytest.approx(10 ** neutral_line, rel=2e-3)
            assert ion["koc_l_kg"] == pytest.approx(10 ** ion_line, rel=0.05)
            assert neutral["kd_l_kg"] == pytest.approx(neutral["koc_l_kg"] * foc, rel=1e-12)


def test_franco_trapp_acid_sorption_falls_with_ph_when_the_anion_sorbs_less():
    rng = random.Random(8)
    for _ in range(100):
        log_kow, pka = rng.uniform(1.5, 6), rng.uniform(4.5, 9.5)
        kocs = [so.franco_trapp("acid", log_kow, pka, ph, 0.01, 0.02)["koc_l_kg"] for ph in np.linspace(pka - 4, pka + 4, 17)]
        assert all(kocs[i] >= kocs[i + 1] * (1 - 1e-9) for i in range(len(kocs) - 1))


def test_published_model_coefficients_and_literature_mcgowan_volumes():
    assert so.li_neutral(3.0, 0.02)["log_kd"] == pytest.approx(0.779 * 3 + 0.211 * 2 - 1.729, rel=1e-12)
    assert so.ecetoc_base_workbook(4.0, 0.02)["log_koc"] == pytest.approx(0.31 * 4 + 2.78, rel=1e-12)
    # Abraham & McGowan (1987) characteristic volumes, cm3 mol-1 / 100
    assert so.mcgowan_volume_from_counts({"C": 6, "H": 6}, ring_count=1)["mcgowan_volume_vx"] == pytest.approx(0.7164, abs=5e-4)
    assert so.mcgowan_volume_from_counts({"C": 1, "H": 4}, ring_count=0)["mcgowan_volume_vx"] == pytest.approx(0.2495, abs=5e-4)
    assert so.mcgowan_volume_from_counts({"C": 2, "H": 6, "O": 1}, ring_count=0)["mcgowan_volume_vx"] == pytest.approx(0.4491, abs=5e-4)


@pytest.mark.parametrize("bad_log_kow", [65.0, 33.84, 25.0, -12.0])
def test_physically_implausible_log_kow_is_refused_not_turned_into_a_koc(bad_log_kow):
    # Real values from a validation run: EPA CompTox held 65.0 for 2'-acetonaphthone beside a second value of 2.68;
    # their median (33.84) used to yield log Koc = 26.8 with no warning.
    for call in (
        lambda: so.li_neutral(bad_log_kow, 0.02),
        lambda: so.ecetoc_base_workbook(bad_log_kow, 0.02),
        lambda: so.franco_trapp("acid", bad_log_kow, 4.0, 7.0, 0.01, 0.02),
    ):
        with pytest.raises(ValueError, match="physically plausible"):
            call()


def test_extreme_but_possible_log_kow_is_allowed_with_an_extrapolation_warning():
    for result in (so.li_neutral(9.0, 0.02), so.ecetoc_base_workbook(9.0, 0.02), so.franco_trapp("base", 9.0, 8.0, 7.0, 0.01, 0.02)):
        assert any("above 8" in w for w in result["warnings"])
    assert not so.li_neutral(4.0, 0.02)["warnings"]


def test_ecetoc_carries_its_measured_external_performance():
    assert any("over-predicted" in w and "223" in w for w in so.ecetoc_base_workbook(3.0, 0.02)["warnings"])


# ---------------------------------------------------------------------------
# Biosolids, plant uptake, river network, PNEC, equilibrium partitioning
# ---------------------------------------------------------------------------


def test_biosolids_series_equals_the_closed_geometric_form_and_respects_the_steady_state_ceiling():
    rng = random.Random(7)
    for _ in range(150):
        conc, rate, depth, rho = 10 ** rng.uniform(-2, 3), rng.uniform(0.5, 20), rng.uniform(0.05, 0.3), rng.uniform(1000, 1700)
        dt50, years = 10 ** rng.uniform(0.7, 3.2), rng.randint(1, 60)
        result = run_biosolids_land_application({
            "source_mode": "biosolids_concentration", "biosolids_concentration_mg_kg_dw": conc, "biosolids_application_t_dw_ha_year": rate,
            "land_application_area_ha": 1.0, "soil_mixing_depth_m": depth, "soil_bulk_density_kg_m3": rho, "operating_days_per_year": 365,
            "fraction_sludge_land_applied": 1.0, "soil_dt50_days": dt50, "assessment_years": years,
        })
        increment = conc * rate * 1000 / 1e6 * 1e6 / (1e4 * depth * rho)
        decay = math.exp(-math.log(2) * 365 / dt50)
        assert result["single_application_increment_mg_kg"] == pytest.approx(increment, rel=1e-12)
        assert result["final_post_application_mg_kg"] == pytest.approx(increment * (1 - decay ** years) / (1 - decay), rel=1e-9)
        assert result["final_post_application_mg_kg"] <= increment / (1 - decay) * (1 + 1e-12)


def test_briggs_tscf_shape_and_plant_uptake_mass_conservation():
    assert briggs_tscf(1.78) == pytest.approx(0.784, rel=1e-12)  # Briggs et al. (1982) maximum
    assert briggs_tscf(1.78 + 1.3) == pytest.approx(briggs_tscf(1.78 - 1.3), rel=1e-12)
    rng = random.Random(2)
    for _ in range(150):
        fractions = [rng.random() for _ in range(3)]
        fractions = [f / sum(fractions) for f in fractions]
        masses = [rng.uniform(0.01, 2) for _ in range(3)]
        payload = {
            "model_mode": "user_tscf", "user_tscf": rng.uniform(0, 1), "soil_concentration_mg_kg_dw": 10 ** rng.uniform(-3, 2), "kd_l_kg": 10 ** rng.uniform(-1, 3),
            "volumetric_water_content_l_l": rng.uniform(0.1, 0.5), "soil_bulk_density_kg_m3": rng.uniform(1000, 1700), "transpiration_l_plant_day": rng.uniform(0.05, 2),
            "harvest_interval_days": rng.uniform(20, 200), "plant_loss_dt50_days": rng.choice([None, 3.0, 30.0]),
            "root_allocation_fraction": fractions[0], "shoot_allocation_fraction": fractions[1], "edible_allocation_fraction": fractions[2],
            "root_fresh_mass_kg": masses[0], "shoot_fresh_mass_kg": masses[1], "edible_fresh_mass_kg": masses[2],
        }
        result = run_plant_uptake_screen(payload)
        porewater = payload["soil_concentration_mg_kg_dw"] / (payload["kd_l_kg"] + payload["volumetric_water_content_l_l"] / (payload["soil_bulk_density_kg_m3"] / 1000))
        uptake = porewater * payload["user_tscf"] * payload["transpiration_l_plant_day"]
        half_life, days = payload["plant_loss_dt50_days"], payload["harvest_interval_days"]
        expected_mass = uptake * days if half_life is None else uptake / (math.log(2) / half_life) * (1 - math.exp(-math.log(2) / half_life * days))
        reconstructed = sum(result[f"{p}_concentration_mg_kg_fw"] * m for p, m in zip(("root", "shoot", "edible_tissue"), masses))
        assert result["soil_porewater_concentration_mg_l"] == pytest.approx(porewater, rel=1e-12)
        assert result["total_chemical_mass_in_plant_mg"] == pytest.approx(expected_mass, rel=1e-9)
        assert reconstructed == pytest.approx(result["total_chemical_mass_in_plant_mg"], rel=1e-9)


def test_river_network_closes_mass_and_matches_first_order_attenuation():
    rng = random.Random(1)
    for _ in range(150):
        n = rng.randint(1, 8)
        segments = [{"segment_id": f"s{i}", "flow_m3_day": 10 ** rng.uniform(3, 7), "travel_time_days": rng.uniform(0, 3), "water_dt50_days": 10 ** rng.uniform(-0.5, 2.5),
                     "local_load_kg_day": 10 ** rng.uniform(-4, 1) if rng.random() < 0.8 else 0.0, "upstream_ids": []} for i in range(n)]
        claimed: set[int] = set()
        for i in range(n - 1, 0, -1):
            candidates = [j for j in range(i) if j not in claimed]
            if candidates and rng.random() < 0.8:
                parent = rng.choice(candidates)
                claimed.add(parent)
                segments[i]["upstream_ids"].append(f"s{parent}")
        result = run_catchment_river_network({"segments": segments, "aquatic_pnec_ug_l": 1.0})
        summary = result["network_summary"]
        assert abs(summary["mass_balance_error_kg_day"]) <= max(1e-12, summary["total_local_input_kg_day"] * 1e-9)
        by_id = {s["segment_id"]: s for s in segments}
        for row in result["segments"]:
            seg = by_id[row["segment_id"]]
            attenuation = math.exp(-math.log(2) / seg["water_dt50_days"] * seg["travel_time_days"])
            assert row["outlet_load_kg_day"] == pytest.approx(row["inlet_load_kg_day"] * attenuation, rel=1e-12)
            assert row["outlet_concentration_ug_l"] == pytest.approx(row["outlet_load_kg_day"] * 1e6 / seg["flow_m3_day"], rel=1e-12)
            assert row["outlet_concentration_ug_l"] * (1 - 1e-12) <= row["mean_concentration_ug_l"] <= row["inlet_concentration_ug_l"] * (1 + 1e-12)


def test_pnec_arithmetic_across_units_and_equilibrium_partitioning_relations():
    rng = random.Random(5)
    to_ug_l = {"ng/L": 1e-3, "ug/L": 1.0, "mg/L": 1e3, "g/L": 1e6}
    for _ in range(150):
        unit, value, factor = rng.choice(list(to_ug_l)), 10 ** rng.uniform(-3, 4), rng.choice([1, 10, 50, 100, 500, 1000])
        result = derive_pnec(endpoint_value=value, endpoint_unit=unit, endpoint_type="NOEC", assessment_factor=factor,
                             assessment_factor_rationale="chronic, two trophic levels", guidance_reference="ECHA R.10 (test)")
        assert float(result["pnec"]["value"]) == pytest.approx(value * to_ug_l[unit] / factor, rel=1e-9)
    for _ in range(150):
        pnec_water, koc = 10 ** rng.uniform(-5, 1), 10 ** rng.uniform(0, 6)
        soil = ep.derive_pnec_soil_from_water(pnec_water_mg_per_l=pnec_water, koc_l_per_kg=koc)
        assert float(soil.pnec_soil_mg_per_kg) == pytest.approx(koc * pnec_water / 85, rel=1e-9)  # TGD / ECETOC TR92 simplification
        assert float(ep.derive_pnec_soil_from_water(pnec_water_mg_per_l=2 * pnec_water, koc_l_per_kg=koc).pnec_soil_mg_per_kg) == pytest.approx(2 * float(soil.pnec_soil_mg_per_kg), rel=1e-12)
