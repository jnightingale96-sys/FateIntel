"""Behavioral guarantees for EU/US separation in the guided assessment.

An exposure scenario is jurisdiction-neutral. Selecting EU or US must keep
that scenario and replace only the regulatory programme, applicable models and
workflow provenance. Native process screens may be shared where their model
registry says they are applicable, but official EU and US tools must never
cross jurisdictions.
"""
from pathlib import Path

from app.services.registry import build_assessment_plan

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
SW = (ROOT / "app" / "static" / "sw.js").read_text(encoding="utf-8")

EU_ONLY_KEYS = {"PEARL", "TOXSWA", "SPIN", "PELMO", "MACRO", "SWASH", "EPIE"}
US_ONLY_KEYS = {
    "PWC", "EXAMS", "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN",
    "CHEMSTEER", "CEM", "EFAST",
}


def applicable_keys(plan):
    return {model["key"] for model in plan["models"] if model["applicable"]}


def assessment_plan(jurisdiction, scenario, group, tier=2):
    return build_assessment_plan({
        "jurisdiction": jurisdiction,
        "contaminant_group": group,
        "scenario": scenario,
        "tier": tier,
    })


def test_official_models_never_cross_jurisdictions():
    cases = [
        ("agricultural_spray", "pesticide"),
        ("groundwater_leaching", "pesticide"),
        ("wastewater_irrigation", "pesticide"),
        ("household_use", "detergent_cleaner"),
        ("product_disposal", "industrial_organic"),
        ("industrial_effluent", "industrial_organic"),
    ]
    for scenario, group in cases:
        us = applicable_keys(assessment_plan("US", scenario, group, tier=3))
        eu = applicable_keys(assessment_plan("EU", scenario, group, tier=3))
        assert not (us & EU_ONLY_KEYS), f"EU-only model leaked into US/{scenario}"
        assert not (eu & US_ONLY_KEYS), f"US-only model leaked into EU/{scenario}"


def test_same_agricultural_scenario_routes_to_focus_or_fifra():
    eu = applicable_keys(assessment_plan("EU", "agricultural_spray", "pesticide", tier=3))
    us = applicable_keys(assessment_plan("US", "agricultural_spray", "pesticide", tier=3))
    assert {"SPIN", "PEARL", "PELMO", "MACRO", "SWASH", "TOXSWA", "PRZM"}.issubset(eu)
    assert {"PWC", "PRZM"}.issubset(us)


def test_plan_names_the_regulatory_programme_for_the_same_scenario():
    eu = assessment_plan("EU", "agricultural_spray", "pesticide", tier=3)
    us = assessment_plan("US", "agricultural_spray", "pesticide", tier=3)
    assert eu["regulatory_programme"]["key"] == "EU_PPP_FOCUS"
    assert us["regulatory_programme"]["key"] == "US_FIFRA"


def test_same_household_and_disposal_scenarios_route_by_jurisdiction():
    eu_household = applicable_keys(assessment_plan("EU", "household_use", "detergent_cleaner"))
    us_household = applicable_keys(assessment_plan("US", "household_use", "detergent_cleaner"))
    eu_disposal = applicable_keys(assessment_plan("EU", "product_disposal", "industrial_organic"))
    us_disposal = applicable_keys(assessment_plan("US", "product_disposal", "industrial_organic"))

    assert "SIMPLETREAT" in eu_household
    assert {"CEM", "EFAST"}.issubset(us_household)
    assert {"ENVIROCHEM_MULTIMEDIA_FATE_SCREEN", "SIMPLEBOX"}.issubset(eu_disposal)
    assert "EFAST" in us_disposal


def test_same_manufacturing_scenario_routes_to_reach_or_tsca_models():
    eu = applicable_keys(assessment_plan("EU", "industrial_effluent", "industrial_organic"))
    us = applicable_keys(assessment_plan("US", "industrial_effluent", "industrial_organic"))
    assert {"ENVIROCHEM_CATCHMENT_RIVER_NETWORK", "SIMPLEBOX"}.issubset(eu)
    assert {"ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN", "CHEMSTEER"}.issubset(us)


def test_shared_native_wastewater_models_are_explicitly_applicable_in_both():
    for jurisdiction in ("EU", "US"):
        keys = applicable_keys(
            assessment_plan(jurisdiction, "municipal_wastewater", "human_pharmaceutical")
        )
        assert {"SIMPLETREAT", "ACTIVITY_SIMPLETREAT"}.issubset(keys)


