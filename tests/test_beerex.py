"""Tri-agency Bee-REX Tier 1 exposure screen: every numeric result checked by hand against the primary source's
own stated factors (USEPA/PMRA/CADPR, "Guidance for Assessing Pesticide Risks to Bees", 19 June 2014, Appendix 3).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import beerex as b


# --------------------------------------------------------------------------------------------------- foliar spray

def test_foliar_dietary_residue_matches_the_guidance_own_factor():
    # "AR Metric* (98 ug a.i /g)" per 1 kg a.i./ha, Appendix 3 Table 1.
    assert b.foliar_spray_dietary_residue_ug_per_g(application_rate_kg_ha=1) == Decimal("98")
    assert b.foliar_spray_dietary_residue_ug_per_g(application_rate_kg_ha=2) == Decimal("196")


def test_foliar_contact_dose_matches_the_guidance_own_factor():
    # "2.4 ug a.i./bee per 1 kg a.i./ha" (Koch & Weisser, 1997).
    assert b.foliar_spray_contact_dose_ug_per_bee(application_rate_kg_ha=1) == Decimal("2.4")


def test_foliar_dietary_dose_uses_the_correct_consumption_rate_per_life_stage():
    # Appendix 3 Table 1: "AR Metric* (98 ug a.i /g) (0.292 g/day)" for adults, "(0.124 g/day)" for larvae.
    adult = b.foliar_spray_dietary_dose_ug_per_bee(application_rate_kg_ha=1, life_stage="adult")
    larval = b.foliar_spray_dietary_dose_ug_per_bee(application_rate_kg_ha=1, life_stage="larval")
    assert adult == pytest.approx(Decimal("28.616"))
    assert larval == pytest.approx(Decimal("12.152"))


def test_foliar_contact_rq_compares_against_the_acute_loc():
    result = b.foliar_spray_contact_rq(application_rate_kg_ha=1, contact_ld50_ug_per_bee=0.1)
    assert result.risk_quotient == Decimal("24")  # 2.4 / 0.1
    assert result.loc == b.LOC_ACUTE
    assert result.exceeds_loc is True


def test_foliar_dietary_rq_below_loc_is_reported_as_such():
    result = b.foliar_spray_dietary_rq(
        application_rate_kg_ha=0.01, life_stage="adult", toxicity_endpoint_ug_per_bee=1000, chronic=False,
    )
    assert result.exceeds_loc is False
    assert result.loc == b.LOC_ACUTE


def test_foliar_dietary_rq_chronic_uses_the_chronic_loc():
    result = b.foliar_spray_dietary_rq(
        application_rate_kg_ha=1, life_stage="larval", toxicity_endpoint_ug_per_bee=10, chronic=True,
    )
    assert result.loc == b.LOC_CHRONIC


def test_foliar_functions_reject_non_positive_application_rate():
    with pytest.raises(b.BeeRexInputError):
        b.foliar_spray_dietary_residue_ug_per_g(application_rate_kg_ha=0)
    with pytest.raises(b.BeeRexInputError):
        b.foliar_spray_contact_dose_ug_per_bee(application_rate_kg_ha=-1)


# --------------------------------------------------------------------------------------------------- seed treatment

def test_seed_treatment_dose_is_fixed_and_independent_of_application_rate():
    # "1 mg a.i./kg" = 1 ug a.i./g, applied with no adjustment for application rate (the guidance's own words).
    adult = b.seed_treatment_dietary_dose_ug_per_bee(life_stage="adult")
    larval = b.seed_treatment_dietary_dose_ug_per_bee(life_stage="larval")
    assert adult == Decimal("0.292")
    assert larval == Decimal("0.124")


def test_seed_treatment_rq_matches_dose_over_endpoint():
    result = b.seed_treatment_dietary_rq(life_stage="adult", toxicity_endpoint_ug_per_bee=0.292, chronic=False)
    assert result.risk_quotient == Decimal("1")
    assert result.pathway == "seed_treatment"


# --------------------------------------------------------------------------------------------------- soil treatment

def test_tscf_equation_matches_the_guidance_own_coefficients():
    # Equation 2: TSCF = -0.0648 x (log Kow)^2 + 0.241 x log Kow + 0.5822.
    tscf = b.briggs_transpiration_stream_concentration_factor(log_kow=2)
    expected = Decimal("-0.0648") * 4 + Decimal("0.241") * 2 + Decimal("0.5822")
    assert tscf == pytest.approx(expected)


def test_rcf_equation_matches_the_guidance_own_form():
    # The bracketed term of Equation 1: 10^(0.95 x log Kow - 2.05) + 0.82.
    rcf = b.briggs_root_concentration_factor(log_kow=2)
    expected = Decimal(str(10.0 ** (0.95 * 2 - 2.05))) + Decimal("0.82")
    assert rcf == pytest.approx(expected)


def test_soil_treatment_refuses_outside_the_briggs_calibration_domain():
    # Section 1.3.2: the Briggs data set is bounded to log Kow < 5.
    with pytest.raises(b.BeeRexInputError, match="log Kow < 5"):
        b.soil_treatment_dietary_rq(
            application_rate_kg_ha=1, log_kow=5, koc_l_per_kg=100, life_stage="adult",
            toxicity_endpoint_ug_per_bee=1, chronic=False,
        )


def test_soil_treatment_within_domain_produces_a_positive_smaller_dose_than_foliar():
    # The guidance states soil-treatment exposures are "usually two orders of magnitude lower" than foliar.
    soil_dose = b.soil_treatment_dietary_dose_ug_per_bee(
        application_rate_kg_ha=1, log_kow=2, koc_l_per_kg=100, life_stage="adult",
    )
    foliar_dose = b.foliar_spray_dietary_dose_ug_per_bee(application_rate_kg_ha=1, life_stage="adult")
    assert 0 < soil_dose < foliar_dose


def test_soil_treatment_rq_round_trips_through_the_dose_function():
    dose = b.soil_treatment_dietary_dose_ug_per_bee(
        application_rate_kg_ha=1, log_kow=2, koc_l_per_kg=100, life_stage="larval",
    )
    result = b.soil_treatment_dietary_rq(
        application_rate_kg_ha=1, log_kow=2, koc_l_per_kg=100, life_stage="larval",
        toxicity_endpoint_ug_per_bee=float(dose), chronic=True,
    )
    assert result.risk_quotient == pytest.approx(Decimal("1"))
    assert result.loc == b.LOC_CHRONIC


def test_soil_treatment_rejects_non_positive_koc():
    with pytest.raises(b.BeeRexInputError):
        b.soil_treatment_stem_concentration_ug_per_g(application_rate_kg_ha=1, log_kow=2, koc_l_per_kg=-1)
