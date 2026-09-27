from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app, BUILD_ID
from app.services.evidence_sources import (
    candidate_import_policy,
    extract_endpoint_candidates_from_text,
    source_registry,
)

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


def _extract(text: str):
    return extract_endpoint_candidates_from_text(
        text,
        source_key="europe_pmc",
        source_name="Europe PMC",
        chemical_name="Test chemical",
        source_record_id="PMID:1",
    )


def test_registry_contains_live_open_and_rights_gated_sources():
    rows = {row["key"]: row for row in source_registry()}
    for key in {
        "pubchem", "europe_pmc", "epa_comptox", "efsa_openfoodtox", "epa_ecotox",
        "uba_pharms", "norman_ecotox", "ecodrug_plus", "oecd_echemportal", "echa_chem",
        "aeru_vsdb", "aeru_ppdb", "premier", "sci_bot",
        "fass_pharma_environment", "janusinfo_pharma_environment", "nihs_japan_pharma_era",
    }:
        assert key in rows
    assert rows["pubchem"]["search_enabled"] is True
    assert rows["europe_pmc"]["search_enabled"] is True
    assert rows["epa_comptox"]["search_enabled"] is True
    assert rows["sci_bot"]["access_mode"] == "blocked"
    assert rows["aeru_vsdb"]["commercial_status"] == "commercial_licence_required"
    assert rows["premier"]["commercial_status"] == "formal_letter_of_access_required"


def test_manure_dt50_context_is_extracted_with_conditions():
    rows = _extract("In cattle manure, the measured DT50 was 31.5 days at 20 °C and pH 7.0 under aerobic storage.")
    manure = next(row for row in rows if row["property_code"] == "FATE.MANURE_DT50")
    assert manure["value"] == pytest.approx(31.5)
    assert manure["unit"] == "days"
    assert manure["matrix"] == "manure"
    assert manure["temperature_c"] == pytest.approx(20.0)
    assert manure["ph"] == pytest.approx(7.0)
    assert manure["needs_professional_review"] is True


def test_hydrolysis_half_life_preserves_original_time_unit():
    rows = _extract("Hydrolysis half-life was 12 h at pH 7 and 25 C; photolysis was not investigated.")
    row = next(item for item in rows if item["property_code"] == "FATE.HYDROLYSIS_DT50")
    assert row["value"] == pytest.approx(12)
    assert row["unit"] == "hours"
    assert row["ph"] == pytest.approx(7)


def test_soil_dt50_koc_and_aquatic_ec50_can_be_surfaced_as_candidates():
    rows = _extract("Aerobic soil DT50 = 45 days at 20 C. Koc = 2835 L/kg. Daphnia EC50 = 7.2 µg/L.")
    keyed = {row["property_code"]: row for row in rows}
    assert keyed["FATE.SOIL_DT50"]["value"] == pytest.approx(45)
    assert keyed["SORPTION.KOC"]["value"] == pytest.approx(2835)
    assert keyed["ECOTOX.AQUATIC.EC50"]["value"] == pytest.approx(7.2)


def test_rights_gate_blocks_sci_bot_and_requires_rights_for_aeru_and_premier():
    assert candidate_import_policy("sci_bot", False)[0] is False
    assert candidate_import_policy("aeru_vsdb", False)[0] is False
    assert candidate_import_policy("aeru_vsdb", True)[0] is True
    assert candidate_import_policy("premier", False)[0] is False
    assert candidate_import_policy("premier", True)[0] is True
    assert candidate_import_policy("pubchem", False)[0] is True


def test_v213_ui_and_client_are_wired():
    assert "v2.24" in BUILD_ID and "8792" not in BUILD_ID
    assert 'id="evidence-data-hub"' in HTML
    assert 'id="search-evidence"' in HTML
    assert "searchEvidenceHub" in JS
    assert "/api/evidence-sources/search" in JS
    assert "/api/evidence-sources/import-candidate" in JS
    assert ".evidence-hub{" in CSS
    assert "border:1px solid #d3dedb" in CSS


def test_evidence_registry_api_exposes_endpoint_catalog():
    with TestClient(app) as client:
        response = client.get("/api/evidence-sources")
        assert response.status_code == 200
        body = response.json()
        keys = {row["key"] for row in body["sources"]}
        endpoints = {row["code"] for row in body["endpoint_catalog"]}
        assert "pubchem" in keys
        assert "FATE.MANURE_DT50" in endpoints
        assert "FATE.HYDROLYSIS_DT50" in endpoints
        assert "ECOTOX.AQUATIC.EC50" in endpoints


