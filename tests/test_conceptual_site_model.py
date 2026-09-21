"""Conceptual site model: validation, linkage mapping, gaps and fail-closed behaviour."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.conceptual_site_model import (
    ConceptualSiteModel, ConceptualSiteModelError, Contaminant, PathwayLink, Source,
    assess, external_route, model_from_dict,
)


def _lead_site(measured=None, receptors=("residents", "groundwater")):
    source = Source(
        id="S1", kind="former_manufacturing", release_media=("soil",),
        contaminants=(Contaminant("lead", "metal_inorganic"),),
    )
    links = (
        PathwayLink("ingestion", "soil", "residents"),
        PathwayLink("soil_to_groundwater", "soil", "groundwater"),
    )
    return ConceptualSiteModel(
        sources=(source,), receptors=receptors, links=links,
        measured={"soil": ("lead",)} if measured is None else measured,
    )


def test_finds_linkages_to_each_connected_receptor_with_external_routes():
    result = assess(_lead_site(), "UK")
    by_receptor = {x["receptor"]: x for x in result["linkages"]}
    assert set(by_receptor) == {"residents", "groundwater"}
    assert "CLEA" in by_receptor["residents"]["external_route"]["route"]
    assert "ConSim" in by_receptor["groundwater"]["external_route"]["route"]
    assert by_receptor["residents"]["taxonomy_letter"] == "C"
    assert result["summary"]["potential_linkages"] == 2


def test_multi_hop_path_soil_to_groundwater_to_surface_water():
    model = ConceptualSiteModel(
        sources=(Source("S1", "landfill", ("soil",), (Contaminant("PCB-153", "legacy_pop_organic"),)),),
        receptors=("surface_water",),
        links=(PathwayLink("soil_to_groundwater", "soil", "groundwater"),
               PathwayLink("groundwater_to_surface_water", "groundwater", "surface_water")),
    )
    linkage = assess(model, "UK")["linkages"][0]
    assert [step["pathway"] for step in linkage["path"]] == ["soil_to_groundwater", "groundwater_to_surface_water"]
    assert linkage["receptor"] == "surface_water"


def test_missing_measurements_are_reported_not_assumed():
    result = assess(_lead_site(measured={}), "UK")
    assert all(x["status"] == "POTENTIAL_LINKAGE_MEASUREMENT_MISSING" for x in result["linkages"])
    assert result["summary"]["measurement_gaps"] == 2
    assert "measured lead concentration in soil" in result["linkages"][0]["missing_data"][0]


def test_measured_data_in_release_medium_clears_the_gap():
    result = assess(_lead_site(), "UK")
    assert all(x["status"] == "POTENTIAL_LINKAGE_DATA_PRESENT" for x in result["linkages"])


def test_receptor_with_no_linkage_is_not_called_safe():
    result = assess(_lead_site(receptors=("residents", "wildlife")), "UK")
    missing = result["receptors_without_linkage"]
    assert [m["receptor"] for m in missing] == ["wildlife"]
    assert missing[0]["status"] == "NO_LINKAGE_IDENTIFIED"
    assert "Not a finding of no risk" in missing[0]["note"]


def test_orphan_pathway_links_and_unlinked_sources_are_flagged():
    model = ConceptualSiteModel(
        sources=(Source("S1", "spill", ("soil",), (Contaminant("benzene", "hydrocarbon_solvent"),)),
                 Source("S2", "waste", ("sediment",), (Contaminant("zinc", "metal_inorganic"),))),
        receptors=("residents",),
        links=(PathwayLink("ingestion", "soil", "residents"),
               PathwayLink("inhalation", "air", "residents")),
    )
    result = assess(model, "US")
    assert result["sources_without_linkage"] == ["S2"]
    assert [u["pathway"] for u in result["unsupported_pathway_links"]] == ["inhalation"]


def test_release_directly_into_a_protected_resource_is_a_zero_hop_linkage():
    model = ConceptualSiteModel(
        sources=(Source("S1", "spill", ("groundwater",), (Contaminant("TCE", "hydrocarbon_solvent"),)),),
        receptors=("groundwater",), links=(),
    )
    linkage = assess(model, "UK")["linkages"][0]
    assert linkage["path"] == [] and linkage["receptor"] == "groundwater"


def test_radionuclide_and_mixture_contaminants_are_flagged_external_not_assessed():
    model = ConceptualSiteModel(
        sources=(Source("S1", "mining", ("soil",),
                        (Contaminant("radium-226", "radionuclide"), Contaminant("mixed fill", "contaminated_mixture"))),),
        receptors=("residents",), links=(PathwayLink("ingestion", "soil", "residents"),),
    )
    for linkage in assess(model, "UK")["linkages"]:
        assert "EXTERNAL MODEL REQUIRED" in linkage["native_assessment"]


def test_unconfirmed_external_routes_are_not_invented():
    assert external_route("UK", "wildlife")["route"].startswith("REGULATORY APPLICABILITY NOT ESTABLISHED")
    assert external_route("CH", "residents")["route"].startswith("REGULATORY APPLICABILITY NOT ESTABLISHED")
    assert "FCSAP" in external_route("CA", "workers")["route"]


def test_no_risk_number_or_verdict_anywhere_in_the_output():
    text = str(assess(_lead_site(), "UK")).lower()
    import re
    cleaned = text.replace("not a finding of no risk", "").replace("no risk is calculated", "")
    for banned in (r"\bsafe\b", r"\bacceptable\b", r"risk quotient", r"\bpec\b", r"\bpnec\b"):
        assert not re.search(banned, cleaned), banned


@pytest.mark.parametrize("builder, message", [
    (lambda: PathwayLink("soil_to_groundwater", "air", "groundwater"), "cannot start"),
    (lambda: PathwayLink("ingestion", "soil", "sediment"), "cannot reach"),
    (lambda: PathwayLink("teleportation", "soil", "residents"), "Unknown pathway"),
    (lambda: Source("S1", "picnic", ("soil",), (Contaminant("x", "pah"),)), "Unknown source kind"),
    (lambda: Source("S1", "spill", ("lava",), (Contaminant("x", "pah"),)), "release_media"),
    (lambda: Source("S1", "spill", ("soil",), ()), "at least one contaminant"),
    (lambda: Contaminant("x", "not_a_group"), "Unknown contaminant_group"),
    (lambda: ConceptualSiteModel(sources=(), receptors=(), links=()), "at least one source"),
    (lambda: ConceptualSiteModel(
        sources=(Source("S1", "spill", ("soil",), (Contaminant("x", "pah"),)),), receptors=("aliens",), links=()),
     "Unknown receptor"),
])
def test_structural_errors_fail_closed(builder, message):
    with pytest.raises(ConceptualSiteModelError, match=message):
        builder()


def test_duplicate_source_ids_rejected():
    src = Source("S1", "spill", ("soil",), (Contaminant("x", "pah"),))
    with pytest.raises(ConceptualSiteModelError, match="unique"):
        ConceptualSiteModel(sources=(src, src), receptors=(), links=())


def test_model_from_dict_rejects_malformed_input():
    with pytest.raises(ConceptualSiteModelError, match="Malformed"):
        model_from_dict({"sources": [{"id": "S1"}]})


_PAYLOAD = {
    "jurisdiction": "UK",
    "sources": [{"id": "S1", "kind": "landfill", "release_media": ["soil"],
                 "contaminants": [{"name": "benzo[a]pyrene", "contaminant_group": "pah"}]}],
    "receptors": ["residents"],
    "links": [{"pathway": "ingestion", "from": "soil", "to": "residents"}],
    "measured": {"soil": ["benzo[a]pyrene"]},
}


def test_api_reference_and_assess_round_trip():
    with TestClient(app) as client:
        reference = client.get("/api/conceptual-site-model/reference").json()
        assert "soil_to_groundwater" in reference["pathways"]
        response = client.post("/api/conceptual-site-model/assess", json=_PAYLOAD)
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["potential_linkages"] == 1
        assert body["linkages"][0]["status"] == "POTENTIAL_LINKAGE_DATA_PRESENT"


def test_api_rejects_bad_jurisdiction_and_bad_model():
    with TestClient(app) as client:
        assert client.post("/api/conceptual-site-model/assess", json={**_PAYLOAD, "jurisdiction": "XX"}).status_code == 422
        bad = {**_PAYLOAD, "links": [{"pathway": "ingestion", "from": "air", "to": "residents"}]}
        assert client.post("/api/conceptual-site-model/assess", json=bad).status_code == 422
