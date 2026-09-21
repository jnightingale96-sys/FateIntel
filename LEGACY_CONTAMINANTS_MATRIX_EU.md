# EU Regulatory/Model Matrix — Legacy & Inorganic Contaminants

Research pass for FateIntel's expansion into PCBs, heavy metals/metalloids, PAHs, legacy
organochlorine pesticides, dioxins/furans, organotins, petroleum hydrocarbons/BTEX,
chlorinated solvents/VOCs, cyanide, nutrients, and contaminated land/sediment/groundwater
assessment. Scope: EU-level frameworks plus Netherlands and Germany as national
contaminated-land examples. Compiled 2026-09-19.

---

## What's genuinely confirmed vs. what needs a follow-up session

**Directly read from primary legal/official text (EUR-Lex HTML, national legal gazette
sites, or the treaty secretariat's own site) in this session:**

- EU POPs Regulation (EU) 2019/1021 — consolidated EUR-Lex text (Article 1 objective,
  Annex I–V structure).
- Directive 2013/39/EU — EUR-Lex HTML (recitals 7/13/17, Article 3(2)/(3), Annex I Part B
  point 3 bioavailability clause, priority substance/biota EQS values).
- Water Framework Directive 2000/60/EC — EUR-Lex consolidated HTML (Article 16, Article
  2(21)/(24), Article 4(1)(a)(ii), Annex V).
- Euratom Basic Safety Standards Directive 2013/59/Euratom — EUR-Lex HTML (Article 1,
  2(1), 2(2)(d), 19).
- REACH Annex XVII, Entry 1 — UK's legislation.gov.uk retained-EU-law mirror of Regulation
  (EC) 1907/2006 Annex XVII (confirmed Entry 1 = "Polychlorinated terphenyls (PCTs)" only —
  **not** PCBs; and Entry 50 PAH text). Caveat below.
- Germany's Bundes-Bodenschutz- und Altlastenverordnung (BBodSchV 2023) — official text on
  gesetze-im-internet.de (structure, Vorsorge-/Prüf-/Maßnahmenwerte definitions, pathway
  tables, effective date).
- Stockholm Convention Annex A/B/C listing page on chm.pops.int (Secretariat's own site;
  confirms PCBs listed under Annex A *and* Annex C, dioxins/furans under Annex C only).
- Netherlands "Into Dutch Soils" official guidance (iplo.nl, the Dutch government's
  environment/planning information point) — read via an automated PDF summarizer, not
  full manual read-through; standard-soil correction figures were cross-checked against
  an independent RIVM PDF and the RIVM soil-risk portal (rvs.rivm.nl) which state 10%
  organic matter / 25% lutum — this is the number used below, overriding an initial
  conflicting "2%" read from the summarizer that is flagged as a probable extraction
  error.

**Confirmed via multiple independent secondary/tertiary sources but NOT verified against
a primary legal PDF/HTML I actually opened and read end-to-end — flagged unconfirmed:**

- CIS Guidance Document No. 38 ("Technical Guidance for implementing EQS for metals") —
  the PDF (128 pages, CIRCABC) could not be parsed by the fetch tool (returned raw binary).
  Its existence, general scope (bioavailability correction methodology for Ni/Pb/Cu/Zn
  using pH/hardness/DOC inputs) and its role as official Common Implementation Strategy
  guidance are corroborated by ResearchGate, WFD-UK, and bio-met documentation, but I have
  not personally verified its exact required-input list or equations. **Needs a follow-up
  session with a proper PDF-text extraction path** (download + local text extraction)
  rather than the WebFetch tool, which cannot read binary PDFs here.
- The specific BLM-based compliance tools "bio-met" and "M-BAT" (UKTAG) — description of
  what they compute and their Cu/Ni/Zn/Pb coverage is corroborated by bio-met.net and
  wfduk.org pages found in search, but I did not open bio-met.net's own methodology PDF
  line-by-line in this session.
- Exact scope of the EU (voluntary, pre-REACH) Risk Assessment Reports for copper, nickel
  and zinc under the old Existing Substances Regulation (793/93/EEC) — existence and
  general BLM linkage confirmed via secondary literature (Springer, IEAM), but I did not
  open the original European Chemicals Bureau (ECB) RAR PDFs themselves. **Needs
  follow-up**: locate current ECHA/JRC mirror of these RARs.
- Stockholm Convention Articles 3, 5, 8 exact operative text — I could not get the
  Secretariat's own convention-text page to render article-level text through WebFetch
  (it returned only navigation chrome), and ecolex.org 404'd. The Article 8/Annex
  D-E-F listing process (screening criteria → risk profile → risk management evaluation →
  COP listing) is corroborated by multiple independent secondary summaries (IISD ENB,
  sustainability-directory) and is consistent with well-established public knowledge of
  the Convention, but **the exact article text was not independently read this session —
  flagged unconfirmed at the clause level**, confirmed only at the mechanism level.
- MCCP / long-chain PFCAs / chlorpyrifos POPs Regulation Annex I amendment — as of
  2026-09-19 this is **still in the EU legislative pipeline**, not yet confirmed in force.
  A Council document dated 11 September 2026 (ST-13064-2026-INIT) suggests it is still
  moving through Council in September 2026, later than the "Q1 2026" trade-press estimate
  from the November 2025 Commission proposal. **Needs a follow-up EUR-Lex check** for the
  actual Official Journal publication before treating MCCPs as legally listed in Annex I.
- WFD/EQSD/Groundwater Directive recast (COM(2022)540, adding ~24 substances plus a PFAS
  group to Annex X) — secondary sources report European Parliament adoption 24 April 2024
  and Council formal adoption of an updated pollutant list on 17 February 2026, with a
  transposition deadline of December 2027. **I did not open the actual adopted directive
  text or its OJ citation** — flagged unconfirmed pending a direct EUR-Lex pull of the
  final adopted act and its Regulation/Directive number.
- REACH's non-applicability to in-situ historic contaminated land — this is a reasoned
  inference from two things I *did* verify directly: (a) REACH Annex XVII restrictions
  and Title II registration duties attach to substances "placed on the market" or
  manufactured/imported, and (b) Directive 2008/98/EC on waste (Article 2(1)(b),
  corroborated via EUR-Lex search snippet, not fully read) excludes "land (in situ),
  including unexcavated contaminated soil" from the waste definition. No single REACH
  provision I found says "this Regulation does not apply to contaminated land" in so many
  words — that conclusion is a structural inference, not a quoted clause. **Flagged as
  inference, not a directly-quotable primary statement.**
- UK CLEA comparison points are asserted from general professional knowledge of CLEA's
  CLEA-model (SGV/GAC exposure modelling, land-use-specific, probabilistic) rather than a
  primary CLEA document opened in this session — used only as a contrast case, not as an
  EU source, and should be independently verified before being cited as authoritative in
  product documentation.

**Bottom line**: the EU-level chemical/water/waste-law skeleton (POPs Reg, WFD/EQSD
mechanism, Euratom BSS separation, REACH Annex XVII text, BBodSchV, Dutch standard-soil
values) is solid — read from primary text. The bioavailability *technical methodology*
detail (CIS Guidance 38, bio-met/M-BAT internals, the old Cu/Ni/Zn RARs) and the two
in-flight 2025–2026 legislative amendments (POPs Reg Annex I MCCP/PFCA addition, WFD/EQSD
recast) are corroborated but not independently verified at the primary-text level and
should be re-checked before any model-building decision is locked in.

---

## 1. EU POPs Regulation (EU) 2019/1021 (recast, as amended)

**Mechanism.** Regulation (EU) 2019/1021 of 20 June 2019 (OJ L 169, 25.6.2019, p.45–77)
is the EU's direct-effect instrument implementing the Stockholm Convention and the
CLRTAP POPs Protocol. Article 1 states its objective is "to protect human health and the
environment from POPs by prohibiting, phasing out as soon as possible, or restricting the
manufacturing, placing on the market and use of substances subject to the Stockholm
Convention…or the [CLRTAP] Protocol…by minimising…releases of such substances, and by
establishing provisions regarding waste consisting of, containing or contaminated by any
of those substances."

Its five annexes carry different obligations:
- **Annex I** — substances subject to a manufacture/placing-on-market/use **prohibition**
  (with narrow exemptions), e.g. PCBs, DDT, PFOS/PFOA, HBCDD, tetra-/pentabromodiphenyl
  ethers.
- **Annex II** — substances subject to **restriction** (conditional/limited use).
- **Annex III** — substances subject to **release-reduction/inventory** obligations, split
  Part A (unintentionally produced PCDD/PCDF, PCBs, HCB) and Part B (other unintentional
  byproducts, e.g. PAHs).
- **Annex IV** — waste concentration limits ("POP content limits") above which waste must
  be managed as POP-waste (values range roughly 1 mg/kg for PFOA up to 10,000 mg/kg for
  short-chain chlorinated paraffins).
- **Annex V** — permitted waste-treatment/disposal methods (destruction/irreversible
  transformation, specified conditions for landfill, exclusions for certain
  recycling/recovery).

Regulation (EU) 2022/2400 amended Annexes IV and V. As of this session's check, MCCPs,
long-chain (C9–C21) PFCAs, and chlorpyrifos are proposed additions to Annex I (Commission
proposal of 21 November 2025) but **not yet confirmed as adopted/in force** — see honesty
section.

**Relevance to legacy contaminants**: this is the EU's operative control instrument for
PCBs and legacy organochlorine pesticides (as listed substances) and for dioxins/furans
and PAHs (as unintentional-release substances under Annex III). It does **not** itself set
soil/sediment/water screening thresholds for contaminated-site assessment — it controls
manufacture/use/waste, not environmental media concentrations.

## 2. Stockholm Convention implementation mechanism

**Mechanism (mechanism-level confidence; article-text not independently re-read this
session — see honesty section).** The Convention organizes controlled chemicals into three
annexes with different obligations: Annex A chemicals must be **eliminated** (production
and use banned, subject to country-specific exemptions); Annex B chemicals must be
**restricted** (production/use limited to "acceptable purposes" and specific exemptions);
Annex C chemicals are **unintentionally produced** byproducts subject to a continuing
obligation to minimize and, where feasible, eliminate releases (e.g. via best available
techniques/best environmental practices).

New chemicals are added through a Parties-nominate → POPs Review Committee (POPRC)
technical-review → Conference of the Parties (COP) decision pathway: a nominating Party
submits a proposal screened against Annex D criteria (persistence, bioaccumulation,
long-range transport potential, adverse effects); if it passes screening, POPRC develops
a risk profile (Annex E) and then a risk management evaluation (Annex F) before
recommending listing; the COP then votes to amend Annex A/B/C.

**PCBs**: listed under **Annex A** (elimination, per chm.pops.int) **and** under **Annex
C** (because PCBs also arise as unintentional combustion/thermal-process byproducts).
**Dioxins (PCDD) and furans (PCDF)**: listed **exclusively under Annex C** — they are not
intentionally manufactured, so only the unintentional-release minimization obligation
applies.

The EU implements these Annex A/B obligations through POPs Regulation Annex I/II
(prohibition/restriction) and the Annex C unintentional-release obligations through POPs
Regulation Annex III (release inventories) plus sector legislation (e.g. Industrial
Emissions Directive for combustion/incineration sources — not independently verified this
session, flagged for follow-up).

## 3. Water Framework Directive 2000/60/EC + EQS Directive 2008/105/EC as amended by 2013/39/EU

**Mechanism (read directly from EUR-Lex).** The WFD's chemical-status test is a
concentration-ceiling compliance mechanism, not a site-specific risk-quotient (PNEC)
calculation. Article 16(2) has the Commission propose a list of "priority substances…
selected amongst those which present a significant risk to or via the aquatic
environment," using combined risk-based prioritisation (from existing EU chemicals-risk
work) and simplified procedures based on hazard evidence plus monitoring of widespread
contamination. Article 16(3) carves out **priority *hazardous* substances** — the subset
subject to a "cessation or phasing-out of discharges, emissions and losses" objective
rather than a mere concentration ceiling. Article 16(7) has the Commission propose quality
standards ("EQS") "applicable to the concentrations of the priority substances in surface
water, sediment or biota."

