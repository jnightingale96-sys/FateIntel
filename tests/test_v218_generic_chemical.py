from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import BUILD_ID, app
from app.services.evidence_sources import extract_endpoint_candidates_from_text
from app.services.identity import identity_hash


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


def diclofenac_candidate() -> dict:
    candidate = {
        "source_key": "pubchem",
        "source_record_id": "CID:3033",
        "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/3033",
        "pubchem_cid": 3033,
        "query_text": "diclofenac",
        "query_mode": "iupac",
        "preferred_name": "Diclofenac",
        "cas_number": "15307-86-5",
        "cas_candidates": ["15307-86-5"],
        "molecular_formula": "C14H11Cl2NO2",
        "molecular_weight_g_mol": 296.15,
        "smiles": "O=C(O)Cc1ccccc1Nc1c(Cl)cccc1Cl",
        "inchikey": "DCOPUUMXTXDBNB-UHFFFAOYSA-N",
        "substance_form": "parent",
        "xlogp_candidate": 4.5,
        "warnings": ["QA identity candidate"],
    }
    candidate["identity_hash"] = identity_hash(candidate)
    return candidate


def create_project(client: TestClient, prefix: str) -> dict:
    response = client.post("/api/projects", json={
        "name": f"{prefix}-{uuid4()}",
        "jurisdiction": "EU + UK",
        "purpose": "v2.19 inherited generic-chemical regression",
    })
    assert response.status_code == 201
    return response.json()


def confirm_diclofenac(client: TestClient, project_id: int) -> dict:
    response = client.post("/api/chemicals/from-resolved-identity", json={
        "project_id": project_id,
        "candidate": diclofenac_candidate(),
        "user_confirmed": True,
    })
    assert response.status_code == 201, response.text
    return response.json()


def reviewed_diclofenac_profile() -> dict:
    # These are deliberately labelled QA inputs; the test verifies binding and
    # mass balance, not that the numbers are selected regulatory values.
    return {
        "ionisation_class": "acid",
        "log_kow": 4.5,
        "pkaa": 4.15,
        "pkab": None,
        "water_solubility_mg_l": 0.01,
        "vapour_pressure_pa": 0.0001,
        "soil_dt50_days": 30,
        "wwtp_biodegradation_fraction": 0.2,
        "wwtp_primary_sludge_fraction": 0.1,
        "wwtp_secondary_sludge_fraction": 0.1,
        "wwtp_volatilisation_fraction": 0,
        "source_summary": "QA-only reviewed inputs for generic chemical binding regression.",
        "provenance": {"status": "qa_fixture_not_regulatory"},
        "reviewer_confirmation": True,
    }


def test_identity_resolution_returns_candidate_without_creating_record(monkeypatch):
    candidate = diclofenac_candidate()
    monkeypatch.setattr("app.main.resolve_pubchem_identity", lambda query, mode: candidate)
    with TestClient(app) as client:
        before = {row["id"] for row in client.get("/api/chemicals").json()}
        response = client.post("/api/identities/resolve", json={"query": "unseeded diclofenac QA", "query_mode": "iupac"})
        assert response.status_code == 200
        assert response.json()["candidate"]["identity_hash"] == candidate["identity_hash"]
        after = {row["id"] for row in client.get("/api/chemicals").json()}
        assert after == before


