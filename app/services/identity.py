from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx


PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov"
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
DEFAULT_TIMEOUT_S = 14.0


def _normalise_text(value: Any) -> str:
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def normalise_identifier(scheme: str, value: Any) -> str:
    """Return a deterministic comparison form without changing stored display text."""

    text = str(value or "").strip()
    if scheme in {"cas", "ec"}:
        return text.replace(" ", "")
    if scheme == "inchikey":
        return text.upper()
    if scheme == "formula":
        return text.replace(" ", "")
    if scheme == "smiles":
        return text
    return _normalise_text(text)


def core_identity_hash(candidate: dict[str, Any]) -> str:
    """Hash molecular identity independently from the retrieval source/query."""

    canonical = {
        "cas_number": normalise_identifier("cas", candidate.get("cas_number")),
        "molecular_formula": normalise_identifier("formula", candidate.get("molecular_formula")),
        "molecular_weight_g_mol": (
            float(candidate["molecular_weight_g_mol"])
            if candidate.get("molecular_weight_g_mol") is not None
            else None
        ),
        "smiles": normalise_identifier("smiles", candidate.get("smiles")),
        "inchikey": normalise_identifier("inchikey", candidate.get("inchikey")),
        "substance_form": _normalise_text(candidate.get("substance_form") or "parent"),
    }
    return sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def identity_hash(candidate: dict[str, Any]) -> str:
    canonical = {
        "source_key": candidate.get("source_key"),
        "source_record_id": candidate.get("source_record_id"),
        "preferred_name": candidate.get("preferred_name"),
        "cas_number": candidate.get("cas_number"),
        "molecular_formula": candidate.get("molecular_formula"),
        "molecular_weight_g_mol": float(candidate["molecular_weight_g_mol"]) if candidate.get("molecular_weight_g_mol") is not None else None,
        "smiles": candidate.get("smiles"),
        "inchikey": candidate.get("inchikey"),
    }
    return sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def identity_conflicts(chemical: Any, candidate: dict[str, Any]) -> list[str]:
    """Identify molecular conflicts before an existing record is reused.

    InChIKey has precedence over CAS for structural identity. CAS, formula and
    molecular weight remain independent conflict checks because salt/parent and
    registry-number mismatches must never be silently collapsed. SMILES is not
    compared textually when an InChIKey is present because equivalent SMILES can
    have different serialisations.
    """

    conflicts: list[str] = []
    checks = (
        ("InChIKey", "inchikey", "inchikey"),
        ("CAS", "cas_number", "cas"),
        ("molecular formula", "molecular_formula", "formula"),
        ("substance form", "substance_form", "text"),
    )
    for label, field, scheme in checks:
        stored = getattr(chemical, field, None)
        supplied = candidate.get(field)
        if stored in {None, ""} or supplied in {None, ""}:
            continue
        if normalise_identifier(scheme, stored) != normalise_identifier(scheme, supplied):
            conflicts.append(label)

    stored_mw = getattr(chemical, "molecular_weight_g_mol", None)
    supplied_mw = candidate.get("molecular_weight_g_mol")
    if stored_mw is not None and supplied_mw is not None:
        tolerance = max(0.01, abs(float(stored_mw)) * 0.001)
        if abs(float(stored_mw) - float(supplied_mw)) > tolerance:
            conflicts.append("molecular weight")

    if not getattr(chemical, "inchikey", None):
        stored_smiles = getattr(chemical, "smiles", None)
        supplied_smiles = candidate.get("smiles")
        if stored_smiles and supplied_smiles and stored_smiles != supplied_smiles:
            conflicts.append("SMILES")
    return conflicts


def validate_identity_candidate(candidate: dict[str, Any]) -> None:
    supplied = str(candidate.get("identity_hash") or "")
    expected = identity_hash(candidate)
    if not supplied or supplied != expected:
        raise ValueError("Resolved identity hash does not match the confirmed snapshot")
    supplied_core = str(candidate.get("core_identity_hash") or "")
    if supplied_core and supplied_core != core_identity_hash(candidate):
        raise ValueError("Resolved core identity hash does not match the molecular identity")
    if candidate.get("source_key") not in {"pubchem", "local_verified_record"}:
        raise ValueError("Unsupported identity source")
    if not candidate.get("inchikey") or not candidate.get("smiles"):
        raise ValueError("A confirmed structure and InChIKey are required")