Article 2(24) defines "good surface water chemical status" as: concentrations of
pollutants not exceeding the EQS in Annex IX / set under Article 16(7). This is combined
with, but assessed separately from, **ecological status** (Article 2(21), assessed via
biological/hydromorphological/physico-chemical quality elements in Annex V); under
Article 4(1)(a)(ii), "good surface water status" requires both ecological *and* chemical
status to be at least "good" — a dual pass/fail test, unlike a PNEC-based risk
characterisation ratio.

**Priority substances list**: Directive 2013/39/EU replaced Annex X of the WFD with a list
of 45 (later expanded) priority substances/groups, adding 12 newly identified substances
(recital 7 — "amending…the list of priority substances by identifying new substances…
setting EQS for those newly identified substances, revising the EQS for some existing
substances").

**Biota EQS mechanism**: Article 3(2) of Directive 2013/39/EU requires Member States to
"apply the biota EQS laid down in Part A of Annex I" for a defined set of substance
numbers (the 2013 text lists numbers including 5 (brominated diphenylethers), 15
(fluoranthene), 21 (mercury and compounds), 28 (PAHs/benzo(a)pyrene), 34/35/37/43/44
(dicofol, PFOS, dioxins/dioxin-like compounds, HBCDD, heptachlor/heptachlor epoxide) among
others). Recital 17 explains the rationale: "Some very hydrophobic substances accumulate
in biota and are hardly detectable in water even using the most advanced analytical
techniques. For such substances, EQS should be set for biota." Confirmed values include
mercury 20 µg/kg (prey tissue, ww) and PBDEs 0.0085 µg/kg (ww) — the water-column AA-EQS
for PBDEs was withdrawn in favour of the biota standard. Article 3(3) allows Member States
to monitor an alternative matrix/taxon or apply an alternative EQS "provided that the
level of protection…is as good as" the biota EQS — i.e. flexibility, not a free pass.

**Metal bioavailability mechanism**: Annex I, Part B, point 3 of the amended EQSD states
that for certain metals the water EQS refers to the **dissolved** or **bioavailable**
concentration, and that "Member States may, when assessing the monitoring results against
the relevant EQS, take into account…hardness, pH, dissolved organic carbon or other water
quality parameters affecting the bioavailability of metals, the bioavailable
concentrations being determined using appropriate bioavailability modelling." This is a
**Member-State-discretionary bioavailability correction**, not a mandatory single formula
in the Directive text itself — the actual modelling method (BLM-derived, simplified tools
like bio-met/M-BAT) sits in non-binding CIS technical guidance (Guidance No. 38),
corroborated but not independently verified in full this session. Confirmed inland
freshwater AA-EQS values (bioavailable): lead 1.2 µg/l (MAC 14 µg/l), nickel 4 µg/l (MAC
34 µg/l) — cadmium's EQS instead varies by five water-hardness classes rather than a
continuous bioavailability model.

**Status of the underlying list**: secondary sources (not independently verified via
EUR-Lex text this session) indicate a further WFD/EQSD/Groundwater Directive recast
(COM(2022)540) adding ~24 substances plus a PFAS group was formally adopted by the Council
on 17 February 2026 with a transposition deadline of December 2027 — flagged for
follow-up confirmation.

## 4. REACH (Regulation (EC) 1907/2006) — relevance to legacy contaminants

**Confirmed structurally.** REACH's registration (Title II), authorisation (Title VII) and
restriction (Title VIII, Annex XVII) obligations attach to substances that are
manufactured, imported, or **placed on the market**, or to articles containing them — it
is forward-looking chemical-commerce control, not a contaminated-media assessment
framework. REACH Annex XVII, Entry 1, directly confirmed from the UK's retained-EU-law
mirror of the Regulation, restricts **"Polychlorinated terphenyls (PCTs)"** to
concentrations ≤50 mg/kg — note this entry covers **PCTs, not PCBs**; PCBs are instead
controlled via the POPs Regulation (Annex I prohibition) and, for existing
equipment/disposal, via Council Directive 96/59/EC on PCB/PCT disposal (corroborated via
search, not independently opened this session). REACH Annex XVII Entry 50 restricts PAH
content in extender oils/tyres (≤1 mg/kg BaP or ≤10 mg/kg sum-PAH), general consumer
rubber/plastic articles (≤1 mg/kg per listed PAH), and toys/childcare articles (≤0.5
mg/kg per listed PAH) — a use-restriction, not an environmental/site threshold.

**Relevance to historic/legacy contaminated sites**: no REACH provision independently
found this session says explicitly "this Regulation does not apply to contaminated land."
The conclusion that REACH is largely irrelevant to *in-situ* legacy soil/groundwater
contamination is a structural inference from (a) REACH's "placed on the market" trigger
and (b) Directive 2008/98/EC's waste-definition exclusion of "land (in situ), including
unexcavated contaminated soil" (corroborated via search snippet, not independently opened
in full) — meaning in-situ contaminated soil is neither a REACH-regulated substance
placement nor (while unexcavated) categorised as waste. Once contaminated soil is
excavated/managed as waste or as a recovered "article"/substance for reuse, separate waste
and (potentially) REACH-adjacent obligations can attach — this transition point is a
genuine grey area that would benefit from dedicated follow-up (ECHA's guidance on waste
and recovered substances, fetched as a URL but not analysed for this specific question
this session).

