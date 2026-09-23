from __future__ import annotations

import math
import re
from typing import Literal, Any

IonisationClass = Literal["acid", "base", "neutral"]

# Exact coefficients represented in the supplied Droge–Goss cation workbook.
MCGOWAN_ATOMIC_VOLUMES = {
    "C": 16.35,
    "H": 8.71,
    "N": 14.39,
    "O": 12.43,
    "Cl": 20.95,
    "F": 12.48,
    "S": 22.91,
    "I": 34.53,
    "B": 18.32,
}
MCGOWAN_BOND_CORRECTION = 6.56
DG_LOG_KOC_INCREMENTS = {
    "oh_groups": -0.1,
    "nh2_groups": 0.6,
    "ether_groups": -0.6,
    "ester_groups": -0.8,
    "ketone_groups": 0.1,
    "amide_groups": -1.4,
    "single_ring_charged_pyridines": 0.3,
    "chloro_groups": 0.5,
    "carboxamide_groups": -0.7,
    "multi_ring_charged_n": 0.7,
}
DG_LOG_KCEC_INCREMENTS = {
    "oh_groups": -0.3,
    "nh2_groups": 0.0,
    "ether_groups": -0.4,
    "ester_groups": -0.7,
    "ketone_groups": -0.2,
    "amide_groups": -1.2,
    # The corresponding workbook cell is blank; it contributes zero.
    "single_ring_charged_pyridines": 0.0,
    "chloro_groups": 0.2,
    "carboxamide_groups": -0.4,
    "multi_ring_charged_n": 0.1,
}
DG_GROUP_KEYS = tuple(DG_LOG_KOC_INCREMENTS)


def infer_ionisation_class(
    mode: str,
    pkaa: float | None,
    pkab: float | None,
) -> IonisationClass:
    if mode in {"acid", "base", "neutral"}:
        return mode
    if mode != "auto":
        raise ValueError("Mode must be auto, acid, base or neutral")
    has_a = pkaa is not None
    has_b = pkab is not None
    if has_a and has_b:
        raise ValueError(
            "Amphoteric/zwitterionic chemicals are outside this prototype's applicability domain."
        )
    if has_a:
        return "acid"
    if has_b:
        return "base"
    return "neutral"


# Sanity bounds for a data-entry check, NOT a claim about any regression's calibration range. A random-chemical
# validation run (2026-09-23) pulled "experimental" log Kow values from EPA CompTox for real chemicals and found
# entries such as 65.0 (recorded beside a second value of 2.68 for the same compound, 2'-acetonaphthone) and a lone
# 10.0 for a salicylanilide; passed through unchecked, the median 33.84 produced log Koc = 26.8. No real organic
# compound has a log Kow anywhere near that, so such an input is an entry/unit/source error, not chemistry.
LOG_KOW_PLAUSIBLE_MIN = -10.0
LOG_KOW_PLAUSIBLE_MAX = 20.0
LOG_KOW_EXTRAPOLATION_WARNING = 8.0


def _log_kow_advisories(log_kow: float) -> list[str]:
    if log_kow > LOG_KOW_EXTRAPOLATION_WARNING:
        return [
            f"log Kow {log_kow:g} is above {LOG_KOW_EXTRAPOLATION_WARNING:g}: measured values this high are rarely reliable and "
            "the regression is being extrapolated. In an external check against 223 experimental Koc values "
            "(EPA CompTox/OPERA), neutral compounds with log Kow >= 4 were over-predicted by about +0.4 log units "
            "on average; verify the log Kow source and prefer a measured Koc."
        ]
    return []


def _validate_common(log_kow: float, foc: float, soil_ph: float, ionic_strength: float) -> None:
    if not math.isfinite(log_kow):
        raise ValueError("logKow/logP must be finite")
    if not LOG_KOW_PLAUSIBLE_MIN <= log_kow <= LOG_KOW_PLAUSIBLE_MAX:
        raise ValueError(
            f"log Kow {log_kow:g} is outside the physically plausible range {LOG_KOW_PLAUSIBLE_MIN:g} to "
            f"{LOG_KOW_PLAUSIBLE_MAX:g}; this is almost certainly a data-entry, unit or source error "
            "(aggregated experimental databases contain such values). Check the source, or supply a measured Koc directly."
        )
    if foc <= 0 or foc > 1:
        raise ValueError("Organic carbon fraction must be >0 and <=1 (g/g)")
    if not 0 <= soil_ph <= 14:
        raise ValueError("Soil pH must be between 0 and 14")
    if ionic_strength < 0:
        raise ValueError("Ionic strength cannot be negative")


