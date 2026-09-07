from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.exceptions import ExternalModelUnavailableError
from app.main import app
from app.services.transformation_pathways import (
    normalise_biotransformer_result,
    predict_environmental_pathway,
    provider_capabilities,
)


PARENT = "CCO"


def sample_provider_payload():
    return {
        "id": 42,
        "status": "Done",
        "number_of_unique_metabolites": 2,
        "total_prediction_time_in_ms": 321,
        "predictions": [
            {
                "substrates": [{"name": "Ethanol", "smiles": PARENT, "formula": "C2H6O"}],
                "products": [{"name": "Acetaldehyde", "smiles": "CC=O", "formula": "C2H4O", "major_isotope_mass": 44.0262}],
                "reaction_type": "Alcohol oxidation",
                "enzyme": "alcohol dehydrogenase",
            },
            {
                "substrates": [{"name": "Acetaldehyde", "smiles": "CC=O"}],
                "products": [{"name": "Acetic acid", "smiles": "CC(=O)O", "formula": "C2H4O2"}],
                "reaction_type": "Aldehyde oxidation",
            },
        ],
        "prediction_errors": [],
    }


def test_provider_is_enabled_for_local_evaluation_but_gated_in_production():
    local = Settings(_env_file=None, envirochem_environment="local")
    production = Settings(_env_file=None, envirochem_environment="production")
    assert provider_capabilities(local)["enabled"] is True
    assert provider_capabilities(local)["licence_status"] == "academic_or_development_evaluation_only"
    assert provider_capabilities(production)["enabled"] is False
    assert "licence_required" in provider_capabilities(production)["licence_status"]


def test_normaliser_builds_provider_neutral_multigeneration_graph():
    result = normalise_biotransformer_result(
        sample_provider_payload(),
        query_id="42",
        parent_smiles=PARENT,
        parent_name="Ethanol",
        number_of_steps=2,
    )
    assert result["summary"]["unique_product_count"] == 2
    assert result["summary"]["reaction_edge_count"] == 2
    assert result["summary"]["maximum_generation"] == 2
    assert result["summary"]["provider_unique_metabolites"] == 2
    assert result["summary"]["provider_prediction_record_count"] == 2
    products = {row["name"]: row for row in result["products"]}
    assert products["Acetaldehyde"]["generation"] == 1
    assert products["Acetic acid"]["generation"] == 2
    assert all(row["status"] == "predicted" for row in result["products"])
    assert result["quantitative_kinetics"]["available"] is False
    assert len(result["query"]["raw_response_sha256"]) == 64


def test_remote_adapter_submits_envmicro_and_polls_json_result():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            assert request.url.path == "/queries.json"
            assert b'"biotransformer_option":"ENVMICRO"' in request.content
            return httpx.Response(202, json={"id": 42, "status": "In progress"})
        assert request.url.path == "/queries/42.json"
        return httpx.Response(200, json=sample_provider_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(
        _env_file=None,
        envirochem_environment="test",
        biotransformer_base_url="https://biotransformer.example",
        biotransformer_poll_interval_seconds=0.1,
        biotransformer_max_wait_seconds=2,
    )
    result = predict_environmental_pathway(
        PARENT,
        parent_name="Ethanol",
        number_of_steps=2,
        configuration=configuration,
        client=client,
        sleep=lambda _: None,
    )
    client.close()
    assert len(requests) == 2
    assert result["summary"]["unique_product_count"] == 2
    assert result["query"]["provider_query_id"] == "42"


def test_production_gate_stops_before_external_request():
    configuration = Settings(_env_file=None, envirochem_environment="production")
    with pytest.raises(ExternalModelUnavailableError, match="commercial licence"):
        predict_environmental_pathway(PARENT, configuration=configuration)


def test_pathway_api_contract_can_return_normalised_prediction(monkeypatch):
    output = normalise_biotransformer_result(
        sample_provider_payload(),
        query_id="42",
        parent_smiles=PARENT,
        parent_name="Ethanol",
        number_of_steps=2,
    )
    monkeypatch.setattr("app.main.predict_environmental_pathway", lambda *args, **kwargs: output)
    with TestClient(app) as client:
        capability = client.get("/api/transformation-pathways/providers")
        assert capability.status_code == 200
        assert capability.json()["default_provider"] == "biotransformer"
        response = client.post(
            "/api/transformation-pathways/predict",
            json={"parent_smiles": PARENT, "parent_name": "Ethanol", "number_of_steps": 2},
        )
    assert response.status_code == 200
    assert response.json()["model_run_id"] is None
    assert response.json()["outputs"]["summary"]["reaction_edge_count"] == 2


def test_completed_prediction_is_persisted_with_provider_audit(monkeypatch):
    output = normalise_biotransformer_result(
        sample_provider_payload(),
        query_id="42",
        parent_smiles=PARENT,
        parent_name="Ethanol",
        number_of_steps=2,
    )
    monkeypatch.setattr("app.main.predict_environmental_pathway", lambda *args, **kwargs: output)
    with TestClient(app) as client:
        project = client.post(
            "/api/projects",
            json={"name": f"TP pathway QA {uuid4().hex[:8]}", "jurisdiction": "UK/EU screening"},
        ).json()
        chemical = client.get("/api/chemicals").json()[0]
        response = client.post(
            "/api/transformation-pathways/predict",
            json={
                "parent_smiles": PARENT,
                "parent_name": "Ethanol",
                "number_of_steps": 2,
                "project_id": project["id"],
                "chemical_id": chemical["id"],
            },
        )
        audit = client.get(f"/api/projects/{project['id']}/audit").json()
    assert response.status_code == 200
    assert isinstance(response.json()["model_run_id"], int)
    assert any(row["action"] == "transformation_pathway_predicted" for row in audit)


def test_interface_exposes_prediction_and_review_controls():
    html = Path("app/static/index.html").read_text(encoding="utf-8")
    script = Path("app/static/app.js").read_text(encoding="utf-8")
    for marker in (
        'id="predict-transformation-pathway"',
        'id="pathway-generations"',
        'id="pathway-provider-status"',
        'id="pathway-products"',
    ):
        assert marker in html
    assert "/api/transformation-pathways/predict" in script
    assert "Formation fractions, rate constants and TP degradation must be fitted separately" in script
