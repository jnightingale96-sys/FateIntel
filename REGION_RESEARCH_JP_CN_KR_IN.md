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
Retrieved via WebSearch summary, not the full PDF text -- the exact quantitative screening/assessment method
(assessment factors, PEC/PNEC formula for industrial chemicals) was NOT independently verified this session and
is marked not yet mapped, the same way AU's AICIS route only encodes what was actually read in the TGD.

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
this session); the underlying quantitative risk-assessment method was not verified and is not encoded.

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

**Currency**: CNY.

## South Korea

**Industrial/new chemicals**: K-REACH, formally the Act on the Registration and Evaluation of Chemical
Substances (passed 30 April 2013, in force 1 January 2015; substantially amended by Ordinance No. 20232, 6
February 2024). The Ministry of Environment (MoE) administers registration; the National Institute of
Environmental Research (NIER) evaluates the shared dossier to determine whether a substance is allowed,
restricted or banned. Sources: CIRS, "K-REACH Registration", <https://www.cirs-group.com/en/chemicals/k-reach-registration>;
REACH24H, "K-REACH 2025 Amendments", <https://en.reach24h.com/news/insights/chemical/k-reach-2025-amendment>.
Secondary compliance-industry sources; the quantitative risk-assessment method was not verified and is not
encoded.

**Pesticides**: Agrochemicals Control Act ("Pesticide Control Act" in some translations), administered by the
Ministry of Agriculture (secondary-source attribution; whether Rural Development Administration holds the
operational registration role was not confirmed this session and is left as an open question, not asserted).
FAOLEX entry: <https://www.fao.org/faolex/results/details/en/c/LEX-FAOC136704/>.

**Contaminated land**: Soil Environment Conservation Act. Official Korea Legislation Research Institute (KLRI)
translation located this session: <https://elaw.klri.re.kr/eng_service/lawTwoView.do?hseq=14745> (not
independently fetched and read in full this session -- summarised from the WebSearch result, not primary text,
unlike the Japan and China soil laws above). The Act classifies soil contamination into two tiers: pollution "of
concern", where the relevant authority can restrict land use and order remediation, and pollution requiring
"countermeasure", where the area is designated and managed under a countermeasure plan. Administered by the
Ministry of Environment.

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
session -- summarised from a WebSearch result, not primary text.

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

**Human/veterinary pharmaceuticals**: not researched this session for any of the four countries below Japan (see
above); treat as an explicit gap, not a claim of no requirement.

**Currency**: INR.

## What is deliberately NOT built from this research

- No quantitative PEC/PNEC or assessment-factor method for any of the four countries' industrial-chemical or
  pesticide pathway -- unlike AICIS (AU) or ECCC's Okonski method (CA), nothing here was read to primary-document
  depth on the numeric method. Each country's `_regulatory_programme()` branch names the real regime and agency
  and says the quantitative method is not yet mapped, the same pattern already used for CA's PMRA and AU's TGA.
- No EXTERNAL_ROUTES entries for human/ecological/groundwater/surface-water receptors for any of the four --
  only the identified soil/land contamination law is encoded as a named route (`contaminated_land`-style, one
  route rather than per-receptor, since none of the four sources broke their site-level regime down by receptor
  the way UK/US/CA/AU/NZ's sources did).
- China's and Korea's pesticide administering bodies are attributed with lower confidence than Japan's or
  India's (secondary sources only, not primary text).
- Whether any of the four has a veterinary-pharmaceutical or biocide-specific environmental pathway was not
  researched.
