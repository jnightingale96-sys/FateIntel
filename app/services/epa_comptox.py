"""US EPA CompTox / CTX Hazard API connector -- ToxValDB records, filtered to ecotoxicity.

Closes the "epa_comptox" gap named in app/data/evidence_source_registry.json ("api_key_ready",
search_enabled: false) and app/config.py's comptox_api_key field ("no live connector reads it yet").
The API key was supplied by the user (email received 2026-09-21, "ccte_api") and stored in the
project's gitignored .env; this module is the first thing that reads it.

Endpoint shapes below are taken directly from the CTX APIs' own published OpenAPI specs (read live via
the built-in browser, not summarised by another tool): https://comptox.epa.gov/ctx-api/docs/chemical.json
(chemical identifier resolution) and https://comptox.epa.gov/ctx-api/docs/hazard.json (the ToxValDb
schema). Chemical resolution: ``GET /chemical/search/equal/{word}`` accepts a CAS number, name, DTXSID,
DTXCID or InChIKey directly and returns a ``ChemicalSearchAll`` array with a ``dtxsid`` field -- confirmed
live 2026-09-23 (CAS 1912-24-9 -> DTXSID9020112, "Atrazine"). Hazard data: ``GET
/hazard/toxval/search/by-dtxsid/{dtxsid}`` returns the full ``ToxValDb`` array for that substance; the
schema carries a ``humanEco`` field (documented values include "human health" and "eco") and a
``speciesSupercategory`` field, both clearly designed to distinguish ecotoxicology (fish/invertebrate/
plant/avian) records from human-health toxicology records drawn from the same compiled database.
Authentication: header ``x-api-key`` (confirmed from the spec's ``securitySchemes``), read from
``settings.comptox_api_key``.

**The one finding that matters most, and why this connector still filters on humanEco=="eco" rather than
being abandoned**: live-tested 2026-09-23 against seven real chemicals spanning pesticides, a PFAS, a
plasticiser and a metal (atrazine CAS 1912-24-9, permethrin CAS 52645-53-1, PFOS CAS 1763-23-1, bisphenol A
CAS 80-05-7, copper CAS 7440-50-8, tributyltin oxide CAS 1330-78-5, phenol CAS 50-00-0) -- 1,832 ToxValDB
records were returned in total, and every single one was ``humanEco == "human health"`` with
``speciesSupercategory == "Mammals"`` (rat/mouse/rabbit). This includes 448 atrazine records whose
``source`` field is literally "ECOTOX" (the EPA ECOTOX Knowledgebase) -- confirming ECOTOX itself also
curates mammalian lab-animal studies used for human risk assessment, and that THOSE are what this
particular API endpoint surfaces, not the aquatic/avian/invertebrate side of ECOTOX. For comparison, the
same atrazine CAS number has 4,414 aquatic-medium LC50/EC50/NOEC/EC10 records in this app's own local bulk
import of the full EPA ECOTOX Knowledgebase (``ecotox_local.py``, ``data/ecotox_reference.jsonl``) -- zero
of which came back through this API. EPA's own landing page describes "Hazard APIs" as covering "human and
ecotoxicology data," and the schema is genuinely built to carry both, but as publicly deployed today this
particular endpoint has not been observed to expose a single non-mammalian ecotoxicology record. This
connector still filters for ``humanEco == "eco"`` -- correctly, defensively, matching the real schema --
so any eco-classified record EPA publishes here in the future surfaces automatically; it should not be
relied on as an aquatic-ecotox source today. ``ecotox_local.py``'s bulk ECOTOX Knowledgebase import remains
the comprehensive, confirmed source for that.

Only ``toxvalType`` values that are themselves the literal endpoint codes this app's ENDPOINT_CATALOG
already has slots for (LC50, EC50, NOEC, EC10 -- confirmed as literal ``toxvalType`` values in the real
data, e.g. eight real "LD50" records were observed) are mapped to a property code; any other eco record is
still surfaced (never dropped) with ``property_code=None`` and a note, the same "don't force an unmapped
value into an existing slot" discipline ``ecotox_local.py`` uses for non-aquatic ECOTOX endpoint codes.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from ..config import Settings, settings
from .evidence_sources import EvidenceCandidate, _candidate_id, _ENDPOINT_BY_CODE

BASE_URL = "https://comptox.epa.gov/ctx-api"
DEFAULT_TIMEOUT_S = 15.0

_TOXVAL_TYPE_TO_PROPERTY_CODE = {
    "LC50": "ECOTOX.AQUATIC.LC50",
    "EC50": "ECOTOX.AQUATIC.EC50",
    "NOEC": "ECOTOX.AQUATIC.NOEC",
    "EC10": "ECOTOX.AQUATIC.EC10",
}

KNOWN_EMPTY_ECO_CAVEAT = (
    "EPA's public CTX Hazard API (ToxValDB by-dtxsid) was live-tested 2026-09-23 against seven real "
    "chemicals (1,832 total ToxValDB records) and returned zero humanEco=='eco' records -- see this "
    "module's own docstring. Do not rely on this source for aquatic/avian/invertebrate ecotoxicity "
    "coverage; the app's local EPA ECOTOX Knowledgebase bulk import (epa_ecotox) remains comprehensive "
    "for that."
)


def _client(configuration: Settings) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(DEFAULT_TIMEOUT_S, connect=7.0),
        headers={"x-api-key": configuration.comptox_api_key or "", "User-Agent": "EnviroChem-Studio/2.24 evidence-source-client"},
    )


def _none_if_dash(value: Any) -> str | None:
    """ToxValDB uses the literal string '-' as its own "not populated" sentinel, not null."""
    if value is None:
        return None
    text = str(value).strip()
    return None if text in ("", "-") else text


def resolve_dtxsid(client: httpx.Client, identifier: str) -> dict[str, Any]:
    """GET /chemical/search/equal/{word}; accepts a CAS number, name, DTXSID or InChIKey directly."""

    response = client.get(f"{BASE_URL}/chemical/search/equal/{quote(identifier, safe='')}")
    response.raise_for_status()
    matches = response.json()
    if not isinstance(matches, list) or not matches:
        raise LookupError(f"EPA CompTox did not resolve a DTXSID for {identifier!r}")
    return matches[0]


def _toxval_record_to_candidate(record: dict[str, Any], *, dtxsid: str, chemical_name: str, cas_number: str | None) -> EvidenceCandidate:
    toxval_type = (_none_if_dash(record.get("toxvalType")) or "").upper()
    property_code = _TOXVAL_TYPE_TO_PROPERTY_CODE.get(toxval_type)
    endpoint_label = _ENDPOINT_BY_CODE[property_code]["label"] if property_code else (record.get("toxvalType") or "ToxValDB record")

    snippet_parts = [
        f"{record.get('toxvalType')} = {record.get('toxvalNumeric')} {record.get('toxvalUnits')}" if record.get("toxvalNumeric") is not None else None,
        f"species: {_none_if_dash(record.get('latinName')) or _none_if_dash(record.get('speciesCommon')) or 'not reported'}",
        f"effect: {_none_if_dash(record.get('toxicologicalEffect'))}" if _none_if_dash(record.get("toxicologicalEffect")) else None,
        f"study duration: {record.get('studyDurationValue')} {record.get('studyDurationUnits')}" if record.get("studyDurationValue") is not None else None,
    ]
    snippet = " | ".join(part for part in snippet_parts if part)

    year_raw = _none_if_dash(record.get("year")) or _none_if_dash(record.get("originalYear"))

    return EvidenceCandidate(
        candidate_id=_candidate_id("epa_comptox", record.get("id"), property_code or toxval_type, dtxsid),
        source_key="epa_comptox", source_name="US EPA CompTox / CTX Hazard API (ToxValDB)",
        source_record_id=str(record.get("id")) if record.get("id") is not None else None,
        source_url=_none_if_dash(record.get("sourceUrl")) or f"https://comptox.epa.gov/dashboard/chemical/hazard/{dtxsid}",
        chemical_name=record.get("name") or chemical_name,
        cas_number=_none_if_dash(record.get("casrn")) or cas_number,
        property_code=property_code, endpoint_label=endpoint_label,
        value=record.get("toxvalNumeric"), unit=_none_if_dash(record.get("toxvalUnits")),
        qualifier=_none_if_dash(record.get("qualifier")) or "=",
        matrix=_none_if_dash(record.get("media")), temperature_c=None, ph=None,
        guideline=_none_if_dash(record.get("guideline")),
        evidence_type="database_record",
        publication_title=_none_if_dash(record.get("title")), publication_year=int(year_raw) if (year_raw or "").isdigit() else None,
        doi=_none_if_dash(record.get("doi")), pmid=None, pmcid=None,
        original_source=_none_if_dash(record.get("longRef")) or _none_if_dash(record.get("author")),
        rights_status="public_government_data", import_allowed=True, needs_professional_review=True,
        extraction_status="structured_database_field", snippet=snippet,
        notes=(
            f"source: {record.get('source') or 'not reported'}; subsource: {_none_if_dash(record.get('subsource')) or 'not reported'}; "
            f"study type: {_none_if_dash(record.get('studyType')) or 'not reported'}; "
            f"risk assessment class: {_none_if_dash(record.get('riskAssessmentClass')) or 'not reported'}"
            + ("" if property_code else " -- toxvalType not mapped to an existing ENDPOINT_CATALOG code; value shown for review, not auto-categorised.")
        ),
    )


_BIODEG_PROP_NAMES = ("Biodeg. Half-Life", "Ready Biodegradability")


def _fate_biodeg_to_candidate(record: dict[str, Any], *, prop_name: str, dtxsid: str, chemical_name: str, cas_number: str | None) -> EvidenceCandidate:
    """One OPERA (predicted) or OPERA/SRC-survey (experimental) biodegradation record from /chemical/fate.

    These are generic aerobic-biodegradation figures, NOT matrix-specific DT50s (no soil/water/manure/sludge
    is stated), so ``property_code`` stays None: shown for review, never auto-slotted into a DT50 endpoint.
    Predictions carry OPERA's own applicability-domain verdict verbatim.
    """

    predicted = record.get("prop_type") == "predicted"
    value = record.get("prop_value")
    unit = _none_if_dash(record.get("prop_unit"))
    text_value = _none_if_dash(record.get("prop_value_text")) or _none_if_dash(record.get("prop_value_string"))
    ad = _none_if_dash(record.get("ad_conclusion_global")) or _none_if_dash(record.get("ad_conclusion"))
    ad_note = (
        f"applicability domain: {ad or 'not stated'}"
        + (f" ({str(record.get('ad_reasoning')).replace('&lt;', '<')})" if _none_if_dash(record.get("ad_reasoning")) else "")
    ) if predicted else None
    label = f"{prop_name} ({'OPERA prediction' if predicted else 'experimental record'})"
    return EvidenceCandidate(
        candidate_id=_candidate_id("epa_comptox_fate", record.get("id"), prop_name, dtxsid),
        source_key="epa_comptox", source_name="US EPA CompTox / CTX Chemical fate API (OPERA / curated experimental)",
        source_record_id=str(record.get("id")) if record.get("id") is not None else None,
        source_url=f"https://comptox.epa.gov/dashboard/chemical/env-fate-transport/{dtxsid}",
        chemical_name=chemical_name, cas_number=cas_number, property_code=None, endpoint_label=label,
        value=value if isinstance(value, (int, float)) and not isinstance(value, bool) else None, unit=unit, qualifier="=",
        matrix=None, temperature_c=25.0 if predicted else record.get("exp_details_temperature_c"), ph=record.get("exp_details_ph"),
        guideline=None, evidence_type="model_prediction" if predicted else "database_record",
        publication_title=_none_if_dash(record.get("ls_name")), publication_year=None, doi=_none_if_dash(record.get("ls_doi")),
        pmid=None, pmcid=None,
        original_source=_none_if_dash(record.get("ls_citation")) or _none_if_dash(record.get("source_name")),
        rights_status="public_government_data", import_allowed=True, needs_professional_review=True,
        extraction_status="structured_database_field" if not predicted else "model_output",
        snippet=" | ".join(part for part in (f"{prop_name} = {text_value or value} {unit or ''}".strip(), ad_note) if part),
        notes=(
            f"model: {record.get('model_name') or record.get('dataset') or 'not reported'}; source: {record.get('source_name') or 'not reported'}; "
            "generic biodegradation figure -- no environmental matrix stated, so NOT a soil/water/manure/sludge DT50 and not auto-categorised."
            + (" OPERA predictions are stated at 25 C." if predicted else "")
            + (" Outside OPERA's applicability domain: treat as unreliable." if predicted and (ad or "").lower() == "outside" else "")
        ),
    )


def fate_biodegradation_candidates(
    client: httpx.Client, dtxsid: str, *, chemical_name: str, cas_number: str | None, limit: int = 20,
) -> list[dict[str, Any]]:
    """Biodegradation records from ``GET /chemical/fate/search/by-dtxsid/{dtxsid}`` (experimental first)."""

    response = client.get(f"{BASE_URL}/chemical/fate/search/by-dtxsid/{quote(dtxsid, safe='')}")
    response.raise_for_status()
    groups = response.json()
    if not isinstance(groups, list):
        return []
    experimental: list[dict[str, Any]] = []
    predicted: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict) or group.get("propName") not in _BIODEG_PROP_NAMES:
            continue
        for key, bucket in (("experimentalFateData", experimental), ("predictedFateData", predicted)):
            for record in group.get(key) or []:
                if isinstance(record, dict):  # the API pads empty sections with [null]
                    bucket.append(_fate_biodeg_to_candidate(record, prop_name=group["propName"], dtxsid=dtxsid, chemical_name=chemical_name, cas_number=cas_number).to_dict())
    return (experimental + predicted)[:limit]


def search_epa_comptox(
    chemical_name: str,
    *,
    cas_number: str | None,
    endpoint_codes: list[str] | None = None,
    limit: int = 20,
    client: httpx.Client | None = None,
    configuration: Settings = settings,
) -> dict[str, Any]:
    """Resolve a DTXSID, fetch its ToxValDB records, and return only humanEco=='eco' ones as candidates.

    Mirrors the ``{source_key, status, candidates, warnings}`` shape every other connector in
    ``search_sources()`` returns. See the module docstring for why ``no_eco_records_found`` is the
    expected, correctly-filtered outcome for most chemicals as this API is publicly deployed today.
    """

    if not configuration.comptox_api_key:
        return {
            "source_key": "epa_comptox", "status": "api_key_missing", "candidates": [],
            "warnings": ["No COMPTOX_API_KEY is configured. Request one from the CTX API Admin and set it in .env."],
        }

    owns_client = client is None
    http = client or _client(configuration)
    try:
        identifier = cas_number or chemical_name
        try:
            match = resolve_dtxsid(http, identifier)
        except LookupError:
            return {"source_key": "epa_comptox", "status": "no_match", "candidates": [], "warnings": []}
        dtxsid = match["dtxsid"]

        response = http.get(f"{BASE_URL}/hazard/toxval/search/by-dtxsid/{quote(dtxsid, safe='')}")
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            records = []

        eco_records = [r for r in records if (_none_if_dash(r.get("humanEco")) or "").strip().lower() == "eco"]
        wanted_codes = set(endpoint_codes) if endpoint_codes else None
        candidates: list[dict[str, Any]] = []
        for record in eco_records:
            candidate = _toxval_record_to_candidate(record, dtxsid=dtxsid, chemical_name=chemical_name, cas_number=cas_number)
            if wanted_codes is not None and candidate.property_code not in wanted_codes:
                continue
            candidates.append(candidate.to_dict())
            if len(candidates) >= limit:
                break

        warnings: list[str] = []
        fate_candidates: list[dict[str, Any]] = []
        if not wanted_codes:  # biodegradation records carry no property code, so an endpoint filter excludes them
            try:
                fate_candidates = fate_biodegradation_candidates(
                    http, dtxsid, chemical_name=chemical_name, cas_number=cas_number, limit=limit,
                )
            except (httpx.HTTPError, ValueError) as exc:
                warnings.append(f"CompTox fate endpoint (OPERA biodegradation) unavailable: {type(exc).__name__}: {exc}")
        candidates.extend(fate_candidates)
        status = "ok" if candidates else "no_eco_records_found"
        if not candidates:
            warnings.append(
                f"{len(records)} ToxValDB record(s) found for {match.get('preferredName') or chemical_name} "
                f"(DTXSID {dtxsid}), none classified humanEco=='eco'. {KNOWN_EMPTY_ECO_CAVEAT}"
            )

        return {
            "source_key": "epa_comptox", "status": status, "candidates": candidates, "warnings": warnings,
            "dtxsid": dtxsid, "total_toxval_records": len(records),
        }
    finally:
        if owns_client:
            http.close()
