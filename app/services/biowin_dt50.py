"""Screening DT50 from the BIOWIN 4 (primary survey) score: DT50 [hours, 25 C] = 10 ** (5 - BIOWIN4).

**Provenance, stated plainly.** The relation was supplied by the project owner as a working screening rule; no
literature source is attached. It is the same relation the veterinary module already uses for manure
(``veterinary.biowin_manure_dt50_hours``: 10**(6 - x) / 10 == 10**(5 - x)), so the two agree by construction.

**Unit check (2026-09-24), against EPA's own EPI Suite output** (the "Result Classification" printed under BIOWIN4:
5.00 -> hours, 4.00 -> days, 3.00 -> weeks, 2.00 -> months, 1.00 -> longer). Read in hours the relation gives 1 h, 10 h,
~4 d, ~6 wk, ~14 months for scores 5..1 -- consistent with those labels at both ends. Read in days it gives 1 d, 10 d,
100 d, 2.7 y, 27 y, i.e. one to two classes too slow. The owner's first statement was also "hours". So the unit is hours;
``output_unit="days"`` only converts the same number. The check supports the unit; it does not turn the relation into
a published one.

**Basis (confirmed by the owner 2026-09-24):** the value is at **25 C**.

The input is meant to be the EPI Suite BIOWIN4 score (``score_source="epi_suite"``); the app's own BIOWIN4 is an
approximate open reconstruction and is flagged. A screening estimate only: never a measured or published value, never
selected automatically, only for use when no experimental DT50 exists.

**Region temperature.** The value is re-expressed at a target temperature with the same theta-based correction the
veterinary module uses (theta 1.047, changeable). The target is a parameter per region: ``REGION_TEMPERATURE_C`` holds
only what the owner has stated (EU = 10 C); any other region must be supplied explicitly -- none is guessed.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .evidence_sources import EvidenceCandidate, _candidate_id
from .veterinary import biowin_manure_dt50_hours, correct_dt50_temperature

FORMULA = "DT50 [hours, 25 C] = 10 ** (5 - BIOWIN4)"
PROVENANCE = "Project-owner screening relation (2026-09-24), no literature source attached; BIOWIN4 score from EPI Suite."
SCORE_SOURCES = ("epi_suite", "app_reconstruction")
REFERENCE_TEMPERATURE_C = 25.0
DEFAULT_THETA = 1.047  # same as veterinary.correct_dt50_temperature
# Only owner-stated values; a region not listed here must be given a temperature explicitly.
REGION_TEMPERATURE_C: dict[str, float] = {"EU": 10.0}
MATRIX_PROPERTY_CODE = {"manure": "FATE.MANURE_DT50", "water": "FATE.WATER_DT50"}
UNIT_HOURS_PER = {"hours": 1.0, "days": 24.0}
# The linear model can leave its 1-5 survey scale; the relation is then an extrapolation, not a prediction.
SCORE_WARN_LOW, SCORE_WARN_HIGH = 1.0, 5.0
SCORE_REJECT_LOW, SCORE_REJECT_HIGH = -2.0, 8.0  # a score this far outside the scale is an input error, not chemistry


def dt50_from_biowin4(
    biowin4_score: float, *, score_source: str = "epi_suite", region: str | None = None,
    target_temperature_c: float | None = None, theta: float = DEFAULT_THETA, output_unit: str = "hours",
) -> dict[str, Any]:
    """DT50 at 25 C and, when a region or target temperature is given, at that temperature (explicit value wins)."""

    if score_source not in SCORE_SOURCES:
        raise ValueError(f"score_source must be one of {SCORE_SOURCES}")
    if output_unit not in UNIT_HOURS_PER:
        raise ValueError(f"output_unit must be one of {tuple(UNIT_HOURS_PER)}")
    if isinstance(biowin4_score, bool) or not isinstance(biowin4_score, (int, float)) or not math.isfinite(biowin4_score):
        raise ValueError("BIOWIN4 score must be a finite number")
    if not SCORE_REJECT_LOW <= biowin4_score <= SCORE_REJECT_HIGH:
        raise ValueError(
            f"BIOWIN4 score {biowin4_score:g} is far outside the model's 1-5 survey scale ({SCORE_REJECT_LOW:g} to "
            f"{SCORE_REJECT_HIGH:g} accepted); check the input"
        )
    if target_temperature_c is None and region is not None:
        if region not in REGION_TEMPERATURE_C:
            raise ValueError(f"no reference temperature is recorded for region {region!r}; pass target_temperature_c explicitly")
        target_temperature_c = REGION_TEMPERATURE_C[region]
    if target_temperature_c is not None and not (isinstance(target_temperature_c, (int, float)) and -50 < target_temperature_c < 60):
        raise ValueError("target_temperature_c must be a number between -50 and 60 C")
    unit_h = UNIT_HOURS_PER[output_unit]
    hours_25 = biowin_manure_dt50_hours(float(biowin4_score))
    warnings = ["Screening estimate from an unsourced project relation; prefer any measured DT50."]
    if score_source == "app_reconstruction":
        warnings.append("BIOWIN4 here is the app's approximate open reconstruction, not EPA EPI Suite output; prefer the EPI Suite score.")
    if not SCORE_WARN_LOW <= biowin4_score <= SCORE_WARN_HIGH:
        warnings.append(f"BIOWIN4 score {biowin4_score:g} is outside the 1-5 survey scale: the relation is extrapolated.")
    result: dict[str, Any] = {
        "biowin4_score": float(biowin4_score), "score_source": score_source, "formula": FORMULA, "provenance": PROVENANCE,
        "unit": output_unit, "reference_temperature_c": REFERENCE_TEMPERATURE_C, "dt50_at_reference": hours_25 / unit_h,
        "region": region, "target_temperature_c": target_temperature_c, "theta": theta, "warnings": warnings,
    }
    if target_temperature_c is None:
        result.update(dt50=hours_25 / unit_h, temperature_c=REFERENCE_TEMPERATURE_C)
    else:
        result.update(
            dt50=correct_dt50_temperature(hours_25, REFERENCE_TEMPERATURE_C, float(target_temperature_c), theta) / unit_h,
            temperature_c=float(target_temperature_c),
        )
    return result


def to_evidence_candidate(
    estimate: dict[str, Any], *, chemical_name: str, cas_number: str | None = None, matrix: str = "manure",
) -> dict[str, Any]:
    if matrix not in MATRIX_PROPERTY_CODE:
        raise ValueError(f"matrix must be one of {tuple(MATRIX_PROPERTY_CODE)}")
    code = MATRIX_PROPERTY_CODE[matrix]
    return EvidenceCandidate(
        candidate_id=_candidate_id("biowin4_dt50", chemical_name, estimate["biowin4_score"], matrix, estimate["temperature_c"]),
        source_key="biowin4_dt50_screen", source_name="BIOWIN4-derived screening DT50 (project relation)", source_record_id=None,
        source_url=None, chemical_name=chemical_name, cas_number=cas_number, property_code=code,
        endpoint_label=f"{matrix.capitalize()} DT50 (BIOWIN4 screening estimate)", value=estimate["dt50"], unit=estimate["unit"], qualifier="=",
        matrix=matrix, temperature_c=estimate["temperature_c"], ph=None, guideline=None, evidence_type="model_prediction",
        publication_title=None, publication_year=None, doi=None, pmid=None, pmcid=None, original_source=PROVENANCE,
        rights_status="project_relation_no_third_party_data", import_allowed=True, needs_professional_review=True,
        extraction_status="model_output", snippet=f"{FORMULA} with BIOWIN4 = {estimate['biowin4_score']:.3f}",
        notes=" | ".join([f"25 C value {estimate['dt50_at_reference']:.4g} {estimate['unit']}; theta {estimate['theta']}", *estimate["warnings"]]),
    ).to_dict()


router = APIRouter(prefix="/biowin-dt50", tags=["biodegradation-screen"])


class BiowinDt50Request(BaseModel):
    biowin4_score: float
    score_source: str = "epi_suite"
    region: str | None = None
    target_temperature_c: float | None = Field(default=None, gt=-50, lt=60)
    theta: float = Field(default=DEFAULT_THETA, gt=0)
    output_unit: str = "hours"
    matrix: str = "manure"
    chemical_name: str | None = None
    cas_number: str | None = None
    include_evidence_candidate: bool = False


@router.get("/regions")
def regions():
    return {"region_temperature_c": REGION_TEMPERATURE_C, "note": "Only owner-stated values are listed; other regions need an explicit target_temperature_c."}


@router.post("/estimate")
def estimate(req: BiowinDt50Request):
    try:
        result = dt50_from_biowin4(
            req.biowin4_score, score_source=req.score_source, region=req.region,
            target_temperature_c=req.target_temperature_c, theta=req.theta, output_unit=req.output_unit,
        )
        if req.include_evidence_candidate:
            result["evidence_candidate"] = to_evidence_candidate(
                result, chemical_name=req.chemical_name or "unnamed", cas_number=req.cas_number, matrix=req.matrix,
            )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return result