def parse_molecular_formula(formula: str | None) -> dict[str, int]:
    """Parse a simple molecular formula into the atom counts required by the workbook.

    Salts, dot-disconnected formulas and bracketed hydrates require manual review. The
    parser deliberately rejects unrecognised text rather than silently losing atoms.
    """
    if not formula:
        return {}
    cleaned = formula.strip().replace(" ", "")
    if not cleaned:
        return {}
    if any(x in cleaned for x in ("·", ".", "(", ")", "[", "]", "+", "-")):
        raise ValueError("Complex, salt or hydrate formulas require reviewed manual atom counts")
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", cleaned)
    if not tokens or "".join(f"{element}{count}" for element, count in tokens) != cleaned:
        raise ValueError("Molecular formula could not be parsed completely")
    counts: dict[str, int] = {}
    for element, count in tokens:
        if element not in MCGOWAN_ATOMIC_VOLUMES:
            raise ValueError(f"Element {element} is outside the supplied McGowan-volume worksheet")
        counts[element] = counts.get(element, 0) + (int(count) if count else 1)
    return counts


def mcgowan_volume_from_counts(
    atom_counts: dict[str, int],
    ring_count: int,
    bond_count: int | None = None,
) -> dict[str, Any]:
    if ring_count < 0:
        raise ValueError("ring_count cannot be negative")
    counts = {element: int(atom_counts.get(element, 0) or 0) for element in MCGOWAN_ATOMIC_VOLUMES}
    if any(value < 0 for value in counts.values()):
        raise ValueError("Atom counts cannot be negative")
    atom_total = sum(counts.values())
    if atom_total <= 0:
        raise ValueError("Atom counts or a reviewed McGowan volume are required for Droge–Goss")
    estimated = bond_count is None
    workbook_bond_count = atom_total - 1 + (ring_count if ring_count > 0 else 0)
    bonds = workbook_bond_count if estimated else int(bond_count)
    if bonds < 0:
        raise ValueError("bond_count cannot be negative")
    numerator = sum(counts[element] * volume for element, volume in MCGOWAN_ATOMIC_VOLUMES.items())
    numerator -= bonds * MCGOWAN_BOND_CORRECTION
    vx = numerator / 100.0
    if vx <= 0:
        raise ValueError("Calculated McGowan volume is not positive; review atom and bond counts")
    return {
        "mcgowan_volume_vx": vx,
        "atom_counts": counts,
        "ring_count": ring_count,
        "bond_count": bonds,
        "bond_count_was_estimated": estimated,
        "workbook_bond_count_formula": "sum(atom counts) - 1 + ring count (ring term omitted when zero)",
    }


