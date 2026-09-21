"""Static wiring of the Contaminated land screen (behaviour was checked in a real browser)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "contaminated-land.js").read_text(encoding="utf-8")

REQUIRED_IDS = [
    "contaminated-land", "cl-status", "cl-name", "cl-jurisdiction", "cl-sources", "cl-add-source", "cl-receptors",
    "cl-link-pathway", "cl-link-from", "cl-link-to", "cl-add-link", "cl-links", "cl-m-element", "cl-m-value",
    "cl-m-unit", "cl-m-medium", "cl-m-basis", "cl-m-weight-wrap", "cl-m-weight", "cl-m-site", "cl-m-origin",
    "cl-m-method", "cl-m-source", "cl-add-measurement", "cl-measurements", "cl-analyse", "cl-save", "cl-saved",
    "cl-open", "cl-delete", "cl-diagram", "cl-fit", "cl-assessment", "cl-load-example", "cl-project-line",
    "cl-save-new", "cl-new", "cl-editing", "cl-m-cancel",
]


def test_every_element_the_script_uses_exists_in_the_page():
    missing = [i for i in REQUIRED_IDS if f'id="{i}"' not in HTML]
    assert missing == []


def test_every_id_the_script_looks_up_is_in_the_page():
    import re
    used = set(re.findall(r'\$id\("([a-z0-9-]+)"\)', JS))
    assert [i for i in sorted(used) if f'id="{i}"' not in HTML and i != "cl-diagram-download"] == []


def test_nav_entry_and_assets_are_registered():
    assert 'data-scroll="contaminated-land"' in HTML
    assert "/static/contaminated-land.css" in HTML and "/static/contaminated-land.js" in HTML
    with TestClient(app) as client:
        for path in ("contaminated-land.js", "contaminated-land.css"):
            assert client.get(f"/static/{path}").status_code == 200


def test_script_escapes_dynamic_text_and_avoids_unsafe_apis():
    for banned in ("eval(", "document.write", "new Function", "outerHTML"):
        assert banned not in JS
    assert "escapeHtml" in JS
    assert "const esc = (value) => escapeHtml(value);" in JS


def test_screen_states_its_scope_limits():
    section = HTML[HTML.index('id="contaminated-land"'):HTML.index('id="degradation-kinetics"')]
    assert "calculates no exposure or risk" in section
    assert "never treats" in section and "no risk" in section


def test_plausibility_ui_shows_sources_and_never_hides_linkages():
    assert "plausibility_rules" in JS and "rel=\"noopener noreferrer\"" in JS
    assert "A linkage is never removed" in JS
    assert "None are assumed" in JS                      # a property value without a source is refused
    assert "https?:" in JS                               # rule links are only ever http(s)


def test_screen_shows_regime_notes_quote_documents_and_limits():
    for token in ("regime_note", "in_regime", "Position by jurisdiction", "Limits:", "q.document", "q.locator"):
        assert token in JS, token


def test_refreshes_cannot_apply_out_of_order_and_failures_are_not_silent():
    assert "refreshSeq" in JS and "seq !== CL.refreshSeq" in JS
    assert "Saved data could not be loaded for this project." in JS
    assert "Choose a saved site model to open." in JS and "Choose a saved site model to delete." in JS
