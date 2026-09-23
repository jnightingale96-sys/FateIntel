"""Formal PBT/vPvB and PMT/vPvM classifier, from SOURCED numeric/hazard-classification criteria only.

This mechanically evaluates the criteria Sections 1.1/1.2 of UK REACH Annex XIII lay out for PBT
(persistent, bioaccumulative and toxic) and vPvB (very persistent, very bioaccumulative) substances, and
Section 4.4.2 of EU CLP (Commission Delegated Regulation (EU) 2023/707, Annex I) lays out for PMT
(persistent, mobile and toxic) and vPvM (very persistent, very mobile). Both were read in full, directly,
via the built-in browser (legislation.gov.uk for REACH Annex XIII; eur-lex.europa.eu for the CLP
delegated regulation) -- not summarised by another tool -- on 2026-09-23.

**What this module is NOT**: both regulations state, in their own text, that identification is "a
weight-of-evidence determination using expert judgement... comparing all relevant and available
information" (REACH Annex XIII, introductory paragraph 2; CLP Annex I 4.4.2.3, near-identical wording),
listing extensive additional evidence types (Section 3.2 of REACH Annex XIII; Section 4.4.2.3.1-3 of the
CLP delegated regulation) -- monitoring data, terrestrial bioaccumulation studies, biomagnification
factors, field studies, and more -- beyond the numeric/classification criteria this module evaluates.
This module answers only the narrower, purely mechanical question: given the specific numeric thresholds
and hazard-classification categories the regulations name in Sections 1.1/1.2 (REACH) and 4.4.2.1/4.4.2.2
(CLP), which are met? A "not met" or "inconclusive" result here is never a substitute for the real
weight-of-evidence determination a regulatory dossier requires, and is reported as such throughout.

Reuses the exact BCF (bioaccumulation) and log Koc (mobility) thresholds already shipped in
pathway_plausibility.py's B2 and M1 rules (BCF_B_THRESHOLD_L_PER_KG, BCF_VB_THRESHOLD_L_PER_KG,
LOG_KOC_M_THRESHOLD, LOG_KOC_VM_THRESHOLD) rather than a second, potentially drifting copy of the same
numbers -- the same discipline used when eu_birds_mammals.py's earthworm pathway reused
equilibrium_partitioning.py's soil-partitioning constants instead of re-deriving them.

Persistence (P/vP) criteria are numerically IDENTICAL between REACH Annex XIII 1.1.1/1.2.1 and CLP Annex I
4.4.2.1.1/4.4.2.2.1 (confirmed by reading both primary texts) -- one shared evaluation is used for both.
Toxicity (T) differs by one criterion: CLP's PMT toxicity criterion (4.4.2.1.3) includes everything
REACH's PBT toxicity criterion (Annex XIII 1.1.3) does, plus "the substance meets the criteria for
classification as endocrine disruptor (category 1) for human health or the environment" -- REACH Annex
XIII's PBT toxicity criterion has no endocrine-disruption limb. Neither vPvB nor vPvM require a toxicity
criterion at all -- both regulations define them purely on P/vP + B/vB or M/vM.
"""

from __future__ import annotations

from typing import Any

from .pathway_plausibility import (
    BCF_B_THRESHOLD_L_PER_KG,
    BCF_VB_THRESHOLD_L_PER_KG,
    LOG_KOC_M_THRESHOLD,
    LOG_KOC_VM_THRESHOLD,
)

MET = "CRITERION_MET"
NOT_MET = "CRITERION_NOT_MET"
INCONCLUSIVE = "INCONCLUSIVE"
MISSING = "DATA_MISSING"
NOT_APPLICABLE = "NOT_APPLICABLE_TO_SUBSTANCE_GROUP"

# Both regimes apply to ORGANIC substances, including organo-metals (REACH Annex XIII introductory text; CLP Annex I
# 4.4.2.3). A random-chemical validation run fed aluminium's experimental BCF (73,300 from EPA CompTox) through this
# classifier and got "very bioaccumulative" -- a meaningless answer, since a BCF of that kind is not the organic-
# substance B criterion at all. Callers that know the substance group must say so.
NON_ORGANIC_GROUPS = frozenset({"metal_inorganic", "radionuclide"})

