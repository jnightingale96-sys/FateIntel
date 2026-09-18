"""Tests for APVMA aquatic risk-quotient triggers."""

from __future__ import annotations

import pytest

from app.services.au_apvma import (
    AQUATIC_RQ_TRIGGER_ACUTE,
    AQUATIC_RQ_TRIGGER_CHRONIC,
    ApvmaInputError,
    aquatic_risk_quotient,
    characterise_aquatic_risk,
)


def test_aquatic_rq_is_pec_over_toxicity_value():
    rq = aquatic_risk_quotient(predicted_environmental_concentration=2, toxicity_value=20)
    assert float(rq) == pytest.approx(0.1)


def test_aquatic_rq_rejects_non_positive_inputs():
    with pytest.raises(ApvmaInputError):
        aquatic_risk_quotient(predicted_environmental_concentration=0, toxicity_value=1)
    with pytest.raises(ApvmaInputError):
        aquatic_risk_quotient(predicted_environmental_concentration=1, toxicity_value=-1)


def test_acute_trigger_is_zero_point_one():
    assert float(AQUATIC_RQ_TRIGGER_ACUTE) == pytest.approx(0.1)


def test_chronic_trigger_is_one():
    assert float(AQUATIC_RQ_TRIGGER_CHRONIC) == pytest.approx(1.0)


def test_characterise_aquatic_risk_acute_below_trigger_is_acceptable():
    result = characterise_aquatic_risk(
        predicted_environmental_concentration=1,
        toxicity_value=100,  # RQ = 0.01 < 0.1
        exposure_type="acute",
    )
    assert result.unacceptable is False


def test_characterise_aquatic_risk_acute_at_trigger_is_unacceptable():
    result = characterise_aquatic_risk(
        predicted_environmental_concentration=1,
        toxicity_value=10,  # RQ = 0.1 == trigger
        exposure_type="acute",
    )
    assert result.unacceptable is True


def test_characterise_aquatic_risk_chronic_uses_different_trigger():
    # RQ = 0.5: acceptable under the acute trigger (0.1 would already flag it)
    # but also acceptable under the chronic trigger (1.0), since it's below both.
    below_both = characterise_aquatic_risk(
        predicted_environmental_concentration=1, toxicity_value=2, exposure_type="chronic"
    )
    assert float(below_both.rq) == pytest.approx(0.5)
    assert below_both.unacceptable is False

    at_chronic_trigger = characterise_aquatic_risk(
        predicted_environmental_concentration=1, toxicity_value=1, exposure_type="chronic"
    )
    assert at_chronic_trigger.unacceptable is True


def test_invalid_exposure_type_rejected():
    with pytest.raises(ApvmaInputError):
        characterise_aquatic_risk(
            predicted_environmental_concentration=1, toxicity_value=1, exposure_type="subacute"
        )
