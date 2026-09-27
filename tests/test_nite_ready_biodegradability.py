"""NITE ready-biodegradability / mineralization lookup: a fixture dataset stands in for the real 1,373-structure export."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services import nite_ready_biodegradability as n

ETHANOL = "CCO"
ETHANOL_CANONICAL = "CCO"
PHENOL = "c1ccc(O)cc1"


@pytest.fixture
def fixture_path(tmp_path):
    path = tmp_path / "nite_ready_biodegradability.json"
    path.write_text(json.dumps({
        "version": "1.0", "source": "nite_ready_biodegradability",
        "records": {
            ETHANOL_CANONICAL: [
                {"cas_number": "64-17-5", "names": "ethanol", "biodeg_percent": 90.0, "biodeg_percent_min": None,
                 "biodeg_percent_max": None, "duration_days": 28.0, "test_guideline": "OECD Guideline 301 C",
                 "endpoint_type": "Ready Biodegradability", "year": "1990", "record_id": "1",
                 "readily_biodegradable": n.classify_ready_biodegradability(90.0, "OECD Guideline 301 C")},
                {"cas_number": "64-17-5", "names": "ethanol", "biodeg_percent": 80.0, "biodeg_percent_min": None,
                 "biodeg_percent_max": None, "duration_days": 28.0, "test_guideline": "OECD Guideline 301 C",
                 "endpoint_type": "Ready Biodegradability", "year": "1990", "record_id": "2",
                 "readily_biodegradable": n.classify_ready_biodegradability(80.0, "OECD Guideline 301 C")},
            ],
        },
    }), encoding="utf-8")
    return path


LOCAL = Settings(_env_file=None, envirochem_environment="local")
STAGING = Settings(_env_file=None, envirochem_environment="staging")
STAGING_CONFIRMED = Settings(_env_file=None, envirochem_environment="staging", nite_ready_biodegradability_commercial_license_confirmed=True)


def test_found_record_averages_duplicates_and_carries_the_citation(fixture_path):
    result = n.lookup_by_smiles(ETHANOL, configuration=LOCAL, data_path=fixture_path)
    assert result["found"] is True and result["n"] == 2
    assert result["biodeg_percent_mean"] == pytest.approx(85.0)
    assert result["canonical_smiles"] == ETHANOL_CANONICAL and "METI" in result["citation"]


def test_unmatched_structure_is_reported_not_invented(fixture_path):
    result = n.lookup_by_smiles(PHENOL, configuration=LOCAL, data_path=fixture_path)
    assert result == {"found": False, "available": True, "reason": "no structure match in the NITE ready-biodegradability set"}


def test_closed_outside_local_test_until_licence_confirmed(fixture_path):
    closed = n.lookup_by_smiles(ETHANOL, configuration=STAGING, data_path=fixture_path)
    assert closed["found"] is False and closed["available"] is False and "closed" in closed["reason"]
    opened = n.lookup_by_smiles(ETHANOL, configuration=STAGING_CONFIRMED, data_path=fixture_path)
    assert opened["found"] is True


def test_candidate_is_a_reviewable_measured_percentage_with_the_confirmed_pass_fail_classification(fixture_path):
    result = n.lookup_by_smiles(ETHANOL, configuration=LOCAL, data_path=fixture_path)
    candidate = n.to_evidence_candidate(result, chemical_name="Ethanol")
    assert candidate["property_code"] == "FATE.BIODEGRADATION" and candidate["value"] == pytest.approx(85.0) and candidate["unit"] == "%"
    assert candidate["guideline"] == "OECD Guideline 301 C" and candidate["matrix"] == "aqueous_screening_test"
    assert candidate["rights_status"] == "third_party_data_licence_unconfirmed" and candidate["needs_professional_review"] is True
    assert "Readily biodegradable: pass" in candidate["notes"] and "OECD TG 301" in candidate["notes"]
    with pytest.raises(ValueError):
        n.to_evidence_candidate({"found": False}, chemical_name="x")


# ---------------------------------------------------------------- confirmed OECD TG 301 pass/fail classification -----

def test_301c_is_classified_pass_or_fail_at_the_60_percent_thod_threshold():
    at_threshold = n.classify_ready_biodegradability(60.0, "OECD Guideline 301 C (Ready Biodegradability: Modified MITI Test (I))")
    just_below = n.classify_ready_biodegradability(59.9, "OECD Guideline 301 C (Ready Biodegradability: Modified MITI Test (I))")
    assert at_threshold["classification"] == "pass" and "OECD TG 301" in at_threshold["basis"]
    assert just_below["classification"] == "fail"


def test_301d_is_indicative_only_302c_is_not_applicable_and_unknown_guidelines_are_unknown():
    d301 = n.classify_ready_biodegradability(90.0, "OECD Guideline 301 D (Ready Biodegradability: Closed Bottle Test)")
    c302 = n.classify_ready_biodegradability(90.0, "OECD Guideline 302 C (Inherent Biodegradability: Modified MITI Test (II))")
    other = n.classify_ready_biodegradability(90.0, "Undefined Test Guideline")
    missing_percent = n.classify_ready_biodegradability(None, "OECD Guideline 301 C")
    assert d301["classification"] == "indicative_only" and "10-day window" in d301["basis"]
    assert c302["classification"] == "not_applicable" and "inherent" in c302["basis"].lower()
    assert other["classification"] == "unknown"
    assert missing_percent["classification"] == "unknown" and "No percentage" in missing_percent["basis"]


def test_real_data_file_has_the_classification_baked_into_every_record():
    import collections

    data = n._load()
    counts = collections.Counter()
    for records in data["records"].values():
        for record in records:
            counts[record["readily_biodegradable"]["classification"]] += 1
    assert counts == {"fail": 868, "pass": 391, "not_applicable": 72, "indicative_only": 34, "unknown": 8}


def test_real_data_file_loads_with_the_expected_shape():
    caps = n.capabilities()
    assert caps["structure_count"] == 1373 and caps["record_count"] == 1373


def test_capabilities_route_and_lookup_route_round_trip(fixture_path, monkeypatch):
    monkeypatch.setattr(n, "DATA_PATH", fixture_path)
    with TestClient(app) as client:
        caps = client.get("/api/providers/nite-ready-biodegradability/capabilities")
        found = client.get("/api/providers/nite-ready-biodegradability/lookup", params={"smiles": ETHANOL, "chemical_name": "Ethanol", "include_evidence_candidate": True})
        missing = client.get("/api/providers/nite-ready-biodegradability/lookup", params={"smiles": PHENOL})
    assert caps.status_code == 200
    assert found.status_code == 200 and found.json()["found"] is True and found.json()["evidence_candidate"]["property_code"] == "FATE.BIODEGRADATION"
    assert missing.status_code == 200 and missing.json()["found"] is False


def test_lookup_by_inchikey_matches_the_smiles_lookup_and_reports_absence(fixture_path):
    import json as _json

    data = _json.loads(fixture_path.read_text(encoding="utf-8"))
    data["by_inchikey"] = {"LFQSCWFLJHTTHZ-UHFFFAOYSA-N": [{**r, "canonical_smiles": ETHANOL_CANONICAL} for r in data["records"][ETHANOL_CANONICAL]]}
    fixture_path.write_text(_json.dumps(data), encoding="utf-8")

    result = n.lookup_by_inchikey("LFQSCWFLJHTTHZ-UHFFFAOYSA-N", configuration=LOCAL, data_path=fixture_path)
    assert result["found"] is True and result["biodeg_percent_mean"] == pytest.approx(85.0)
    assert n.lookup_by_inchikey("NOT-A-REAL-KEY", configuration=LOCAL, data_path=fixture_path)["found"] is False
    assert n.lookup_by_inchikey("", configuration=LOCAL, data_path=fixture_path) == {"found": False, "available": True, "reason": "an InChIKey is required"}
    closed = n.lookup_by_inchikey("LFQSCWFLJHTTHZ-UHFFFAOYSA-N", configuration=STAGING, data_path=fixture_path)
    assert closed["found"] is False and closed["available"] is False


def test_real_data_file_has_an_inchikey_index_matching_the_smiles_index():
    from rdkit import Chem

    canonical_smiles, records = next(iter(n._load()["records"].items()))
    inchikey = Chem.MolToInchiKey(Chem.MolFromSmiles(canonical_smiles))
    by_key = n.lookup_by_inchikey(inchikey)
    assert by_key["found"] is True and by_key["biodeg_percent_mean"] == pytest.approx(n.lookup_by_smiles(canonical_smiles)["biodeg_percent_mean"])