def franco_trapp(
    ionisation_class: Literal["acid", "base"],
    log_kow: float,
    pka: float,
    soil_ph: float,
    ionic_strength_mol_l: float,
    organic_carbon_fraction: float,
) -> dict:
    _validate_common(log_kow, organic_carbon_fraction, soil_ph, ionic_strength_mol_l)
    if not math.isfinite(pka):
        raise ValueError("pKa must be finite")

    if ionisation_class == "acid":
        z = -1
        log_koc_neutral = 0.54 * log_kow + 1.11
        log_koc_ion = 0.11 * log_kow + 1.54
        labels = ("neutral acid", "anion")
    elif ionisation_class == "base":
        z = 1
        log_koc_neutral = 0.42 * log_kow + 1.34
        log_koc_ion = 0.47 * log_kow + 1.95
        labels = ("neutral base", "cation")
    else:
        raise ValueError("Franco–Trapp requires acid or base classification")

    gamma_neutral = 10 ** (0.3 * ionic_strength_mol_l)
    sqrt_i = math.sqrt(ionic_strength_mol_l)
    gamma_ion = 10 ** (
        -0.5 * z * z * (sqrt_i / (1 + sqrt_i) - 0.3 * ionic_strength_mol_l)
    )
    dissociation_term = 10 ** (z * (pka - soil_ph))
    neutral_term = 1 / (1 / gamma_neutral + dissociation_term / gamma_ion)
    ionic_term = neutral_term * dissociation_term

    koc_neutral = 10 ** log_koc_neutral
    koc_ion = 10 ** log_koc_ion
    koc_apparent = koc_neutral * neutral_term + koc_ion * ionic_term
    kd = koc_apparent * organic_carbon_fraction

    return {
        "model_key": f"FRANCO_TRAPP_{ionisation_class.upper()}",
        "model_name": f"Franco & Trapp (2008) — {ionisation_class}",
        "selected_output_kind": "apparent Koc",
        "koc_l_kg": koc_apparent,
        "kd_l_kg": kd,
        "log_koc": math.log10(koc_apparent),
        "log_kd": math.log10(kd),
        "species": {
            "neutral_label": labels[0],
            "ionic_label": labels[1],
            "log_koc_neutral": log_koc_neutral,
            "log_koc_ion": log_koc_ion,
            "koc_neutral_l_kg": koc_neutral,
            "koc_ion_l_kg": koc_ion,
            "gamma_neutral": gamma_neutral,
            "gamma_ion": gamma_ion,
            "dissociation_term": dissociation_term,
            "neutral_activity_term": neutral_term,
            "ionic_activity_term": ionic_term,
        },
        "formula_trace": [
            f"log Koc ({labels[0]}) = {log_koc_neutral:.8g}",
            f"log Koc ({labels[1]}) = {log_koc_ion:.8g}",
            f"gamma neutral = {gamma_neutral:.8g}",
            f"gamma ion = {gamma_ion:.8g}",
            f"dissociation term = 10^[z × (pKa − pH)] = {dissociation_term:.8g}",
            f"apparent Koc = Koc_neutral × fon + Koc_ion × fod = {koc_apparent:.8g} L/kg",
            f"Kd = apparent Koc × fOC = {kd:.8g} L/kg",
        ],
        "assumptions": [
            "Uses the linear Franco and Trapp regressions represented in the supplied workbook.",
            "The workbook's activity-adjusted neutral and ionic terms are reproduced exactly.",
            "The pKa membrane correction and logKow of the ion are not used in the workbook Koc calculation.",
        ],
        "warnings": _log_kow_advisories(log_kow),
    }


def li_neutral(
    log_kow: float,
    organic_carbon_fraction: float,
    variant: Literal["publication", "workbook_literal"] = "publication",
) -> dict:
    _validate_common(log_kow, organic_carbon_fraction, 7.0, 0.0)
    toc_percent = organic_carbon_fraction * 100

    if variant == "publication":
        slope = 0.779
        toc_used = toc_percent
        name = "Li, Carter & Boxall (2020) — publication-aligned neutral model"
        note = "Uses the published coefficient 0.779 and the scenario TOC (%) derived from fOC."
    elif variant == "workbook_literal":
        slope = 0.799
        toc_used = 1.64
        name = "Li neutral model — supplied workbook literal"
        note = "Reproduces cell E3 exactly: coefficient 0.799 and hard-coded TOC = 1.64%."
    else:
        raise ValueError("Unknown neutral-model variant")

    log_kd = slope * log_kow + 0.211 * toc_used - 1.729
    kd = 10 ** log_kd
    koc = kd / organic_carbon_fraction

    warnings = _log_kow_advisories(log_kow)
    if log_kow <= 0.85:
        warnings.append("Published neutral-model applicability states logKow > 0.85.")
    if variant == "workbook_literal":
        warnings.append(
            "The workbook differs from the publication: 0.799 versus 0.779 and fixed 1.64% TOC."
        )

    return {
        "model_key": f"LI_NEUTRAL_{variant.upper()}",
        "model_name": name,
        "selected_output_kind": "Kd converted to Koc",
        "koc_l_kg": koc,
        "kd_l_kg": kd,
        "log_koc": math.log10(koc),
        "log_kd": log_kd,
        "toc_percent_used": toc_used,
        "formula_trace": [
            f"log Kd = {slope} × logKow + 0.211 × TOC(%) − 1.729",
            f"log Kd = {log_kd:.8g}",
            f"Kd = 10^logKd = {kd:.8g} L/kg",
            f"Koc = Kd / fOC = {koc:.8g} L/kg",
        ],
        "assumptions": [note, "TOC is expressed as percent in the regression; fOC is g/g for Koc conversion."],
        "warnings": warnings,
    }