def test_guided_screen_gates_only_eu_regulatory_controls():
    assert 'data-eu-only="1" data-scroll="pearl-groundwater"' in HTML
    assert 'class="toxswa-official-import hidden" data-focus-official="1"' in HTML
    assert "$$('[data-eu-only]').forEach(node => node.classList.toggle('hidden', !eu));" in JS
    assert "$$('[data-us-only]')" not in JS


def test_water_sediment_and_industrial_panels_have_scientific_gates():
    assert "function waterSedimentWorkbenchEligible()" in JS
    assert "currentTier() >= 2" in JS
    assert "function officialFocusToxswaEligible()" in JS
    assert 'regulatoryProductClass() === "pesticide"' in JS
    assert "currentTier() >= 3" in JS
    assert "function isUSIndustrialSelection(" in JS
    assert 'state.use === "industrial"' in JS
    assert "$('us-models-placeholder')?.classList.toggle('hidden', !isUSIndustrialSelection())" in JS


def test_nonindustrial_chemical_does_not_receive_us_industrial_models():
    plan = assessment_plan("US", "industrial_effluent", "human_pharmaceutical", tier=2)
    keys = applicable_keys(plan)
    assert "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN" not in keys
    assert "CHEMSTEER" not in keys
    assert any("reserved for chemicals classified as industrial organic" in warning for warning in plan["warnings"])


def test_official_toxswa_is_tier3_pesticide_only_but_native_screen_is_tier2():
    tier2 = applicable_keys(assessment_plan("EU", "surface_water_discharge", "industrial_organic", tier=2))
    tier3_pesticide = applicable_keys(assessment_plan("EU", "agricultural_spray", "pesticide", tier=3))
    assert "ENVIROCHEM_TOXSWA_PROCESS_SCREEN" in tier2
    assert "TOXSWA" not in tier2
    assert {"ENVIROCHEM_TOXSWA_PROCESS_SCREEN", "TOXSWA", "SWASH"}.issubset(tier3_pesticide)


def test_jurisdiction_specific_model_cards_are_visually_separated():
    for key in ("US_INDUSTRIAL_SCREEN", "CHEMSTEER", "PWC", "CEM", "EFAST"):
        assert f'data-model="{key}" data-us-only-model="1"' in HTML
    # US-only tools are shown for the US and hidden for every other region (EU, CA, AU, NZ).
    assert "$$('[data-us-only-model]').forEach(node => node.classList.toggle('hidden', !us));" in JS


def test_scenario_cards_are_jurisdiction_neutral_and_workflow_routed():
    releases = (
        "surface_water", "soil", "manufacturing",
        "household_use", "product_disposal", "agricultural_spray",
    )
    for release in releases:
        assert f'data-release="{release}"' in HTML
    assert 'data-us-only="1"' not in HTML
    assert "const PROGRAMME_ROUTED_RELEASES = new Set([" in JS
    assert '"household_use", "product_disposal", "agricultural_spray"' in JS


def test_guided_plan_and_prepared_workflow_use_the_active_jurisdiction():
    assert "/api/assessment-plan" in JS
    assert "jurisdiction: state.modelSystem" in JS
    assert "jurisdiction: context.jurisdiction" in JS
    assert "regulatory_scenario: context.scenario" in JS
    assert "contaminant_group: context.contaminant_group" in JS
    assert "jurisdiction: 'US'" not in JS


def test_jurisdiction_switch_clears_results_but_preserves_scenario():
    reset = JS[JS.index("function resetForJurisdictionSwitch()"):
               JS.index("function updateScenarioJurisdictionCopy()")]
    assert "state.results = null" in reset
    assert "state.assessmentPlan = null" in reset
    assert "$('run-progress')?.classList.add('hidden')" in reset
    assert "clearAssessmentFailure()" in reset
    assert "state.release =" not in reset
    assert "Keep the scientist's selected" in reset


def test_project_and_native_run_provenance_cannot_silently_cross_tabs():
    assert "function projectMatchesModelSystem(" in JS
    assert "if (!projectMatchesModelSystem(exactProject))" in JS
    assert "if (!projectMatchesModelSystem())" in JS
    assert "row.jurisdiction === jurisdiction" in JS
    assert "`${name} — ${state.modelSystem} guided fate assessment`" in JS
    for expected in (
        "Guided ${state.modelSystem} human-pharmaceutical",
        "Guided ${state.modelSystem} ${profile.ionisation_class} sorption",
        "Guided ${state.modelSystem} WWTP assessment",
        "Selected ${state.modelSystem} wastewater-irrigation",
    ):
        assert expected in JS


