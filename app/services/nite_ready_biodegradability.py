"""Measured microbial mineralization / ready-biodegradability lookup: the "Biodegradation NITE" database.

1,373 experimental records for 1,373 distinct structures, exported read-only (2026-09-27) from a locally restored
QSAR Toolbox 4.9 PostgreSQL database (storehouse "Biodegradation NITE", endpoint path "in water: screening tests").
The database holds biodegradation test data for existing chemicals under Japan's Chemical Substances Control Law
(CSCL), run by METI (Ministry of Economy, Trade and Industry, Japan) to OECD Test Guidelines 301C, 301D, 302C or
302D. Each record is **biodegradation expressed as the percentage of observed oxygen uptake to theoretical oxygen
demand (BOD, %)** over a stated duration (mostly 28 days for 301C, the "Modified MITI Test (I)") -- a measure of
aerobic microbial MINERALIZATION (respiration to CO2/H2O), not a soil DT50 and not a transformation-product pathway.

**Licence: UNCONFIRMED**, exactly like the PEPPER and OASIS-soil-DT50 providers -- a vendor-donated database bundled
inside a Toolbox database backup, no separate redistribution terms found. Same gate shape: open for local/
development evaluation, closed elsewhere until an operator confirms a licence.

**No pass/fail "readily biodegradable" classification is applied here.** OECD 301 guidance defines a numeric
pass threshold (commonly cited as >=60% for an O2-consumption/CO2-evolution test, reached within a 10-day window
of the 28-day test), but that criterion has not been read in primary text in this project, so it is not encoded --
the raw percentage, duration and guideline are reported and nothing more. Matching is by RDKit-canonical SMILES only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import Settings, settings
from .evidence_sources import EvidenceCandidate, _candidate_id

PROVIDER_KEY = "nite_ready_biodegradability"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "nite_ready_biodegradability.json"
CITATION = (
    "\"Biodegradation NITE\" database, Laboratory of Mathematical Chemistry (LMC) / METI (Japan) -- biodegradation "
    "test data for existing chemicals under the Japanese Chemical Substances Control Law (CSCL), OECD TG 301C/301D/"
    "302C/302D, expressed as % of theoretical oxygen demand consumed (microbial mineralization)."
)
_cache: dict[str, Any] | None = None


def commercial_gate(configuration: Settings = settings) -> tuple[bool, str]:
    """Same discipline as ``oasis_soil_dt50.commercial_gate``: unconfirmed-licence vendor-donated content."""

    if getattr(configuration, "nite_ready_biodegradability_commercial_license_confirmed", False):
        return True, "commercial_licence_confirmed_by_operator"
    if configuration.envirochem_environment in {"local", "test"}:
        return True, "academic_or_development_evaluation_only"
    return False, "nite_ready_biodegradability_licence_required_for_staging_or_production"


def _load(data_path: Path | None = None) -> dict[str, Any]:
    global _cache
    path = data_path if data_path is not None else DATA_PATH
    if _cache is None or _cache.get("_path") != str(path):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_path"] = str(path)
        _cache = data
    return _cache


def availability(data_path: Path | None = None) -> dict[str, Any]:
    path = data_path if data_path is not None else DATA_PATH
    return {"available": path.is_file(), "missing": [] if path.is_file() else [str(path)]}


def capabilities(configuration: Settings = settings, *, data_path: Path | None = None) -> dict[str, Any]:
    gate_open, licence_status = commercial_gate(configuration)
    avail = availability(data_path)
    record_count = sum(len(v) for v in _load(data_path)["records"].values()) if avail["available"] else 0
    return {
        "provider_key": PROVIDER_KEY, "enabled": bool(avail["available"] and gate_open), "licence_status": licence_status,
        **avail, "structure_count": len(_load(data_path)["records"]) if avail["available"] else 0, "record_count": record_count,
        "endpoint": "microbial mineralization / ready biodegradability (% theoretical oxygen demand, OECD 301C/301D/302C/302D)",
        "citation": CITATION,
    }


def _canonical(smiles: str) -> str | None:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol is not None else None


def lookup_by_smiles(smiles: str, *, configuration: Settings = settings, data_path: Path | None = None) -> dict[str, Any]:
    """The measured mineralization records for one structure, or ``{"found": False, ...}``."""

    gate_open, licence_status = commercial_gate(configuration)
    if not gate_open:
        return {"found": False, "available": False, "reason": f"closed outside local/test evaluation: {licence_status}"}
    if not availability(data_path)["available"]:
        return {"found": False, "available": False, "reason": "data file missing"}
    key = _canonical(smiles)
    if key is None:
        return {"found": False, "available": True, "reason": "SMILES could not be parsed"}
    records = _load(data_path)["records"].get(key)
    if not records:
        return {"found": False, "available": True, "reason": "no structure match in the NITE ready-biodegradability set"}
    percents = [r["biodeg_percent"] for r in records if r["biodeg_percent"] is not None]
    return {
        "found": True, "available": True, "canonical_smiles": key, "records": records, "n": len(records),
        "biodeg_percent_mean": sum(percents) / len(percents) if percents else None,
        "citation": CITATION,
    }


def to_evidence_candidate(result: dict[str, Any], *, chemical_name: str, cas_number: str | None = None) -> dict[str, Any]:
    if not result.get("found"):
        raise ValueError("to_evidence_candidate requires a found=True lookup result")
    record = result["records"][0]
    duration = record.get("duration_days")
    return EvidenceCandidate(
        candidate_id=_candidate_id("nite_ready_biodegradability", result["canonical_smiles"], result["biodeg_percent_mean"]),
        source_key=PROVIDER_KEY, source_name="Biodegradation NITE (METI Japan, OECD TG 301/302)", source_record_id=record.get("record_id"),
        source_url=None, chemical_name=chemical_name, cas_number=cas_number or record.get("cas_number"),
        property_code="FATE.BIODEGRADATION", endpoint_label="Ready biodegradability / mineralization (% ThOD, measured)",
        value=result["biodeg_percent_mean"], unit="%", qualifier="=", matrix="aqueous_screening_test", temperature_c=None, ph=None,
        guideline=record.get("test_guideline"), evidence_type="database_record", publication_title=None,
        publication_year=int(record["year"]) if (record.get("year") or "").isdigit() else None, doi=None, pmid=None, pmcid=None,
        original_source=CITATION, rights_status="third_party_data_licence_unconfirmed", import_allowed=True,
        needs_professional_review=True, extraction_status="structured_database_field",
        snippet=(f"{result['biodeg_percent_mean']:.3g}% of theoretical oxygen demand across {result['n']} record(s)"
                 + (f" over {duration:g} d" if duration is not None else "")),
        notes="A ready-biodegradability screening percentage (microbial mineralization via O2 consumption), not a soil or water DT50; no pass/fail threshold is applied here.",
    ).to_dict()


router = APIRouter(prefix="/nite-ready-biodegradability", tags=["biodegradation-screen"])


@router.get("/capabilities")
def get_capabilities():
    return capabilities()


@router.get("/lookup")
def get_lookup(smiles: str, chemical_name: str | None = None, cas_number: str | None = None, include_evidence_candidate: bool = False):
    try:
        result = lookup_by_smiles(smiles)
    except Exception as exc:  # noqa: BLE001 - a malformed request should not 500
        raise HTTPException(422, str(exc)) from exc
    if include_evidence_candidate and result.get("found"):
        result["evidence_candidate"] = to_evidence_candidate(result, chemical_name=chemical_name or "unnamed", cas_number=cas_number)
    return result
