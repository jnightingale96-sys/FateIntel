import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.multimedia_fate import run_multimedia_fate_screen
from app.services.river_network import run_catchment_river_network


ROOT = Path(__file__).resolve().parents[1]


def test_multimedia_screen_solves_and_closes_mass_balance():
    result = run_multimedia_fate_screen({
        "emissions_kg_day": {"air": 1.0},
        "compartments": [
            {
                "key": "air",
                "volume_m3": 1.0e9,
                "half_life_days": 10.0,
                "advective_loss_per_day": 0.1,
            },
            {
                "key": "freshwater",
                "volume_m3": 1.0e6,
                "half_life_days": 20.0,
                "advective_loss_per_day": 0.02,
            },
        ],
        "transfers": [
            {"source": "air", "target": "freshwater", "rate_per_day": 0.05},
            {"source": "freshwater", "target": "air", "rate_per_day": 0.01},
        ],
    })
    assert result["model_key"] == "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN"
    assert len(result["compartments"]) == 2
    assert all(row["mass_kg"] >= 0 for row in result["compartments"])
    assert len(result["intermedia_fluxes"]) == 2
    assert result["mass_balance"]["relative_closure_error"] == pytest.approx(0.0, abs=1e-12)
    assert "not an execution of SimpleBox" in result["warnings"][0]


def test_multimedia_screen_requires_terminal_loss():
    with pytest.raises(ValueError, match="singular|constrained|solved"):
        run_multimedia_fate_screen({
            "emissions_kg_day": {"air": 1.0},
            "compartments": [
                {"key": "air", "volume_m3": 1.0e9},
                {"key": "freshwater", "volume_m3": 1.0e6},
            ],
            "transfers": [
                {"source": "air", "target": "freshwater", "rate_per_day": 0.1},
                {"source": "freshwater", "target": "air", "rate_per_day": 0.1},
            ],
        })


def test_catchment_river_routes_wwtp_load_and_closes():
    result = run_catchment_river_network({
        "default_water_dt50_days": 10.0,
        "aquatic_pnec_ug_l": 0.5,
        "segments": [
            {
                "segment_id": "A",
                "flow_m3_day": 10_000.0,
                "travel_time_days": 1.0,
                "local_effluent_concentration_ug_l": 10.0,
                "local_effluent_flow_m3_day": 1_000.0,
            },
            {
                "segment_id": "B",
                "upstream_ids": ["A"],
                "flow_m3_day": 20_000.0,
                "travel_time_days": 2.0,
            },
        ],
    })
    first, second = result["segments"]
    assert first["local_effluent_load_kg_day"] == pytest.approx(0.01)
    assert first["inlet_concentration_ug_l"] == pytest.approx(1.0)
    assert first["outlet_load_kg_day"] == pytest.approx(0.01 * math.pow(2.0, -0.1))
    assert second["upstream_load_kg_day"] == pytest.approx(first["outlet_load_kg_day"])
    assert result["network_summary"]["mass_balance_error_kg_day"] == pytest.approx(0.0, abs=1e-12)
    assert result["network_summary"]["segments_above_pnec"]


def test_catchment_river_supports_confluences():
    result = run_catchment_river_network({
        "default_water_dt50_days": 100.0,
        "segments": [
            {"segment_id": "A", "flow_m3_day": 1000, "travel_time_days": 1, "local_load_kg_day": 0.001},
            {"segment_id": "B", "flow_m3_day": 2000, "travel_time_days": 1, "local_load_kg_day": 0.002},
            {"segment_id": "C", "upstream_ids": ["A", "B"], "flow_m3_day": 4000, "travel_time_days": 1},
        ],
    })
    by_id = {row["segment_id"]: row for row in result["segments"]}
    assert by_id["C"]["upstream_load_kg_day"] == pytest.approx(
        by_id["A"]["outlet_load_kg_day"] + by_id["B"]["outlet_load_kg_day"]
    )
    assert result["network_summary"]["mass_balance_error_kg_day"] == pytest.approx(0.0, abs=1e-12)


def test_catchment_river_warns_on_implausible_dilution_jump():
    result = run_catchment_river_network({
        "default_water_dt50_days": 100.0,
        "segments": [
            {"segment_id": "A", "flow_m3_day": 1000, "travel_time_days": 1, "local_load_kg_day": 0.001},
            {"segment_id": "B", "upstream_ids": ["A"], "flow_m3_day": 11000, "travel_time_days": 1},
        ],
    })
    assert any("more than 10 times" in warning for warning in result["warnings"])


def test_catchment_river_rejects_cycles():
    with pytest.raises(ValueError, match="cycle"):
        run_catchment_river_network({
            "default_water_dt50_days": 10,
            "segments": [
                {"segment_id": "A", "upstream_ids": ["B"], "flow_m3_day": 1000, "travel_time_days": 1},
                {"segment_id": "B", "upstream_ids": ["A"], "flow_m3_day": 1000, "travel_time_days": 1},
            ],
        })


def test_model_expansion_api_persists_both_run_types():
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "v2.15 model expansion API test"}).json()
        chemical = client.get("/api/chemicals").json()[0]

        multimedia = client.post("/api/model-runs/multimedia-fate", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "emissions_kg_day": {"air": 1.0},
            "compartments": [
                {"key": "air", "volume_m3": 1.0e9, "half_life_days": 10, "advective_loss_per_day": 0.1},
                {"key": "freshwater", "volume_m3": 1.0e6, "half_life_days": 20, "advective_loss_per_day": 0.02},
            ],
            "transfers": [{"source": "air", "target": "freshwater", "rate_per_day": 0.05}],
        })
        assert multimedia.status_code == 200, multimedia.text
        assert multimedia.json()["outputs"]["model_key"] == "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN"

        river = client.post("/api/model-runs/catchment-river", json={
            "project_id": project["id"],
            "chemical_id": chemical["id"],
            "default_water_dt50_days": 10,
            "segments": [{
                "segment_id": "reach-1",
                "flow_m3_day": 20_000,
                "travel_time_days": 1,
                "local_effluent_concentration_ug_l": 0.7,
                "local_effluent_flow_m3_day": 2_000,
            }],
        })
        assert river.status_code == 200, river.text
        assert river.json()["outputs"]["model_key"] == "ENVIROCHEM_CATCHMENT_RIVER_NETWORK"


def test_model_expansion_is_exposed_in_professional_ui():
    html = (ROOT / "app" / "static" / "expert.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "static" / "expert-app.js").read_text(encoding="utf-8")
    assert 'id="multimedia-form"' in html
    assert 'id="river-network-form"' in html
    assert "/api/model-runs/multimedia-fate" in js
    assert "/api/model-runs/catchment-river" in js
    assert "not labelled as SimpleBox output" in html