REACH_ANNEX_XIII_SOURCE = (
    "Regulation (EC) No 1907/2006 (REACH) as it applies in Great Britain (UK REACH), Annex XIII, "
    "Sections 1.1 (PBT) and 1.2 (vPvB), legislation.gov.uk"
)
REACH_ANNEX_XIII_URL = "https://www.legislation.gov.uk/eur/2006/1907/annex/XIII"
CLP_PMT_SOURCE = (
    "Regulation (EC) No 1272/2008 (CLP) Annex I, Section 4.4, as inserted by Commission Delegated "
    "Regulation (EU) 2023/707 of 19 December 2022, Official Journal L 93, 31.3.2023"
)
CLP_PMT_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023R0707"

WEIGHT_OF_EVIDENCE_CAVEAT = (
    "Both regulations require a weight-of-evidence determination using expert judgement over all relevant "
    "and available information (REACH Annex XIII, introductory paragraph 2; CLP Annex I 4.4.2.3) -- this "
    "classifier only evaluates the specific numeric thresholds and hazard-classification categories named "
    "in REACH Annex XIII Sections 1.1/1.2 and CLP Annex I Sections 4.4.2.1/4.4.2.2. It never performs the "
    "full weight-of-evidence assessment (monitoring data, terrestrial bioaccumulation studies, "
    "biomagnification/trophic magnification factors, field studies and more -- REACH Annex XIII Section "
    "3.2; CLP Annex I 4.4.2.3.1-3), so 'not met' or 'inconclusive' here is never a substitute for a real "
    "regulatory PBT/vPvB/PMT/vPvM determination."
)

# UK REACH Annex XIII 1.1.1 (PBT) / CLP Annex I 4.4.2.1.1 (PMT) -- identical thresholds, confirmed by
# reading both primary texts directly.
P_HALF_LIFE_THRESHOLD_DAYS: dict[str, int] = {
    "marine_water": 60,
    "freshwater_or_estuarine_water": 40,
    "marine_sediment": 180,
    "freshwater_or_estuarine_sediment": 120,
    "soil": 120,
}
# UK REACH Annex XIII 1.2.1 (vPvB) / CLP Annex I 4.4.2.2.1 (vPvM) -- also identical between the two.
VP_HALF_LIFE_THRESHOLD_DAYS: dict[str, int] = {
    "marine_water": 60,
    "freshwater_or_estuarine_water": 60,
    "marine_sediment": 180,
    "freshwater_or_estuarine_sediment": 180,
    "soil": 180,
}
HALF_LIFE_COMPARTMENTS = tuple(P_HALF_LIFE_THRESHOLD_DAYS)

T_NOEC_OR_EC10_THRESHOLD_MG_L = 0.01


class ClassifierInputError(ValueError):
    """Invalid input. Never defaulted, never guessed."""


def _half_life_determination(half_life_days: dict[str, float] | None, thresholds: dict[str, int], *, label: str) -> dict[str, Any]:
    supplied = dict(half_life_days or {})
    unknown = set(supplied) - set(thresholds)
    if unknown:
        raise ClassifierInputError(f"Unknown half-life compartment(s) {sorted(unknown)}; allowed: {sorted(thresholds)}")
    for key, value in supplied.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ClassifierInputError(f"half_life_days[{key!r}] must be a positive number of days")

    exceeding = {k: v for k, v in supplied.items() if v > thresholds[k]}
    if exceeding:
        basis = [f"{k.replace('_', ' ')} half-life {v:g} days > {thresholds[k]} days" for k, v in exceeding.items()]
        return {"outcome": MET, "basis": basis, "compartments_supplied": sorted(supplied)}
    if not supplied:
        return {"outcome": MISSING, "basis": [], "compartments_supplied": []}
    if set(supplied) >= set(thresholds):
        basis = [f"{k.replace('_', ' ')} half-life {v:g} days <= {thresholds[k]} days" for k, v in supplied.items()]
        return {"outcome": NOT_MET, "basis": basis, "compartments_supplied": sorted(supplied)}
    basis = [f"{k.replace('_', ' ')} half-life {v:g} days <= {thresholds[k]} days" for k, v in supplied.items()]
    missing_compartments = sorted(set(thresholds) - set(supplied))
    return {
        "outcome": INCONCLUSIVE, "basis": basis, "compartments_supplied": sorted(supplied),
        "note": f"Only {len(supplied)} of {len(thresholds)} compartments supplied for the {label} criterion "
                f"(missing: {', '.join(c.replace('_', ' ') for c in missing_compartments)}); the criterion is "
                "met if ANY compartment exceeds its threshold, so an unmeasured compartment could still meet it.",
    }


