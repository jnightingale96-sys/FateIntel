from pathlib import Path

from fastapi.testclient import TestClient

from app.main import BUILD_ID, app

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
GUIDED_HTML = (STATIC / "index.html").read_text(encoding="utf-8")
GUIDED_JS = (STATIC / "app.js").read_text(encoding="utf-8")
EXPERT_HTML = (STATIC / "expert.html").read_text(encoding="utf-8")
EXPERT_JS = (STATIC / "expert-app.js").read_text(encoding="utf-8")
LAUNCHER = (ROOT / "START_ENVIROCHEM_CONSOLE.cmd").read_text(encoding="utf-8")
LAUNCHER_SUPPORT = (ROOT / "app" / "launcher_support.py").read_text(encoding="utf-8")
TOOLS = (ROOT / "ENVIROCHEM_TOOLS.bat").read_text(encoding="utf-8")


def test_build_identity_is_decoupled_from_runtime_port():
    assert "v2.24" in BUILD_ID
    assert "8792" not in BUILD_ID
    assert 'set "PORT=8792"' in LAUNCHER
    assert 'if defined ENVIROCHEM_PORT set "PORT=%ENVIROCHEM_PORT%"' in LAUNCHER
    assert "-m app.launcher_support configured-port" in LAUNCHER
    assert "-m app.launcher_support probe-build" in LAUNCHER
    assert "-m app.launcher_support find-port" in LAUNCHER
    assert "FateIntel is already running" in LAUNCHER
    assert "open-when-ready" in LAUNCHER
    assert "/api/ready" in LAUNCHER_SUPPORT
    with TestClient(app) as client:
        payload = client.get("/api/build").json()
    assert payload["runtime_port_configurable"] is True
    assert payload["default_port"] == 8792
    assert "expected_port" not in payload


def test_guided_ui_has_truthful_save_state_and_project_switcher():
    assert 'id="save-state"' in GUIDED_HTML
    assert "Assessment autosaved" not in GUIDED_HTML
    assert 'id="project-menu"' in GUIDED_HTML
    assert 'if (tracksSave) setSaveState("saving", "Saving…")' in GUIDED_JS
    assert 'url.startsWith(route)' in GUIDED_JS
    assert "renderProjectSwitcher" in GUIDED_JS


def test_rule_based_explainer_and_unavailable_routes_are_explicit():
    assert "Assessment Explainer" in GUIDED_HTML
    assert "RULE-BASED EXPLAINER" in GUIDED_HTML
    assert "AI Copilot" not in GUIDED_HTML
    assert 'id="regulatory-programme"' in GUIDED_HTML
    assert "PROGRAMME_ROUTED_RELEASES" in GUIDED_JS
    assert "no result will be fabricated" in GUIDED_JS
    assert "This is a rule-based assessment explainer" in GUIDED_JS


def test_expert_ui_surfaces_async_failures_without_alerts():
    assert 'id="toast-stack"' in EXPERT_HTML
    assert 'window.addEventListener("unhandledrejection"' in EXPERT_JS
    assert "alert(" not in EXPERT_JS
    assert "showToast" in EXPERT_JS


def test_support_tools_are_consolidated_and_resets_are_confirmed():
    assert "Run startup diagnostics" in TOOLS
    assert "Type RESET PYTHON to continue" in TOOLS
    assert "Type DELETE LOCAL DATA to continue" in TOOLS
    for retired in (
        "DIAGNOSE_STARTUP.bat",
        "RESET_PYTHON_ENVIRONMENT.bat",
        "RESET_LOCAL_DATABASE.bat",
        "CHECK_FOCUS_INSTALLATION.bat",
        "VERIFY_NEW_BUILD.bat",
    ):
        assert not (ROOT / retired).exists()
