"""Sourced plausibility prompts: criteria, boundaries, fail-closed input handling and site-model integration."""

from __future__ import annotations

import math

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.conceptual_site_model import (
    ConceptualSiteModel, ConceptualSiteModelError, Contaminant, PathwayLink, Source, assess, model_from_dict,
)
from app.services.pathway_plausibility import (
    INCONCLUSIVE, MISSING, QUESTIONS, RULES, SUPPORTS, UNSOURCED_GAPS, PropertyError,
    evaluate_path, evaluate_step, evaluate_step_all, properties_from_dict, rules_metadata,
)


def props(**values):
    return properties_from_dict({k: {"value": v, "source": "datasheet X"} for k, v in values.items()})


VOL = {"pathway": "volatilisation", "from": "soil", "to": "air"}
SOIL_GAS_INH = {"pathway": "inhalation", "from": "soil_gas", "to": "residents"}
FOOD = {"pathway": "food_chain_transfer", "from": "biota", "to": "residents"}


def outcome(name, group, p, step):
    return evaluate_step(name, group, p, step)["outcome"]


# ---------- properties input ----------
def test_properties_are_parsed_with_their_sources():
    p = properties_from_dict({"log_kow": {"value": 6.5, "source": "PubChem"}})
    assert p.get("log_kow") == 6.5 and p.source("log_kow") == "PubChem"
    assert p.as_dict() == {"log_kow": {"value": 6.5, "source": "PubChem"}}
    assert properties_from_dict(None) is None and properties_from_dict({}) is None


@pytest.mark.parametrize("data, fragment", [
    ({"boiling_point": {"value": 1, "source": "x"}}, "Unknown property"),
    ({"log_kow": {"value": 5}}, "needs a source"),
    ({"log_kow": {"value": 5, "source": "  "}}, "needs a source"),
    ({"log_kow": {"source": "x"}}, "expected"),
    ({"log_kow": 5}, "expected"),
    ({"vapour_pressure_mm_hg": {"value": 0, "source": "x"}}, "greater than zero"),
    ({"henry_law_constant_atm_m3_mol": {"value": -1e-5, "source": "x"}}, "greater than zero"),
    ({"bcf_or_baf_aquatic": {"value": -3, "source": "x"}}, "greater than zero"),
    ({"log_kow": {"value": math.nan, "source": "x"}}, "finite"),
    ({"log_kow": {"value": math.inf, "source": "x"}}, "finite"),
    ({"log_kow": {"value": True, "source": "x"}}, "finite"),
    ({"log_kow": {"value": "6.5", "source": "x"}}, "finite"),
])
def test_invalid_properties_are_rejected_never_defaulted(data, fragment):
    with pytest.raises(PropertyError, match=fragment):
        properties_from_dict(data)


def test_log_kow_may_be_negative_or_zero():
    assert properties_from_dict({"log_kow": {"value": -1.2, "source": "x"}}).get("log_kow") == -1.2


# ---------- V1: EPA volatility definition (strict "greater than", either property) ----------
def test_volatile_when_either_property_exceeds_the_epa_value():
    assert outcome("benzene", "hydrocarbon_solvent", props(vapour_pressure_mm_hg=95, henry_law_constant_atm_m3_mol=5.5e-3), VOL) == SUPPORTS
    assert outcome("x", "industrial_organic", props(vapour_pressure_mm_hg=5), VOL) == SUPPORTS
    assert outcome("x", "industrial_organic", props(henry_law_constant_atm_m3_mol=2e-5), VOL) == SUPPORTS


def test_boundary_values_are_not_volatile_because_the_criterion_is_strictly_greater_than():
    both = props(vapour_pressure_mm_hg=1, henry_law_constant_atm_m3_mol=1e-5)
    assert outcome("x", "industrial_organic", both, VOL) == QUESTIONS


def test_below_both_values_questions_relevance_but_carries_the_epa_caveats():
    result = evaluate_step("x", "pah", props(vapour_pressure_mm_hg=1e-6, henry_law_constant_atm_m3_mol=1e-8), VOL)
    assert result["outcome"] == QUESTIONS
    for word in ("naphthalene", "PCB congeners", "elemental mercury", "review it, do not exclude it"):
        assert word in result["message"]
    assert len(result["basis"]) == 2 and "datasheet X" in result["basis"][0]


