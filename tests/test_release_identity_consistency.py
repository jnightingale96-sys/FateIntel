"""The packaged application must report one consistent release identity.

app/version.py is the single source of truth, but the launcher, service
worker, web manifest and cache-busting static-asset query strings each carry
their own copy of the current version string. An earlier release (Alpha 3.2)
bumped app/version.py without updating any of these, so the backend reported
alpha3.2 while the launcher, README and cached JS/CSS still said alpha3.1 --
confirmed by an external audit and independently reproduced. This test makes
that class of drift fail loudly instead of silently, matching the existing
"v2.23" in BUILD_ID convention already used elsewhere in this suite.
"""
from pathlib import Path

from app.version import APP_VERSION, BUILD_ID

ROOT = Path(__file__).resolve().parents[1]
CURRENT_TAG = "alpha3.2.1"  # bump alongside app/version.py at each release


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_version_module_is_internally_consistent():
    assert CURRENT_TAG in APP_VERSION
    assert CURRENT_TAG in BUILD_ID


def test_static_cache_busting_tags_match_current_release():
    for relative_path in ("app/static/index.html", "app/static/expert.html", "app/static/sw.js"):
        assert CURRENT_TAG in _read(relative_path), f"{relative_path} does not reference {CURRENT_TAG}"


def test_manifest_reports_the_current_build_id():
    manifest = _read("app/static/manifest.webmanifest")
    assert CURRENT_TAG in manifest
    assert BUILD_ID in manifest


def test_launcher_reports_the_current_build_id():
    launcher = _read("START_ENVIROCHEM_CONSOLE.cmd")
    assert BUILD_ID in launcher
    assert CURRENT_TAG in launcher


def test_readme_references_the_current_build_id():
    assert BUILD_ID in _read("README.md")


def test_progress_status_title_matches_current_version():
    # Title-line convention is "Alpha 3.2.1" (spaced), unlike the hyphenated
    # cache-busting tag used elsewhere -- check the numeric core only.
    assert "3.2.1" in _read("PROGRESS_STATUS.md").splitlines()[0]


def test_no_stale_alpha3_1_identity_strings_remain():
    # The one deliberate exception: the historical Alpha 3.1 release-notes file
    # correctly keeps its own version string, and PROGRESS_STATUS.md carries a
    # historical Alpha 3.1 section header alongside its current title.
    checked = (
        "app/static/index.html", "app/static/expert.html", "app/static/sw.js",
        "app/static/manifest.webmanifest", "README.md", "START_ENVIROCHEM_CONSOLE.cmd",
    )
    for relative_path in checked:
        text = _read(relative_path)
        assert "alpha3.1" not in text.lower(), f"{relative_path} still references the superseded alpha3.1 identity"
