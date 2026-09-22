"""Real-browser check of the assessment setup shell (region tabs, chemical group, tracks, per-group screen visibility).

Starts its own server against a throwaway SQLite file, so the real database is never touched.
Usage:  python scripts/browser_check_flow.py [--engine chromium|firefox|webkit|all]   (needs `pip install playwright`)
"""

from __future__ import annotations

import argparse
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bc", ROOT / "scripts" / "browser_check_contaminated_land.py")
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


def visible(page, selector: str) -> bool:
    """True when the element exists and is actually displayed (not display:none, not zero-size)."""
    return bool(page.evaluate(
        """(sel) => { const el = document.querySelector(sel); if (!el) return false;
            const cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden' && el.getClientRects().length > 0; }""",
        selector))


def nav_visible(page, target: str) -> bool:
    return visible(page, f'.nav-item[data-scroll="{target}"]')


def choose(page, container: str, text: str) -> None:
    page.locator(f"#{container} button", has_text=text).first.click()
    page.wait_for_function("() => window.flowShell && window.flowShell._state.workflow !== null")
    page.wait_for_timeout(350)


def selected(page, container: str) -> list[str]:
    return page.eval_on_selector_all(f'#{container} button[aria-selected="true"]', "els => els.map(e => e.textContent)")


def rail_text(page) -> str:
    """Rail and note text. Status pills are upper-cased by CSS, so compare with `in_rail`, which ignores case."""
    return page.inner_text("#flow-rail") + "\n" + page.inner_text("#flow-note")


def in_rail(page, needle: str) -> bool:
    return needle.lower() in rail_text(page).lower()


