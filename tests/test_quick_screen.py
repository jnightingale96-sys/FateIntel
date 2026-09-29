"""Quick risk screen: PNEC auto-selection from real ECOTOX-shaped fixtures, and the exposure/RQ orchestration.
Never depends on live network access -- evidence_sources.search_sources is monkeypatched throughout.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import quick_screen as qs


def _candidate(property_code, value, unit, species, source_record_id="1"):
    return {
        "property_code": property_code, "value": value, "unit": unit,
        "endpoint_label": property_code.rsplit(".", 1)[-1], "source_record_id": source_record_id,
        "snippet": f"{property_code.rsplit('.', 1)[-1]} = {value} {unit} | species: {species} | effect: X",
    }


# ------------------------------------------------------------------------------------------------ derive_screening_pnec

def test_no_candidates_reports_a_data_gap_not_a_value():
    result = qs.derive_screening_pnec([])
    assert result.pnec_ug_l is None
    assert result.data_gap is not None
    assert "does not predict one" in result.data_gap


def test_three_or_more_chronic_species_gets_af_10():
    candidates = [
        _candidate("ECOTOX.AQUATIC.NOEC", 100, "ug/L", "Daphnia magna", "1"),
        _candidate("ECOTOX.AQUATIC.NOEC", 50, "ug/L", "Oncorhynchus mykiss", "2"),
        _candidate("ECOTOX.AQUATIC.NOEC", 200, "ug/L", "Selenastrum capricornutum", "3"),
    ]
    result = qs.derive_screening_pnec(candidates)
    assert result.assessment_factor == Decimal("10")
    assert result.critical_value_ug_l == Decimal("50")
    assert result.pnec_ug_l == Decimal("5")
    assert len(result.species_considered) == 3


def test_one_chronic_value_gets_af_100():
    candidates = [_candidate("ECOTOX.AQUATIC.NOEC", 100, "ug/L", "Daphnia magna", "1")]
    result = qs.derive_screening_pnec(candidates)
    assert result.assessment_factor == Decimal("100")
    assert result.pnec_ug_l == Decimal("1")


def test_acute_only_gets_af_1000():
    candidates = [
        _candidate("ECOTOX.AQUATIC.EC50", 1000, "ug/L", "Daphnia magna", "1"),
        _candidate("ECOTOX.AQUATIC.LC50", 500, "ug/L", "Oncorhynchus mykiss", "2"),
    ]
    result = qs.derive_screening_pnec(candidates)
    assert result.assessment_factor == Decimal("1000")
    assert result.critical_value_ug_l == Decimal("500")
    assert result.pnec_ug_l == Decimal("0.5")
    assert "acute" in result.basis


def test_chronic_data_preferred_over_acute_even_when_acute_is_lower():
    candidates = [
        _candidate("ECOTOX.AQUATIC.EC50", 1, "ug/L", "Daphnia magna", "1"),  # very low acute value
        _candidate("ECOTOX.AQUATIC.NOEC", 100, "ug/L", "Oncorhynchus mykiss", "2"),
    ]
    result = qs.derive_screening_pnec(candidates)
    assert result.assessment_factor == Decimal("100")  # chronic band, not acute
    assert result.critical_value_ug_l == Decimal("100")


def test_unit_conversion_handles_mg_and_ng():
    candidates = [
        _candidate("ECOTOX.AQUATIC.NOEC", 1, "mg/L", "Daphnia magna", "1"),
        _candidate("ECOTOX.AQUATIC.NOEC", 500, "ng/L", "Oncorhynchus mykiss", "2"),
    ]
    result = qs.derive_screening_pnec(candidates)
    # 500 ng/L = 0.5 ug/L, lower than 1 mg/L = 1000 ug/L
    assert result.critical_value_ug_l == Decimal("0.5")


def test_non_positive_or_unparseable_values_are_skipped_not_invented():
    candidates = [
        _candidate("ECOTOX.AQUATIC.NOEC", -5, "ug/L", "Daphnia magna", "1"),
        _candidate("ECOTOX.AQUATIC.NOEC", 10, "furlongs/fortnight", "Oncorhynchus mykiss", "2"),
        _candidate("ECOTOX.AQUATIC.NOEC", 42, "ug/L", "Selenastrum capricornutum", "3"),
    ]
    result = qs.derive_screening_pnec(candidates)
    assert result.critical_value_ug_l == Decimal("42")
    assert result.candidates_used == 1


def test_irrelevant_property_codes_are_ignored():
    candidates = [{"property_code": "PHYS.LOGKOW", "value": 3, "unit": "dimensionless", "snippet": ""}]
    result = qs.derive_screening_pnec(candidates)
    assert result.pnec_ug_l is None


# --------------------------------------------------------------------------------------------- screen_chemical_risk

def test_screen_chemical_risk_generic_wwtp_requires_positive_release(monkeypatch):
    with pytest.raises(qs.QuickScreenInputError, match="positive"):
        qs.screen_chemical_risk(chemical_name="X", cas_number=None, smiles=None, release_kg_year=0, scenario="generic_wwtp")


def test_screen_chemical_risk_ema_mode_requires_dose(monkeypatch):
    with pytest.raises(qs.QuickScreenInputError, match="maximum_daily_dose_mg"):
        qs.screen_chemical_risk(chemical_name="X", cas_number=None, smiles=None, release_kg_year=1, scenario="ema_phase_i_pharma")


def test_screen_chemical_risk_end_to_end_generic_wwtp(monkeypatch):
    def fake_search_sources(*, chemical_name, cas_number, source_keys, limit_per_source):
        assert source_keys == ["epa_ecotox"]
        return {"candidates": [
            _candidate("ECOTOX.AQUATIC.NOEC", 100, "ug/L", "Daphnia magna", "1"),
            _candidate("ECOTOX.AQUATIC.NOEC", 50, "ug/L", "Oncorhynchus mykiss", "2"),
            _candidate("ECOTOX.AQUATIC.NOEC", 200, "ug/L", "Selenastrum capricornutum", "3"),
        ]}
    monkeypatch.setattr(qs, "search_sources", fake_search_sources)

    result = qs.screen_chemical_risk(
        chemical_name="Test Chemical", cas_number="000-00-0", smiles="CCO",
        release_kg_year=1000, scenario="generic_wwtp", population=10_000,
    )
    assert result["screening_estimate"] is True and result["reviewed"] is False
    assert result["hazard"]["pnec_ug_l"] == pytest.approx(5.0)  # 50 / AF10
    assert result["exposure"]["pec_surface_water_ug_l"] > 0
    assert result["risk"]["risk_quotient"] == pytest.approx(
        result["exposure"]["pec_surface_water_ug_l"] / 5.0
    )
    assert result["risk"]["risk_band"] in {"risk_not_excluded", "low"}


def test_screen_chemical_risk_ema_mode_end_to_end(monkeypatch):
    def fake_search_sources(*, chemical_name, cas_number, source_keys, limit_per_source):
        return {"candidates": [_candidate("ECOTOX.AQUATIC.NOEC", 25, "ug/L", "Ceriodaphnia dubia", "1")]}
    monkeypatch.setattr(qs, "search_sources", fake_search_sources)

    result = qs.screen_chemical_risk(
        chemical_name="Carbamazepine", cas_number="298-46-4", smiles=None,
        release_kg_year=1, scenario="ema_phase_i_pharma", maximum_daily_dose_mg=2000,
    )
    assert result["exposure"]["scenario"] == "ema_phase_i_pharma"
    # Matches the real gold-standard-case result verified live this session.
    assert result["exposure"]["pec_surface_water_ug_l"] == pytest.approx(10.0)
    assert result["hazard"]["pnec_ug_l"] == pytest.approx(0.25)  # 25 / AF100 (only one species)
    assert result["risk"]["risk_quotient"] == pytest.approx(40.0)


def test_screen_chemical_risk_reports_data_gap_without_crashing(monkeypatch):
    def fake_search_sources(*, chemical_name, cas_number, source_keys, limit_per_source):
        return {"candidates": []}
    monkeypatch.setattr(qs, "search_sources", fake_search_sources)

    result = qs.screen_chemical_risk(
        chemical_name="Unknown Substance", cas_number=None, smiles=None,
        release_kg_year=10, scenario="generic_wwtp",
    )
    assert result["hazard"]["pnec_ug_l"] is None
    assert result["hazard"]["data_gap"] is not None
    assert result["risk"]["risk_quotient"] is None
    assert result["risk"]["risk_band"] == "cannot_be_characterised"
