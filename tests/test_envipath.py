from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.exceptions import ExternalModelUnavailableError
from app.main import app
from app.services.envipath import (
    predict_pathway,
    provider_capabilities,
    search_curated_pathways,
)


PARENT = "CCO"


def sample_pathway_payload(*, package_name="EAWAG-BBD"):
    return {
        "id": "https://envipath.org/package/pkg-1/pathway/pw-1",
        "name": "Ethanol pathway",
        "package": {"id": "https://envipath.org/package/pkg-1", "name": package_name},
        "nodes": [
            {"id": "node-1", "smiles": PARENT, "name": "Ethanol", "depth": 0},
            {"id": "node-2", "smiles": "CC=O", "name": "Acetaldehyde", "depth": 1, "InChI": "InChI=1S/C2H4O", "inchikey": "IKHGUXGNUITLKF"},
            {"id": "node-3", "smiles": "CC(=O)O", "name": "Acetic acid", "depth": 2},
        ],
        "links": [
            {"source": "node-1", "target": "node-2", "reactionType": "Alcohol oxidation", "ecNumbers": "1.1.1.1"},
            {"source": "node-2", "target": "node-3", "reactionType": "Aldehyde oxidation"},
        ],
    }


def test_provider_is_enabled_for_local_evaluation_but_gated_in_production():
    local = Settings(_env_file=None, envirochem_environment="local")
    production = Settings(_env_file=None, envirochem_environment="production")
    assert provider_capabilities(local)["enabled"] is True
    assert provider_capabilities(local)["licence_status"] == "academic_or_development_evaluation_only"
    assert provider_capabilities(production)["enabled"] is False
    assert "licence_required" in provider_capabilities(production)["licence_status"]


def test_production_gate_stops_search_before_external_request():
    configuration = Settings(_env_file=None, envirochem_environment="production")
    with pytest.raises(ExternalModelUnavailableError, match="commercial licence"):
        search_curated_pathways(PARENT, configuration=configuration)


def test_production_gate_stops_predict_before_external_request():
    configuration = Settings(_env_file=None, envirochem_environment="production")
    with pytest.raises(ExternalModelUnavailableError, match="commercial licence"):
        predict_pathway(PARENT, package_id="pkg-1", configuration=configuration)


