"""PubChem identity resolver: transient-failure retry and honest 'not found' reporting.

Both behaviours came out of a random-chemical validation run (real CAS numbers sampled from the local ECOTOX index):
18 of the first 44 lookups hit PubChem's 503 "ServerBusy" throttle with no retry, and mixtures/UVCB substances
(404 from PubChem) were reported to users as "temporarily unavailable" -- telling them to retry something that can
never succeed.
"""

from __future__ import annotations

import httpx
import pytest

from app.services.identity import _get_with_retry, _resolve_cid


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_transient_503_is_retried_then_succeeds():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, text="ServerBusy") if len(calls) < 3 else httpx.Response(200, json={"ok": True})

    sleeps = []
    response = _get_with_retry(_client(handler), "https://pubchem.test/x", sleep=sleeps.append)
    assert response.status_code == 200
    assert len(calls) == 3
    assert sleeps == [0.8, 2.0]


def test_persistent_503_returns_the_last_response_for_the_caller_to_raise_on():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    response = _get_with_retry(_client(handler), "https://pubchem.test/x", sleep=lambda _s: None)
    assert response.status_code == 503
    assert len(calls) == 3  # bounded: never loops forever


def test_retry_after_header_is_honoured_but_capped():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "120"})
        return httpx.Response(200, json={})

    sleeps = []
    _get_with_retry(_client(handler), "https://pubchem.test/x", sleep=sleeps.append)
    assert sleeps == [5.0]


def test_timeout_is_retried():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json={})

    response = _get_with_retry(_client(handler), "https://pubchem.test/x", sleep=lambda _s: None)
    assert response.status_code == 200 and len(calls) == 2


def test_a_real_404_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404, json={"Fault": {"Code": "PUGREST.NotFound"}})

    response = _get_with_retry(_client(handler), "https://pubchem.test/x", sleep=lambda _s: None)
    assert response.status_code == 404 and len(calls) == 1


def test_unknown_compound_is_reported_as_not_found_not_as_an_outage():
    client = _client(lambda request: httpx.Response(404, json={"Fault": {"Code": "PUGREST.NotFound"}}))
    with pytest.raises(ValueError, match="no single-compound record"):
        _resolve_cid(client, "68585-34-2", "cas")  # a real UVCB CAS number PubChem has no structure for


def test_unknown_compound_surfaces_as_a_validation_error_not_a_temporary_outage(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    def not_found(query, mode):
        raise ValueError("PubChem has no single-compound record for this identifier (mixtures, UVCB substances and trade names have no unique structure)")

    monkeypatch.setattr("app.main.resolve_pubchem_identity", not_found)
    with TestClient(app) as client:
        response = client.post("/api/identities/resolve", json={"query": "68585-34-2", "query_mode": "cas"})
    assert response.status_code != 200
    assert "temporarily unavailable" not in response.text


# ------------------------------------------------------------------------------------ malformed query (400)
# Found live 2026-10-01 screening an invalid SMILES during a pre-demo QA pass: PubChem's real PUGREST.BadRequest
# response (confirmed live against the real API) was being reported identically to a genuine outage -- the same
# "temporarily unavailable" class of bug the 404 case above was already fixed for, just for a different status
# code. A malformed query can never succeed by retrying; the fix must name the real problem instead.

def test_a_real_400_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400, json={"Fault": {"Code": "PUGREST.BadRequest", "Message": "Unable to standardize the given structure"}})

    response = _get_with_retry(_client(handler), "https://pubchem.test/x", sleep=lambda _s: None)
    assert response.status_code == 400 and len(calls) == 1


def test_malformed_smiles_is_reported_as_invalid_not_as_an_outage():
    client = _client(lambda request: httpx.Response(400, json={"Fault": {"Code": "PUGREST.BadRequest", "Message": "Unable to standardize the given structure"}}))
    with pytest.raises(ValueError, match="rejected this SMILES query as invalid"):
        _resolve_cid(client, "XJ(not-a-smiles)", "smiles")


def test_malformed_query_surfaces_as_a_validation_error_not_a_temporary_outage(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    def bad_request(query, mode):
        raise ValueError(f"PubChem rejected this {mode.upper()} query as invalid: Unable to standardize the given structure. Check the SMILES syntax.")

    monkeypatch.setattr("app.main.resolve_pubchem_identity", bad_request)
    with TestClient(app) as client:
        response = client.post("/api/identities/resolve", json={"query": "not-a-smiles", "query_mode": "smiles"})
    assert response.status_code == 422
    assert "temporarily unavailable" not in response.text
    assert "invalid" in response.text
