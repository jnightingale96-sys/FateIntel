"""Analytical identification: how a researcher would actually find a chemical in a sample.

Three real, open sources -- deliberately kept separate from `evidence_sources.py`, whose
`EvidenceCandidate` shape is built for scalar fate/ecotox endpoint values, not structural or
spectral identification data:

- NORMAN SusDat (S0) -- OPERA-model-predicted ESI ionisation mode, precursor M+H+/M-H- mass, and
  chromatographic platform, for essentially any substance with a known structure. A static,
  slimmed, indexed snapshot (`app/data/norman_susdat_reference.jsonl` + `norman_susdat_index.json`,
  built by `scripts/convert_norman_references.py`) -- SusDat covers ~109k substances, too large to
  load as one in-memory dict, so only a small inchikey->byte-offset index is kept in memory and a
  lookup seeks straight to its one line.
- NORMAN EAWAGTPS (S66) -- real, curated parent/transformation-product pairs from Eawag. A static
  snapshot (`app/data/eawag_transformation_products.json`, ~165 KB, small enough to load whole).
  Every entry is a documented pair; nothing here is predicted.
- MassBank Europe -- an open, unauthenticated REST API returning real, measured MS2 product-ion
  spectra plus the chromatography metadata (retention time, column, mobile phase, ionisation mode)
  recorded with each spectrum. Live-verified 2026-09-08 against
  `https://massbank.eu/MassBank-api/records?inchi_key=...`: response is a bare JSON list of record
  objects (not wrapped in an envelope key); the fields this module reads --
  `compound.{formula,mass,smiles,inchi,link}`, `acquisition.{instrument,instrument_type,
  mass_spectrometry.{ms_type,ion_mode,subtags},chromatography}` (chromatography and subtags are
  lists of `{"subtag": ..., "value": ...}` pairs, not a flat dict), `mass_spectrometry.focused_ion`
  (same subtag/value shape), and `peak.{numPeak,peak.values}` (each value a `{mz,intensity,rel}`
  object) -- were all read directly off a real response for carbamazepine (64 records), not
  assumed from documentation. `https://massbank.eu/MassBank/RecordDisplay?id={accession}` was
  confirmed live to render that exact record.

Every lookup returns either a real match with its source, or an explicit "not in this reference
set" / "no reference spectrum found" result -- never a fabricated m/z, retention time or
transformation product standing in for one that is simply absent from these sources.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from ..config import Settings, settings
from ..exceptions import ExternalDataSourceError, ExternalModelUnavailableError

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

SOURCE_REGISTRY_PATH = DATA_DIR / "analytical_source_registry.json"
SOURCE_REGISTRY: list[dict[str, Any]] = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
_SOURCE_BY_KEY = {row["key"]: row for row in SOURCE_REGISTRY}

EAWAGTPS_PATH = DATA_DIR / "eawag_transformation_products.json"
_EAWAGTPS: dict[str, Any] = json.loads(EAWAGTPS_PATH.read_text(encoding="utf-8"))
_EAWAGTPS_BY_PARENT: dict[str, list[dict[str, Any]]] = _EAWAGTPS["by_parent_inchikey"]

# A second known-transformation-product source: real, curated precursor -> product structure pairs from the
# "Observed Microbial metabolism" database (LMC Bourgas + US EPA, METAPATH platform; largely UM-BBD and literature
# derived, mostly aerobic general biodegradation -- not soil-specific), exported read-only (2026-09-27) from a
# locally restored QSAR Toolbox 4.9 database. Licence UNCONFIRMED, same gate discipline as PEPPER/oasis_soil_dt50 --
# see analytical_source_registry.json's "oasis_observed_microbial_metabolism" entry and
# scripts/convert_observed_microbial_metabolism.py for the full provenance. Keyed by the PRECURSOR's InChIKey (which
# may itself be a pathway intermediate, not only a root parent), so re-querying a returned TP's own InChIKey follows
# the chain, exactly like NORMAN EAWAGTPS.
OBSERVED_MICROBIAL_METABOLISM_PATH = DATA_DIR / "observed_microbial_metabolism.json"
_OBSERVED_MICROBIAL_METABOLISM: dict[str, Any] = json.loads(OBSERVED_MICROBIAL_METABOLISM_PATH.read_text(encoding="utf-8"))
_OBSERVED_MICROBIAL_METABOLISM_BY_PARENT: dict[str, list[dict[str, Any]]] = _OBSERVED_MICROBIAL_METABOLISM["by_parent_inchikey"]
OBSERVED_MICROBIAL_METABOLISM_CITATION = (
    "\"Observed Microbial metabolism\" database, Laboratory of Mathematical Chemistry (LMC), Bourgas, with US EPA "
    "(ORD/NERL, ORD/NHEERL/MED), METAPATH platform -- real observed precursor/product pairs, largely from UM-BBD "
    "and the literature. Licence unconfirmed; no formation-fraction/yield data for almost all pairs."
)

SUSDAT_INDEX_PATH = DATA_DIR / "norman_susdat_index.json"
_SUSDAT_INDEX: dict[str, Any] = json.loads(SUSDAT_INDEX_PATH.read_text(encoding="utf-8"))
SUSDAT_DATA_PATH = DATA_DIR / _SUSDAT_INDEX["data_file"]

MASSBANK_CITATION = "MassBank Europe -- open reference mass spectral database. https://massbank.eu/"
MAX_MASSBANK_SPECTRA = 25
MAX_PRODUCT_IONS_PER_SPECTRUM = 100
MAX_PROVIDER_RESPONSE_BYTES = 8 * 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_registry() -> list[dict[str, Any]]:
    return SOURCE_REGISTRY


def ionisation_and_platform(inchikey: str) -> dict[str, Any]:
    """OPERA-predicted ESI mode, precursor ion mass and platform recommendation from NORMAN SusDat."""
    key = (inchikey or "").strip()
    if not key:
        raise ValueError("An InChIKey is required")

    offset = _SUSDAT_INDEX["offsets"].get(key)
    if offset is None:
        return {
            "found": False,
            "inchikey": key,
            "message": "This substance is not in the NORMAN SusDat reference snapshot.",
            "source_key": "norman_susdat",
        }

    with SUSDAT_DATA_PATH.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        record = json.loads(handle.readline())

    return {
        "found": True,
        "inchikey": key,
        "predicted_esi_mode": record.get("predicted_esi_mode"),
        "probability_positive_esi": record.get("probability_positive_esi"),
        "probability_negative_esi": record.get("probability_negative_esi"),
        "precursor_m_plus_h_da": record.get("precursor_m_plus_h_da"),
        "precursor_m_minus_h_da": record.get("precursor_m_minus_h_da"),
        "predicted_chromatography": record.get("predicted_chromatography"),
        "probability_gc": record.get("probability_gc"),
        "probability_rplc": record.get("probability_rplc"),
        "preferable_platform": record.get("preferable_platform"),
        "evidence_status": "model_predicted",
        "source_key": "norman_susdat",
        "source_url": record.get("source_url"),
        "citation": _SOURCE_BY_KEY["norman_susdat"]["name"],
    }


def known_transformation_products(inchikey: str) -> dict[str, Any]:
    """Known (not predicted) transformation products of one parent/precursor, merged from every curated-pair
    source this app has: NORMAN EAWAGTPS, then the observed microbial metabolism database. Each entry keeps its
    own ``source_key``/``source_name``/``citation``/``source_url`` so provenance stays visible per row."""
    key = (inchikey or "").strip()
    if not key:
        raise ValueError("An InChIKey is required")

    eawagtps_entries = [
        {**entry, "evidence_status": "database_curated", "source_key": "norman_eawagtps",
         "source_name": "NORMAN EAWAGTPS", "citation": _EAWAGTPS["citation"], "source_url": _EAWAGTPS["source_url"]}
        for entry in _EAWAGTPS_BY_PARENT.get(key, [])
    ]
    microbial_entries = [
        {
            "tp_name": entry.get("tp_cas") or "Observed microbial metabolite", "tp_smiles": entry["tp_smiles"],
            "tp_inchikey": entry["tp_inchikey"], "tp_formula": entry.get("tp_formula"), "tp_cas": entry.get("tp_cas"),
            "tp_exact_mass_da": entry.get("tp_exact_mass_da"), "transformation_type": None, "ionization": None,
            "mass_diff_da": None, "formula_diff": None,
            "quantity_percent": entry.get("quantity_percent"),  # present for very few pairs; never invented otherwise
            "evidence_status": "database_curated", "source_key": "oasis_observed_microbial_metabolism",
            "source_name": "Observed Microbial metabolism (LMC/US EPA)", "citation": OBSERVED_MICROBIAL_METABOLISM_CITATION,
            "source_url": None, "source_record_id": ";".join(entry.get("source_record_ids") or []) or None,
        }
        for entry in _OBSERVED_MICROBIAL_METABOLISM_BY_PARENT.get(key, [])
    ]
    entries = eawagtps_entries + microbial_entries
    return {
        "found": bool(entries),
        "parent_inchikey": key,
        "known_transformation_product_count": len(entries),
        "known_transformation_products": entries,
        "message": None if entries else (
            "No known transformation products for this parent are recorded in the NORMAN EAWAGTPS or observed "
            "microbial metabolism reference sets."
        ),
        "source_key": "norman_eawagtps+oasis_observed_microbial_metabolism",
        "citation": _EAWAGTPS["citation"],
        "source_url": _EAWAGTPS["source_url"],
    }


def _subtags_to_dict(rows: Any) -> dict[str, list[str]]:
    """enviPath-style defensive parsing: chromatography/subtags are lists of {subtag, value}."""
    out: dict[str, list[str]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        tag = row.get("subtag")
        value = row.get("value")
        if not tag or value is None:
            continue
        out.setdefault(str(tag), []).append(str(value))
    return out


def _first(values: dict[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        found = values.get(key)
        if found:
            return found[0]
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalise_massbank_record(record: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    accession = record.get("accession")
    if not accession:
        return None

    compound = record.get("compound") or {}
    acquisition = record.get("acquisition") or {}
    ms = acquisition.get("mass_spectrometry") or {}
    subtags = _subtags_to_dict(ms.get("subtags"))
    chromatography = _subtags_to_dict(acquisition.get("chromatography"))
    focused_ion = _subtags_to_dict((record.get("mass_spectrometry") or {}).get("focused_ion"))
    peak_block = ((record.get("peak") or {}).get("peak") or {})
    raw_values = peak_block.get("values")
    product_ions = []
    if isinstance(raw_values, list):
        for value in raw_values[:MAX_PRODUCT_IONS_PER_SPECTRUM]:
            if not isinstance(value, dict):
                continue
            mz = _as_float(value.get("mz"))
            if mz is None:
                continue
            product_ions.append({
                "mz": mz,
                "intensity": _as_float(value.get("intensity")),
                "relative_intensity": _as_float(value.get("rel")),
            })
    product_ions.sort(key=lambda ion: ion.get("intensity") or 0, reverse=True)

    solvents = chromatography.get("SOLVENT") or []

    return {
        "accession": accession,
        "title": record.get("title"),
        "instrument": acquisition.get("instrument"),
        "instrument_type": acquisition.get("instrument_type"),
        "ion_mode": ms.get("ion_mode"),
        "ionization": _first(subtags, "IONIZATION"),
        "fragmentation_mode": _first(subtags, "FRAGMENTATION_MODE"),
        "collision_energy": _first(subtags, "COLLISION_ENERGY"),
        "resolution": _first(subtags, "RESOLUTION"),
        "precursor_mz": _as_float(_first(focused_ion, "PRECURSOR_M/Z")),
        "precursor_type": _first(focused_ion, "PRECURSOR_TYPE"),
        "retention_time_min": _as_float(_first(chromatography, "RETENTION_TIME")),
        "column": _first(chromatography, "COLUMN_NAME"),
        "flow_gradient": _first(chromatography, "FLOW_GRADIENT"),
        "flow_rate": _first(chromatography, "FLOW_RATE"),
        "mobile_phase_solvents": solvents,
        "compound_formula": compound.get("formula"),
        "compound_smiles": compound.get("smiles"),
        "product_ion_count": len(product_ions),
        "product_ions": product_ions,
        "evidence_status": "database_curated",
        "source_key": "massbank_eu",
        "source_record_id": accession,
        "source_url": f"https://massbank.eu/MassBank/RecordDisplay?id={accession}",
    }


def known_product_ions(
    inchikey: str,
    *,
    ion_mode: str | None = None,
    configuration: Settings = settings,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Real, measured product-ion spectra for one substance, from MassBank Europe."""
    key = (inchikey or "").strip()
    if not key:
        raise ValueError("An InChIKey is required")

    if not configuration.massbank_enabled:
        raise ExternalModelUnavailableError(
            "MassBank integration is disabled by configuration.",
            details={"provider": "massbank_eu"},
        )

    own_client = client is None
    http = client or httpx.Client(
        timeout=configuration.massbank_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "EnviroChem/analytical-identification-0.1.0", "Accept": "application/json"},
    )
    try:
        try:
            response = http.get(
                f"{configuration.massbank_base_url}/MassBank-api/records",
                params={"inchi_key": key},
            )
        except httpx.HTTPError as exc:
            raise ExternalDataSourceError(
                "MassBank could not be reached.",
                details={"provider": "massbank_eu", "exception": type(exc).__name__},
            ) from exc
        if response.status_code == 404:
            payload: Any = []
        elif response.status_code >= 400:
            raise ExternalDataSourceError(
                f"MassBank search failed with HTTP {response.status_code}.",
                details={"provider": "massbank_eu", "status_code": response.status_code},
            )
        else:
            if len(response.content) > MAX_PROVIDER_RESPONSE_BYTES:
                raise ExternalDataSourceError(
                    "MassBank response exceeded the 8 MB safety limit.",
                    details={"provider": "massbank_eu"},
                )
            try:
                payload = response.json()
            except (ValueError, json.JSONDecodeError):
                raise ExternalDataSourceError(
                    "MassBank did not return valid JSON.",
                    details={"provider": "massbank_eu"},
                )

        raw_records = payload if isinstance(payload, list) else []
        spectra = [row for row in (_normalise_massbank_record(record) for record in raw_records) if row]
        if ion_mode:
            wanted = ion_mode.strip().upper()
            spectra = [row for row in spectra if (row.get("ion_mode") or "").upper() == wanted]
        total_match_count = len(spectra)
        spectra = spectra[:MAX_MASSBANK_SPECTRA]

        return {
            "inchikey": key,
            "found": bool(spectra),
            "match_count": total_match_count,
            "returned_count": len(spectra),
            "ion_mode_filter": ion_mode,
            "spectra": spectra,
            "message": None if spectra else (
                "No reference product-ion spectrum was found in MassBank Europe for this substance"
                + (f" in {ion_mode} mode." if ion_mode else ".")
            ),
            "source_key": "massbank_eu",
            "citation": MASSBANK_CITATION,
            "queried_at": _utc_now(),
        }
    finally:
        if own_client:
            http.close()


