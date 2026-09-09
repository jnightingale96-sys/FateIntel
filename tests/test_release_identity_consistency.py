"""The packaged application must report one consistent release identity.

app/version.py is the single source of truth, but the launcher(s), service
worker, web manifest, README heading and cache-busting static-asset query
strings each carry their own copy of the current version string. Three
earlier releases each missed a different subset of these independently:
Alpha 3.2 bumped app/version.py without updating the launcher/README/cached
JS/CSS at all; the Alpha 3.2.1 hotfix that followed updated
START_ENVIROCHEM_CONSOLE.cmd and one embedded README build= link but missed
the separate START_ENVIROCHEM.bat wrapper and README's own H1/intro; and the
Alpha 3.2.2 hotfix fixed those but missed a static "NEW · v2.23 ALPHA 3.1"
release badge in index.html, in a space-separated prose form that no
hyphenated-tag check would catch. All were confirmed by independent external
audits and independently reproduced. This test makes that whole class of
drift fail loudly instead of silently, matching the existing "v2.23" in
BUILD_ID convention already used elsewhere in this suite.

SUPERSEDED_TAGS accumulates one entry per past release rather than being
replaced at each bump: the whole point is to catch a *previously* fixed
reference quietly regressing, and a single "check only the immediately prior
tag" list would stop watching for the ones before that.
"""
from pathlib import Path

from app.version import APP_VERSION, BUILD_ID

ROOT = Path(__file__).resolve().parents[1]
CURRENT_TAG = "alpha3.4.0"  # bump alongside app/version.py at each release
CURRENT_NUMBER = "3.4.0"  # numeric core, for the space-separated prose forms
SUPERSEDED_TAGS = ("alpha3.1", "alpha3.2.1", "alpha3.2.2", "alpha3.2.3", "alpha3.3.0")  # append the previous CURRENT_TAG here at each release


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _contains_stale_tag(text: str, stale_tag: str) -> bool:
    # Catches both the hyphenated "alpha3.1" form and the space-separated,
    # possibly upper-cased "Alpha 3.1" prose form (e.g. a UI release badge) --
    # checking only the hyphenated form previously missed a stale prose badge
    # in index.html that no other check caught.
    lowered = text.lower()
    return stale_tag in lowered or stale_tag.replace("alpha", "alpha ") in lowered


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
    # START_ENVIROCHEM_CONSOLE.cmd carries the full hyphenated BUILD_ID; the
    # thin START_ENVIROCHEM.bat wrapper only ever carried a human-readable
    # "Alpha X.Y.Z" banner (space-separated, no BUILD variable of its own) --
    # checking only the former previously missed the latter drifting.
    console = _read("START_ENVIROCHEM_CONSOLE.cmd")
    assert BUILD_ID in console
    assert CURRENT_TAG in console

    wrapper = _read("START_ENVIROCHEM.bat")
    assert CURRENT_NUMBER in wrapper, "START_ENVIROCHEM.bat does not reference the current release number"


def test_release_badge_matches_current_release():
    # A static prose release badge on the guided-assessment welcome screen
    # (index.html) previously drifted independently of every hyphenated
    # cache-busting tag check -- it carries only the human-readable number.
    assert CURRENT_NUMBER in _read("app/static/index.html")


def test_readme_references_the_current_build_id():
    assert BUILD_ID in _read("README.md")


def test_readme_heading_matches_current_release():
    # Checking BUILD_ID anywhere in the file previously missed the H1/intro
    # itself drifting while only a deeper build= link got updated.
    heading = _read("README.md").splitlines()[0]
    assert CURRENT_TAG.replace("alpha", "Alpha ") in heading or CURRENT_NUMBER in heading


def test_progress_status_title_matches_current_version():
    # Title-line convention is "Alpha 3.2.3" (spaced), unlike the hyphenated
    # cache-busting tag used elsewhere -- check the numeric core only.
    assert CURRENT_NUMBER in _read("PROGRESS_STATUS.md").splitlines()[0]


def test_no_superseded_identity_strings_remain():
    # These files should only ever report the CURRENT identity, with no
    # legitimate historical exception (unlike README.md and PROGRESS_STATUS.md,
    # which deliberately retain historical "Alpha X.Y.Z" section headers as
    # changelog entries -- their current-ness is checked separately, by heading
    # and title-line, above). Checks every past release's tag, not just the one
    # immediately before this one, so a previously fixed reference regressing
    # is still caught.
    checked = (
        "app/static/index.html", "app/static/expert.html", "app/static/sw.js",
        "app/static/manifest.webmanifest",
        "START_ENVIROCHEM_CONSOLE.cmd", "START_ENVIROCHEM.bat",
    )
    for relative_path in checked:
        text = _read(relative_path)
        for stale_tag in SUPERSEDED_TAGS:
            assert not _contains_stale_tag(text, stale_tag), f"{relative_path} still references the superseded {stale_tag} identity"
    readme_heading = _read("README.md").splitlines()[0]
    for stale_tag in SUPERSEDED_TAGS:
        assert not _contains_stale_tag(readme_heading, stale_tag), f"README heading still references the superseded {stale_tag} identity"
