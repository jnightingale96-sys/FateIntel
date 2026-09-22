# Region research: Japan, China, South Korea, India

Research for adding these four as regions in `workflow_registry.py` / `registry.py`, at the same depth as the
existing AU/CA/NZ work: name the real regime and agency, name a contaminated-land route where one is confirmed,
and mark anything not confirmed as a gap rather than guessing. This is NOT full ECHA/AICIS-depth PEC/PNEC
methodology research (that would need a session of its own per country); it names the regime and hands over,
the same way `EXTERNAL_ROUTES` already does for the UK/US/EU/CA/AU/NZ.

All research done 2026-09-22. Retrieval dates noted per source below.

## Japan

**Industrial/new chemicals**: Chemical Substances Control Law (CSCL, formally the Act on the Evaluation of
Chemical Substances and Regulation of Their Manufacture, etc., 1973). Jointly administered by METI, MHLW and
the Ministry of the Environment (MoE). New substances go through a "Screening Evaluation" and "Step-wise Risk
Assessment" against exposure and hazard information (persistence, bioaccumulation, human/ecological toxicity).
Source: METI, "Chemical Substances Control Law (CSCL)" (official overview PDF),
<https://www.meti.go.jp/policy/chemical_management/english/cscl/files/about/01CSCL.pdf>; OECD PFAS country
page confirms the same three-ministry structure, <https://www.oecd.org/content/dam/oecd/en/topics/policy-sub-issues/risk-management-risk-reduction-and-sustainable-chemistry2/pfas-country-information/Japan.pdf>.

**Method structure, 2026-09-22 follow-up**: fetched and read (via PyMuPDF, after WebFetch's own summariser
reported it as unreadable -- the same "the tool's summary isn't enough" pattern as the UK CLP mobility text
earlier in this project) NITE's own technical presentation: Yusuke Hirai (Risk Analysis Division, Chemical
Management Center, NITE), "Chemical Risk Assessment under the Chemical Substances Control Law in Japan and
comparison with REACH," 6th SETAC World Congress / SETAC Europe 22nd Annual Meeting, Berlin, 23 May 2012,
<https://www.nite.go.jp/data/000009696.pdf>. It describes a real, two-stage, government-run (not industry-run,
~30 NITE/CERI staff) process: (1) ALL existing substances are screened by cross-tabulating a Hazard Class (1-4,
scored from repeated-dose toxicity, reproductive toxicity, mutagenicity, carcinogenicity and ecotoxicity data --
"if no data available, default class (class 2) will be applied") against an Exposure Class (1-5, set by total
estimated national emissions in tonnes/year: Class 1 >10,000 t, down to Class 5 1-<10 t, with <1 t excluded from
prioritisation) in a priority matrix, producing High/Medium/Low; (2) substances scoring High become "Priority
Assessment Chemical Substances" (PACs) and get a real Risk Assessment: a modelled PEC (from notified production/
use volume, an emission-factor table and an exposure scenario by lifecycle stage) compared against DNEL/PNEC.
Production/import volume is separately tiered (Tier 1: 1-10 t/y, Tier 2: 10-100 t/y, Tier 3: 100-1,000 t/y,
Tier 4: >=1,000 t/y), setting how much hazard/exposure data is required at each tier. **What this is NOT**: a
calculable method FateIntel could run. The source is a 2012 conference slide deck, not the current official
guideline text; a 2022 revision to the PAC screening/risk-assessment method was found in search results (CIRS
Group, "Japan to Publish Revised Risk Assessment Methods for Priority Assessment Chemical Substances (PACs)")
but not read, so none of the 2012 numeric class boundaries above are asserted as current. Encoded in
`_regulatory_programme` as `JP_CSCL_PARTIAL` -- structure named, current numbers not verified.

**Pesticides**: Agricultural Chemicals Regulation Act (1948, substantially revised 2018 to add post-market
re-evaluation). Registration is refused if the residue standard under the Food Sanitation Act is exceeded, or if
"the Predicted Environmental Concentration (PEC) of their active ingredients in areas of public waters does not
conform to the standards set by the Minister of the Environment to prevent adverse effect on drinking water" --
a genuine, named PEC-based environmental criterion. Official English translation:
<https://www.japaneselawtranslation.go.jp/en/laws/view/3507/en>. Retrieved via WebSearch summary of the official
translation page; the PEC calculation method itself was not independently fetched and is not encoded.