def test_diclofenac_confirmation_profile_gate_and_custom_wwtp_lifecycle():
    with TestClient(app) as client:
        project = create_project(client, "Diclofenac")
        confirmed = confirm_diclofenac(client, project["id"])
        chemical = confirmed["chemical"]
        assert chemical["preferred_name"] == "Diclofenac"
        assert chemical["cas_number"] == "15307-86-5"
        assert confirmed["profile"]["review_status"] == "draft"

        readiness_url = f"/api/projects/{project['id']}/chemicals/{chemical['id']}/guided-readiness?release=wastewater"
        blocked = client.get(readiness_url).json()
        assert blocked["ready"] is False
        assert "reviewer_confirmation" in blocked["missing"]
        assert blocked["wwtp_model_mode"] == "custom_screening"

        saved = client.put(
            f"/api/projects/{project['id']}/chemicals/{chemical['id']}/assessment-profile",
            json=reviewed_diclofenac_profile(),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["profile_origin"] == "reviewed_custom"
        ready = client.get(readiness_url).json()
        assert ready["ready"] is True
        assert ready["wwtp_model_mode"] == "custom_screening"

        sorption_payload = {
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "assessment_profile_id": saved.json()["id"],
            "scenario_name": "Diclofenac reviewed-profile sorption QA",
            "mode": "acid",
            "neutral_variant": "publication",
            "base_variant": "franco_trapp",
            "log_kow": 4.5,
            "pkaa": 4.15,
            "soil_ph": 7.0,
            "organic_carbon_fraction": 0.02,
            "ionic_strength_mol_l": 0.01,
        }
        sorption = client.post("/api/model-runs/sorption", json=sorption_payload)
        assert sorption.status_code == 200, sorption.text
        assert sorption.json()["outputs"]["ionisation_class"] == "acid"
        sorption_payload["log_kow"] = 2.45
        blocked_sorption = client.post("/api/model-runs/sorption", json=sorption_payload)
        assert blocked_sorption.status_code == 422
        assert "reviewed assessment profile" in blocked_sorption.text

        mismatched_identity = client.post("/api/model-runs/emission", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "scenario_name": "Identity mismatch must fail",
            "emission_mode": "direct_daily_use",
            "parent_name": "Carbamazepine",
            "parent_molecular_weight_g_mol": 236.27,
            "daily_active_amount": 10,
            "daily_active_unit": "g",
            "emitting_days_per_year": 365,
            "population": 100000,
            "wastewater_l_person_day": 200,
            "direct_to_sewer_fraction": 1,
            "systemic_fraction": 0,
            "parent_urine_fraction": 0,
            "parent_faeces_fraction": 0,
            "metabolites": [],
        })
        assert mismatched_identity.status_code == 422
        assert "parent name does not match" in mismatched_identity.text

        emission = client.post("/api/model-runs/emission", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "scenario_name": "Diclofenac QA daily-use emission",
            "emission_mode": "direct_daily_use",
            "parent_name": "Diclofenac",
            "parent_molecular_weight_g_mol": 296.15,
            "daily_active_amount": 10,
            "daily_active_unit": "g",
            "emitting_days_per_year": 365,
            "population": 100000,
            "wastewater_l_person_day": 200,
            "direct_to_sewer_fraction": 1,
            "systemic_fraction": 0,
            "parent_urine_fraction": 0,
            "parent_faeces_fraction": 0,
            "metabolites": [],
            "consumption_source_title": "QA fixture",
        })
        assert emission.status_code == 200, emission.text
        custom_payload = {
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "assessment_profile_id": saved.json()["id"],
            "emission_model_run_id": emission.json()["model_run_id"],
            "species_key": "parent",
            "scenario_name": "Diclofenac custom WWTP QA",
            "model_mode": "custom_screening",
            "biodegradation_fraction": 0.2,
            "primary_sludge_fraction": 0.1,
            "secondary_sludge_fraction": 0.1,
            "volatilisation_fraction": 0,
            "post_wwtp_biodegradation_fraction": 0,
            "receiving_water_dilution_factor": 10,
            "sludge_to_soil_fraction": 0.1,
            "mixed_soil_mass_kg": 2_000_000,
        }
        wwtp = client.post("/api/model-runs/activity-simpletreat", json=custom_payload)
        assert wwtp.status_code == 200, wwtp.text
        assert wwtp.json()["outputs"]["model_mode"] == "custom_screening"
        assert wwtp.json()["outputs"]["pathway_fractions"]["effluent"] == pytest.approx(0.6)

        biosolids = client.post("/api/model-runs/biosolids", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "assessment_profile_id": saved.json()["id"],
            "activity_simpletreat_model_run_id": wwtp.json()["model_run_id"],
            "source_mode": "wwtp_chemical_mass",
            "chemical_mass_to_sludge_kg_day": wwtp.json()["outputs"]["sludge_mass_kg_day"],
            "operating_days_per_year": 365,
            "fraction_sludge_land_applied": 1,
            "land_application_area_ha": 100,
            "storage_days": 30,
            "storage_dt50_days": None,
            "soil_mixing_depth_m": 0.2,
            "soil_bulk_density_kg_m3": 1500,
            "soil_dt50_days": 30,
            "assessment_years": 10,
            "runoff_fraction": 0,
            "leaching_fraction": 0,
        })
        assert biosolids.status_code == 200, biosolids.text

        irrigation_payload = {
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "assessment_profile_id": saved.json()["id"],
            "sorption_model_run_id": sorption.json()["model_run_id"],
            "activity_simpletreat_model_run_id": wwtp.json()["model_run_id"],
            "chemical_name": "Diclofenac",
            "cas_number": "15307-86-5",
            "kd_l_kg": sorption.json()["outputs"]["selected"]["kd_l_kg"],
            "soil_dt50_days": 30,
            "water_solubility_mg_l": 0.01,
            "vapour_pressure_pa": 0.0001,
        }
        irrigation = client.post("/api/model-runs/wastewater-irrigation-comparison", json=irrigation_payload)
        assert irrigation.status_code == 200, irrigation.text
        irrigation_payload["chemical_name"] = "Carbamazepine"
        blocked_irrigation = client.post("/api/model-runs/wastewater-irrigation-comparison", json=irrigation_payload)
        assert blocked_irrigation.status_code == 422
        assert "reviewed assessment profile or identity" in blocked_irrigation.text

        custom_payload["biodegradation_fraction"] = 0.21
        blocked_mismatch = client.post("/api/model-runs/activity-simpletreat", json=custom_payload)
        assert blocked_mismatch.status_code == 422
        assert "reviewed assessment profile" in blocked_mismatch.text
        custom_payload["biodegradation_fraction"] = 0.2
        custom_payload["model_mode"] = "supplied_workbook_9box_preset"
        blocked_preset = client.post("/api/model-runs/activity-simpletreat", json=custom_payload)
        assert blocked_preset.status_code == 422
        assert "expected custom_screening" in blocked_preset.text


