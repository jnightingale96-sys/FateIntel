"""Tests for the Canada (ECCC/CEPA) assessment-factor PNEC derivation."""

from __future__ import annotations

import pytest

from app.services.canada_pnec import (
    CanadaPnecInputError,
    assessment_factor,
    endpoint_standardization_factor,
    mode_of_action_factor,
    pnec_from_critical_toxicity_value,
    species_variation_factor,
)


def test_fes_all_extrapolations_needed_is_ten():
    fes = endpoint_standardization_factor(
        short_to_long_term_extrapolation_needed=True,
        lethal_to_sublethal_extrapolation_needed=True,
        median_to_no_effect_extrapolation_needed=True,
    )
    assert float(fes) == pytest.approx(10.0)


def test_fes_no_extrapolations_needed_is_one():
    fes = endpoint_standardization_factor(
        short_to_long_term_extrapolation_needed=False,
        lethal_to_sublethal_extrapolation_needed=False,
        median_to_no_effect_extrapolation_needed=False,
    )
    assert float(fes) == pytest.approx(1.0)


def test_fes_mixed_extrapolations_is_five():
    fes = endpoint_standardization_factor(
        short_to_long_term_extrapolation_needed=True,
        lethal_to_sublethal_extrapolation_needed=False,
        median_to_no_effect_extrapolation_needed=False,
    )
    assert float(fes) == pytest.approx(5.0)


def test_fsv_matches_published_table():
    assert float(species_variation_factor(organism_categories=1, species_count=1)) == pytest.approx(50.0)
    assert float(species_variation_factor(organism_categories=1, species_count=7)) == pytest.approx(5.0)
    assert float(species_variation_factor(organism_categories=3, species_count=3)) == pytest.approx(5.0)
    assert float(species_variation_factor(organism_categories=3, species_count=7)) == pytest.approx(1.0)


def test_fsv_rejects_impossible_category_species_combination():
    with pytest.raises(CanadaPnecInputError):
        species_variation_factor(organism_categories=3, species_count=1)


def test_fsv_rejects_out_of_range_category_count():
    with pytest.raises(CanadaPnecInputError):
        species_variation_factor(organism_categories=4, species_count=7)


def test_fmoa_named_categories():
    assert float(mode_of_action_factor("narcotic")) == pytest.approx(1.0)
    assert float(mode_of_action_factor("non_narcotic_expressed_in_dataset")) == pytest.approx(2.0)
    assert float(mode_of_action_factor("non_narcotic_not_fully_expressed")) == pytest.approx(5.0)
    assert float(mode_of_action_factor("narcotic_short_term_non_narcotic_long_term_not_expressed")) == pytest.approx(10.0)


def test_fmoa_rejects_unknown_category():
    with pytest.raises(CanadaPnecInputError):
        mode_of_action_factor("made_up_category")  # type: ignore[arg-type]


def test_worked_example_matches_fact_sheet_exactly():
    # Fact sheet's own example: carp 96-h LC50 34 mg/L (FES 10), water flea
    # 48-h EC50 15 mg/L (FES 10, lowest SEV -> CTV), water flea 21-day EC10
    # 3 mg/L (FES 1), algae 72-h EC50 10 mg/L (FES 5). CTV = 15 mg/L.
    # FES = 10 (acute severe-effect to chronic low/no-effect extrapolation).
    # FSV = 5 (3 species across 3 categories -> "2 to 3 species" column).
    # FMOA = 1 (narcotic mode of action).
    # PNEC = 15 / (10 * 5 * 1) = 0.3 mg/L.
    fes = endpoint_standardization_factor(
        short_to_long_term_extrapolation_needed=True,
        lethal_to_sublethal_extrapolation_needed=True,
        median_to_no_effect_extrapolation_needed=True,
    )
    fsv = species_variation_factor(organism_categories=3, species_count=3)
    fmoa = mode_of_action_factor("narcotic")
    factor = assessment_factor(fes=fes, fsv=fsv, fmoa=fmoa)

    assert float(factor.assessment_factor) == pytest.approx(50.0)
    pnec = pnec_from_critical_toxicity_value(critical_toxicity_value=15, factor=factor)
    assert float(pnec) == pytest.approx(0.3)


def test_pnec_rejects_non_positive_ctv():
    factor = assessment_factor(fes=10, fsv=5, fmoa=1)  # type: ignore[arg-type]
    with pytest.raises(CanadaPnecInputError):
        pnec_from_critical_toxicity_value(critical_toxicity_value=0, factor=factor)


def test_rationale_names_the_source():
    factor = assessment_factor(fes=10, fsv=5, fmoa=1)  # type: ignore[arg-type]
    rationale = factor.rationale()
    assert "FES(10)" in rationale
    assert "FSV(5)" in rationale
    assert "FMOA(1)" in rationale
    assert "Okonski" in rationale
