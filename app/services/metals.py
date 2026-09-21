"""Metals and metalloids: identity, concentration basis and provenance, fail-closed.

Metals are not organic chemicals: no SMILES, no Kow, no biodegradation, and toxicity depends on
speciation and bioavailability (US EPA Framework for Metals Risk Assessment, 2007). This module keeps
every measured number on its original basis (total / dissolved / particulate / bioavailable / free ion)
and refuses to convert between bases silently. It performs no bioavailability modelling and contains
no regulatory criteria: see LEGACY_CONTAMINANTS_MATRIX_*.md for what was and was not confirmed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any

# Starter set of environmentally relevant metals/metalloids, not exhaustive.
# Uranium is also a radionuclide: chemical and radiological assessment are separate questions.
METAL_METALLOID_ELEMENTS: dict[str, str] = {
    "Al": "aluminium", "Sb": "antimony", "As": "arsenic", "Ba": "barium", "Be": "beryllium",
    "B": "boron", "Cd": "cadmium", "Cr": "chromium", "Co": "cobalt", "Cu": "copper",
    "Fe": "iron", "Pb": "lead", "Mn": "manganese", "Hg": "mercury", "Mo": "molybdenum",
    "Ni": "nickel", "Se": "selenium", "Ag": "silver", "Sn": "tin", "Tl": "thallium",
    "U": "uranium", "V": "vanadium", "Zn": "zinc",
}
_NAME_TO_SYMBOL = {name: sym for sym, name in METAL_METALLOID_ELEMENTS.items()}
_NAME_TO_SYMBOL["aluminum"] = "Al"  # US spelling

BASES = ("total", "dissolved", "particulate", "bioavailable", "free_ion", "unknown")
MEDIA = ("water", "soil", "sediment", "biota")
ORIGINS = ("measured", "estimated", "modelled")

_WATER_TO_UG_L = {"ng/L": 1e-3, "ug/L": 1.0, "mg/L": 1e3, "g/L": 1e6}
_SOLID_TO_MG_KG = {"ug/kg": 1e-3, "mg/kg": 1.0, "g/kg": 1e3}

# Confirmed inputs for the UKTAG M-BAT simplified BLM (UK matrix doc, section 6). Other tools may need more.
MBAT_CONFIRMED_WATER_INPUTS = ("pH", "dissolved organic carbon", "calcium or hardness")

# Framework existence only, no numeric criteria. Every entry traces to a row in the research matrices.
BIOAVAILABILITY_REFERENCES: dict[str, list[dict[str, str]]] = {
    "Cu": [
        {"jurisdiction": "UK", "framework": "Bioavailable EQS via UKTAG M-BAT (simplified BLM); varies with DOC",
         "source": "LEGACY_CONTAMINANTS_MATRIX_UK.md sections 5-6"},
        {"jurisdiction": "US", "framework": "2007 freshwater BLM-based aquatic life criterion; no marine BLM finalised",
         "source": "LEGACY_CONTAMINANTS_MATRIX_US.md"},
    ],
    "Ni": [{"jurisdiction": "UK", "framework": "Bioavailable EQS in the 2015 WFD Directions",
            "source": "LEGACY_CONTAMINANTS_MATRIX_UK.md section 5"}],
    "Pb": [{"jurisdiction": "UK", "framework": "Bioavailable EQS in the 2015 WFD Directions",
            "source": "LEGACY_CONTAMINANTS_MATRIX_UK.md section 5"}],
    "Mn": [{"jurisdiction": "UK", "framework": "Bioavailable EQS via M-BAT/UKTAG tool",
            "source": "LEGACY_CONTAMINANTS_MATRIX_UK.md section 5"}],
}
_EU_BIOAVAILABILITY_NOTE = {
    "jurisdiction": "EU",
    "framework": "Directive 2013/39/EU Annex I Part B point 3: Member States MAY take bioavailability into account (discretionary, not mandatory)",
    "source": "LEGACY_CONTAMINANTS_MATRIX_EU.md",
}


class MetalDataError(ValueError):
    """Invalid or unusable metal record. Never papered over with a default."""


class BasisMismatchError(MetalDataError):
    """Two values on different concentration bases were combined without an explicit derivation."""


def identify_element(name_or_symbol: str) -> str | None:
    """Return the element symbol for a metal/metalloid name or symbol, else None (not classified, not guessed)."""
    text = (name_or_symbol or "").strip()
    if text in METAL_METALLOID_ELEMENTS:
        return text
    if text.capitalize() in METAL_METALLOID_ELEMENTS and len(text) <= 2:
        return text.capitalize()
    return _NAME_TO_SYMBOL.get(text.lower())


@dataclass(frozen=True)
class MetalMeasurement:
    element: str
    value: float
    unit: str
    basis: str
    medium: str
    source: str
    origin: str = "measured"
    weight_basis: str | None = None  # "dry" or "wet"; required for soil/sediment/biota
    oxidation_state: str | None = None
    species: str | None = None
    method: str | None = None
    date: str | None = None
    jurisdiction: str | None = None
    confidence: str | None = None
    applicability: str | None = None
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.element not in METAL_METALLOID_ELEMENTS:
            raise MetalDataError(f"Element {self.element!r} is not in the metals/metalloids reference set")
        if not isinstance(self.value, (int, float)) or not math.isfinite(self.value) or self.value < 0:
            raise MetalDataError("Concentration must be a finite, non-negative number")
        if self.basis not in BASES:
            raise MetalDataError(f"basis must be one of {BASES}")
        if self.medium not in MEDIA:
            raise MetalDataError(f"medium must be one of {MEDIA}")
        if self.origin not in ORIGINS:
            raise MetalDataError(f"origin must be one of {ORIGINS}")
        if not (self.source or "").strip():
            raise MetalDataError("Every value needs a source")
        if self.medium == "water":
            if self.unit not in _WATER_TO_UG_L:
                raise MetalDataError(f"Water concentrations must use one of {sorted(_WATER_TO_UG_L)}")
            if self.weight_basis is not None:
                raise MetalDataError("weight_basis does not apply to water")
        else:
            if self.unit not in _SOLID_TO_MG_KG:
                raise MetalDataError(f"{self.medium} concentrations must use one of {sorted(_SOLID_TO_MG_KG)}")
            if self.weight_basis not in ("dry", "wet"):
                raise MetalDataError("Solid and biota concentrations must state weight_basis 'dry' or 'wet'; it is never assumed")

    def standard_value(self) -> tuple[float, str]:
        """Value in ug/L (water) or mg/kg (solids). The original value and unit stay on the record."""
        if self.medium == "water":
            return self.value * _WATER_TO_UG_L[self.unit], "ug/L"
        return self.value * _SOLID_TO_MG_KG[self.unit], f"mg/kg {self.weight_basis} weight"


def check_basis_for_criterion(measurement: MetalMeasurement, criterion_basis: str) -> dict[str, Any]:
    """Report whether a measurement is on the basis a criterion requires. Never converts."""
    if criterion_basis not in BASES or criterion_basis == "unknown":
        raise MetalDataError("criterion_basis must be a stated concentration basis")
    if measurement.basis == "unknown":
        return {"status": "BASIS_UNKNOWN", "compatible": False,
                "message": "Measurement basis is unknown; state whether it is total, dissolved, etc. before comparing."}
    if measurement.basis != criterion_basis:
        return {"status": "BASIS_MISMATCH", "compatible": False,
                "message": f"Measured basis is {measurement.basis} but the criterion needs {criterion_basis}. "
                           "No silent conversion: supply a measurement on the required basis or an explicit, sourced derivation."}
    return {"status": "OK", "compatible": True, "message": "Bases match."}


def derive_dissolved_from_total(
    total: MetalMeasurement, dissolved_fraction: float, fraction_source: str,
) -> MetalMeasurement:
    """Explicit, labelled estimate of dissolved metal from total using a user-supplied, sourced fraction."""
    if total.basis != "total" or total.medium != "water":
        raise BasisMismatchError("Derivation requires a total-basis water measurement")
    if not (isinstance(dissolved_fraction, (int, float)) and 0 <= dissolved_fraction <= 1):
        raise MetalDataError("dissolved_fraction must be between 0 and 1")
    if not (fraction_source or "").strip():
        raise MetalDataError("A dissolved fraction needs a source; no default is assumed")
    return replace(
        total, value=total.value * dissolved_fraction, basis="dissolved", origin="estimated",
        assumptions=total.assumptions + (f"dissolved fraction {dissolved_fraction} from {fraction_source}",),
    )


def incremental_over_background(measured: MetalMeasurement, background: MetalMeasurement) -> dict[str, Any]:
    """Show measured, background and incremental side by side. Refuses to mix elements, bases, media or weight bases."""
    for attr in ("element", "basis", "medium", "weight_basis"):
        if getattr(measured, attr) != getattr(background, attr):
            raise BasisMismatchError(f"measured and background differ in {attr}")
    m_val, unit = measured.standard_value()
    b_val, _ = background.standard_value()
    result: dict[str, Any] = {"measured": m_val, "background": b_val, "unit": unit, "basis": measured.basis}
    if m_val > b_val:
        result.update(incremental=m_val - b_val, status="ABOVE_BACKGROUND")
    else:
        result.update(incremental=None, status="AT_OR_BELOW_BACKGROUND")
    return result


def bioavailability_context(element: str, jurisdiction: str | None = None) -> dict[str, Any]:
    """Which sourced bioavailability frameworks exist for this metal. Frameworks only, no thresholds."""
    if element not in METAL_METALLOID_ELEMENTS:
        raise MetalDataError(f"Element {element!r} is not in the metals/metalloids reference set")
    refs = list(BIOAVAILABILITY_REFERENCES.get(element, []))
    refs.append(_EU_BIOAVAILABILITY_NOTE)
    if jurisdiction:
        refs = [r for r in refs if r["jurisdiction"] == jurisdiction]
    return {
        "element": element,
        "references": refs,
        "status": "FRAMEWORK_KNOWN_MODEL_EXTERNAL" if refs else "REGULATORY APPLICABILITY NOT ESTABLISHED",
        "note": "FateIntel does not model bioavailability; use the external tool and import the result with provenance.",
        "confirmed_water_inputs": MBAT_CONFIRMED_WATER_INPUTS,
    }