## 5. EU-level metal bioavailability / Biotic Ligand Model (BLM) approaches

**Confirmed mechanism-level, methodology-detail unconfirmed (see honesty section).** The
WFD/EQSD text itself (Annex I Part B point 3, confirmed above) authorises but does not
mandate bioavailability correction using hardness/pH/DOC-based modelling. The actual
technical methodology lives in non-binding Common Implementation Strategy guidance —
principally **CIS Guidance Document No. 38** ("Technical Guidance for implementing
Environmental Quality Standards (EQS) for metals," Common Implementation Strategy for the
WFD) — whose existence and general scope (bioavailability correction for Ni, Pb, Cu, Zn
using BLM-derived relationships and inputs such as pH, water hardness, and dissolved
organic carbon) is corroborated by ResearchGate, WFD-UK and bio-met.net sources, but whose
exact content I could not read directly (PDF binary not parseable by the fetch tool used).
Downstream, simplified compliance tools implement BLM outputs for routine regulatory use:
**bio-met** (covers Cu, Ni, Zn, Pb EQS-compliance assessment) and the UK Environment
Agency's **M-BAT** — both corroborated via search but not independently read line-by-line.
The precedent Existing Substances Regulation-era EU Risk Assessment Reports for copper,
nickel and zinc (developed under Regulation 793/93/EEC before REACH) are reported in
secondary literature as an early basis for the BLM-linked EU approach; I did not locate
and open the original European Chemicals Bureau RAR PDFs this session — flagged for
follow-up (likely findable via echa.europa.eu or JRC archive mirrors).

