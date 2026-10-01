"""enviPath transformation-pathway adapter: curated-pathway search + prediction.

enviPath (https://envipath.org) offers two capabilities BioTransformer does not:
searching its existing, human-curated pathway packages (e.g. EAWAG-BBD) for real
reviewed transformation pathways, and its own rule-based "relative reasoning"
prediction engine. Both are exposed here, producing the same node/edge/product
output envelope `transformation_pathways.py` already uses so the API route and
frontend renderer stay provider-neutral.

Endpoint/payload shapes below combine two sources of evidence: the
enviPath-python client's own source code (not just its README) -- login as a
form POST with `hiddenMethod=login`; a new pathway prediction as
`POST {package_id}/pathway` with `smilesinput`/`name`/`description`, the new
pathway's id in the response `Location` header, completion polled via
`GET {pathway_id}?status` -> `{"completed": "true"|"false"|"error"}` -- and a
live probe of envipath.org made while building this module (2026-09-08):
envipath.org has been rebuilt since that client was written. A bare `/search`
now 302-redirects anonymous requests to an HTML login page (no anonymous read
access at all), but `{API_PREFIX}/search` returns a clean
`401 {"detail": "Unauthorized"}` -- confirming `/api/legacy/` is the live JSON
API's real prefix and that some form of authentication is mandatory, with no
`WWW-Authenticate` header (ruling out HTTP Basic). The current login page also
sits behind a CAPTCHA-style challenge widget, making the old scripted
form-POST login unreliable against the live site -- an API token
(`ENVIPATH_API_TOKEN`, sent as `Authorization: Bearer`) is the recommended,
robust auth path and is tried first; the session-login POST is kept only as a
fallback for older/self-hosted instances and is unverified against the
current site. The exact field names inside a completed pathway's
`nodes`/`links` JSON (compound SMILES, reaction metadata) could not be
confirmed without valid credentials to complete a real request -- this module
follows the same defensive, multiple-candidate-key lookup style already used
for BioTransformer's own field-naming inconsistencies (see `_text()` below) so
an unexpected field name degrades to a missing value instead of a crash. Treat
node/edge parsing as best-effort until validated against a live, authenticated
enviPath account.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable

import httpx

from ..config import Settings, settings
from ..exceptions import ExternalDataSourceError, ExternalModelUnavailableError


ADAPTER_VERSION = "envirochem-envipath-adapter-0.1.0"
API_PREFIX = "/api/legacy"
MAX_PROVIDER_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_NORMALISED_NODES = 500
ENVIPATH_CITATION = (
    "enviPath -- the environmental contaminant biotransformation pathway resource. "
    "https://envipath.org"
)
DEFAULT_PACKAGE_NAME = "enviPath package"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _commercial_gate(configuration: Settings) -> tuple[bool, str]:
    if configuration.envipath_commercial_license_confirmed:
        return True, "commercial_licence_confirmed_by_operator"
    if configuration.envirochem_environment in {"local", "test"} and not configuration.commercial_license_gate_strict:
        return True, "academic_or_development_evaluation_only"
    return False, "commercial_licence_required_for_staging_or_production"


def provider_capabilities(configuration: Settings = settings) -> dict[str, Any]:
    gate_open, licence_status = _commercial_gate(configuration)
    return {
        "provider_key": "envipath",
        "provider_name": "enviPath",
        "adapter_version": ADAPTER_VERSION,
        "enabled": bool(configuration.envipath_enabled and gate_open),
        "configured": bool(configuration.envipath_enabled),
        "licence_status": licence_status,
        "execution_mode": "remote_json_api",
        "base_url": configuration.envipath_base_url,
        "authenticated": bool(
            configuration.envipath_api_token
            or (configuration.envipath_username and configuration.envipath_password)
        ),
        "capabilities": ["curated_pathway_search", "rule_based_prediction"],
        "input": ["parent SMILES", "optional package id filter (search)", "optional parent name (predict)"],
        "outputs": ["pathway nodes", "reaction edges", "package/pathway provenance"],
        "does_not_provide": [
            "measured occurrence outside curated package annotations",
            "formation fractions",
            "rate constants",
            "DT50 values",
        ],
        "citation": ENVIPATH_CITATION,
        "terms_note": (
            "envipath.org states it is free for academic and non-commercial use only, and requires "
            "account registration. Commercial deployment requires separate written permission."
        ),
        "official_url": "https://envipath.org/",
        "api_documentation": "https://github.com/enviPath/enviPath-python",
    }


def _guard_response_size(response: httpx.Response, action: str) -> None:
    if len(response.content) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ExternalDataSourceError(
            f"enviPath {action} exceeded the 8 MB response safety limit.",
            details={"provider": "envipath", "action": action},
        )


def _response_error(response: httpx.Response, action: str) -> ExternalDataSourceError:
    return ExternalDataSourceError(
        f"enviPath {action} failed with HTTP {response.status_code}.",
        details={"provider": "envipath", "action": action, "status_code": response.status_code},
    )


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except (ValueError, json.JSONDecodeError):
        return None


def _authenticate(http: httpx.Client, configuration: Settings) -> None:
    """Best-effort authentication; no-ops when no credentials are configured.

    A bearer API token (the recommended path -- see module docstring) is
    attached directly to every subsequent request via a client default
    header, since httpx.Client does not need a separate "login" call for
    that. Username/password session login is attempted as a fallback for
    older/self-hosted instances; a missing/failed login does not by itself
    raise here -- the resulting request will surface its own 401 if the
    target resource genuinely requires it.
    """
    if configuration.envipath_api_token:
        http.headers["Authorization"] = f"Bearer {configuration.envipath_api_token}"
        return
    if not (configuration.envipath_username and configuration.envipath_password):
        return
    try:
        http.post(
            f"{configuration.envipath_base_url}/login",
            data={
                "hiddenMethod": "login",
                "loginusername": configuration.envipath_username,
                "loginpassword": configuration.envipath_password,
            },
        )
    except httpx.HTTPError:
        return


def _text(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "" and value != []:
            if isinstance(value, (dict, list)):
                continue
            return str(value)
    return None


def _nested(mapping: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        cursor: Any = mapping
        for key in path:
            if not isinstance(cursor, dict):
                cursor = None
                break
            cursor = cursor.get(key)
        if cursor:
            return cursor
    return None


def _compound_smiles(node_or_compound: dict[str, Any]) -> str | None:
    direct = _text(node_or_compound, "smiles", "defaultSmiles", "canonicalSmiles")
    if direct:
        return direct
    nested = _nested(
        node_or_compound,
        ("defaultStructure", "smiles"),
        ("compound", "defaultStructure", "smiles"),
        ("structures", "0", "smiles"),
    )
    return str(nested) if nested else None


def _compound_node(
    raw: dict[str, Any],
    *,
    smiles: str,
    generation: int,
    fallback_name: str,
    role: str,
    evidence_status: str,
) -> dict[str, Any]:
    return {
        "id": f"ep-{sha256(smiles.encode('utf-8')).hexdigest()[:12]}",
        "name": _text(raw, "name", "compoundName") or _nested(raw, ("compound", "name")) or fallback_name,
        "smiles": smiles,
        "inchi": _text(raw, "InChI", "inchi") or _nested(raw, ("compound", "InChI")),
        "inchikey": _text(raw, "inchikey", "InChIKey") or _nested(raw, ("compound", "inchikey")),
        "formula": _text(raw, "formula", "chemicalFormula"),
        "monoisotopic_mass_da": None,
        "generation": generation,
        "role": role,
        "evidence_status": evidence_status,
    }


def _normalise_pathway_payload(
    payload: dict[str, Any],
    *,
    parent_smiles: str,
    parent_name: str,
    evidence_status: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Shared normaliser for both a predicted and a curated-search pathway.

    Mirrors the output envelope `transformation_pathways.normalise_biotransformer_result`
    produces (model_version/provider/query/pathway/products/summary/quantitative_kinetics/
    warnings) so the API route and frontend renderer need no provider-specific branching,
    while independently parsing enviPath's own `nodes`/`links` field names rather than
    forcing enviPath data through BioTransformer's substrate/product parsing.
    """
    raw_nodes = payload.get("nodes") or []
    raw_edges = payload.get("links") or payload.get("edges") or []
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ExternalDataSourceError(
            "enviPath returned an unsupported pathway format.",
            details={"provider": "envipath"},
        )

    nodes_by_smiles: dict[str, dict[str, Any]] = {
        parent_smiles: _compound_node(
            {}, smiles=parent_smiles, generation=0, fallback_name=parent_name,
            role="parent", evidence_status="submitted_parent",
        )
    }
    id_to_smiles: dict[str, str] = {}

    for index, raw_node in enumerate(raw_nodes[:MAX_NORMALISED_NODES], start=1):
        if not isinstance(raw_node, dict):
            continue
        smiles = _compound_smiles(raw_node)
        if not smiles:
            continue
        node_id = _text(raw_node, "id", "nodeId") or str(index)
        id_to_smiles[node_id] = smiles
        if smiles in nodes_by_smiles:
            continue
        depth = raw_node.get("depth")
        generation = int(depth) if isinstance(depth, (int, float)) else 1
        nodes_by_smiles[smiles] = _compound_node(
            raw_node, smiles=smiles, generation=generation,
            fallback_name=f"Node {index}", role="transformation_product",
            evidence_status=evidence_status,
        )

    edges: list[dict[str, Any]] = []
    for index, raw_edge in enumerate(raw_edges, start=1):
        if not isinstance(raw_edge, dict):
            continue
        source_ref = _text(raw_edge, "source", "start", "from")
        target_ref = _text(raw_edge, "target", "end", "to")
        source_smiles = id_to_smiles.get(source_ref or "", parent_smiles)
        target_smiles = id_to_smiles.get(target_ref or "")
        if not target_smiles:
            continue
        source_node = nodes_by_smiles.get(source_smiles)
        target_node = nodes_by_smiles.get(target_smiles)
        if not source_node or not target_node:
            continue
        edges.append({
            "id": f"ep-edge-{sha256(f'{source_ref}|{target_ref}|{index}'.encode('utf-8')).hexdigest()[:12]}",
            "source": source_node["id"],
            "target": target_node["id"],
            "generation": target_node["generation"],
            "reaction_type": _text(raw_edge, "reactionType", "name") or "enviPath transformation",
            "reaction_info": _text(raw_edge, "smirks", "description"),
            "enzyme_or_biosystem": _text(raw_edge, "ecNumbers", "biosystem"),
            "evidence_status": evidence_status,
        })

    nodes = sorted(nodes_by_smiles.values(), key=lambda row: (row["generation"], row["name"], row["smiles"]))
    product_nodes = [node for node in nodes if node["role"] == "transformation_product"]
    products = [
        {
            "name": node["name"],
            "smiles": node["smiles"],
            "status": "database_curated" if evidence_status == "database_curated" else "predicted",
            "matrix": provenance.get("package_name", DEFAULT_PACKAGE_NAME),
            "source": provenance.get("pathway_url") or provenance.get("package_name") or "enviPath",
            "generation": node["generation"],
            "formula": node["formula"],
            "monoisotopic_mass_da": node["monoisotopic_mass_da"],
            "provider_node_id": node["id"],
        }
        for node in product_nodes
    ]

    raw_hash = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    warnings = [
        "enviPath output reflects the selected package's data (curated review status or prediction "
        "rule set); always confirm the underlying package before using a result for regulatory work.",
    ]
    if not product_nodes:
        warnings.append("enviPath returned no normalisable transformation products for this query.")

    return {
        "model_version": ADAPTER_VERSION,
        "provider": provider_capabilities(),
        "query": {
            "provider_query_id": provenance.get("pathway_id"),
            "parent_name": parent_name,
            "parent_smiles": parent_smiles,
            "package_id": provenance.get("package_id"),
            "package_name": provenance.get("package_name"),
            "retrieved_at": _utc_now(),
            "raw_response_sha256": raw_hash,
        },
        "pathway": {"nodes": nodes, "edges": edges},
        "products": products,
        "summary": {
            "unique_product_count": len(product_nodes),
            "reaction_edge_count": len(edges),
            "maximum_generation": max((node["generation"] for node in product_nodes), default=0),
        },
        "quantitative_kinetics": {
            "available": False,
            "formation_fractions": None,
            "rate_constants": None,
            "dt50_values": None,
            "next_step": "Fit reviewed parent/TP time-series data in the EnviroChem kinetic pathway module.",
        },
        "warnings": warnings,
    }