def ecetoc_base_workbook(
    log_kow: float,
    organic_carbon_fraction: float,
) -> dict:
    _validate_common(log_kow, organic_carbon_fraction, 7.0, 0.0)
    log_koc = 0.31 * log_kow + 2.78
    koc = 10 ** log_koc
    kd = koc * organic_carbon_fraction
    return {
        "model_key": "ECETOC_BASE_WORKBOOK",
        "model_name": "ECETOC base regression — supplied workbook",
        "selected_output_kind": "Koc screening estimate",
        "koc_l_kg": koc,
        "kd_l_kg": kd,
        "log_koc": log_koc,
        "log_kd": math.log10(kd),
        "formula_trace": [
            "log Koc = 0.31 × logKow + 2.78",
            f"log Koc = {log_koc:.8g}",
            f"Koc = 10^logKoc = {koc:.8g} L/kg",
            f"Kd = Koc × fOC = {kd:.8g} L/kg",
        ],
        "assumptions": [
            "Reproduces cells G3:H3 of the supplied sorption workbook.",
            "The worksheet label 'Kd' at G3 is treated as log Koc because H3 is 10^G3 and is labelled Koc.",
            "This regression does not use pH, pKa, ionic strength or cation-exchange capacity.",
        ],
        "warnings": [
            "ECETOC is retained as a rapid comparison; it does not represent the clay-CEC contribution included by Droge–Goss.",
            "Measured performance: against 223 experimental Koc values (EPA CompTox/OPERA, random sample, 2026-09-23) this "
            "regression over-predicted log Koc by about +1.0 log units on average (only 17% of chemicals within 0.5 log "
            "units), for neutrals and bases alike. Treat it as an upper-sorption comparison, not a best estimate.",
            *_log_kow_advisories(log_kow),
        ],
    }


