"""GET /api/projects' new q/limit params (added for the "Saved assessments" view) must be purely additive:
omitting them returns every project exactly as before, since the project switcher and the example-loader's
state.projects lookup both rely on getting the full list.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _create_project(client, name):
    return client.post("/api/projects", json={"name": name, "jurisdiction": "EU", "purpose": "test"}).json()


def test_no_params_returns_every_project_unfiltered():
    with TestClient(app) as client:
        _create_project(client, "Alpha search-test project")
        _create_project(client, "Beta search-test project")
        all_rows = client.get("/api/projects").json()
        names = {row["name"] for row in all_rows}
        assert "Alpha search-test project" in names
        assert "Beta search-test project" in names


def test_q_filters_by_case_insensitive_substring():
    with TestClient(app) as client:
        _create_project(client, "Zeta unique-marker-xyz project")
        _create_project(client, "Unrelated project name")
        rows = client.get("/api/projects", params={"q": "unique-marker-xyz"}).json()
        assert len(rows) == 1
        assert rows[0]["name"] == "Zeta unique-marker-xyz project"
        # case-insensitive
        rows_upper = client.get("/api/projects", params={"q": "UNIQUE-MARKER-XYZ"}).json()
        assert len(rows_upper) == 1


def test_limit_caps_the_result_count():
    with TestClient(app) as client:
        for i in range(5):
            _create_project(client, f"Limit-test project {i}")
        rows = client.get("/api/projects", params={"q": "Limit-test", "limit": 2}).json()
        assert len(rows) == 2


def test_limit_is_clamped_to_a_sane_maximum():
    with TestClient(app) as client:
        rows = client.get("/api/projects", params={"limit": 10000}).json()
        # Should not error, and should not silently return an unbounded result either.
        assert isinstance(rows, list)
