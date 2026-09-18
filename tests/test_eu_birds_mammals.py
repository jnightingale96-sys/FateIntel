"""Tests for the EU birds & mammals Tier 1 TER screening (EFSA 2023 guidance)."""

from __future__ import annotations

import pytest

from app.services.eu_birds_mammals import (
    FoodItemExposureInput,
    GuidanceInputError,
    acute_dietary_ter,
    daily_dose,
    fish_secondary_poisoning_ter,
    reproductive_dietary_ter,
    time_weighted_average_factor,
)


def test_acute_ter_low_risk_at_or_above_ten():
    result = acute_dietary_ter(ld50_mg_kg_bw=100, daily_dose_mg_kg_bw=5)
    assert result.ter == pytest.approx(20.0)
    assert result.low_risk is True


def test_acute_ter_not_low_risk_below_ten():
    result = acute_dietary_ter(ld50_mg_kg_bw=100, daily_dose_mg_kg_bw=20)
    assert result.ter == pytest.approx(5.0)
    assert result.low_risk is False


def test_reproductive_ter_trigger_is_five_not_ten():
    just_above = reproductive_dietary_ter(relevant_endpoint_mg_kg_bw_day=10, ddd_mg_kg_bw_day=1.9)
    just_below = reproductive_dietary_ter(relevant_endpoint_mg_kg_bw_day=10, ddd_mg_kg_bw_day=2.1)
    assert float(just_above.ter) == pytest.approx(10 / 1.9)
    assert just_above.low_risk is True
    assert float(just_below.ter) == pytest.approx(10 / 2.1)
    assert just_below.low_risk is False


def test_daily_dose_screening_step_single_item():
    dd = daily_dose(
        food_intake_rate_g_day=20,
        body_weight_g=20,
        food_items=[FoodItemExposureInput(application_rate_kg_ha=1, residue_unit_dose_mg_kg=40.2)],
    )
    # DD = FIR * (AR * RUD * MAF) / BW = 20 * (1*40.2*1) / 20
    assert float(dd) == pytest.approx(40.2)


def test_daily_dose_tier1_applies_deposition_and_proportion_of_diet():
    dd = daily_dose(
        food_intake_rate_g_day=20,
        body_weight_g=20,
        food_items=[
            FoodItemExposureInput(
                application_rate_kg_ha=1,
                residue_unit_dose_mg_kg=40.2,
                deposition_fraction=0.25,
                proportion_of_diet=0.5,
            )
        ],
    )
    # DD = 20 * (1*40.2*1*0.25*0.5) / 20 = 5.025
    assert float(dd) == pytest.approx(5.025)


def test_daily_dose_sums_multiple_food_items():
    dd = daily_dose(
        food_intake_rate_g_day=10,
        body_weight_g=10,
        food_items=[
            FoodItemExposureInput(application_rate_kg_ha=1, residue_unit_dose_mg_kg=10, proportion_of_diet=0.5),
            FoodItemExposureInput(application_rate_kg_ha=1, residue_unit_dose_mg_kg=20, proportion_of_diet=0.5),
        ],
    )
    # DD = FIR * [(1*10*1*1*0.5) + (1*20*1*1*0.5)] / BW = 10 * (5+10) / 10 = 15
    assert float(dd) == pytest.approx(15.0)


def test_daily_dose_applies_ftwa_for_reproductive_exposure():
    ftwa = time_weighted_average_factor()
    dd_acute = daily_dose(
        food_intake_rate_g_day=20,
        body_weight_g=20,
        food_items=[FoodItemExposureInput(application_rate_kg_ha=1, residue_unit_dose_mg_kg=40.2)],
    )
    ddd_repro = daily_dose(
        food_intake_rate_g_day=20,
        body_weight_g=20,
        food_items=[FoodItemExposureInput(application_rate_kg_ha=1, residue_unit_dose_mg_kg=40.2)],
        fTWA=float(ftwa),
    )
    assert float(ddd_repro) < float(dd_acute)
    assert float(ddd_repro) == pytest.approx(float(dd_acute) * float(ftwa))


def test_default_ftwa_matches_guidance_default_dt50_and_21_day_window():
    ftwa = time_weighted_average_factor()
    # k = ln2/10, j = 21 -> fTWA = (1-e^-kj)/kj, verified independently via Python's math module
    assert float(ftwa) == pytest.approx(0.5267497730571319, rel=1e-9)


def test_ftwa_requires_positive_inputs():
    with pytest.raises(GuidanceInputError):
        time_weighted_average_factor(dt50_days=0)


def test_fish_secondary_poisoning_uses_log_kow_lookup_band():
    result = fish_secondary_poisoning_ter(
        log_kow=6,
        relevant_endpoint_mg_kg_bw_day=1,
        food_intake_rate_g_day=20,
        body_weight_g=20,
        twa_surface_water_concentration_ug_l=10,
    )
    assert result["triggered"] is True
    assert result["ebmf"] == pytest.approx(10.0)
    assert result["bcf_fish_l_kg"] == pytest.approx(5000.0)
    assert result["daily_dose_pec_fish_mg_kg_bw_day"] == pytest.approx(500.0)
    assert result["ter"] == pytest.approx(0.002)
    assert result["low_risk"] is False


def test_fish_secondary_poisoning_not_triggered_below_log_kow_three():
    result = fish_secondary_poisoning_ter(
        log_kow=2,
        relevant_endpoint_mg_kg_bw_day=1,
        food_intake_rate_g_day=20,
        body_weight_g=20,
        twa_surface_water_concentration_ug_l=10,
    )
    assert result["triggered"] is False
    assert result["low_risk"] is None


def test_fish_secondary_poisoning_measured_bcf_overrides_default_band():
    default_band = fish_secondary_poisoning_ter(
        log_kow=6,
        relevant_endpoint_mg_kg_bw_day=1,
        food_intake_rate_g_day=20,
        body_weight_g=20,
        twa_surface_water_concentration_ug_l=10,
    )
    measured = fish_secondary_poisoning_ter(
        log_kow=6,
        relevant_endpoint_mg_kg_bw_day=1,
        food_intake_rate_g_day=20,
        body_weight_g=20,
        twa_surface_water_concentration_ug_l=10,
        measured_bcf_fish_l_kg=1200,
    )
    assert measured["bcf_source"] == "measured"
    assert measured["bcf_fish_l_kg"] == pytest.approx(1200.0)
    assert default_band["bcf_source"].startswith("guidance default band")
    assert measured["daily_dose_pec_fish_mg_kg_bw_day"] < default_band["daily_dose_pec_fish_mg_kg_bw_day"]


def test_daily_dose_rejects_empty_food_items():
    with pytest.raises(GuidanceInputError):
        daily_dose(food_intake_rate_g_day=20, body_weight_g=20, food_items=[])


def test_daily_dose_rejects_non_positive_inputs():
    with pytest.raises(GuidanceInputError):
        daily_dose(
            food_intake_rate_g_day=20,
            body_weight_g=0,
            food_items=[FoodItemExposureInput(application_rate_kg_ha=1, residue_unit_dose_mg_kg=1)],
        )
