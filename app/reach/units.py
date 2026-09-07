"""Strict concentration-unit normalisation for aquatic endpoints."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import isfinite


CANONICAL_UNIT = "µg/L"

_TO_MICROGRAMS_PER_LITRE = {
    "ng/l": Decimal("0.001"),
    "ug/l": Decimal("1"),
    "mg/l": Decimal("1000"),
    "g/l": Decimal("1000000"),
}

_CANONICAL_LABELS = {
    "ng/l": "ng/L",
    "ug/l": CANONICAL_UNIT,
    "mg/l": "mg/L",
    "g/l": "g/L",
}


def normalise_concentration_unit(unit: str) -> str:
    """Return one of ``ng/L``, ``µg/L``, ``mg/L`` or ``g/L``.

    The micro sign, Greek mu and ASCII ``u`` are accepted as equivalent.  No
    density assumptions or mass/mass conversions are made.
    """

    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("A concentration unit is required")
    key = (
        unit.strip()
        .replace("μ", "u")
        .replace("µ", "u")
        .replace("ℓ", "l")
        .replace(" ", "")
        .casefold()
    )
    if key not in _CANONICAL_LABELS:
        supported = ", ".join(_CANONICAL_LABELS.values())
        raise ValueError(f"Unsupported concentration unit {unit!r}; use {supported}")
    return _CANONICAL_LABELS[key]


def _positive_decimal(value: int | float | str | Decimal) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Concentration must be a positive finite number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Concentration must be a positive finite number") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError("Concentration must be a positive finite number")
    return number


def convert_concentration(
    value: int | float | str | Decimal,
    from_unit: str,
    to_unit: str = CANONICAL_UNIT,
) -> Decimal:
    """Convert between supported mass-per-litre units using decimal arithmetic."""

    number = _positive_decimal(value)
    source = normalise_concentration_unit(from_unit).replace("µ", "u").casefold()
    target = normalise_concentration_unit(to_unit).replace("µ", "u").casefold()
    converted = number * _TO_MICROGRAMS_PER_LITRE[source] / _TO_MICROGRAMS_PER_LITRE[target]
    if not isfinite(float(converted)):
        raise ValueError("Converted concentration is not finite")
    return converted
