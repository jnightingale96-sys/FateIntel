"""Contaminant-aware plausibility prompts for site-model pathways, from SOURCED criteria only.

This does not decide anything. For a pathway step it asks: given the substance properties the user supplied
(each with a source), does a published criterion support the pathway's relevance, question it, or is the
evidence inconclusive or missing? A linkage is never removed, no risk is calculated, and "questions relevance"
is a prompt to review, never an exclusion.

Only four criteria were read in primary text and are encoded (see RULES for quotes, pages and URLs):
  * V1  US EPA vapor-intrusion guide (2015), Section 3.1: definition of a "volatile" chemical (the UK Environment
        Agency's CLEA report repeats the same Henry's law value as one used by several regulators; no UK-specific
        volatility criterion was found).
  * B1  Stockholm Convention Annex D 1(c)(i): bioaccumulation screening criterion.
  * B2  UK REACH Annex XIII (retained EU law): B if BCF > 2,000, vB if BCF > 5,000, for organic substances.
  * M1  EU CLP (Delegated Regulation (EU) 2023/707), Annex I 4.4.2.1.2 / 4.4.2.2.2: mobile / very mobile (log Koc);
        the UK government (Defra, June 2025) uses the same values on an interim, non-statutory, PFAS-focused basis.
Each result says whether the criterion is formal in the jurisdiction being assessed or a reference from another regime.
Not encoded, because no primary text supports it: plant uptake, erosion, dermal contact, and any rule that
would exclude a pathway. Pathways without a rule are reported as such.
Property values are never assumed or converted: keys carry their unit and a value needs a source.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .metals import identify_element

SUPPORTS = "SUPPORTS_RELEVANCE"
QUESTIONS = "QUESTIONS_RELEVANCE"
INCONCLUSIVE = "INCONCLUSIVE"
MISSING = "PROPERTY_MISSING"

# key -> (label incl. unit, must be > 0)
PROPERTY_SPECS: dict[str, tuple[str, bool]] = {
    "vapour_pressure_mm_hg": ("vapour pressure (mm Hg)", True),
    "henry_law_constant_atm_m3_mol": ("Henry's law constant (atm-m3/mol)", True),
    "bcf_or_baf_aquatic": ("bioconcentration or bioaccumulation factor, aquatic species (L/kg, dimensionless)", True),
    "log_kow": ("log Kow (octanol-water partition coefficient)", False),
    "log_koc": ("log Koc (common logarithm of the organic carbon-water partition coefficient, Koc in L/kg)", False),
}

RULES: dict[str, dict[str, Any]] = {
    "V1": {
        "title": "US EPA definition of a volatile chemical",
        "criterion": "volatile if vapor pressure > 1 mm Hg, or Henry's law constant > 1e-5 atm-m3/mol",
        "applies_to": "volatilisation pathway; inhalation from soil gas",
        "source": "US EPA OSWER Technical Guide for Assessing and Mitigating the Vapor Intrusion Pathway from "
                  "Subsurface Vapor Sources to Indoor Air (June 2015)",
        "url": "https://www.epa.gov/sites/default/files/2015-09/documents/oswer-vapor-intrusion-technical-guide-final.pdf",
        "quotes": [
            {"page": 58, "section": "3.1 Contaminants of Potential Concern",
             "text": "Several physicochemical criteria may be considered for defining and screening for volatility. For purposes of this "
                     "Technical Guide, a chemical generally is considered to be “volatile” if: 1) Vapor pressure is greater than "
                     "1 millimeter of mercury (mm Hg), or 2) Henry’s law constant (ratio of a chemical’s vapor pressure in air to its "
                     "solubility in water) is greater than 10-5 atmosphere-meter cubed per mole (atm m3 mol-1)"},
            {"page": 87, "document": "Environment Agency, Updated technical background to the CLEA model (Science Report SC050021/SR3, 2009)",
             "url": "https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/291014/scho0508bnqw-e-e.pdf",
             "text": "ITRC (2007) noted that several regulatory agencies have defined volatile chemicals as those with a Henry\u2019s Law constant greater "
                     "than 1 x 10-5 atm m3 mol-1 (that is, greater than 1 Pa m3 mol-1)."},
            {"page": 44, "text": "Other compounds that are not as volatile as these VOCs (e.g., so-called semi-volatile organic compounds), "
                                 "but that may be cause for concern, include some polycyclic aromatic hydrocarbons (PAHs) (e.g., naphthalene), "
                                 "some polychlorinated biphenyl (PCB) congeners, and elemental mercury, a dense NAPL (DNAPL)."},
        ],
        "caveats": [
            "The guide says several physicochemical criteria may be considered for volatility; this is the one it adopts 'for purposes of this Technical Guide'.",
            "This is a US EPA vapor-intrusion definition; other jurisdictions may use different volatility criteria.",
            "The guide itself says some less-volatile compounds can still be of concern, so failing the definition is a prompt to review, not an exclusion.",
            "Within the body of the guide, elemental mercury is the only metal named as a vapour-intrusion concern; it gives no rule for other metals.",
        ],
        "regimes": {
            "US": "US EPA vapor-intrusion guidance (2015)",
            "UK": "No UK volatility criterion was found. The Environment Agency's CLEA technical basis (SR3, 2009) reports this Henry's law value as one used by several regulatory agencies, and does not adopt a threshold of its own.",
        },
        "retrieved": "2026-09-20",
    },
    "B1": {
        "title": "Stockholm Convention Annex D bioaccumulation screening criterion",
        "criterion": "BCF or BAF in aquatic species > 5,000 or, in the absence of such data, log Kow > 5",
        "applies_to": "food-chain transfer",
        "source": "Stockholm Convention on Persistent Organic Pollutants, Annex D (Information requirements and screening "
                  "criteria), paragraph 1(c)(i), 2021 English text",
        "url": "http://chm.pops.int/Portals/0/download.aspx?d=UNEP-POPS-COP-CONVTEXT-2021.English.pdf",
        "quotes": [
            {"page": 68, "text": "Bio-accumulation: (i) Evidence that the bio-concentration factor or bio-accumulation factor in aquatic "
                                 "species for the chemical is greater than 5,000 or, in the absence of such data, that the log Kow is greater than 5"},
        ],
        "caveats": [
            "This is a screening criterion for proposing chemicals for listing, used here only to say whether bioaccumulation is a supported concern.",
            "Below the value, food-chain transfer is NOT excluded: the same Annex lists other reasons for concern, such as high bioaccumulation in other species or monitoring data in biota.",
            "US EPA's Framework for Metals Risk Assessment (2007) cautions against generic BCF/BAF use for metals; log Kow does not describe metals.",
        ],
        "regimes": {"*": "Stockholm Convention screening criterion (international treaty), not a national classification rule"},
        "retrieved": "2026-09-20",
    },
    "B2": {
        "title": "UK REACH Annex XIII bioaccumulation criteria (B and vB)",
        "criterion": "bioaccumulative (B) if the bioconcentration factor in aquatic species > 2,000; very bioaccumulative (vB) if > 5,000; applies to organic substances, including organo-metals",
        "applies_to": "food-chain transfer",
        "source": "Regulation (EC) No 1907/2006 (REACH) as it applies in Great Britain (UK REACH), Annex XIII, criteria for the identification of "
                  "persistent, bioaccumulative and toxic substances and very persistent and very bioaccumulative substances, legislation.gov.uk",
        "url": "https://www.legislation.gov.uk/eur/2006/1907/annex/XIII",
        "quotes": [
            {"locator": "Annex XIII, section 1.1.2 Bioaccumulation",
             "text": "A substance fulfils the bioaccumulation criterion (B) when the bioconcentration factor in aquatic species is higher than 2 000."},
            {"locator": "Annex XIII, very bioaccumulative criterion",
             "text": "A substance fulfils the \u2018very bioaccumulative\u2019 criterion (vB) when the bioconcentration factor in aquatic species is higher than 5 000."},
            {"locator": "Annex XIII, introduction",
             "text": "This Annex shall apply to all organic substances, including organo-metals."},
        ],
        "caveats": [
            "This is the identification criterion for PBT/vPvB substances in UK REACH, applied here only to say whether bioaccumulation is a supported concern for a site pathway.",
            "It needs a BCF in aquatic species; unlike the Stockholm screening criterion it has no log Kow alternative.",
            "Below 2,000 is inconclusive, never a reason to exclude food-chain transfer.",
            "It applies to organic substances, including organo-metals: it is not applied to inorganic metals here.",
        ],
        "regimes": {"UK": "Statutory criterion in UK REACH Annex XIII (retained EU law), used to identify PBT/vPvB substances"},
        "retrieved": "2026-09-20",
    },
    "M1": {
        "title": "EU CLP mobility criteria (mobile and very mobile)",
        "criterion": "mobile (M) if log Koc < 3; very mobile (vM) if log Koc < 2; for an ionisable substance, the lowest log Koc for pH 4 to 9",
        "applies_to": "soil-to-groundwater and groundwater-to-surface-water transport",
        "source": "Commission Delegated Regulation (EU) 2023/707 of 19 December 2022 amending Regulation (EC) No 1272/2008, "
                  "Annex I, Section 4.4 (Persistent, Mobile and Toxic; Very Persistent, Very Mobile), Official Journal L 93, 31.3.2023, pp. 24-25",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32023R0707&from=EN",
        "quotes": [
            {"page": 19, "section": "4.4.2.1.2 Mobility",
             "text": "A substance shall be considered to fulfil the mobility criterion (M) when the log Koc is less than 3. For an ionisable "
                     "substance, the mobility criterion shall be considered fulfilled when the lowest log Koc value for pH between 4 and 9 is less than 3."},
            {"page": 19, "section": "4.4.2.2.2 Mobility",
             "text": "A substance shall be considered to fulfil the \u201cvery mobile\u201d criterion (vM) when the log Koc is less than 2. For an "
                     "ionisable substance, the mobility criterion shall be considered fulfilled when the lowest log Koc value for pH between 4 and 9 is less than 2."},
            {"page": 19, "section": "4.4.2.3 Basis of classification",
             "text": "For the classification of PMT substances and vPvM substances, a weight of evidence determination using expert judgment "
                     "shall be applied, by comparing all relevant and available information"},
            {"page": 18, "section": "4.4.1.1 Definitions",
             "text": "\u201clog Koc\u201d means the common logarithm of the organic carbon-water partition coefficient (i.e. Koc)."},
            {"locator": "paragraph 16", "document": "Defra, Interim approach to the PMT concept to support UK REACH risk management of PFAS (4 June 2025)",
             "url": "https://www.gov.uk/government/publications/interim-position-statement-on-the-approach-to-pmt-concept-to-support-uk-reach-risk-management-of-pfas/interim-approach-to-the-pmt-concept-to-support-uk-reach-risk-management-of-pfas",
             "text": "Koc is too simplistic to determine the potential mobility of PFAS. The dominant retention mechanisms in soils are not yet well understood and vary depending on soil and PFAS properties. "
                     "Nonetheless, Koc is a useful screening measure of mobility and is suitable for identifying many substances that may need additional assessment."},
            {"locator": "paragraph 26", "document": "Defra, Interim approach to the PMT concept to support UK REACH risk management of PFAS (4 June 2025)",
             "url": "https://www.gov.uk/government/publications/interim-position-statement-on-the-approach-to-pmt-concept-to-support-uk-reach-risk-management-of-pfas/interim-approach-to-the-pmt-concept-to-support-uk-reach-risk-management-of-pfas",
             "text": "Definitive criteria are not being formally adopted in UK REACH, or other legislation, as discussions are ongoing internationally, and knowledge and data are evolving."},
        ],
        "caveats": [
            "This is a hazard-classification criterion. Using it as a prompt about how relevant dissolved transport through soil and groundwater is, is FateIntel's application of it, not something the regulation states.",
            "The regulation classifies by weight of evidence using expert judgment (4.4.2.3), so a value at or above the threshold never excludes leaching: persistence, soil properties and ionisation all matter.",
            "For an ionisable substance the criterion uses the lowest log Koc for pH 4 to 9: a single supplied value may not be that value.",
            "The regulation does not state a unit for Koc; enter it in L/kg (equal to mL/g) as is usual in data sources.",
            "The definition is an organic carbon-water partition coefficient, so the criterion is not applied to metals here.",
            "UK (Defra, June 2025): the same log Koc values are used on an interim, non-statutory basis focused on PFAS risk management under UK REACH; the same document says Koc is too simplistic to determine the mobility of PFAS.",
            "Current status of PMT/vPvM classes in GB CLP was not established from primary text (HSE's GB CLP pages do not mention them).",
        ],
        "regimes": {
            "EU": "Hazard classification criterion in EU CLP (Delegated Regulation (EU) 2023/707)",
            "UK": "Interim, non-statutory approach set out by Defra (4 June 2025), focused on PFAS risk management under UK REACH; definitive criteria are not formally adopted",
        },
        "retrieved": "2026-09-20",
    },
}

UNSOURCED_GAPS = (
    "Plant uptake, erosion, dermal contact and runoff: no sourced plausibility rule; these pathways are shown as "
    "modelled by the user.",
    "Jurisdictions other than those named in each rule's regimes (US volatility guidance; EU CLP and UK interim mobility; "
    "UK REACH bioaccumulation): other regimes' criteria are not encoded.",
    "No UK-specific volatility criterion was found (the Environment Agency CLEA report only repeats a value attributed to ITRC 2007).",
    "Current status of PMT/vPvM hazard classes in GB CLP: not established from primary text; HSE's GB CLP pages do not mention them "
    "and secondary sources conflict.",
)


class PropertyError(ValueError):
    """Invalid property value. Never defaulted."""


@dataclass(frozen=True)
class SubstanceProperties:
    """Measured/reported properties, each with the source it came from. Keys carry their unit."""

    values: tuple[tuple[str, float, str], ...] = ()  # (key, value, source)

    def get(self, key: str) -> float | None:
        return next((v for k, v, _ in self.values if k == key), None)

    def source(self, key: str) -> str | None:
        return next((s for k, _, s in self.values if k == key), None)

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {k: {"value": v, "source": s} for k, v, s in self.values}


def properties_from_dict(data: dict[str, Any] | None) -> SubstanceProperties | None:
    if not data:
        return None
    if not isinstance(data, dict):
        raise PropertyError("properties must be an object of {name: {value, source}}")
    out: list[tuple[str, float, str]] = []
    for key, entry in data.items():
        if key not in PROPERTY_SPECS:
            raise PropertyError(f"Unknown property {key!r}; allowed: {sorted(PROPERTY_SPECS)}")
        if not isinstance(entry, dict) or "value" not in entry:
            raise PropertyError(f"{key}: expected {{value, source}}")
        value, source = entry["value"], str(entry.get("source") or "").strip()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise PropertyError(f"{key}: value must be a finite number")
        if PROPERTY_SPECS[key][1] and value <= 0:
            raise PropertyError(f"{key}: value must be greater than zero")
        if not source:
            raise PropertyError(f"{key}: every property value needs a source; none is assumed")
        out.append((key, float(value), source))
    return SubstanceProperties(tuple(out)) if out else None


def _result(rule: str, outcome: str, message: str, basis: list[str] | None = None) -> dict[str, Any]:
    return {"rule": rule, "outcome": outcome, "message": message, "basis": basis or [], "source": RULES[rule]["source"]}


def _regime(rule: str, jurisdiction: str | None) -> tuple[bool, str]:
    """Is this criterion a formal position of the jurisdiction being assessed, or a reference from another regime?"""
    regimes = RULES[rule]["regimes"]
    if "*" in regimes:
        return True, regimes["*"]
    if jurisdiction in regimes:
        return True, regimes[jurisdiction]
    named = "; ".join(f"{k}: {v}" for k, v in regimes.items())
    return False, f"Reference criterion from another regime ({named})"


def _volatility(name: str, group: str, props: SubstanceProperties | None) -> dict[str, Any]:
    vp = props.get("vapour_pressure_mm_hg") if props else None
    hlc = props.get("henry_law_constant_atm_m3_mol") if props else None
    met_vp = vp is not None and vp > 1
    met_hlc = hlc is not None and hlc > 1e-5
    if met_vp or met_hlc:
        which = []
        if met_vp:
            which.append(f"vapour pressure {vp:g} mm Hg > 1 ({props.source('vapour_pressure_mm_hg')})")
        if met_hlc:
            which.append(f"Henry's law constant {hlc:g} atm-m3/mol > 1e-5 ({props.source('henry_law_constant_atm_m3_mol')})")
        return _result("V1", SUPPORTS, "Meets the US EPA definition of a volatile chemical, so a vapour route is a supported concern.", which)
    if vp is not None and hlc is not None:
        return _result(
            "V1", QUESTIONS,
            "Does not meet the US EPA definition of a volatile chemical (both properties are at or below the values), so this vapour "
            "route may be less significant. EPA's own guide notes that some less-volatile compounds (some PAHs such as naphthalene, some "
            "PCB congeners, elemental mercury) can still be of concern: review it, do not exclude it.",
            [f"vapour pressure {vp:g} mm Hg ({props.source('vapour_pressure_mm_hg')})",
             f"Henry's law constant {hlc:g} atm-m3/mol ({props.source('henry_law_constant_atm_m3_mol')})"],
        )
    if vp is not None or hlc is not None:
        have = "vapour pressure" if vp is not None else "Henry's law constant"
        need = "Henry's law constant" if vp is not None else "vapour pressure"
        return _result("V1", INCONCLUSIVE,
                       f"The supplied {have} does not exceed the EPA value, but the definition is 'either' property, so the {need} is needed to apply it.")
    extra = ""
    if group == "metal_inorganic":
        extra = (" For metals the reviewed EPA guide names only elemental mercury as a vapour-intrusion concern and gives no rule for other "
                 "metals; chemical form matters, so supply the properties of the actual form.")
    if identify_element(name) == "Hg":
        extra += " Elemental mercury is named in the guide as a DNAPL of concern that is less volatile than typical VOCs; confirm the form present."
    return _result("V1", MISSING,
                   "No vapour pressure or Henry's law constant supplied, so the EPA volatility definition cannot be applied." + extra)


def _bioaccumulation(name: str, group: str, props: SubstanceProperties | None) -> dict[str, Any]:
    bcf = props.get("bcf_or_baf_aquatic") if props else None
    kow = props.get("log_kow") if props else None
    if group == "metal_inorganic":
        return _result("B1", INCONCLUSIVE,
                       "The Annex D BCF/BAF and log Kow values are not applied to metals here: EPA's Framework for Metals Risk Assessment "
                       "cautions against generic BCF/BAF use for metals and log Kow does not describe them. Use element- and form-specific "
                       "bioaccumulation evidence.")
    if bcf is not None:
        basis = [f"BCF/BAF {bcf:g} ({props.source('bcf_or_baf_aquatic')})"]
        if bcf > 5000:
            return _result("B1", SUPPORTS, "Meets the Stockholm Convention Annex D bioaccumulation screening criterion (BCF/BAF > 5,000), so bioaccumulation is a supported concern.", basis)
        return _result("B1", INCONCLUSIVE, "Below the Annex D screening value (BCF/BAF <= 5,000). This does not exclude food-chain transfer: Annex D lists other reasons for concern.", basis)
    if kow is not None:
        basis = [f"log Kow {kow:g} ({props.source('log_kow')}), used because no BCF/BAF was supplied"]
        if kow > 5:
            return _result("B1", SUPPORTS, "Meets the Annex D screening criterion on log Kow (> 5, in the absence of BCF/BAF data), so bioaccumulation is a supported concern.", basis)
        return _result("B1", INCONCLUSIVE, "Below the Annex D log Kow screening value (<= 5). This does not exclude food-chain transfer.", basis)
    return _result("B1", MISSING, "No BCF/BAF or log Kow supplied, so the Annex D bioaccumulation screening criterion cannot be applied.")


def _mobility(name: str, group: str, props: SubstanceProperties | None) -> dict[str, Any]:
    koc = props.get("log_koc") if props else None
    if group == "metal_inorganic":
        return _result("M1", INCONCLUSIVE,
                       "The CLP mobility criterion is defined on the organic carbon-water partition coefficient, so it is not applied to metals "
                       "here. Use element- and form-specific partitioning evidence for soil and groundwater transport.")
    if koc is None:
        return _result("M1", MISSING, "No log Koc supplied, so the EU CLP mobility criterion cannot be applied.")
    basis = [f"log Koc {koc:g} ({props.source('log_koc')})"]
    ionisable = " For an ionisable substance the regulation uses the lowest log Koc for pH 4 to 9: confirm the supplied value is that value."
    pfas_note = ""
    if group == "pfas_persistent_mobile":
        pfas_note = (" UK Defra (June 2025) states that Koc is too simplistic to determine the potential mobility of PFAS, so treat "
                     "a log Koc for a PFAS with particular caution: a high value does not show low mobility.")
    ionisable += pfas_note
    if koc < 2:
        return _result("M1", SUPPORTS,
                       "Meets the EU CLP criterion for a very mobile substance (log Koc < 2), so dissolved transport through soil and groundwater is a supported concern." + ionisable, basis)
    if koc < 3:
        return _result("M1", SUPPORTS,
                       "Meets the EU CLP criterion for a mobile substance (log Koc < 3), so dissolved transport through soil and groundwater is a supported concern." + ionisable, basis)
    return _result("M1", INCONCLUSIVE,
                   "Does not meet the EU CLP mobility criterion (log Koc >= 3). This does not exclude leaching: the regulation classifies by weight of "
                   "evidence with expert judgment, and if the substance is ionisable the lowest log Koc for pH 4 to 9 may be lower." + pfas_note, basis)


def _bioaccumulation_uk(name: str, group: str, props: SubstanceProperties | None) -> dict[str, Any]:
    bcf = props.get("bcf_or_baf_aquatic") if props else None
    if group == "metal_inorganic":
        return _result("B2", INCONCLUSIVE,
                       "UK REACH Annex XIII applies to organic substances, including organo-metals, so it is not applied to inorganic metals here.")
    if bcf is None:
        return _result("B2", MISSING, "No BCF supplied, so the UK REACH Annex XIII bioaccumulation criteria (B: BCF > 2,000; vB: BCF > 5,000) cannot be applied.")
    basis = [f"BCF {bcf:g} ({props.source('bcf_or_baf_aquatic')})"]
    if bcf > 5000:
        return _result("B2", SUPPORTS, "Meets the UK REACH Annex XIII criterion for a very bioaccumulative substance (vB: BCF > 5,000), so bioaccumulation is a supported concern.", basis)
    if bcf > 2000:
        return _result("B2", SUPPORTS, "Meets the UK REACH Annex XIII criterion for a bioaccumulative substance (B: BCF > 2,000), so bioaccumulation is a supported concern.", basis)
    return _result("B2", INCONCLUSIVE, "Does not meet the UK REACH Annex XIII bioaccumulation criterion (BCF <= 2,000). This does not exclude food-chain transfer.", basis)


_PATHWAY_EVALUATORS = {
    "volatilisation": (_volatility,),
    "food_chain_transfer": (_bioaccumulation, _bioaccumulation_uk),
    "soil_to_groundwater": (_mobility,),
    "groundwater_to_surface_water": (_mobility,),
}


def evaluate_step_all(name: str, group: str, props: SubstanceProperties | None, step: dict[str, str],
                      jurisdiction: str | None = None) -> list[dict[str, Any]]:
    """Every sourced prompt for one pathway step {pathway, from, to}; empty when no sourced rule covers it."""
    pathway = step["pathway"]
    key = "volatilisation" if pathway == "inhalation" and step["from"] == "soil_gas" else pathway
    out = []
    for fn in _PATHWAY_EVALUATORS.get(key, ()):
        result = {"pathway": pathway, **fn(name, group, props)}
        result["in_regime"], result["regime_note"] = _regime(result["rule"], jurisdiction)
        out.append(result)
    return out


def evaluate_step(name: str, group: str, props: SubstanceProperties | None, step: dict[str, str],
                  jurisdiction: str | None = None) -> dict[str, Any] | None:
    """The first prompt for a step (the primary rule), or None when no sourced rule covers it."""
    results = evaluate_step_all(name, group, props, step, jurisdiction)
    return results[0] if results else None


def evaluate_path(name: str, group: str, props: SubstanceProperties | None, path: list[dict[str, str]],
                  jurisdiction: str | None = None) -> list[dict[str, Any]]:
    return [r for step in path for r in evaluate_step_all(name, group, props, step, jurisdiction)]


def rules_metadata() -> dict[str, Any]:
    return {"rules": RULES, "not_encoded": list(UNSOURCED_GAPS),
            "note": "Prompts for review from sourced criteria. A linkage is never removed and no risk is calculated."}