**Net assessment for FateIntel**: there is a genuine EU-endorsed bioavailability
methodology track for metals in freshwater compliance assessment, distinct from (and more
sophisticated than) a simple hardness-based lookup table — but it is guidance-layer, not
binding Directive text, and any FateIntel implementation would need the actual Guidance
No. 38 equations/inputs pulled from a properly extracted copy of the PDF, not assumed.

## 6. National contaminated-land methodologies: Netherlands and Germany

### Netherlands

**Confirmed from official sources (iplo.nl summarised via automated tool; RIVM PDF and
rvs.rivm.nl cross-check for the standard-soil figures).** The Dutch system is a
**generic soil-quality-standard model**, not a site-specific probabilistic exposure model
like UK CLEA. It uses three reference levels: **Target Values (Streefwaarden/AW)** —
background/"clean soil" reference; and **Intervention Values (Interventiewaarden)** — the
concentration above which the soil's functional properties for humans, plants and animals
are considered seriously impaired/threatened, triggering a legal "serious contamination"
determination and (subject to urgency assessment) a remediation obligation. Values are
normalised to a **"Standard Soil"** of **10% organic matter and 25% lutum (clay fraction
<2 µm)** — confirmed independently via RIVM's soil-risk portal — with measured
concentrations mathematically corrected to this reference using organic-matter/clay
correction formulas (for metals: both organic matter and clay; for organics: organic
matter only). A site is classified as a legally "serious case" of contamination when
contaminated soil volume exceeds roughly 25 m³ or contaminated groundwater volume exceeds
roughly 100 m³ above intervention values (per search-corroborated secondary description;
not independently re-verified against the primary circular text this session).

