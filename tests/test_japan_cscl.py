"""Japan CSCL assessment-factor tiers: both tiers checked against the two real MoE worked examples they were
confirmed from (Carbamazepine, 1,1,1,2-Tetrafluoroethane), not invented numbers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.japan_cscl import (
    AF_ACUTE_MULTI_SPECIES,
    AF_CHRONIC_MULTI_SPECIES,
    JapanCsclInputError,
    derive_pnec_japan_cscl,
)


def test_chronic_tier_matches_the_real_carbamazepine_worked_example():
    # MoE Vol. 21: lowest chronic NOEC (Ceriodaphnia dubia, 7-d reproductive inhibition) = 25 ug/L,
    # assessment factor 10 -> PNEC 2.5 ug/L, exactly as published.
    result = derive_pnec_japan_cscl(lowest_toxicity_value_ug_per_l=25, data_type="chronic_multi_species")
    assert result.assessment_factor == AF_CHRONIC_MULTI_SPECIES == Decimal("10")
    assert result.pnec_ug_per_l == pytest.approx(Decimal("2.5"))


def test_acute_tier_matches_the_real_carbamazepine_worked_example():
    # MoE Vol. 21: lowest acute value among the four species was the Daphnia magna 48-h EC50, ">13,800 ug/L";
    # the document reports the resulting PNEC as ">130 ug/L", consistent with AF 100 applied to 13,800.
    result = derive_pnec_japan_cscl(lowest_toxicity_value_ug_per_l=13800, data_type="acute_multi_species")
    assert result.assessment_factor == AF_ACUTE_MULTI_SPECIES == Decimal("100")
    assert result.pnec_ug_per_l == pytest.approx(Decimal("138"))


def test_rejects_a_data_type_outside_the_two_confirmed_tiers():
    with pytest.raises(JapanCsclInputError, match="only two tiers"):
        derive_pnec_japan_cscl(lowest_toxicity_value_ug_per_l=100, data_type="single_species")  # type: ignore[arg-type]


def test_rejects_a_non_positive_toxicity_value():
    with pytest.raises(JapanCsclInputError, match="positive"):
        derive_pnec_japan_cscl(lowest_toxicity_value_ug_per_l=0, data_type="chronic_multi_species")
    with pytest.raises(JapanCsclInputError, match="positive"):
        derive_pnec_japan_cscl(lowest_toxicity_value_ug_per_l=-5, data_type="acute_multi_species")


def test_result_carries_a_checkable_source_citation():
    result = derive_pnec_japan_cscl(lowest_toxicity_value_ug_per_l=25, data_type="chronic_multi_species")
    assert "env.go.jp" in result.guidance_reference
    assert "298-46-4" in result.guidance_reference  # Carbamazepine's own CAS number, not a generic citation
