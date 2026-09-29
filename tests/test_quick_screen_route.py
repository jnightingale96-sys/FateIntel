"""Route-level wiring test for POST /api/quick-screen/risk -- the module's own arithmetic is already covered
by tests/test_quick_screen.py; these only check the route resolves identity the same way
/api/identities/resolve does (local record first, then PubChem) and calls screen_chemical_risk with the
right shape, returning 422 (not 500) on an invalid reviewer input.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import quick_screen as qs


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _fake_candidates(*, chemical_name, cas_number, source_keys, limit_per_source):
    assert source_keys == ["epa_ecotox"]
    return {"candidates": [
        {"property_code": "ECOTOX.AQUATIC.NOEC", "value": 25, "unit": "ug/L",
         "snippet": "NOEC = 25 ug/L | species: Ceriodaphnia dubia | effect: X", "source_record_id": "1"},
    ]}


def test_quick_screen_route_resolves_via_pubchem_when_not_a_local_record(client, monkeypatch):
    monkeypatch.setattr(qs, "search_sources", _fake_candidates)
    monkeypatch.setattr(
        "app.main.resolve_pubchem_identity",
        lambda query, query_mode: {"preferred_name": "Carbamazepine", "cas_number": "298-46-4", "smiles": "C1=CC2=CC=CC=C2N(C1=CC=CC=C1N2C(=O)N)"},
    )

    result = client.post("/api/quick-screen/risk", json={
        "query": "298-46-4", "query_mode": "cas", "scenario": "ema_phase_i_pharma",
        "maximum_daily_dose_mg": 2000,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["identity"]["preferred_name"] == "Carbamazepine"
    assert body["screening_estimate"] is True and body["reviewed"] is False
    assert body["exposure"]["pec_surface_water_ug_l"] == pytest.approx(10.0)
    assert body["risk"]["risk_quotient"] == pytest.approx(40.0)


def test_quick_screen_route_rejects_missing_release_with_422_not_500(client, monkeypatch):
    result = client.post("/api/quick-screen/risk", json={"query": "298-46-4", "query_mode": "cas", "scenario": "generic_wwtp"})
    assert result.status_code == 422


def test_quick_screen_route_surfaces_unknown_compound_as_validation_error(client, monkeypatch):
    def not_found(query, query_mode):
        raise ValueError(f"No PubChem match for {query_mode} query {query!r}")

    monkeypatch.setattr("app.main.resolve_pubchem_identity", not_found)
    result = client.post("/api/quick-screen/risk", json={
        "query": "not-a-real-compound", "query_mode": "cas", "scenario": "generic_wwtp", "release_kg_year": 1,
    })
    assert result.status_code in {400, 404, 422}


def test_quick_screen_route_reports_data_gap_without_crashing(client, monkeypatch):
    monkeypatch.setattr(qs, "search_sources", lambda **kw: {"candidates": []})
    monkeypatch.setattr(
        "app.main.resolve_pubchem_identity",
        lambda query, query_mode: {"preferred_name": "Unknown Substance", "cas_number": None, "smiles": None},
    )

    result = client.post("/api/quick-screen/risk", json={
        "query": "0000-00-0", "query_mode": "cas", "scenario": "generic_wwtp", "release_kg_year": 10,
    })
    assert result.status_code == 200
    body = result.json()
    assert body["hazard"]["pnec_ug_l"] is None
    assert body["risk"]["risk_band"] == "cannot_be_characterised"