**Current legal status — important, actively changing**: the historic "Circular on Target
Values and Intervention Values for Soil Remediation" (Circulaire bodemsanering) is
confirmed (via DCMR/RIVM/Business.gov.nl sources) to have been **superseded as of 1
January 2024** by the Omgevingswet (Environment and Planning Act) and its implementing
Besluit bodemkwaliteit / Besluit activiteiten leefomgeving (the "old" Circular remains
applicable only under transitional law for remediations already underway). The intervention
values and standard-soil methodology are carried forward largely unchanged in substance,
now codified in Besluit activiteiten leefomgeving Bijlage IIA rather than the old Circular
— so the *methodology shape* described above should still be current, but any numeric
table sourced from a pre-2024 "Circular" PDF should be flagged as superseded-in-form
(same values, new legal basis) pending confirmation.

**Conceptual contrast with UK CLEA** (asserted from general knowledge, not independently
verified against a primary CLEA document this session): CLEA is a probabilistic,
land-use-specific direct human-exposure model (deriving Soil Guideline Values/Generic
Assessment Criteria per receptor scenario — residential with/without homegrown produce,
allotment, commercial/industrial — using exposure-pathway modelling and toxicological
HCV/MTC values), whereas the Dutch system sets **generic, use-independent** soil-quality
thresholds primarily anchored to ecosystem/soil-function protection (not solely
human-health exposure), with human exposure as one of several protected "soil functions"
rather than the sole driver of the numeric value.

### Germany

**Confirmed directly from gesetze-im-internet.de (BBodSchV, in force since 1.8.2023,
replacing the 1999 version, published BGBl. I 2021 pp.2598/2716).** The ordinance
structures values into three tiers, each tied to a distinct legal consequence:

- **Vorsorgewerte** ("precautionary values") — § 3(1): concentrations above which concern
  about harmful soil change must generally be assumed; precautionary, not yet
  investigation-triggering. Tables in Anlage 1 (inorganic/organic substances).
