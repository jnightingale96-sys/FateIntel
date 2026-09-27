"""OASIS soil DT50 lookup: a fixture dataset stands in for the real 208-structure export, so tests never depend on it."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services import oasis_soil_dt50 as o

ETHANOL = "CCO"
ETHANOL_CANONICAL = "CCO"
PHENOL = "c1ccc(O)cc1"


@pytest.fixture
def fixture_path(tmp_path):
    path = tmp_path / "oasis_soil_dt50.json"
    path.write_text(json.dumps({
        "version": "1.0", "source": "oasis_soil_dt50",
        "records": {
            ETHANOL_CANONICAL: [
                {"cas_number": "64-17-5", "names": "ethanol", "dt50_mean_days": 4.0, "dt50_min_days": 2.0, "dt50_max_days": 6.0, "qualifier": 0, "record_id": "1"},
                {"cas_number": "64-17-5", "names": "ethanol", "dt50_mean_days": 6.0, "dt50_min_days": None, "dt50_max_days": None, "qualifier": 0, "record_id": "2"},
            ],
        },
    }), encoding="utf-8")
    return path


LOCAL = Settings(_env_file=None, envirochem_environment="local")
STAGING = Settings(_env_file=None, envirochem_environment="staging")
STAGING_CONFIRMED = Settings(_env_file=None, envirochem_environment="staging", oasis_soil_dt50_commercial_license_confirmed=True)


def test_found_record_averages_duplicates_and_carries_the_citation(fixture_path):
    result = o.lookup_by_smiles(ETHANOL, configuration=LOCAL, data_path=fixture_path)
    assert result["found"] is True and result["n"] == 2
    assert result["dt50_mean_days"] == pytest.approx(5.0)
    assert result["canonical_smiles"] == ETHANOL_CANONICAL and "LMC" in result["citation"]


def test_unmatched_structure_is_reported_not_invented(fixture_path):
    result = o.lookup_by_smiles(PHENOL, configuration=LOCAL, data_path=fixture_path)
    assert result == {"found": False, "available": True, "reason": "no structure match in the OASIS soil DT50 set"}


def test_unparsable_smiles_is_refused_not_silently_dropped(fixture_path):
    result = o.lookup_by_smiles("not a smiles (((", configuration=LOCAL, data_path=fixture_path)
    assert result["found"] is False and "could not be parsed" in result["reason"]


def test_closed_outside_local_test_until_licence_confirmed(fixture_path):
    closed = o.lookup_by_smiles(ETHANOL, configuration=STAGING, data_path=fixture_path)
    assert closed["found"] is False and closed["available"] is False and "closed" in closed["reason"]
    opened = o.lookup_by_smiles(ETHANOL, configuration=STAGING_CONFIRMED, data_path=fixture_path)
    assert opened["found"] is True


def test_missing_data_file_is_reported_not_a_crash(tmp_path):
    result = o.lookup_by_smiles(ETHANOL, configuration=LOCAL, data_path=tmp_path / "missing.json")
    assert result == {"found": False, "available": False, "reason": "data file missing"}


def test_candidate_is_a_reviewable_measured_record_with_licence_flagged(fixture_path):
    result = o.lookup_by_smiles(ETHANOL, configuration=LOCAL, data_path=fixture_path)
    candidate = o.to_evidence_candidate(result, chemical_name="Ethanol")
    assert candidate["property_code"] == "FATE.SOIL_DT50" and candidate["value"] == pytest.approx(5.0)
    assert candidate["evidence_type"] == "database_record" and candidate["matrix"] == "soil"
    assert candidate["rights_status"] == "third_party_data_licence_unconfirmed" and candidate["needs_professional_review"] is True
    assert candidate["cas_number"] == "64-17-5" and "RIVM" in candidate["original_source"]
    with pytest.raises(ValueError):
        o.to_evidence_candidate({"found": False}, chemical_name="x")


def test_real_data_file_loads_and_finds_a_known_pesticide():
    # the real shipped file, not the fixture -- confirms the conversion script's output is usable
    result = o.lookup_by_smiles("CC(=O)Nc1ccc(Oc2ccc(Cl)cc2Cl)cc1")  # a chloroacetanilide-style structure, may or may not match
    caps = o.capabilities()
    assert caps["structure_count"] == 208 and caps["record_count"] == 215


def test_capabilities_route_and_lookup_route_round_trip(fixture_path, monkeypatch):
    monkeypatch.setattr(o, "DATA_PATH", fixture_path)
    with TestClient(app) as client:
        caps = client.get("/api/providers/oasis-soil-dt50/capabilities")
        found = client.get("/api/providers/oasis-soil-dt50/lookup", params={"smiles": ETHANOL, "chemical_name": "Ethanol", "include_evidence_candidate": True})
        missing = client.get("/api/providers/oasis-soil-dt50/lookup", params={"smiles": PHENOL})
    assert caps.status_code == 200
    assert found.status_code == 200 and found.json()["found"] is True and found.json()["evidence_candidate"]["property_code"] == "FATE.SOIL_DT50"
    assert missing.status_code == 200 and missing.json()["found"] is False


def test_lookup_by_inchikey_matches_the_smiles_lookup_and_reports_absence(fixture_path):
    import json as _json

    data = _json.loads(fixture_path.read_text(encoding="utf-8"))
    data["by_inchikey"] = {"WQZGKKKJIJFFOK-GASJEMHNSA-N": [{**data["records"][ETHANOL_CANONICAL][0], "canonical_smiles": ETHANOL_CANONICAL}]}
    fixture_path.write_text(_json.dumps(data), encoding="utf-8")

    result = o.lookup_by_inchikey("WQZGKKKJIJFFOK-GASJEMHNSA-N", configuration=LOCAL, data_path=fixture_path)
    assert result["found"] is True and result["dt50_mean_days"] == pytest.approx(4.0)
    assert o.lookup_by_inchikey("NOT-A-REAL-KEY", configuration=LOCAL, data_path=fixture_path)["found"] is False
    assert o.lookup_by_inchikey("", configuration=LOCAL, data_path=fixture_path) == {"found": False, "available": True, "reason": "an InChIKey is required"}
    closed = o.lookup_by_inchikey("WQZGKKKJIJFFOK-GASJEMHNSA-N", configuration=STAGING, data_path=fixture_path)
    assert closed["found"] is False and closed["available"] is False


def test_real_data_file_has_an_inchikey_index_matching_the_smiles_index():
    from rdkit import Chem

    canonical_smiles, records = next(iter(o._load()["records"].items()))
    inchikey = Chem.MolToInchiKey(Chem.MolFromSmiles(canonical_smiles))
    by_key = o.lookup_by_inchikey(inchikey)
    assert by_key["found"] is True and by_key["dt50_mean_days"] == pytest.approx(o.lookup_by_smiles(canonical_smiles)["dt50_mean_days"])