**Human pharmaceuticals**: MHLW's "Guidance on the Environmental Risk Assessment in New Pharmaceutical
Development" (2016) is a real, named ERA workflow: ecotoxicity testing is triggered by log Kow and an action
limit of 0.01 microgram/L; PEC is calculated from annual consumption, excretion rate and WWTP removal rate; PNEC
from LC50/EC50/NOEC; risk assessed via the PEC/PNEC ratio. Source: multiple peer-reviewed secondary citations of
the MHLW guidance (PubMed 42091543, jstage.jst.go.jp/article/cpb/69/9/69_c21-00250), not the MHLW notification
itself, which was not located and fetched this session -- treat the existence and shape of the guidance as
confirmed, but the exact numeric criteria as secondary-sourced, not primary-verified.

**Contaminated land**: Soil Contamination Countermeasures Act (Act No. 53 of 2002). Primary source fetched and
read this session: <https://www.japaneselawtranslation.go.jp/en/laws/view/2038/en> (official Japanese Law
Translation database, retrieved 2026-09-22). Article 1: the Act aims to "facilitate the implementation of
countermeasures against soil contamination" and "protect the health of the citizens" from designated hazardous
substances. Prefectural governors (and mayors of specified cities) administer most of it; the Minister of the
Environment oversees designated investigation institutions and sets national standards. A survey is triggered
when a facility using hazardous substances ceases operations (Art. 3), when land-use change above a threshold is
proposed (Art. 4), or when a governor suspects contamination poses a health risk (Art. 5). Once land is
designated as requiring action: land-form changes are restricted (Art. 9), owners may be ordered to remove or
contain the contamination (Art. 7), and for lesser sites a notify-before-modifying duty applies (Art. 12).
Restrictions lift once established safety standards are met.

**Currency**: JPY.

## China

**Industrial/new chemicals**: "China REACH" -- the Measures for the Environmental (Administration/Management)
Registration of New Chemical Substances, MEE Order No. 12 (2020), administered by the Ministry of Ecology and
Environment (MEE). A comprehensive revision is in progress: a draft was opened for comment mid-2026 and the
revised Measures are due to enter into force 15 August 2026, superseding Order 12 (holders of an existing Order
12 filing must obtain a registration certificate under the new Measures by 31 December 2026). Sources: REACH24H,
"MEE Order No. 12 Revision FAQ", <https://en.reach24h.com/news/insights/chemical/mee-order-no-12-revision-faq-china-new-chemical-substances>;
CIRS, "Breaking News! The Registration System for New Chemical Substances in China Undergoes a Major Overhaul",
<https://www.cirs-group.com/en/chemicals/breaking-news-the-registration-system-for-new-chemical-substances-in-china-undergoes-a-major-overhaul>.
Both are compliance-industry secondary sources (no official MEE English page for the 2026 revision was found
this session).