def droge_goss_cation(payload: dict[str, Any]) -> dict[str, Any]:
    foc = float(payload["organic_carbon_fraction"])
    cec_total = float(payload.get("cec_total_mol_c_kg") or 0)
    if foc <= 0 or foc > 1:
        raise ValueError("Organic carbon fraction must be >0 and <=1 (g/g)")
    if cec_total <= 0:
        raise ValueError("Droge–Goss requires total soil CEC in mol charge/kg dry soil")

    reviewed_vx = payload.get("mcgowan_volume_vx")
    formula_counts = parse_molecular_formula(payload.get("molecular_formula"))
    manual_counts = {
        element: payload.get(f"atom_{element.lower() if element != 'Cl' else 'cl'}")
        for element in MCGOWAN_ATOMIC_VOLUMES
    }
    counts = {}
    count_conflicts: list[str] = []
    for element in MCGOWAN_ATOMIC_VOLUMES:
        manual_value = manual_counts.get(element)
        formula_value = int(formula_counts.get(element, 0))
        if manual_value is not None and formula_counts and int(manual_value) != formula_value:
            count_conflicts.append(f"{element}: manual {int(manual_value)} versus formula {formula_value}")
        counts[element] = int(manual_value) if manual_value is not None else formula_value
    if count_conflicts:
        raise ValueError("Manual atom counts conflict with molecular formula (" + "; ".join(count_conflicts) + ")")

    if reviewed_vx is not None:
        vx = float(reviewed_vx)
        if vx <= 0:
            raise ValueError("Reviewed McGowan volume must be positive")
        volume_record = {
            "mcgowan_volume_vx": vx,
            "atom_counts": counts,
            "ring_count": int(payload.get("ring_count") or 0),
            "bond_count": payload.get("bond_count"),
            "bond_count_was_estimated": False,
            "workbook_bond_count_formula": None,
        }
    else:
        volume_record = mcgowan_volume_from_counts(
            counts,
            int(payload.get("ring_count") or 0),
            int(payload["bond_count"]) if payload.get("bond_count") is not None else None,
        )
        vx = volume_record["mcgowan_volume_vx"]

    nai = float(payload.get("n_h_attached_to_cationic_n") or 0)
    if nai < 0:
        raise ValueError("Nai cannot be negative")
    groups = {key: float(payload.get(key) or 0) for key in DG_GROUP_KEYS}
    if any(value < 0 for value in groups.values()):
        raise ValueError("Droge–Goss functional-group counts cannot be negative")

    log_koc_om = 1.53 * vx + 0.32 * nai - 0.27
    log_kcec_clay = 1.22 * vx - 0.21 * nai + 2.09 - 1.0
    for key, value in groups.items():
        log_koc_om += value * DG_LOG_KOC_INCREMENTS[key]
        log_kcec_clay += value * DG_LOG_KCEC_INCREMENTS[key]

    koc_om = 10 ** log_koc_om
    kcec_clay = 10 ** log_kcec_clay
    cec_from_om = 3.4 * foc
    cec_from_clay = cec_total - cec_from_om
    if cec_from_clay < -1e-12:
        raise ValueError(
            "Total CEC is smaller than the workbook organic-matter CEC term (3.4 × fOC); review units or soil inputs"
        )
    cec_from_clay = max(0.0, cec_from_clay)
    organic_matter_kd = koc_om * foc
    clay_kd = kcec_clay * cec_from_clay
    kd = organic_matter_kd + clay_kd
    if kd <= 0:
        raise ValueError("Droge–Goss calculated a non-positive Kd")
    effective_koc = kd / foc
    clay_share = clay_kd / kd if kd else 0.0

    electrolyte = payload.get("electrolyte_system") or "5 mM CaCl2"
    warnings = [
        "Droge–Goss predicts a cation Kd from separate organic-matter and clay-CEC contributions; the effective Koc is supplied only for compatibility with Koc-based downstream tools.",
        "Sorption is sensitive to electrolyte composition and divalent cations. The supplied workbook coefficients are calibrated for 5 mM CaCl2/average-clay conditions.",
        "Functional-group and ionised-nitrogen descriptors require expert review; automated structure perception is not treated as validated in this build.",
    ]
    if str(electrolyte).strip().lower() not in {"5 mm cacl2", "5mm cacl2", "5 mmol/l cacl2"}:
        warnings.append("The selected electrolyte differs from the workbook calibration; no salt correction has been applied.")
    descriptor_status = "reviewed_mcgowan_volume" if reviewed_vx is not None else ("explicit_bond_count" if payload.get("bond_count") is not None else "screening_estimate")
    if volume_record["bond_count_was_estimated"]:
        warnings.append("Bond count was estimated from total atom count and the supplied ring count. This is a screening descriptor and must be reviewed before regulatory use.")
    if payload.get("bond_count") is None and reviewed_vx is None:
        warnings.append("A reviewed McGowan volume or explicit total bond count is preferred; large tabular workbook outputs are not used as calibration values.")

    return {
        "model_key": "DROGE_GOSS_CATION_WORKBOOK",
        "model_name": "Droge & Goss organic-cation soil sorption — supplied workbook implementation",
        "selected_output_kind": "Kd from organic matter + clay CEC",
        "koc_l_kg": effective_koc,
        "kd_l_kg": kd,
        "log_koc": math.log10(effective_koc),
        "log_kd": math.log10(kd),
        "cation_sorption": {
            "mcgowan_volume_vx": vx,
            "nai": nai,
            "log_koc_organic_matter": log_koc_om,
            "koc_organic_matter_l_kg_oc": koc_om,
            "log_kcec_clay": log_kcec_clay,
            "kcec_clay_l_mol_c": kcec_clay,
            "cec_total_mol_c_kg": cec_total,
            "cec_from_organic_matter_mol_c_kg": cec_from_om,
            "cec_from_clay_mol_c_kg": cec_from_clay,
            "organic_matter_kd_contribution_l_kg": organic_matter_kd,
            "clay_kd_contribution_l_kg": clay_kd,
            "clay_fraction_of_total_kd": clay_share,
            "functional_group_counts": groups,
            "structure_record": volume_record,
            "electrolyte_system": electrolyte,
            "descriptor_validation": {
                "status": descriptor_status,
                "molecular_formula_atom_counts": formula_counts,
                "manual_atom_counts": {k: v for k, v in manual_counts.items() if v is not None},
                "atom_count_conflicts": [],
                "bond_count_source": "reviewed" if payload.get("bond_count") is not None else ("reviewed_vx" if reviewed_vx is not None else "estimated"),
            },
        },
        "formula_trace": [
            f"Vx = {vx:.8g}",
            f"log Koc,OM = 1.53 × Vx + 0.32 × Nai − 0.27 + group increments = {log_koc_om:.8g}",
            f"log Kcec,clay = 1.22 × Vx − 0.21 × Nai + 2.09 + group increments − 1 = {log_kcec_clay:.8g}",
            f"CEC from OM = 3.4 × fOC = {cec_from_om:.8g} mol charge/kg",
            f"CEC from clay = CECtotal − CECfrom,OM = {cec_from_clay:.8g} mol charge/kg",
            f"Kd,OM = Koc,OM × fOC = {organic_matter_kd:.8g} L/kg",
            f"Kd,clay = Kcec,clay × CECclay = {clay_kd:.8g} L/kg",
            f"Kd,total = Kd,OM + Kd,clay = {kd:.8g} L/kg",
            f"effective Koc = Kd,total / fOC = {effective_koc:.8g} L/kg",
        ],
        "assumptions": [
            "The equations and increment factors reproduce the clean 'soil' worksheet and the validation examples in the supplied cation workbook.",
            "CEC from organic matter is represented as 3.4 × fOC, exactly as in the workbook.",
            "The primary model output for cations is Kd because clay CEC and organic matter are additive sorption phases.",
        ],
        "warnings": warnings,
    }


