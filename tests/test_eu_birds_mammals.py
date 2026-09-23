"""Tests for the EU birds & mammals Tier 1 TER screening (EFSA 2023 guidance)."""

from __future__ import annotations

import pytest

from app.services.eu_birds_mammals import (
    EARTHWORM_BCF_VALIDATED_LOG_KOW_RANGE,
    FoodItemExposureInput,
    GuidanceInputError,
    acute_dietary_ter,
    daily_dose,
    earthworm_bioconcentration_factor,
    earthworm_secondary_poisoning_ter,
    fish_secondary_poisoning_ter,
    reproductive_dietary_ter,
    time_weighted_average_factor,
)
from app.services.equilibrium_partitioning import FOC_SOIL_DEFAULT, RHO_SOIL_DEFAULT, RHO_SOLID_DEFAULT


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


# ---------- earthworm-eating secondary poisoning (ECHA R.16, Jager 1998) ----------
def test_earthworm_bcf_matches_jager_equation_by_hand():
    # BCFearthworm = (0.84 + 0.012*Kow) / RHOearthworm, RHOearthworm default 1 -- log Kow 4 -> Kow 10,000
    bcf = earthworm_bioconcentration_factor(log_kow=4.0)
    assert float(bcf) == pytest.approx(0.84 + 0.012 * 10_000.0)


def test_earthworm_bcf_respects_a_supplied_rho():
    default = earthworm_bioconcentration_factor(log_kow=3.0)
    halved = earthworm_bioconcentration_factor(log_kow=3.0, rho_earthworm_kg_wwt_per_l=2.0)
    assert float(halved) == pytest.approx(float(default) / 2)


def test_earthworm_secondary_poisoning_matches_the_r16_equations_by_hand():
    # Koc=500, Csoil=1.0 mg/kg wwt -> Ksoil-water = Focsoil*Koc = 0.02*500 = 10
    # Cporewater = (Csoil * RHOsoil) / (1000 * Ksoil-water) = (1*1700)/(1000*10) = 0.17 mg/L
    # BCFearthworm(log Kow=4) = 0.84 + 0.012*10000 = 120.84
    # CONVsoil = RHOsoil/RHOsolid = 1700/2500 = 0.68; Fgut default 0.1
    # Cearthworm = (120.84*0.17 + 1.0*0.1*0.68) / (1 + 0.1*0.68) = 20.6108 / 1.068
    result = earthworm_secondary_poisoning_ter(
        log_kow=4.0, koc_l_per_kg=500, soil_concentration_mg_kg_wwt=1.0,
        relevant_endpoint_mg_kg_bw_day=10, food_intake_rate_g_day=20, body_weight_g=20,
    )
    ksoil_water = float(FOC_SOIL_DEFAULT) * 500
    c_porewater = (1.0 * float(RHO_SOIL_DEFAULT)) / (1000 * ksoil_water)
    conv_soil = float(RHO_SOIL_DEFAULT) / float(RHO_SOLID_DEFAULT)
    c_earthworm = (120.84 * c_porewater + 1.0 * 0.1 * conv_soil) / (1 + 0.1 * conv_soil)
    assert result["porewater_concentration_mg_l"] == pytest.approx(c_porewater)
    assert result["bcf_earthworm_l_kg"] == pytest.approx(120.84)
    assert result["earthworm_concentration_mg_kg_wwt"] == pytest.approx(c_earthworm)
    daily_dose_expected = (20 / 20) * c_earthworm
    assert result["daily_dose_pec_earthworm_mg_kg_bw_day"] == pytest.approx(daily_dose_expected)
    assert result["ter"] == pytest.approx(10 / daily_dose_expected)
    assert result["bcf_source"].startswith("Jager")
    assert result["within_bcf_validated_range"] is True
    assert "R.16" in result["guidance_reference"]


def test_earthworm_reports_when_log_kow_is_outside_the_jager_validated_range():
    below = earthworm_secondary_poisoning_ter(
        log_kow=0.5, koc_l_per_kg=50, soil_concentration_mg_kg_wwt=1.0,
        relevant_endpoint_mg_kg_bw_day=10, food_intake_rate_g_day=20, body_weight_g=20,
    )
    within = earthworm_secondary_poisoning_ter(
        log_kow=4.0, koc_l_per_kg=50, soil_concentration_mg_kg_wwt=1.0,
        relevant_endpoint_mg_kg_bw_day=10, food_intake_rate_g_day=20, body_weight_g=20,
    )
    assert below["within_bcf_validated_range"] is False
    assert within["within_bcf_validated_range"] is True
    # Out-of-range is reported, not silently refused -- a result is still returned.
    assert below["ter"] > 0
    lower, upper = EARTHWORM_BCF_VALIDATED_LOG_KOW_RANGE
    assert (float(lower), float(upper)) == (1.0, 8.0)


def test_earthworm_measured_bcf_overrides_the_jager_estimate():
    modelled = earthworm_secondary_poisoning_ter(
        log_kow=4.0, koc_l_per_kg=500, soil_concentration_mg_kg_wwt=1.0,
        relevant_endpoint_mg_kg_bw_day=10, food_intake_rate_g_day=20, body_weight_g=20,
    )
    measured = earthworm_secondary_poisoning_ter(
        log_kow=4.0, koc_l_per_kg=500, soil_concentration_mg_kg_wwt=1.0,
        relevant_endpoint_mg_kg_bw_day=10, food_intake_rate_g_day=20, body_weight_g=20,
        measured_bcf_earthworm_l_per_kg=50,
    )
    assert measured["bcf_source"] == "measured"
    assert measured["bcf_earthworm_l_kg"] == pytest.approx(50.0)
    assert measured["earthworm_concentration_mg_kg_wwt"] != modelled["earthworm_concentration_mg_kg_wwt"]


def test_earthworm_uses_the_same_soil_partitioning_constants_as_equilibrium_partitioning():
    # Internal consistency guard: this module must not silently drift from equilibrium_partitioning.py's own
    # Focsoil/RHOsoil/RHOsolid constants, since both trace to the same EU soil-partitioning convention.
    assert float(FOC_SOIL_DEFAULT) == pytest.approx(0.02)
    assert float(RHO_SOIL_DEFAULT) == pytest.approx(1700)
    assert float(RHO_SOLID_DEFAULT) == pytest.approx(2500)


def test_earthworm_rejects_non_positive_inputs():
    with pytest.raises(GuidanceInputError):
        earthworm_secondary_poisoning_ter(
            log_kow=4.0, koc_l_per_kg=500, soil_concentration_mg_kg_wwt=0,
            relevant_endpoint_mg_kg_bw_day=10, food_intake_rate_g_day=20, body_weight_g=20,
        )
    with pytest.raises(GuidanceInputError):
        earthworm_bioconcentration_factor(log_kow=4.0, rho_earthworm_kg_wwt_per_l=0)


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
