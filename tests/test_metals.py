"""Metals data model: basis, units, provenance and fail-closed behaviour."""

from __future__ import annotations

import math

import pytest

from app.services.metals import (
    BasisMismatchError, MetalDataError, MetalMeasurement, bioavailability_context,
    check_basis_for_criterion, derive_dissolved_from_total, identify_element,
    incremental_over_background,
)
from app.services.registry import build_assessment_plan


def _water(value=10.0, unit="ug/L", basis="total", element="Cu", **kw):
    return MetalMeasurement(element=element, value=value, unit=unit, basis=basis,
                            medium="water", source="lab report 12", **kw)


def _soil(value=100.0, unit="mg/kg", basis="total", weight_basis="dry", element="Pb"):
    return MetalMeasurement(element=element, value=value, unit=unit, basis=basis,
                            medium="soil", source="site survey", weight_basis=weight_basis)


def test_identify_element_by_symbol_and_name_and_refuses_guessing():
    assert identify_element("Pb") == "Pb"
    assert identify_element("lead") == "Pb"
    assert identify_element("Mercury") == "Hg"
    assert identify_element("aluminum") == "Al"
    assert identify_element("benzene") is None
    assert identify_element("") is None


def test_water_units_standardise_to_ug_per_litre_and_keep_original():
    m = _water(value=0.5, unit="mg/L")
    assert m.standard_value() == (500.0, "ug/L")
    assert (m.value, m.unit) == (0.5, "mg/L")


def test_solid_units_standardise_to_mg_per_kg_with_weight_basis():
    value, unit = _soil(value=2, unit="g/kg").standard_value()
    assert value == 2000
    assert unit == "mg/kg dry weight"


def test_solid_without_weight_basis_is_rejected_never_assumed():
    with pytest.raises(MetalDataError, match="weight_basis"):
        _soil(weight_basis=None)


def test_water_unit_on_soil_and_solid_unit_on_water_are_rejected():
    with pytest.raises(MetalDataError):
        _soil(unit="mg/L")
    with pytest.raises(MetalDataError):
        _water(unit="mg/kg")


def test_source_is_mandatory():
    with pytest.raises(MetalDataError, match="source"):
        MetalMeasurement(element="Cu", value=1, unit="ug/L", basis="total", medium="water", source=" ")


@pytest.mark.parametrize("bad", [-1.0, math.nan, math.inf])
def test_invalid_concentrations_rejected(bad):
    with pytest.raises(MetalDataError):
        _water(value=bad)


def test_non_metal_element_rejected():
    with pytest.raises(MetalDataError, match="reference set"):
        _water(element="C")


def test_basis_mismatch_is_reported_not_converted():
    result = check_basis_for_criterion(_water(basis="total"), "dissolved")
    assert result["status"] == "BASIS_MISMATCH"
    assert result["compatible"] is False


def test_unknown_basis_cannot_be_compared():
    assert check_basis_for_criterion(_water(basis="unknown"), "dissolved")["status"] == "BASIS_UNKNOWN"


def test_matching_basis_is_ok():
    assert check_basis_for_criterion(_water(basis="dissolved"), "dissolved")["compatible"] is True


def test_criterion_basis_must_be_stated():
    with pytest.raises(MetalDataError):
        check_basis_for_criterion(_water(), "unknown")


def test_dissolved_derivation_is_explicit_labelled_and_sourced():
    derived = derive_dissolved_from_total(_water(value=10.0), 0.4, "filtered/unfiltered pair, report 12")
    assert derived.basis == "dissolved"
    assert derived.origin == "estimated"
    assert derived.value == pytest.approx(4.0)
    assert any("0.4" in a and "report 12" in a for a in derived.assumptions)


def test_dissolved_derivation_requires_total_water_and_a_sourced_fraction():
    with pytest.raises(BasisMismatchError):
        derive_dissolved_from_total(_water(basis="dissolved"), 0.4, "x")
    with pytest.raises(MetalDataError, match="source"):
        derive_dissolved_from_total(_water(), 0.4, "")
    with pytest.raises(MetalDataError, match="between 0 and 1"):
        derive_dissolved_from_total(_water(), 1.5, "x")


def test_incremental_over_background_above_and_below():
    above = incremental_over_background(_soil(value=150), _soil(value=40))
    assert above["status"] == "ABOVE_BACKGROUND" and above["incremental"] == 110
    below = incremental_over_background(_soil(value=30), _soil(value=40))
    assert below["status"] == "AT_OR_BELOW_BACKGROUND" and below["incremental"] is None


def test_background_comparison_refuses_mixed_bases_elements_or_weight_basis():
    with pytest.raises(BasisMismatchError):
        incremental_over_background(_soil(basis="total"), _soil(basis="particulate"))
    with pytest.raises(BasisMismatchError):
        incremental_over_background(_soil(element="Pb"), _soil(element="Cd"))
    with pytest.raises(BasisMismatchError):
        incremental_over_background(_soil(weight_basis="dry"), _soil(weight_basis="wet"))


def test_bioavailability_context_reports_frameworks_only():
    uk = bioavailability_context("Cu", "UK")
    assert uk["status"] == "FRAMEWORK_KNOWN_MODEL_EXTERNAL"
    assert {r["jurisdiction"] for r in uk["references"]} == {"UK"}
    assert "dissolved organic carbon" in uk["confirmed_water_inputs"]
    us = bioavailability_context("Cu", "US")
    assert "no marine BLM" in us["references"][0]["framework"]


def test_bioavailability_context_does_not_invent_coverage():
    assert bioavailability_context("Hg", "UK")["status"] == "REGULATORY APPLICABILITY NOT ESTABLISHED"
    assert bioavailability_context("Hg", "UK")["references"] == []


def test_metal_plan_lists_metal_specific_inputs_and_external_model_warning():
    plan = build_assessment_plan({
        "jurisdiction": "UK", "contaminant_group": "metal_inorganic",
        "scenario": "surface_water_discharge", "tier": 2,
    })
    joined = " ".join(plan["required_inputs"])
    assert "concentration basis" in joined and "background" in joined
    assert any("EXTERNAL MODEL REQUIRED" in w for w in plan["warnings"])
