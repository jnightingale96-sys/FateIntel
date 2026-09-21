# UK regulatory/model matrix — legacy & inorganic contaminants (contaminated land, groundwater, surface water, sediment)

Research pass, 2026-09-19. Scope: United Kingdom only (England/Wales primarily — EA/UKHSA/CL:AIRE
are England-and-Wales-centric; SEPA/Scotland and NIEA/Northern Ireland equivalents are named where
found but not independently verified this session). Every row below is sourced to a document this
session actually opened (via WebFetch, or via the `r.jina.ai` text-extraction proxy when a gov.uk
PDF's binary/compressed stream defeated WebFetch's own parser — both count as "opened," not
recalled). No code was written or modified; this is a research document only.

## What's genuinely confirmed vs what needs a follow-up session

**Solidly confirmed, read from primary sources this session:**
- LCRM's actual 4-part structure (Before You Start / Stage 1 Risk Assessment / Stage 2 Options
  Appraisal / Stage 3 Remediation and Verification) and Stage 1's 3-tier structure (Preliminary /
  Generic Quantitative / Detailed Quantitative), including the direct quote "You must always start
  with a preliminary risk assessment" and "In England, Northern Ireland and Wales you must use
  C4SLs if available rather an SGV" — read from the live gov.uk LCRM Stage 1 page.
- C4SLs exist for exactly 6 substances from the original 2014 DEFRA/EA Phase 1 project (arsenic,
  benzene, benzo[a]pyrene, cadmium, chromium VI, lead); CL:AIRE (with SAGTA funding a Phase 2 since
  2018) now runs the C4SL programme, not DEFRA/EA directly — confirmed from claire.co.uk's own C4SL
  project page.
- SGVs are frozen: the EA is not publishing new ones, and the surviving (non-withdrawn) SGV reports
  only cover arsenic, cadmium, selenium, benzene/toluene/ethylbenzene/xylene, dioxins/furans/dl-PCBs
  and phenol, all dated 2009 or earlier — confirmed directly from CL:AIRE's own SGV listing page.
- The screening-criteria hierarchy (C4SL preferred > LQM/CIEH S4UL > SGV, with margin-of-exposure
  as a fallback when no published value exists) — read from an EA/Defra "Information Sheet 2:
  Generic screening criteria" PDF (via jina proxy).