def _bioaccumulation_determination(bcf_l_per_kg: float | None) -> dict[str, Any]:
    if bcf_l_per_kg is None:
        return {"outcome": MISSING, "basis": []}
    if isinstance(bcf_l_per_kg, bool) or not isinstance(bcf_l_per_kg, (int, float)) or bcf_l_per_kg <= 0:
        raise ClassifierInputError("bcf_l_per_kg must be a positive number")
    basis = [f"BCF {bcf_l_per_kg:g} L/kg"]
    vb = bcf_l_per_kg > BCF_VB_THRESHOLD_L_PER_KG
    b = bcf_l_per_kg > BCF_B_THRESHOLD_L_PER_KG
    return {
        "outcome": MET if b else INCONCLUSIVE, "vb_outcome": MET if vb else INCONCLUSIVE, "basis": basis,
        "note": None if b else "BCF at or below the B threshold does not itself rule out bioaccumulation -- REACH Annex XIII Section 3.2.2 lists further evidence types (terrestrial bioaccumulation studies, biomagnification factors, human tissue data) not evaluated here.",
    }


def _mobility_determination(log_koc: float | None) -> dict[str, Any]:
    if log_koc is None:
        return {"outcome": MISSING, "basis": []}
    if isinstance(log_koc, bool) or not isinstance(log_koc, (int, float)):
        raise ClassifierInputError("log_koc must be a number")
    basis = [f"log Koc {log_koc:g}"]
    vm = log_koc < LOG_KOC_VM_THRESHOLD
    m = log_koc < LOG_KOC_M_THRESHOLD
    return {
        "outcome": MET if m else INCONCLUSIVE, "vm_outcome": MET if vm else INCONCLUSIVE, "basis": basis,
        "note": None if m else "log Koc at or above the M threshold does not itself rule out mobility -- for an ionisable substance the regulation uses the lowest log Koc for pH 4 to 9, which a single supplied value may not be.",
    }


def _toxicity_determination(
    *,
    noec_or_ec10_mg_l: float | None,
    carcinogenic_category_1a_1b: bool,
    germ_cell_mutagen_category_1a_1b: bool,
    reproductive_toxicant_category_1a_1b_2: bool,
    stot_re_category_1_2: bool,
    endocrine_disruptor_category_1: bool,
    include_endocrine_disruptor_criterion: bool,
) -> dict[str, Any]:
    if noec_or_ec10_mg_l is not None and (isinstance(noec_or_ec10_mg_l, bool) or not isinstance(noec_or_ec10_mg_l, (int, float)) or noec_or_ec10_mg_l <= 0):
        raise ClassifierInputError("noec_or_ec10_mg_l must be a positive number")

    met_flags: list[str] = []
    if noec_or_ec10_mg_l is not None and noec_or_ec10_mg_l < T_NOEC_OR_EC10_THRESHOLD_MG_L:
        met_flags.append(f"long-term NOEC/EC10 {noec_or_ec10_mg_l:g} mg/L < {T_NOEC_OR_EC10_THRESHOLD_MG_L} mg/L")
    if carcinogenic_category_1a_1b:
        met_flags.append("classified carcinogenic category 1A or 1B")
    if germ_cell_mutagen_category_1a_1b:
        met_flags.append("classified germ cell mutagenic category 1A or 1B")
    if reproductive_toxicant_category_1a_1b_2:
        met_flags.append("classified toxic for reproduction category 1A, 1B or 2")
    if stot_re_category_1_2:
        met_flags.append("classified STOT RE (specific target organ toxicity, repeated exposure) category 1 or 2")
    if include_endocrine_disruptor_criterion and endocrine_disruptor_category_1:
        met_flags.append("classified endocrine disruptor category 1 (human health or environment)")

    any_input_supplied = (
        noec_or_ec10_mg_l is not None or carcinogenic_category_1a_1b or germ_cell_mutagen_category_1a_1b
        or reproductive_toxicant_category_1a_1b_2 or stot_re_category_1_2
        or (include_endocrine_disruptor_criterion and endocrine_disruptor_category_1)
    )
    if met_flags:
        return {"outcome": MET, "basis": met_flags}
    if noec_or_ec10_mg_l is None and not any_input_supplied:
        return {"outcome": MISSING, "basis": []}
    basis = []
    if noec_or_ec10_mg_l is not None:
        basis.append(f"long-term NOEC/EC10 {noec_or_ec10_mg_l:g} mg/L >= {T_NOEC_OR_EC10_THRESHOLD_MG_L} mg/L")
    return {
        "outcome": INCONCLUSIVE, "basis": basis,
        "note": "None of the supplied hazard-classification flags or the NOEC/EC10 value met the toxicity criterion; this does not rule out toxicity -- other unclassified endpoints (e.g. long-term invertebrate/fish/algal toxicity data, avian reproductive toxicity) are not evaluated here.",
    }