def search_curated_pathways(
    parent_smiles: str,
    *,
    package_ids: list[str] | None = None,
    configuration: Settings = settings,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Search enviPath's existing curated pathway packages for a compound.

    Read-only: results are candidates for a scientist to explicitly copy into
    the review list, not persisted automatically -- the same rule already used
    for PubChem/Europe PMC in the Evidence Data Hub (`evidence_sources.py`).
    """
    if not parent_smiles.strip():
        raise ValueError("Parent SMILES is required")

    capabilities = provider_capabilities(configuration)
    if not configuration.envipath_enabled:
        raise ExternalModelUnavailableError(
            "enviPath integration is disabled by configuration.",
            details={"provider": "envipath"},
        )
    if not capabilities["enabled"]:
        raise ExternalModelUnavailableError(
            "enviPath is blocked outside local/test evaluation until a commercial licence is confirmed.",
            details={"provider": "envipath", "licence_status": capabilities["licence_status"]},
        )

    own_client = client is None
    http = client or httpx.Client(
        timeout=configuration.envipath_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": f"EnviroChem/{ADAPTER_VERSION}", "Accept": "application/json"},
    )
    try:
        _authenticate(http, configuration)
        params: dict[str, Any] = {"search": parent_smiles.strip(), "method": "defaultSmiles"}
        if package_ids:
            params["packages[]"] = package_ids
        try:
            response = http.get(f"{configuration.envipath_base_url}{API_PREFIX}/search", params=params)
        except httpx.HTTPError as exc:
            raise ExternalDataSourceError(
                "enviPath could not be reached.",
                details={"provider": "envipath", "exception": type(exc).__name__},
            ) from exc
        if response.status_code >= 400:
            raise _response_error(response, "search")
        _guard_response_size(response, "search")
        payload = _json_or_none(response)
        if not isinstance(payload, dict):
            raise ExternalDataSourceError(
                "enviPath search did not return valid JSON.",
                details={"provider": "envipath"},
            )

        pathway_hits = payload.get("pathway") or payload.get("pathways") or []
        if not isinstance(pathway_hits, list):
            pathway_hits = []

        results: list[dict[str, Any]] = []
        for hit in pathway_hits:
            if not isinstance(hit, dict):
                continue
            try:
                normalised = _normalise_pathway_payload(
                    hit,
                    parent_smiles=parent_smiles.strip(),
                    parent_name=_text(hit, "name") or "Parent",
                    evidence_status="database_curated",
                    provenance={
                        "pathway_id": _text(hit, "id"),
                        "pathway_url": _text(hit, "id"),
                        "package_id": _nested(hit, ("package", "id")),
                        "package_name": _nested(hit, ("package", "name")) or DEFAULT_PACKAGE_NAME,
                    },
                )
            except ExternalDataSourceError:
                continue
            results.append(normalised)

        return {
            "provider": capabilities,
            "parent_smiles": parent_smiles.strip(),
            "pathway_count": len(results),
            "pathways": results,
            "warnings": [
                "Curated results reflect enviPath's existing reviewed packages; review each package's "
                "own provenance before using a result for regulatory work.",
            ] if results else [
                "No curated enviPath pathway matched this compound in the searched package(s).",
            ],
        }
    finally:
        if own_client:
            http.close()


def predict_pathway(
    parent_smiles: str,
    *,
    parent_name: str = "Parent",
    package_id: str,
    number_of_steps: int = 1,
    configuration: Settings = settings,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    max_wait_seconds: float = 45.0,
    poll_interval_seconds: float = 1.0,
) -> dict[str, Any]:
    """Trigger enviPath's own rule-based pathway prediction for one parent.

    Endpoint/payload/polling contract confirmed from the enviPath-python client's
    source: POST {package_id}/pathway with smilesinput/name, new pathway id comes
    back in the Location response header, poll GET {pathway_id}?status for a
    completed: "true"/"false"/"error" field.
    """
    if not parent_smiles.strip():
        raise ValueError("Parent SMILES is required")
    if not package_id:
        raise ValueError("A target enviPath package id is required to run a prediction")

    capabilities = provider_capabilities(configuration)
    if not configuration.envipath_enabled:
        raise ExternalModelUnavailableError(
            "enviPath integration is disabled by configuration.",
            details={"provider": "envipath"},
        )
    if not capabilities["enabled"]:
        raise ExternalModelUnavailableError(
            "enviPath is blocked outside local/test evaluation until a commercial licence is confirmed.",
            details={"provider": "envipath", "licence_status": capabilities["licence_status"]},
        )

    own_client = client is None
    http = client or httpx.Client(
        timeout=configuration.envipath_timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": f"EnviroChem/{ADAPTER_VERSION}", "Accept": "application/json"},
    )
    try:
        _authenticate(http, configuration)
        try:
            response = http.post(
                f"{configuration.envipath_base_url}{API_PREFIX}/{package_id}/pathway",
                data={
                    "smilesinput": parent_smiles.strip(),
                    "name": parent_name,
                    "description": f"EnviroChem-submitted prediction for {parent_name}",
                },
            )
        except httpx.HTTPError as exc:
            raise ExternalDataSourceError(
                "enviPath could not be reached.",
                details={"provider": "envipath", "exception": type(exc).__name__},
            ) from exc
        if response.status_code >= 400:
            raise _response_error(response, "prediction submission")
        pathway_id = response.headers.get("location") or response.headers.get("Location")
        if not pathway_id:
            raise ExternalDataSourceError(
                "enviPath accepted the prediction request but did not return a pathway location.",
                details={"provider": "envipath"},
            )

        started = time.monotonic()
        while time.monotonic() - started <= max_wait_seconds:
            sleep(poll_interval_seconds)
            try:
                status_response = http.get(f"{pathway_id}", params={"status": ""})
            except httpx.HTTPError as exc:
                raise ExternalDataSourceError(
                    "enviPath status check failed.",
                    details={"provider": "envipath", "pathway_id": pathway_id, "exception": type(exc).__name__},
                ) from exc
            if status_response.status_code >= 400:
                raise _response_error(status_response, "status check")
            status_payload = _json_or_none(status_response)
            completed = str((status_payload or {}).get("completed", "")).lower()
            if completed == "error":
                raise ExternalDataSourceError(
                    "enviPath reported that the prediction failed.",
                    details={"provider": "envipath", "pathway_id": pathway_id},
                )
            if completed == "true":
                break
        else:
            raise ExternalDataSourceError(
                "enviPath did not complete the prediction before the configured wait limit.",
                details={"provider": "envipath", "pathway_id": pathway_id},
            )

        try:
            result_response = http.get(pathway_id)
        except httpx.HTTPError as exc:
            raise ExternalDataSourceError(
                "enviPath result retrieval failed.",
                details={"provider": "envipath", "pathway_id": pathway_id, "exception": type(exc).__name__},
            ) from exc
        if result_response.status_code >= 400:
            raise _response_error(result_response, "result retrieval")
        _guard_response_size(result_response, "result retrieval")
        payload = _json_or_none(result_response)
        if not isinstance(payload, dict):
            raise ExternalDataSourceError(
                "enviPath prediction result was not valid JSON.",
                details={"provider": "envipath", "pathway_id": pathway_id},
            )

        return _normalise_pathway_payload(
            payload,
            parent_smiles=parent_smiles.strip(),
            parent_name=parent_name,
            evidence_status="model_predicted",
            provenance={
                "pathway_id": pathway_id,
                "pathway_url": pathway_id,
                "package_id": package_id,
                "package_name": _nested(payload, ("package", "name")) or DEFAULT_PACKAGE_NAME,
            },
        )
    finally:
        if own_client:
            http.close()