def run_sorption_model(payload: dict) -> dict:
    mode = infer_ionisation_class(
        payload.get("mode", "auto"),
        payload.get("pkaa"),
        payload.get("pkab"),
    )
    log_kow = float(payload["log_kow"])
    foc = float(payload["organic_carbon_fraction"])
    soil_ph = float(payload.get("soil_ph", 7.2))
    ionic_strength = float(payload.get("ionic_strength_mol_l", 0.01))

    comparisons = []
    if mode == "acid":
        if payload.get("pkaa") is None:
            raise ValueError("Acid mode requires pKaA")
        selected = franco_trapp("acid", log_kow, float(payload["pkaa"]), soil_ph, ionic_strength, foc)
    elif mode == "neutral":
        neutral_variant = payload.get("neutral_variant", "workbook_literal")
        if neutral_variant not in {"workbook_literal", "publication"}:
            raise ValueError("neutral_variant must be workbook_literal or publication")
        selected = li_neutral(log_kow, foc, neutral_variant)
        comparison_variant = "publication" if neutral_variant == "workbook_literal" else "workbook_literal"
        comparisons.append(li_neutral(log_kow, foc, comparison_variant))
    elif mode == "base":
        if payload.get("pkab") is None:
            raise ValueError("Base mode requires pKaB")
        base_variant = payload.get("base_variant", "droge_goss")
        if base_variant == "droge_goss":
            selected = droge_goss_cation(payload)
            comparisons.append(ecetoc_base_workbook(log_kow, foc))
        elif base_variant == "franco_trapp":
            selected = franco_trapp("base", log_kow, float(payload["pkab"]), soil_ph, ionic_strength, foc)
            comparisons.append(ecetoc_base_workbook(log_kow, foc))
        elif base_variant == "ecetoc":
            selected = ecetoc_base_workbook(log_kow, foc)
            try:
                comparisons.append(droge_goss_cation(payload))
            except ValueError:
                pass
        else:
            raise ValueError("base_variant must be droge_goss, franco_trapp or ecetoc")
        if base_variant != "franco_trapp":
            comparisons.append(
                franco_trapp("base", log_kow, float(payload["pkab"]), soil_ph, ionic_strength, foc)
            )
    else:
        raise ValueError("Unsupported ionisation class")

    return {
        "ionisation_class": mode,
        "shared_inputs": {
            "log_kow": log_kow,
            "pkaa": payload.get("pkaa"),
            "pkab": payload.get("pkab"),
            "soil_ph": soil_ph,
            "organic_carbon_fraction_g_g": foc,
            "total_organic_carbon_percent": foc * 100,
            "ionic_strength_mol_l": ionic_strength,
            "neutral_variant": payload.get("neutral_variant", "workbook_literal"),
            "base_variant": payload.get("base_variant", "droge_goss"),
            "cec_total_mol_c_kg": payload.get("cec_total_mol_c_kg"),
        },
        "selected": selected,
        "comparisons": comparisons,
        "workbook_dependency_map": [
            "Neutral/acid screen: logP, fOC, pH and ionic strength follow the previously supplied sorption workbook.",
            "Droge–Goss: fOC and total CEC are separated into organic-matter CEC (3.4 × fOC) and clay CEC.",
            "Droge–Goss molecular size uses the workbook McGowan atomic-volume and bond-correction table.",
            "Droge–Goss polar-group increments are applied separately to log Koc,OM and log Kcec,clay.",
            "The cation output is total Kd; effective Koc is a compatibility conversion and must not hide the clay contribution.",
        ],
        "global_warnings": [
            "The supplied neutral workbook formula contains a coefficient and TOC-input discrepancy relative to Li et al. (2020); both outputs are shown.",
            "Amphoteric and zwitterionic chemicals are not implemented in this build.",
            "Measured sorption data should supersede modelled values when reliable and scenario-relevant evidence exists.",
        ],
    }
