from pathlib import Path

from app.services.envirodesign import browser_config

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


def test_tier_1_2_assessment_precedes_advanced_modules_in_document_order():
    assert HTML.index('id="assessment-flow"') < HTML.index('id="advanced-refinement"')
    assert HTML.index('id="advanced-refinement"') < HTML.index('id="pearl-groundwater"')
    assert HTML.index('id="pearl-groundwater"') < HTML.index('id="envirodesign"')


def test_regulatory_model_switch_exposes_us_foundation_and_external_boundary():
    assert 'data-model-system="EU"' in HTML
    assert 'data-model-system="US"' in HTML
    assert 'US EXPOSURE FOUNDATIONS · ALPHA 2' in HTML
    assert 'EPA tools remain managed external workflows' in JS
    assert 'Native screen ≠ EPA model output' in HTML


def test_native_calculators_and_jurisdiction_workflows_are_kept_distinct():
    assert 'const LIVE_RELEASES = new Set(["wastewater","biosolids","irrigation"]);' in JS
    assert 'const PROGRAMME_ROUTED_RELEASES = new Set([' in JS
    assert "routesThroughRegulatoryProgramme()" in JS
    for text in ('Wastewater', 'Biosolids', 'Wastewater irrigation'):
        assert text in HTML
    for text in ('Manufacturing / processing', 'Household / consumer use', 'Product disposal', 'Agricultural spray'):
        assert text in HTML


def test_scenario_specific_assessment_does_not_run_pearl_automatically():
    run_block = JS[JS.index('async function runAssessment()'):JS.index('function setMetricVisible')]
    assert 'runPearl(' not in run_block
    assert "if (state.release === 'biosolids')" in run_block
    assert "if (state.release === 'irrigation')" in run_block


def test_irrigation_and_biosolids_have_independent_multiyear_series():
    assert "drawSoilSeries(biosolids.outputs.annual_series" in JS
    assert "drawSoilSeries(irrigation.outputs.native_screen.annual_series" in JS
    assert 'id="irrigation-years"' in HTML and 'value="10"' in HTML
    assert 'id="biosolids-years"' in HTML and 'value="10"' in HTML


def test_envirodesign_exposes_human_readable_benzene_region_and_native_depiction_rule():
    config = browser_config()
    assert config['feature_smarts']['benzene_like_aromatic_ring'] == 'c1ccccc1'
    assert 'Original RDKit depiction' in HTML
    assert 'mol.get_svg(620,350)' in JS


def test_professional_geometry_override_uses_crisp_rules():
    assert '--radius:2px' in CSS
    assert '.flow-line{left:25px;border-left:1px solid' in CSS
    assert 'border-radius:2px !important' in CSS
    assert '#pearl-flow-arrows path{stroke-width:1.2' in CSS

def test_envirodesign_does_not_load_remote_rdkit_during_core_startup():
    init_block = JS[JS.index('async function init()'):]
    assert 'runEnviroDesign(false)' not in init_block
    assert 'EnviroDesign is an advanced, user-invoked screen' in JS