def test_one_property_below_is_inconclusive_because_the_definition_is_either_property():
    result = evaluate_step("x", "pah", props(vapour_pressure_mm_hg=1e-6), VOL)
    assert result["outcome"] == INCONCLUSIVE and "Henry's law constant is needed" in result["message"]
    result = evaluate_step("x", "pah", props(henry_law_constant_atm_m3_mol=1e-9), VOL)
    assert result["outcome"] == INCONCLUSIVE and "vapour pressure is needed" in result["message"]


def test_no_properties_reports_missing_not_a_default():
    assert outcome("x", "industrial_organic", None, VOL) == MISSING


def test_metal_message_reflects_only_what_the_epa_guide_actually_says():
    message = evaluate_step("zinc", "metal_inorganic", None, VOL)["message"]
    assert "only elemental mercury" in message and "no rule for other metals" in message
    mercury = evaluate_step("mercury", "metal_inorganic", None, VOL)["message"]
    assert "DNAPL" in mercury and "confirm the form" in mercury


def test_a_supplied_property_lets_the_criterion_apply_to_a_metal_too():
    assert outcome("mercury", "metal_inorganic", props(henry_law_constant_atm_m3_mol=1.1e-2), VOL) == SUPPORTS


def test_volatility_applies_to_volatilisation_and_soil_gas_inhalation_only():
    p = props(vapour_pressure_mm_hg=10)
    assert evaluate_step("x", "pah", p, SOIL_GAS_INH)["rule"] == "V1"
    for step in ({"pathway": "inhalation", "from": "air", "to": "residents"},
                 {"pathway": "inhalation", "from": "soil", "to": "workers"},
                 {"pathway": "ingestion", "from": "soil", "to": "residents"},
                 {"pathway": "plant_uptake", "from": "soil", "to": "vegetation"}):
        assert evaluate_step("x", "pah", p, step) is None


# ---------- B1: Stockholm Annex D bioaccumulation screening ----------
def test_bcf_above_5000_supports_and_exactly_5000_does_not():
    assert outcome("x", "legacy_pop_organic", props(bcf_or_baf_aquatic=5001), FOOD) == SUPPORTS
    assert outcome("x", "legacy_pop_organic", props(bcf_or_baf_aquatic=5000), FOOD) == INCONCLUSIVE


def test_bcf_takes_precedence_over_log_kow_as_the_criterion_states():
    result = evaluate_step("x", "legacy_pop_organic", props(bcf_or_baf_aquatic=100, log_kow=7), FOOD)
    assert result["outcome"] == INCONCLUSIVE and "BCF/BAF 100" in result["basis"][0]


def test_log_kow_is_used_only_in_the_absence_of_bcf():
    supports = evaluate_step("x", "pah", props(log_kow=5.1), FOOD)
    assert supports["outcome"] == SUPPORTS and "no BCF/BAF was supplied" in supports["basis"][0]
    assert outcome("x", "pah", props(log_kow=5.0), FOOD) == INCONCLUSIVE


def test_below_the_value_never_excludes_food_chain_transfer():
    result = evaluate_step("x", "pah", props(log_kow=2), FOOD)
    assert "does not exclude food-chain transfer" in result["message"]
    assert result["outcome"] != QUESTIONS   # bioaccumulation evidence can support relevance but never question it


def test_missing_bioaccumulation_evidence_is_reported():
    assert outcome("x", "pah", None, FOOD) == MISSING


def test_bioaccumulation_criteria_are_not_applied_to_metals():
    result = evaluate_step("lead", "metal_inorganic", props(log_kow=6, bcf_or_baf_aquatic=99999), FOOD)
    assert result["outcome"] == INCONCLUSIVE and "Framework for Metals Risk Assessment" in result["message"]


# ---------- rule provenance ----------
def test_every_rule_carries_source_url_page_quote_and_retrieval_date():
    for rule_id, rule in RULES.items():
        assert rule["url"].startswith("http"), rule_id
        assert rule["retrieved"] == "2026-09-20" and rule["caveats"] and rule["quotes"]
        assert all((q.get("page", 0) > 0 or q.get("locator")) and len(q["text"]) > 40 for q in rule["quotes"]), rule_id
        assert rule["regimes"], rule_id


def test_encoded_thresholds_match_the_quoted_source_text():
    v1 = " ".join(q["text"] for q in RULES["V1"]["quotes"])
    assert "greater than 1 millimeter of mercury" in v1 and "greater than 10-5 atmosphere-meter cubed per mole" in v1
    b1 = RULES["B1"]["quotes"][0]["text"]
    assert "greater than 5,000" in b1 and "log Kow is greater than 5" in b1
    m1 = " ".join(q["text"] for q in RULES["M1"]["quotes"])
    assert "log Koc is less than 3" in m1 and "log Koc is less than 2" in m1
    assert "lowest log Koc value for pH between 4 and 9" in m1 and "weight of evidence" in m1


