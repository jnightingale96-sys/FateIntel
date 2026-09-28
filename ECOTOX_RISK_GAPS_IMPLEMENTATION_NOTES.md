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

**2026-09-27/28 re-confirmation: read the full R.16.6.7 "Predators (secondary poisoning)" section directly**
(RIVM-hosted mirror of the same guidance, echa.europa.eu itself Azure-WAF-blocked). Section R.16.6.7 covers
exactly two food chains — fish-eating and worm-eating — and its own text names a benthic-relevant example of what
it does NOT cover: "Safe levels for fish-eating animals do not exclude risks for other birds or mammals feeding
on other aquatic organisms (e.g. mussels and worms)." This upgrades the finding above from "no formula found" to
"the primary source itself says this pathway isn't its own worked example" — a citable absence, not an unsearched
one. Still not implemented, for the same reason: no formula exists anywhere primary-sourced to build it from.
Separately, this same re-read confirmed the fish/earthworm formulas already implemented here ARE R.16's general
REACH method (not pesticide-specific) — Table R.16-3's default BMF1 bands match this module's own EFSA(2023)
`_FISH_EBMF_BANDS` table exactly — so `ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN` is now also offered for
`industrial_organic` scenarios (`app/services/registry.py`), not only pesticide ones.

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

## 2. Native bee exposure model (git — commit pending as of this note)

**What shipped**: new module `app/services/eu_bees.py`, implementing the EU honey-bee Tier 1 spray
screening step (five ratios: `HQcontact`, `ETRacute adult oral`, `ETRchronic adult oral`, `ETRlarvae`,
`ETRhpg`) plus a `honey_bee_tier1_screen()` convenience function that runs all five in one call and
reports every one independently (never gates on the first breach).

**Source, and how it was actually obtained**: efsa.onlinelibrary.wiley.com is Cloudflare-blocked (same
situation as item 1) — not bypassed. The complete 266-page primary document, **EFSA Journal
2013;11(7):3295, "Guidance Document on the risk assessment of plant protection products on bees (Apis
mellifera, Bombus spp. and solitary bees)"**, was fetched from an open mirror
(`apiservices.biz/documents/articles-en/EFSA_risk_assesment_July_2013.pdf`) and read in full via
PyMuPDF. Section 3.1.2 "Risk assessment for applications applied as sprays for honey bees" (pp. 15-17)
gives the complete Tier 1 screening procedure directly in its own text — not a compound-specific worked
example, and no need for the larger Appendix J lookup tables:

- `HQcontact = AR / LD50contact` (AR g a.s./ha, LD50contact µg a.s./bee). Trigger: > 42 (downwards
  spray) or > 85 (sideward/upwards spray).
- `ETRacute adult oral = AR x SV / LD50oral` (AR kg a.s./ha; SV = 7.55 downwards, 10.6
  sideward/upwards). Trigger: > 0.2.
- `ETRchronic adult oral = AR x SV / LC50oral` (same SV pair; LC50oral µg a.s./bee/day). Trigger: > 0.03.
- `ETRlarvae = AR x SV / NOEClarvae` (SV = 4.4 downwards, 6.1 sideward/upwards). Trigger: > 0.2.
- `ETRhpg = AR x SV / NOEChpg` (same SV pair as adult oral; only relevant if the adult chronic study
  showed a hypopharyngeal-gland effect). Trigger: > 1.

