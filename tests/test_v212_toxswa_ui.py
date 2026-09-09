from pathlib import Path

from app.main import BUILD_ID
from app.services.registry import CONTAMINANT_GROUPS
from app.services.toxswa_surface_water import ROUTE_MATRIX, TWA_WINDOWS_DAYS

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
LAUNCHER = (ROOT / "START_ENVIROCHEM_CONSOLE.cmd").read_text(encoding="utf-8")


def test_toxswa_precedes_pearl_and_envirodesign_in_advanced_flow():
    assert HTML.index('id="toxswa-surface-water"') < HTML.index('id="pearl-groundwater"')
    assert HTML.index('id="pearl-groundwater"') < HTML.index('id="envirodesign"')
    assert 'id="continue-toxswa"' in HTML


def test_toxswa_ui_exposes_all_registered_contaminant_groups():
    assert set(ROUTE_MATRIX) == set(CONTAMINANT_GROUPS)
    for group in CONTAMINANT_GROUPS:
        assert f'value="{group}"' in HTML


def test_native_and_official_modes_are_explicitly_separated():
    assert "Adapted process screen" in HTML
    assert "Official FOCUS workflow" in HTML
    assert "not official FOCUS" in JS
    assert "FOCUS_TOXSWA_OFFICIAL_IMPORT" in (ROOT / "app" / "main.py").read_text(encoding="utf-8")


def test_twa_windows_include_three_day_endpoint_and_long_windows():
    assert TWA_WINDOWS_DAYS == [1, 2, 3, 4, 7, 14, 21, 28, 42, 50, 100]
    assert 'id="toxswa-twa3"' in HTML


def test_official_workflow_and_output_import_are_wired_in_frontend():
    assert 'id="prepare-toxswa-workflow"' in HTML
    assert 'id="import-toxswa-summary"' in HTML
    assert 'prepareOfficialToxswaWorkflow' in JS
    assert 'importOfficialToxswaSummary' in JS
    assert '/api/toxswa/import-official-summary' in JS


def test_current_port_build_and_crisp_toxswa_geometry():
    assert "v2.24" in BUILD_ID
    assert "8792" not in BUILD_ID
    assert 'set "PORT=%ENVIROCHEM_PORT%"' in LAUNCHER
    assert '.toxswa-shell{' in CSS and 'border:1px solid #d3dedb' in CSS
    assert 'stroke-width:1.2' in CSS


def test_pearl_and_toxswa_share_flat_process_graphic_language():
    pearl_svg = HTML[HTML.index('class="pearl-process-svg"'):]
    pearl_svg = pearl_svg[:pearl_svg.index("</svg>")]
    assert 'class="toxswa-process-svg"' in HTML
    assert 'class="pearl-process-svg"' in HTML
    assert "lineargradient" not in pearl_svg.lower()
    assert "softGlow" not in pearl_svg
    for compartment in ("pr-surface", "pr-soil", "pr-groundwater"):
        assert f'class="{compartment}"' in pearl_svg
    for live_layer in (
        'id="pearl-layer-lines"',
        'id="pearl-target-line"',
        'id="pearl-flow-arrows"',
        'id="pearl-particles"',
        'id="pearl-profile-line"',
    ):
        assert live_layer in pearl_svg
    assert ".pearl-process-svg .pr-arrow" in CSS
    assert "marker-end:url(#pearl-arrow)" in CSS
    assert "PEARL_PLOT_GEOMETRY" in JS