def test_guideline_and_wwtp_removal_are_preserved_as_candidates():
    rows = _extract("In an OECD 302B activated sludge study, 98% removal was measured in the wastewater treatment plant at 20 C.")
    removal = next(row for row in rows if row["property_code"] == "FATE.WWTP_REMOVAL")
    assert removal["value"] == pytest.approx(98)
    assert removal["unit"] == "%"
    assert removal["matrix"] == "activated_sludge"
    assert removal["guideline"] == "OECD 302B"


def test_oecd_guideline_is_attached_to_water_sediment_dt50():
    rows = _extract("In an OECD 308 aerobic water-sediment study, the total-system DT50 was 82 days at 20 C.")
    row = next(item for item in rows if item["property_code"] == "FATE.WATER_SEDIMENT_DT50")
    assert row["guideline"] == "OECD 308"


def test_registry_contains_oasis_and_nite_as_licence_gated_search_enabled_sources():
    rows = {row["key"]: row for row in source_registry()}
    for key in {"oasis_soil_dt50", "nite_ready_biodegradability"}:
        assert key in rows
        assert rows[key]["search_enabled"] is True
        assert rows[key]["commercial_status"] == "qsar_toolbox_data_licence_to_confirm"
        assert rows[key]["access_mode"] == "local_model_provider"


def test_evidence_hub_ui_offers_oasis_and_nite_checkboxes_and_sends_smiles():
    assert 'id="evidence-use-oasis-soil-dt50"' in HTML
    assert 'id="evidence-use-nite-mineralization"' in HTML
    assert "oasis_soil_dt50" in JS and "nite_ready_biodegradability" in JS
    assert "smiles" in JS


def test_search_route_wires_smiles_through_to_oasis_and_nite(monkeypatch, tmp_path):
    import json as _json

    from app.services import nite_ready_biodegradability as n
    from app.services import oasis_soil_dt50 as o

    ethanol = "CCO"
    oasis_fixture = tmp_path / "oasis.json"
    oasis_fixture.write_text(_json.dumps({
        "version": "1.0", "source": "oasis_soil_dt50",
        "records": {ethanol: [{"cas_number": "64-17-5", "names": "ethanol", "dt50_mean_days": 4.0, "dt50_min_days": None, "dt50_max_days": None, "qualifier": 0, "record_id": "1"}]},
    }), encoding="utf-8")
    nite_fixture = tmp_path / "nite.json"
    nite_fixture.write_text(_json.dumps({
        "version": "1.0", "source": "nite_ready_biodegradability",
        "records": {ethanol: [{"cas_number": "64-17-5", "names": "ethanol", "biodeg_percent": 90.0, "biodeg_percent_min": None,
                                "biodeg_percent_max": None, "duration_days": 28.0, "test_guideline": "OECD Guideline 301 C",
                                "endpoint_type": "Ready Biodegradability", "year": "1990", "record_id": "1",
                                "readily_biodegradable": n.classify_ready_biodegradability(90.0, "OECD Guideline 301 C")}]},
    }), encoding="utf-8")
    monkeypatch.setattr(o, "DATA_PATH", oasis_fixture)
    monkeypatch.setattr(o, "_cache", None)
    monkeypatch.setattr(n, "DATA_PATH", nite_fixture)
    monkeypatch.setattr(n, "_cache", None)

    with TestClient(app) as client:
        result = client.post("/api/evidence-sources/search", json={
            "chemical_name": "Ethanol", "cas_number": "64-17-5",
            "source_keys": ["oasis_soil_dt50", "nite_ready_biodegradability"],
            "smiles": ethanol,
        })
    assert result.status_code == 200
    body = result.json()
    keyed = {row["source_key"]: row for row in body["source_results"]}
    assert keyed["oasis_soil_dt50"]["status"] == "ok"
    assert keyed["nite_ready_biodegradability"]["status"] == "ok"
    assert len(body["candidates"]) == 2


def test_search_route_without_smiles_returns_smiles_required_not_a_500():
    with TestClient(app) as client:
        result = client.post("/api/evidence-sources/search", json={
            "chemical_name": "Ethanol", "source_keys": ["oasis_soil_dt50", "nite_ready_biodegradability"],
        })
    assert result.status_code == 200
    keyed = {row["source_key"]: row for row in result.json()["source_results"]}
    assert keyed["oasis_soil_dt50"]["status"] == "smiles_required"
    assert keyed["nite_ready_biodegradability"]["status"] == "smiles_required"