def test_regions_select_has_a_real_us_only_option():
    assert '<option value="US">United States</option>' in HTML
    # Every region maps to its own option and its own tab; nothing falls back to US or EU.
    assert "if ($('regions')) $('regions').value = state.modelSystem;" in JS
    assert '<option selected="" value="EU">European Union</option>' in HTML  # the default region
    for region, label in (
        ("UK", "United Kingdom"), ("CH", "Switzerland"),
        ("CA", "Canada"), ("AU", "Australia"), ("NZ", "New Zealand"),
        ("JP", "Japan"), ("CN", "China"), ("KR", "South Korea"), ("IN", "India"),
    ):
        assert f'<option value="{region}">{label}</option>' in HTML
        assert f'data-model-system="{region}"' in HTML


def test_every_region_tab_actually_works_against_the_plan_endpoint():
    # Regression: AU/CA/NZ were added to the tabs and to registry._regulatory_programme() in an earlier session,
    # but AssessmentPlanCreate's jurisdiction Literal was never updated to match, so /api/assessment-plan silently
    # 422'd for all three -- undetected because the newer "Assessment setup" stage rail calls
    # registry._regulatory_programme() directly and never goes through this endpoint or its schema.
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        for jurisdiction in ("EU", "UK", "CH", "US", "AU", "CA", "NZ", "JP", "CN", "KR", "IN"):
            response = client.post("/api/assessment-plan", json={
                "jurisdiction": jurisdiction, "contaminant_group": "industrial_organic",
                "scenario": "municipal_wastewater", "tier": 1,
            })
            assert response.status_code == 200, (jurisdiction, response.json())


def test_uk_and_switzerland_never_receive_eu_reach_wording():
    uk = build_assessment_plan({"jurisdiction": "UK", "contaminant_group": "industrial_organic", "scenario": "industrial_effluent", "tier": 1})
    ch = build_assessment_plan({"jurisdiction": "CH", "contaminant_group": "industrial_organic", "scenario": "industrial_effluent", "tier": 1})
    assert uk["regulatory_programme"]["key"] == "UK_REACH_INDUSTRIAL" and "UK REACH" in uk["regulatory_programme"]["name"]
    assert ch["regulatory_programme"]["key"] == "CH_CHEMO_INDUSTRIAL" and "REACH" not in ch["regulatory_programme"]["name"]
    assert "EU" not in uk["regulatory_programme"]["name"] and "EU" not in ch["regulatory_programme"]["name"]


def test_an_unmapped_jurisdiction_never_inherits_eu_wording():
    # The tail of _regulatory_programme used to be an unguarded default that any unmatched jurisdiction fell into.
    # A jurisdiction with no branch at all must say so plainly, not silently receive EU REACH text. "BR" (Brazil)
    # is genuinely unmapped -- unlike JP, which now has its own branch (see test_workflow_registry.py). Calls
    # _regulatory_programme directly (build_assessment_plan also does an unrelated FRAMEWORKS lookup that would
    # StopIteration for a jurisdiction that isn't registered there at all -- not what this test is about).
    from app.services.registry import _regulatory_programme
    programme = _regulatory_programme("BR", "industrial_organic", "industrial_effluent")
    assert programme["key"] == "JURISDICTION_NOT_MAPPED"
    assert "not yet mapped" in programme["name"] and "EU" not in programme["name"] and "REACH" not in programme["scope"]


def test_laboratory_use_maps_to_a_valid_contaminant_group():
    assert 'laboratory:"industrial_organic"' in JS
    assert 'laboratory:"workplace"' not in JS


def test_regulatory_programme_panel_is_not_us_named():
    for marker in (
        'id="regulatory-programme"', 'id="regulatory-plan"',
        'id="regulatory-requirements"', 'id="regulatory-workflows"',
    ):
        assert marker in HTML
    assert "US external programme pathway" not in HTML


def test_failed_guided_run_stops_spinner_and_keeps_actionable_error_visible():
    for marker in (
        'id="run-error"', 'id="run-error-title"', 'id="run-error-message"',
        'id="run-error-detail"', 'id="retry-assessment"',
    ):
        assert marker in HTML
    assert "function renderAssessmentFailure(error)" in JS
    assert "$('run-progress')?.classList.add('hidden')" in JS
    assert "response.headers.get(\"X-Request-ID\")" in JS
    assert "renderAssessmentFailure(error);" in JS
    assert "stage('identity',0,'Assessment requires review')" not in JS
    assert "self.skipWaiting()" in SW
    assert "self.clients.claim()" in SW