def identification_profile(
    inchikey: str,
    *,
    ion_mode: str | None = None,
    configuration: Settings = settings,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Bundles ionisation/platform, known product ions and known transformation products."""
    key = (inchikey or "").strip()
    if not key:
        raise ValueError("An InChIKey is required")

    # MassBank is a live third-party service; the ionisation and transformation-product sections come from local
    # reference files. One dead upstream must not take the local sections down with it, so its failure is reported
    # inside the product-ion section (found=False, unavailable=True) instead of failing the whole profile.
    try:
        product_ions = known_product_ions(key, ion_mode=ion_mode, configuration=configuration, client=client)
    except (ExternalDataSourceError, ExternalModelUnavailableError) as exc:
        product_ions = {
            "inchikey": key, "found": False, "unavailable": True, "match_count": 0, "returned_count": 0, "spectra": [],
            "message": f"Product-ion spectra could not be retrieved from MassBank Europe right now ({exc}). This is not a 'no spectrum' result.",
            "source_key": "massbank_eu", "citation": MASSBANK_CITATION, "queried_at": _utc_now(),
        }
    return {
        "inchikey": key,
        "generated_at": _utc_now(),
        "ionisation_and_platform": ionisation_and_platform(key),
        "known_product_ions": product_ions,
        "known_transformation_products": known_transformation_products(key),
    }