- **Prüfwerte** ("test/trigger values") — pathway-specific; exceedance triggers a
  case-by-case investigation to determine whether a "harmful soil change" or
  "Altlast" (contaminated site) actually exists. Tables in Anlage 2, differentiated by
  exposure pathway: **Boden-Mensch** (soil→human direct contact, further split by land use
  — children's playgrounds, residential, parks/recreational, industrial/commercial),
  **Boden-Grundwasser** (soil→groundwater leaching, assessed both at the source and at a
  downgradient assessment point), and **Boden-Nutzpflanze** (soil→crop uptake).
- **Maßnahmenwerte** ("remediation/action values") — exceedance generally establishes a
  presumption that a harmful soil change/contaminated site exists and that remediation is
  required; set for the Boden-Mensch pathway and certain plant-uptake scenarios.

Analytical procedures are specified in Anlage 3. This is a **pathway-specific, tiered
trigger-value system** (precaution → investigation trigger → remediation trigger),
conceptually closer to CLEA's pathway-based logic than the Dutch system's single generic
"serious contamination" threshold, but still fundamentally a fixed-value lookup-table
system rather than CLEA's per-receptor probabilistic exposure calculation — Germany
supplies fixed Prüf-/Maßnahmenwerte per defined land-use/pathway combination rather than
letting the assessor build a site-specific probabilistic model. Where the ordinance has no
listed value for a given substance, § 4(5) requires that the same derivation
methods/criteria used for the listed substances be applied case-by-case — i.e. the
methodology is meant to be extensible by design, which is directly relevant to how
FateIntel might eventually cover contaminants the German ordinance doesn't yet tabulate.

## 7. EU sediment and biota EQS

**Confirmed.** The WFD's own enabling clause (Article 16(7), confirmed above) explicitly
allows EQS to be set for "surface water, sediment or biota" — sediment and biota are
first-class alternative compliance matrices in the Directive's own text, not an
after-the-fact add-on. In practice (per Directive 2013/39/EU, confirmed above) the EU has
so far exercised the **biota** option for a defined list of highly bioaccumulative/
hydrophobic substances (mercury, PBDEs, HBCDD, dioxins/dioxin-like compounds, PFOS,
dicofol, heptachlor/heptachlor epoxide, certain PAHs, hexachlorobenzene, hexachloro-
butadiene) specifically because — per recital 17 — these substances "accumulate in biota
and are hardly detectable in water even using the most advanced analytical techniques."
Member States retain Article 3(3) flexibility to substitute an alternative matrix/taxon
or an equivalent-protection alternative EQS. I did not find, and did not have time to
independently confirm, whether the EU has adopted a *general EU-wide sediment EQS list* in
the way it has a biota EQS list (sediment appears to remain more of a Member-State-specific
monitoring option than a harmonised EU sediment-EQS table) — **flagged for follow-up**:
check CIS Guidance No. 25 ("Chemical Monitoring of Sediment and Biota," found via search
at circabc.europa.eu but not opened this session) for whether it specifies binding or
merely advisory sediment EQS.

## 8. Radionuclide/radiological contamination as a separate regime

**Confirmed directly from EUR-Lex.** Directive 2013/59/Euratom (Basic Safety Standards,
BSS) establishes "uniform basic safety standards for the protection of the health of
individuals subject to occupational, medical and public exposures against the dangers
arising from ionising radiation" (Article 1), applying across "planned, existing or
emergency exposure situation[s]" (Article 2(1)). Article 2(2)(d) explicitly brings
**legacy/historic radiological contamination** into scope: it covers "the exposure of
workers or members of the public to indoor radon, the external exposure from building
materials and cases of lasting exposure resulting from the after-effects of an emergency
or **a past human activity**" — i.e. an existing-exposure-situation category structurally
analogous to "contaminated land," but run entirely through the Euratom/radiological-
protection legal base (Article 31 Euratom Treaty), not through REACH or the WFD chemical
framework. The Directive addresses ionising-radiation hazard only; it does not purport to
cover the chemical (non-radiological) toxicity of radioactive substances — that would fall
to REACH/CLP in the ordinary way (this delineation is a reasonable structural reading of
the Directive's radiation-only framing rather than a quoted clause saying so explicitly).
Practical conclusion for FateIntel: **radiological contaminated-site assessment (e.g.
legacy uranium mining/milling sites, NORM-impacted sites) is a genuinely separate
regulatory and technical domain** from the chemical fate/exposure models FateIntel
currently builds, requiring its own dosimetry-based methodology if ever pursued — it
should not be bolted onto the chemical PNEC/EQS/CLEA-style machinery.

---

## Matrix

| Contaminant Family | Assessment Purpose | Environmental Compartment | Tier | Model/Tool or Instrument Name | Required Inputs | Outputs | Regulatory Status | Native-Buildable or External-Handoff-Only | Screening/Refinement/Regulatory | Limitations | Source URL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PCBs, legacy OC pesticides, PFOS/PFOA, HBCDD, brominated flame retardants | Manufacture/use/waste control (not media screening) | Cross-media (product/waste stage) | Regulatory (legal control, not a risk model) | EU POPs Regulation (EU) 2019/1021, Annexes I–V | Substance identity/CAS, use category, waste POP-content concentration | Prohibited/restricted status; waste POP-content limit compliance (Annex IV) | Current; recent amendment for Annexes IV/V (2022/2400); MCCP/PFCA/chlorpyrifos Annex I addition proposed Nov 2025, **not yet confirmed in force** | External-handoff-only (legal status lookup, not a fate/exposure calculation) | Regulatory | Controls commerce/waste, not environmental concentrations; doesn't screen contaminated sites | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:02019R1021-20241017 |
| PCBs, dioxins/furans, and all Convention-listed POPs | International listing/control mechanism underlying EU law | Cross-media | Regulatory (treaty mechanism) | Stockholm Convention Annexes A (elimination)/B (restriction)/C (unintentional release) | Nomination dossier vs. Annex D screening criteria; risk profile (Annex E); risk management evaluation (Annex F) | COP listing decision; national elimination/restriction/release-minimisation obligations | Current; actively expanding (POPRC ongoing reviews, e.g. Sept–Oct 2025 POPRC-21) | External-handoff-only | Regulatory | Article-level text not independently re-read this session (see honesty section); EU implements via POPs Reg, not directly self-executing | https://chm.pops.int/TheConvention/ThePOPs/ListingofPOPs/tabid/2509/Default.aspx |
| Priority organic substances (PAHs, HCB, dioxins, pesticides, brominated compounds, etc.) | Surface-water chemical-status compliance | Surface water (water column) | Regulatory | WFD 2000/60/EC Art. 16 + EQS Directive 2008/105/EC as amended by 2013/39/EU, Annex I Part A | Monitored water-column concentration vs. AA-EQS/MAC-EQS per Annex X substance | Pass/fail "good chemical status" per substance and overall | Current; further recast (COM(2022)540) reportedly adopted by Council 17 Feb 2026 per secondary sources, **not independently verified this session** | External-handoff-only (compliance lookup against published EQS table) | Regulatory | Binary ceiling test, not a probabilistic/site-specific risk calc; EQS values fixed EU-wide regardless of local receiving-water conditions (except metals/biota, see below) | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013L0039 |
| Highly bioaccumulative/hydrophobic substances: Hg, PBDEs, HBCDD, dioxins/dioxin-like compounds, PFOS, dicofol, heptachlor(+epoxide), certain PAHs, HCB, HCBD | Surface-water chemical-status compliance where water-column detection is impractical | Biota (fish/prey tissue) | Regulatory | WFD/EQSD Annex I Part A biota EQS (Directive 2013/39/EU Art. 3(2)) | Tissue concentration (wet weight) in specified biota matrix/taxon | Pass/fail vs. biota EQS (e.g. Hg 20 µg/kg ww; PBDEs 0.0085 µg/kg ww) | Current | External-handoff-only | Regulatory | Member States may substitute matrix/taxon or alternative EQS if "equally protective" (Art. 3(3)) — introduces some national variability | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013L0039 |
| Metals: Ni, Pb (bioavailability-adjusted); Cd (hardness-class-adjusted); Cu, Zn (national/guidance-level bioavailability tools) | Surface-water chemical-status compliance accounting for site water-chemistry-dependent toxicity | Surface water (dissolved fraction) | Refinement (bioavailability correction) / Regulatory (final compliance test) | Bioavailability-corrected metal EQS per EQSD Annex I Part B point 3; implemented via CIS Guidance No. 38 and tools such as bio-met / UK M-BAT (BLM-derived) | pH, water hardness, dissolved organic carbon (DOC), dissolved metal concentration | Bioavailable (site-corrected) metal concentration for EQS comparison | Current (EQS in force); Guidance No. 38 methodology content **not independently verified this session — PDF unreadable via tool used** | Guidance/tool layer is external-handoff-only (adopt bio-met/M-BAT or equivalent BLM tool rather than rebuild); the underlying BLM science is in principle native-buildable but nontrivial | Refinement feeding into a Regulatory pass/fail | Bioavailability correction is Member-State-discretionary, not mandatory EU-wide; exact CIS Guidance 38 equations/inputs need direct verification before implementation | https://circabc.europa.eu/sd/a/a705289f-7001-4c7d-ac7c-1cf8140e2117/Guidance%20No%2038%20-%20Technical%20guidance%20for%20EQS%20for%20metals.pdf (unparsed this session — flagged) |
| PCTs (and, via a separate non-REACH instrument, PCBs) | Market/use restriction | Product/commerce (not environmental media) | Regulatory | REACH Annex XVII Entry 1 (PCTs); PCBs instead controlled via POPs Reg Annex I + Council Directive 96/59/EC (PCB/PCT disposal) | Substance concentration in mixture/equipment | Placing-on-market/use ban above 50 mg/kg (0.005% wt) for PCTs | Current | External-handoff-only | Regulatory | Confirms REACH Annex XVII does **not** carry a dedicated PCB entry — easy to mis-model if assumed by analogy to PCTs | https://www.legislation.gov.uk/eur/2006/1907/annex/XVII |
| PAHs | Product/consumer-article restriction | Product/commerce | Regulatory | REACH Annex XVII Entry 50 | PAH congener content (BaP and 7/8-PAH sum) in rubber/plastic components, extender oils, toys | Placing-on-market ban above congener-specific limits (0.5–10 mg/kg depending on article class) | Current (further tightened 2025/660 for clay shooting targets, effective 22 Apr 2026) | External-handoff-only | Regulatory | Product-safety restriction, not an environmental/soil PAH screening value | https://www.legislation.gov.uk/eur/2006/1907/annex/XVII |
| Any substance (structural framing only) | Confirms REACH's non-role for in-situ legacy contamination | Soil/groundwater (in situ) | N/A (scope-exclusion finding) | REACH Title II/VII/VIII "placed on the market" trigger + Directive 2008/98/EC waste-definition exclusion for unexcavated contaminated land | N/A | N/A — informs FateIntel that REACH should not be modelled as a contaminated-land instrument | Current | N/A | N/A | Inference, not a directly quoted REACH clause — see honesty section | https://echa.europa.eu/regulations/reach/understanding-reach ; https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A02008L0098-20240218 |
| Radionuclides / radiological contamination (incl. legacy/NORM sites) | Dose-based protection of workers/public from ionising radiation, including "past human activity" legacy contamination | Cross-media, dose-based (not concentration-based) | Regulatory, specialist (separate legal base — Euratom Treaty Art. 31, not REACH/WFD) | Euratom Basic Safety Standards Directive 2013/59/Euratom | Radionuclide activity concentrations, dose-conversion factors, exposure pathway/scenario (occupational, medical, public, existing/legacy) | Effective dose (mSv) vs. dose constraints/reference levels | Current | External-handoff-only — genuinely separate technical domain (dosimetry, not chemical fate/PNEC) | Regulatory | Explicitly covers "past human activity" legacy exposure (Art. 2(2)(d)) but is dose-based, not concentration-based — cannot be shoehorned into FateIntel's PNEC/EQS chemical-risk machinery | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013L0059 |
| All contaminants (metals + organics) — generic soil quality | Generic soil-function protection trigger for remediation | Soil (and via leaching, groundwater) | Screening/regulatory generic value (not site-specific probabilistic model) | Netherlands: Target Values (Streefwaarden) / Intervention Values (Interventiewaarden), standard-soil-corrected (10% organic matter, 25% lutum), now codified under Besluit activiteiten leefomgeving Bijlage IIA (post-1 Jan 2024; formerly the Circulaire bodemsanering) | Measured soil concentration; site organic-matter % and clay % for standard-soil correction | Classification vs. clean/serious-contamination thresholds; "serious case" trigger (~>25 m³ soil or >100 m³ groundwater above Intervention Value, per secondary source) | Current under new Omgevingswet legal basis (post-2024); values reported materially unchanged from prior Circular, methodology shape unchanged | External-handoff-only (adopt Dutch value tables/correction formulas as reference, not reproduce as generic default without licensing/context check) | Screening → Regulatory trigger | Use-independent generic thresholds, not receptor/land-use-specific like CLEA; some numeric-table detail (serious-case volume thresholds) not independently re-verified against primary 2024 text this session | https://iplo.nl/publish/pages/220025/into_dutch_soils.pdf ; https://rvs.rivm.nl/onderwerpen/normen/milieu/bodem-grond-en-grondwater |
| All contaminants (metals + organics) — pathway-specific soil values | Tiered precaution → investigation-trigger → remediation-trigger soil assessment | Soil, by pathway: soil→human (land-use-specific), soil→groundwater, soil→crop | Screening (Vorsorgewerte) → Detailed investigation trigger (Prüfwerte) → Remediation trigger (Maßnahmenwerte) | Germany: Bundes-Bodenschutz- und Altlastenverordnung (BBodSchV 2023), Anlagen 1–3 | Measured soil concentration by pathway/land-use category; site-specific investigation data once Prüfwert exceeded | Precaution flag / investigation requirement / remediation requirement, each tied to specific land-use or pathway table | Current, in force since 1.8.2023 (replacing 1999 version) | External-handoff-only for the tabulated substances; §4(5) extensibility clause supports native derivation for untabulated substances using the same documented method | Screening/Refinement/Regulatory, all three tiers present by design | Fixed lookup-table values per defined pathway/land-use combination, not a per-receptor probabilistic exposure model; extension to new substances requires following the ordinance's own (not independently reviewed this session) derivation methodology | https://www.gesetze-im-internet.de/bbodschv_2023/BJNR271600021.html |
| Sediment-associated contaminants generally | Alternative compliance matrix where water-column EQS is impractical | Sediment | Regulatory (enabling clause) — extent of an *EU-wide harmonised* sediment EQS list unconfirmed | WFD Art. 16(7) enabling clause ("surface water, sediment or biota"); CIS Guidance No. 25 (Chemical Monitoring of Sediment and Biota) | Sediment concentration by substance | Would be pass/fail vs. a sediment EQS, where one is set | Enabling clause current; whether a harmonised EU sediment-EQS table (vs. biota, which is confirmed) exists **needs follow-up** — Guidance No. 25 not opened this session | Unconfirmed / follow-up needed | Unclear — likely Regulatory if adopted, else Member-State-discretionary monitoring option | Flagged as an open question rather than a confirmed model | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013L0039 (enabling text only) |

---

## Follow-up queue (do before building anything on top of this)

1. Extract and read CIS Guidance No. 38 (metals EQS bioavailability) as actual text —
   download the CIRCABC PDF and run local text extraction rather than WebFetch, then
   document the exact BLM/M-BAT/bio-met input parameters and equations.
2. Verify current in-force status of the POPs Regulation MCCP/long-chain PFCA/chlorpyrifos
   Annex I amendment via a direct EUR-Lex OJ search (Council doc ST-13064-2026-INIT was
   still in process as of 11 Sept 2026).
3. Verify the WFD/EQSD/Groundwater Directive recast (COM(2022)540) final adopted text,
   OJ citation, and exact Annex X substance additions directly from EUR-Lex — currently
   sourced only from secondary trade-press/legislative-tracker summaries.
4. Read CIS Guidance No. 25 (Chemical Monitoring of Sediment and Biota) to settle whether
   the EU has a harmonised sediment-EQS table or leaves sediment monitoring as a
   Member-State option.
5. Locate and open the original EU Risk Assessment Reports for copper, nickel and zinc
   (pre-REACH, Existing Substances Regulation era) to confirm their direct linkage to the
   current BLM-based EQS methodology, or confirm they are now superseded/archival only.
6. Read the Stockholm Convention's own Articles 3, 5, 8 and Annexes D/E/F text directly
   (a downloadable PDF exists at chm.pops.int; this session could not get the HTML
   navigation page to surface article-level text).
7. Confirm the REACH/waste-law boundary for contaminated land with a direct, on-point
   legal source (e.g. an ECHA or European Commission staff working document explicitly
   discussing contaminated-land treatment under REACH/CLP/waste law), rather than relying
   on the structural inference made in section 4 above.
8. Independently verify UK CLEA's actual mechanism (SGV/GAC derivation, exposure model
   structure) against a primary Environment Agency/UKHSA document before using it as the
   comparison baseline in any product documentation — this session used general knowledge
   only for the CLEA side of the comparison.