def _not_applicable(group: str, source: str, source_url: str, keys: tuple[str, ...], headline: tuple[str, ...]) -> dict[str, Any]:
    reason = (
        f"The substance group '{group}' is not an organic substance, and this regime applies only to organic "
        "substances including organo-metals; use element- and form-specific evidence instead."
    )
    block = {"outcome": NOT_APPLICABLE, "basis": [], "note": reason}
    result: dict[str, Any] = {key: dict(block) for key in keys}
    result.update({name: NOT_APPLICABLE for name in headline})
    result.update({"source": source, "source_url": source_url, "caveat": WEIGHT_OF_EVIDENCE_CAVEAT, "scope_note": reason})
    return result


def _combine(*determinations: dict[str, Any]) -> str:
    # All named criteria are AND-combined (PBT needs P and B and T; PMT needs P and M and T; the vP/vB and
    # vP/vM pairs likewise). One conclusive NOT_MET therefore settles the whole determination regardless of
    # what is still unknown elsewhere -- checked before MISSING for that reason, not after.
    outcomes = [d["outcome"] for d in determinations]
    if any(o == NOT_MET for o in outcomes):
        return NOT_MET
    if any(o == MISSING for o in outcomes):
        return MISSING
    if all(o == MET for o in outcomes):
        return MET
    return INCONCLUSIVE


def classify_pbt_and_vpvb(
    *,
    half_life_days: dict[str, float] | None = None,
    bcf_l_per_kg: float | None = None,
    noec_or_ec10_mg_l: float | None = None,
    carcinogenic_category_1a_1b: bool = False,
    germ_cell_mutagen_category_1a_1b: bool = False,
    reproductive_toxicant_category_1a_1b_2: bool = False,
    stot_re_category_1_2: bool = False,
    substance_group: str | None = None,
) -> dict[str, Any]:
    """UK REACH Annex XIII Sections 1.1 (PBT) and 1.2 (vPvB) -- organic substances, including organo-metals only.

    ``half_life_days`` keys are any of HALF_LIFE_COMPARTMENTS; only supplied compartments are evaluated (P/vP
    are OR conditions across compartments, so an unmeasured compartment could still meet the criterion --
    see the ``note`` on the persistence result when fewer than all five are supplied). vPvB does not require
    a toxicity criterion (Annex XIII 1.2), so ``toxicity`` is reported for information only and does not gate
    the ``vpvb`` determination.
    """

    if substance_group in NON_ORGANIC_GROUPS:
        return _not_applicable(
            substance_group, REACH_ANNEX_XIII_SOURCE, REACH_ANNEX_XIII_URL,
            ("persistence", "very_persistence", "bioaccumulation", "very_bioaccumulation", "toxicity"), ("pbt", "vpvb"),
        )
    p = _half_life_determination(half_life_days, P_HALF_LIFE_THRESHOLD_DAYS, label="P (persistent)")
    vp = _half_life_determination(half_life_days, VP_HALF_LIFE_THRESHOLD_DAYS, label="vP (very persistent)")
    b_result = _bioaccumulation_determination(bcf_l_per_kg)
    b = {"outcome": b_result["outcome"], "basis": b_result["basis"], "note": b_result.get("note")}
    vb = {"outcome": b_result.get("vb_outcome", MISSING), "basis": b_result["basis"]}
    t = _toxicity_determination(
        noec_or_ec10_mg_l=noec_or_ec10_mg_l,
        carcinogenic_category_1a_1b=carcinogenic_category_1a_1b,
        germ_cell_mutagen_category_1a_1b=germ_cell_mutagen_category_1a_1b,
        reproductive_toxicant_category_1a_1b_2=reproductive_toxicant_category_1a_1b_2,
        stot_re_category_1_2=stot_re_category_1_2,
        endocrine_disruptor_category_1=False,
        include_endocrine_disruptor_criterion=False,
    )

    return {
        "persistence": p, "very_persistence": vp, "bioaccumulation": b, "very_bioaccumulation": vb, "toxicity": t,
        "pbt": _combine(p, b, t),
        "vpvb": _combine(vp, vb),
        "source": REACH_ANNEX_XIII_SOURCE, "source_url": REACH_ANNEX_XIII_URL,
        "caveat": WEIGHT_OF_EVIDENCE_CAVEAT,
        "scope_note": "Applies to organic substances, including organo-metals (REACH Annex XIII, introductory text); not applied to inorganic metals.",
    }


