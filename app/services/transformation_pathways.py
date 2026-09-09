"""Provider-neutral transformation pathway prediction adapters.

BioTransformer is used as an interim provider through its documented JSON
endpoint.  The environmental microbial module is a hypothesis generator: it
does not provide measured occurrence, formation fractions, rate constants or
matrix-specific degradation kinetics.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable

import httpx

from ..config import Settings, settings
from ..exceptions import ExternalDataSourceError, ExternalModelUnavailableError


ADAPTER_VERSION = "envirochem-biotransformer-adapter-0.1.0"
BIOTRANSFORMER_VERSION = "3.1.0-web"
MAX_PROVIDER_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_NORMALISED_PREDICTION_RECORDS = 500
BIOTRANSFORMER_CITATION = (
    "Wishart DS et al. BioTransformer 3.0—a web server for accurately "
    "predicting metabolic transformation products. Nucleic Acids Research "
    "50(W1), W115–W123 (2022). https://doi.org/10.1093/nar/gkac313"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _commercial_gate(configuration: Settings) -> tuple[bool, str]:
    if configuration.biotransformer_commercial_license_confirmed:
        return True, "commercial_licence_confirmed_by_operator"
    if configuration.envirochem_environment in {"local", "test"}:
        return True, "academic_or_development_evaluation_only"
    return False, "commercial_licence_required_for_staging_or_production"


def provider_capabilities(configuration: Settings = settings) -> dict[str, Any]:
    gate_open, licence_status = _commercial_gate(configuration)
    return {
        "provider_key": "biotransformer",
        "provider_name": "BioTransformer",
        "provider_version": BIOTRANSFORMER_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "enabled": bool(configuration.biotransformer_enabled and gate_open),
        "configured": bool(configuration.biotransformer_enabled),
        "licence_status": licence_status,
        "execution_mode": "remote_json_api",
        "base_url": configuration.biotransformer_base_url,
        "module": "ENVMICRO",
        "supported_generations": [1, 2, 3],
        "documented_post_limit": "2 requests per minute",
        "input": ["single parent SMILES", "optional parent name", "1–3 generations"],
        "outputs": ["predicted products", "substrate-product edges", "reaction annotations"],
        "does_not_provide": [
            "measured occurrence",
            "formation fractions",
            "rate constants",
            "DT50 values",
            "matrix-specific confidence",
        ],
        "citation": BIOTRANSFORMER_CITATION,
        "terms_note": (
            "The ENVMICRO module uses enviPath/EAWAG-derived data. Development evaluation is allowed "
            "only within the applicable terms; commercial deployment requires written permission."
        ),
        "official_url": "https://biotransformer.ca/",
        "api_documentation": "https://biotransformer.ca/help",
    }


def _response_error(response: httpx.Response, action: str) -> ExternalDataSourceError:
    if response.status_code == 429:
        return ExternalDataSourceError(
            "BioTransformer rate limit reached. Wait at least 30 seconds before submitting another parent.",
            details={"provider": "biotransformer", "action": action, "status_code": 429},
        )
    if response.status_code == 406:
        # Live-confirmed 2026-09-09: identical headers and JSON body succeed
        # from curl but are rejected 406 "Not Acceptable" from Python's httpx
        # client, on both HTTP/1.1 and HTTP/2, regardless of Accept/
        # Accept-Encoding/Connection headers. biotransformer.ca sits behind
        # Cloudflare, so this is most consistent with TLS/HTTP client
        # fingerprinting at the edge, not a malformed request -- there is no
        # header this adapter can send to reliably fix it, and spoofing a
        # browser TLS fingerprint to get past that protection is out of
        # scope here. Reported plainly so a user is not left staring at a
        # bare "HTTP 406" with no explanation or alternative.
        return ExternalDataSourceError(
            "BioTransformer's live server rejected this request with HTTP 406 (Not Acceptable). "
            "This is not a malformed request -- biotransformer.ca sits behind Cloudflare, which "
            "appears to be blocking this server's automated HTTP client rather than the request "
            "itself. Retrying rarely helps. Use the enviPath curated-pathway lookup as an "
            "alternative source for known transformation products in the meantime.",
            details={"provider": "biotransformer", "action": action, "status_code": 406},
        )
    return ExternalDataSourceError(
        f"BioTransformer {action} failed with HTTP {response.status_code}.",
        details={"provider": "biotransformer", "action": action, "status_code": response.status_code},
    )


def _guard_response_size(response: httpx.Response, action: str) -> None:
    if len(response.content) > MAX_PROVIDER_RESPONSE_BYTES:
        raise ExternalDataSourceError(
            f"BioTransformer {action} exceeded the 8 MB response safety limit.",
            details={"provider": "biotransformer", "action": action},
        )


def _json_or_none(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _query_id(response: httpx.Response, payload: dict[str, Any] | None) -> str | None:
    if payload:
        for key in ("id", "query_id", "queryId"):
            value = payload.get(key)
            if value is not None and value != "":
                return str(value)
    for candidate in (response.headers.get("location", ""), response.text):
        match = re.search(r"(?:data-query-id=[\"']|/queries/)(\d+)", candidate)
        if match:
            return match.group(1)
    return None


def _text(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "" and value != []:
            if isinstance(value, (dict, list)):
                return json.dumps(value, sort_keys=True, ensure_ascii=False)
            return str(value)
    return None


def _number(mapping: dict[str, Any], *keys: str) -> float | None:
    value = _text(mapping, *keys)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _compound_smiles(compound: dict[str, Any]) -> str | None:
    return _text(
        compound,
        "smiles",
        "SMILES",
        "canonical_smiles",
        "Canonical SMILES",
        "InChI_SMILES",
    )


def _compound_node(
    compound: dict[str, Any],
    *,
    smiles: str,
    generation: int,
    fallback_name: str,
    role: str,
) -> dict[str, Any]:
    return {
        "id": f"tp-{sha256(smiles.encode('utf-8')).hexdigest()[:12]}",
        "name": _text(compound, "name", "Name", "preferred_name", "metabolite_name") or fallback_name,
        "smiles": smiles,
        "inchi": _text(compound, "inchi", "InChI"),
        "inchikey": _text(compound, "inchikey", "InChIKey"),
        "formula": _text(compound, "formula", "chemical_formula", "Chemical Formula"),
        "monoisotopic_mass_da": _number(
            compound,
            "major_isotope_mass",
            "Major Isotope Mass",
            "monoisotopic_mass",
            "mass",
        ),
        "generation": generation,
        "role": role,
        "evidence_status": "model_predicted" if role == "transformation_product" else "submitted_parent",
    }


def normalise_biotransformer_result(
    payload: dict[str, Any],
    *,
    query_id: str,
    parent_smiles: str,
    parent_name: str,
    number_of_steps: int,
) -> dict[str, Any]:
    predictions = payload.get("predictions") or []
    if not isinstance(predictions, list):
        raise ExternalDataSourceError(
            "BioTransformer returned an unsupported predictions format.",
            details={"provider": "biotransformer", "query_id": query_id},
        )

    provider_prediction_record_count = len(predictions)
    predictions = predictions[:MAX_NORMALISED_PREDICTION_RECORDS]

    nodes_by_smiles: dict[str, dict[str, Any]] = {
        parent_smiles: _compound_node(
            {}, smiles=parent_smiles, generation=0, fallback_name=parent_name, role="parent"
        )
    }
    edges: list[dict[str, Any]] = []

    for prediction_index, prediction in enumerate(predictions, start=1):
        if not isinstance(prediction, dict):
            continue
        substrates = prediction.get("substrates") or prediction.get("substrate") or []
        products = prediction.get("products") or prediction.get("product") or []
        if isinstance(substrates, dict):
            substrates = [substrates]
        if isinstance(products, dict):
            products = [products]
        if not isinstance(substrates, list) or not isinstance(products, list):
            continue

        substrate_nodes: list[dict[str, Any]] = []
        for substrate_index, substrate in enumerate(substrates, start=1):
            if not isinstance(substrate, dict):
                continue
            smiles = _compound_smiles(substrate)
            if not smiles:
                continue
            existing = nodes_by_smiles.get(smiles)
            if existing is None:
                existing = _compound_node(
                    substrate,
                    smiles=smiles,
                    generation=0 if smiles == parent_smiles else 1,
                    fallback_name=f"Substrate {prediction_index}.{substrate_index}",
                    role="parent" if smiles == parent_smiles else "transformation_product",
                )
                nodes_by_smiles[smiles] = existing
            substrate_nodes.append(existing)

        if not substrate_nodes:
            substrate_nodes = [nodes_by_smiles[parent_smiles]]
        inferred_generation = max(node["generation"] for node in substrate_nodes) + 1
        supplied_generation = _number(prediction, "generation", "iteration", "step")
        generation = max(1, int(supplied_generation)) if supplied_generation is not None else inferred_generation

        for product_index, product in enumerate(products, start=1):
            if not isinstance(product, dict):
                continue
            smiles = _compound_smiles(product)
            if not smiles:
                continue
            node = nodes_by_smiles.get(smiles)
            if node is None:
                node = _compound_node(
                    product,
                    smiles=smiles,
                    generation=generation,
                    fallback_name=f"TP {len(nodes_by_smiles)}",
                    role="transformation_product",
                )
                nodes_by_smiles[smiles] = node
            else:
                node["generation"] = min(node["generation"], generation)

            for substrate_node in substrate_nodes:
                edge_key = f"{substrate_node['id']}|{node['id']}|{prediction_index}|{product_index}"
                edges.append({
                    "id": f"edge-{sha256(edge_key.encode('utf-8')).hexdigest()[:12]}",
                    "source": substrate_node["id"],
                    "target": node["id"],
                    "generation": generation,
                    "reaction_type": _text(
                        prediction,
                        "reaction_type",
                        "reactionType",
                        "biotransformation_type",
                        "Biotransformation type",
                    ) or "Environmental microbial transformation",
                    "reaction_info": _text(
                        prediction,
                        "reaction_info",
                        "reactionInfo",
                        "reaction",
                        "description",
                    ),
                    "enzyme_or_biosystem": _text(
                        prediction,
                        "enzyme",
                        "enzymes",
                        "biosystem",
                        "biosystem_name",
                    ),
                    "evidence_status": "model_predicted",
                })

    nodes = sorted(nodes_by_smiles.values(), key=lambda row: (row["generation"], row["name"], row["smiles"]))
    product_nodes = [node for node in nodes if node["role"] == "transformation_product"]
    products = [
        {
            "name": node["name"],
            "smiles": node["smiles"],
            "status": "predicted",
            "matrix": "generic environmental microbial (soil/water)",
            "source": f"BioTransformer ENVMICRO query {query_id}",
            "generation": node["generation"],
            "formula": node["formula"],
            "monoisotopic_mass_da": node["monoisotopic_mass_da"],
            "provider_node_id": node["id"],
        }
        for node in product_nodes
    ]

    raw_hash = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    provider_errors = payload.get("prediction_errors") or []
    warnings = [
        "All products are model predictions until confirmed by analytical or literature evidence.",
        "BioTransformer ENVMICRO does not provide molar formation fractions, rate constants or DT50 values.",
        "The environmental module is generic to soil/water microbiota and can include aerobic and anaerobic reactions; it is not an activated-sludge, soil or sediment study simulation.",
        "Multi-generation predictions can expand rapidly. Review every structure and reaction before downstream assessment.",
    ]
    if provider_errors:
        warnings.append(f"Provider reported prediction errors: {provider_errors}")
    if provider_prediction_record_count > MAX_NORMALISED_PREDICTION_RECORDS:
        warnings.append(
            f"The provider returned {provider_prediction_record_count} reaction records; only the first "
            f"{MAX_NORMALISED_PREDICTION_RECORDS} were normalised for safe interactive review."
        )
    if not product_nodes:
        warnings.append("BioTransformer returned no normalisable transformation products for this query.")

    return {
        "model_version": ADAPTER_VERSION,
        "provider": provider_capabilities(),
        "query": {
            "provider_query_id": query_id,
            "parent_name": parent_name,
            "parent_smiles": parent_smiles,
            "module": "ENVMICRO",
            "requested_generations": number_of_steps,
            "provider_status": payload.get("status"),
            "provider_prediction_time_ms": payload.get("total_prediction_time_in_ms"),
            "retrieved_at": _utc_now(),
            "raw_response_sha256": raw_hash,
        },
        "pathway": {"nodes": nodes, "edges": edges},
        "products": products,
        "summary": {
            "unique_product_count": len(product_nodes),
            "reaction_edge_count": len(edges),
            "maximum_generation": max((node["generation"] for node in product_nodes), default=0),
            "provider_unique_metabolites": payload.get("number_of_unique_metabolites"),
            "provider_prediction_record_count": provider_prediction_record_count,
            "normalised_prediction_record_count": len(predictions),
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


def predict_environmental_pathway(
    parent_smiles: str,
    *,
    parent_name: str = "Parent",
    number_of_steps: int = 1,
    configuration: Settings = settings,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not 1 <= number_of_steps <= 3:
        raise ValueError("BioTransformer supports one to three environmental transformation generations")
    if not parent_smiles.strip():
        raise ValueError("Parent SMILES is required")

    capabilities = provider_capabilities(configuration)
    if not configuration.biotransformer_enabled:
        raise ExternalModelUnavailableError(
            "BioTransformer integration is disabled by configuration.",
            details={"provider": "biotransformer"},
        )
    if not capabilities["enabled"]:
        raise ExternalModelUnavailableError(
            "BioTransformer ENVMICRO is blocked outside local/test evaluation until a commercial licence is confirmed.",
            details={"provider": "biotransformer", "licence_status": capabilities["licence_status"]},
        )

    own_client = client is None
    http = client or httpx.Client(
        timeout=configuration.biotransformer_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": f"EnviroChem/{ADAPTER_VERSION}"},
    )
    try:
        try:
            response = http.post(
                f"{configuration.biotransformer_base_url}/queries.json",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={
                    "biotransformer_option": "ENVMICRO",
                    "number_of_steps": number_of_steps,
                    "query_input": f"{parent_name}\t{parent_smiles.strip()}",
                    "task_type": "PREDICTION",
                },
            )
        except httpx.HTTPError as exc:
            raise ExternalDataSourceError(
                "BioTransformer could not be reached.",
                details={"provider": "biotransformer", "exception": type(exc).__name__},
            ) from exc
        if response.status_code >= 400:
            raise _response_error(response, "submission")
        _guard_response_size(response, "submission")

        initial_payload = _json_or_none(response)
        query_id = _query_id(response, initial_payload)
        if query_id is None:
            raise ExternalDataSourceError(
                "BioTransformer accepted the request but did not return a query identifier.",
                details={"provider": "biotransformer"},
            )
        if initial_payload and str(initial_payload.get("status", "")).casefold() == "done":
            return normalise_biotransformer_result(
                initial_payload,
                query_id=query_id,
                parent_smiles=parent_smiles.strip(),
                parent_name=parent_name,
                number_of_steps=number_of_steps,
            )

        started = time.monotonic()
        while time.monotonic() - started <= configuration.biotransformer_max_wait_seconds:
            sleep(configuration.biotransformer_poll_interval_seconds)
            try:
                result_response = http.get(
                    f"{configuration.biotransformer_base_url}/queries/{query_id}.json",
                    headers={"Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise ExternalDataSourceError(
                    "BioTransformer result retrieval failed.",
                    details={"provider": "biotransformer", "query_id": query_id, "exception": type(exc).__name__},
                ) from exc
            if result_response.status_code >= 400:
                raise _response_error(result_response, "result retrieval")
            _guard_response_size(result_response, "result retrieval")
            result_payload = _json_or_none(result_response)
            if result_payload is None:
                raise ExternalDataSourceError(
                    "BioTransformer result was not valid JSON.",
                    details={"provider": "biotransformer", "query_id": query_id},
                )
            status = str(result_payload.get("status", "")).casefold()
            if status == "done":
                return normalise_biotransformer_result(
                    result_payload,
                    query_id=query_id,
                    parent_smiles=parent_smiles.strip(),
                    parent_name=parent_name,
                    number_of_steps=number_of_steps,
                )
            if status == "failed":
                raise ExternalDataSourceError(
                    "BioTransformer reported that the prediction failed.",
                    details={
                        "provider": "biotransformer",
                        "query_id": query_id,
                        "prediction_errors": result_payload.get("prediction_errors") or [],
                    },
                )

        raise ExternalDataSourceError(
            "BioTransformer did not complete before the configured wait limit.",
            details={"provider": "biotransformer", "query_id": query_id},
        )
    finally:
        if own_client:
            http.close()
