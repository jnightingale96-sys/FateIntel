"""FastAPI router for the soil DT50 provider.

    POST /api/providers/soil-dt50/predict       batch prediction (+ optional site correction, evidence candidate)
    POST /api/providers/soil-dt50/correct       move a known reference DT50 to site conditions (no model needed)
    GET  /api/providers/soil-dt50/model-card    provenance, validation metrics, domain
    GET  /api/providers/soil-dt50/capabilities  licence gate, missing dependencies

``correct`` needs no heavy dependency and no licence: it is FOCUS/EFSA arithmetic. ``predict`` and ``model-card``
need the model artifact, so they are refused (403) when the licence gate is closed and 503 when a dependency is missing.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from ...config import settings
from . import availability, capabilities, commercial_gate, corrections
from .evidence import to_evidence_candidate

router = APIRouter(prefix="/soil-dt50", tags=["soil-degradation"])

MAX_BATCH = 500


class ChemicalIn(BaseModel):
    smiles: str = Field(min_length=1, max_length=2000)
    id: str | None = None
    name: str | None = None
    cas_number: str | None = None


class ConditionsIn(BaseModel):
    temperature_c: float | None = Field(None, description="Mean soil temperature, degC")
    moisture: float | None = Field(None, gt=0, description="Soil moisture (same units as moisture_ref)")
    moisture_ref: float | None = Field(None, gt=0, description="Moisture at pF2 / field capacity")
    depth_cm: float | None = Field(None, ge=0, description="Depth for the FOCUS depth factor")
    ea_j_mol: float = Field(corrections.EA_DEFAULT, gt=0)
    walker_b: float = Field(corrections.B_WALKER_DEFAULT, ge=0)


class PredictRequest(BaseModel):
    chemicals: list[ChemicalIn] = Field(..., min_length=1)
    conditions: ConditionsIn | None = None
    regime: Literal["REACH", "EU_PPP", "Stockholm"] = "REACH"
    threshold_P_days: float | None = Field(None, gt=0)
    threshold_vP_days: float | None = Field(None, gt=0)
    sigma_between_soils: float | None = Field(None, ge=0, le=2)
    prefer_experimental: bool = True
    strip_counterions: bool = True
    include_evidence_candidate: bool = False


class CorrectRequest(BaseModel):
    dt50_ref_days: float = Field(..., gt=0)
    conditions: ConditionsIn


def _require_model() -> None:
    gate_open, licence_status = commercial_gate()
    if not settings.soil_dt50_enabled:
        raise HTTPException(403, "The soil DT50 provider is disabled by configuration.")
    if not gate_open:
        raise HTTPException(403, f"Soil DT50 model is closed outside local/test evaluation: {licence_status}.")
    avail = availability()
    if not avail["available"]:
        raise HTTPException(503, f"Soil DT50 dependencies missing: {', '.join(avail['missing'])}")


@router.get("/capabilities")
def provider_capabilities():
    return capabilities()


@router.post("/predict")
async def predict(req: PredictRequest):
    if len(req.chemicals) > MAX_BATCH:
        raise HTTPException(413, f"max {MAX_BATCH} chemicals per request")
    _require_model()
    from .predictor import SiteConditions, get_predictor

    thresholds = (req.threshold_P_days, req.threshold_vP_days) if req.threshold_P_days else None
    conditions = SiteConditions(**req.conditions.model_dump()) if req.conditions else None
    predictor = get_predictor()
    # PaDEL runs a JVM subprocess -- keep it off the event loop.
    results = await run_in_threadpool(
        predictor.predict, [c.model_dump(include={"smiles", "id", "name"}) for c in req.chemicals], conditions,
        req.regime, thresholds, req.sigma_between_soils, req.prefer_experimental, req.strip_counterions,
    )
    gate_open, _ = commercial_gate()
    rows = []
    for chemical, result in zip(req.chemicals, results):
        row = result.to_dict()
        if req.include_evidence_candidate:
            row["evidence_candidate"] = to_evidence_candidate(
                row, chemical_name=chemical.name or chemical.smiles, cas_number=chemical.cas_number, import_allowed=gate_open,
            )
        rows.append(row)
    return {"results": rows, "model": predictor.meta["version"]}


@router.post("/correct")
def correct(req: CorrectRequest):
    c = req.conditions
    dt50, factors = corrections.to_site_conditions(
        req.dt50_ref_days, temp_c=c.temperature_c, theta=c.moisture, theta_ref=c.moisture_ref,
        depth_cm=c.depth_cm, ea=c.ea_j_mol, b=c.walker_b,
    )
    warnings = []
    if (c.moisture is None) != (c.moisture_ref is None):
        warnings.append("moisture correction NOT applied: it needs both moisture and moisture_ref (same units)")
    return {
        "DT50_site_days": None if dt50 == float("inf") else dt50, "factors": factors,
        "no_degradation": dt50 == float("inf"), "warnings": warnings,
    }


@router.get("/model-card")
def model_card():
    _require_model()
    from .predictor import get_predictor

    return get_predictor().model_card()
