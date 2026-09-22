"""Workflow registry: which tracks, stages and screens apply to a region and chemical group."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.conceptual_site_model import EXTERNAL_ROUTES, NOT_ESTABLISHED
from app.services.registry import CONTAMINANT_GROUPS, DISCRETE_ORGANIC_GROUPS, NO_NATIVE_PATHWAY_GROUPS
from app.services.workflow_registry import (
    FAMILIES, GROUP_LABELS, MODULES, REGIONS, SITE, USE_RELEASE, WorkflowError, reference, resolve_workflow,
)

client = TestClient(app)
ORGANIC_USE_GROUPS = ["human_pharmaceutical", "veterinary_pharmaceutical", "industrial_organic", "pesticide", "biocide"]


def stage(workflow, track_id, stage_id):
    track = next(t for t in workflow["tracks"] if t["id"] == track_id)
    return next(s for s in track["stages"] if s["id"] == stage_id)


# ---------- the registry is complete and consistent ----------
def test_every_group_belongs_to_exactly_one_family_and_has_a_label():
    seen = [g for f in FAMILIES for g in f["groups"]]
    assert sorted(seen) == sorted(CONTAMINANT_GROUPS) and len(seen) == len(set(seen))
    assert set(GROUP_LABELS) == set(CONTAMINANT_GROUPS)


def test_every_family_track_is_known_and_default_is_one_of_them():
    for family in FAMILIES:
        assert set(family["tracks"]) <= {USE_RELEASE, SITE}
        assert (family["default_track"] in family["tracks"]) if family["tracks"] else family["default_track"] is None


def test_blocked_groups_are_exactly_the_families_with_no_tracks():
    no_track = {g for f in FAMILIES if not f["tracks"] for g in f["groups"]}
    assert no_track == set(NO_NATIVE_PATHWAY_GROUPS)


def test_every_resolvable_pair_resolves_and_only_names_known_modules():
    for region in REGIONS:
        for group in CONTAMINANT_GROUPS:
            wf = resolve_workflow(region, group)
            assert set(wf["modules"]) <= set(MODULES)
            assert set(wf["modules"]) | {h["module"] for h in wf["hidden_modules"]} == set(MODULES)
            assert not set(wf["modules"]) & {h["module"] for h in wf["hidden_modules"]}
            for track in wf["tracks"]:
                for s in track["stages"]:
                    assert s["module"] is None or s["module"] in wf["modules"], (region, group, s)


# ---------- contaminated land stays out of organic chemical assessments ----------
@pytest.mark.parametrize("region", list(REGIONS))
@pytest.mark.parametrize("group", ORGANIC_USE_GROUPS + ["personal_care_cosmetic", "detergent_cleaner"])
def test_contaminated_land_never_appears_for_use_based_organic_groups(region, group):
    wf = resolve_workflow(region, group)
    assert "contaminated_land" not in wf["modules"]
    assert [t["id"] for t in wf["tracks"]] == [USE_RELEASE]


@pytest.mark.parametrize("group", ["metal_inorganic", "pah", "legacy_pop_organic", "organotin", "hydrocarbon_solvent", "pfas_persistent_mobile"])
def test_contaminated_land_is_offered_for_the_site_relevant_groups(group):
    wf = resolve_workflow("US", group)
    assert "contaminated_land" in wf["modules"]
    assert SITE in [t["id"] for t in wf["tracks"]]


def test_site_first_groups_open_on_the_site_track():
    for group in ("metal_inorganic", "pah", "legacy_pop_organic", "organotin", "hydrocarbon_solvent"):
        assert resolve_workflow("EU", group)["default_track"] == SITE
    assert resolve_workflow("EU", "pfas_persistent_mobile")["default_track"] == USE_RELEASE


# ---------- native organic screens only where valid ----------
def test_native_screen_and_organic_tools_follow_discrete_organic_groups():
    for group in CONTAMINANT_GROUPS:
        if group in NO_NATIVE_PATHWAY_GROUPS:
            continue
        wf = resolve_workflow("US", group)
        native = group in DISCRETE_ORGANIC_GROUPS
        assert ("results" in wf["modules"]) == native, group
        assert ("kinetics" in wf["modules"]) == native, group
        screen = stage(wf, USE_RELEASE, "screen")
        assert screen["status"] == ("available" if native else "external_required")
        if not native:
            assert screen["module"] is None and "external" in screen["note"]


# ---------- blocked groups ----------
@pytest.mark.parametrize("group", sorted(NO_NATIVE_PATHWAY_GROUPS))
@pytest.mark.parametrize("region", list(REGIONS))
def test_blocked_groups_have_no_tracks_and_only_the_route_page(region, group):
    wf = resolve_workflow(region, group)
    assert wf["blocked"] is True and wf["tracks"] == [] and wf["default_track"] is None
    assert wf["modules"] == ["plan"] and "does not model" in wf["reason"]


# ---------- regions differ, following what is actually built ----------
@pytest.mark.parametrize("region", ["EU", "UK", "CH"])
def test_focus_regions_all_have_the_shared_refinement_screens_and_not_the_us_ones(region):
    wf = resolve_workflow(region, "human_pharmaceutical")
    assert {"water_sediment", "pearl"} <= set(wf["modules"]) and "us_models" not in wf["modules"]
    assert stage(wf, USE_RELEASE, "refine")["status"] == "available"


def test_uk_and_switzerland_each_have_their_own_tab_not_a_shared_eu_one():
    # The three used to be one combined region ("EU, UK and Switzerland"); each now resolves separately.
    assert {"EU", "UK", "CH"} <= set(REGIONS)
    assert "EU_UK_CH" not in REGIONS
    assert REGIONS["UK"]["jurisdictions"] == ["UK"] and REGIONS["CH"]["jurisdictions"] == ["CH"]
    assert REGIONS["UK"]["label"] != REGIONS["EU"]["label"] != REGIONS["CH"]["label"]


def test_uk_and_switzerland_get_their_own_regulatory_route_text_not_eu_reach():
    # Before this, any jurisdiction other than US/AU/CA/NZ fell into _regulatory_programme's unguarded EU-labelled
    # tail, so a UK or CH assessment would have silently been told it was routed through "EU REACH". Confirm that
    # bug is gone: each names its own regime, and neither is labelled with the other's or EU's wording.
    uk = stage(resolve_workflow("UK", "industrial_organic"), USE_RELEASE, "route")
    ch = stage(resolve_workflow("CH", "industrial_organic"), USE_RELEASE, "route")
    assert "UK REACH" in uk["detail"] and uk["status"] == "available"
    assert "ChemO" in ch["detail"] and "REACH" not in ch["detail"] and ch["status"] == "available"
    assert "UK REACH" not in ch["detail"] and "EU REACH" not in uk["detail"] and "EU REACH" not in ch["detail"]


def test_us_flow_has_the_us_models_and_not_the_eu_screens():
    us = resolve_workflow("US", "pesticide")
    assert "us_models" in us["modules"] and not {"water_sediment", "pearl"} & set(us["modules"])
    assert stage(us, USE_RELEASE, "refine")["status"] == "managed_external"


@pytest.mark.parametrize("region", ["CA", "AU", "NZ", "JP", "CN", "KR", "IN"])
def test_other_regions_state_that_no_dedicated_refinement_exists(region):
    wf = resolve_workflow(region, "industrial_organic")
    assert not {"water_sediment", "pearl", "us_models"} & set(wf["modules"])
    refine = stage(wf, USE_RELEASE, "refine")
    assert refine["status"] == "not_built" and refine["module"] is None
    assert REGIONS[region]["label"] in refine["note"]


# ---------- Japan, China, South Korea, India: named regime, honestly unmapped method, never EU/UK wording ----------
def test_all_eleven_regions_are_present():
    assert set(REGIONS) == {"EU", "UK", "CH", "US", "CA", "AU", "NZ", "JP", "CN", "KR", "IN"}


@pytest.mark.parametrize("region, needle", [
    ("JP", "CSCL"), ("CN", "China REACH"), ("KR", "K-REACH"), ("IN", "MSIHC"),
])
def test_jp_cn_kr_in_name_their_own_regime_and_mark_the_method_partial(region, needle):
    route = stage(resolve_workflow(region, "industrial_organic"), USE_RELEASE, "route")
    assert needle in route["detail"]
    assert route["status"] == "partial"  # regime named, quantitative method not yet mapped -- never claimed available
    for other in ("EU REACH", "UK REACH"):
        assert other not in route["detail"]


def test_japan_pesticide_route_names_its_own_pec_criterion():
    route = stage(resolve_workflow("JP", "pesticide"), USE_RELEASE, "route")
    assert "Predicted Environmental Concentration" in route["detail"] and "Agricultural Chemicals" in route["detail"]


# ---------- Japan/China industrial methods, upgraded from "agency only" in the 2026-09-22 follow-up ----------
def test_japan_industrial_route_names_the_confirmed_cscl_structure_but_stays_partial():
    route = stage(resolve_workflow("JP", "industrial_organic"), USE_RELEASE, "route")
    assert route["status"] == "partial"  # real structure confirmed, but no calculable current method is offered
    for term in ("Hazard Class", "Exposure Class", "DNEL/PNEC", "priority matrix"):
        assert term in route["detail"], term
    assert "2022" in route["detail"]  # honestly flags that a later revision exists and was not read


def test_china_industrial_route_names_the_confirmed_2019_guideline_but_stays_partial():
    route = stage(resolve_workflow("CN", "industrial_organic"), USE_RELEASE, "route")
    assert route["status"] == "partial"
    assert "2019" in route["detail"] and "PEC/PNEC" in route["detail"]
    assert "uncertainty-factor values were not confirmed" in route["detail"]


def test_korea_and_india_industrial_routes_stay_agency_only_after_the_follow_up_search():
    # Unlike Japan and China, the follow-up search found nothing India- or Korea-specific for the industrial
    # pathway, so these two must NOT have picked up a real-structure upgrade.
    kr = stage(resolve_workflow("KR", "industrial_organic"), USE_RELEASE, "route")
    ind = stage(resolve_workflow("IN", "industrial_organic"), USE_RELEASE, "route")
    assert kr["programme_key"] == "KR_KREACH_NOT_MAPPED" and ind["programme_key"] == "IN_MSIHC_NOT_MAPPED"


def test_korea_pesticide_route_names_the_confirmed_registering_authority():
    # 2026-09-22 follow-up: the Rural Development Administration / MAFRA attribution was confirmed after the
    # initial JP/CN/KR/IN research session, which had left it as an open question.
    route = stage(resolve_workflow("KR", "pesticide"), USE_RELEASE, "route")
    assert "Rural Development Administration" in route["detail"] and "Agriculture" in route["detail"]


def test_india_cmsr_draft_is_not_claimed_as_an_enacted_regime():
    route = stage(resolve_workflow("IN", "industrial_organic"), USE_RELEASE, "route")
    assert "draft" in route["detail"].lower() and "MSIHC" in route["detail"]


# ---------- pharma pathways added in the 2026-09-22 follow-up research ----------
def test_china_pharma_route_names_discharge_standards_not_a_pec_pnec_claim():
    route = stage(resolve_workflow("CN", "human_pharmaceutical"), USE_RELEASE, "route")
    assert "discharge standard" in route["detail"].lower() and "GB 21" in route["detail"]
    assert "No pre-market environmental risk assessment guideline" in route["detail"]


def test_korea_pharma_route_names_a_real_but_unmapped_mfds_requirement():
    route = stage(resolve_workflow("KR", "human_pharmaceutical"), USE_RELEASE, "route")
    assert "MFDS" in route["detail"] and "environmental-risk information" in route["detail"]


def test_india_pharma_route_states_a_confirmed_no_era_requirement():
    route = stage(resolve_workflow("IN", "human_pharmaceutical"), USE_RELEASE, "route")
    assert "no environmental risk assessment requirement" in route["detail"].lower()
    assert "confirmed, not a research gap" in route["detail"]


def test_korea_and_india_pharma_findings_are_not_extended_to_veterinary():
    # MFDS and CDSCO are each that country's human-medicines regulator; veterinary medicines were not researched,
    # so the veterinary group must fall through to the generic (industrial-style) "not yet mapped" branch instead
    # of silently inheriting a human-medicines-specific finding.
    kr_vet = stage(resolve_workflow("KR", "veterinary_pharmaceutical"), USE_RELEASE, "route")
    in_vet = stage(resolve_workflow("IN", "veterinary_pharmaceutical"), USE_RELEASE, "route")
    assert kr_vet["detail"] == stage(resolve_workflow("KR", "industrial_organic"), USE_RELEASE, "route")["detail"]
    assert in_vet["detail"] == stage(resolve_workflow("IN", "industrial_organic"), USE_RELEASE, "route")["detail"]


def test_china_pharma_finding_is_kept_for_veterinary_with_its_own_caveat_documented():
    # Unlike Korea/India, China's finding is a manufacturing-category discharge standard, not a human/veterinary
    # regulatory-review split, so it is deliberately kept for both groups (see the code comment for the caveat).
    human = stage(resolve_workflow("CN", "human_pharmaceutical"), USE_RELEASE, "route")
    vet = stage(resolve_workflow("CN", "veterinary_pharmaceutical"), USE_RELEASE, "route")
    assert human["detail"] == vet["detail"]


@pytest.mark.parametrize("region, receptors", [("JP", {"human"}), ("KR", {"human"}), ("CN", {"human", "ecological"})])
def test_jp_cn_kr_site_methods_are_named_only_where_the_research_confirmed_them(region, receptors):
    methods = _site_methods(region)
    named = {m["receptor"] for m in methods if m["named"]}
    assert named == receptors


def test_india_is_the_only_new_region_with_all_four_receptors_named():
    # The 2025 Contaminated Sites Rules' own scope language explicitly names soil, groundwater, surface water and
    # sediment together -- broader than Japan, China or Korea's sources, which is a real difference, not a slip.
    methods = _site_methods("IN")
    assert {m["receptor"] for m in methods if m["named"]} == {"human", "ecological", "groundwater", "surface_water"}


def test_regulatory_route_text_comes_from_the_registry_programme():
    assert "AICIS" in stage(resolve_workflow("AU", "industrial_organic"), USE_RELEASE, "route")["detail"]
    assert "HSNO" in stage(resolve_workflow("NZ", "pesticide"), USE_RELEASE, "route")["detail"]
    assert "Canadian" in stage(resolve_workflow("CA", "human_pharmaceutical"), USE_RELEASE, "route")["detail"]


def test_partially_mapped_routes_are_marked_partial_not_available():
    assert stage(resolve_workflow("CA", "human_pharmaceutical"), USE_RELEASE, "route")["status"] == "partial"
    assert stage(resolve_workflow("EU", "industrial_organic"), USE_RELEASE, "route")["status"] == "available"


# ---------- site track methods mirror the site model's own routes ----------
def _site_methods(region, group="legacy_pop_organic"):
    wf = resolve_workflow(region, group)
    return next(t for t in wf["tracks"] if t["id"] == SITE)["methods"]


@pytest.mark.parametrize("region", ["EU", "UK", "CH", "US"])
def test_site_methods_mirror_external_routes_and_mark_gaps_not_established(region):
    methods = _site_methods(region)
    assert len(methods) == 4  # one jurisdiction (this region's own) x four receptor classes
    assert all(m["jurisdiction"] == REGIONS[region]["jurisdictions"][0] for m in methods)
    for m in methods:
        found = EXTERNAL_ROUTES.get((m["jurisdiction"], m["receptor"]))
        assert m["named"] is bool(found)
        assert m["route"] == (found["route"] if found else NOT_ESTABLISHED)


def test_switzerland_has_no_named_site_method_yet():
    # Splitting UK and Switzerland out of the combined EU tab surfaces this honestly: EXTERNAL_ROUTES has no CH
    # entries at all, so every CH receptor stays "regulatory applicability not established", never borrowed from EU.
    assert all(not m["named"] for m in _site_methods("CH"))


def test_uk_and_eu_site_methods_are_not_identical():
    # UK and EU are genuinely different regimes (e.g. UK has no confirmed ecological route; EU does) -- confirms
    # the split didn't just alias one region's methods onto the other's.
    assert _site_methods("UK") != [dict(m, jurisdiction="EU") for m in _site_methods("EU")]


def test_site_track_never_claims_a_calculation():
    site = stage(resolve_workflow("US", "metal_inorganic"), SITE, "site_model")
    assert "No exposure or risk is calculated" in site["detail"]


# ---------- input handling and API ----------
def test_unknown_region_or_group_is_rejected():
    with pytest.raises(WorkflowError, match="Unknown region"):
        resolve_workflow("XX", "pesticide")
    with pytest.raises(WorkflowError, match="Unknown chemical group"):
        resolve_workflow("US", "not_a_group")


def test_reference_lists_every_group_once_with_a_label():
    ref = reference()
    keys = [g["key"] for f in ref["families"] for g in f["groups"]]
    assert sorted(keys) == sorted(CONTAMINANT_GROUPS)
    assert [r["key"] for r in ref["regions"]] == list(REGIONS)
    assert "product decision" in ref["note"]


def test_api_endpoints():
    ref = client.get("/api/workflow/reference")
    assert ref.status_code == 200 and len(ref.json()["families"]) == len(FAMILIES)
    ok = client.get("/api/workflow", params={"region": "AU", "group": "metal_inorganic"})
    assert ok.status_code == 200 and ok.json()["default_track"] == SITE
    assert client.get("/api/workflow", params={"region": "AU", "group": "nope"}).status_code == 422
    assert client.get("/api/workflow", params={"region": "ZZ", "group": "pesticide"}).status_code == 422
    assert client.get("/api/workflow", params={"region": "AU"}).status_code == 422
