"""Tests for the NZ EPA (HSNO) Level-of-Concern risk characterisation."""

from __future__ import annotations

import pytest

from app.services.nz_levels_of_concern import (
    NzLocInputError,
    characterise_risk,
    level_of_concern,
    risk_level,
    risk_quotient,
)


def test_loc_matches_table_9_for_aquatic():
    assert float(level_of_concern("aquatic_acute")) == pytest.approx(0.1)
    assert float(level_of_concern("aquatic_acute", threatened_species=True)) == pytest.approx(0.05)
    assert float(level_of_concern("aquatic_chronic")) == pytest.approx(1.0)
    assert float(level_of_concern("aquatic_chronic", threatened_species=True)) == pytest.approx(0.1)


def test_loc_matches_table_9_for_soil_and_birds():
    assert float(level_of_concern("soil_organisms_acute", threatened_species=True)) == pytest.approx(0.01)
    assert float(level_of_concern("terrestrial_vertebrates_chronic")) == pytest.approx(0.2)
    assert float(level_of_concern("terrestrial_vertebrates_chronic", threatened_species=True)) == pytest.approx(0.1)


def test_loc_matches_table_9_for_bees_and_invertebrates():
    assert float(level_of_concern("bees_acute")) == pytest.approx(0.4)
    assert float(level_of_concern("bees_chronic")) == pytest.approx(1.0)
    assert float(level_of_concern("terrestrial_invertebrates")) == pytest.approx(2.0)


def test_bees_have_no_threatened_species_column():
    with pytest.raises(NzLocInputError):
        level_of_concern("bees_acute", threatened_species=True)


def test_non_target_plants_threatened_only_valid_variant():
    assert float(level_of_concern("non_target_plants_threatened", threatened_species=True)) == pytest.approx(1.0)
    with pytest.raises(NzLocInputError):
        level_of_concern("non_target_plants_threatened", threatened_species=False)


def test_unknown_receptor_exposure_rejected():
    with pytest.raises(NzLocInputError):
        level_of_concern("made_up_receptor")  # type: ignore[arg-type]


def test_risk_quotient_is_pec_over_toxicity_value():
    rq = risk_quotient(predicted_environmental_concentration=2, toxicity_value=8)
    assert float(rq) == pytest.approx(0.25)


def test_risk_quotient_rejects_non_positive_inputs():
    with pytest.raises(NzLocInputError):
        risk_quotient(predicted_environmental_concentration=0, toxicity_value=1)
    with pytest.raises(NzLocInputError):
        risk_quotient(predicted_environmental_concentration=1, toxicity_value=-1)


def test_risk_level_bands_match_table_10():
    from decimal import Decimal

    loc = Decimal("0.1")
    assert risk_level(Decimal("0.05"), loc) == "negligible"   # 0.5x LOC
    assert risk_level(Decimal("0.1"), loc) == "low"            # 1x LOC
    assert risk_level(Decimal("0.99"), loc) == "low"           # 9.9x LOC
    assert risk_level(Decimal("1.0"), loc) == "medium"         # 10x LOC
    assert risk_level(Decimal("9.99"), loc) == "medium"        # 99.9x LOC
    assert risk_level(Decimal("10.0"), loc) == "high"          # 100x LOC


def test_characterise_risk_end_to_end_aquatic_acute():
    # PEC 0.5 ug/L, LC50 5 ug/L -> RQ = 0.1. LOC (normal aquatic acute) = 0.1.
    # RQ/LOC = 1 -> "low" per Table 10.
    result = characterise_risk(
        receptor_exposure="aquatic_acute",
        predicted_environmental_concentration=0.5,
        toxicity_value=5,
    )
    assert float(result.rq) == pytest.approx(0.1)
    assert float(result.loc) == pytest.approx(0.1)
    assert result.risk_level == "low"


def test_characterise_risk_threatened_species_lowers_loc_and_raises_risk_level():
    result_normal = characterise_risk(
        receptor_exposure="aquatic_acute",
        predicted_environmental_concentration=0.5,
        toxicity_value=5,
        threatened_species=False,
    )
    result_threatened = characterise_risk(
        receptor_exposure="aquatic_acute",
        predicted_environmental_concentration=0.5,
        toxicity_value=5,
        threatened_species=True,
    )
    assert result_threatened.loc < result_normal.loc
    assert result_threatened.rq == result_normal.rq
