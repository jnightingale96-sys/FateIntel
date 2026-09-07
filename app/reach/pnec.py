"""Transparent PNEC arithmetic with an explicit, reviewer-supplied AF."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .units import CANONICAL_UNIT, convert_concentration, normalise_concentration_unit


SUPPORTED_AQUATIC_ENDPOINTS = {
    "ECOTOX.AQUATIC.LC50": "LC50",
    "ECOTOX.AQUATIC.EC50": "EC50",
    "ECOTOX.AQUATIC.NOEC": "NOEC",
    "ECOTOX.AQUATIC.EC10": "EC10",
}


def _assessment_factor(value: int | float | str | Decimal) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Assessment factor must be a finite number greater than or equal to 1")
    try:
        factor = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Assessment factor must be a finite number greater than or equal to 1") from exc
    if not factor.is_finite() or factor < 1:
        raise ValueError("Assessment factor must be a finite number greater than or equal to 1")
    return factor


def derive_pnec(
    *,
    endpoint_value: int | float | str | Decimal,
    endpoint_unit: str,
    endpoint_type: str,
    assessment_factor: int | float | str | Decimal,
    assessment_factor_rationale: str,
    guidance_reference: str,
    target_compartment: str = "freshwater",
) -> dict[str, object]:
    """Derive a freshwater screening PNEC without inferring the AF.

    Assessment-factor selection depends on the usable dataset and expert
    interpretation.  EnviroChem therefore performs and records the arithmetic,
    but never chooses a factor from the endpoint label alone.
    """

    if target_compartment != "freshwater":
        raise ValueError("EnviroChem currently supports explicit-AF freshwater PNEC derivation only")
    if endpoint_type not in set(SUPPORTED_AQUATIC_ENDPOINTS.values()):
        raise ValueError("Endpoint type must be LC50, EC50, NOEC or EC10")
    rationale = assessment_factor_rationale.strip()
    reference = guidance_reference.strip()
    if len(rationale) < 10:
        raise ValueError("Assessment-factor rationale must contain at least 10 characters")
    if len(reference) < 5:
        raise ValueError("A guidance or decision reference is required")

    factor = _assessment_factor(assessment_factor)
    source_unit = normalise_concentration_unit(endpoint_unit)
    normalised = convert_concentration(endpoint_value, source_unit, CANONICAL_UNIT)
    pnec = normalised / factor
    return {
        "target_compartment": target_compartment,
        "critical_endpoint": {
            "endpoint_type": endpoint_type,
            "value": float(Decimal(str(endpoint_value))),
            "unit": source_unit,
            "normalised_value": float(normalised),
            "normalised_unit": CANONICAL_UNIT,
        },
        "assessment_factor": float(factor),
        "assessment_factor_source": "reviewer_supplied",
        "assessment_factor_rationale": rationale,
        "guidance_reference": reference,
        "pnec": {"value": float(pnec), "unit": CANONICAL_UNIT},
        "calculation": "normalised critical endpoint / reviewer-supplied assessment factor",
        "regulatory_status": "review_required_not_authoritative_selection",
    }
