"""POPs regulatory-status flag: data integrity, matching and fail-closed behaviour."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pops
from app.services.conceptual_site_model import (
    ConceptualSiteModel, Contaminant, PathwayLink, Source, assess,
)


def _cas_checksum_ok(cas: str) -> bool:
    body, check = cas.rsplit("-", 1)[0].replace("-", ""), cas.rsplit("-", 1)[1]
    total = sum((i + 1) * int(d) for i, d in enumerate(reversed(body)))
    return total % 10 == int(check)


def _entries():
    return pops._reference()["entries"]


def test_every_cas_number_in_the_seed_list_passes_the_check_digit():
    bad = [(e["key"], c) for e in _entries() for c in e["cas"] if not _cas_checksum_ok(c)]
    assert bad == []


def test_keys_and_cas_numbers_are_unique():
    keys = [e["key"] for e in _entries()]
    assert len(keys) == len(set(keys))
    cas = [c for e in _entries() for c in e["cas"]]
    assert len(cas) == len(set(cas))


def test_every_entry_is_sourced_and_marked_with_an_eu_verification_status():
    allowed = {"CONFIRMED_ORIGINAL_2019_TEXT", "CONFIRMED_VIA_EU_MATRIX_RESEARCH",
               "LISTED_PER_EU_MATRIX_CONSOLIDATED_READ", "PROPOSED_NOT_CONFIRMED", "NOT_CONFIRMED"}
    for entry in _entries():
        assert entry["eu"]["status"] in allowed, entry["key"]
        assert set(entry["stockholm_annexes"]) <= {"A", "B", "C"}
    meta = pops.reference_metadata()
    assert meta["stockholm_source"].startswith("https://chm.pops.int")
    assert meta["eu_source"].startswith("https://eur-lex.europa.eu")
    assert any("decaBDE" in c for c in meta["caveats"])


def test_ddt_by_cas_reports_stockholm_annex_b_and_eu_annex_i():
    result = pops.pops_status(cas_number="50-29-3")
    assert result["status"] == "POPS_REGULATORY_STATUS_DETECTED"
    assert result["match_basis"] == "cas"
    match = result["matches"][0]
    assert match["stockholm_convention"]["annexes"] == ["B"]
    assert match["eu_pops_regulation_2019_1021"]["annex"] == "I"
    assert "Annexes IV" in match["waste_management"]


def test_pcbs_are_listed_under_both_annex_a_and_c():
    match = pops.pops_status(cas_number="1336-36-3")["matches"][0]
    assert match["stockholm_convention"]["annexes"] == ["A", "C"]
    assert "31 December 2025" in match["eu_pops_regulation_2019_1021"]["exemptions"]


@pytest.mark.parametrize("name", ["PCB-153", "Aroclor 1254", "polychlorinated biphenyls", "PCBs"])
def test_pcb_names_match_with_a_confirm_by_cas_warning(name):
    result = pops.pops_status(name=name)
    assert result["status"] == "POPS_REGULATORY_STATUS_DETECTED"
    assert result["match_basis"] == "name"
    assert "Confirm the substance identity by CAS" in result["confidence_note"]


@pytest.mark.parametrize("name", ["furan", "dibenzofuran", "PCP (phencyclidine)", "benzene", "lead", "DDTX"])
def test_lookalike_names_do_not_false_match(name):
    assert pops.pops_status(name=name)["status"] == "NOT_DETERMINED"


def test_miss_is_never_reported_as_not_a_pop():
    result = pops.pops_status(cas_number="71-43-2", name="benzene")
    assert result["status"] == "NOT_DETERMINED"
    assert "not evidence" in result["seed_list_limits"]
    assert result["matches"] == []


def test_no_input_is_not_determined_with_a_reason():
    result = pops.pops_status()
    assert result["status"] == "NOT_DETERMINED" and "No CAS number or name" in result["reason"]


def test_cas_and_name_that_disagree_are_an_identity_conflict_not_resolved():
    result = pops.pops_status(cas_number="50-29-3", name="chlordane")
    assert result["status"] == "IDENTITY_CONFLICT"
    assert result["matches"] == []


def test_agreeing_cas_and_name_match_on_cas():
    result = pops.pops_status(cas_number="58-89-9", name="Lindane")
    assert result["status"] == "POPS_REGULATORY_STATUS_DETECTED" and result["match_basis"] == "cas"


def test_proposed_listing_is_not_presented_as_in_force():
    match = pops.pops_status(name="chlorpyrifos")["matches"][0]
    assert match["eu_pops_regulation_2019_1021"]["status"] == "PROPOSED_NOT_CONFIRMED"
    assert match["waste_management"].startswith("NOT ESTABLISHED")
    assert match["stockholm_convention"]["annexes"] == ["A"]


def test_dioxins_are_stockholm_annex_c_only_and_eu_release_inventory():
    match = pops.pops_status(name="2,3,7,8-TCDD dioxin")["matches"][0]
    assert match["stockholm_convention"]["annexes"] == ["C"]
    assert match["eu_pops_regulation_2019_1021"]["annex"].startswith("III Part A")


def test_national_implementation_is_only_claimed_for_the_eu():
    assert "directly applicable" in pops.pops_status(cas_number="50-29-3", jurisdiction="EU")["national_implementation"]
    assert pops.pops_status(cas_number="50-29-3", jurisdiction="UK")["national_implementation"].startswith("NOT RESEARCHED")


def test_api_status_reference_and_validation():
    with TestClient(app) as client:
        ok = client.get("/api/pops/status", params={"cas_number": "118-74-1", "jurisdiction": "EU"})
        assert ok.status_code == 200 and ok.json()["matches"][0]["key"] == "hcb"
        assert client.get("/api/pops/status", params={"name": "benzene"}).json()["status"] == "NOT_DETERMINED"
        assert client.get("/api/pops/status", params={"name": "x", "jurisdiction": "XX"}).status_code == 422
        reference = client.get("/api/pops/reference").json()
        assert reference["substance_count"] == len(_entries())
        assert client.get("/api/chemicals/999999999/pops-status").status_code == 404


def test_site_model_carries_pops_flag_per_contaminant():
    model = ConceptualSiteModel(
        sources=(Source("S1", "former_manufacturing", ("soil",), (
            Contaminant("PCB-153", "legacy_pop_organic", "1336-36-3"),
            Contaminant("zinc", "metal_inorganic"),
        )),),
        receptors=("residents",), links=(PathwayLink("ingestion", "soil", "residents"),),
    )
    result = assess(model, "EU")
    by_name = {x["contaminant"]: x["pops_status"] for x in result["linkages"]}
    assert by_name == {"PCB-153": "POPS_REGULATORY_STATUS_DETECTED", "zinc": "NOT_DETERMINED"}
    flags = {f["contaminant"]: f for f in result["contaminant_pops_flags"]}
    assert flags["PCB-153"]["matches"][0]["key"] == "pcb"
    assert flags["PCB-153"]["national_implementation"].startswith("Regulation (EU)")
