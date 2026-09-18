"""Tests for PMRA general and bee risk-quotient characterisation."""

from __future__ import annotations

import pytest

from app.services.pmra_pesticides import (
    BEE_LOC_ACUTE,
    BEE_LOC_CHRONIC,
    DEFAULT_LOC,
    PmraInputError,
    characterise_bee_risk,
    characterise_general_risk,
    risk_quotient,
)


def test_risk_quotient_is_exposure_over_toxicity():
    rq = risk_quotient(exposure_estimate=2, toxicity_value=20)
    assert float(rq) == pytest.approx(0.1)


def test_risk_quotient_rejects_non_positive_inputs():
    with pytest.raises(PmraInputError):
        risk_quotient(exposure_estimate=0, toxicity_value=1)
    with pytest.raises(PmraInputError):
        risk_quotient(exposure_estimate=1, toxicity_value=-1)


def test_default_loc_is_one():
    assert float(DEFAULT_LOC) == pytest.approx(1.0)


def test_general_risk_below_default_loc_is_acceptable():
    result = characterise_general_risk(
        exposure_estimate=1, toxicity_value=10, receptor_group="aquatic_invertebrates"
    )
    assert float(result.rq) == pytest.approx(0.1)
    assert float(result.loc) == pytest.approx(1.0)
    assert result.exceeds_loc is False


def test_general_risk_at_default_loc_is_unacceptable():
    result = characterise_general_risk(exposure_estimate=1, toxicity_value=1, receptor_group="birds")
    assert result.exceeds_loc is True


def test_general_risk_accepts_reviewer_supplied_custom_loc():
    result = characterise_general_risk(
        exposure_estimate=1, toxicity_value=5, receptor_group="special_case", custom_loc=0.5
    )
    assert float(result.loc) == pytest.approx(0.5)
    assert result.exceeds_loc is False


def test_general_risk_rejects_non_positive_custom_loc():
    with pytest.raises(PmraInputError):
        characterise_general_risk(
            exposure_estimate=1, toxicity_value=5, receptor_group="x", custom_loc=0
        )


def test_bee_loc_values_match_tri_agency_guidance():
    assert float(BEE_LOC_ACUTE) == pytest.approx(0.4)
    assert float(BEE_LOC_CHRONIC) == pytest.approx(1.0)


def test_bee_risk_acute_below_loc_is_acceptable():
    result = characterise_bee_risk(exposure_estimate=1, toxicity_value=100, exposure_type="acute")
    assert float(result.rq) == pytest.approx(0.01)
    assert result.exceeds_loc is False
    assert result.receptor_group == "bees"


def test_bee_risk_acute_at_loc_is_unacceptable():
    result = characterise_bee_risk(exposure_estimate=1, toxicity_value=2.5, exposure_type="acute")
    assert float(result.rq) == pytest.approx(0.4)
    assert result.exceeds_loc is True


def test_bee_risk_chronic_uses_different_loc():
    below = characterise_bee_risk(exposure_estimate=1, toxicity_value=5, exposure_type="chronic")
    assert float(below.rq) == pytest.approx(0.2)
    assert below.exceeds_loc is False

    at_loc = characterise_bee_risk(exposure_estimate=1, toxicity_value=1, exposure_type="chronic")
    assert at_loc.exceeds_loc is True


def test_bee_risk_rejects_invalid_exposure_type():
    with pytest.raises(PmraInputError):
        characterise_bee_risk(exposure_estimate=1, toxicity_value=1, exposure_type="subacute")
