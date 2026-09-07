from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas import USIndustrialExposureRunCreate
from app.services.identity import core_identity_hash, identity_hash
from app.services.us_exposure import (
    manifest,
    scenario_catalogue,
    run_industrial_exposure_screen,
)


def payload() -> dict:
    return {
        "project_id": 1,
        "chemical_id": 1,
        "scenario_name": "Adhesive use screening case",
        "source_scenario_key": "use_of_adhesives",
        "chemical_throughput_kg_day": 100,
        "operating_days_year": 250,
        "release_events": [{
            "event_key": "application_loss",
            "name": "Application and curing loss",
            "loss_fraction": 0.1,
            "control_efficiency_fraction": 0.5,
            "media_fractions": {"air": 0.2, "water": 0.8},
            "control_destination": "landfill",
            "evidence_status": "scenario_default",
            "source_reference": "EPA Use of Adhesives ESD; parameter is a QA fixture",
        }],
        "worker_tasks": [{
            "task_name": "Adhesive application",
            "inhalation_mode": "measured_air",
            "task_duration_hours": 8,
            "exposure_days_year": 250,
            "body_weight_kg": 80,
            "inhalation_rate_m3_hour": 1.25,
            "respirator_apf": 2,
            "inhalation_absorption_fraction": 1,
            "measured_air_concentration_mg_m3": 2,
            "dermal_contact_mg_shift": 20,
            "glove_protection_factor": 4,
            "dermal_absorption_fraction": 0.1,
        }],
        "citations": [{
            "source_key": "epa_use_of_adhesives_esd",
            "reference": "EPA Use of Adhesives ESD",
            "evidence_status": "scenario_default",
        }],
        "uncertainty_notes": "QA fixture values; replace with site and chemical evidence.",
        "scientist_review_confirmed": False,
    }


def test_source_catalogue_separates_published_and_draft_scenarios():
    info = manifest()
    assert info["scenario_count"] == 60
    assert info["scenario_status_counts"] == {"published": 12, "draft": 48}
    assert len(scenario_catalogue()) == 12
    assert all(row["default_enabled"] for row in scenario_catalogue())
    drafts = scenario_catalogue(status="draft")
    assert len(drafts) == 48
    assert not any(row["default_enabled"] for row in drafts)


def test_industrial_screen_closes_mass_and_keeps_waste_as_transfer():
    parsed = USIndustrialExposureRunCreate.model_validate(payload())
    result = run_industrial_exposure_screen(parsed.model_dump())
    assert result["releases"]["daily_kg"]["air"] == pytest.approx(1)
    assert result["releases"]["daily_kg"]["water"] == pytest.approx(4)
    assert result["releases"]["daily_kg"]["landfill"] == pytest.approx(5)
    assert result["releases"]["retained_or_unmodelled_process_mass_kg_day"] == pytest.approx(90)
    assert result["mass_balance"]["closure_error_kg_day"] == pytest.approx(0, abs=1e-12)
    assert result["regulatory_equivalence"] is False
    assert "transfer" in " ".join(result["warnings"]).lower()


def test_measured_worker_routes_and_ppe_are_explicit():
    parsed = USIndustrialExposureRunCreate.model_validate(payload())
    worker = run_industrial_exposure_screen(parsed.model_dump())["worker_exposure"][0]
    assert worker["inhaled_external_mg_shift"] == pytest.approx(10)
    assert worker["dermal_external_mg_shift"] == pytest.approx(5)
    assert worker["dermal_absorbed_mg_shift"] == pytest.approx(0.5)
    assert worker["total_absorbed_mg_shift"] == pytest.approx(10.5)
    assert worker["acute_absorbed_dose_mg_kg_shift"] == pytest.approx(10.5 / 80)


def test_well_mixed_screen_uses_time_averaged_build_up():
    data = payload()
    data["worker_tasks"] = [{
        "task_name": "Powder charging",
        "inhalation_mode": "well_mixed_screen",
        "task_duration_hours": 2,
        "exposure_days_year": 100,
        "body_weight_kg": 80,
        "inhalation_rate_m3_hour": 1,
        "respirator_apf": 1,
        "inhalation_absorption_fraction": 1,
        "chemical_handled_kg_per_shift": 0.001,
        "airborne_release_fraction": 0.1,
        "local_exhaust_control_fraction": 0,
        "room_volume_m3": 100,
        "air_exchange_rate_per_hour": 1,
        "dermal_contact_mg_shift": 0,
    }]
    parsed = USIndustrialExposureRunCreate.model_validate(data)
    worker = run_industrial_exposure_screen(parsed.model_dump())["worker_exposure"][0]
    # G=50 mg/h, Css=0.5 mg/m3 and the two-hour build-up factor is ~0.568.
    assert worker["generation_rate_mg_hour"] == pytest.approx(50)
    assert worker["air_concentration_mg_m3"] == pytest.approx(0.2838338, rel=1e-6)


