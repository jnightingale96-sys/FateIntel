# Brazil, Mexico, Singapore, Taiwan, South Africa — jurisdiction expansion (completing "finish the countries")

## Why

Continuation of `REGION_RESEARCH_NORWAY_UAE_SAUDI.md`. That file's "Not done" section named five countries
whose research agents hit a session rate limit and failed before returning: Brazil, Mexico, Singapore,
Taiwan, South Africa. Both agents were re-launched once the rate limit cleared and completed successfully
this time. This file covers implementing that research — the last piece of "finish the countries" before
returning to the 90-day commercial validation plan.

## What shipped

All five follow the exact pattern already used for JP/CN/KR/IN and Norway/UAE/Saudi Arabia: `schemas.py`
Literal extended, `registry.py`'s `FRAMEWORKS` and `_regulatory_programme()` gained real branches,
`workflow_registry.py`'s `REGIONS` gained entries (all five with `refinement: None` — none confirmed a
shared native fate-screen suite the way Norway did), `index.html`'s tabs and dropdown extended, `app.js`'s
region maps extended. Live-verified in the browser: clicked the South Africa tab in the running app,
confirmed zero console errors, read back the real rendered "South Africa selected... No dedicated
refinement screen is built for South Africa yet" text.

None of the five got any calculable native model added (no FOCUS-suite extension, no EFSA screens) —
every one of them stays in the same "regime named, EXTERNAL MODEL REQUIRED" shape as JP/CN/KR/IN, not
Norway's "genuinely confirmed equivalent regime" shape. This is an honest reflection of what the research
found, not a scope limitation self-imposed this session.

### Brazil (BR) — the single strongest-sourced pesticide finding of the whole country-expansion effort

- **Pesticides**: IBAMA's own 2012 methodology document (a real, hosted, primary government PDF, not a
  secondary description) names a two-part method — PPA (hazard baseline) and ARA (an exposure-layered risk
  assessment: application method, dose, crop, climate, with aquatic- and soil-organism scenarios). This is
  genuinely comparable to Japan's CSCL finding in strength, arguably better sourced. **Deliberately not
  implemented as a calculator**: the equations themselves were not read to implementation depth this
  session, so `BR_IBAMA_PPA_ARA_PARTIAL` stays a "structure confirmed" pathway, not a working model — the
  same discipline that kept CSCL's real structure from becoming a fabricated calculation.
- **Industrial chemicals**: Law 15.022/2024 created the INSQ, a REACH-like regime, in force since 15
  November 2024 — but its implementing decree (dossier format, assessment method) was still in public
  consultation as of the research date, with full dossiers due 15 November 2026. No method exists to map yet
  — a genuine "not yet finalised" gap, not a research shortfall.
- **Human pharmaceuticals**: no ANVISA ERA requirement found; a peer-reviewed comparative review states
  plainly "Brazil and other Latin American regulators have not integrated ERAs into drug approval" —
  confirmed absence, secondary-sourced.
- **Veterinary pharmaceuticals**: MAPA (not ANVISA) — IN 26/2009 names environmental protection as a
  concern but gives no method.

### Mexico (MX) — the one jurisdiction with a genuinely confirmed absence of a *review step*, not just a method

- **Pesticides**: the CICOPLAFEST tripartite system requires environmental-fate and ecotoxicity studies to
  be *submitted*, but a peer-reviewed academic source (SciELO) states explicitly that registration is
  decided on dossier completeness, not on running any Mexico-specific risk assessment against local
  conditions — a confirmed absence of the calculation step itself, not merely of a documented method.
- **Industrial chemicals**: genuinely nothing found (COFEPRIS's "registro sanitario" is a security control,
  not environmental risk regulation) — reported as an open research gap, explicitly not a confirmed absence,
  since the search wasn't exhaustive.
- **Human/veterinary pharmaceuticals**: both stay unconfirmed — the human-pharma ERA claim came from a
  single weak non-government consultancy source, and SENASICA (the distinct veterinary regulator) had
  nothing found either way.

### Singapore (SG), Taiwan (TW) — REACH-modelled structure without a calculable method (Taiwan), narrow listed-substance licensing (Singapore)