**Method structure, 2026-09-22 follow-up**: a real, named risk-assessment guideline was found and its existence
is confirmed, though its full text was not: the Technical Framework Guideline for Environmental Risk Assessment
of Chemical Substances (Trial) ("Framework Guide to the Technology Methods of Environmental Risk Assessment for
Chemical Substances (Trial)" in one translation), jointly issued by MEE and the National Health Commission (NHC)
on 3 September 2019, described consistently across Lexology, National Law Review, ChemLinked and REACH24H as a
"four-step" method (hazard identification, dose-response assessment, exposure assessment, risk characterisation)
using a PEC/PNEC-style approach, with aquatic ecotoxicity testing across three trophic levels (algae, fish,
daphnia) -- a real, PEC/PNEC-shaped method, not just an agency name. A further "Systematic Framework for
Technical Standards on Environmental Risk Assessment and Control of Chemical Substances (2024)" was released
16 October 2024, updating this. **Not confirmed**: one search result attributed specific PNEC uncertainty
factors (100 for acute-only aquatic data, 10 additional for chronic data) to this guideline, but that same
search also returned a generic, non-China-specific "How to Calculate PNEC" reference page describing the same
common international convention -- the attribution could not be disentangled from the search summary with
confidence, so no numeric factor is encoded. Encoded in `_regulatory_programme` as `CN_MEE_PARTIAL`.

**Pesticides**: registered by the department of agriculture and rural affairs under the State Council (Ministry
of Agriculture and Rural Affairs). The Soil Pollution law itself (below) directly requires this department to
"strengthen the registration of pesticides and fertilizers, and organize safety assessments of the impact of
pesticides and fertilizers on soil environment" -- so pesticide registration and soil-impact review are linked
by statute, not just by practice.

**Contaminated land**: Law of the People's Republic of China on the Prevention and Control of Soil Contamination
(passed 31 August 2018, in force 1 January 2019) -- China's first dedicated soil-pollution law. Primary source
fetched and read this session: official MEE English translation,
<https://english.mee.gov.cn/Resources/laws/environmental_laws/202011/t20201113_807786.shtml> (retrieved
2026-09-22). Article 1 purpose: to "protect and improve the ecological environment, prevent and control soil
contamination, safeguard public health, promote sustainable use of soil resources." Administered at state level
by the Ministry of Ecology and Environment (unified supervision) together with sectoral departments (agriculture
and rural affairs, natural resources, housing and urban-rural development, forestry and grassland) each within
their own remit, mirrored at provincial/municipal level. Investigation is triggered when contamination is
suspected to exceed risk-control standards (Art. 52), when land use is proposed to change to residential,
administrative or public-service purposes (Art. 59), or via routine surveys/monitoring. Once contamination is
confirmed: land is categorised (priority protection / safe utilisation / strict control) with different
obligations per category; contaminated construction land cannot be used for residential or public-service
purposes until remediation targets are met (Art. 61); the liable party must prepare a remediation plan and pass
an effect assessment before the site is removed from the contamination catalogue.

**Human/veterinary pharmaceuticals** (researched in a 2026-09-22 follow-up session): no pre-market environmental
risk assessment guideline was found under the NMPA or the Ministry of Ecology and Environment -- searches
surfaced GMP manufacturing-quality standards and academic ecotoxicology studies of Chinese rivers, not a
regulatory ERA requirement. What IS real and confirmed: category-specific national discharge standards for
pharmaceutical-manufacturing wastewater, issued by MEE, with official English pages fetched this session --
"Discharge standard of water pollutants for pharmaceutical industry -- Chinese traditional medicine category"
(GB 21906-2008), <https://english.mee.gov.cn/Resources/standards/water_environment/Discharge_standard/200811/t20081103_130775.shtml>,
and "Water Pollutant Discharge Standard of Extractive Pharmaceutical Industry" (GB 21905-2008), plus separate
standards for fermentation-products and chemical-synthesis-products categories. This is a manufacturing-effluent
control, not a pre-market PEC/PNEC risk assessment for a specific drug -- the two are reported separately, not
conflated.

**Currency**: CNY.

## South Korea

**Industrial/new chemicals**: K-REACH, formally the Act on the Registration and Evaluation of Chemical
Substances (passed 30 April 2013, in force 1 January 2015; substantially amended by Ordinance No. 20232, 6
February 2024). The Ministry of Environment (MoE) administers registration; the National Institute of
Environmental Research (NIER) evaluates the shared dossier to determine whether a substance is allowed,
restricted or banned. Sources: CIRS, "K-REACH Registration", <https://www.cirs-group.com/en/chemicals/k-reach-registration>;
REACH24H, "K-REACH 2025 Amendments", <https://en.reach24h.com/news/insights/chemical/k-reach-2025-amendment>.
Secondary compliance-industry sources; the quantitative risk-assessment method was not verified and is not
encoded. **2026-09-22 follow-up search**: no K-REACH-specific numeric method was found. One search result stated
"a ratio of >1 triggers action... according to guidelines of the REACH program" -- reading that in context, it
describes the EU REACH convention, not K-REACH specifically, so it is not attributed to Korea here. NIER's own
NIER Announcement No. 2022-317 (hazard-assessment-result updates) and its 30 September 2022 "Regulation on
Registration Application Dossier Preparation, Hazard Evaluation Methods" were both located by name but not
fetched -- named as a lead for a future session, not encoded as a finding.