def test_unsourced_gaps_are_declared():
    meta = rules_metadata()
    assert set(meta["rules"]) == {"V1", "B1", "B2", "M1"}
    assert not any("could not be retrieved" in g for g in UNSOURCED_GAPS)     # the EU mobility text was retrieved (M1)
    assert any("plant uptake" in g.lower() for g in meta["not_encoded"])


# ---------- integration with the site model ----------
def _site(properties=None, group="hydrocarbon_solvent", name="benzene"):
    contaminant = Contaminant(name, group, None, properties)
    return ConceptualSiteModel(
        sources=(Source("S1", "spill", ("groundwater",), (contaminant,)),),
        receptors=("residents",),
        links=(PathwayLink("volatilisation", "groundwater", "air"), PathwayLink("inhalation", "air", "residents"),
               PathwayLink("volatilisation", "groundwater", "soil_gas"), PathwayLink("inhalation", "soil_gas", "residents")),
    )


def test_linkages_carry_plausibility_prompts_and_are_never_removed():
    without = assess(_site(), "US")
    with_props = assess(_site(props(vapour_pressure_mm_hg=1e-7, henry_law_constant_atm_m3_mol=1e-9)), "US")
    assert len(without["linkages"]) == len(with_props["linkages"]) > 0  # a QUESTIONS prompt never deletes a linkage
    via_soil_gas = [x for x in with_props["linkages"] if any(s["from"] == "soil_gas" for s in x["path"])]
    assert via_soil_gas and all(x["plausibility"][0]["outcome"] == QUESTIONS for x in via_soil_gas)
    assert with_props["summary"]["plausibility_questioned"] >= 1
    assert without["summary"]["plausibility_property_missing"] >= 1
    assert without["summary"]["plausibility_questioned"] == 0


def test_radionuclides_and_mixtures_get_no_plausibility_prompts():
    result = assess(_site(group="radionuclide", name="radon"), "UK")
    assert all(x["plausibility"] == [] for x in result["linkages"])


def test_assessment_publishes_the_rules_it_used_and_an_honest_disclaimer():
    result = assess(_site(), "UK")
    assert set(result["plausibility_rules"]["rules"]) == {"V1", "B1", "B2", "M1"}
    assert "they never remove a linkage" in result["disclaimer"]
    assert "Conceptual mapping only" in result["disclaimer"]


_PAYLOAD = {
    "jurisdiction": "US",
    "sources": [{"id": "S1", "kind": "spill", "release_media": ["groundwater"], "contaminants": [
        {"name": "benzene", "contaminant_group": "hydrocarbon_solvent",
         "properties": {"vapour_pressure_mm_hg": {"value": 95, "source": "datasheet X"}}}]}],
    "receptors": ["residents"],
    "links": [{"pathway": "volatilisation", "from": "groundwater", "to": "soil_gas"},
              {"pathway": "inhalation", "from": "soil_gas", "to": "residents"}],
}


def test_model_from_dict_reads_properties_and_rejects_bad_ones():
    model = model_from_dict(_PAYLOAD)
    assert model.sources[0].contaminants[0].properties.get("vapour_pressure_mm_hg") == 95
    bad = {**_PAYLOAD, "sources": [{**_PAYLOAD["sources"][0], "contaminants": [
        {"name": "benzene", "contaminant_group": "hydrocarbon_solvent",
         "properties": {"vapour_pressure_mm_hg": {"value": 95}}}]}]}
    with pytest.raises(ConceptualSiteModelError, match="needs a source"):
        model_from_dict(bad)


def test_api_returns_plausibility_and_rejects_unsourced_values():
    with TestClient(app) as client:
        ok = client.post("/api/conceptual-site-model/assess", json=_PAYLOAD)
        assert ok.status_code == 200
        body = ok.json()
        outcomes = {r["outcome"] for x in body["linkages"] for r in x["plausibility"]}
        assert outcomes == {SUPPORTS}            # vapour pressure 95 mm Hg is above the EPA value of 1
        assert body["plausibility_rules"]["rules"]["V1"]["url"].startswith("https://www.epa.gov/")
        unsourced = {**_PAYLOAD, "sources": [{**_PAYLOAD["sources"][0], "contaminants": [
            {"name": "benzene", "contaminant_group": "hydrocarbon_solvent",
             "properties": {"vapour_pressure_mm_hg": {"value": 95}}}]}]}
        rejected = client.post("/api/conceptual-site-model/assess", json=unsourced)
        assert rejected.status_code == 422 and "needs a source" in rejected.json()["detail"]
        assert client.get("/api/conceptual-site-model/reference").json()["property_specs"]["log_kow"]


