"""Tests for the EPA CompTox / CTX Hazard API connector (app/services/epa_comptox.py).

Sample response bodies below are constructed from the REAL schema fields confirmed live against the
actual API 2026-09-23 (see the module's own docstring) -- not fabricated field names. The one
``humanEco: "eco"`` record used below is a synthetic test fixture built to match that real schema (no
such record was actually observed live; the module docstring documents that honestly) so the
filtering/mapping logic has something to prove itself against.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.services.epa_comptox import search_epa_comptox

TEST_CONFIG = Settings(_env_file=None, comptox_api_key="test-key-123")

# A real-shaped chemical-resolution response (atrazine, as actually returned live).
ATRAZINE_MATCH = [{
    "dtxsid": "DTXSID9020112", "dtxcid": "DTXCID90112", "casrn": "1912-24-9",
    "preferredName": "Atrazine", "hasStructureImage": 1, "smiles": "CCNC1=NC(NC(C)C)=NC(Cl)=N1",
    "isMarkush": False, "searchName": "CAS-RN", "searchValue": "1912-24-9", "rank": 5,
}]

# A real-shaped human-health-only ToxValDB record, matching what was actually observed live for every
# one of the seven chemicals tested (source=ECOTOX, humanEco="human health", speciesSupercategory="Mammals").
HUMAN_HEALTH_RECORD = {
    "id": 113489, "dtxsid": "DTXSID9020112", "casrn": "1912-24-9", "name": "Atrazine",
    "source": "ECOTOX", "subsource": "EPA ORD", "toxvalType": "LOEL", "toxvalNumeric": 1.0,
    "toxvalUnits": "mg/L", "qualifier": "=", "humanEco": "human health", "speciesCommon": "Mouse",
    "latinName": "Mus musculus", "speciesSupercategory": "Mammals", "studyType": "chronic",
    "studyDurationValue": 121.76, "studyDurationUnits": "days", "toxicologicalEffect": "Genetics: Gene expression",
    "riskAssessmentClass": "-", "doi": "-", "guideline": "-", "title": "Some study title", "year": "2008",
    "author": "Cimino-Reale,G.", "longRef": "Toxicol. Lett.180:59-66", "sourceUrl": "https://cfpub.epa.gov/ecotox/",
    "media": "no vehicle",
}

# A synthetic eco-classified record, built to the same real schema, for testing the filter/mapping path.
ECO_RECORD = {
    "id": 999001, "dtxsid": "DTXSID9020112", "casrn": "1912-24-9", "name": "Atrazine",
    "source": "ECOTOX", "subsource": "-", "toxvalType": "LC50", "toxvalNumeric": 4.5,
    "toxvalUnits": "mg/L", "qualifier": "=", "humanEco": "eco", "speciesCommon": "Rainbow trout",
    "latinName": "Oncorhynchus mykiss", "speciesSupercategory": "Fish", "studyType": "acute",
    "studyDurationValue": 96.0, "studyDurationUnits": "hours", "toxicologicalEffect": "Mortality",
    "riskAssessmentClass": "-", "doi": "-", "guideline": "-", "title": "A fish acute toxicity study", "year": "2010",
    "author": "Test Author", "longRef": "Test Journal 1:1-10", "sourceUrl": "https://cfpub.epa.gov/ecotox/",
    "media": "freshwater",
}

# An eco record whose toxvalType has no existing ENDPOINT_CATALOG slot -- must still be surfaced, not dropped.
ECO_RECORD_UNMAPPED_TYPE = {**ECO_RECORD, "id": 999002, "toxvalType": "Effect Time", "toxvalUnits": "days"}


def _handler(chemical_response, toxval_response, fate_response=()):
    def handler(request: httpx.Request) -> httpx.Response:
        if "/chemical/fate/search/by-dtxsid/" in request.url.path:
            return httpx.Response(200, json=list(fate_response))
        if "/chemical/search/equal/" in request.url.path:
            return httpx.Response(200, json=chemical_response)
        if "/hazard/toxval/search/by-dtxsid/" in request.url.path:
            return httpx.Response(200, json=toxval_response)
        raise AssertionError(f"unexpected request: {request.url}")
    return handler


def test_returns_api_key_missing_when_no_key_configured():
    result = search_epa_comptox("Atrazine", cas_number="1912-24-9", configuration=Settings(_env_file=None, comptox_api_key=None))
    assert result["status"] == "api_key_missing"
    assert result["candidates"] == []


def test_no_match_when_chemical_does_not_resolve():
    client = httpx.Client(transport=httpx.MockTransport(_handler([], [])))
    result = search_epa_comptox("Not A Real Chemical", cas_number="0-00-0", client=client, configuration=TEST_CONFIG)
    client.close()
    assert result["status"] == "no_match"
    assert result["candidates"] == []


def test_no_eco_records_found_is_reported_honestly_not_as_ok():
    # Matches what was actually observed live: real chemical resolves, real ToxValDB records come back,
    # none are humanEco=='eco'.
    client = httpx.Client(transport=httpx.MockTransport(_handler(ATRAZINE_MATCH, [HUMAN_HEALTH_RECORD])))
    result = search_epa_comptox("Atrazine", cas_number="1912-24-9", client=client, configuration=TEST_CONFIG)
    client.close()
    assert result["status"] == "no_eco_records_found"
    assert result["candidates"] == []
    assert result["total_toxval_records"] == 1
    assert result["dtxsid"] == "DTXSID9020112"
    assert "none classified humanEco" in result["warnings"][0]


def test_eco_record_is_surfaced_and_mapped_to_the_lc50_property_code():
    client = httpx.Client(transport=httpx.MockTransport(_handler(ATRAZINE_MATCH, [HUMAN_HEALTH_RECORD, ECO_RECORD])))
    result = search_epa_comptox("Atrazine", cas_number="1912-24-9", client=client, configuration=TEST_CONFIG)
    client.close()
    assert result["status"] == "ok"
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["property_code"] == "ECOTOX.AQUATIC.LC50"
    assert candidate["value"] == 4.5
    assert candidate["unit"] == "mg/L"
    assert "Rainbow trout" in candidate["snippet"] or "Oncorhynchus mykiss" in candidate["snippet"]
    assert candidate["source_key"] == "epa_comptox"
    assert candidate["needs_professional_review"] is True
    # ToxValDB's "-" sentinel must be normalised to None, not surfaced as a literal "-" doi.
    assert candidate["doi"] is None


def test_eco_record_with_unmapped_toxval_type_is_still_surfaced_not_dropped():
    client = httpx.Client(transport=httpx.MockTransport(_handler(ATRAZINE_MATCH, [ECO_RECORD_UNMAPPED_TYPE])))
    result = search_epa_comptox("Atrazine", cas_number="1912-24-9", client=client, configuration=TEST_CONFIG)
    client.close()
    assert result["status"] == "ok"
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["property_code"] is None
    assert candidate["endpoint_label"] == "Effect Time"
    assert "not mapped to an existing ENDPOINT_CATALOG code" in candidate["notes"]


def test_endpoint_codes_filter_is_applied_to_eco_candidates():
    client = httpx.Client(transport=httpx.MockTransport(_handler(ATRAZINE_MATCH, [ECO_RECORD])))
    result = search_epa_comptox(
        "Atrazine", cas_number="1912-24-9", endpoint_codes=["ECOTOX.AQUATIC.NOEC"], client=client, configuration=TEST_CONFIG,
    )
    client.close()
    assert result["status"] == "no_eco_records_found"
    assert result["candidates"] == []


def test_limit_caps_the_number_of_candidates():
    many_eco_records = [{**ECO_RECORD, "id": 999000 + i} for i in range(5)]
    client = httpx.Client(transport=httpx.MockTransport(_handler(ATRAZINE_MATCH, many_eco_records)))
    result = search_epa_comptox("Atrazine", cas_number="1912-24-9", limit=2, client=client, configuration=TEST_CONFIG)
    client.close()
    assert len(result["candidates"]) == 2


# Shape observed live 2026-09-24 (atrazine, DTXSID9020112): the API pads an empty section with [null].
OPERA_BIODEG_GROUP = {
    "propName": "Biodeg. Half-Life",
    "experimentalFateData": [None],
    "predictedFateData": [{
        "id": 61414149, "prop_name": "Biodeg. Half-Life", "prop_type": "predicted", "model_name": "OPERA_BioDeg",
        "source_name": "OPERA2.8", "prop_value": 4.897788193684462, "prop_unit": "days",
        "ad_conclusion_global": "Outside",
        "ad_reasoning": "Outside training set (Global AD = 0) and poor local representation (Local AD index = 0.307 &lt; 0.4)",
    }],
}
EXPERIMENTAL_BIODEG_GROUP = {
    "propName": "Biodeg. Half-Life",
    "experimentalFateData": [{
        "id": 77, "prop_type": "experimental", "dataset": "exp_prop_BIODEG_v1", "prop_value": 30.0, "prop_unit": "days",
        "source_name": "SRC 98-008 survey", "ls_citation": "Test citation", "ls_doi": None,
    }],
    "predictedFateData": [None],
}
UNRELATED_GROUP = {"propName": "Bioconcentration Factor", "experimentalFateData": [{"id": 1, "prop_value": 8.0}], "predictedFateData": [None]}


def _fate_search(fate_groups, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(_handler(ATRAZINE_MATCH, [HUMAN_HEALTH_RECORD], fate_groups)))
    return search_epa_comptox("Atrazine", cas_number="1912-24-9", client=client, configuration=Settings(comptox_api_key="k"), **kwargs)


def test_opera_prediction_is_surfaced_with_its_applicability_domain_and_no_matrix_claim():
    result = _fate_search([UNRELATED_GROUP, OPERA_BIODEG_GROUP])
    assert result["status"] == "ok" and len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["value"] == pytest.approx(4.897788193684462) and candidate["unit"] == "days"
    assert candidate["evidence_type"] == "model_prediction" and candidate["property_code"] is None and candidate["matrix"] is None
    assert candidate["temperature_c"] == 25.0 and candidate["needs_professional_review"] is True
    assert "Outside" in candidate["snippet"] and "Local AD index = 0.307 < 0.4" in candidate["snippet"]  # &lt; unescaped
    assert "NOT a soil/water/manure/sludge DT50" in candidate["notes"] and "unreliable" in candidate["notes"]


def test_experimental_biodegradation_record_precedes_the_prediction_and_null_padding_is_ignored():
    result = _fate_search([OPERA_BIODEG_GROUP, EXPERIMENTAL_BIODEG_GROUP])
    kinds = [c["evidence_type"] for c in result["candidates"]]
    assert kinds == ["database_record", "model_prediction"]
    assert result["candidates"][0]["value"] == 30.0 and result["candidates"][0]["original_source"] == "Test citation"


def test_endpoint_filter_excludes_uncoded_biodegradation_records():
    assert _fate_search([OPERA_BIODEG_GROUP], endpoint_codes=["ECOTOX.AQUATIC.LC50"])["candidates"] == []


def test_fate_endpoint_failure_does_not_break_the_toxval_search():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/chemical/fate/" in request.url.path:
            return httpx.Response(500)
        return _handler(ATRAZINE_MATCH, [ECO_RECORD])(request)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = search_epa_comptox("Atrazine", cas_number="1912-24-9", client=client, configuration=Settings(comptox_api_key="k"))
    assert result["status"] == "ok" and len(result["candidates"]) == 1
    assert any("fate endpoint" in w for w in result["warnings"])
