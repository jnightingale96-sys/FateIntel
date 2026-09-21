"""Conceptual site model SVG diagram."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from app.main import app
from app.services.conceptual_site_model import model_from_dict
from app.services.csm_diagram import EXAMPLE_SITE_PAYLOAD, GREEN, AMBER, LINE, render_svg


def _svg(payload=None):
    payload = payload or EXAMPLE_SITE_PAYLOAD
    return render_svg(model_from_dict(payload), payload["jurisdiction"])


def test_example_diagram_is_well_formed_xml_with_a_viewbox():
    root = ET.fromstring(_svg())
    assert root.tag.endswith("svg")
    assert root.attrib["viewBox"].startswith("0 0 ")
    assert root.attrib["role"] == "img"


def test_diagram_shows_sources_media_receptors_and_pathway_labels():
    svg = _svg()
    for text in ("S1", "former manufacturing", "lead", "PCB-153", "soil", "groundwater", "residents",
                 "aquatic organisms", "soil to groundwater", "groundwater to surface water"):
        assert text in svg, text


def test_pop_badge_only_on_detected_substances():
    svg = _svg()
    assert svg.count("· POP") == 1  # PCB-153 by CAS; lead and trichloroethylene are not flagged
    assert "PCB-153 <tspan" in svg


def test_edge_colours_reflect_data_state():
    svg = _svg()
    assert f'stroke="{GREEN}"' in svg      # soil -> residents etc. (lead measured in soil)
    assert f'stroke="{AMBER}"' in svg      # linkages needing an unmeasured contaminant
    assert f'stroke="{LINE}" stroke-width="2" stroke-dasharray' in svg  # orphan erosion pathway


def test_receptor_without_linkage_is_dashed_and_labelled_not_called_safe():
    svg = _svg()
    assert "receptor: no linkage identified" in svg
    assert "not a finding of no risk" in svg
    assert "no exposure or risk is calculated" in svg
    lowered = svg.lower()
    for banned in ("safe", "acceptable", "no risk."):
        assert banned not in lowered


def test_hostile_names_are_escaped_and_svg_still_parses():
    payload = {
        "jurisdiction": "UK",
        "sources": [{"id": "S<1>", "kind": "spill", "release_media": ["soil"],
                     "contaminants": [{"name": 'x"><script>alert(1)</script>&', "contaminant_group": "pah"}]}],
        "receptors": ["residents"],
        "links": [{"pathway": "ingestion", "from": "soil", "to": "residents"}],
    }
    svg = _svg(payload)
    assert "<script>" not in svg
    ET.fromstring(svg)


def test_minimal_model_without_links_still_renders():
    payload = {
        "jurisdiction": "US",
        "sources": [{"id": "S1", "kind": "waste", "release_media": ["soil"],
                     "contaminants": [{"name": "zinc", "contaminant_group": "metal_inorganic"}]}],
        "receptors": [],
    }
    ET.fromstring(_svg(payload))


def test_api_diagram_endpoints():
    with TestClient(app) as client:
        example = client.get("/api/conceptual-site-model/diagram/example")
        assert example.status_code == 200
        assert example.headers["content-type"].startswith("image/svg+xml")
        ET.fromstring(example.text)
        posted = client.post("/api/conceptual-site-model/diagram", json=EXAMPLE_SITE_PAYLOAD)
        assert posted.status_code == 200 and posted.text == example.text
        assert client.post("/api/conceptual-site-model/diagram", json={**EXAMPLE_SITE_PAYLOAD, "jurisdiction": "XX"}).status_code == 422
        bad = {**EXAMPLE_SITE_PAYLOAD, "links": [{"pathway": "ingestion", "from": "air", "to": "residents"}]}
        assert client.post("/api/conceptual-site-model/diagram", json=bad).status_code == 422