- **Singapore industrial chemicals**: NEA's Hazardous Substances Licence is a *listed-substance* licensing
  system (Second Schedule), not general new-chemical registration — a real, different design from EU REACH,
  not a lesser version of it. A new mandatory reporting framework for GHS-triggered substances takes effect
  1 January 2026.
- **Singapore human pharma**: HSA's own guidance-documents index was checked directly and lists no general
  ERA requirement for standard drug registration — a confirmed absence from a primary source (the strongest
  Singapore finding). A secondary, unconfirmed claim about cell/tissue/gene-therapy-specific ERA was
  deliberately left out of the encoded scope text's assertions, reported only as unconfirmed.
- **Taiwan industrial chemicals**: the TCCSCA is explicitly modelled on EU REACH (confirmed by reading the
  primary law text directly, not a secondary description) — the same "real structure, no calculable method"
  shape as Japan's CSCL and Brazil's pesticide pathway above.
- **Taiwan pesticides**: the current parent-ministry name genuinely could not be confirmed (Council of
  Agriculture's 2023 reorganisation into a Ministry of Agriculture) — reported as an explicit uncertainty
  in the scope text rather than guessing which name is current.

### South Africa (ZA) — two peer-reviewed confirmed absences, plus a real structural finding

- **Pesticides and human pharmaceuticals**: a single peer-reviewed 2026 literature review (*Environmental
  Monitoring and Assessment*) states explicitly that Act 36 of 1947 "does not include... mandatory
  environmental risk assessments" and that SAHPRA's Medicines Act "does not address the entry of
  pharmaceuticals into the environment" — two genuine confirmed absences from one peer-reviewed source,
  with the pharma finding partially corroborated by SAHPRA's own registration-guidance table of contents
  (fetched directly, showing no environment/Module 1.6 entry).
  - **Genuine structural finding, not assumed**: food-producing-animal veterinary "stock remedies" are
    **not** regulated by SAHPRA at all — they sit under the exact same Act 36 as pesticides, administered by
    DALRRD. Veterinarian-administered remedies are separately carved out under a different Act entirely
    (the Veterinary Act 16 of 1933). This is exactly the kind of cross-jurisdiction structural divergence
    this project's discipline exists to catch rather than silently assume away.
  - The pesticide ERA-absence finding was **not** extrapolated to the veterinary stock-remedies pathway,
    even though they share the same Act — the primary document fetch for the stock-remedies-specific
    guideline failed (a certificate error), so `ZA_ACT36_VETERINARY_NOT_MAPPED` stays an open gap rather
    than a second confirmed-absence claim built on an unread document.
- **Industrial chemicals**: confirmed absent (multiple consistent secondary sources); NEMA authorises
  control but only asbestos and PCBs are confirmed as actually-controlled substances.

## Tests

- `tests/test_workflow_registry.py`: region-count assertion updated (16 → 19); 6 new cases across the five
  countries (Brazil's PPA/ARA structure named and kept partial; Brazil's confirmed pharma absence; Mexico's
  three genuinely distinct agencies across pesticide/veterinary/human routes; Taiwan's REACH-modelled
  structure kept partial; South Africa's Act 36 pesticide/veterinary sharing vs. SAHPRA's separate human
  pathway; South Africa's two confirmed absences named by their exact programme keys; Singapore's confirmed
  pharma absence).
- `tests/test_jurisdiction_separation.py`: the existing region round-trip regression tests (the ones that
  originally caught the JP/CN/KR/IN "stale Literal" bug class) extended to cover all five. The "genuinely
  unmapped jurisdiction" placeholder test was switched from `"BR"` (now mapped) to `"ZZ"` (a code this
  codebase will never add a branch for), so it stays meaningful as more countries are added in the future.
- Live-verified in the running app: clicked the South Africa tab, confirmed zero console errors, read back
  the real rendered regulatory-route text.

Full suite: 901 passed, 5 skipped (was 870 after Norway/UAE/Saudi Arabia; 849 before that).

## Country-expansion list is now complete

Every country named in the original "more countries" list (Brazil, Mexico, Norway, Singapore, Taiwan, Gulf
states, South Africa) has been researched and implemented. FateIntel now supports 19 jurisdictions. Per the
user's own instruction ("Finish the countries, then back to the 90-day validation plan"), the next step is
returning to that paused validation-plan work.
