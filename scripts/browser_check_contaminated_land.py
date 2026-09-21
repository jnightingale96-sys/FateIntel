"""Real-browser check of the "Contaminated land" screen in Chromium, Firefox and WebKit.

Starts its own FateIntel server on a free port against a THROWAWAY SQLite database (never the real
data/envirochem.sqlite), drives the screen with real clicks, and prints PASS/FAIL per check.

Usage (any Python that has Playwright; the server itself runs in the project's .venv if present):
    python scripts/browser_check_contaminated_land.py                      # all three engines
    python scripts/browser_check_contaminated_land.py firefox webkit
    python scripts/browser_check_contaminated_land.py --screenshots out    # keep the screenshots

One-off setup: pip install playwright && python -m playwright install chromium firefox webkit
An engine that is not installed is reported and skipped, never counted as a pass.
Exit code 0 only if every engine that ran passed every check.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ("chromium", "firefox", "webkit")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server_python() -> str:
    for candidate in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def start_server(db_path: Path, port: int) -> subprocess.Popen:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}
    proc = subprocess.Popen(
        [server_python(), "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit("The test server exited early; check that the project's dependencies are installed.")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/frameworks", timeout=2).read()
            return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise SystemExit("The test server did not become ready within 60 seconds.")


SNAPSHOTS: list[str] = []

# The app sets `scroll-behavior: smooth`. In Firefox and WebKit a Playwright click issued while a smooth scroll is still
# animating is sometimes silently lost (measured: WebKit 3 of 40, Firefox 1 of 40, Chromium 0 of 40; 0 of 40 everywhere
# with smooth scrolling off). That looked like an intermittent app hang for a long time. Real users click at the position
# they see, so this is a test-timing artefact: switch CSS smooth scrolling off for the run, and wait for the nav's own
# explicit smooth scroll to settle before doing anything else.
NO_SMOOTH_SCROLL = "html { scroll-behavior: auto !important; }"


def settle_scroll(page) -> None:
    last_y = None
    for _ in range(60):
        y = page.evaluate("window.scrollY")
        if y == last_y:
            page.wait_for_timeout(100)
            if page.evaluate("window.scrollY") == y:
                return
        last_y = y
        page.wait_for_timeout(120)


def open_section(page) -> None:
    page.click('button.nav-item[data-scroll="contaminated-land"]')
    page.wait_for_selector("#cl-sources .cl-source")
    settle_scroll(page)


def open_saved_model(page, label: str) -> None:
    """Click Open, recording the button/select state before and shortly after, for failure reports."""
    js = """() => { const b = document.getElementById('cl-open'), s = document.getElementById('cl-saved');
        const r = b.getBoundingClientRect(); const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return {disabled: b.disabled, selectValue: s.value, options: s.options.length,
                clickable: top === b || b.contains(top), status: document.querySelector('#cl-status strong')?.textContent,
                scrollY: Math.round(window.scrollY)}; }"""
    before = page.evaluate(js)
    page.click("#cl-open")
    page.wait_for_timeout(400)
    after = page.evaluate(js)
    SNAPSHOTS.append(f"{label}: before={before} after={after}")
    del SNAPSHOTS[:-6]


def analyse_and_wait(page) -> None:
    """Click Analyse and wait until THIS analysis finished. Waiting for the results table is not enough: an earlier
    analysis leaves one behind, so the wait would return at once and later checks would read stale content. The click
    handler sets the status to "Analysing..." synchronously, so "Analysis complete" can only come from this run."""
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-status strong') && document.querySelector('#cl-status strong').textContent.startsWith('Analysis complete')")


def run_flow(page, errors, check, BASE, shots: Path, engine: str) -> None:
    page.goto(BASE + "/", wait_until="networkidle")
    check("nav item present", page.locator('button.nav-item[data-scroll="contaminated-land"]').count() == 1)
    open_section(page)
    # Make sure the section's own controls are not hidden under the sticky top bar once the nav scroll has settled
    # (a real bug once: "Load fictional example" ended up beneath the project pill).
    covered = page.evaluate("""() => {
        const b = document.getElementById('cl-load-example');
        const r = b.getBoundingClientRect();
        const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return !(top === b || b.contains(top));
    }""")
    check("Load example button is not covered by the sticky top bar after the nav scroll", not covered)
    check("builder renders one blank source", page.locator("#cl-sources .cl-source").count() == 1)
    check("jurisdiction select filled", page.locator("#cl-jurisdiction option").count() >= 7)
    check("measurement element list has Pb", page.locator('#cl-m-element option[value="Pb"]').count() == 1)

    # water medium hides weight basis and swaps units
    page.select_option("#cl-m-medium", "water")
    check("water hides weight basis", page.locator("#cl-m-weight-wrap").is_hidden())
    check("water shows ug/L unit", page.locator('#cl-m-unit option[value="ug/L"]').count() == 1)
    page.select_option("#cl-m-medium", "soil")
    check("soil shows weight basis", page.locator("#cl-m-weight-wrap").is_visible())

    # error path: analyse an empty model
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-status').classList.contains('cl-error')")
    check("empty model analysis reports an error", "could not be analysed" in page.inner_text("#cl-status"),
          page.inner_text("#cl-status").replace("\n", " | ")[:140])

    # example
    page.click("#cl-load-example")
    page.wait_for_function("document.querySelectorAll('#cl-sources .cl-source').length === 2")
    check("example fills 2 sources", True)
    check("example fills pathways", page.locator("#cl-links li").count() == 9, str(page.locator("#cl-links li").count()))
    analyse_and_wait(page)
    check("diagram image shown", page.locator("#cl-diagram img").count() == 1)
    img_ok = page.eval_on_selector("#cl-diagram img", "i => i.complete && i.naturalWidth > 0")
    check("diagram image decoded", img_ok)
    page.click("#cl-fit")
    check("fit toggle switches to actual size", page.locator("#cl-diagram.actual").count() == 1 and page.inner_text("#cl-fit") == "Fit to width",
          f"class={page.get_attribute('#cl-diagram', 'class')!r} button={page.inner_text('#cl-fit')!r} img={page.locator('#cl-diagram img').count()}")
    page.click("#cl-fit")
    stats = page.locator(".cl-stat strong").all_inner_texts()
    check("summary stats rendered", len(stats) == 4, str(stats))
    text = page.inner_text("#cl-assessment")
    check("POPs badge shown for PCB-153", "POPs status detected" in text)
    check("no-linkage receptor warned, not called safe", "not a finding of no risk" in text and "wildlife" in text.lower())
    check("external route shown for UK", "CLEA" in text and "ConSim" in text)
    check("disclaimer shown", "no exposure, dose or risk is calculated" in text.lower())
    check("no 'safe' verdict wording", " safe" not in text.lower())
    page.locator("#contaminated-land").screenshot(path=str(shots / f"contaminated_land_{engine}.png"))

    # measurement flow (creates a project in the SCRATCH database)
    before_gaps = int(stats[2])
    page.select_option("#cl-m-element", "Pb")
    page.fill("#cl-m-value", "350")
    page.select_option("#cl-m-medium", "soil")
    page.select_option("#cl-m-unit", "mg/kg")
    page.select_option("#cl-m-weight", "dry")
    page.select_option("#cl-m-site", "soil")
    # missing source must be refused client-side
    page.click("#cl-add-measurement")
    check("measurement without source refused", "needs a source" in page.inner_text("#cl-status"))
    page.fill("#cl-m-source", "Lab report ABC-12, sample BH3")
    page.click("#cl-add-measurement")
    page.wait_for_selector("#cl-measurements .cl-measurement")
    check("measurement listed with original units", "350 mg/kg dry weight" in page.inner_text("#cl-measurements"))
    check("project created and shown", "Site:" in page.inner_text("#cl-project-line"))
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-status strong').textContent.startsWith('Analysis complete')")
    stats2 = page.locator(".cl-stat strong").all_inner_texts()
    check("measurement reduces the gap count", int(stats2[2]) < before_gaps, f"{before_gaps} -> {stats2[2]}")
    check("measurement linkage reported", "linked to the model" in page.inner_text("#cl-assessment"))

    # save, reload, reopen
    page.click("#cl-save")
    page.wait_for_function("document.querySelectorAll('#cl-saved option[value]:not([value=\"\"])').length === 1")
    check("saved model listed", "Fictional example site" in " ".join(page.locator("#cl-saved option").all_inner_texts()), "select.innerText=" + repr(page.inner_text("#cl-saved")) + " options=" + repr(page.locator("#cl-saved option").all_inner_texts()))
    page.reload(wait_until="networkidle")
    open_section(page)
    page.wait_for_function("document.querySelectorAll('#cl-saved option[value]:not([value=\"\"])').length === 1")
    check("saved model survives reload (project remembered)", True)
    open_saved_model(page, "open#1")
    page.wait_for_function("document.querySelectorAll('#cl-sources .cl-source').length === 2")
    check("open restores sources and name", page.input_value("#cl-name") == "Fictional example site")
    analyse_and_wait(page)
    check("reopened model still analyses with saved measurement", "linked to the model" in page.inner_text("#cl-assessment"))

    # ---- edit a measurement in place ----
    page.click('#cl-measurements button[data-edit]')
    check("edit loads the measurement into the form",
          page.input_value("#cl-m-value") == "350" and page.input_value("#cl-m-source").startswith("Lab report ABC-12")
          and page.input_value("#cl-m-unit") == "mg/kg" and page.input_value("#cl-m-site") == "soil")
    check("edit shows Update and Cancel", page.inner_text("#cl-add-measurement") == "Update measurement" and page.locator("#cl-m-cancel").is_visible())
    check("edited row is highlighted", page.locator("#cl-measurements .cl-measurement.editing").count() == 1)
    page.click("#cl-m-cancel")
    check("cancel restores the form", page.inner_text("#cl-add-measurement") == "Save measurement"
          and page.input_value("#cl-m-value") == "" and page.locator("#cl-m-cancel").is_hidden(),
          f"button={page.inner_text('#cl-add-measurement')!r} value={page.input_value('#cl-m-value')!r} cancel_hidden={page.locator('#cl-m-cancel').is_hidden()}")
    page.click('#cl-measurements button[data-edit]')
    page.fill("#cl-m-value", "410")
    page.select_option("#cl-m-basis", "dissolved")
    page.fill("#cl-m-source", "Lab report ABC-12 (re-issued)")
    page.click("#cl-add-measurement")
    page.wait_for_function("document.querySelector('#cl-status strong').textContent === 'Measurement updated.'")
    listed = page.inner_text("#cl-measurements")
    check("measurement updated, not duplicated", "410 mg/kg dry weight" in listed and "dissolved" in listed
          and page.locator("#cl-measurements .cl-measurement").count() == 1, listed.replace("\n", " ")[:120])
    check("form back to Save after update", page.inner_text("#cl-add-measurement") == "Save measurement")
    page.fill("#cl-m-value", "")
    page.click('#cl-measurements button[data-edit]')
    page.click("#cl-add-measurement")   # empty source guard while editing is unaffected: source is prefilled
    page.wait_for_function("document.querySelector('#cl-status strong').textContent === 'Measurement updated.'")

    # ---- edit a saved model in place ----
    check("open marks the model as being edited", page.inner_text("#cl-save") == "Update saved model"
          and page.locator("#cl-save-new").is_visible() and "Editing saved model" in page.inner_text("#cl-editing"))
    page.fill("#cl-name", "Fictional example site (revised)")
    page.click('#cl-links button[data-i="0"]')
    check("pathway removed in builder", page.locator("#cl-links li").count() == 8)
    page.click("#cl-save")
    page.wait_for_function("document.querySelector('#cl-status strong').textContent === 'Site model updated.'")
    opts = page.locator("#cl-saved option").all_inner_texts()
    check("saved model updated in place, not duplicated", len(opts) == 1 and "(revised)" in opts[0], str(opts))
    page.reload(wait_until="networkidle")
    open_section(page)
    page.wait_for_function("document.querySelectorAll('#cl-saved option[value]:not([value=\"\"])').length === 1")
    open_saved_model(page, "open#2 (after reload)")
    page.wait_for_function("document.querySelectorAll('#cl-links li').length === 8")
    check("update persisted across reload", page.input_value("#cl-name").endswith("(revised)"))
    page.fill("#cl-name", "Copy of the revised model")
    page.click("#cl-save-new")
    page.wait_for_function("document.querySelector('#cl-status strong').textContent === 'Site model saved.'")
    check("save as new copy adds a second model", page.locator("#cl-saved option").count() == 2)
    page.click("#cl-new")
    check("new model resets the builder", page.inner_text("#cl-save") == "Save site model"
          and page.locator("#cl-save-new").is_hidden() and page.input_value("#cl-name") == ""
          and page.locator("#cl-links li").count() == 1)  # the single 'no pathways yet' placeholder row

    # delete measurement then both models
    page.click('#cl-measurements button[aria-label="Delete measurement"]')
    page.wait_for_function("document.querySelectorAll('#cl-measurements .cl-measurement').length === 0")
    check("measurement deleted", True)
    for _ in range(2):
        page.click("#cl-delete")
        page.wait_for_timeout(400)
    page.wait_for_function("document.querySelector('#cl-saved').value === ''")
    check("both models deleted", True)

    # XSS check: hostile contaminant name is inert
    page.click("#cl-load-example")
    page.wait_for_function("document.querySelectorAll('#cl-sources .cl-source').length === 2")
    page.fill('#cl-sources .cl-source:first-child input[data-f="name"]', '<img src=x onerror="window.__xss=1">')
    analyse_and_wait(page)
    check("hostile name does not execute", page.evaluate("window.__xss === undefined"))

    # ---- plausibility: sourced properties, badges, prompts, rules panel ----
    page.click("#cl-load-example")
    page.wait_for_function("document.querySelectorAll('#cl-sources .cl-source').length === 2")
    tce = page.locator("#cl-sources .cl-source").nth(1)
    check("properties section starts collapsed", tce.locator("details.cl-props[open]").count() == 0)
    tce.locator("summary").click()
    tce.locator('input[data-f="p:vapour_pressure_mm_hg"]').fill("50")
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-status').classList.contains('cl-error')")
    check("property value without a source is refused", "source of the property values" in page.inner_text("#cl-status"))
    tce.locator('input[data-f="p:source"]').fill("browser test value, not real data")
    analyse_and_wait(page)
    text = page.inner_text("#cl-assessment")
    check("supported badge shown for the volatile route", "supported" in text and "V1" in text)
    check("plausibility prompts panel shown", "Plausibility prompts" in text and "A linkage is never removed" in text)
    check("missing properties are listed, not assumed", "Properties needed to apply the screening definitions" in text)
    check("linkage count unchanged by plausibility", page.locator(".cl-stat strong").first.inner_text() == "20")
    page.locator("details.cl-rules summary").click()
    rules = page.inner_text("details.cl-rules")
    check("rules panel quotes the source text and page", "greater than 10-5 atmosphere-meter cubed per mole" in rules
          and "PDF page 58" in rules and "greater than 5,000" in rules)
    check("rules panel lists what is not encoded", "Not encoded" in rules and "plant uptake" in rules.lower())
    check("rules panel includes the UK sources (UK REACH Annex XIII, Defra, Environment Agency)",
          "Annex XIII" in rules and "higher than 2 000" in rules and "Defra" in rules
          and "Environment Agency" in rules and "several regulatory agencies" in rules)
    check("rules panel says where each criterion is formal and its limits",
          "Position by jurisdiction" in rules and "Limits:" in rules and "interim, non-statutory" in rules.lower())
    check("rule quotes link to their source documents",
          page.locator('details.cl-rules a[href^="https://www.legislation.gov.uk/"]').count() >= 1)
    check("rules panel includes the EU CLP mobility rule with its quote",
          "M1" in rules and "log Koc is less than 3" in rules and "weight of evidence" in rules)
    check("rule source links to the EPA document",
          page.locator('details.cl-rules a[href^="https://www.epa.gov/"]').count() == 1)
    tce.locator('input[data-f="p:vapour_pressure_mm_hg"]').fill("0.00001")
    tce.locator('input[data-f="p:henry_law_constant_atm_m3_mol"]').fill("0.00000001")
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-assessment').innerText.includes('review: questioned')")
    q_text = page.inner_text("#cl-assessment")
    check("below both EPA values questions relevance with the caveat",
          "naphthalene" in q_text and "review it, do not exclude it" in q_text)
    check("questioned route is still listed", page.locator(".cl-stat strong").first.inner_text() == "20")
    check("prompt states the UK regime position for volatility", "No UK volatility criterion was found" in q_text)
    tce.locator('input[data-f="p:log_koc"]').fill("1.8")
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-assessment').innerText.includes('very mobile substance')")
    check("log Koc below 2 shows the very-mobile prompt", "M1" in page.inner_text("#cl-assessment"))
    page.fill("#cl-name", "Plausibility round trip")
    page.click("#cl-save")
    page.wait_for_function("document.querySelector('#cl-status strong').textContent === 'Site model saved.'")
    page.click("#cl-new")
    open_saved_model(page, "open#3 (plausibility round trip)")
    page.wait_for_function("document.querySelectorAll('#cl-sources .cl-source').length === 2")
    tce = page.locator("#cl-sources .cl-source").nth(1)
    check("properties survive save and reopen",
          float(tce.locator('input[data-f="p:vapour_pressure_mm_hg"]').input_value()) == 1e-05
          and tce.locator('input[data-f="p:source"]').input_value() == "browser test value, not real data"
          and tce.locator("details.cl-props[open]").count() == 1)
    tce.locator('input[data-f="p:source"]').fill('<img src=x onerror="window.__xss2=1">')
    analyse_and_wait(page)
    check("hostile property source does not execute", page.evaluate("window.__xss2 === undefined"))
    check("hostile property source is shown as text", "<img src=x" in page.inner_text("#cl-assessment"))
    tce.locator('input[data-f="p:vapour_pressure_mm_hg"]').fill("abc")
    page.click("#cl-analyse")
    page.wait_for_function("document.querySelector('#cl-status').classList.contains('cl-error')")
    check("non-numeric property is refused", "must be a number" in page.inner_text("#cl-status"))
    page.click("#cl-delete")
    page.wait_for_timeout(400)

    # mobile layout
    page.set_viewport_size({"width": 390, "height": 900})
    page.locator("#contaminated-land").scroll_into_view_if_needed()
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check("no horizontal page overflow at 390px", overflow <= 1, f"overflow={overflow}")
    page.locator("#cl-sources").screenshot(path=str(shots / f"contaminated_land_mobile_{engine}.png"))

    check("no console/page errors", not errors, "; ".join(errors)[:300])


def run_engine(playwright, engine: str, base: str, shots: Path):
    results: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))
        print(("  PASS " if ok else "  FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)

    try:
        browser = getattr(playwright, engine).launch()
    except Exception as exc:  # engine not installed
        print(f"  SKIPPED: {engine} is not available ({str(exc).splitlines()[0]})")
        return None
    try:
        context = browser.new_context(viewport={"width": 1500, "height": 1000})
        context.add_init_script(
            "document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
            f" s.textContent = {NO_SMOOTH_SCROLL!r}; document.head.appendChild(s); }});")
        page = context.new_page()
        # Playwright polls wait_for_function with requestAnimationFrame by default, which headless Firefox/WebKit can
        # pause when the window is not visible, so a wait can time out although the page is already in the awaited
        # state. Poll on a timer instead.
        SNAPSHOTS.clear()
        _wait = page.wait_for_function
        awaited: list[str] = []

        def _wait_logged(expression, **kw):
            awaited.append(expression)
            return _wait(expression, polling=100, **kw)

        page.wait_for_function = _wait_logged
        errors: list[str] = []
        net: list[str] = []
        page.on("response", lambda r: net.append(f"{r.status} {r.request.method} {r.url.split('/api/')[-1][:60]}") if "/api/" in r.url else None)
        page.on("requestfailed", lambda r: net.append(f"FAILED {r.method} {r.url.split('/api/')[-1][:60]}") if "/api/" in r.url else None)
        # the empty-model error test deliberately provokes one HTTP 422, which browsers log
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "422" not in m.text else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: d.accept())
        try:
            run_flow(page, errors, check, base, shots, engine)
        except Exception as exc:  # a timeout or a selector that never appeared is a failure, not a crash
            try:
                status = " | ".join(page.inner_text("#cl-status").splitlines())[:200] + f" [class={page.get_attribute('#cl-status', 'class')!r}, count={page.locator('#cl-status').count()}]"
                last_line = [ln.strip() for ln in str(exc).splitlines() if "waiting for" in ln or "function" in ln.lower()][:2]
                try:
                    truth = page.evaluate("""async () => {
                        const id = localStorage.getItem('fateintel.contaminatedLand.projectId');
                        const saved = id ? await (await fetch(`/api/projects/${id}/site-models`)).json() : null;
                        return {storedProjectId: id, serverSavedModels: saved && saved.length,
                                savedSelectHtml: document.getElementById('cl-saved').innerHTML.slice(0, 200),
                                projectLine: document.getElementById('cl-project-line').innerText.slice(0, 120),
                                scrollY: window.scrollY, readyState: document.readyState};
                    }""")
                except Exception as diag_exc:
                    truth = f"(diagnostic failed: {diag_exc})"
                status += f" | truth={truth!r}"
            except Exception:
                status, last_line = "(page unreadable)", []
            check("flow completed without an unexpected error", False,
                  f"{type(exc).__name__}: {str(exc).splitlines()[0]} | status={status!r} | page_errors={errors[:3]!r} | snapshots={SNAPSHOTS[-3:]!r} | after_check={results[-1][0] if results else None!r} | waiting_for={awaited[-1][:200] if awaited else None!r} | last_api={net[-8:]!r} | {last_line}")
    finally:
        browser.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("engines", nargs="*", help=f"any of {', '.join(ENGINES)} (default: all three)")
    parser.add_argument("--screenshots", type=Path, help="directory to keep screenshots in")
    args = parser.parse_args()
    engines = args.engines or list(ENGINES)
    unknown = [e for e in engines if e not in ENGINES]
    if unknown:
        parser.error(f"unknown engine(s): {', '.join(unknown)}; choose from {', '.join(ENGINES)}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed: pip install playwright && python -m playwright install chromium firefox webkit")
        return 2

    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    shots = args.screenshots or Path(tmp.name)
    shots.mkdir(parents=True, exist_ok=True)
    port = free_port()
    server = start_server(Path(tmp.name) / "browser_check.sqlite", port)
    base = f"http://127.0.0.1:{port}"
    summary: dict[str, str] = {}
    try:
        with sync_playwright() as playwright:
            for engine in engines:
                print(f"== {engine}")
                results = run_engine(playwright, engine, base, shots)
                if results is None:
                    summary[engine] = "skipped (not installed)"
                    continue
                failed = [r for r in results if not r[1]]
                summary[engine] = f"{len(results) - len(failed)}/{len(results)} checks passed"
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
        tmp.cleanup()

    print("\nSummary")
    for engine, text in summary.items():
        print(f"  {engine:9s} {text}")
    ran = [t for t in summary.values() if not t.startswith("skipped")]
    all_ok = bool(ran) and all(t.split("/")[0] == t.split("/")[1].split()[0] for t in ran)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