**Pesticides**: Agrochemicals Control Act ("Pesticide Control Act" in some translations). **Confirmed in a
2026-09-22 follow-up session**: the Rural Development Administration (RDA) is the operational registering
authority -- "The Administrator of the Rural Development Administration has authority to issue certificates of
registration for agrochemical items after examination of documents and testing samples" -- while the Act itself
falls under the Ministry of Agriculture, Food and Rural Affairs' (MAFRA) statutory/competent authority. Registration
is valid for ten years. Corroborated across three independent sources found by WebSearch (none fetched in full):
the Korea Legislation Research Institute's own translation portal, a USDA FAS country report, and a compliance-
industry secondary source (agrochemical.chemlinked.com). FAOLEX entry (blocked this session, HTTP 403):
<https://www.fao.org/faolex/results/details/en/c/LEX-FAOC136704/>.

**Contaminated land**: Soil Environment Conservation Act. Official Korea Legislation Research Institute (KLRI)
translation located this session: <https://elaw.klri.re.kr/eng_service/lawTwoView.do?hseq=14745> (not
independently fetched and read in full this session -- summarised from the WebSearch result, not primary text,
unlike the Japan and China soil laws above). The Act classifies soil contamination into two tiers: pollution "of
concern", where the relevant authority can restrict land use and order remediation, and pollution requiring
"countermeasure", where the area is designated and managed under a countermeasure plan. Administered by the
Ministry of Environment.

**Human/veterinary pharmaceuticals** (researched in a 2026-09-22 follow-up session): a real requirement, only
thinly sourced. Multiple secondary sources (drug-registration consultancy pages, not the MFDS itself) report that
New Drug Application and biologics submissions to the Ministry of Food and Drug Safety (MFDS) must include
"information on potential environmental risks associated with the product and its manufacturing process" as a
supporting document, aligned with ICH guidelines. No named MFDS guideline document, and no quantitative
PEC/PNEC-style method, was located this session -- treat the requirement's existence as reasonably confirmed and
its actual content as an open gap, not treat the whole thing as absent.

**Currency**: KRW.

## India

**Industrial/new chemicals**: no comprehensive chemicals-registration law is in force. A "Chemicals (Management
and Safety) Rules" ("India REACH", CMSR) has been through five public drafts but was NOT confirmed as enacted
this session -- treat as draft/not yet law, not a supported pathway. Source: CIRS,
<https://www.cirs-group.com/en/chemicals/india-chemical-management-and-safety-rules-cmsr-reach>. The currently
operative regime for hazardous industrial chemicals is instead the Manufacture, Storage and Import of Hazardous
Chemicals Rules, 1989 (MSIHC), made under the Environment (Protection) Act, 1986, administered by the Ministry
of Environment, Forest and Climate Change (MoEFCC) and enforced by the Central/State Pollution Control Boards.
Confirmed still in force this session (last amendment referenced was 2000); primary text located at
<https://www.indiacode.nic.in/ViewFileUploaded?path=AC_CEN_16_18_00011_198629_1517807327582%2Frulesindividualfile%2F&file=msihc_rules_ameded_upto_date.pdf>
(India Code, the Government of India's official legislation portal) but not independently fetched and read this
session -- summarised from a WebSearch result, not primary text. **2026-09-22 follow-up search**: no MSIHC-
specific quantitative environmental risk-assessment method was found. Results returned generic Quantitative Risk
Assessment guidance (accident/spillage/emergency-response risk, a different discipline from environmental fate
PEC/PNEC) and a generic statement that "the simple quotient approach... has become the basis of environmental
risk assessment of chemicals throughout the world" -- not India-specific, so not encoded as a finding.

**Pesticides**: The Insecticides Act, 1968 (in force since 1 August 1971, with the Insecticides Rules, 1971).
Registration is administered centrally by the Central Insecticides Board & Registration Committee (CIBRC), under
the Directorate of Plant Protection, Quarantine & Storage, Department of Agriculture & Cooperation (Ministry of
Agriculture); manufacture/formulation/sale licensing sits with State governments. Source: CIBRC's own government
page, <https://ppqs.gov.in/divisions/central-insecticides-board-registration-committee/about-cibrc> (an official
.gov.in source; summarised from a WebSearch result, not independently fetched this session).

