"""Tests for the EU honey-bee Tier 1 spray screening (EFSA 2013 guidance, Section 3.1.2)."""

from __future__ import annotations

import pytest

from app.services.eu_bees import (
    ETR_ACUTE_ORAL_TRIGGER,
    ETR_CHRONIC_ORAL_TRIGGER,
    ETR_HPG_TRIGGER,
    ETR_LARVAE_TRIGGER,
    HQ_CONTACT_TRIGGER_DOWNWARDS,
    HQ_CONTACT_TRIGGER_SIDEWARD_UPWARDS,
    GuidanceInputError,
    honey_bee_acute_oral_etr,
    honey_bee_chronic_oral_etr,
    honey_bee_contact_hq,
    honey_bee_hpg_etr,
    honey_bee_larvae_etr,
    honey_bee_tier1_screen,
)


# ---------------------------------------------------------------------------
# Contact HQ
# ---------------------------------------------------------------------------


def test_contact_hq_matches_the_formula_by_hand():
    result = honey_bee_contact_hq(application_rate_g_ha=50, ld50_contact_ug_bee=0.2, spray_direction="downwards")
    assert result["hq_contact"] == pytest.approx(250.0)
    assert result["trigger"] == pytest.approx(float(HQ_CONTACT_TRIGGER_DOWNWARDS))
    assert result["negligible_risk"] is False


def test_contact_hq_uses_the_higher_trigger_for_sideward_upwards_sprays():
    just_below = honey_bee_contact_hq(application_rate_g_ha=50, ld50_contact_ug_bee=0.6, spray_direction="sideward_upwards")
    just_above = honey_bee_contact_hq(application_rate_g_ha=50, ld50_contact_ug_bee=0.5, spray_direction="sideward_upwards")
    assert just_below["hq_contact"] == pytest.approx(50 / 0.6)
    assert just_below["trigger"] == pytest.approx(float(HQ_CONTACT_TRIGGER_SIDEWARD_UPWARDS))
    assert just_below["negligible_risk"] is True
    assert just_above["hq_contact"] == pytest.approx(100.0)
    assert just_above["negligible_risk"] is False


# ---------------------------------------------------------------------------
# Acute adult oral ETR
# ---------------------------------------------------------------------------


def test_acute_oral_etr_matches_the_formula_by_hand_for_both_spray_directions():
    downwards = honey_bee_acute_oral_etr(application_rate_kg_ha=0.05, ld50_oral_ug_bee=1.2, spray_direction="downwards")
    sideward = honey_bee_acute_oral_etr(application_rate_kg_ha=0.05, ld50_oral_ug_bee=1.2, spray_direction="sideward_upwards")
    assert downwards["sv"] == pytest.approx(7.55)
    assert downwards["etr_acute_adult_oral"] == pytest.approx(0.05 * 7.55 / 1.2)
    assert downwards["negligible_risk"] is False  # > 0.2
    assert sideward["sv"] == pytest.approx(10.6)
    assert sideward["etr_acute_adult_oral"] == pytest.approx(0.05 * 10.6 / 1.2)


def test_acute_oral_etr_negligible_below_trigger():
    result = honey_bee_acute_oral_etr(application_rate_kg_ha=0.001, ld50_oral_ug_bee=1, spray_direction="downwards")
    assert result["etr_acute_adult_oral"] < float(ETR_ACUTE_ORAL_TRIGGER)
    assert result["negligible_risk"] is True


# ---------------------------------------------------------------------------
# Chronic adult oral ETR
# ---------------------------------------------------------------------------


def test_chronic_oral_etr_matches_the_formula_by_hand_and_uses_the_tighter_trigger():
    negligible = honey_bee_chronic_oral_etr(application_rate_kg_ha=0.001, lc50_oral_ug_bee_per_day=1, spray_direction="downwards")
    not_negligible = honey_bee_chronic_oral_etr(application_rate_kg_ha=0.01, lc50_oral_ug_bee_per_day=1, spray_direction="downwards")
    assert negligible["etr_chronic_adult_oral"] == pytest.approx(0.001 * 7.55 / 1)
    assert negligible["trigger"] == pytest.approx(float(ETR_CHRONIC_ORAL_TRIGGER))
    assert negligible["negligible_risk"] is True
    assert not_negligible["etr_chronic_adult_oral"] == pytest.approx(0.01 * 7.55 / 1)
    assert not_negligible["negligible_risk"] is False


# ---------------------------------------------------------------------------
# Larvae ETR
# ---------------------------------------------------------------------------


def test_larvae_etr_matches_the_formula_by_hand_with_its_own_sv_pair():
    downwards = honey_bee_larvae_etr(application_rate_kg_ha=0.01, noec_larvae_ug_per_developmental_period=1, spray_direction="downwards")
    sideward = honey_bee_larvae_etr(application_rate_kg_ha=0.01, noec_larvae_ug_per_developmental_period=1, spray_direction="sideward_upwards")
    assert downwards["sv"] == pytest.approx(4.4)
    assert downwards["etr_larvae"] == pytest.approx(0.01 * 4.4 / 1)
    assert downwards["negligible_risk"] is True
    assert sideward["sv"] == pytest.approx(6.1)
    assert sideward["etr_larvae"] == pytest.approx(0.01 * 6.1 / 1)

    not_negligible = honey_bee_larvae_etr(application_rate_kg_ha=0.1, noec_larvae_ug_per_developmental_period=1, spray_direction="downwards")
    assert not_negligible["etr_larvae"] == pytest.approx(0.44)
    assert not_negligible["negligible_risk"] is False
    assert not_negligible["trigger"] == pytest.approx(float(ETR_LARVAE_TRIGGER))


