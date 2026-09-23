# Ecotox / risk-evaluation gaps — implementation notes

Running log. Add to it; don't replace it.

## Why

User (2026-09-23), asked to weigh in on "complete more countries, then more ecotox/risk evaluations": agreed
ecotox/risk gaps are higher-leverage than more countries right now (country expansion mostly yields honest
"agency named, not yet mapped" labels; ecotox gaps improve every region already built). User: "1 first but then
prompt 2 and 3 when done" (1 = ecotox/risk gaps, 2 = more countries, 3 = the paused 90-day validation plan).
Three named gaps, in the order tackled:
1. Earthworm/benthic-invertebrate secondary poisoning (EU birds & mammals) — DONE (earthworm only; see below).
2. Native bee exposure model — not started.
3. Formal PBT/PMT/vPvM classifier — not started.

## 1. Earthworm-eating secondary poisoning (git — commit pending as of this note)

**What shipped**: `app/services/eu_birds_mammals.py` gained `earthworm_bioconcentration_factor()` and
`earthworm_secondary_poisoning_ter()`, extending the existing fish-eating secondary-poisoning pathway (built in
an earlier session) to the second of the three prey types the module's own docstring named as missing.

**Source, and how it was actually obtained**: efsa.onlinelibrary.wiley.com (the EFSA Journal's host) is behind
Cloudflare bot-detection — confirmed by navigating there in the built-in browser and seeing the "Just a moment…"
interstitial. Per this project's rule against defeating bot-detection, that was not pushed through. A EC
implementation-schedule cover page, a Sagentia advisory PDF, and a ResearchGate preview page were all tried and
each gave only secondary confirmation that EFSA (2023) uses "the 'pore water' approach" for earthworms with a
7-day TWA soil concentration — real, but not the formula itself. The actual formula was found in a different,
related, and freely-hosted primary document: **ECHA, "Guidance on Information Requirements and Chemical Safety
Assessment, Chapter R.16: Environmental Exposure Estimation", Version 2.1 (October 2012)**, fetched from an RIVM
mirror (rivm.nl) that Wiley/EFSA blocked but RIVM did not, and read in full via PyMuPDF after WebFetch's own
summariser reported the PDF unreadable (same "the tool's own summary isn't enough" pattern used earlier in this
project for the UK CLP mobility text). Section R.16.6.7.2 (pp. 90-91, equations R.16-71 to R.16-76) and
Table R.16-9 (p. 49) give the complete method:

- `Kp_soil = Foc_soil x Koc` (R.16-6)
- `BCFearthworm = (0.84 + 0.012 x Kow) / RHOearthworm`, RHOearthworm default 1 kgwwt/L (R.16-76, **Jager, T.
  (1998), "Mechanistic approach for estimating bioconcentration of organic chemicals in earthworms", Environ.
  Toxicol. Chem.**) — the equation is explicitly attributed to Jager (1998) in the ECHA text itself.
- `Cporewater = (Csoil x RHOsoil) / (1000 x Ksoil-water)` — derived by algebraically inverting the *already
  shipped and tested* `derive_pnec_soil_from_water()` in `equilibrium_partitioning.py`, rather than re-deriving
  independently from the PDF's own column-scrambled equation layout for R.16-57 (safer: one soil-porewater
  relationship across the whole app, not two that could quietly drift apart). Confirmed dimensionally consistent
  with the primary text's own symbol table for R.16-57.
- `Cearthworm = (BCFearthworm x Cporewater + Csoil x Fgut x CONVsoil) / (1 + Fgut x CONVsoil)`, with
  `CONVsoil = RHOsoil / RHOsolid` (R.16-74) and `Fgut = 0.1 kg dwt gut/kg wwt worm` by default (R.16.6.7.2, p. 91)
  (R.16-72/73/75) — the weighted-average-of-tissue-and-gut-contents model, since predators eat earthworms gut
  contents and all.
- `PECoral,predator = Cearthworm` (R.16-71).
- Jager (1998)'s own stated application range: soil-exposure data covered log Kow 3-8, water-only data 1-6, "an
  application range of 1-8 is advised" — implemented as `EARTHWORM_BCF_VALIDATED_LOG_KOW_RANGE`, reported per
  result as `within_bcf_validated_range`, never silently gating the calculation.

**The one honest caveat that matters most**: this is ECHA's REACH guidance (2012), not the EFSA (2023)
birds-and-mammals guidance text itself, which was never obtained. Multiple independent secondary sources (HSE,
Sagentia, ADAS/CEA — none of them quoting the actual formula) consistently describe EFSA (2023)'s own earthworm
method as "the pore water approach," which is exactly this mechanism, and Jager/Romijn-style equilibrium
partitioning for soil organisms is the standard, widely cross-referenced EU method for this exposure route — but
the *exact* numeric constants (0.84, 0.012, Fgut=0.1) have not been independently confirmed as reproduced
verbatim in the EFSA (2023) text. Reported as such in the module docstring and every result's
`guidance_reference` field (cites ECHA R.16 by name, not the EFSA Journal reference the rest of the module uses).

**Benthic-invertebrate-eating secondary poisoning is still NOT implemented.** Checked ECHA R.16 directly this
session: it has no equivalent sediment-organism bioaccumulation formula. A secondary source (Sagentia, 2025)
describes "the introduction of benthic invertebrate-eating species" as one of EFSA (2023)'s own changes from the
2009 guidance — this looks like a genuinely new addition specific to the 2023 text, not something carried over
from the older REACH-era guidance. No primary source for its formula was found this session.

**Not wired to an API endpoint or UI screen — matching existing precedent, not an oversight.** Neither
`eu_birds_mammals.py`'s existing (pre-this-session) fish pathway nor `equilibrium_partitioning.py`'s soil/sediment
PNEC functions (built in an earlier session, explicitly named as closing "the highest-leverage gap") are wired to
any `/api/` route or front-end screen either — confirmed by grep across `app/main.py` and every `app/static/*.js`/
`*.html` file. This looks like a deliberate, established pattern in this codebase: build and test the science
first, wire the UI later as a separate unit of work. The earthworm addition follows the same pattern rather than
breaking from it. If the user wants any of these three actually reachable from the guided page, that is a
distinct follow-up task (an endpoint at minimum; a form + results panel for the full experience).

**Tests**: `tests/test_eu_birds_mammals.py`, 8 new cases (BCF formula by hand, a full by-hand cross-check of every
intermediate value against the R.16 equations, the validated-range report at both ends, measured-BCF override,
an internal-consistency guard against `equilibrium_partitioning.py`'s own constants drifting, input validation).
Full suite: 775 passed, 5 skipped.

## 2. Native bee exposure model — not started

## 3. Formal PBT/PMT/vPvM classifier — not started

Existing building blocks already in the codebase: `pathway_plausibility.py`'s B2 rule (UK REACH Annex XIII
bioaccumulation: B if BCF>2,000, vB if BCF>5,000) and M1 rule (EU CLP mobility: mobile if log Koc<3, very mobile
if <2) are single-criterion *prompts* within the site-model plausibility system, not a formal multi-criterion
classifier that combines P/vP + B/vB + T (or P/vP + M/vM + T) into an actual PBT/vPvB/PMT/vPvM determination
against the real regulatory definition. A classifier would need the full REACH Annex XIII criteria set (including
persistence — DT50 thresholds — and toxicity — NOEC/CMR criteria — neither of which exist in this codebase yet)
research before it could be built with the same "don't invent chemistry" discipline used throughout this project.