def test_curated_search_normalises_multiple_pathway_hits():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/legacy/search"
        assert request.url.params["search"] == PARENT
        assert request.url.params["method"] == "defaultSmiles"
        return httpx.Response(200, json={"pathway": [sample_pathway_payload()]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(
        _env_file=None, envirochem_environment="test", envipath_base_url="https://envipath.example",
    )
    result = search_curated_pathways(PARENT, configuration=configuration, client=client)
    client.close()

    assert result["pathway_count"] == 1
    pathway = result["pathways"][0]
    assert pathway["summary"]["unique_product_count"] == 2
    assert pathway["summary"]["reaction_edge_count"] == 2
    products = {row["name"]: row for row in pathway["products"]}
    assert products["Acetaldehyde"]["status"] == "database_curated"
    assert products["Acetaldehyde"]["generation"] == 1
    assert products["Acetic acid"]["generation"] == 2
    assert pathway["query"]["package_name"] == "EAWAG-BBD"


def test_curated_search_with_no_hits_reports_no_match_without_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"pathway": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, envirochem_environment="test", envipath_base_url="https://envipath.example")
    result = search_curated_pathways(PARENT, configuration=configuration, client=client)
    client.close()

    assert result["pathway_count"] == 0
    assert result["pathways"] == []
    assert "No curated enviPath pathway matched" in result["warnings"][0]


def test_predict_pathway_submits_logs_in_polls_and_normalises_result():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/login":
            assert b"hiddenMethod=login" in request.content
            return httpx.Response(200)
        if request.method == "POST" and request.url.path == "/api/legacy/pkg-1/pathway":
            assert b"smilesinput" in request.content
            return httpx.Response(
                302, headers={"Location": "https://envipath.example/api/legacy/pkg-1/pathway/new-pw"},
            )
        if "status" in request.url.params:
            return httpx.Response(200, json={"completed": "true"})
        return httpx.Response(200, json=sample_pathway_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(
        _env_file=None, envirochem_environment="test", envipath_base_url="https://envipath.example",
        envipath_username="qa", envipath_password="qa",
    )
    result = predict_pathway(
        PARENT, parent_name="Ethanol", package_id="pkg-1", configuration=configuration,
        client=client, sleep=lambda _: None, poll_interval_seconds=0.01,
    )
    client.close()

    assert any(r.url.path == "/login" for r in requests)
    assert result["summary"]["unique_product_count"] == 2
    assert result["products"][0]["status"] == "predicted"
    assert result["query"]["package_id"] == "pkg-1"


def test_api_token_is_preferred_over_session_login_and_sent_as_bearer():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"pathway": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(
        _env_file=None, envirochem_environment="test", envipath_base_url="https://envipath.example",
        envipath_api_token="qa-token", envipath_username="qa", envipath_password="qa",
    )
    search_curated_pathways(PARENT, configuration=configuration, client=client)
    client.close()

    assert not any(r.url.path == "/login" for r in requests), "token auth must skip the session-login POST entirely"
    assert all(r.headers.get("authorization") == "Bearer qa-token" for r in requests)


def test_predict_pathway_reports_provider_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(302, headers={"Location": "https://envipath.example/pkg-1/pathway/new-pw"})
        return httpx.Response(200, json={"completed": "error"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, envirochem_environment="test", envipath_base_url="https://envipath.example")
    from app.exceptions import ExternalDataSourceError
    with pytest.raises(ExternalDataSourceError, match="prediction failed"):
        predict_pathway(
            PARENT, package_id="pkg-1", configuration=configuration,
            client=client, sleep=lambda _: None, poll_interval_seconds=0.01,
        )
    client.close()


def test_providers_endpoint_lists_both_biotransformer_and_envipath():
    with TestClient(app) as client:
        response = client.get("/api/transformation-pathways/providers")
    assert response.status_code == 200
    provider_keys = {row["provider_key"] for row in response.json()["providers"]}
    assert provider_keys == {"biotransformer", "envipath"}


def test_search_curated_route_returns_normalised_pathways(monkeypatch):
    sample_result = {
        "provider": provider_capabilities(),
        "parent_smiles": PARENT,
        "pathway_count": 0,
        "pathways": [],
        "warnings": ["No curated enviPath pathway matched this compound in the searched package(s)."],
    }
    monkeypatch.setattr("app.main.search_envipath_curated_pathways", lambda *args, **kwargs: sample_result)
    with TestClient(app) as client:
        response = client.get("/api/transformation-pathways/search-curated", params={"parent_smiles": PARENT})
    assert response.status_code == 200
    assert response.json()["pathway_count"] == 0


def test_envipath_predict_provider_persists_model_run_with_provider_audit(monkeypatch):
    from app.services.envipath import _normalise_pathway_payload
    normalised = _normalise_pathway_payload(
        sample_pathway_payload(), parent_smiles=PARENT, parent_name="Ethanol",
        evidence_status="model_predicted", provenance={"pathway_id": "pw-1", "package_id": "pkg-1", "package_name": "EAWAG-BBD"},
    )
    monkeypatch.setattr("app.main.predict_envipath_pathway", lambda *args, **kwargs: normalised)
    with TestClient(app) as client:
        project = client.post(
            "/api/projects", json={"name": f"enviPath predict QA {uuid4().hex[:8]}", "jurisdiction": "UK/EU screening"},
        ).json()
        chemical = client.get("/api/chemicals").json()[0]
        response = client.post(
            "/api/transformation-pathways/predict",
            json={
                "provider": "envipath",
                "parent_smiles": PARENT,
                "parent_name": "Ethanol",
                "envipath_package_id": "pkg-1",
                "project_id": project["id"],
                "chemical_id": chemical["id"],
            },
        )
        audit = client.get(f"/api/projects/{project['id']}/audit").json()
    assert response.status_code == 200
    assert isinstance(response.json()["model_run_id"], int)
    matching = [row for row in audit if row["action"] == "transformation_pathway_predicted"]
    assert matching and matching[0]["payload"]["provider"] == "envipath"


def test_predict_requires_package_id_for_envipath_provider():
    with TestClient(app) as client:
        response = client.post(
            "/api/transformation-pathways/predict",
            json={"provider": "envipath", "parent_smiles": PARENT},
        )
    assert response.status_code == 422
