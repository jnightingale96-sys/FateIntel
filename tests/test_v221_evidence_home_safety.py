from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import BUILD_ID, app


ROOT = Path(__file__).resolve().parents[1]
EXPERT_HTML = (ROOT / "app" / "static" / "expert.html").read_text(encoding="utf-8")
EXPERT_JS = (ROOT / "app" / "static" / "expert-app.js").read_text(encoding="utf-8")


def _home_payload() -> dict:
    return {
        "product_identifier": "manual-reference-123",
        "product_name": "QA household product",
        "chemical_name": "User-entered chemical",
        "amount_value": 10,
        "amount_unit": "mL",
        "frequency_value": 1,
        "frequency_unit": "week",
        "release_route": "down_drain",
        "log_kow": 1.5,
        "koc_l_kg": 100,
        "soil_dt50_days": 20,
    }


def test_unbound_home_summary_is_explicitly_qualitative():
    with TestClient(app) as client:
        response = client.post("/api/home-use-summary", json=_home_payload())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["scope"]["screening_type"] == "qualitative_household_use_fate_summary"
    assert result["scope"]["pec_calculated"] is False
    assert result["scope"]["pnec_used"] is False
    assert result["scope"]["risk_quotient_calculated"] is False
    assert result["identity_binding"] is None
    assert any("barcode" in warning.lower() for warning in result["warnings"])


def test_home_summary_can_bind_confirmed_identity_and_reviewed_profile():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={
            "name": f"Home binding QA {uuid4()}",
            "jurisdiction": "UK/EU screening",
            "purpose": "v2.21 home-use binding test",
        }).json()
        resolved = client.post("/api/identities/resolve", json={
            "query": "298-46-4",
            "query_mode": "cas",
        })
        assert resolved.status_code == 200, resolved.text
        confirmed = client.post("/api/chemicals/from-resolved-identity", json={
            "project_id": project["id"],
            "candidate": resolved.json()["candidate"],
            "user_confirmed": True,
        })
        assert confirmed.status_code == 201, confirmed.text
        chemical = confirmed.json()["chemical"]
        profile = confirmed.json()["profile"]

        payload = _home_payload() | {
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "assessment_profile_id": profile["id"],
            "bind_to_reviewed_profile": True,
            "chemical_name": "This text must be replaced",
            "log_kow": 99,
            "soil_dt50_days": 999,
        }
        response = client.post("/api/home-use-summary", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["chemical_name"] == "Carbamazepine"
    assert result["identity_binding"]["chemical_id"] == chemical["id"]
    assert result["identity_binding"]["identity_hash"]
    basis = {item["field"]: item for item in result["input_basis"]}
    assert basis["chemical_identity"]["status"] == "confirmed"
    assert basis["log_kow"]["status"] == "reviewed"
    assert basis["soil_dt50_days"]["status"] == "reviewed"
    assert basis["koc_l_kg"]["status"] == "not_reviewed_here"


def test_partial_profile_binding_is_rejected():
    payload = _home_payload() | {"project_id": 1}
    with TestClient(app) as client:
        response = client.post("/api/home-use-summary", json=payload)
    assert response.status_code == 422
    assert "bind_to_reviewed_profile" in response.text


def test_evidence_records_include_canonical_provenance_hash():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={
            "name": f"Evidence provenance QA {uuid4()}",
            "jurisdiction": "UK/EU screening",
            "purpose": "v2.21 provenance test",
        }).json()
        chemical = next(row for row in client.get("/api/chemicals").json() if row["cas_number"] == "298-46-4")
        client.post(f"/api/projects/{project['id']}/chemicals/{chemical['id']}")
        created = client.post("/api/evidence", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "source": {"title": "Canonical provenance QA", "identifier": "QA:V221"},
            "property_code": "FATE.SOIL_DT50",
            "original_value": 42,
            "original_unit": "days",
            "temperature_c": 20,
            "representative_group_key": "qa-v221",
        })
        assert created.status_code == 201, created.text
        rows = client.get(f"/api/projects/{project['id']}/chemicals/{chemical['id']}/evidence").json()
    record = next(row for row in rows if row["id"] == created.json()["id"])
    assert len(record["provenance_hash"]) == 64
    assert all(character in "0123456789abcdef" for character in record["provenance_hash"])


def test_v221_ui_uses_real_workspace_data_not_the_supplied_mock_scaffold():
    assert "v2.24" in BUILD_ID
    assert 'id="evidence-filter"' in EXPERT_HTML
    assert 'id="provenance-dialog"' in EXPERT_HTML
    assert 'id="h-use-selected"' in EXPERT_HTML
    assert "renderEvidenceTable" in EXPERT_JS
    assert "bind_to_reviewed_profile" in EXPERT_JS
    assert "AI Copilot" not in EXPERT_HTML
    assert "Barcode (mock)" not in EXPERT_HTML
    assert "IUCLID XML" not in EXPERT_HTML