def local_identity_candidate(chemical: Any, *, query: str, query_mode: str) -> dict[str, Any]:
    candidate = {
        "source_key": "local_verified_record",
        "source_record_id": f"chemical:{chemical.id}",
        "source_url": None,
        "query_text": query,
        "query_mode": query_mode,
        "preferred_name": chemical.preferred_name,
        "cas_number": chemical.cas_number,
        "cas_candidates": [chemical.cas_number] if chemical.cas_number else [],
        "molecular_formula": chemical.molecular_formula,
        "molecular_weight_g_mol": chemical.molecular_weight_g_mol,
        "smiles": chemical.smiles,
        "inchikey": chemical.inchikey,
        "substance_form": chemical.substance_form,
        "xlogp_candidate": None,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "warnings": ["This identity is the locally stored, previously confirmed record."],
    }
    candidate["identity_hash"] = identity_hash(candidate)
    candidate["core_identity_hash"] = core_identity_hash(candidate)
    return candidate


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(DEFAULT_TIMEOUT_S, connect=7.0),
        follow_redirects=True,
        headers={"User-Agent": "EnviroChem-Studio/2.18 identity-resolution-client"},
    )


RETRYABLE_STATUS = {429, 502, 503, 504}
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (0.8, 2.0)


def _get_with_retry(client: httpx.Client, url: str, *, sleep=time.sleep) -> httpx.Response:
    """GET with a small bounded retry for transient PubChem conditions only.

    PubChem's usage policy throttles bursts with 503 "ServerBusy" (and 429); a timeout or dropped connection is
    equally transient. Anything else (404, 400, ...) is a real answer and is returned immediately.
    Found by a random-chemical validation run in which 18 of the first 44 lookups hit 503 with no retry.
    """
    for attempt in range(MAX_ATTEMPTS):
        last = attempt == MAX_ATTEMPTS - 1
        try:
            response = client.get(url)
        except (httpx.TimeoutException, httpx.TransportError):
            if last:
                raise
            sleep(BACKOFF_SECONDS[attempt])
            continue
        if response.status_code in RETRYABLE_STATUS and not last:
            retry_after = response.headers.get("Retry-After", "")
            delay = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else BACKOFF_SECONDS[attempt]
            sleep(min(delay, 5.0))
            continue
        return response
    raise AssertionError("unreachable")


def _resolve_cid(client: httpx.Client, query: str, query_mode: str) -> int:
    namespace = "smiles" if query_mode == "smiles" else "name"
    url = f"{PUBCHEM_BASE}/rest/pug/compound/{namespace}/{quote(query, safe='')}/cids/JSON"
    response = _get_with_retry(client, url)
    if response.status_code == 404:
        # A 404 is PubChem's definitive "no such compound", not an outage. UVCB substances, mixtures and trade names
        # (e.g. CAS 68585-34-2, 39341-15-6) have no single structure record; calling that "temporarily unavailable"
        # would tell the user to retry something that can never succeed.
        raise ValueError("PubChem has no single-compound record for this identifier (mixtures, UVCB substances and trade names have no unique structure)")
    if response.status_code == 400:
        # PubChem's own "PUGREST.BadRequest" -- the query itself is malformed (an invalid SMILES string is the
        # common case), not a service outage. Surfacing this as "temporarily unavailable" told the user to
        # retry something that can never succeed; this is the same discipline as the 404 case above. PubChem's
        # own fault message is specific and worth keeping (e.g. "Unable to standardize the given structure").
        try:
            fault_message = response.json().get("Fault", {}).get("Message")
        except (ValueError, json.JSONDecodeError):
            fault_message = None
        hint = {"smiles": "Check the SMILES syntax.", "cas": "Check the CAS number format.", "iupac": "Check the spelling or try a CAS number instead."}.get(query_mode, "")
        raise ValueError(f"PubChem rejected this {query_mode.upper()} query as invalid" + (f": {fault_message}" if fault_message else ".") + f" {hint}".rstrip())
    response.raise_for_status()
    rows = response.json().get("IdentifierList", {}).get("CID", [])
    if not rows:
        raise ValueError("PubChem did not return a compound identity")
    if len(rows) > 1:
        raise ValueError("The identifier maps to multiple PubChem compounds; refine it to one parent substance")
    return int(rows[0])