# ---------- M1: EU CLP mobility (log Koc < 3 mobile, < 2 very mobile) ----------
SOIL_GW = {"pathway": "soil_to_groundwater", "from": "soil", "to": "groundwater"}
GW_SW = {"pathway": "groundwater_to_surface_water", "from": "groundwater", "to": "surface_water"}


def test_log_koc_below_2_is_very_mobile_and_below_3_is_mobile():
    very = evaluate_step("x", "industrial_organic", props(log_koc=1.5), SOIL_GW)
    assert very["outcome"] == SUPPORTS and "very mobile substance (log Koc < 2)" in very["message"]
    mobile = evaluate_step("x", "industrial_organic", props(log_koc=2.5), SOIL_GW)
    assert mobile["outcome"] == SUPPORTS and "mobile substance (log Koc < 3)" in mobile["message"]


def test_mobility_boundaries_are_strict_less_than():
    assert outcome("x", "industrial_organic", props(log_koc=2.0), SOIL_GW) == SUPPORTS   # 2.0 is not < 2, but is < 3
    assert "log Koc < 3" in evaluate_step("x", "industrial_organic", props(log_koc=2.0), SOIL_GW)["message"]
    assert outcome("x", "industrial_organic", props(log_koc=3.0), SOIL_GW) == INCONCLUSIVE


def test_high_log_koc_never_excludes_leaching_and_carries_the_weight_of_evidence_note():
    result = evaluate_step("x", "pah", props(log_koc=4.5), GW_SW)
    assert result["outcome"] == INCONCLUSIVE and result["outcome"] != QUESTIONS
    assert "does not exclude leaching" in result["message"] and "weight of evidence" in result["message"]


def test_ionisable_caveat_is_attached_to_supporting_results():
    assert "lowest log Koc for pH 4 to 9" in evaluate_step("x", "pah", props(log_koc=1), SOIL_GW)["message"]


def test_mobility_missing_and_metals():
    assert outcome("x", "pah", None, SOIL_GW) == MISSING
    metal = evaluate_step("lead", "metal_inorganic", props(log_koc=1), SOIL_GW)
    assert metal["outcome"] == INCONCLUSIVE and "organic carbon-water partition coefficient" in metal["message"]


def test_mobility_applies_only_to_the_two_transport_pathways():
    for step in (SOIL_GW, GW_SW):
        assert evaluate_step("x", "pah", props(log_koc=1), step)["rule"] == "M1"
    for step in ({"pathway": "runoff", "from": "soil", "to": "surface_water"},
                 {"pathway": "erosion", "from": "soil", "to": "sediment"},
                 {"pathway": "dermal_contact", "from": "soil", "to": "workers"}):
        assert evaluate_step("x", "pah", props(log_koc=1), step) is None


def test_m1_rule_records_the_official_journal_citation_and_limits():
    rule = RULES["M1"]
    assert "2023/707" in rule["source"] and "L 93" in rule["source"] and "eur-lex.europa.eu" in rule["url"]
    assert any("hazard-classification criterion" in c for c in rule["caveats"])
    assert any("lowest log Koc" in c for c in rule["caveats"])
    assert any("unit" in c for c in rule["caveats"])


# ---------- UK sources: B2 (UK REACH Annex XIII), UK mobility framing, UK volatility finding ----------
def all_rules(name, group, p, step, jurisdiction=None):
    return {r["rule"]: r for r in evaluate_step_all(name, group, p, step, jurisdiction)}


def test_food_chain_step_yields_both_the_treaty_and_the_uk_reach_criterion():
    results = all_rules("x", "legacy_pop_organic", props(bcf_or_baf_aquatic=3000, log_kow=6), FOOD)
    assert set(results) == {"B1", "B2"}
    assert results["B1"]["outcome"] == INCONCLUSIVE      # 3,000 is below the Stockholm 5,000
    assert results["B2"]["outcome"] == SUPPORTS          # but above the UK REACH B value of 2,000
    assert "bioaccumulative substance (B: BCF > 2,000)" in results["B2"]["message"]


