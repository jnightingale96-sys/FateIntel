"""Local query connector for the EPA ECOTOX Knowledgebase bulk-import reference file.

Reads the JSONL + index pair produced by ``scripts/import_ecotox.py`` (see that script's own
docstring for the full scope/filtering rationale -- aquatic-medium LC50/EC50/NOEC/EC10 records
only). Neither file is shipped in git; this module returns an honest "not imported" status,
never a silent empty result, when they are missing.

Returned candidates reuse ``evidence_sources.EvidenceCandidate`` and slot into
``search_sources()``'s existing dispatch exactly like the pubchem/europe_pmc connectors --
every candidate still goes through the same "no machine-extracted value is auto-selected"
review rule, since a real ECOTOX record is still one study's result, not a chosen PNEC input.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from . import evidence_sources
from .evidence_sources import EvidenceCandidate, _candidate_id

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_JSONL_PATH = BASE_DIR / "data" / "ecotox_reference.jsonl"
DEFAULT_INDEX_PATH = BASE_DIR / "data" / "ecotox_index.json"

_ENDPOINT_TO_PROPERTY_CODE = {
    "LC50": "ECOTOX.AQUATIC.LC50",
    "EC50": "ECOTOX.AQUATIC.EC50",
    "NOEC": "ECOTOX.AQUATIC.NOEC",
    "EC10": "ECOTOX.AQUATIC.EC10",
}


# ECOTOX's "aquatic" media filter (see scripts/import_ecotox.py) selects tests by MEDIUM, not by how the dose was
# expressed. A random-chemical validation run over 3,140 candidates (2026-09-23) found the reported unit is an
# aqueous mass concentration for 79%, a molar concentration for 14%, and something else entirely for 7% (dietary
# g/kg diet, body-weight mg/kg bdwt, injected ug/cell, neq/g, %, ...) -- values that carry an "Aquatic LC50" label but
# are not aqueous concentrations and must never feed an aquatic PNEC. Candidates are kept (nothing is dropped) but
# the unit basis is now stated on each one.
_MASS_CONCENTRATION_UNITS = {"ng/L", "ug/L", "mg/L", "g/L", "ppt", "ppb", "ppm", "ng/ml", "ug/ml", "mg/ml"}
_MOLAR_UNITS = {"nM", "uM", "mM", "M", "nmol/L", "umol/L", "mmol/L", "mol/L"}


def unit_advisory(unit: str | None) -> str | None:
    """None for an aqueous mass concentration; otherwise a plain statement of what the unit basis is."""

    if unit is None or not str(unit).strip():
        return "UNIT NOT REPORTED: the value cannot be interpreted as a concentration."
    bare = str(unit).strip()
    if bare.startswith("AI "):
        bare = bare[3:].strip()
    if bare in _MASS_CONCENTRATION_UNITS:
        return None
    if bare in _MOLAR_UNITS:
        return (
            f"MOLAR UNIT ({unit}): convert to a mass concentration with the substance's molecular weight before "
            "use; it is not directly usable as a mass-based (mg/L) endpoint."
        )
    return (
        f"NOT AN AQUEOUS CONCENTRATION (unit '{unit}' is a dietary, body-weight, percent or other basis): kept for "
        "completeness, but do not use as an aquatic PNEC input."
    )


_MOLAR_TO_MOL_PER_L = {"nM": 1e-9, "uM": 1e-6, "mM": 1e-3, "M": 1.0, "nmol/L": 1e-9, "umol/L": 1e-6, "mmol/L": 1e-3, "mol/L": 1.0}


def molar_to_mg_per_l(value: float | None, unit: str | None, molecular_weight_g_mol: float | None) -> float | None:
    """mg/L equivalent of a molar aqueous concentration, or None when it cannot be computed honestly.

    Needs a reported value, a recognised molar unit and a positive molecular weight. The original value and unit
    are never replaced; the conversion is only ever offered alongside them.
    """

    if value is None or unit is None or not molecular_weight_g_mol or molecular_weight_g_mol <= 0:
        return None
    bare = str(unit).strip()
    if bare.startswith("AI "):
        bare = bare[3:].strip()
    factor = _MOLAR_TO_MOL_PER_L.get(bare)
    return None if factor is None else float(value) * factor * float(molecular_weight_g_mol) * 1000.0


def is_imported(index_path: Path = DEFAULT_INDEX_PATH, jsonl_path: Path = DEFAULT_JSONL_PATH) -> bool:
    return index_path.exists() and jsonl_path.exists()


def _load_index(index_path: Path) -> dict[str, Any]:
    return json.loads(index_path.read_text(encoding="utf-8"))


def _record_to_candidate(record: dict[str, Any], *, chemical_name: str, molecular_weight_g_mol: float | None = None) -> EvidenceCandidate | None:
    property_code = _ENDPOINT_TO_PROPERTY_CODE.get(record.get("endpoint") or "")
    if property_code is None:
        return None
    reference_bits = [
        record.get("reference_author"),
        record.get("reference_title"),
        record.get("reference_source"),
    ]
    snippet_parts = [
        f"{record.get('endpoint')} = {record.get('conc1_mean')} {record.get('conc1_unit')}"
        if record.get("conc1_mean") is not None else None,
        f"species: {record.get('species_latin_name') or record.get('species_common_name')}"
        if record.get("species_latin_name") or record.get("species_common_name") else None,
        f"effect: {record.get('effect')}" if record.get("effect") else None,
        f"duration: {record.get('obs_duration_mean')} {record.get('obs_duration_unit')}"
        if record.get("obs_duration_mean") is not None else None,
    ]
    snippet = " | ".join(part for part in snippet_parts if part)

    return EvidenceCandidate(
        candidate_id=_candidate_id("epa_ecotox", record.get("result_id"), property_code, record.get("cas_number")),
        source_key="epa_ecotox",
        source_name="US EPA ECOTOX Knowledgebase",
        source_record_id=record.get("result_id"),
        source_url=record.get("source_url"),
        chemical_name=record.get("chemical_name") or chemical_name,
        cas_number=record.get("cas_number"),
        property_code=property_code,
        endpoint_label=property_code.rsplit(".", 1)[-1],
        value=record.get("conc1_mean"),
        unit=record.get("conc1_unit"),
        qualifier="=",
        matrix=record.get("media_type"),
        temperature_c=None,
        ph=None,
        guideline=None,
        evidence_type="database_record",
        publication_title=record.get("reference_title"),
        publication_year=int(record["reference_year"]) if (record.get("reference_year") or "").isdigit() else None,
        doi=record.get("reference_doi"),
        pmid=None,
        pmcid=None,
        original_source=" ".join(bit for bit in reference_bits if bit) or None,
        rights_status="public_government_data",
        import_allowed=True,
        needs_professional_review=True,
        extraction_status="structured_database_field",
        snippet=snippet,
        notes=(
            (f"{advisory} " if (advisory := unit_advisory(record.get("conc1_unit"))) else "")
            + (f"Equivalent mass concentration ~ {mg_l:.6g} mg/L (converted from {record.get('conc1_mean')} {record.get('conc1_unit')} using MW {molecular_weight_g_mol:g} g/mol; the reported value and unit above are unchanged). " if (mg_l := molar_to_mg_per_l(record.get("conc1_mean"), record.get("conc1_unit"), molecular_weight_g_mol)) is not None else "")
            + f"species: {record.get('species_latin_name') or 'not reported'}; "
            f"ecotox group: {record.get('species_ecotox_group') or 'not reported'}; "
            f"exposure_type: {record.get('exposure_type') or 'not reported'}; "
            f"test_location: {record.get('test_location') or 'not reported'}"
        ),
    )


def search_ecotox_local(
    chemical_name: str,
    *,
    cas_number: str | None,
    endpoint_codes: Iterable[str] | None = None,
    limit: int = 20,
    molecular_weight_g_mol: float | None = None,
    jsonl_path: Path = DEFAULT_JSONL_PATH,
    index_path: Path = DEFAULT_INDEX_PATH,
) -> dict[str, Any]:
    """Look up locally-imported ECOTOX aquatic LC50/EC50/NOEC/EC10 records by CAS number.

    Mirrors the ``{source_key, status, candidates, warnings}`` shape every other connector in
    ``search_sources()`` returns. Requires ``cas_number`` -- the import is CAS-indexed and does
    not currently support a chemical-name-only lookup (unlike pubchem/europe_pmc, which can
    resolve a name themselves).
    """

    if not is_imported(index_path, jsonl_path):
        return {
            "source_key": "epa_ecotox", "status": "not_imported", "candidates": [],
            "warnings": [
                "EPA ECOTOX has not been imported locally yet. Run "
                "`python scripts/import_ecotox.py --source path/to/ecotox_ascii_MM_DD_YYYY/` "
                "against a fresh download from https://cfpub.epa.gov/ecotox/ first."
            ],
        }
    if not cas_number:
        return {
            "source_key": "epa_ecotox", "status": "cas_number_required", "candidates": [],
            "warnings": ["The local ECOTOX import is indexed by CAS number; a chemical name alone can't be looked up."],
        }

    index = _load_index(index_path)
    offsets: list[int] = index.get("offsets", {}).get(cas_number, [])
    if not offsets:
        return {"source_key": "epa_ecotox", "status": "no_match", "candidates": [], "warnings": []}

    wanted_codes = set(endpoint_codes) if endpoint_codes else None
    candidates: list[dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8", newline="\n") as handle:
        for offset in offsets:
            if len(candidates) >= limit:
                break
            handle.seek(offset)
            record = json.loads(handle.readline())
            candidate = _record_to_candidate(record, chemical_name=chemical_name, molecular_weight_g_mol=molecular_weight_g_mol)
            if candidate is None:
                continue
            if wanted_codes is not None and candidate.property_code not in wanted_codes:
                continue
            candidates.append(candidate.to_dict())

    return {
        "source_key": "epa_ecotox", "status": "ok" if candidates else "no_match",
        "candidates": candidates, "warnings": [],
        "total_available": len(offsets),
    }