def _property_row(client: httpx.Client, cid: int) -> dict[str, Any]:
    property_names = "Title,IUPACName,MolecularFormula,MolecularWeight,InChIKey,CanonicalSMILES,IsomericSMILES,XLogP"
    url = f"{PUBCHEM_BASE}/rest/pug/compound/cid/{cid}/property/{property_names}/JSON"
    response = _get_with_retry(client, url)
    response.raise_for_status()
    rows = response.json().get("PropertyTable", {}).get("Properties", [])
    if not rows:
        raise ValueError("PubChem returned no molecular identity properties")
    return rows[0]


def _synonyms(client: httpx.Client, cid: int) -> list[str]:
    url = f"{PUBCHEM_BASE}/rest/pug/compound/cid/{cid}/synonyms/JSON"
    response = _get_with_retry(client, url)
    response.raise_for_status()
    blocks = response.json().get("InformationList", {}).get("Information", [])
    return [str(value).strip() for value in (blocks[0].get("Synonym", []) if blocks else []) if str(value).strip()]


def resolve_pubchem_identity(query: str, query_mode: str) -> dict[str, Any]:
    if query_mode == "product":
        raise ValueError("Product-name resolution requires a formulation/SDS workflow; enter the active substance name or CAS number")
    if query_mode not in {"cas", "smiles", "iupac"}:
        raise ValueError("Unsupported identity query mode")
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("An identity query is required")

    with _client() as client:
        cid = _resolve_cid(client, cleaned, query_mode)
        properties = _property_row(client, cid)
        synonyms = _synonyms(client, cid)

    cas_candidates = []
    for value in synonyms:
        if CAS_RE.fullmatch(value) and value not in cas_candidates:
            cas_candidates.append(value)
    requested_cas = cleaned if CAS_RE.fullmatch(cleaned) else None
    cas_number = requested_cas or (cas_candidates[0] if cas_candidates else None)
    preferred_name = (
        properties.get("Title")
        or properties.get("IUPACName")
        or next((value for value in synonyms if not CAS_RE.fullmatch(value) and len(value) <= 200), cleaned)
    )
    smiles = properties.get("ConnectivitySMILES") or properties.get("CanonicalSMILES") or properties.get("IsomericSMILES")
    candidate = {
        "source_key": "pubchem",
        "source_record_id": f"CID:{cid}",
        "source_url": f"{PUBCHEM_BASE}/compound/{cid}",
        "pubchem_cid": cid,
        "query_text": cleaned,
        "query_mode": query_mode,
        "preferred_name": preferred_name,
        "cas_number": cas_number,
        "cas_candidates": cas_candidates[:12],
        "molecular_formula": properties.get("MolecularFormula"),
        "molecular_weight_g_mol": float(properties["MolecularWeight"]),
        "smiles": smiles,
        "inchikey": properties.get("InChIKey"),
        "substance_form": "parent",
        "xlogp_candidate": properties.get("XLogP"),
        "structure_image_url": f"{PUBCHEM_BASE}/image/imgsrv.fcgi?cid={cid}&t=l",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "warnings": [
            "PubChem identity metadata is a candidate snapshot and must be confirmed before it is stored.",
            "Confirm the parent/salt form and CAS number; PubChem synonym lists may contain historical registry numbers.",
            "XLogP, when present, is a computed candidate and is not selected for modelling automatically.",
        ],
    }
    if not all((candidate["molecular_formula"], candidate["molecular_weight_g_mol"], candidate["smiles"], candidate["inchikey"])):
        raise ValueError("PubChem identity is missing a formula, molecular weight, SMILES or InChIKey")
    candidate["identity_hash"] = identity_hash(candidate)
    candidate["core_identity_hash"] = core_identity_hash(candidate)
    return candidate


def identity_matches_query(chemical: Any, query: str) -> bool:
    normalised = _normalise_text(query)
    return normalised in {
        _normalise_text(chemical.preferred_name),
        _normalise_text(chemical.cas_number),
        _normalise_text(chemical.smiles),
        _normalise_text(chemical.inchikey),
    }