- RTM's 4-level tiered structure (Level 1 pore-water/no attenuation → Level 2 unsaturated-zone
  attenuation → Level 3 aquifer attenuation → Level 4 receptor dilution) and its explicit,
  quoted distinction from ConSim ("ConSim starts with a concentration in the soil/ground and
  predicts an impact down the pathway... whereas the remedial targets methodology defines an
  acceptable environmental standard at a receptor and works back") — read directly from the 2006
  EA RTM document (GEHO0706BLEQ-E-E) via the jina proxy, including that it supersedes 1999's R&D
  Publication 20.
- The current (2016-established, last updated 31 July 2026 per the gov.uk page metadata) EA
  groundwater-risk-assessment-for-environmental-permits guidance names ConSim and LandSim as the
  EA's own probabilistic tools, and does NOT itself cite RTM by name on that particular page —
  read directly from the live gov.uk guidance page.
- LIT-10419 ("Modelling: surface water pollution risk assessment") is EXPLICITLY WITHDRAWN — the
  document's own withdrawal notice, read directly, states "This guidance has been withdrawn because
  it contains information that is out of date" and tells users to contact the EA directly; no named
  replacement is given within the withdrawn document itself. This is a real, current gap: FateIntel
  should NOT treat LIT-10419's modelling content as current EA methodology.
- UKHSA's actual role in contaminated land: read directly from a UKHSA-authored gov.uk factsheet
  (updated 31 Oct 2024) that UKHSA "does not have a specific statutory role in relation to
  contaminated land but plays an advisory role" — this CONTRADICTS the framing in this task's brief
  that UKHSA is "now" the publisher of SGVs/C4SLs. The primary source found says UKHSA/its
  predecessors (PHE, HPA) provide toxicological *input* (health criteria values feeding CLEA), while
  actual publication of SGVs/C4SLs has historically been DEFRA/EA (SGVs, 2009-era) then CL:AIRE/
  SAGTA (C4SL Phase 2, ongoing). This distinction matters for provenance metadata and should not be
  quietly "corrected" back to the brief's assumption without a further check.
- Cefas Action Level 1/Action Level 2 numeric table (As, Hg, Cd, Cu, Pb, Zn, plus PAH and PCB(ICES7)
  entries) and the "no concern below AL1 / further consideration AL1–AL2 / generally unsuitable
  above AL2" decision logic — read directly from the live gov.uk "Marine licensing: Sediment
  Analysis and sample plans" guidance page. Note: full metal suite listed by the page includes As,
  Hg, Cd, Cr, Cu, Ni, Pb, Zn plus organotins (TBT/DBT/MBT), PCBs (two methods), PAHs, DDT, dieldrin,
  but the AL2 organics values were not printed in the WebFetch extraction — flagged unconfirmed
  below, needs a direct re-check.
- Radioactive contaminated land is NOT a wholly separate statute — it is Part 2A of the
  Environmental Protection Act 1990, EXTENDED in 2006–2007 (transposing Directive 96/29/Euratom) to
  cover radioactivity, with its own dose-based harm thresholds (3 mSv/year effective dose, or 15
  mSv/year to the eye lens) distinct from the chemical contaminated-land harm criteria — read
  directly from two EA briefing notes (LIT_7924, LIT_7921, both dated 2012/2014) via the jina proxy.
  **These EA briefings are 12+ years old**; their continued currency was not independently
  re-verified this session and should be treated as needing a freshness check, not as confirmed
  current guidance.
- M-BAT (developed by WCA Environment; Excel-based; simplified Biotic Ligand Model for copper,
  zinc, manganese, nickel; needs site pH, DOC, and calcium as inputs) — this was NOT read directly
  from the PDF (wfduk.org returned a bot-verification wall to every fetch attempt, including via
  jina and via the browser tool), so this characterization rests on a WebSearch tool summary that
  appears to quote the method statement's own text ("M-BAT is an algorithm-based tool... developed
  by wca environment based on the bio-met database"). **This is a meaningfully weaker source than
  everything else in this document** — it is a search-engine snippet of a primary source, not the
  primary source itself opened and read. Flagged explicitly; a follow-up session should find a
  non-wfduk.org mirror or use an authenticated/different browser path to actually open the PDF.
- bio-met.net (the current BLM-based tool, successor/parallel resource to M-BAT, v6 released March
  2026, free access, covers Cu/Ni/Zn/Pb/Co) — read directly from the live bio-met.net homepage.
  Its relationship to M-BAT specifically (same underlying science, different org/interface) is
  inferred from both being BLM-based tools for the same UK bioavailable-EQS use case, not from an
  explicit statement on either site connecting them — flagged as inference, not confirmed fact.
- SoBRA's groundwater vapour GAC (GACgwvap) — 66 volatile substances, first published 2017, updated
  September 2024, built on the EA's own CLEA model to back-calculate a shallow-groundwater
  concentration tolerable for vapour intrusion — confirmed via WebSearch summaries quoting the
  SoBRA report's own methodology section; the full PDF itself was not opened this session (SoBRA's
  PDF is served through a WordPress download-gate URL that wasn't fetched) — flagged as
  search-snippet-sourced, follow-up should open the actual report PDF.
- The WFD (Standards and Classification) Directions 2015 EQS table structure and specific
  bioavailable metal numbers (nickel 4 µg/l inland-bioavailable / 8.6 µg/l other-surface-water;
  lead 1.2/1.3 µg/l; manganese 123 µg/l; copper and manganese computed via the M-BAT/UKTAG tool
  rather than a flat number) — read directly from the legislation.gov.uk Directions PDF via jina.
  **Caveat**: this is the 2015 Directions text; whether it has since been amended (post-Brexit
  Directions updates, e.g. new PFAS/priority-substance additions referenced elsewhere as "from 22
  December 2018") was not independently traced to a consolidated current version — a follow-up
  should pull the current consolidated Directions (there have been at least 2015, 2019 amendment
  rounds referenced in secondary sources) rather than relying on the 2015 text as if it were still
  the final word.
- CIRIA C781 ("Contaminated sediments: a guide for risk assessment and management", 2019) exists
  and is the current dedicated UK sediment-risk guidance (navigation dredging, harbours, coastal
  landfills; adaptive management framework) — confirmed it exists and its scope from CIRIA's own
  and NBS's publication-index listings, but **the document itself is paywalled** (CIRIA sells it as
  a book; no free PDF found) — its actual methodology/thresholds were NOT read and are NOT claimed
  here. This is a real gap, not filled with invented content.
- CIRIA C552 ("Contaminated land risk assessment: a guide to good practice", 2001) — same
  paywall situation; existence and high-level scope (risk categories via
  severity x likelihood matrix) confirmed via secondary description only, primary text not read.

**Explicitly NOT confirmed — do not build against these without a follow-up session:**
- Exact current CLEA software version number (search results gave conflicting/stale-looking
  "1.05/1.06/1.071" references from a third-party consultancy page, not from the EA/UKHSA
  themselves) — unconfirmed, needs the actual current CLEA download page checked directly.
- Whether UKHSA issues something formally called "Toxicological Guidance Values (TGVs)" as a
  distinct current product — searched directly, found no primary UKHSA document using that exact
  term this session. Do not assume TGV is UKHSA's current terminology without checking further.
- Full numeric Cefas AL2 values for organics (PAHs, PCBs, organotins, DDT, dieldrin) — AL1 numbers
  for PAH (0.1) and PCB-ICES7 (0.01) were captured but AL2 organics figures were not visible in the
  extracted text.
- Whether the EA has published a live replacement for the withdrawn LIT-10419 surface-water
  modelling guidance, versus surface-water risk assessment now living entirely inside the generic
  "Risk assessments for your environmental permit" collection and the H1/H1 Annex tool suite. The
  H1 tool's own current technical annexes (e.g. H1 Annex D2 for sanitary/other pollutants) were
  located by URL but not opened and read this session.
- SEPA (Scotland) and NIEA (Northern Ireland) equivalents to LCRM/CLEA/C4SL — SEPA's "Technical
  concepts" page surfaced in search results but was not opened; Scotland/NI-specific divergences
  from the England/Wales LCRM+CLEA+C4SL stack are unverified and likely non-trivial (Scotland's
  contaminated land regime has historically differed procedurally). Out of scope for this pass but
  worth flagging since "UK" in the brief could be read as encompassing all four nations.
- Whether ConSim and LandSim are still the current versions/tools in active EA use in 2026, versus
  legacy tools kept referenced in older guidance pages — the live 2026-updated gov.uk groundwater
  guidance page does name them, which is reasonably strong evidence of currency, but no direct
  ConSim vendor/product page was opened to confirm active maintenance/licensing status.

---

## 1. Land Contamination Risk Management (LCRM) — overarching framework

| Field | Detail |
|---|---|
| CONTAMINANT FAMILY | All (framework-level, contaminant-agnostic) |
| ASSESSMENT PURPOSE | Statutory/regulatory risk management of land contamination (Part 2A EPA 1990 and planning-regime contaminated land) |
| ENVIRONMENTAL COMPARTMENT | Soil, controlled waters (groundwater + surface water), ground gas |
| TIER | Framework spans all tiers: Stage 1 itself has 3 internal tiers (Preliminary / Generic Quantitative / Detailed Quantitative Risk Assessment) |
| MODEL/TOOL NAME | LCRM (Land Contamination Risk Management) — Before You Start, Stage 1 Risk Assessment, Stage 2 Options Appraisal, Stage 3 Remediation and Verification |
| REQUIRED INPUTS | Desk study/site walkover data (Tier 1); site investigation contaminant concentration data compared to generic assessment criteria (Tier 2); site-specific exposure/fate parameters for bespoke modelling (Tier 3) |
| OUTPUTS | Conceptual site model; classification of pollutant linkages; risk-based decision on whether remediation is needed; (Stage 2) shortlisted/selected remediation option; (Stage 3) verification report |
| REGULATORY STATUS | Current. Published/last updated 12 June 2025 per the gov.uk page. Supersedes CLR11 (2004) — the brief's premise is confirmed. |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Native-buildable at Tier 1/2 (conceptual site model logic, GAC comparison workflow); Tier 3 detailed quantitative modelling is external-handoff (site-specific fate/transport modelling, typically bespoke consultancy work) |
| SCREENING/REFINEMENT/REGULATORY | All three — Tier 1/2 are screening/refinement, the whole LCRM output feeds directly into statutory Part 2A / planning-condition regulatory decisions |
| LIMITATIONS | Framework only — does not itself contain numeric criteria; those come from CLEA/C4SL/SGV/GAC (see below). England/Wales-focused; Scotland/NI equivalents not verified this session. |
| SOURCE URL | https://www.gov.uk/government/publications/land-contamination-risk-management-lcrm/lcrm-stage-1-risk-assessment and https://www.gov.uk/government/publications/land-contamination-risk-management-lcrm/lcrm-stage-2-options-appraisal (both read directly) |

---

## 2. CLEA / SGV / C4SL / S4UL — human-health soil exposure criteria stack

| Field | CLEA (the model) | SGV (Soil Guideline Values) | C4SL (Category 4 Screening Levels) | S4UL (LQM/CIEH Suitable 4 Use Levels) |
|---|---|---|---|---|
| CONTAMINANT FAMILY | Framework — any contaminant with a toxicological health-criteria value | Arsenic, cadmium, selenium, benzene, toluene, ethylbenzene, xylene, dioxins/furans/dl-PCBs, phenol only (surviving non-withdrawn reports) | Arsenic, benzene, benzo[a]pyrene, cadmium, chromium VI, lead (Phase 1, 2014); Phase 2 (SAGTA-led, since 2018) adds more — 9 of 19 planned substances completed per claire.co.uk, PFAS added as a 20th target after 2023 EA funding | 89 substances per the LQM/CIEH report found in search (metals, TPH, PAHs, explosives, etc.) |
| ASSESSMENT PURPOSE | Forward exposure modelling (soil contaminant conc. → dose → health-based screening value) for human-health risk under Part 2A/LCRM | Minimal-risk generic screening value, legacy | "Low risk" generic screening value — deliberately less conservative than SGV/minimal-risk, "strongly precautionary" but pragmatic | Generic screening value filling gaps where no SGV/C4SL exists |
| ENVIRONMENTAL COMPARTMENT | Soil (direct ingestion, dermal contact, inhalation of dust/vapour, homegrown produce ingestion — exposure pathways per the CLEA model's known scope; not independently re-verified pathway-by-pathway from a CLEA technical manual this session, this characterization is carried from the brief's own framing and cross-checked only against general secondary descriptions) | Soil | Soil | Soil |
| TIER | Screening (Tier 1/2 generic criteria within LCRM) | Screening | Screening — LCRM's preferred first-choice screening value | Screening — secondary preference after C4SL |
| MODEL/TOOL NAME | CLEA software/model | SGV reports (per-substance) | C4SL reports (per-substance) | LQM/CIEH S4UL reports |
| REQUIRED INPUTS | Land-use scenario (residential w/ or w/o plant uptake, allotment, commercial/industrial), exposure duration/frequency assumptions, toxicological health criteria value, soil organic matter content | (built into the published value) | (built into the published value; uses a "low level of toxicological concern" (LLTC) approach per Information Sheet 2) | (built into the published value; uses a health criteria value (HCV) approach) |
| OUTPUTS | Generic assessment criteria (a soil concentration threshold) per land use | Single soil conc. threshold per substance/land-use | Single soil conc. threshold per substance/land-use (less conservative than SGV) | Single soil conc. threshold per substance/land-use |
| REGULATORY STATUS | Current, actively required by LCRM Stage 1 | Frozen/legacy — EA confirmed (per CL:AIRE's own SGV page) not publishing new SGVs; all current SGV reports date 2009 or earlier, pre-2009 ones withdrawn | Current, actively growing (Phase 2 ongoing) | Current, industry-standard fill-in |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | External-handoff for full CLEA modelling (proprietary Excel/software tool with EA/UKHSA-derived toxicological inputs); native-buildable if FateIntel just needs to *apply* already-published SGV/C4SL/S4UL numbers as lookup criteria (not re-derive them) | Native-buildable as lookup table | Native-buildable as lookup table | Native-buildable as lookup table (subject to LQM/CIEH licensing terms on the report itself — not checked this session) |
| SCREENING/REFINEMENT/REGULATORY | Screening/Regulatory (values feed directly into Part 2A determinations) | Screening/Regulatory | Screening/Regulatory (LCRM: "must use C4SLs if available") | Screening/Refinement |
| LIMITATIONS | Full model/algorithm derivation not independently re-verified against a CLEA technical manual this session (see honesty section) | Very limited substance coverage, dated methodology (pre-2009 withdrawn as based on superseded 2002 framework) | Only 6 Phase-1 substances have LEGALLY preferred status per LCRM's explicit wording; Phase 2 substances' regulatory standing not separately confirmed | Not a government-published value — industry/LQM-CIEH-authored; UKHSA's role is advisory input, not primary publisher, per this session's UKHSA factsheet read |
| SOURCE URL | https://www.gov.uk/government/publications/land-contamination-risk-management-lcrm/lcrm-stage-1-risk-assessment | https://claire.co.uk/component/content/article/soil-guideline-values.html?catid=417&showall=1&Itemid=146 | https://claire.co.uk/projects-and-initiatives/category-4-screening-levels | Existence/89-substance figure via WebSearch summary of LQM/CIEH report (secondary characterization; report itself not opened this session — flag for follow-up) |

---

## 3. Remedial Targets Methodology (RTM) and ConSim — groundwater risk assessment

| Field | Detail |
|---|---|
| CONTAMINANT FAMILY | Framework-level — any soil/groundwater contaminant threatening controlled waters |
| ASSESSMENT PURPOSE | Derive remedial targets / assess risk to groundwater and surface water receptors from contaminated soil/groundwater sources |
| ENVIRONMENTAL COMPARTMENT | Groundwater (with a defined path to surface water/abstraction receptors) |
| TIER | 4-level tiered structure: Level 1 (pore water, no attenuation, most conservative) → Level 2 (unsaturated-zone attenuation + groundwater dilution) → Level 3 (aquifer/saturated-zone attenuation to a downgradient compliance point) → Level 4 (dilution at receiving watercourse/abstraction) |
| MODEL/TOOL NAME | RTM ("Remedial Targets Methodology: Hydrogeological Risk Assessment for Land Contamination", EA, 2006, product code GEHO0706BLEQ-E-E) — an analytical/deterministic methodology; **ConSim** is a separate, EA-associated probabilistic (Monte Carlo) software tool solving the same underlying transport equations but running the calculation in the opposite direction (source-forward vs receptor-backward) |
| REQUIRED INPUTS | Source concentration/extent, hydraulic conductivity, groundwater velocity/gradient, soil porosity/bulk density/organic carbon content, partition coefficients (Koc), Henry's Law constants (for volatiles), receptor location/type, distance to compliance point |
| OUTPUTS | RTM: a remedial target concentration at source that will not exceed a standard at the receptor. ConSim: probabilistic frequency-curve output (distribution of predicted receptor-point concentrations, not a single point estimate) |
| REGULATORY STATUS | RTM (2006) is current and explicitly supersedes 1999's R&D Publication 20; it is the framework the current (2016, updated through 31 July 2026 per gov.uk metadata) EA groundwater-permit guidance points toward for tiered risk assessment logic, though that specific live guidance page's own text (as fetched) names ConSim/LandSim as the EA's probabilistic tools without citing "RTM" by name on that page — treat RTM as still current but confirm the live guidance's exact citation chain in a follow-up. |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | RTM's Level 1/2 analytical equations are native-buildable (published, deterministic formulas). ConSim itself (proprietary EA-commissioned probabilistic software) is external-handoff-only unless/until FateIntel builds its own equivalent Monte Carlo layer over the same analytical solutions RTM publishes. |
| SCREENING/REFINEMENT/REGULATORY | Screening (Level 1) through Regulatory (used directly to set remediation targets accepted by the EA) |
| LIMITATIONS | 2006 document is now 20 years old; whether all its default parameter values (e.g. any default Kd/Koc tables) remain EA-endorsed vs superseded by newer chemical-specific data was not checked. ConSim's current commercial/licensing/maintenance status was not independently verified (no vendor page opened). |
| SOURCE URL | https://assets.publishing.service.gov.uk/media/5a7e2570e5274a2e8ab46226/geho0706bleq-e-e.pdf (read via jina proxy) and https://www.gov.uk/guidance/groundwater-risk-assessment-for-your-environmental-permit (read directly) |

---

## 4. Environment Agency surface-water pollution risk assessment

| Field | Detail |
|---|---|
| CONTAMINANT FAMILY | Framework-level — hazardous substances discharged to surface water (point-source, from permitted installations/discharges) |
| ASSESSMENT PURPOSE | Assess risk of surface-water EQS exceedance / receiving-water deterioration from a permitted discharge (environmental permitting, "H1" risk assessment) |
| ENVIRONMENTAL COMPARTMENT | Surface water (freshwater rivers/lakes and tidal/coastal waters) |
| TIER | Not independently re-derived this session beyond what LIT-10419 (withdrawn) described: initial dilution calculation → simple plume model → complex hydrodynamic modelling (tidal/coastal); Monte Carlo software for freshwater EQS/deterioration/effluent-quality testing |
| MODEL/TOOL NAME | H1 risk assessment tool / "Risk assessments for your environmental permit" (current, gov.uk collection) is the live pointer; **LIT-10419 ("Modelling: surface water pollution risk assessment") is explicitly WITHDRAWN** ("contains information that is out of date," EA's own words, dated content marked © 2014) |
| REQUIRED INPUTS | (from the withdrawn LIT-10419, for historical/contextual value only) discharge concentration data (incl. handling of "less than"/non-detect values), receiving-water flow/dilution characteristics, EQS values to test against |
| OUTPUTS | Risk rating for source-pathway-receptor linkages (per WebSearch-sourced characterization of the EA's approach — not independently confirmed against a live primary methodology document this session); compliance/non-compliance against EQS |
| REGULATORY STATUS | **This is a live regulatory gap as of this session**: the last substantive EA surface-water modelling methodology document found (LIT-10419) is formally withdrawn with no named replacement inside the withdrawal notice itself. Current guidance appears to live inside the general "Risk assessments for your environmental permit" collection and the H1 tool/Annex suite (e.g. H1 Annex D2 for sanitary/other pollutants), but those specific documents were not opened and read this session. |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Unconfirmed pending follow-up — cannot responsibly classify without reading the current live methodology document |
| SCREENING/REFINEMENT/REGULATORY | Regulatory (feeds environmental permit decisions) |
| LIMITATIONS | **Do not build against LIT-10419's content as if current.** This is the single clearest "needs a follow-up session" item in this whole document for compartment 4 — the current live methodology was not located and read this session. |
| SOURCE URL | https://assets.publishing.service.gov.uk/media/68518c88cf42a58f50cac9bb/Withdrawn_LIT-10419.pdf (read via jina proxy; withdrawal notice confirmed directly) |

---

## 5. UK Environmental Quality Standards (EQS) and bioavailable EQS for metals

| Field | Detail |
|---|---|
| CONTAMINANT FAMILY | Priority substances and specific pollutants under the Water Framework Directive — metals (Cd, Pb, Hg, Ni + UK-specific Cu/Zn/Mn as "specific pollutants"), PAHs, organochlorines (DDT), pesticides (atrazine, diuron, isoproturon, cypermethrin), industrial chemicals (DEHP, tributyltin), PFOS, dioxins |
| ASSESSMENT PURPOSE | WFD ecological/chemical status classification of surface waters; compliance assessment against legally-binding standards |
| ENVIRONMENTAL COMPARTMENT | Surface water (inland + "other" i.e. transitional/coastal), with separate biota standards for some substances |
| TIER | Regulatory (this is the compliance standard itself, not a screening tool) — though a tiered *compliance assessment approach* exists for bioavailable metals, described below |
| MODEL/TOOL NAME | The Water Framework Directive (Standards and Classification) Directions 2015 — retained-EU-law legal instrument, current UK home of EQS values post-Brexit (via the Water Environment (WFD)(England and Wales) Regulations 2017, which retained WFD/Groundwater Directive/EQS Directive transposition) |
| REQUIRED INPUTS | Monitored ambient concentration (dissolved fraction, for bioavailable metals) | 
| OUTPUTS | Pass/fail against Annual Average (AA-EQS) and Maximum Allowable Concentration (MAC-EQS) values per substance |
| REGULATORY STATUS | Current as retained EU law; **caveat**: verified against the 2015 Directions text specifically — whether a more recent consolidated amendment exists (secondary sources referenced a "from 22 December 2018" addition of PFOS/dioxins/cypermethrin, suggesting at least one amendment round) was not traced to its own primary text this session |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Native-buildable as a lookup table (EQS values are published numbers) |
| SCREENING/REFINEMENT/REGULATORY | Regulatory |
| LIMITATIONS | Full 45-substance table was not exhaustively transcribed this session — only bioavailable-metal figures were pulled out. A follow-up should extract the complete Table 1 for FateIntel's reference data. |
| SOURCE URL | https://www.legislation.gov.uk/uksi/2015/1623/pdfs/uksiod_20151623_en_003.pdf (read via jina proxy) |

**Confirmed numeric bioavailable-metal EQS values (from the 2015 Directions, as extracted):**

| Metal | Bioavailable EQS | Compartment | Method |
|---|---|---|---|
| Nickel | 4 µg/l | Inland surface waters | Bioavailable (M-BAT/BLM-adjusted) |
| Nickel | 8.6 µg/l | Other surface waters | Bioavailable |
| Lead | 1.2 µg/l | Inland | Bioavailable |
| Lead | 1.3 µg/l | Other surface waters | Bioavailable |
| Manganese | 123 µg/l | (compartment not separately distinguished in extraction) | Bioavailable, via UKTAG tool |
| Copper | Not a flat number — determined via UKTAG M-BAT formula, varies with DOC | — | Bioavailable, formula-based |
| Zinc | Ambient Background Concentration subtracted, 1.2–7.1 µg/l range by catchment (Add-As-Backgrounds approach) | Varies by catchment | Bioavailable |

Cross-check consistency note: an independent secondary source (ScienceDirect abstract found via
search) separately quoted "1 µg/l bioavailable Cu, 10.9 µg/l bioavailable Zn, 123 µg/l bioavailable
Mn" as UK specific-pollutant EQS figures — the manganese figure (123 µg/l) matches exactly between
the primary Directions text and this secondary source, which is reassuring corroboration, but the
copper/zinc figures from that secondary source were not independently re-verified against the
primary Directions PDF text itself this session (the Directions text described copper/zinc as
formula-derived rather than flat numbers, which may just mean the secondary source is quoting a
worked example rather than a flat statutory number — this inconsistency is unresolved, flag for
follow-up).

---

## 6. M-BAT and bio-met — metal bioavailability assessment tools

| Field | M-BAT | bio-met |
|---|---|---|
| CONTAMINANT FAMILY | Copper, zinc, manganese, nickel (not lead — per WebSearch-sourced characterization) | Copper, nickel, zinc, lead, cobalt |
| ASSESSMENT PURPOSE | Convert site water chemistry (pH, DOC, hardness/Ca) into a site-specific bioavailable PNEC or % of EQS, for WFD compliance assessment (Tier 2/3 of the compliance tiering) | Same underlying purpose — BLM-based bioavailability assessment for WFD compliance, apparently a newer/parallel/successor tool |
| ENVIRONMENTAL COMPARTMENT | UK freshwaters | Freshwater aquatic environment, explicitly framed around the EU/UK WFD |
| TIER | Tier 2/3 of a tiered compliance-assessment approach (per a secondary/search-sourced characterization — "Tier 3... compares observed concentrations with a bioavailable PNEC derived from biotic ligand models") | Not independently characterized against a tiering scheme this session |
| MODEL/TOOL NAME | M-BAT (Metal Bioavailability Assessment Tool) | bio-met (v6, released March 2026 per the live site) |
| REQUIRED INPUTS | Site pH, DOC, calcium (hardness); optionally dissolved metal concentration | Not independently confirmed — presumably similar BLM inputs (water chemistry) but this session's read of bio-met.net's homepage did not itemize exact input fields |
| OUTPUTS | Site-specific bioavailable PNEC, or bioavailable fraction of a measured concentration | BLM-based bioavailability assessment output (exact output format not confirmed) |
| REGULATORY STATUS | Current — is the UKTAG-endorsed simplified-BLM tool cited directly inside the 2015 WFD Directions' copper/manganese EQS methodology | Current, actively maintained (v6, March 2026 — very recent, strong currency signal) |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Native-buildable IF the underlying simplified-BLM algorithm/coefficients can be obtained from a readable copy of the method statement (not achieved this session — see below) | Same caveat — underlying BLM science not independently extracted this session |
| SCREENING/REFINEMENT/REGULATORY | Refinement/Regulatory (feeds directly into statutory WFD compliance determination) | Same |
| LIMITATIONS | **Could not open the actual M-BAT method statement PDF this session** — wfduk.org returned a bot-verification wall to WebFetch (direct and via jina proxy) and to the browser tool. Everything above is derived from a WebSearch snippet that appears to quote the document's own text, not from the document itself. This is the weakest-sourced entry in this whole matrix and needs a dedicated follow-up (try an authenticated browser session, a different network path, or search for a non-wfduk.org mirror/citation of the method statement's actual algorithm). | Read directly from the live bio-met.net homepage; deeper technical/algorithm pages on that site were not explored this session. |
| SOURCE URL | https://www.wfduk.org/resources/rivers-lakes-metal-bioavailability-assessment-tool-m-bat (NOT successfully opened — bot-blocked; characterization is WebSearch-snippet-sourced only) | https://bio-met.net/ (read directly) |

---

## 7. Cefas action levels — marine sediment / dredged material disposal

| Field | Detail |
|---|---|
| CONTAMINANT FAMILY | Metals (As, Hg, Cd, Cr, Cu, Ni, Pb, Zn) and organics (organotins TBT/DBT/MBT, PCBs [two assessment methods, incl. ICES7], PAHs, DDT, dieldrin) |
| ASSESSMENT PURPOSE | Weight-of-evidence decision support for marine licensing of dredged material disposal at sea (NOT a statutory pass/fail standard by itself) |
| ENVIRONMENTAL COMPARTMENT | Marine/estuarine sediment |
| TIER | Two-level screening: AL1 (no concern) / between AL1–AL2 (further testing, e.g. bioassays) / above AL2 (generally unsuitable for sea disposal) |
| MODEL/TOOL NAME | Cefas Guideline Action Levels for the Disposal of Dredged Material |
| REQUIRED INPUTS | Sediment contaminant concentration (mg/kg dry weight), compared also against local geological background levels |
| OUTPUTS | Categorical decision-support flag (no concern / further consideration / generally unsuitable), feeding into a broader marine licensing weight-of-evidence decision alongside bioassays and site history |
| REGULATORY STATUS | Current in practice (actively used in gov.uk marine licensing guidance and cited on live consultation documents this session) but the numeric action levels themselves reportedly date to 1994 (per an unopened MDPI paper's abstract found in search, "Reviewing the UK's Action Levels for the Management of Dredged Material" — this specific claim about the 1994 origin was NOT independently confirmed by opening that paper, which returned HTTP 403; flagged) |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Native-buildable — the AL1/AL2 thresholds are simple published numeric criteria, well suited to a lookup-table implementation |
| SCREENING/REFINEMENT/REGULATORY | Screening (explicitly NOT a statutory standard — "not statutory contaminant concentrations... used as part of a weight of evidence approach," per the EA/Cefas framing found in search) feeding a regulatory licensing decision |
| LIMITATIONS | AL2 numeric values for the organic contaminants (PAHs, PCBs, TBT, DDT, dieldrin) were not captured in this session's extraction — only AL1 organics values (PAH 0.1, PCB-ICES7 0.01 mg/kg) came through; a follow-up should re-fetch the full table. The "action levels set in 1994, arguably outdated" critique is a real, professionally-published concern (MDPI paper title itself signals this) but the paper's actual content/recommendations were not read this session (403 error). |
| SOURCE URL | https://www.gov.uk/guidance/marine-licensing-sediment-analysis-and-sample-plans (read directly) |

**Confirmed numeric values (mg/kg dry weight), as extracted from the live gov.uk guidance page:**

| Contaminant | AL1 | AL2 |
|---|---|---|
| Arsenic | 20 | 100 |
| Mercury | 0.3 | 3 |
| Cadmium | 0.4 | 5 |
| Copper | 40 | 400 |
| Lead | 50 | 500 |
| Zinc | 130 | 800 |
| PAHs | 0.1 | not captured — follow-up needed |
| PCBs (ICES 7) | 0.01 | not captured — follow-up needed |
| Chromium, Nickel, organotins (TBT/DBT/MBT), DDT, dieldrin | listed as covered contaminants but numeric AL1/AL2 not captured in this extraction | — |

---

## 8. Contaminated groundwater and contaminated sediment — general UK approaches

| Field | Groundwater (general) | Sediment (freshwater/estuarine, non-marine-disposal context) |
|---|---|---|
| CONTAMINANT FAMILY | All | All |
| ASSESSMENT PURPOSE | Risk to controlled-water receptors (drinking water abstraction, groundwater-dependent ecosystems) | Risk to aquatic ecology and human health from contaminated bed sediment (navigation dredging, harbours, contaminated waterways, coastal landfills) |
| ENVIRONMENTAL COMPARTMENT | Groundwater | Freshwater/estuarine sediment |
| TIER | See RTM/ConSim above (section 3) | Adaptive management framework (per CIRIA C781's own description, not independently verified — see below) |
| MODEL/TOOL NAME | RTM + ConSim + LandSim (section 3); LCRM Stage 1 Tier 1–3 for the land-contamination angle | CIRIA C781 ("Contaminated sediments: a guide for risk assessment and management", 2019); CIRIA C552 (2001, general contaminated-land risk assessment, includes a severity x likelihood risk-category matrix) for older/broader context |
| REQUIRED INPUTS | See section 3 | Not confirmed — C781 not opened |
| OUTPUTS | See section 3 | Not confirmed — C781 not opened |
| REGULATORY STATUS | Current (section 3) | C781 (2019) appears to be the current dedicated UK sediment guide, superseding/supplementing older approaches; **the document itself was not read (paywalled by CIRIA)** |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Mixed, see section 3 | Cannot classify responsibly without reading the actual methodology — flagged unconfirmed |
| SCREENING/REFINEMENT/REGULATORY | Mixed, see section 3 | Unconfirmed |
| LIMITATIONS | — | **Important finding, worth flagging explicitly**: one secondary source stated plainly that "sediment quality standards (EQSs) are only applicable in the water column and there are no equivalent [WFD-legal] standards for sediments used in the UK" — i.e., unlike the water-column EQS regime (section 5), there does not appear to be a UK statutory numeric sediment quality standard outside the Cefas marine-disposal action levels (section 7); freshwater/estuarine sediment risk assessment instead relies on guidance frameworks (CIRIA C781/C552) rather than legally-binding thresholds. This was not independently confirmed against a primary EA/Defra statement this session but is a plausible and specific enough claim to flag as a likely real gap worth a dedicated follow-up search. |
| SOURCE URL | See section 3 | Existence/scope only: https://www.ciria.org/ItemDetail?iProductcode=C781&Category=BOOK and https://www.thenbs.com/PublicationIndex/documents/details?DocID=325149&Pub=CIRIA (neither opened for full text — paywalled) |

---

## 9. Generic Assessment Criteria (GAC) for TPH, chlorinated solvents/VOCs, and cyanide

| Field | TPH (petroleum hydrocarbons) | Chlorinated solvents / VOCs (vapour pathway) | Cyanide |
|---|---|---|---|
| CONTAMINANT FAMILY | Petroleum hydrocarbons (fraction-based, per TPHCWG-style banding referenced in CL:AIRE's guidance) | Chlorinated solvents and other volatile organic contaminants in groundwater | Inorganic (free/simple) cyanide in soil |
| ASSESSMENT PURPOSE | Human-health and controlled-waters risk screening for petroleum-contaminated soil/groundwater | Human-health risk screening for vapour intrusion from contaminated groundwater into indoor/outdoor air | Human-health risk screening (soil ingestion pathway) |
| ENVIRONMENTAL COMPARTMENT | Soil and groundwater | Groundwater → vapour → indoor/outdoor air | Soil |
| TIER | Screening (GAC), refinable to detailed quantitative modelling | Screening (GAC), built on CLEA | Screening (GAC) |
| MODEL/TOOL NAME | (a) CL:AIRE "Petroleum Hydrocarbons in Groundwater" guidance (Shell-led steering group, reviewed by EA/NRW/NIEA, SoBRA-supported); (b) CL:AIRE/AGS/EIC "Soil Generic Assessment Criteria for Human Health Risk Assessment" (Jan 2010) | SoBRA "Development of Generic Assessment Criteria for Assessing Vapour Risks to Human Health from Volatile Contaminants in Groundwater" (GACgwvap) — 66 substances, orig. 2017, updated Sept 2024 | CL:AIRE/AGS/EIC Soil GAC (2010) — includes inorganic cyanide, receptor scenario reportedly built around a 3-year-old child (per search-sourced characterization) |
| REQUIRED INPUTS | Fraction-speciated TPH data (aliphatic/aromatic carbon-number bands); land-use scenario | Groundwater concentration; CLEA-based exposure/land-use scenario (residential/commercial) | Soil concentration; land-use/receptor scenario |
| OUTPUTS | GAC per TPH fraction/land use; also a comparison against hazardous-waste classification thresholds for imported soil (per a search-sourced characterization) | GACgwvap — a shallow-groundwater concentration threshold tolerable for vapour-intrusion risk | GAC value (a WebSearch snippet cited "800 mg/kg" for cyanide in soil — **not independently confirmed against the primary 2010 CL:AIRE report itself this session**, flag as unconfirmed numeric claim) |
| REGULATORY STATUS | Current, industry-standard (CL:AIRE-published, EA-reviewed) | Current, actively maintained (2024 update) | Current but dated (2010; no confirmation of a more recent update found this session) |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Native-buildable as lookup criteria if the published GAC tables can be obtained (the actual GAC PDF, support.esdat.net mirror, returned HTTP 403 to WebFetch this session — not read) | Native-buildable as lookup criteria (SoBRA report itself not opened this session — WebSearch-snippet-sourced) | Native-buildable as lookup criterion, pending confirmation of the actual number |
| SCREENING/REFINEMENT/REGULATORY | Screening/Refinement | Screening/Refinement | Screening |
| LIMITATIONS | Neither the CL:AIRE petroleum-hydrocarbons-in-groundwater guidance nor the 2010 Soil GAC report was opened and read directly this session — both characterizations rest on WebSearch snippets. This is a real gap for a domain (TPH) central to the brief's stated scope; strongly recommend a follow-up session specifically to open these two CL:AIRE PDFs directly (try the jina proxy or a different mirror if claire.co.uk/support.esdat.net block direct fetch). | SoBRA's actual GAC report PDF not opened this session (download-gated URL) | The "800 mg/kg" cyanide figure is unconfirmed — treat as a lead to verify, not a fact to build against |
| SOURCE URL | Existence/scope only, via WebSearch: https://claire.co.uk/home/news-new/cl-aire-publishes-petroleum-hydrocarbons-in-groundwater-guidance.html and https://support.esdat.net/Environmental%20Standards/uk/gac-report_6.12.09b.pdf (403, not opened) | Existence/scope only, via WebSearch: https://sobra.org.uk/groundwater-vapour/development-of-generic-assessment-criteria-for-assessing-vapour-risks-to-human-health-from-volatile-contaminants-in-groundwater/ (not opened) | Same as TPH column, esdat.net mirror (403, not opened) |

---

## 10. Radiological / radionuclide contaminated land — is it a separate regime?

| Field | Detail |
|---|---|
| CONTAMINANT FAMILY | Radionuclides / radioactive contamination |
| ASSESSMENT PURPOSE | Identification and remediation of land where radioactivity causes prolonged human exposure above defined dose thresholds |
| ENVIRONMENTAL COMPARTMENT | Land (soil), with a distinct dose-based (not concentration-based) harm criterion |
| TIER | Not a tiered generic-criteria system like CLEA/C4SL — a dose-threshold determination (3 mSv/year effective dose, or 15 mSv/year equivalent dose to the eye lens, triggers "radioactive contaminated land" designation) |
| MODEL/TOOL NAME | Not a separate statute — Part 2A of the Environmental Protection Act 1990 was EXTENDED in 2006–2007 (implementing Directive 96/29/Euratom, the Basic Safety Standards Directive) to bring radioactive contamination within the same overall Part 2A framework, but with its own harm criteria and (for nuclear-licensed sites) a carve-out where ONR/ the Nuclear Installations Act 1965 liability regime applies instead |
| REQUIRED INPUTS | Radiation dose modelling (not chemical concentration-based exposure modelling) |
| OUTPUTS | Designation (or not) of land as "radioactive contaminated land"; remediation requirement on the "appropriate person" or the EA |
| REGULATORY STATUS | The framework itself (the 2006/2007 Part 2A extension) appears to remain the operative regime, but the two EA guidance documents read this session (LIT_7924, LIT_7921) date from 2012/2014 — 12+ years old, currency not re-verified |
| NATIVE-BUILDABLE OR EXTERNAL-HANDOFF-ONLY | Almost certainly external-handoff — radiological dose assessment is a fundamentally different discipline (health physics) from FateIntel's existing chemical fate/exposure modelling base, and this research pass did not surface evidence FateIntel should build native radiological capability |
| SCREENING/REFINEMENT/REGULATORY | Regulatory |
| LIMITATIONS | This answers the brief's Q9 directly: **UK does NOT have a wholly separate radiological contaminated-land statute** — it is a distinct, dose-based extension bolted onto the same Part 2A regime chemical contamination uses, with a clear institutional carve-out for nuclear-licensed sites (ONR) vs. everything else (EA/local authorities). Whether this remains accurate in 2026 (vs. e.g. having been further revised) was not re-checked against a document newer than 2014. |
| SOURCE URL | https://assets.publishing.service.gov.uk/media/5a7b8859ed915d131105fdc9/LIT_7924_904adc.pdf and https://assets.publishing.service.gov.uk/media/5a7c6d4ae5274a5590059ca3/LIT_7921_57c3f1.pdf (both read via jina proxy) |

---

## Cross-cutting notes for engineering follow-up

1. **The single highest-value follow-up action**: open the actual CL:AIRE petroleum-hydrocarbons
   and 2010 Soil GAC PDFs, and the SoBRA GACgwvap PDF, directly — these three cover exactly the
   contaminant families (TPH, chlorinated solvents, cyanide) the brief calls out by name, and this
   session could only characterize them via WebSearch snippets, not by reading the primary source.
2. **Second highest-value follow-up**: get past wfduk.org's bot wall for the M-BAT method statement
   — it's cited directly inside the legally-binding 2015 WFD Directions for copper/manganese EQS,
   so its actual algorithm matters if FateIntel wants to compute bioavailable EQS compliance
   natively rather than just pointing users to bio-met.net.
3. **A real, not cosmetic, regulatory-status gap surfaced this session**: LIT-10419 (surface-water
   pollution modelling) is formally withdrawn with no named replacement inside the withdrawal
   notice. Do not build FateIntel's UK surface-water discharge risk screening around LIT-10419's
   content. The live replacement (likely inside the H1 tool/Annex suite or the general "Risk
   assessments for your environmental permit" collection) needs to be located and read.
4. **The brief's assumption that "UKHSA now" publishes SGVs/C4SLs is not what the primary source
   says** — UKHSA is advisory (toxicological input), CL:AIRE/SAGTA runs C4SL, and SGVs are simply
   frozen/legacy with no current publisher actively issuing new ones. Metadata fields in any
   FateIntel data model for these values should credit CL:AIRE (C4SL) / DEFRA-EA (SGV, legacy) as
   publisher-of-record, with UKHSA/PHE/HPA as toxicological-input contributor, not primary
   publisher.
5. **Sediment quality lacks a UK statutory numeric standard outside the marine-disposal Cefas
   action levels** — this is a plausible, specific-enough claim from a secondary source to flag as
   a likely real gap in UK regulatory coverage, worth confirming directly with Defra/EA in a
   follow-up before FateIntel either builds or explicitly declines to build a sediment-criteria
   module.