def classify_pmt_and_vpvm(
    *,
    half_life_days: dict[str, float] | None = None,
    log_koc: float | None = None,
    noec_or_ec10_mg_l: float | None = None,
    carcinogenic_category_1a_1b: bool = False,
    germ_cell_mutagen_category_1a_1b: bool = False,
    reproductive_toxicant_category_1a_1b_2: bool = False,
    stot_re_category_1_2: bool = False,
    endocrine_disruptor_category_1: bool = False,
    substance_group: str | None = None,
) -> dict[str, Any]:
    """EU CLP (Delegated Regulation (EU) 2023/707), Annex I Sections 4.4.2.1 (PMT) and 4.4.2.2 (vPvM).

    Persistence thresholds are numerically identical to REACH Annex XIII's PBT/vPvB persistence criteria
    (confirmed by reading both primary texts) -- see ``classify_pbt_and_vpvb`` for the same compartment
    semantics. The toxicity criterion here additionally includes endocrine-disruptor category 1
    classification (CLP Annex I 4.4.2.1.3(d)), which REACH Annex XIII's PBT toxicity criterion does not
    have. vPvM does not require a toxicity criterion (CLP Annex I 4.4.2.2), matching vPvB.
    """

    if substance_group in NON_ORGANIC_GROUPS:
        return _not_applicable(
            substance_group, CLP_PMT_SOURCE, CLP_PMT_URL,
            ("persistence", "very_persistence", "mobility", "very_mobility", "toxicity"), ("pmt", "vpvm"),
        )
    p = _half_life_determination(half_life_days, P_HALF_LIFE_THRESHOLD_DAYS, label="P (persistent)")
    vp = _half_life_determination(half_life_days, VP_HALF_LIFE_THRESHOLD_DAYS, label="vP (very persistent)")
    m_result = _mobility_determination(log_koc)
    m = {"outcome": m_result["outcome"], "basis": m_result["basis"], "note": m_result.get("note")}
    vm = {"outcome": m_result.get("vm_outcome", MISSING), "basis": m_result["basis"]}
    t = _toxicity_determination(
        noec_or_ec10_mg_l=noec_or_ec10_mg_l,
        carcinogenic_category_1a_1b=carcinogenic_category_1a_1b,
        germ_cell_mutagen_category_1a_1b=germ_cell_mutagen_category_1a_1b,
        reproductive_toxicant_category_1a_1b_2=reproductive_toxicant_category_1a_1b_2,
        stot_re_category_1_2=stot_re_category_1_2,
        endocrine_disruptor_category_1=endocrine_disruptor_category_1,
        include_endocrine_disruptor_criterion=True,
    )

    return {
        "persistence": p, "very_persistence": vp, "mobility": m, "very_mobility": vm, "toxicity": t,
        "pmt": _combine(p, m, t),
        "vpvm": _combine(vp, vm),
        "source": CLP_PMT_SOURCE, "source_url": CLP_PMT_URL,
        "caveat": WEIGHT_OF_EVIDENCE_CAVEAT,
        "scope_note": "Applies to all organic substances, including organo-metals (CLP Annex I 4.4.2.3); not applied to inorganic metals.",
    }
