"""FIFRA companion-model routing: PWC alone is not a complete pesticide
ecological assessment. build_assessment_plan must conditionally route
AgDRIFT/TerrPlant/T-REX/BeeREX from application_method/use_site_category/
bee_attractive, not show them indiscriminately for every pesticide use --
and must not disturb the existing, tested dual-jurisdiction PRZM selection
(EU FOCUS *and* US FIFRA both legitimately select PRZM for the same
agricultural_spray/pesticide/tier-3 inputs -- see
test_jurisdiction_separation.py::test_same_agricultural_scenario_routes_to_focus_or_fifra).
"""
from pathlib import Path

from app.services.registry import build_assessment_plan

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


def applicable_keys(plan):
    return {model["key"] for model in plan["models"] if model["applicable"]}


def assessment_plan(jurisdiction, scenario, group, tier=2, **extra):
    return build_assessment_plan({
        "jurisdiction": jurisdiction,
        "contaminant_group": group,
        "scenario": scenario,
        "tier": tier,
        **extra,
    })


def test_aerial_bee_attractive_spray_routes_all_four_companion_models():
    plan = assessment_plan(
        "US", "agricultural_spray", "pesticide", tier=2,
        application_method="aerial", use_site_category="field_crop", bee_attractive=True,
    )
    keys = applicable_keys(plan)
    assert {"PWC", "AGDRIFT", "TERRPLANT", "TREX", "BEEREX"}.issubset(keys)
    assert plan["regulatory_programme"]["key"] == "US_FIFRA"


def test_soil_incorporated_non_bee_attractive_drops_drift_and_bee_models():
    plan = assessment_plan(
        "US", "agricultural_spray", "pesticide", tier=2,
        application_method="soil_incorporated", use_site_category="field_crop", bee_attractive=False,
    )
    keys = applicable_keys(plan)
    assert {"PWC", "TERRPLANT", "TREX"}.issubset(keys)
    assert "AGDRIFT" not in keys
    assert "BEEREX" not in keys


def test_enclosed_greenhouse_drops_terrestrial_models_too():
    plan = assessment_plan(
        "US", "agricultural_spray", "pesticide", tier=2,
        application_method="soil_incorporated", use_site_category="enclosed_greenhouse", bee_attractive=False,
    )
    keys = applicable_keys(plan)
    assert "PWC" in keys
    assert "TERRPLANT" not in keys
    assert "TREX" not in keys


def test_missing_trigger_fields_default_to_the_conservative_no_drift_no_bee_state():
    # No application_method/use_site_category/bee_attractive supplied at all --
    # must not fabricate AgDRIFT/BeeREX applicability from nothing.
    plan = assessment_plan("US", "agricultural_spray", "pesticide", tier=2)
    keys = applicable_keys(plan)
    assert "AGDRIFT" not in keys
    assert "BEEREX" not in keys
    assert {"PWC", "TERRPLANT", "TREX"}.issubset(keys)


def test_pwc_groundwater_section_is_called_out_as_mandatory():
    plan = assessment_plan("US", "agricultural_spray", "pesticide", tier=2)
    assert any("groundwater" in item.lower() and "mandatory" in item.lower() for item in plan["required_inputs"])


def test_eu_focus_przm_dual_selection_is_undisturbed_by_the_new_us_routing():
    # Regression guard for the exact scenario this merge could have broken:
    # the EU FOCUS branch's own PRZM selection (registry.py, tier>=3 pesticide
    # agricultural_spray/soil_incorporation) must be completely unaffected by
    # the new US-side conditional routing added alongside it.
    eu = assessment_plan("EU", "agricultural_spray", "pesticide", tier=3)
    eu_keys = applicable_keys(eu)
    assert {"SPIN", "PEARL", "PELMO", "MACRO", "SWASH", "TOXSWA", "PRZM"}.issubset(eu_keys)
    assert eu["regulatory_programme"]["key"] == "EU_PPP_FOCUS"
    # None of the new US-only ecological companion models should ever appear for EU.
    assert not ({"AGDRIFT", "TERRPLANT", "TREX", "BEEREX"} & eu_keys)


def test_pesticide_only_execution_gate_covers_the_new_models():
    # main.py's pesticide-only 422 gate (previously {"PWC","TOXSWA"}) must now
    # also cover the four new models -- but NOT PRZM, whose groups legitimately
    # span pesticide/biocide/industrial_organic/emerging_contaminant for its
    # dual EU FOCUS / US FIFRA use.
    main_py = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '{"PWC", "TOXSWA", "AGDRIFT", "TERRPLANT", "TREX", "BEEREX"}' in main_py


def test_pesticide_trigger_controls_are_wired_into_the_guided_panel():
    assert 'id="fifra-triggers"' in HTML
    assert "application_method" in JS and "use_site_category" in JS and "bee_attractive" in JS


def test_new_models_are_not_added_to_the_local_execution_bridge():
    # None of PRZM/AGDRIFT/TERRPLANT/TREX/BEEREX have a real configured
    # executable -- they must stay on the manual-handoff path, not be added to
    # EPA_EXECUTION_MODEL_KEYS (which would falsely claim local-execution
    # readiness for a model with no config field, no allowlist entry, and no
    # verified executable).
    execution_py = (ROOT / "app" / "services" / "external_execution.py").read_text(encoding="utf-8")
    assert 'EPA_EXECUTION_MODEL_KEYS = frozenset({"PWC", "CHEMSTEER", "CEM", "EFAST"})' in execution_py