def run(page, errors, base):
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    page.goto(base + "/", wait_until="networkidle")
    page.wait_for_function("() => window.flowShell && window.flowShell._state.workflow !== null", timeout=15000)

    # ---- first load: EU, human pharmaceutical
    check("eleven region tabs", page.locator("[data-model-system]").count() == 11)
    check("default EU tab is selected", page.get_attribute('[data-model-system="EU"]', "aria-selected") == "true")
    check("default group is human pharmaceutical", selected(page, "flow-groups") == ["Human pharmaceutical"], str(selected(page, "flow-groups")))
    check("pharma: contaminated land screen is hidden", not visible(page, "#contaminated-land"))
    check("pharma: contaminated land nav item is hidden", not nav_visible(page, "contaminated-land"))
    check("pharma: assessment flow is visible", visible(page, "#assessment-flow"))
    check("pharma: EnviroDesign is visible", visible(page, "#envirodesign"))
    check("pharma: no track row (one track)", not visible(page, "#flow-tracks"))
    check("pharma: rail names the regulatory route", "Regulatory route" in rail_text(page))

    # ---- metals: site track opens first and hides the organic flow
    choose(page, "flow-families", "Metals and metalloids")
    check("metals: two tracks offered", page.locator("#flow-tracks button").count() == 2)
    check("metals: opens on the site track", selected(page, "flow-tracks") == ["Contaminated-site assessment"], str(selected(page, "flow-tracks")))
    check("metals site: contaminated land is visible", visible(page, "#contaminated-land"))
    check("metals site: organic assessment flow is hidden", not visible(page, "#assessment-flow"))
    check("metals site: EnviroDesign / kinetics hidden", not visible(page, "#envirodesign") and not visible(page, "#degradation-kinetics"))
    check("metals site: nav shows contaminated land, not assessments",
          nav_visible(page, "contaminated-land") and not nav_visible(page, "assessment-flow"))
    check("metals site: rail says no risk is calculated", "No exposure or risk is calculated" in rail_text(page))
    check("metals site: regional methods are listed", "Regional methods (" in rail_text(page) or page.locator(".flow-methods").count() == 1)
    page.locator("#flow-tracks button", has_text="Use and release").click()
    page.wait_for_timeout(300)
    check("metals use/release: assessment visible, land hidden", visible(page, "#assessment-flow") and not visible(page, "#contaminated-land"))
    check("metals use/release: no native screen (results, kinetics hidden)", not visible(page, "#degradation-kinetics"))
    check("metals use/release: rail says an external model is required", in_rail(page, "External model required"))

    # ---- PFAS is offered both tracks and defaults to use and release
    choose(page, "flow-families", "PFAS")
    check("pfas: opens on use and release", selected(page, "flow-tracks") == ["Use and release assessment"], str(selected(page, "flow-tracks")))
    check("pfas: land not shown until the site track is chosen", not visible(page, "#contaminated-land"))

    # ---- radionuclides: blocked, only identity + route remain
    choose(page, "flow-families", "Radionuclides")
    choose(page, "flow-groups", "Radionuclide")
    check("radionuclide: blocked note shown", "does not model" in page.inner_text("#flow-note"))
    check("radionuclide: no track row", not visible(page, "#flow-tracks"))
    check("radionuclide: regulatory route card visible", visible(page, "#regulatory-pathway"))
    check("radionuclide: release / compartment cards hidden", not visible(page, "#step-release") and not visible(page, "#step-compartments"))
    check("radionuclide: land screen hidden", not visible(page, "#contaminated-land"))

    # ---- use card <-> group stay in step
    choose(page, "flow-families", "Pesticides and biocides")
    check("pesticide group selected", "Pesticide (plant protection)" in selected(page, "flow-groups"), str(selected(page, "flow-groups")))
    check("pesticide -> agriculture use card active", page.get_attribute('#use-cards [data-use="agriculture"]', "class").find("active") >= 0)
    page.click('#use-cards [data-use="veterinary"]')
    page.wait_for_function("() => window.flowShell._state.group === 'veterinary_pharmaceutical'")
    page.wait_for_timeout(300)
    check("veterinary card -> veterinary group in the chooser", "Veterinary medicine" in selected(page, "flow-groups"), str(selected(page, "flow-groups")))

    # ---- regions
    choose(page, "flow-families", "Pharmaceuticals and personal care")
    choose(page, "flow-groups", "Human pharmaceutical")
    check("EU rail: refinement is ready", "Water-sediment process screen" in rail_text(page))

    # UK and Switzerland are their own tabs, sharing the FOCUS refinement suite but never each other's or EU's
    # regulatory-route wording (registry._regulatory_programme has its own branch for each).
    page.click('[data-model-system="UK"]')
    page.wait_for_timeout(600)
    check("UK: status names the UK, not the EU", "United Kingdom" in page.inner_text("#model-system-status"))
    check("UK: FOCUS PEARL still available (shared refinement)", visible(page, "#pearl-groundwater"))
    check("UK: rail names UK REACH", "UK REACH" in rail_text(page), rail_text(page)[:200])
    check("UK: rail never says EU REACH", "EU REACH" not in rail_text(page))
    page.click('[data-model-system="CH"]')
    page.wait_for_timeout(600)
    check("CH: status names Switzerland", "Switzerland" in page.inner_text("#model-system-status"))
    check("CH: FOCUS PEARL still available (shared refinement)", visible(page, "#pearl-groundwater"))
    check("CH: rail names ChemO, not REACH", "ChemO" in rail_text(page) and "REACH" not in rail_text(page), rail_text(page)[:200])
    choose(page, "flow-families", "Metals and metalloids")
    ch_methods = page.inner_text("#flow-rail")
    check("CH site methods: nothing named yet (honest)", "0 of" in ch_methods or "not established" in ch_methods.lower(), ch_methods[:300])
    choose(page, "flow-families", "Pharmaceuticals and personal care")
    choose(page, "flow-groups", "Human pharmaceutical")

    page.click('[data-model-system="CA"]')
    page.wait_for_timeout(700)
    status = page.inner_text("#model-system-status")
    check("CA: status names Canada and not the EU", "Canada" in status and "EU" not in status, status[:120])
    check("CA: FOCUS PEARL hidden", not visible(page, "#pearl-groundwater"))
    check("CA: rail says refinement is not built", in_rail(page, "Not built") and in_rail(page, "No dedicated refinement screen is built for Canada"))
    check("CA: rail names a Canadian route", "Canadian" in rail_text(page), rail_text(page)[:200])
    spray = page.inner_text('#release-cards [data-release="agricultural_spray"]')
    check("CA: agricultural spray card has no EU/FOCUS wording", "FOCUS" not in spray and "EU" not in spray, spray)
    for code, needle in (("AU", "AICIS"), ("NZ", "HSNO"), ("JP", "CSCL"), ("CN", "China REACH"), ("KR", "K-REACH"), ("IN", "MSIHC")):
        choose(page, "flow-families", "Industrial, detergent")
        page.click(f'[data-model-system="{code}"]')
        page.wait_for_timeout(600)
        check(f"{code}: rail names its regulator ({needle})", needle in rail_text(page), rail_text(page)[:160])
        check(f"{code}: no EU or US refinement screen", not visible(page, "#pearl-groundwater") and not visible(page, "#us-models-placeholder"))
        check(f"{code}: no EU or UK REACH wording", "EU REACH" not in rail_text(page) and "UK REACH" not in rail_text(page))

    # Japan's pesticide route names its own PEC criterion; India's site track names all four receptors (the
    # 2025 Contaminated Sites Rules is the broadest of the four new countries' sources).
    page.click('[data-model-system="JP"]')
    page.wait_for_timeout(500)
    choose(page, "flow-families", "Pesticides and biocides")
    check("JP pesticide: names its own PEC criterion", "Predicted Environmental Concentration" in rail_text(page), rail_text(page)[:250])
    page.click('[data-model-system="IN"]')
    page.wait_for_timeout(500)
    choose(page, "flow-families", "Legacy persistent organics")
    in_methods = page.inner_text("#flow-rail")
    check("IN site methods: all four receptors named", "4 of 4" in in_methods, in_methods[:300])
    choose(page, "flow-families", "Pharmaceuticals and personal care")
    choose(page, "flow-groups", "Human pharmaceutical")
    page.click('[data-model-system="US"]')
    page.wait_for_timeout(600)
    check("US rail: EPA models are the refinement", "US EPA models" in rail_text(page))
    check("US: PEARL hidden", not visible(page, "#pearl-groundwater"))

    # ---- site jurisdiction follows the region
    page.click('[data-model-system="AU"]')
    page.wait_for_timeout(400)
    choose(page, "flow-families", "Metals and metalloids")
    check("AU metals site: jurisdiction selector moved to AU", page.input_value("#cl-jurisdiction") == "AU", page.input_value("#cl-jurisdiction"))

    # ---- layout
    check("no horizontal page overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
    check("no console or page errors", not errors, "; ".join(errors[:3]))
    return results


def run_failure_path(page, base):
    """If the registry call fails nothing may be hidden."""
    out = []
    page.route("**/api/workflow*", lambda route: route.fulfill(status=500, body='{"detail":"boom"}', content_type="application/json"))
    page.goto(base + "/", wait_until="networkidle")
    page.wait_for_timeout(1500)
    out.append(("registry failure: every screen stays visible", page.evaluate("document.querySelectorAll('.flow-hidden').length === 0")))
    out.append(("registry failure: user is told", "could not be loaded" in page.inner_text("#flow-note")))
    return out


def run_engine(playwright, engine: str, base: str):
    browser = getattr(playwright, engine).launch()
    try:
        context = browser.new_context(viewport={"width": 1500, "height": 1000})
        context.add_init_script(
            "document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
            f" s.textContent = {bc.NO_SMOOTH_SCROLL!r}; document.head.appendChild(s); }});")
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "favicon" not in m.text else None)
        results = run(page, errors, base)
        page.close()
        fail_page = context.new_page()
        results += [(n, ok, "") for n, ok in run_failure_path(fail_page, base)]
        return results
    finally:
        browser.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", default="chromium", choices=["chromium", "firefox", "webkit", "all"])
    engines = ["chromium", "firefox", "webkit"] if parser.parse_args().engine == "all" else [parser.parse_args().engine]
    failed = 0
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    port = bc.free_port()
    server = bc.start_server(Path(tmp.name) / "flow.sqlite", port)
    try:
        with sync_playwright() as p:
            for engine in engines:
                results = run_engine(p, engine, f"http://127.0.0.1:{port}")
                bad = [(n, d) for n, ok, d in results if not ok]
                print(f"[{engine}] {len(results) - len(bad)}/{len(results)} checks passed")
                for name, detail in bad:
                    print(f"   FAIL {name}" + (f"  ({detail})" if detail else ""))
                failed += len(bad)
    finally:
        server.terminate()
        tmp.cleanup()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