def test_soil_release_can_be_screened_to_groundwater_with_explicit_equations():
    data = payload()
    data["release_events"][0]["media_fractions"] = {"air": 0.2, "water": 0.3, "soil": 0.5}
    data["groundwater_screen"] = {
        "soil_release_area_ha": 2,
        "source_zone_depth_m": 0.2,
        "assessment_depth_m": 1,
        "soil_bulk_density_kg_m3": 1500,
        "volumetric_water_content": 0.25,
        "annual_recharge_mm": 250,
        "koc_l_kg": 100,
        "soil_organic_carbon_fraction": 0.02,
        "soil_dt50_days": 365,
        "additional_attenuation_fraction": 1,
        "parameter_source": "QA soil and recharge fixture",
    }
    parsed = USIndustrialExposureRunCreate.model_validate(data)
    result = run_industrial_exposure_screen(parsed.model_dump())
    groundwater = result["groundwater_leaching"]
    assert groundwater["status"] == "screened"
    assert groundwater["kd_l_kg"] == pytest.approx(2)
    assert groundwater["retardation_factor"] > 1
    assert groundwater["screened_groundwater_concentration_ug_l"] >= 0
    assert "retardation" in groundwater["equations"]
    assert any("not PWC" in row for row in groundwater["limitations"])
    fate = next(row for row in result["completeness"]["sections"] if row["key"] == "fate_transport")
    assert fate["complete"] is True


def test_soil_release_without_groundwater_inputs_remains_visible_gap():
    data = payload()
    data["release_events"][0]["media_fractions"] = {"soil": 1}
    result = run_industrial_exposure_screen(USIndustrialExposureRunCreate.model_validate(data).model_dump())
    assert result["groundwater_leaching"]["status"] == "not_assessed"
    assert any("groundwater leaching was not screened" in row for row in result["warnings"])


def test_schema_rejects_double_counted_events_and_unclosed_media_split():
    data = payload()
    data["release_events"][0]["media_fractions"] = {"air": 0.7}
    with pytest.raises(ValidationError, match="must sum to 1"):
        USIndustrialExposureRunCreate.model_validate(data)
    data = payload()
    data["release_events"].append({
        **data["release_events"][0],
        "event_key": "second",
        "loss_fraction": 0.95,
    })
    with pytest.raises(ValidationError, match="cannot sum to more than 1"):
        USIndustrialExposureRunCreate.model_validate(data)


def _candidate(namespace: str) -> dict:
    qa_cas = f"9{int(namespace[:4], 16):04d}-{int(namespace[4:6], 16):02d}-7"
    row = {
        "source_key": "pubchem",
        "source_record_id": f"US-EXPOSURE-QA-{namespace}",
        "source_url": f"https://example.invalid/us-exposure/{namespace}",
        "query_text": "Toluene",
        "query_mode": "iupac",
        "preferred_name": f"Toluene US exposure QA {namespace}",
        "cas_number": qa_cas,
        "cas_candidates": [qa_cas],
        "molecular_formula": "C7H8",
        "molecular_weight_g_mol": 92.14,
        "smiles": "Cc1ccccc1",
        "inchikey": f"YXFVVABEGXRONW-{namespace.upper()}-N",
        "substance_form": "parent",
        "warnings": ["QA fixture only"],
    }
    row["identity_hash"] = identity_hash(row)
    row["core_identity_hash"] = core_identity_hash(row)
    return row


def test_api_persists_screen_with_immutable_identity_binding():
    namespace = uuid4().hex[:10]
    with TestClient(app) as client:
        project = client.post(
            "/api/projects",
            json={"name": f"US-exposure-{namespace}", "jurisdiction": "US"},
        ).json()
        confirmed = client.post(
            "/api/chemicals/from-resolved-identity",
            json={
                "project_id": project["id"],
                "candidate": _candidate(namespace),
                "user_confirmed": True,
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        chemical = confirmed.json()["chemical"]
        request = payload()
        request["project_id"] = project["id"]
        request["chemical_id"] = chemical["id"]
        response = client.post("/api/model-runs/us-industrial-exposure", json=request)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["outputs"]["mass_balance"]["closure_error_kg_day"] == pytest.approx(0)
        binding = client.get(
            f"/api/model-runs/{result['model_run_id']}/identity-binding"
        )
        assert binding.status_code == 200
        assert binding.json()["chemical_id"] == chemical["id"]


def test_catalogue_and_completeness_api_contracts():
    with TestClient(app) as client:
        assert len(client.get("/api/us-exposure/scenarios").json()) == 12
        assert len(client.get("/api/us-exposure/scenarios?status=draft").json()) == 48
        response = client.post(
            "/api/us-exposure/completeness",
            json={"identity_confirmed": True, "uses_and_volumes": True},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["complete_count"] == 2
        assert result["assessment_complete"] is False
        assert any(row["key"] == "waste_disposal" for row in result["missing"])
