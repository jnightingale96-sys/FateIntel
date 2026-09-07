"""Adversarial regression coverage for the Alpha 3.2.1 trust-and-release hotfix.

An external audit of the Alpha 3.2 ZIP demonstrated, end to end, that:
(a) every field in the pesticide-model forms accepted the literal string
    "not-a-number" and still reached workflow status "prepared";
(b) a workflow could be marked "reviewed" after importing nothing but
    `nonsense=1` via the plain /import-output route.
Both were independently reproduced against the live app before this hotfix,
and are captured here as permanent regressions to guard against reintroducing
either gap.
"""
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _chemical(client: TestClient) -> dict:
    return next(row for row in client.get("/api/chemicals").json() if row["preferred_name"] == "Carbamazepine")


def _project(client: TestClient, label: str) -> dict:
    return client.post("/api/projects", json={"name": f"{label} {uuid4().hex[:8]}", "jurisdiction": "US"}).json()


def _prepare(client: TestClient, model_key: str, input_data: dict) -> dict:
    project = _project(client, f"{model_key} review-gate QA")
    response = client.post("/api/model-workflows", json={
        "project_id": project["id"],
        "chemical_id": _chemical(client)["id"],
        "model_key": model_key,
        "jurisdiction": "US",
        "tier": 2,
        "scenario_name": f"{model_key} review-gate QA",
        "input_data": input_data,
    })
    assert response.status_code == 200, response.text
    return response.json()


NONSENSE_AGDRIFT_INPUTS = {
    "contaminant_group": "pesticide",
    "application_parameters": {"application_method": "not-a-number", "boom_height_m": "not-a-number", "droplet_size_category": "not-a-number", "application_rate_kg_ha": "not-a-number"},
    "meteorological_conditions": {"wind_speed_m_s": "not-a-number"},
    "buffer_and_geometry": {"buffer_distance_m": "not-a-number", "waterbody_width_m": "not-a-number"},
}

NONSENSE_PWC_INPUTS = {
    "contaminant_group": "pesticide",
    "application_pattern": {"application_rate_kg_ha": "not-a-number", "number_of_applications": "not-a-number", "application_method": "aerial"},
    "pwc3_us_scenario": {"scenario_id": "x", "crop": "x"},
    "soil_and_crop_inputs": {"crop": "x"},
    "weather_series": {"weather_station_id": "x"},
    "soil_dt50": {"value_days": "not-a-number", "source": "x"},
    "koc_or_kd": {"value": "not-a-number", "unit": "L/kg"},
    "aquatic_fate_inputs": {},
    "groundwater_and_waterbody_configuration": {"waterbody_type": "index_pond", "depth_m": "not-a-number"},
}


def test_nonnumeric_agdrift_inputs_never_reach_prepared():
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", NONSENSE_AGDRIFT_INPUTS)
        assert workflow["status"] != "prepared", "nonsense numeric strings must not satisfy AgDRIFT's required inputs"
        assert workflow["manifest"]["missing_inputs"], "at least one field must be reported missing/invalid"


def test_nonnumeric_pwc_inputs_never_reach_prepared():
    with TestClient(app) as client:
        workflow = _prepare(client, "PWC", NONSENSE_PWC_INPUTS)
        assert workflow["status"] != "prepared"
        missing = workflow["manifest"]["missing_inputs"]
        assert any("must be numeric" in item for item in missing), missing


def test_plain_text_import_can_never_reach_reviewed_for_any_model():
    # Exact reproduction of the audited AgDRIFT bypass: prepare with garbage,
    # import only "nonsense=1" via the plain /import-output route, attempt to
    # accept the review. Must be rejected, not silently marked "reviewed".
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", {
            "contaminant_group": "pesticide",
            "application_parameters": {"a": 1}, "meteorological_conditions": {"a": 1}, "buffer_and_geometry": {"a": 1},
        })
        imported = client.post(f"/api/model-workflows/{workflow['id']}/import-output", json={"raw_output_text": "nonsense=1"})
        assert imported.status_code == 200, imported.text
        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "adversarial bypass attempt",
        })
        assert reviewed.status_code == 409, reviewed.text
        assert "genuine" in reviewed.json()["detail"].lower()


def test_hashed_file_import_now_available_to_a_previously_blocked_model():
    # Before this hotfix, /import-output-files was hard-restricted to
    # EPA_EXECUTION_MODEL_KEYS ({PWC, CHEMSTEER, CEM, EFAST}); AgDRIFT (outside
    # that set) had no way to produce genuine provenance at all. Confirm the
    # route is now open to it, and that a genuine import can actually reach
    # "reviewed" -- the fix must open a real path, not just close the old one.
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", {
            "contaminant_group": "pesticide",
            "application_parameters": {"application_method": "aerial", "boom_height_m": 2, "droplet_size_category": "medium", "application_rate_kg_ha": 1.1},
            "meteorological_conditions": {"wind_speed_m_s": 3},
            "buffer_and_geometry": {"buffer_distance_m": 30, "waterbody_width_m": 10},
        })
        assert workflow["status"] == "prepared", workflow

        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Adversarial-test genuine import",
                "structured_outputs_json": json.dumps({
                    "off_site_deposition_fraction": 0.02, "downwind_deposition_curve": "QA curve",
                }),
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("agdrift_result.txt", b"off_site_deposition_fraction=0.02", "text/plain")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["output_record"]["execution_provenance"]["real_execution"] is True

        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "genuine hashed-file import",
        })
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "reviewed"
