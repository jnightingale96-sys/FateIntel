"""Screening water DT50 from the BIOWIN 4 (primary survey) score: DT50 [days] = 10 ** (5 - BIOWIN4).

**Provenance, stated plainly.** This relation was supplied by the project owner (2026-09-24) as a working screening
rule. No literature source has been attached to it. The BIOWIN4 input is meant to be the score from US EPA EPI Suite
(``score_source="epi_suite"``, entered by the user). The app's own BIOWIN4 (``envirodesign``, ``score_source=
"app_reconstruction"``) is only an *approximate open reconstruction* ("not EPA source code or regulatory-equivalent
output") and is flagged as such. Either way the result is a labelled screening estimate, never a measured or published
value, never selected automatically, and only for use when no experimental DT50 exists.

Reading of the formula: the exponent is ``5 - BIOWIN4`` (the request arrived as "10^5-BIOWIN4" with the superscript
lost). That reading has the correct direction -- a higher BIOWIN4 score means faster degradation -- and lines up with the
survey scale's own labels (score 5 ~ hours-to-a-day, 4 ~ days, 3 ~ weeks, 2 ~ months, 1 ~ recalcitrant):
5 -> 1 d, 4 -> 10 d, 3 -> 100 d, 2 -> 1,000 d, 1 -> 10,000 d.

**Temperature.** The BIOWIN survey score carries no stated temperature. The output is therefore recorded as
*temperature-unspecified*. If the owner confirms a reference temperature it can be passed as ``stated_temperature_c`` and
the value is also normalised to the 20 C FOCUS/EFSA reference with the same Arrhenius factor (Ea 65.4 kJ/mol) the soil
provider uses; nothing is assumed otherwise.
"""

from __future__ import annotations

import math
from typing import Any

from .evidence_sources import EvidenceCandidate, _candidate_id
from .soil_dt50 import corrections

FORMULA = "DT50 [days] = 10 ** (5 - BIOWIN4)"
PROVENANCE = "Project-owner screening relation (2026-09-24), no literature source attached; BIOWIN4 score from EPI Suite."
SCORE_SOURCES = ("epi_suite", "app_reconstruction")
# The linear model can leave its 1-5 survey scale; the relation is then an extrapolation, not a prediction.
SCORE_WARN_LOW, SCORE_WARN_HIGH = 1.0, 5.0
SCORE_REJECT_LOW, SCORE_REJECT_HIGH = -2.0, 8.0  # a score this far outside the scale is an input error, not chemistry


def dt50_days_from_biowin4(
    biowin4_score: float, *, score_source: str = "epi_suite", stated_temperature_c: float | None = None,
) -> dict[str, Any]:
    if score_source not in SCORE_SOURCES:
        raise ValueError(f"score_source must be one of {SCORE_SOURCES}")
    if isinstance(biowin4_score, bool) or not isinstance(biowin4_score, (int, float)) or not math.isfinite(biowin4_score):
        raise ValueError("BIOWIN4 score must be a finite number")
    if not SCORE_REJECT_LOW <= biowin4_score <= SCORE_REJECT_HIGH:
        raise ValueError(
            f"BIOWIN4 score {biowin4_score:g} is far outside the model's 1-5 survey scale ({SCORE_REJECT_LOW:g} to "
            f"{SCORE_REJECT_HIGH:g} accepted); check the input"
        )
    dt50 = 10.0 ** (5.0 - float(biowin4_score))
    warnings = [
        "Screening estimate from an unsourced project relation; prefer any measured DT50.",
    ]
    if score_source == "app_reconstruction":
        warnings.append("BIOWIN4 here is the app's approximate open reconstruction, not EPA EPI Suite output; prefer the EPI Suite score.")
    if not SCORE_WARN_LOW <= biowin4_score <= SCORE_WARN_HIGH:
        warnings.append(f"BIOWIN4 score {biowin4_score:g} is outside the 1-5 survey scale: the relation is extrapolated.")
    result: dict[str, Any] = {
        "biowin4_score": float(biowin4_score), "score_source": score_source, "dt50_days": dt50, "formula": FORMULA, "provenance": PROVENANCE,
        "matrix": "water (screening)", "temperature_c": stated_temperature_c,
        "temperature_basis": "stated by the owner" if stated_temperature_c is not None else "unspecified -- the BIOWIN score has no stated temperature",
        "warnings": warnings,
    }
    if stated_temperature_c is not None:
        factor = corrections.temperature_factor(stated_temperature_c)
        result["dt50_days_at_20c"] = None if factor == 0 else dt50 * factor
        result["normalisation"] = "Arrhenius, Ea 65.4 kJ/mol (FOCUS/EFSA), from the stated temperature to 20 C"
    return result


def to_evidence_candidate(estimate: dict[str, Any], *, chemical_name: str, cas_number: str | None = None) -> dict[str, Any]:
    return EvidenceCandidate(
        candidate_id=_candidate_id("biowin4_dt50", chemical_name, estimate["biowin4_score"]),
        source_key="biowin4_dt50_screen", source_name="BIOWIN4-derived screening DT50 (project relation)", source_record_id=None,
        source_url=None, chemical_name=chemical_name, cas_number=cas_number, property_code="FATE.WATER_DT50",
        endpoint_label="Water-phase degradation DT50 (screening estimate)", value=estimate["dt50_days"], unit="days", qualifier="=",
        matrix="surface_water", temperature_c=estimate["temperature_c"], ph=None, guideline=None, evidence_type="model_prediction",
        publication_title=None, publication_year=None, doi=None, pmid=None, pmcid=None, original_source=PROVENANCE,
        rights_status="project_relation_no_third_party_data", import_allowed=True, needs_professional_review=True,
        extraction_status="model_output", snippet=f"{FORMULA} with BIOWIN4 = {estimate['biowin4_score']:.3f}",
        notes=" | ".join([f"temperature: {estimate['temperature_basis']}", *estimate["warnings"]]),
    ).to_dict()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
from fastapi import APIRouter, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

router = APIRouter(prefix="/biowin-dt50", tags=["biodegradation-screen"])


class BiowinDt50Request(BaseModel):
    biowin4_score: float
    score_source: str = "epi_suite"
    stated_temperature_c: float | None = Field(default=None, gt=-50, lt=60)
    chemical_name: str | None = None
    cas_number: str | None = None
    include_evidence_candidate: bool = False


@router.post("/estimate")
def estimate(req: BiowinDt50Request):
    try:
        result = dt50_days_from_biowin4(req.biowin4_score, score_source=req.score_source, stated_temperature_c=req.stated_temperature_c)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if req.include_evidence_candidate:
        result["evidence_candidate"] = to_evidence_candidate(result, chemical_name=req.chemical_name or "unnamed", cas_number=req.cas_number)
    return result