# ---------------------------------------------------------------------------
# HPG ETR
# ---------------------------------------------------------------------------


def test_hpg_etr_matches_the_formula_by_hand_and_shares_the_adult_oral_sv_pair():
    negligible = honey_bee_hpg_etr(application_rate_kg_ha=0.1, noec_hpg_ug_bee_per_day=1, spray_direction="downwards")
    not_negligible = honey_bee_hpg_etr(application_rate_kg_ha=0.2, noec_hpg_ug_bee_per_day=1, spray_direction="downwards")
    assert negligible["sv"] == pytest.approx(7.55)
    assert negligible["etr_hpg"] == pytest.approx(0.1 * 7.55)
    assert negligible["negligible_risk"] is True
    assert not_negligible["etr_hpg"] == pytest.approx(0.2 * 7.55)
    assert not_negligible["negligible_risk"] is False
    assert not_negligible["trigger"] == pytest.approx(float(ETR_HPG_TRIGGER))


# ---------------------------------------------------------------------------
# Full Tier 1 screen
# ---------------------------------------------------------------------------


def test_tier1_screen_runs_every_ratio_and_reports_each_independently():
    result = honey_bee_tier1_screen(
        application_rate_g_ha=50,
        spray_direction="downwards",
        ld50_contact_ug_bee=0.2,
        ld50_oral_ug_bee=1.2,
        lc50_oral_ug_bee_per_day=1,
        noec_larvae_ug_per_developmental_period=1,
    )
    # Same numbers as the individual-function tests above, cross-checked here end to end.
    assert result["contact"]["hq_contact"] == pytest.approx(250.0)
    assert result["acute_adult_oral"]["etr_acute_adult_oral"] == pytest.approx(0.05 * 7.55 / 1.2)
    assert result["chronic_adult_oral"]["etr_chronic_adult_oral"] == pytest.approx(0.05 * 7.55 / 1)
    assert result["larvae"]["etr_larvae"] == pytest.approx(0.05 * 4.4 / 1)
    assert result["hpg"] is None  # not supplied -> not fabricated
    assert result["negligible_risk_overall"] is False  # contact HQ alone breaches its trigger


def test_tier1_screen_includes_hpg_only_when_supplied_and_reflects_it_in_the_overall_flag():
    with_hpg = honey_bee_tier1_screen(
        application_rate_g_ha=0.5,
        spray_direction="downwards",
        ld50_contact_ug_bee=1,
        ld50_oral_ug_bee=100,
        lc50_oral_ug_bee_per_day=100,
        noec_larvae_ug_per_developmental_period=100,
        noec_hpg_ug_bee_per_day=100,
    )
    assert with_hpg["hpg"] is not None
    assert with_hpg["hpg"]["etr_hpg"] == pytest.approx(0.0005 * 7.55 / 100)
    assert with_hpg["negligible_risk_overall"] is True


def test_tier1_screen_converts_the_single_supplied_rate_correctly_for_both_units():
    result = honey_bee_tier1_screen(
        application_rate_g_ha=100,
        spray_direction="sideward_upwards",
        ld50_contact_ug_bee=10,
        ld50_oral_ug_bee=10,
        lc50_oral_ug_bee_per_day=10,
        noec_larvae_ug_per_developmental_period=10,
    )
    # Contact uses the raw g/ha figure directly.
    assert result["contact"]["hq_contact"] == pytest.approx(100 / 10)
    # Oral/larvae ratios use the same rate converted to kg/ha (0.1 kg/ha).
    assert result["acute_adult_oral"]["etr_acute_adult_oral"] == pytest.approx(0.1 * 10.6 / 10)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"application_rate_g_ha": 0, "ld50_contact_ug_bee": 1, "spray_direction": "downwards"},
        {"application_rate_g_ha": -1, "ld50_contact_ug_bee": 1, "spray_direction": "downwards"},
        {"application_rate_g_ha": 1, "ld50_contact_ug_bee": 0, "spray_direction": "downwards"},
    ],
)
def test_contact_hq_rejects_non_positive_inputs(kwargs):
    with pytest.raises(GuidanceInputError):
        honey_bee_contact_hq(**kwargs)


def test_functions_reject_an_unrecognised_spray_direction():
    with pytest.raises(GuidanceInputError):
        honey_bee_contact_hq(application_rate_g_ha=50, ld50_contact_ug_bee=1, spray_direction="sideways")  # type: ignore[arg-type]
    with pytest.raises(GuidanceInputError):
        honey_bee_acute_oral_etr(application_rate_kg_ha=0.05, ld50_oral_ug_bee=1, spray_direction="up")  # type: ignore[arg-type]