**Contaminated land**: Environment Protection (Management of Contaminated Sites) Rules, 2025 -- India's first
codified procedure for identifying, assessing and remediating chemically contaminated sites, notified as
Notification S.O. 3401(E), dated 24 July 2025, under the Environment (Protection) Act, 1986. Administered by
district authorities/local bodies (initial listing), State Pollution Control Boards (preliminary assessment
within 90 days, then detailed survey within a further 90 days against 189 hazardous chemicals listed under the
Hazardous and Other Wastes Management Rules, 2016), the Central Pollution Control Board and an expert board.
Rule 5 sets a strict-liability framework: once a site is declared contaminated, the State Board must identify
the Responsible Person within 90 days and secure a remediation plan. Sources (secondary summaries of the
gazette notification, not the notification itself, which was not located and fetched this session): Mondaq,
"The Environment Protection (Management Of Contaminated Sites) Rules, 2025: An Analysis",
<https://www.mondaq.com/india/waste-management/1659440>; Drishti IAS,
<https://www.drishtiias.com/daily-updates/daily-news-analysis/environment-protection-management-of-contaminated-sites-rules-2025>.
This is a genuinely new (2025), currently-in-force rule -- worth flagging to the user given how recent it is.

**Human/veterinary pharmaceuticals** (researched in a 2026-09-22 follow-up session): a confirmed absence, not a
research gap. A peer-reviewed comparative review -- "Environmental Risk Assessment in Pharmaceutical Regulation:
A Comparative Review of EMA, U.S. FDA and CDSCO Guidelines", Therapeutic Innovation & Regulatory Science (Springer
Nature) -- states that "the Indian regulator (CDSCO) has no specific ERA (Environmental Risk Assessment)
requirement, and India's Drugs & Cosmetics Act and regulations do not address environmental risk," with pharma
manufacturing emissions instead controlled by the environment ministry's general pollution rules. The article
itself is paywalled and was not fetched -- summarised from the WebSearch result (the article's abstract/snippet),
not primary-verified. <https://link.springer.com/article/10.1007/s43441-026-01035-6>.

**Currency**: INR.

## What is deliberately NOT built from this research

- Still no CALCULABLE quantitative PEC/PNEC or assessment-factor method for any of the four countries, unlike
  AICIS (AU) or ECCC's Okonski method (CA) -- FateIntel cannot run any of these four countries' industrial
  methods. A 2026-09-22 follow-up did upgrade Japan's and China's industrial branches from "agency named only" to
  "real method structure confirmed, current numeric thresholds not verified" (`JP_CSCL_PARTIAL`,
  `CN_MEE_PARTIAL`) after fetching a NITE technical presentation and confirming China's named 2019 MEE/NHC
  guideline. A further, dedicated search for Korea's and India's industrial quantitative methods found nothing
  India- or Korea-specific (both searches turned up generic international risk-assessment conventions or
  unrelated disciplines, e.g. accident/spillage QRA for India's MSIHC) -- those two remain "agency named only."
  Every pesticide pathway across all four remains fully unmapped too, except Japan's named-but-uncalculated PEC
  criterion.
- No EXTERNAL_ROUTES entries for human/ecological/groundwater/surface-water receptors for any of the four --
  only the identified soil/land contamination law is encoded as a named route (`contaminated_land`-style, one
  route rather than per-receptor, since none of the four sources broke their site-level regime down by receptor
  the way UK/US/CA/AU/NZ's sources did).
- China's pesticide administering body (Ministry of Agriculture and Rural Affairs) is attributed with lower
  confidence than Japan's, India's or (as of the 2026-09-22 follow-up) Korea's -- secondary sources only, not
  primary text.
- Veterinary-pharmaceutical and biocide-specific environmental pathways were not researched for any of the four.
  The Korea and India human-pharmaceutical findings above are deliberately NOT extended to
  `veterinary_pharmaceutical` in code, since MFDS and CDSCO are each that country's HUMAN-medicines regulator and
  veterinary medicines plausibly sit with a different body (not confirmed). China's finding is kept for both,
  since it is a manufacturing-category discharge standard, not a human/veterinary regulatory-review split -- but
  that generalisation (that veterinary-drug manufacturing in China actually falls under the same GB standards) was
  not independently confirmed either.
