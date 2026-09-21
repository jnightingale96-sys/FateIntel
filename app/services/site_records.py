"""Glue between saved metal measurements and a saved conceptual site model.

A measurement feeds a site model's "measured data" flag only when its element matches a contaminant in the
model (by name or symbol) and it states which site-model medium it represents. Anything that cannot be linked
is reported back, never silently dropped or guessed.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Iterable

from .conceptual_site_model import MEDIA, ConceptualSiteModel
from .metals import MetalDataError, MetalMeasurement, identify_element

_OPTIONAL = ("oxidation_state", "species", "method", "jurisdiction", "confidence", "applicability")


def measurement_from_payload(data: dict[str, Any]) -> tuple[MetalMeasurement, str | None]:
    """Validate a JSON payload into a MetalMeasurement plus its optional site_medium. Raises MetalDataError."""
    element = data.get("element")
    if identify_element(str(element or "")) != element:
        raise MetalDataError("element must be a metal/metalloid chemical symbol, for example 'Pb'")
    site_medium = data.get("site_medium")
    if site_medium is not None and site_medium not in MEDIA:
        raise MetalDataError(f"site_medium must be one of {MEDIA}")
    try:
        measurement = MetalMeasurement(
            element=element, value=data["value"], unit=data["unit"], basis=data["basis"],
            medium=data["medium"], source=data.get("source", ""),
            origin=data.get("origin", "measured"), weight_basis=data.get("weight_basis"),
            date=data.get("date"), assumptions=tuple(data.get("assumptions", ())),
            **{k: data.get(k) for k in _OPTIONAL},
        )
    except KeyError as exc:
        raise MetalDataError(f"Missing required field {exc}") from exc
    return measurement, site_medium


def record_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id, "project_id": row.project_id, "element": row.element, "value": row.value,
        "unit": row.unit, "basis": row.basis, "medium": row.medium, "weight_basis": row.weight_basis,
        "source": row.source, "origin": row.origin, "oxidation_state": row.oxidation_state,
        "species": row.species, "method": row.method, "date": row.measured_date,
        "jurisdiction": row.jurisdiction, "confidence": row.confidence, "applicability": row.applicability,
        "assumptions": json.loads(row.assumptions_json or "[]"), "site_medium": row.site_medium,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def merge_measured(
    model: ConceptualSiteModel, measurements: Iterable[Any],
) -> tuple[ConceptualSiteModel, dict[str, Any]]:
    """Return the model with `measured` extended from saved measurements, and a report of what was linked."""
    element_by_contaminant: dict[str, str] = {}
    for source in model.sources:
        for contaminant in source.contaminants:
            element = identify_element(contaminant.name)
            if element and contaminant.contaminant_group == "metal_inorganic":
                element_by_contaminant[contaminant.name] = element

    measured = {medium: set(names) for medium, names in model.measured.items()}
    linked: list[dict[str, Any]] = []
    unlinked: list[dict[str, Any]] = []
    for row in measurements:
        names = [n for n, el in element_by_contaminant.items() if el == row.element]
        if row.site_medium is None:
            unlinked.append({"measurement_id": row.id, "element": row.element,
                             "reason": "site_medium not set; state which site-model medium this sample represents"})
        elif not names:
            unlinked.append({"measurement_id": row.id, "element": row.element,
                             "reason": "no metal contaminant for this element in the site model"})
        else:
            for name in names:
                measured.setdefault(row.site_medium, set()).add(name)
                linked.append({"measurement_id": row.id, "contaminant": name,
                               "medium": row.site_medium, "basis": row.basis})
    merged = replace(model, measured={m: tuple(sorted(n)) for m, n in measured.items()})
    return merged, {"linked_measurements": linked, "unlinked_measurements": unlinked}