def test_uk_reach_b_and_vb_boundaries_are_strict():
    for value, expected, fragment in ((2000, INCONCLUSIVE, "BCF <= 2,000"), (2001, SUPPORTS, "(B: BCF > 2,000)"),
                                      (5000, SUPPORTS, "(B: BCF > 2,000)"), (5001, SUPPORTS, "(vB: BCF > 5,000)")):
        result = all_rules("x", "pah", props(bcf_or_baf_aquatic=value), FOOD)["B2"]
        assert result["outcome"] == expected and fragment in result["message"], value


def test_uk_reach_criterion_needs_a_bcf_and_is_not_applied_to_inorganic_metals():
    assert all_rules("x", "pah", props(log_kow=7), FOOD)["B2"]["outcome"] == MISSING   # log Kow is not an alternative here
    metal = all_rules("lead", "metal_inorganic", props(bcf_or_baf_aquatic=99999), FOOD)["B2"]
    assert metal["outcome"] == INCONCLUSIVE and "organic substances, including organo-metals" in metal["message"]


def test_uk_reach_rule_quotes_the_legislation_and_states_its_scope():
    rule = RULES["B2"]
    text = " ".join(q["text"] for q in rule["quotes"])
    assert "higher than 2 000" in text and "higher than 5 000" in text and "organic substances, including organo-metals" in text
    assert rule["url"] == "https://www.legislation.gov.uk/eur/2006/1907/annex/XIII"


def test_each_result_says_whether_the_criterion_is_formal_in_the_assessed_jurisdiction():
    p = props(vapour_pressure_mm_hg=10, log_koc=1, bcf_or_baf_aquatic=9000)
    vol = evaluate_step("x", "pah", p, VOL, "US")
    assert vol["in_regime"] is True and "US EPA" in vol["regime_note"]
    uk_vol = evaluate_step("x", "pah", p, VOL, "UK")
    assert uk_vol["in_regime"] is True and "No UK volatility criterion was found" in uk_vol["regime_note"]
    eu_vol = evaluate_step("x", "pah", p, VOL, "EU")
    assert eu_vol["in_regime"] is False and eu_vol["regime_note"].startswith("Reference criterion from another regime")
    assert evaluate_step("x", "pah", p, SOIL_GW, "EU")["in_regime"] is True
    assert "interim, non-statutory" in evaluate_step("x", "pah", p, SOIL_GW, "UK")["regime_note"].lower()
    assert evaluate_step("x", "pah", p, SOIL_GW, "US")["in_regime"] is False
    assert all_rules("x", "pah", p, FOOD, "US")["B1"]["in_regime"] is True      # treaty criterion applies everywhere
    assert all_rules("x", "pah", p, FOOD, "US")["B2"]["in_regime"] is False     # UK REACH criterion is a UK reference elsewhere
    assert all_rules("x", "pah", p, FOOD, "UK")["B2"]["in_regime"] is True


def test_the_uk_volatility_finding_is_recorded_as_corroboration_not_a_uk_criterion():
    quotes = RULES["V1"]["quotes"]
    uk = next(q for q in quotes if "Environment Agency" in q.get("document", ""))
    assert "several regulatory agencies have defined volatile chemicals" in uk["text"]
    assert "greater than 1 Pa m3 mol-1" in uk["text"] and uk["url"].endswith("scho0508bnqw-e-e.pdf")
    assert any("No UK-specific volatility criterion" in g for g in UNSOURCED_GAPS)


def test_pfas_get_the_defra_koc_caution_on_mobility_results():
    for koc in (1.0, 4.5):
        message = evaluate_step("PFOA", "pfas_persistent_mobile", props(log_koc=koc), SOIL_GW)["message"]
        assert "too simplistic to determine the potential mobility of PFAS" in message
        assert "a high value does not show low mobility" in message
    plain = evaluate_step("x", "pah", props(log_koc=1.0), SOIL_GW)["message"]
    assert "PFAS" not in plain


def test_uk_mobility_position_is_recorded_with_its_limits():
    rule = RULES["M1"]
    text = " ".join(q["text"] for q in rule["quotes"])
    assert "Definitive criteria are not being formally adopted in UK REACH" in text
    assert "Koc is too simplistic to determine the potential mobility of PFAS" in text
    assert any("not established from primary text" in c for c in rule["caveats"])
    assert any("GB CLP" in g and "not established" in g for g in UNSOURCED_GAPS)


def test_site_model_results_carry_regime_information():
    site = _site(props(vapour_pressure_mm_hg=10))
    uk = assess(site, "UK")
    prompt = next(r for x in uk["linkages"] for r in x["plausibility"])
    assert prompt["in_regime"] is True and "regime_note" in prompt
    us = assess(site, "US")
    assert next(r for x in us["linkages"] for r in x["plausibility"])["in_regime"] is True