def test_carbamazepine_benchmark_remains_identity_locked_and_ready():
    with TestClient(app) as client:
        project = create_project(client, "Carbamazepine-benchmark")
        chemical = next(row for row in client.get("/api/chemicals").json() if row["cas_number"] == "298-46-4")
        attached = client.post(f"/api/projects/{project['id']}/chemicals/{chemical['id']}")
        assert attached.status_code == 201
        readiness = client.get(
            f"/api/projects/{project['id']}/chemicals/{chemical['id']}/guided-readiness?release=wastewater"
        ).json()
        assert readiness["ready"] is True
        assert readiness["wwtp_model_mode"] == "supplied_workbook_9box_preset"
        assert readiness["profile"]["profile_origin"] == "protected_carbamazepine_benchmark"


def test_evidence_candidate_cannot_be_staged_against_another_identity():
    with TestClient(app) as client:
        project = create_project(client, "Evidence-contamination")
        diclofenac = confirm_diclofenac(client, project["id"])["chemical"]
        carbamazepine = next(row for row in client.get("/api/chemicals").json() if row["cas_number"] == "298-46-4")
        client.post(f"/api/projects/{project['id']}/chemicals/{carbamazepine['id']}")
        candidate = {
            "candidate_id": "diclo-logkow-qa",
            "source_key": "pubchem",
            "source_record_id": "CID:3033",
            "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/3033",
            "chemical_name": "Diclofenac",
            "cas_number": "15307-86-5",
            "property_code": "PHYS.LOGKOW",
            "value": 4.5,
            "unit": "dimensionless",
            "rights_status": "third_party_annotation_source_terms_apply",
            "import_allowed": True,
        }
        response = client.post("/api/evidence-sources/import-candidate", json={
            "project_id": project["id"],
            "chemical_id": carbamazepine["id"],
            "candidate": candidate,
        })
        assert response.status_code == 422
        assert "CAS does not match" in response.text
        assert diclofenac["id"] != carbamazepine["id"]


def test_property_candidates_cover_generic_profile_fields():
    rows = extract_endpoint_candidates_from_text(
        "Water solubility: 2.5 mg/L at 20 C. Vapor pressure: 1.2E-5 Pa. log Kow = 4.5. pKa = 4.15. Aerobic soil DT50 = 30 days.",
        source_key="pubchem",
        source_name="PubChem",
        chemical_name="Diclofenac",
        cas_number="15307-86-5",
        source_record_id="CID:3033",
    )
    keyed = {row["property_code"]: row for row in rows}
    assert keyed["PHYS.WATER_SOLUBILITY"]["value"] == pytest.approx(2.5)
    assert keyed["PHYS.VAPOUR_PRESSURE"]["value"] == pytest.approx(1.2e-5)
    assert keyed["PHYS.LOGKOW"]["value"] == pytest.approx(4.5)
    assert keyed["PHYS.PKA"]["value"] == pytest.approx(4.15)
    assert keyed["FATE.SOIL_DT50"]["value"] == pytest.approx(30)


def test_v219_guided_ui_uses_confirmed_identity_and_reviewed_profile_contract():
    assert "v2.23" in BUILD_ID and "8792" not in BUILD_ID
    for marker in (
        'id="identity-candidate"', 'id="confirm-identity"', 'id="chemical-profile-panel"',
        'id="profile-logkow"', 'id="profile-wwtp-bio"', 'id="profile-reviewed"',
    ):
        assert marker in HTML
    assert "/api/identities/resolve" in JS
    assert "/api/chemicals/from-resolved-identity" in JS
    assert "refreshGuidedReadiness" in JS
    assert "parent_name:state.chemical.preferred_name" in JS
    assert "model_mode:readiness.wwtp_model_mode" in JS
    assert "Evidence staging blocked" in JS