"Downwards spray" vs. "sideward/upwards spray" confirmed from the guidance's own text (p. 15 area,
matched at line ~9569 of the extracted text): sideward/upwards is explicitly the guidance's own example
of "sideward/upwards (SUW) spray applications (e.g. air assisted orchard sprayer)" — i.e. an
air-assisted/orchard-type sprayer; "downwards" is the standard ground/boom application by elimination
(the guidance's own two-category split, not an inference from outside the text).

**Scope boundary, stated plainly (matches the same discipline as `eu_birds_mammals.py`)**: honey bees
only (bumble bees and solitary bees have different trigger values elsewhere in the guidance, not
implemented); spray applications only (granular and seed-treatment routes have their own different
first-tier schemes, sections not read this session, not implemented).

**The one honest caveat that matters most**: a REVISED version of this guidance was adopted in 2023
(EFSA Journal 2023;21(5):7989) — not obtained this session either (also Wiley-hosted). Partial text
was read from an open PMC mirror (`pmc.ncbi.nlm.nih.gov/articles/PMC10173852/`) via WebFetch (which,
unlike the built-in browser, was NOT blocked by Cloudflare on this specific host — confirmed by direct
comparison). That partial reading shows the 2023 revision keeps the same overall PEQ/HQ/ETR shape but
with a different contact-exposure formulation (`PEQcontact = AR x EFcontact x BSF`) and, per its own
newer specific protection goal (10% maximum colony-size reduction), different trigger values — neither
of which were confirmed or extracted in full. This module implements the 2013 guidance's own Tier 1
screen only, labelled as such throughout (module docstring, `GUIDANCE_REFERENCE` constant, every
result's `guidance_reference` field) — it is not represented as the current 2023 EU trigger set.

**Not wired to an API endpoint or UI screen** — same established precedent as item 1 and the
pre-existing fish/earthworm pathways.

**Registry visibility**: unlike item 1 (which extended an already-registered module), this is a brand
new module, so — matching how `ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN` was itself originally registered —
a new `ENVIROCHEM_EU_BEES_SCREEN` entry was added to `registry.py`'s `MODELS` list and
`adapters.py`'s `ADAPTER_CONTRACTS`, selected for EU/UK/CH pesticide agricultural_spray/
soil_incorporation scenarios when `bee_attractive` is set (mirroring the existing US `BEEREX` gating on
the same flag). AU is deliberately excluded from this new entry even though AU inherits
`ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN` — APVMA's own bee methodology is an explicitly named, confirmed
research gap in `au_apvma.py`, unlike the birds/mammals screen, which is a confirmed EFSA-2009-aligned
methodology match. This still does not add any calculation endpoint — the registry entry only makes the
model "planned" and visible in the assessment plan, exactly as `ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN` has
been since before this session.

Also fixed in passing: `ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN`'s registry/adapter `expected_outputs` and
workflow steps were stale (listed only `fish_secondary_poisoning_ter`, missing the earthworm pathway
added earlier in this same session under item 1) — updated to include
`earthworm_secondary_poisoning_ter` and its own workflow step.

**Tests**: `tests/test_eu_bees.py`, 14 new cases (every one of the five ratios cross-checked by hand
for both spray directions, the full `honey_bee_tier1_screen()` convenience function including the
HPG-optional behaviour and unit-conversion correctness, input validation). `tests/test_registry.py`
gained 3 new cases for the `bee_attractive` gating (EU selects it, EU without the flag does not, AU
never selects it). `tests/test_adapter_contracts.py` extended to expect the new key. Full suite: 792
passed, 5 skipped (was 775).

## 3. Formal PBT/PMT/vPvM classifier (git — commit pending as of this note)

**What shipped**: new module `app/services/pbt_pmt_classifier.py`, with two entry points —
`classify_pbt_and_vpvb()` (UK REACH Annex XIII, Sections 1.1/1.2) and `classify_pmt_and_vpvm()` (EU CLP
Annex I Section 4.4, as inserted by Delegated Regulation (EU) 2023/707). Both combine persistence (P/vP,
per-compartment DT50 half-life), bioaccumulation (B/vB, BCF) or mobility (M/vM, log Koc), and toxicity (T
— NOEC/EC10, CMR classification, STOT RE, and for PMT only, endocrine-disruptor category 1) into an actual
AND-combined determination, not just the single-criterion prompts `pathway_plausibility.py` already had.

**Source, and how it was actually obtained**: read directly in full via the built-in browser (not
summarised by another tool) — REACH Annex XIII from `legislation.gov.uk/eur/2006/1907/annex/XIII` (the
same UK REACH source `pathway_plausibility.py`'s B2/M1 rules already cite) and the CLP delegated
regulation's full Annex I Section 4.4 text via `javascript_tool` against `eur-lex.europa.eu`'s rendered
page (a first WebFetch pass on the same URL returned a plausible-looking but tool-summarised version,
which was not trusted — the primary page text was pulled directly instead, matching this project's
standing discipline against relying on another tool's own summary of a primary source).

**The numbers, confirmed identical where they are identical**: REACH Annex XIII 1.1.1 (P) and CLP Annex I
4.4.2.1.1 (P) give the exact same five compartment thresholds (marine water > 60 days, fresh/estuarine
water > 40 days, marine sediment > 180 days, fresh/estuarine sediment > 120 days, soil > 120 days) — and
1.2.1/4.4.2.2.1 (vP) likewise match exactly (60/60/180/180/180). This was confirmed by reading both
primary texts, not assumed, and one shared `_half_life_determination()` helper is used for both PBT-P and
PMT-P. Toxicity differs by exactly one limb: CLP's PMT toxicity criterion (4.4.2.1.3(d)) adds "classified
endocrine disruptor category 1 (human health or environment)", which REACH Annex XIII's PBT toxicity
criterion (1.1.3) does not have — `classify_pbt_and_vpvb()` doesn't even expose that parameter, so it
can't be silently applied where the regulation doesn't provide for it.

**Reused, not re-typed**: the BCF (B: >2,000, vB: >5,000) and log Koc (M: <3, vM: <2) thresholds were
already shipped in `pathway_plausibility.py`'s B2/M1 rules as inline literals — extracted into named
constants (`BCF_B_THRESHOLD_L_PER_KG`, `BCF_VB_THRESHOLD_L_PER_KG`, `LOG_KOC_M_THRESHOLD`,
`LOG_KOC_VM_THRESHOLD`) there and imported here, so the two modules' numbers can't quietly drift apart —
same discipline as reusing `equilibrium_partitioning.py`'s constants for the earthworm pathway (item 1).

**The one honest caveat that matters most, on every single result**: both regulations state, in their own
text, that identification is a weight-of-evidence determination using expert judgement over *all* relevant
and available information (REACH Annex XIII intro paragraph 2; CLP Annex I 4.4.2.3, near-identical
wording), listing further evidence types this classifier does not evaluate (terrestrial bioaccumulation
studies, biomagnification/trophic magnification factors, monitoring and field data, and more). This
classifier mechanically checks only the specific numeric/hazard-classification criteria named in Sections
1.1/1.2 (REACH) and 4.4.2.1/4.4.2.2 (CLP) — every result carries a `caveat` field saying exactly this, and
a "not met"/"inconclusive" outcome is documented as never being a substitute for a real regulatory
determination. Consistent with this, a BCF or log Koc that misses its numeric threshold is reported as
`INCONCLUSIVE`, never a conclusive "not bioaccumulative"/"not mobile" — only persistence can return a
conclusive `NOT_MET`, and only when *all five* compartments were measured and none exceed the threshold
(persistence is an OR condition across compartments, so partial data can never conclusively rule it out).

**Not wired to an API endpoint, and deliberately not added to `registry.py`'s `MODELS` list** — checked
first: `pathway_plausibility.py`'s own `evaluate_step`/`evaluate_path`/`rules_metadata` functions aren't
wired to any endpoint either (only its `PROPERTY_SPECS` labels are exposed, via
`/api/conceptual-site-model/reference`), and it has no `registry.py` entry at all. This classifier is the
same kind of substance-level hazard-classification tool, not a jurisdiction/scenario-routed exposure or
fate model — forcing it into `registry.py`'s region/group/tier-driven `MODELS` list (the pattern used for
the new bee screen, item 2) would be a worse fit than following `pathway_plausibility.py`'s own precedent.

**Tests**: `tests/test_pbt_pmt_classifier.py`, 14 new cases — PBT met when all three criteria are met,
vPvB met on persistence+bioaccumulation alone (no toxicity needed, per Annex XIII 1.2), a genuine
conclusive `NOT_MET` when every persistence compartment is measured and none exceed, partial persistence
data correctly staying `INCONCLUSIVE` rather than `NOT_MET`, bioaccumulation below threshold staying
`INCONCLUSIVE`, each CMR/STOT-RE flag recognised independently, a drift guard cross-checking the reused
`pathway_plausibility.py` thresholds, PMT's endocrine-disruptor limb, and input validation. Full suite:
806 passed, 5 skipped (was 792).
