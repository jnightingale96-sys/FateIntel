from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.external_execution import external_tool_status


def _chemical(client: TestClient) -> dict:
    return next(row for row in client.get("/api/chemicals").json() if row["preferred_name"] == "Carbamazepine")


def _complete_pwc_inputs() -> dict:
    return {
        "contaminant_group": "pesticide",
        "application_pattern": {"rate_kg_ha": 1, "applications": 1},
        "pwc3_us_scenario": {"scenario": "QA fixture", "version": "test"},
        "soil_and_crop_inputs": {"crop": "QA crop", "soil": "QA soil"},
        "weather_series": {"file": "QA weather", "version": "test"},
        "soil_dt50": {"value": 30, "unit": "days"},
        "koc_or_kd": {"value": 100, "unit": "L/kgOC"},
        "aquatic_fate_inputs": {"water_dt50_days": 20, "sediment_dt50_days": 40},
        "groundwater_and_waterbody_configuration": {"groundwater": True, "surface_water": True},
    }


def _complete_cem_inputs() -> dict:
    return {
        "chemical_identity_and_properties": {"name": "QA chemical", "molecular_weight": 100},
        "product_or_article_category": {"category": "QA product"},
        "chemical_weight_fraction": {"value": 0.01},
        "use_frequency_and_duration": {"frequency": 1, "duration_minutes": 10},
        "emission_model_selection": {"model": "reviewed QA selection"},
        "inhalation_dermal_ingestion_models": {"routes": ["inhalation", "dermal", "ingestion"]},
        "population_and_lifestage_factors": {"population": "adult QA"},
        "parameter_provenance": {"source": "QA fixture"},
    }


def _workflow(client: TestClient, model_key: str, input_data: dict) -> dict:
    project = client.post(
        "/api/projects", json={"name": f"EPA bridge {model_key} {uuid4().hex[:8]}", "jurisdiction": "US"}
    ).json()
    response = client.post("/api/model-workflows", json={
        "project_id": project["id"],
        "chemical_id": _chemical(client)["id"],
        "model_key": model_key,
        "jurisdiction": "US",
        "tier": 2,
        "scenario_name": f"{model_key} QA official workflow",
        "input_data": input_data,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "prepared"
    return result


def test_bridge_defaults_to_manual_handoff_without_server_configuration(monkeypatch):
    monkeypatch.setattr(settings, "envirochem_external_execution_enabled", False)
    monkeypatch.setattr(settings, "envirochem_pwc_path", None)
    monkeypatch.setattr(settings, "envirochem_pwc_command_args_json", None)
    monkeypatch.setattr(settings, "envirochem_pwc_output_globs_json", None)
    status = external_tool_status("PWC")
    assert status["execution_ready"] is False
    assert status["default_route"] == "manual_official_execution_and_hashed_import"
    assert any("false" in item for item in status["missing_requirements"])


def test_pinned_local_execution_captures_files_and_can_be_reviewed(tmp_path, monkeypatch):
    runner = tmp_path / "fake_official_runner.py"
    runner.write_text(
        """from pathlib import Path
import sys
manifest = Path(sys.argv[1])
output = Path(sys.argv[2])
assert manifest.is_file()
output.mkdir(parents=True, exist_ok=True)
(output / 'pwc_result.txt').write_text(
    'model_version=PWC3 QA\\n'
    'scenario_file_version=QA-1\\n'
    'surface_water_concentration=0.12\\n'
    'sediment_concentration=1.4\\n'
    'groundwater_concentration=0.03\\n'
    'raw_output_archive=captured fixture\\n', encoding='utf-8')
print('official_fixture_completed=true')
""",
        encoding="utf-8",
    )
    executable = Path(sys.executable).resolve()
    monkeypatch.setattr(settings, "envirochem_external_execution_enabled", True)
    monkeypatch.setattr(settings, "envirochem_pwc_path", executable)
    monkeypatch.setattr(
        settings,
        "envirochem_pwc_command_args_json",
        json.dumps([str(runner), "{manifest}", "{output_dir}"]),
    )
    monkeypatch.setattr(settings, "envirochem_pwc_output_globs_json", json.dumps(["output/*.txt"]))
    monkeypatch.setattr(settings, "envirochem_external_execution_timeout_seconds", 10)
    status = external_tool_status("PWC")
    assert status["execution_ready"] is True

    with TestClient(app) as client:
        workflow = _workflow(client, "PWC", _complete_pwc_inputs())
        executed = client.post(f"/api/model-workflows/{workflow['id']}/execute", json={
            "operator": "QA operator",
            "installed_version": "PWC3 QA fixture",
            "expected_executable_sha256": status["executable_sha256"],
            "confirm_authorised_installation": True,
            "confirm_unmodified_official_software": True,
        })
        assert executed.status_code == 200, executed.text
        result = executed.json()
        assert result["status"] == "execution_captured"
        provenance = result["output_record"]["execution_provenance"]
        assert provenance["real_execution"] is True
        assert provenance["succeeded"] is True
        assert provenance["artifacts"][0]["relative_path"] == "output/pwc_result.txt"
        assert len(provenance["artifacts"][0]["sha256"]) == 64

        accepted = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "Independent QA reviewer",
            "decision": "accepted",
            "notes": "Fixture endpoint map and process provenance checked",
        })
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "reviewed"


def test_manual_official_import_requires_original_files_and_complete_mapping():
    with TestClient(app) as client:
        workflow = _workflow(client, "CEM", _complete_cem_inputs())
        weak_import = client.post(f"/api/model-workflows/{workflow['id']}/import-output", json={
            "raw_output_text": "consumer_inhalation_exposure=1",
            "model_version": "3.2",
            "executable_version": "3.2",
        })
        assert weak_import.status_code == 409

        structured = {
            "model_version": "3.2",
            "product_or_article_category": "QA product",
            "consumer_inhalation_exposure": {"dose": 1.0},
            "consumer_dermal_exposure": {"dose": 2.0},
            "consumer_ingestion_exposure": {"dose": 3.0},
        }
        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "3.2",
                "executable_version": "3.2 QA build",
                "operator": "QA operator",
                "execution_notes": "Executed in the separately installed QA fixture",
                "structured_outputs_json": json.dumps(structured),
                "confirm_genuine_execution": "true",
                "confirm_authorised_installation": "true",
            },
            files={"files": ("cem-output.txt", b"CEM QA original output\n", "text/plain")},
        )
        assert imported.status_code == 200, imported.text
        result = imported.json()
        assert result["status"] == "output_imported"
        assert result["output_record"]["execution_provenance"]["real_execution"] is True
        assert len(result["output_record"]["source_files"][0]["sha256"]) == 64
        assert result["output_record"]["model_specific_validation"]["review_required"] is False


def test_handoff_zip_contains_manifest_checklist_and_checksums():
    with TestClient(app) as client:
        workflow = _workflow(client, "CEM", _complete_cem_inputs())
        response = client.get(f"/api/model-workflows/{workflow['id']}/handoff")
        assert response.status_code == 200
        with ZipFile(BytesIO(response.content)) as archive:
            names = set(archive.namelist())
            assert {"manifest.json", "EXECUTION_CHECKLIST.md", "SHA256SUMS.txt"}.issubset(names)
            checklist = archive.read("EXECUTION_CHECKLIST.md").decode("utf-8")
            assert "no official executable" in checklist.lower()
