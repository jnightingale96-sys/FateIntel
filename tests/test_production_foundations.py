from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.exceptions import ChemicalIdentityError
from app.logging_config import JsonFormatter
from app.main import BUILD_ID, app


def test_settings_are_validated_from_environment(monkeypatch):
    monkeypatch.setenv("ENVIROCHEM_PORT", "9812")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    monkeypatch.setenv("LOG_FORMAT", "json")
    configured = Settings(_env_file=None)
    assert configured.envirochem_port == 9812
    assert configured.log_level == "WARNING"
    assert configured.log_format == "json"
    assert configured.database_backend == "sqlite"


def test_invalid_log_level_is_rejected(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "verbose-ish")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_env_file_precedence_is_deterministic(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ENVIROCHEM_PORT=9200\nLOG_LEVEL=ERROR\n", encoding="utf-8")
    monkeypatch.delenv("ENVIROCHEM_PORT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    from_file = Settings(_env_file=env_file)
    assert from_file.envirochem_port == 9200
    assert from_file.log_level == "ERROR"

    monkeypatch.setenv("ENVIROCHEM_PORT", "9300")
    from_environment = Settings(_env_file=env_file)
    assert from_environment.envirochem_port == 9300
    explicit = Settings(_env_file=env_file, envirochem_port=9400)
    assert explicit.envirochem_port == 9400


def test_health_readiness_and_request_correlation_contract():
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"X-Request-ID": "qa-health-219"})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "qa-health-219"
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["checks"]["database"]["status"] == "ok"
        assert payload["checks"]["database"]["backend"] == "sqlite"
        assert "latency_ms" in payload["checks"]["database"]

        ready = client.get("/api/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"


def test_readiness_returns_503_when_database_check_fails(monkeypatch):
    monkeypatch.setattr(
        "app.main.database_diagnostics",
        lambda: {"status": "error", "backend": "sqlite", "latency_ms": 1.0, "error_type": "OperationalError"},
    )
    with TestClient(app) as client:
        response = client.get("/api/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"


def test_typed_application_error_has_safe_machine_readable_response(monkeypatch):
    def fail_resolution(query, query_mode):
        raise ChemicalIdentityError("Identity candidate requires manual adjudication", details={"query_mode": query_mode})

    monkeypatch.setattr("app.main.resolve_pubchem_identity", fail_resolution)
    with TestClient(app) as client:
        response = client.post(
            "/api/identities/resolve",
            json={"query": "production-foundations-unknown-chemical", "query_mode": "iupac"},
            headers={"X-Request-ID": "qa-error-219"},
        )
        assert response.status_code == 422
        payload = response.json()
        assert payload["detail"] == "Identity candidate requires manual adjudication"
        assert payload["error"]["code"] == "chemical_identity_error"
        assert payload["request_id"] == "qa-error-219"


def test_json_log_formatter_is_machine_readable():
    import logging

    record = logging.LogRecord("envirochem.test", logging.INFO, __file__, 1, "profile %s", ("saved",), None)
    record.request_id = "qa-log-219"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "profile saved"
    assert payload["request_id"] == "qa-log-219"
    assert payload["level"] == "INFO"


def test_build_identifies_production_foundations_without_runtime_port_in_hash():
    assert "v2.23" in BUILD_ID
    assert "8792" not in BUILD_ID
    with TestClient(app) as client:
        payload = client.get("/api/build").json()
    assert payload["default_port"] == 8792
    assert payload["request_tracing"] is True
    assert payload["database_backend"] == "sqlite"
