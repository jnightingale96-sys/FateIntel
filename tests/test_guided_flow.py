from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "app" / "static"


def test_guided_interface_contains_progressive_story_flow():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    required = [
        'id="step-identity"',
        'id="step-use"',
        'id="regulatory-pathway"',
        'id="step-release"',
        'id="step-compartments"',
        'id="step-models"',
        'id="step-tier"',
        'id="assistant-panel"',
        'id="results"',
        'id="us-models-placeholder"',
        'id="us-exposure-scenario"',
        'id="run-us-exposure"',
    ]
    for marker in required:
        assert marker in html


def test_guided_javascript_orchestrates_real_working_endpoints():
    script = (STATIC / "app.js").read_text(encoding="utf-8")
    endpoints = [
        "/api/model-runs/sorption",
        "/api/model-runs/emission",
        "/api/model-runs/activity-simpletreat",
        "/api/model-runs/wastewater-irrigation-comparison",
        "/api/model-runs/biosolids",
        "/api/model-runs/plant-uptake",
        "/api/model-runs/pearl-groundwater",
        "/api/global-regulatory/pathway",
        "/api/us-exposure/manifest",
        "/api/model-runs/us-industrial-exposure",
    ]
    for endpoint in endpoints:
        assert endpoint in script
