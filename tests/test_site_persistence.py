"""Saved site models and metal measurements, and how measurements feed the site model's data flags.

Runs against a throwaway SQLite database (dependency override) so it never writes to the real project data.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import AuditEvent

SITE = {
    "name": "Former works, north yard",
    "jurisdiction": "UK",
    "sources": [{"id": "S1", "kind": "former_manufacturing", "release_media": ["soil"], "contaminants": [
        {"name": "lead", "contaminant_group": "metal_inorganic"},
        {"name": "PCB-153", "contaminant_group": "legacy_pop_organic", "cas_number": "1336-36-3"},
    ]}],
    "receptors": ["residents", "groundwater"],
    "links": [
        {"pathway": "ingestion", "from": "soil", "to": "residents"},
        {"pathway": "soil_to_groundwater", "from": "soil", "to": "groundwater"},
    ],
}

LEAD_SOIL = {
    "element": "Pb", "value": 350, "unit": "mg/kg", "basis": "total", "medium": "soil", "weight_basis": "dry",
    "source": "Lab report ABC-12, sample BH3 0.5 m", "site_medium": "soil",
}


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as c:
            c.session_factory = Session
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


def _project(client, name="Site test") -> int:
    response = client.post("/api/projects", json={"name": name, "jurisdiction": "UK", "purpose": "test"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _save(client, project_id, site=SITE):
    response = client.post(f"/api/projects/{project_id}/site-models", json=site)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _assessment(client, project_id, site_id):
    response = client.get(f"/api/projects/{project_id}/site-models/{site_id}/assessment")
    assert response.status_code == 200, response.text
    return response.json()


def _by_contaminant(assessment):
    out: dict[str, set[str]] = {}
    for linkage in assessment["linkages"]:
        out.setdefault(linkage["contaminant"], set()).add(linkage["status"])
    return out


def test_valid_measurement_is_saved_with_provenance_and_original_units(client):
    pid = _project(client)
    response = client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL)
    assert response.status_code == 201
    saved = response.json()
    assert (saved["value"], saved["unit"], saved["basis"], saved["weight_basis"]) == (350, "mg/kg", "total", "dry")
    assert saved["source"].startswith("Lab report ABC-12") and saved["origin"] == "measured"
    assert client.get(f"/api/projects/{pid}/metal-measurements").json()[0]["id"] == saved["id"]


@pytest.mark.parametrize("change, fragment", [
    ({"weight_basis": None}, "weight_basis"),
    ({"element": "lead"}, "chemical symbol"),
    ({"element": "C"}, "chemical symbol"),
    ({"source": ""}, "source"),
    ({"value": -1}, "non-negative"),
    ({"basis": "mostly dissolved"}, "basis"),
    ({"site_medium": "lava"}, "site_medium"),
    ({"unit": "mg/L"}, "concentrations must use"),
])
def test_invalid_measurements_are_rejected_never_defaulted(client, change, fragment):
    pid = _project(client)
    response = client.post(f"/api/projects/{pid}/metal-measurements", json={**LEAD_SOIL, **change})
    assert response.status_code == 422
    assert fragment in response.json()["detail"]
    assert client.get(f"/api/projects/{pid}/metal-measurements").json() == []


def test_missing_required_field_and_unknown_project(client):
    pid = _project(client)
    incomplete = {k: v for k, v in LEAD_SOIL.items() if k != "basis"}
    assert client.post(f"/api/projects/{pid}/metal-measurements", json=incomplete).status_code == 422
    assert client.post("/api/projects/999999/metal-measurements", json=LEAD_SOIL).status_code == 404
    assert client.get("/api/projects/999999/site-models").status_code == 404


def test_site_model_round_trip_and_validation(client):
    pid = _project(client)
    sid = _save(client, pid)
    listed = client.get(f"/api/projects/{pid}/site-models").json()
    assert [m["id"] for m in listed] == [sid] and listed[0]["name"] == "Former works, north yard"
    fetched = client.get(f"/api/projects/{pid}/site-models/{sid}").json()
    assert fetched["model"]["sources"][0]["id"] == "S1"

    bad_link = {**SITE, "links": [{"pathway": "ingestion", "from": "air", "to": "residents"}]}
    assert client.post(f"/api/projects/{pid}/site-models", json=bad_link).status_code == 422
    assert client.post(f"/api/projects/{pid}/site-models", json={**SITE, "name": " "}).status_code == 422
    assert client.post(f"/api/projects/{pid}/site-models", json={**SITE, "jurisdiction": "XX"}).status_code == 422
    assert len(client.get(f"/api/projects/{pid}/site-models").json()) == 1  # nothing invalid was stored


def test_saved_measurement_clears_the_data_gap_for_the_matching_metal_only(client):
    pid = _project(client)
    sid = _save(client, pid)
    before = _by_contaminant(_assessment(client, pid, sid))
    assert before["lead"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}

    client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL)
    after = _assessment(client, pid, sid)
    statuses = _by_contaminant(after)
    assert statuses["lead"] == {"POTENTIAL_LINKAGE_DATA_PRESENT"}
    assert statuses["PCB-153"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}  # metal data never counts for an organic
    linked = after["measurement_linkage"]["linked_measurements"]
    assert linked and linked[0]["contaminant"] == "lead" and linked[0]["basis"] == "total"


def test_unlinkable_measurements_are_reported_not_dropped_or_guessed(client):
    pid = _project(client)
    sid = _save(client, pid)
    client.post(f"/api/projects/{pid}/metal-measurements", json={k: v for k, v in LEAD_SOIL.items() if k != "site_medium"})
    client.post(f"/api/projects/{pid}/metal-measurements", json={**LEAD_SOIL, "element": "Cd"})
    report = _assessment(client, pid, sid)["measurement_linkage"]
    reasons = {u["element"]: u["reason"] for u in report["unlinked_measurements"]}
    assert "site_medium not set" in reasons["Pb"]
    assert "no metal contaminant for this element" in reasons["Cd"]
    assert report["linked_measurements"] == []
    assert _by_contaminant(_assessment(client, pid, sid))["lead"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}


def test_measurement_in_a_different_medium_does_not_clear_the_soil_gap(client):
    pid = _project(client)
    sid = _save(client, pid)
    client.post(f"/api/projects/{pid}/metal-measurements",
                json={**LEAD_SOIL, "site_medium": "groundwater", "medium": "water", "unit": "ug/L", "weight_basis": None})
    assert _by_contaminant(_assessment(client, pid, sid))["lead"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}


def test_measurements_from_another_project_never_leak_in(client):
    p1, p2 = _project(client, "one"), _project(client, "two")
    sid = _save(client, p1)
    client.post(f"/api/projects/{p2}/metal-measurements", json=LEAD_SOIL)
    assert _by_contaminant(_assessment(client, p1, sid))["lead"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}
    assert client.get(f"/api/projects/{p2}/site-models/{sid}").status_code == 404


def test_saved_diagram_reflects_measurements(client):
    pid = _project(client)
    sid = _save(client, pid)
    url = f"/api/projects/{pid}/site-models/{sid}/diagram"
    before = client.get(url)
    assert before.headers["content-type"].startswith("image/svg+xml")
    ET.fromstring(before.text)
    green_edge = re.compile(r'<path d="[^"]*" fill="none" stroke="#2f9e6e"')
    assert not green_edge.search(before.text)  # no green (measured) pathway edges yet
    client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL)
    assert green_edge.search(client.get(url).text)


def test_deleting_a_measurement_restores_the_gap_and_deletes_are_scoped(client):
    pid, other = _project(client), _project(client, "other")
    sid = _save(client, pid)
    mid = client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL).json()["id"]
    assert client.delete(f"/api/projects/{other}/metal-measurements/{mid}").status_code == 404
    assert client.delete(f"/api/projects/{pid}/metal-measurements/{mid}").status_code == 204
    assert _by_contaminant(_assessment(client, pid, sid))["lead"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}
    assert client.delete(f"/api/projects/{pid}/site-models/{sid}").status_code == 204
    assert client.get(f"/api/projects/{pid}/site-models/{sid}").status_code == 404


def test_saves_and_deletes_are_audited(client):
    pid = _project(client)
    sid = _save(client, pid)
    mid = client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL).json()["id"]
    client.delete(f"/api/projects/{pid}/metal-measurements/{mid}")
    client.delete(f"/api/projects/{pid}/site-models/{sid}")
    with client.session_factory() as db:
        events = {(e.entity_type, e.action) for e in db.query(AuditEvent).filter(AuditEvent.project_id == pid)}
    assert {("site_model", "created"), ("site_model", "deleted"),
            ("metal_measurement", "created"), ("metal_measurement", "deleted")} <= events


def test_reference_carries_what_the_screen_needs():
    with TestClient(app) as c:
        ref = c.get("/api/conceptual-site-model/reference").json()
    groups = {g["key"]: g for g in ref["contaminant_groups"]}
    assert groups["metal_inorganic"]["letter"] == "C" and "radionuclide" in groups
    assert ref["metal_elements"]["Pb"] == "lead"
    assert {"total", "dissolved", "particulate", "bioavailable", "free_ion", "unknown"} == set(ref["measurement"]["bases"])
    assert "ug/L" in ref["measurement"]["water_units"] and "mg/kg" in ref["measurement"]["solid_units"]


def test_example_payload_is_a_valid_model():
    from app.services.conceptual_site_model import model_from_dict
    with TestClient(app) as c:
        payload = c.get("/api/conceptual-site-model/example").json()
    assert len(model_from_dict(payload).sources) == 2


def test_draft_analysis_merges_project_measurements_and_stores_nothing(client):
    pid = _project(client)
    draft = {**SITE}
    before = client.post(f"/api/projects/{pid}/site-models/analyse", json=draft).json()
    assert before["summary"]["with_measured_data"] == 0
    client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL)
    after = client.post(f"/api/projects/{pid}/site-models/analyse", json=draft)
    assert after.status_code == 200
    body = after.json()
    assert body["summary"]["with_measured_data"] > 0
    assert body["measurement_linkage"]["linked_measurements"][0]["contaminant"] == "lead"
    ET.fromstring(body["diagram_svg"])
    assert client.get(f"/api/projects/{pid}/site-models").json() == []  # analysis never saves


def test_draft_analysis_rejects_bad_input(client):
    pid = _project(client)
    assert client.post("/api/projects/999999/site-models/analyse", json=SITE).status_code == 404
    assert client.post(f"/api/projects/{pid}/site-models/analyse", json={**SITE, "jurisdiction": "XX"}).status_code == 422
    bad = {**SITE, "links": [{"pathway": "ingestion", "from": "air", "to": "residents"}]}
    assert client.post(f"/api/projects/{pid}/site-models/analyse", json=bad).status_code == 422


def _audit_events(client, pid, entity_type, action):
    import json
    with client.session_factory() as db:
        rows = db.query(AuditEvent).filter(AuditEvent.project_id == pid, AuditEvent.entity_type == entity_type,
                                           AuditEvent.action == action).all()
        return [json.loads(r.payload_json) for r in rows]


def test_site_model_can_be_updated_in_place_and_previous_version_is_audited(client):
    pid = _project(client)
    sid = _save(client, pid)
    edited = {**SITE, "name": "Former works, revised",
              "receptors": ["residents"], "links": [{"pathway": "ingestion", "from": "soil", "to": "residents"}]}
    response = client.put(f"/api/projects/{pid}/site-models/{sid}", json=edited)
    assert response.status_code == 200 and response.json()["name"] == "Former works, revised"
    assert response.json()["id"] == sid
    stored = client.get(f"/api/projects/{pid}/site-models/{sid}").json()
    assert stored["model"]["receptors"] == ["residents"] and len(stored["model"]["links"]) == 1
    assert len(client.get(f"/api/projects/{pid}/site-models").json()) == 1  # updated, not duplicated
    event = _audit_events(client, pid, "site_model", "updated")[0]
    assert event["previous_name"] == "Former works, north yard"
    assert len(event["previous_model"]["links"]) == 2


def test_invalid_site_model_update_is_rejected_and_the_saved_version_is_untouched(client):
    pid = _project(client)
    sid = _save(client, pid)
    url = f"/api/projects/{pid}/site-models/{sid}"
    bad_link = {**SITE, "links": [{"pathway": "ingestion", "from": "air", "to": "residents"}]}
    for bad in (bad_link, {**SITE, "name": " "}, {**SITE, "jurisdiction": "XX"}):
        assert client.put(url, json=bad).status_code == 422
    stored = client.get(url).json()
    assert stored["name"] == "Former works, north yard" and len(stored["model"]["links"]) == 2
    assert _audit_events(client, pid, "site_model", "updated") == []


def test_site_model_update_is_scoped_to_its_project(client):
    p1, p2 = _project(client, "one"), _project(client, "two")
    sid = _save(client, p1)
    assert client.put(f"/api/projects/{p2}/site-models/{sid}", json=SITE).status_code == 404
    assert client.put(f"/api/projects/{p1}/site-models/999999", json=SITE).status_code == 404


def test_measurement_can_be_corrected_and_the_change_flows_into_the_analysis(client):
    pid = _project(client)
    sid = _save(client, pid)
    mid = client.post(f"/api/projects/{pid}/metal-measurements",
                      json={**LEAD_SOIL, "site_medium": None}).json()["id"]
    assert _by_contaminant(_assessment(client, pid, sid))["lead"] == {"POTENTIAL_LINKAGE_MEASUREMENT_MISSING"}

    corrected = {**LEAD_SOIL, "value": 410, "basis": "dissolved", "source": "Lab report ABC-12 (re-issued)"}
    response = client.put(f"/api/projects/{pid}/metal-measurements/{mid}", json=corrected)
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["value"], body["basis"], body["site_medium"]) == (mid, 410, "dissolved", "soil")
    assert len(client.get(f"/api/projects/{pid}/metal-measurements").json()) == 1  # replaced, not duplicated
    assert _by_contaminant(_assessment(client, pid, sid))["lead"] == {"POTENTIAL_LINKAGE_DATA_PRESENT"}

    event = _audit_events(client, pid, "metal_measurement", "updated")[0]
    assert event["previous"]["value"] == 350 and event["previous"]["basis"] == "total"
    assert event["current"]["value"] == 410 and event["previous"]["site_medium"] is None


def test_invalid_measurement_update_is_rejected_and_the_record_is_untouched(client):
    pid = _project(client)
    mid = client.post(f"/api/projects/{pid}/metal-measurements", json=LEAD_SOIL).json()["id"]
    url = f"/api/projects/{pid}/metal-measurements/{mid}"
    for change in ({"weight_basis": None}, {"source": ""}, {"value": -5}, {"element": "lead"}, {"site_medium": "lava"}):
        assert client.put(url, json={**LEAD_SOIL, **change}).status_code == 422
    saved = client.get(f"/api/projects/{pid}/metal-measurements").json()[0]
    assert saved["value"] == 350 and saved["weight_basis"] == "dry"
    assert _audit_events(client, pid, "metal_measurement", "updated") == []


def test_measurement_update_is_scoped_to_its_project(client):
    p1, p2 = _project(client, "one"), _project(client, "two")
    mid = client.post(f"/api/projects/{p1}/metal-measurements", json=LEAD_SOIL).json()["id"]
    assert client.put(f"/api/projects/{p2}/metal-measurements/{mid}", json=LEAD_SOIL).status_code == 404
    assert client.put(f"/api/projects/{p1}/metal-measurements/999999", json=LEAD_SOIL).status_code == 404


def test_saved_model_keeps_sourced_properties_and_the_analysis_uses_them(client):
    pid = _project(client)
    site = {
        "name": "Solvent plume", "jurisdiction": "US",
        "sources": [{"id": "S1", "kind": "spill", "release_media": ["groundwater"], "contaminants": [
            {"name": "benzene", "contaminant_group": "hydrocarbon_solvent",
             "properties": {"vapour_pressure_mm_hg": {"value": 95, "source": "supplier datasheet, rev 3"}}}]}],
        "receptors": ["residents"],
        "links": [{"pathway": "volatilisation", "from": "groundwater", "to": "soil_gas"},
                  {"pathway": "inhalation", "from": "soil_gas", "to": "residents"}],
    }
    sid = _save(client, pid, site)
    stored = client.get(f"/api/projects/{pid}/site-models/{sid}").json()["model"]
    assert stored["sources"][0]["contaminants"][0]["properties"]["vapour_pressure_mm_hg"]["source"] == "supplier datasheet, rev 3"
    result = _assessment(client, pid, sid)
    prompts = [r for x in result["linkages"] for r in x["plausibility"]]
    assert prompts and {r["outcome"] for r in prompts} == {"SUPPORTS_RELEVANCE"}
    assert "supplier datasheet, rev 3" in prompts[0]["basis"][0]
    unsourced = {**site, "sources": [{**site["sources"][0], "contaminants": [
        {"name": "benzene", "contaminant_group": "hydrocarbon_solvent",
         "properties": {"vapour_pressure_mm_hg": {"value": 95}}}]}]}
    assert client.post(f"/api/projects/{pid}/site-models", json=unsourced).status_code == 422
