"""Tests for sediment/soil PNEC derivation via the equilibrium partitioning method."""

from __future__ import annotations

import pytest

from app.services.equilibrium_partitioning import (
    EquilibriumPartitioningInputError,
    SEDIMENT_WET_TO_DRY_FACTOR,
    derive_pnec_sediment_from_water,
    derive_pnec_soil_from_water,
)


def test_soil_pnec_matches_tgd_simplified_formula_exactly():
    # ECETOC TR No. 92 Appendix A.2's own algebraic simplification:
    # PNECsoil = Koc * PNECwater / 85
    result = derive_pnec_soil_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    assert float(result.pnec_soil_mg_per_kg) == pytest.approx(1000.0 / 85, rel=1e-9)


def test_soil_pnec_scales_linearly_with_koc_and_pnec_water():
    low = derive_pnec_soil_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=100.0)
    high = derive_pnec_soil_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    assert float(high.pnec_soil_mg_per_kg) == pytest.approx(float(low.pnec_soil_mg_per_kg) * 10, rel=1e-9)


def test_soil_pnec_rejects_non_positive_inputs():
    with pytest.raises(EquilibriumPartitioningInputError):
        derive_pnec_soil_from_water(pnec_water_mg_per_l=0, koc_l_per_kg=100)
    with pytest.raises(EquilibriumPartitioningInputError):
        derive_pnec_soil_from_water(pnec_water_mg_per_l=1, koc_l_per_kg=-5)


def test_sediment_pnec_matches_tgd_rounded_simplified_formula_within_rounding_error():
    # ECETOC TR No. 92 Appendix B.2's own rounded simplification:
    # PNECsediment (wet) = PNECwater * (0.783 + 0.0217 * Koc)
    # The source document rounds 1000/1150 and derived constants; our unrounded arithmetic
    # should agree within that rounding's margin, not exactly.
    result = derive_pnec_sediment_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    tgd_rounded_approx = 1.0 * (0.783 + 0.0217 * 1000.0)
    assert float(result.pnec_sediment_wet_mg_per_kg) == pytest.approx(tgd_rounded_approx, rel=2e-3)


def test_sediment_pnec_exact_unrounded_coefficients():
    # Exact (unrounded) coefficients: 0.9*(1000/1150) + 0.1*0.1*2500/1000*(1000/1150)*Koc
    result = derive_pnec_sediment_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    expected = 0.9 * (1000 / 1150) + (0.1 * 0.1 * 2500 / 1000) * (1000 / 1150) * 1000.0
    assert float(result.pnec_sediment_wet_mg_per_kg) == pytest.approx(expected, rel=1e-9)


def test_sediment_pnec_dry_weight_uses_tgd_wet_to_dry_factor():
    result = derive_pnec_sediment_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    assert float(result.pnec_sediment_dry_mg_per_kg) == pytest.approx(
        float(result.pnec_sediment_wet_mg_per_kg) * float(SEDIMENT_WET_TO_DRY_FACTOR), rel=1e-9
    )


def test_sediment_pnec_rejects_non_positive_inputs():
    with pytest.raises(EquilibriumPartitioningInputError):
        derive_pnec_sediment_from_water(pnec_water_mg_per_l=0, koc_l_per_kg=100)
    with pytest.raises(EquilibriumPartitioningInputError):
        derive_pnec_sediment_from_water(pnec_water_mg_per_l=1, koc_l_per_kg=0)


def test_high_log_kow_factor_is_never_applied_by_default():
    without_factor = derive_pnec_sediment_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    assert float(without_factor.high_log_kow_factor_applied) == pytest.approx(1.0)

    without_factor_soil = derive_pnec_soil_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0)
    assert float(without_factor_soil.high_log_kow_factor_applied) == pytest.approx(1.0)


def test_high_log_kow_factor_is_applied_only_when_explicitly_supplied():
    baseline = derive_pnec_sediment_from_water(pnec_water_mg_per_l=1.0, koc_l_per_kg=200000.0)
    with_factor = derive_pnec_sediment_from_water(
        pnec_water_mg_per_l=1.0, koc_l_per_kg=200000.0, high_log_kow_factor=10
    )
    assert float(with_factor.pnec_sediment_wet_mg_per_kg) == pytest.approx(
        float(baseline.pnec_sediment_wet_mg_per_kg) * 10, rel=1e-9
    )
    assert float(with_factor.high_log_kow_factor_applied) == pytest.approx(10.0)


def test_high_log_kow_factor_rejects_non_positive_value():
    with pytest.raises(EquilibriumPartitioningInputError):
        derive_pnec_sediment_from_water(
            pnec_water_mg_per_l=1.0, koc_l_per_kg=1000.0, high_log_kow_factor=0
        )
