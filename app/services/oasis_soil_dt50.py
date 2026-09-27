"""Measured soil DT50 lookup: the "Biodegradation in soil OASIS" database (LMC Bourgas, v1.1, 2009).

218 experimental soil half-lives (215 with a parseable structure, across 208 distinct structures) for mostly-pesticide
chemicals, exported read-only (2026-09-27) from a locally restored QSAR Toolbox 4.9 PostgreSQL database (storehouse
id 22, endpoint path "in soil" / DT50). The underlying study data is attributed row-by-row to a secondary
compilation, RIVM Report No 679101014 (1994) -- this module reports that reference, not the primary studies.

**Licence: UNCONFIRMED**, exactly like the PEPPER provider's embedded EAWAG-SOIL training data
(``soil_dt50.commercial_gate``) -- LMC-donated content bundled inside a vendor database backup, no separate
redistribution terms found. The same gate shape is used here: open for local/development evaluation, closed
elsewhere until an operator confirms a licence. This is real, measured, matrix-specific (soil) data -- it is
deliberately given priority ABOVE PEPPER's prediction in the soil transformation-product "best available" ladder,
consistent with "prefer experimental data where possible".

Matching is by RDKit-canonical SMILES only (no fuzzy/substructure matching, no CAS-only fallback): a wrong match
would silently hand a transformation product someone else's measured half-life.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import Settings, settings
from .evidence_sources import EvidenceCandidate, _candidate_id

PROVIDER_KEY = "oasis_soil_dt50"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "oasis_soil_dt50.json"
CITATION = (
    "\"Biodegradation in soil OASIS\" database, v1.1 (2009), Laboratory of Mathematical Chemistry (LMC), Bourgas, "
    "Bulgaria -- 218 experimental soil DT50 records for 216 compounds, compiled from the \"Biodegradation in soil "
    "OASIS\" collection of 318 observed metabolic maps. Underlying study data attributed to RIVM Report No "
    "679101014 (1994) -- a secondary compilation, not the original studies."
)
_cache: dict[str, Any] | None = None


def commercial_gate(configuration: Settings = settings) -> tuple[bool, str]:
    """Same discipline as ``soil_dt50.commercial_gate``: this data is LMC-donated content of unconfirmed licence."""

    if getattr(configuration, "oasis_soil_dt50_commercial_license_confirmed", False):
        return True, "commercial_licence_confirmed_by_operator"
    if configuration.envirochem_environment in {"local", "test"}:
        return True, "academic_or_development_evaluation_only"
    return False, "oasis_soil_dt50_training_data_licence_required_for_staging_or_production"


def _load(data_path: Path | None = None) -> dict[str, Any]:
    """``data_path=None`` resolves ``DATA_PATH`` dynamically (as a global lookup, not a bound default), so
    monkeypatching this module's ``DATA_PATH`` -- the supported way to point tests at a fixture -- takes effect
    everywhere, including through the API routes below."""

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
        "endpoint": "soil DT50 (aerobic, mostly pesticide chemicals; conditions as reported per study, not normalised)",
        "citation": CITATION,
    }


def _canonical(smiles: str) -> str | None:
    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol is not None else None


def lookup_by_smiles(smiles: str, *, configuration: Settings = settings, data_path: Path | None = None) -> dict[str, Any]:
    """The measured records for one structure, or ``{"found": False, ...}``. Never invents a value for a near match."""

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
        return {"found": False, "available": True, "reason": "no structure match in the OASIS soil DT50 set"}
    means = [r["dt50_mean_days"] for r in records if r["dt50_mean_days"] is not None]
    return {
        "found": True, "available": True, "canonical_smiles": key, "records": records, "n": len(records),
        "dt50_mean_days": sum(means) / len(means) if means else None,  # arithmetic mean across duplicate records
        "citation": CITATION,
    }


def lookup_by_inchikey(inchikey: str, *, configuration: Settings = settings, data_path: Path | None = None) -> dict[str, Any]:
    """Same as ``lookup_by_smiles``, but keyed by InChIKey -- for callers (the Identification screen) that have an
    InChIKey and no SMILES to hand. Built from the same conversion script's ``by_inchikey`` index."""

    gate_open, licence_status = commercial_gate(configuration)
    if not gate_open:
        return {"found": False, "available": False, "reason": f"closed outside local/test evaluation: {licence_status}"}
    if not availability(data_path)["available"]:
        return {"found": False, "available": False, "reason": "data file missing"}
    key = (inchikey or "").strip()
    if not key:
        return {"found": False, "available": True, "reason": "an InChIKey is required"}
    records = _load(data_path)["by_inchikey"].get(key)
    if not records:
        return {"found": False, "available": True, "reason": "no structure match for this InChIKey"}
    means = [r["dt50_mean_days"] for r in records if r["dt50_mean_days"] is not None]
    return {
        "found": True, "available": True, "inchikey": key, "records": records, "n": len(records),
        "dt50_mean_days": sum(means) / len(means) if means else None, "citation": CITATION,
    }


def to_evidence_candidate(result: dict[str, Any], *, chemical_name: str, cas_number: str | None = None) -> dict[str, Any]:
    if not result.get("found"):
        raise ValueError("to_evidence_candidate requires a found=True lookup result")
    record = result["records"][0]
    return EvidenceCandidate(
        candidate_id=_candidate_id("oasis_soil_dt50", result["canonical_smiles"], result["dt50_mean_days"]),
        source_key=PROVIDER_KEY, source_name="Biodegradation in soil OASIS (LMC Bourgas)", source_record_id=record.get("record_id"),
        source_url=None, chemical_name=chemical_name, cas_number=cas_number or record.get("cas_number"),
        property_code="FATE.SOIL_DT50", endpoint_label="Soil DT50 (measured)", value=result["dt50_mean_days"], unit="days",
        qualifier="=", matrix="soil", temperature_c=None, ph=None, guideline=None, evidence_type="database_record",
        publication_title=None, publication_year=1994, doi=None, pmid=None, pmcid=None,
        original_source="RIVM Report No 679101014 (1994), via " + CITATION,
        rights_status="third_party_data_licence_unconfirmed", import_allowed=True, needs_professional_review=True,
        extraction_status="structured_database_field",
        snippet=f"Soil DT50 mean {result['dt50_mean_days']:.3g} d across {result['n']} record(s)" + (f"; names: {record['names']}" if record.get("names") else ""),
        notes="Study conditions are as reported per record, not normalised to a reference temperature or moisture.",
    ).to_dict()


router = APIRouter(prefix="/oasis-soil-dt50", tags=["biodegradation-screen"])


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
