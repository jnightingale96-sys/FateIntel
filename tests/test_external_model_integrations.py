from copy import deepcopy

from fastapi.testclient import TestClient

from app.main import app
from app.services.adapters import ADAPTER_CONTRACTS, prepare_workflow_manifest
from app.services.external_models import (
    MODEL_PROFILES,
    integration_catalog,
    validate_external_model_inputs,
    validate_external_model_output,
)
from app.services.registry import MODELS


def model(key: str):
    return next(row for row in MODELS if row["key"] == key)


def test_profiles_distinguish_spin_dependency_from_simulators():
    assert set(MODEL_PROFILES) == {"SPIN", "MACRO", "GREATER", "PWC", "CHEMSTEER", "CEM", "EFAST"}
    assert MODEL_PROFILES["SPIN"]["is_simulation_model"] is False
    assert MODEL_PROFILES["MACRO"]["is_simulation_model"] is True
    assert MODEL_PROFILES["GREATER"]["is_simulation_model"] is True
    assert "5.5.4a" in MODEL_PROFILES["MACRO"]["official_version"]
    assert MODEL_PROFILES["GREATER"]["official_version"] == "4"
    assert "legacy" in MODEL_PROFILES["EFAST"]["official_version"].lower()
    assert "3.003" in MODEL_PROFILES["PWC"]["official_version"]
    assert "does not reproduce" in MODEL_PROFILES["CHEMSTEER"]["known_constraints"][0]


def test_catalog_reports_paths_without_claiming_execution():
    catalog = {row["key"]: row for row in integration_catalog()}
    assert catalog["SPIN"]["path_environment_variable"] == "ENVIROCHEM_SPIN_PATH"
    assert catalog["MACRO"]["path_environment_variable"] == "ENVIROCHEM_MACRO_PATH"
    assert catalog["GREATER"]["path_environment_variable"] == "ENVIROCHEM_GREATER_PATH"
    assert catalog["CHEMSTEER"]["path_environment_variable"] == "ENVIROCHEM_CHEMSTEER_PATH"
    assert catalog["CEM"]["path_environment_variable"] == "ENVIROCHEM_CEM_PATH"
    assert catalog["EFAST"]["path_environment_variable"] == "ENVIROCHEM_EFAST_PATH"
    assert catalog["PWC"]["path_environment_variable"] == "ENVIROCHEM_PWC_PATH"
    assert isinstance(catalog["MACRO"]["path_exists"], bool)


def test_spin_template_and_tscf_guard_are_model_specific():
    data = deepcopy(MODEL_PROFILES["SPIN"]["input_template"])
    validation = validate_external_model_inputs("SPIN", data)
    assert "substance_identity" in validation["missing_inputs"]
    data["substance_properties"] = {
        "koc_or_freundlich": 500,
        "water_solubility_mg_l": 17.7,
        "vapour_pressure_pa": 0.0002,
        "soil_dt50_days": 35,
        "tscf": 0.5,
    }
    validation = validate_external_model_inputs("SPIN", data)
    assert any("TSCF is 0.5" in warning for warning in validation["warnings"])


def test_macro_manifest_preserves_route_and_official_version_context():
    data = deepcopy(MODEL_PROFILES["MACRO"]["input_template"])
    manifest = prepare_workflow_manifest({
        "project_id": 1,
        "chemical_id": 1,
        "model_key": "MACRO",
        "jurisdiction": "EU",
        "tier": 3,
        "scenario_name": "FOCUS drainage preparation",
        "input_data": data,
        "executable_path": None,
    }, model("MACRO"))
    validation = manifest["model_specific_validation"]
    assert "5.5.4a" in validation["official_version"]
    assert "execution_route" in manifest["missing_inputs"]
    assert "m2t" in ADAPTER_CONTRACTS["MACRO"]["accepted_output_formats"]


def test_greater_requires_basin_rights_and_crs():
    data = deepcopy(MODEL_PROFILES["GREATER"]["input_template"])
    data["basin_database"] = {"basin_id": "Rhine", "database_version": "2026", "rights_basis": None}
    data["georeferenced_river_network"] = {"dataset": "river.gpkg", "crs": None, "reach_identifier_field": "reach_id"}
    validation = validate_external_model_inputs("GREATER", data)
    assert "basin_database.rights_basis" in validation["missing_inputs"]
    assert "georeferenced_river_network.crs" in validation["missing_inputs"]


def test_model_specific_output_mapping_remains_review_gated():
    validation = validate_external_model_output("MACRO", {"groundwater_or_drainage_endpoint": 0.12})
    assert validation["review_required"] is True
    assert "run_log_reference" in validation["missing_recommended_outputs"]


def test_external_model_profiles_are_available_over_api():
    with TestClient(app) as client:
        catalog = client.get("/api/external-model-integrations")
        assert catalog.status_code == 200
        assert {row["key"] for row in catalog.json()} == {"SPIN", "MACRO", "GREATER", "PWC", "CHEMSTEER", "CEM", "EFAST"}
        macro = client.get("/api/external-model-integrations/macro")
        assert macro.status_code == 200
        assert macro.json()["key"] == "MACRO"
        missing = client.get("/api/external-model-integrations/not-a-model")
        assert missing.status_code == 404


def test_spin_workflow_full_prepare_import_review_lifecycle():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "SPIN integration lifecycle"}).json()
        chemical = next(row for row in client.get("/api/chemicals").json() if row["preferred_name"] == "Carbamazepine")
        prepared = client.post("/api/model-workflows", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "model_key": "SPIN",
            "jurisdiction": "EU",
            "tier": 2,
            "scenario_name": "Reviewed SPIN dependency record",
            "input_data": {
                "substance_identity": {"preferred_name": "Carbamazepine", "cas_number": "298-46-4", "molecular_weight_g_mol": 236.27},
                "substance_properties": {"koc_or_freundlich": 500, "water_solubility_mg_l": 17.7, "vapour_pressure_pa": 0.0002, "soil_dt50_days": 35, "tscf": 0},
                "transformation_pathway": {"parent_key": "CBZ", "metabolites": [], "formation_fractions": []},
                "host_model_targets": {"models": ["PEARL", "MACRO"]},
                "database_version": {"spin_version": "4.4", "record_revision": "review-1"},
            },
            "executable_path": None,
        })
        assert prepared.status_code == 200, prepared.text
        workflow = prepared.json()
        assert workflow["status"] == "prepared"
        assert workflow["manifest"]["missing_inputs"] == []

        imported = client.post(f"/api/model-workflows/{workflow['id']}/import-output", json={
            "raw_output_text": "substance_record_snapshot=CBZ review-1\ntransformation_pathway=parent only\nspin_database_version=4.4",
            "structured_outputs": {},
            "model_version": "4.4",
            "executable_version": "4.4",
            "execution_notes": "Dependency record reviewed in standalone SPIN",
        })
        assert imported.status_code == 200, imported.text
        output_validation = imported.json()["output_record"]["model_specific_validation"]
        assert output_validation["review_required"] is False

        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "Integration test reviewer",
            "decision": "accepted",
            "notes": "Record snapshot and version checked",
        })
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "reviewed"
