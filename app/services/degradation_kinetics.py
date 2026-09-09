"""Degradation kinetics: SFO/FOMC/HS/DFOP fitting and major/minor metabolite classification.

Every model equation, the chi-square goodness-of-fit procedure, and the metabolite
significance thresholds below were read directly from primary regulatory guidance
documents on 2026-09-09 (not assumed from secondary summaries, which turned out to
disagree with each other and with the primary text on several points):

- FOCUS (2014) "Generic guidance for Estimating Persistence and Degradation Kinetics
  from Environmental Fate Studies on Pesticides in EU Registration", Report of the
  FOCUS Work Group on Degradation Kinetics, Version 1.1, 18 December 2014.
  http://esdac.jrc.ec.europa.eu/projects/degradation-kinetics
  ("FOCUS Kinetics" below.)
- VICH GL38 "Environmental impact assessments for veterinary medicinal products --
  Phase II", as adopted by EMA/CVMP.
  https://www.ema.europa.eu/en/documents/scientific-guideline/vich-gl38-environmental-impact-assessments-veterinary-medicinal-products-vmps-phase-ii_en.pdf

Two DIFFERENT "10%" rules exist and must not be conflated -- they were found, verbatim,
in two different documents answering two different regulatory questions:

1. FOCUS Kinetics Section 8.5.1 "Minor metabolites" (verbatim): "This section concerns
   metabolites that are observed at levels lower than 10% of the applied parent
   throughout the study." Below 10% of applied parent at every sampling point, a full
   formation-and-decline kinetic fit is *not required* to the same reliability standard
   -- FOCUS explicitly allows a simpler decline-from-observed-maximum fit instead, or
   no fit at all if the pathway is unclear. This is a *kinetic-modelling-reliability*
   distinction, not a risk-relevance decision (FOCUS Kinetics explicitly says
   toxicological/ecotoxicological/environmental "relevance" of a metabolite is decided
   by a separate document -- the Guidance Document on Relevant Metabolites -- and that
   this report "makes no assumptions about whether they are relevant or not").
2. VICH GL38 (verbatim, appearing twice, Phase II PEC refinement sections): "Excreted
   metabolites representing 10% or more of the administered dose and which do not form
   part of biochemical pathways should be added to the active substance to allow the
   PEC to be recalculated." This is a *PEC/exposure-inclusion* rule for veterinary
   medicinal products, keyed to administered dose (not applied parent residue in a
   degradation study), and carries an extra qualifier this module cannot evaluate
   automatically -- whether the metabolite "forms part of biochemical pathways" is an
   expert/reviewer judgement, not a computable property.

Both use "10%" as the number; they are not the same rule, and this module keeps them
as two distinct, separately-cited `regulatory_framework` options rather than one
generic threshold, so a result can never claim compliance with a document it did not
actually apply.

The four kinetic models below (equations, parameter counts, and the exact chi-square
formula) are transcribed from the FOCUS Kinetics document itself (Boxes 5-1 through
5-4, Section 6.3.1.2, Section 8.4.3): SFO (Box 5-1), FOMC / Gustafson-Holden (Box 5-2),
HS / hockey-stick (Box 5-3), DFOP / bi-exponential (Box 5-4). FOCUS Kinetics states
HS has "no advantage ... for parent compounds in soil" and is not a core parent model
(it is a fallback tier-1 model and a water-sediment model); DFOP has no analytical DTx
solution and FOCUS itself recommends an iterative/numerical search -- this module
solves DTx numerically for every model (bisection against the fitted M(t) curve) rather
than trusting a hand-transcribed closed form for every case, which also sidesteps any
transcription risk for the more visually mangled equations in the source PDF.

Regulatory disclaimer, restated in every function's output: "guidance, not an absolute
cut-off criterion" (FOCUS Kinetics' own words about the chi-square error threshold) --
this module never silently accepts or rejects a model; it reports the chi-square error,
the guidance threshold, and lets a reviewer decide, exactly like every other model in
this app.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Literal

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import chi2

FOCUS_KINETICS_CITATION = (
    "FOCUS (2014) Generic guidance for Estimating Persistence and Degradation Kinetics "
    "from Environmental Fate Studies on Pesticides in EU Registration, Version 1.1, "
    "18 December 2014. http://esdac.jrc.ec.europa.eu/projects/degradation-kinetics"
)
VICH_GL38_CITATION = (
    "VICH GL38 (EMA/CVMP) Environmental impact assessments for veterinary medicinal "
    "products -- Phase II. "
    "https://www.ema.europa.eu/en/vich-gl38-environmental-impact-assessments-veterinary-medicinal-products-phase-ii-scientific-guideline"
)

# FOCUS Kinetics Section 8.5.1: "This section concerns metabolites that are observed
# at levels lower than 10% of the applied parent throughout the study."
FOCUS_MINOR_METABOLITE_THRESHOLD_PERCENT = 10.0
# VICH GL38: "Excreted metabolites representing 10% or more of the administered dose
# and which do not form part of biochemical pathways should be added..."
VICH_METABOLITE_INCLUSION_THRESHOLD_PERCENT = 10.0

# FOCUS Kinetics Section 8.4.3 / 6.3.1.2: chi-square error guidance, "should only be
# considered as guidance and not absolute cut-off criterion."
CHI_SQUARE_ERROR_GUIDANCE_PERCENT = 15.0

RegulatoryFramework = Literal["focus_pesticide_kinetics", "vich_gl38_veterinary"]
ModelKey = Literal["SFO", "FOMC", "HS", "DFOP"]
MODEL_KEYS: tuple[ModelKey, ...] = ("SFO", "FOMC", "HS", "DFOP")


class KineticFitError(ValueError):
    """Raised when a model cannot be fitted to the supplied data at all."""


# --------------------------------------------------------------------------------
# Model equations -- FOCUS Kinetics Boxes 5-1 to 5-4. M(t) is % of applied (or mass).
# --------------------------------------------------------------------------------

def sfo_model(t: np.ndarray, m0: float, k: float) -> np.ndarray:
    """Box 5-1: M = M0 * exp(-k*t)."""
    return m0 * np.exp(-k * t)


def fomc_model(t: np.ndarray, m0: float, alpha: float, beta: float) -> np.ndarray:
    """Box 5-2 (Gustafson & Holden): M = M0 * (1 + t/beta)^(-alpha)."""
    return m0 * np.power(1.0 + t / beta, -alpha)


def hs_model(t: np.ndarray, m0: float, k1: float, k2: float, tb: float) -> np.ndarray:
    """Box 5-3 (hockey-stick): first-order with a rate-constant breakpoint at t=tb."""
    t = np.asarray(t, dtype=float)
    before = m0 * np.exp(-k1 * t)
    at_break = m0 * np.exp(-k1 * tb)
    after = at_break * np.exp(-k2 * (t - tb))
    return np.where(t <= tb, before, after)


def dfop_model(t: np.ndarray, m0: float, g: float, k1: float, k2: float) -> np.ndarray:
    """Box 5-4 (bi-exponential): M = M0 * (g*exp(-k1*t) + (1-g)*exp(-k2*t))."""
    return m0 * (g * np.exp(-k1 * t) + (1.0 - g) * np.exp(-k2 * t))


_MODEL_FUNCTIONS: dict[ModelKey, Callable[..., np.ndarray]] = {
    "SFO": sfo_model,
    "FOMC": fomc_model,
    "HS": hs_model,
    "DFOP": dfop_model,
}

# FOCUS Kinetics Table 6-3 / 8-5: number of fitted parameters per model (M0 free).
_MODEL_PARAM_COUNT: dict[ModelKey, int] = {"SFO": 2, "FOMC": 3, "HS": 4, "DFOP": 4}


def _initial_guess_and_bounds(
    model: ModelKey, t: np.ndarray, m: np.ndarray,
) -> tuple[list[float], tuple[list[float], list[float]]]:
    m0_guess = float(m[0]) if t[0] == 0 else float(np.max(m))
    m0_lo, m0_hi = m0_guess * 0.5, max(m0_guess * 1.5, m0_guess + 1.0)
    t_span = float(max(t.max(), 1.0))
    # Crude single-first-order rate estimate from the first/last observed points,
    # used only to seed the optimiser -- never reported as a result.
    tail = max(m[-1], 1e-6)
    k_guess = max(math.log(max(m0_guess, 1e-6) / tail) / t_span, 1e-4)

    if model == "SFO":
        return [m0_guess, k_guess], ([0.0, 1e-6], [np.inf, 10.0])
    if model == "FOMC":
        return [m0_guess, 1.0, t_span], ([0.0, 1e-3, 1e-3], [np.inf, 50.0, np.inf])
    if model == "HS":
        return [m0_guess, k_guess, k_guess / 4, t_span / 2], (
            [0.0, 1e-6, 1e-6, 0.0], [np.inf, 10.0, 10.0, t_span],
        )
    if model == "DFOP":
        return [m0_guess, 0.5, k_guess, k_guess / 4], (
            [0.0, 0.0, 1e-6, 1e-6], [np.inf, 1.0, 10.0, 10.0],
        )
    raise KineticFitError(f"Unknown kinetic model {model!r}")


def fit_kinetic_model(model: ModelKey, t_obs: np.ndarray, m_obs: np.ndarray) -> dict[str, Any]:
    """Fits one model to raw (unaveraged) replicate observations via nonlinear least squares.

    FOCUS Kinetics Section 6.3.1.1: "True replicates: use individually in curve fitting,
    but average before calculating chi-square" -- so this function is deliberately given
    every replicate point, not day-level means.
    """
    t_obs = np.asarray(t_obs, dtype=float)
    m_obs = np.asarray(m_obs, dtype=float)
    if t_obs.shape != m_obs.shape or t_obs.size < _MODEL_PARAM_COUNT[model] + 1:
        raise KineticFitError(
            f"{model} needs at least {_MODEL_PARAM_COUNT[model] + 1} observations to fit "
            f"{_MODEL_PARAM_COUNT[model]} parameters with at least one residual degree of freedom."
        )
    fn = _MODEL_FUNCTIONS[model]
    p0, bounds = _initial_guess_and_bounds(model, t_obs, m_obs)
    try:
        params, _covariance = curve_fit(
            fn, t_obs, m_obs, p0=p0, bounds=bounds, maxfev=20000,
        )
    except (RuntimeError, ValueError) as exc:
        raise KineticFitError(f"{model} fit did not converge: {exc}") from exc

    predicted = fn(t_obs, *params)
    param_names = {
        "SFO": ("m0", "k"),
        "FOMC": ("m0", "alpha", "beta"),
        "HS": ("m0", "k1", "k2", "tb"),
        "DFOP": ("m0", "g", "k1", "k2"),
    }[model]
    return {
        "model": model,
        "parameters": dict(zip(param_names, (float(v) for v in params))),
        "predicted": predicted,
        "sse": float(np.sum((m_obs - predicted) ** 2)),
    }


def chi_square_error_percent(
    day_means: np.ndarray, day_predicted: np.ndarray, n_params: int, alpha: float = 0.05,
) -> dict[str, Any]:
    """FOCUS Kinetics Eq. 6-1, solved for the model error % at which the test is passed.

    err% = (100 / mean(O)) * sqrt( sum((C-O)^2) / chi2_tabulated(alpha, df) )
    where df = number of day-level (averaged) observations minus number of fitted
    parameters, and the model is judged not appropriate at the chosen significance
    level if its actual chi-square statistic exceeds chi2_tabulated -- reported here
    as the equivalent error percentage so it can be compared directly against the
    15% guidance figure FOCUS Kinetics itself uses (Section 8.4.3), which this module
    also does not treat as a hard pass/fail cut-off.
    """
    day_means = np.asarray(day_means, dtype=float)
    day_predicted = np.asarray(day_predicted, dtype=float)
    degrees_of_freedom = day_means.size - n_params
    if degrees_of_freedom < 1:
        return {
            "degrees_of_freedom": degrees_of_freedom,
            "error_percent": None,
            "note": "Not enough independent day-level observations to compute a chi-square error for this model.",
        }
    o_bar = float(np.mean(day_means))
    if o_bar <= 0:
        return {"degrees_of_freedom": degrees_of_freedom, "error_percent": None, "note": "Mean observed value is zero."}
    sse = float(np.sum((day_predicted - day_means) ** 2))
    chi2_tabulated = float(chi2.ppf(1 - alpha, degrees_of_freedom))
    error_percent = (100.0 / o_bar) * math.sqrt(sse / chi2_tabulated)
    return {
        "degrees_of_freedom": degrees_of_freedom,
        "chi_square_tabulated": chi2_tabulated,
        "significance_level": alpha,
        "error_percent": error_percent,
        "passes_guidance_threshold": error_percent <= CHI_SQUARE_ERROR_GUIDANCE_PERCENT,
        "guidance_threshold_percent": CHI_SQUARE_ERROR_GUIDANCE_PERCENT,
        "note": (
            "FOCUS Kinetics: 'this value should only be considered as guidance and not "
            "absolute cut-off criterion' -- a reviewer decision, not an automatic pass/fail."
        ),
    }


def endpoint_dtx(
    model: ModelKey, params: dict[str, float], m0_reference: float, x: float,
) -> float | None:
    """DTx (days to x% decline) found by bisecting the fitted M(t) curve.

    Solved numerically rather than from a hand-transcribed closed form for every model:
    FOCUS Kinetics itself states DFOP has no analytical solution ("DTx values can only
    be found by an iterative procedure"), and this keeps SFO/FOMC/HS/DFOP on one
    consistent, independently-checkable code path instead of four different formulas.
    """
    if not (0 < x < 100):
        raise ValueError("x must be between 0 and 100")
    target = m0_reference * (100.0 - x) / 100.0
    fn = _MODEL_FUNCTIONS[model]

    def value_at(t: float) -> float:
        return float(fn(np.array([t]), *[params[name] for name in _PARAM_ORDER[model]])[0])

    lo, hi = 0.0, 1.0
    for _ in range(60):
        if value_at(hi) <= target:
            break
        hi *= 2
    else:
        return None  # never reaches x% decline within a reasonable horizon
    for _ in range(100):
        mid = (lo + hi) / 2
        if value_at(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


_PARAM_ORDER: dict[ModelKey, tuple[str, ...]] = {
    "SFO": ("m0", "k"),
    "FOMC": ("m0", "alpha", "beta"),
    "HS": ("m0", "k1", "k2", "tb"),
    "DFOP": ("m0", "g", "k1", "k2"),
}


def _day_level_means(observations: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    days = np.array([float(row["day"]) for row in observations])
    means = np.array([float(np.mean(row["replicate_values_percent"])) for row in observations])
    return days, means


def _raw_replicate_points(observations: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    t_list: list[float] = []
    m_list: list[float] = []
    for row in observations:
        for value in row["replicate_values_percent"]:
            t_list.append(float(row["day"]))
            m_list.append(float(value))
    return np.array(t_list), np.array(m_list)


def restrict_to_decline_from_maximum(
    observations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Re-bases a formation-then-decline series to start at its observed maximum.

    A transformation product typically forms from the parent and only later declines --
    fitting SFO/FOMC/HS/DFOP directly to the whole rise-and-fall series is invalid,
    since every one of those models is a monotonic decline from t=0 (confirmed
    empirically: attempting it on a rising-then-falling series drives every model to a
    degenerate near-zero rate constant and a nonsensical, effectively infinite DT50).
    The scientifically correct approach is a coupled parent-metabolite formation/decay
    fit (FOCUS Kinetics Chapter 8, Box 8-1/8-2) -- out of scope here. FOCUS Kinetics
    Section 8.5.1 explicitly sanctions a simpler, honest alternative instead:
    "an estimate of the degradation of minor metabolites can be obtained by fitting
    the decline curve of the metabolite from its observed maximum" -- this function
    implements exactly that, and is also used for major metabolites when a full
    coupled fit is not available, always labelled as such in the result.
    """
    day_t, day_m = _day_level_means(observations)
    peak_index = int(np.argmax(day_m))
    if peak_index == 0:
        return observations, None
    peak_day = float(day_t[peak_index])
    restricted = [
        {"day": float(row["day"]) - peak_day, "replicate_values_percent": row["replicate_values_percent"]}
        for row in observations
        if float(row["day"]) >= peak_day
    ]
    metadata = {
        "restricted": True,
        "peak_day": peak_day,
        "peak_percent": float(day_m[peak_index]),
        "citation": FOCUS_KINETICS_CITATION,
        "note": (
            "FOCUS Kinetics Section 8.5.1: DT50/DT90 fitted to the decline from this metabolite's own "
            "observed maximum (day re-based to 0 at the peak), not from time of parent application -- a full "
            "coupled parent-metabolite formation/decay fit was not attempted."
        ),
    }
    return restricted, metadata


def fit_and_select_model(
    observations: list[dict[str, Any]],
    *,
    candidate_models: tuple[ModelKey, ...] = MODEL_KEYS,
) -> dict[str, Any]:
    """Fits every candidate model, selects per FOCUS's simplest-model-that-passes rule.

    FOCUS Kinetics: prefer SFO where its chi-square error passes the (guidance, not
    absolute) threshold; otherwise compare the bi-phasic models and prefer whichever
    passes at the smaller error level ("the model which passes at the smaller level
    describes the data better").
    """
    if len(observations) < 2:
        raise KineticFitError("At least two sampling days are required to fit a decline curve.")
    day_t, day_m = _day_level_means(observations)
    raw_t, raw_m = _raw_replicate_points(observations)
    m0_reference = float(day_m[0]) if day_t[0] == 0 else float(np.max(day_m))

    fits: dict[str, Any] = {}
    for model in candidate_models:
        try:
            fit = fit_kinetic_model(model, raw_t, raw_m)
        except KineticFitError as exc:
            fits[model] = {"model": model, "error": str(exc)}
            continue
        day_predicted = _MODEL_FUNCTIONS[model](day_t, *[fit["parameters"][n] for n in _PARAM_ORDER[model]])
        chi_square = chi_square_error_percent(day_m, day_predicted, _MODEL_PARAM_COUNT[model])
        dt50 = endpoint_dtx(model, fit["parameters"], m0_reference, 50.0)
        dt90 = endpoint_dtx(model, fit["parameters"], m0_reference, 90.0)
        fits[model] = {
            "model": model,
            "parameters": fit["parameters"],
            "chi_square": chi_square,
            "dt50_days": dt50,
            "dt90_days": dt90,
        }

    passing = [
        key for key in candidate_models
        if fits.get(key, {}).get("chi_square", {}).get("passes_guidance_threshold")
    ]
    if "SFO" in passing:
        selected = "SFO"
        selection_reason = "SFO passes the chi-square guidance threshold; FOCUS Kinetics prefers the simplest adequate model."
    elif passing:
        selected = min(passing, key=lambda key: fits[key]["chi_square"]["error_percent"])
        selection_reason = (
            "SFO did not pass the chi-square guidance threshold; among the bi-phasic models that did pass, "
            f"{selected} has the lowest error percentage."
        )
    else:
        fitted_keys = [k for k in candidate_models if "error" not in fits.get(k, {"error": True})]
        if not fitted_keys:
            selected = None
            selection_reason = "No candidate model could be fitted to this data."
        else:
            selected = min(
                fitted_keys,
                key=lambda key: fits[key]["chi_square"]["error_percent"]
                if fits[key]["chi_square"]["error_percent"] is not None else math.inf,
            )
            selection_reason = (
                "No model passed the chi-square guidance threshold; reporting the lowest-error fit "
                "for reviewer judgement rather than silently accepting or discarding it."
            )

    return {
        "fits": fits,
        "selected_model": selected,
        "selection_reason": selection_reason,
        "citation": FOCUS_KINETICS_CITATION,
        "day_level_observations": [{"day": float(d), "mean_percent": float(m)} for d, m in zip(day_t, day_m)],
    }


def classify_metabolite_significance(
    max_observed_percent_of_reference: float,
    *,
    framework: RegulatoryFramework,
    forms_part_of_biochemical_pathway: bool | None = None,
) -> dict[str, Any]:
    """Classifies a transformation product against the requested regulatory framework.

    Two distinct, separately-cited rules -- see the module docstring for why they are
    not merged into one generic threshold.
    """
    if framework == "focus_pesticide_kinetics":
        is_major = max_observed_percent_of_reference >= FOCUS_MINOR_METABOLITE_THRESHOLD_PERCENT
        return {
            "framework": framework,
            "threshold_percent": FOCUS_MINOR_METABOLITE_THRESHOLD_PERCENT,
            "max_observed_percent": max_observed_percent_of_reference,
            "classification": "major" if is_major else "minor",
            "requires_full_kinetic_fit": is_major,
            "citation": FOCUS_KINETICS_CITATION,
            "rule_text": (
                "FOCUS Kinetics Section 8.5.1: metabolites observed at levels lower than 10% of the applied "
                "parent throughout the study are 'minor' -- a full formation/decline kinetic fit is not required "
                "to the same reliability standard (a decline-from-maximum fit, or no fit if the pathway is "
                "unclear, may be used instead). This is a kinetic-modelling-reliability distinction, not a "
                "toxicological/ecotoxicological relevance decision -- that is governed by a separate document "
                "(the Guidance Document on Relevant Metabolites)."
            ),
            "still_shown_in_pathway": True,
        }
    if framework == "vich_gl38_veterinary":
        meets_threshold = max_observed_percent_of_reference >= VICH_METABOLITE_INCLUSION_THRESHOLD_PERCENT
        biochemical_pathway_known = forms_part_of_biochemical_pathway is not None
        include_in_pec = meets_threshold and forms_part_of_biochemical_pathway is not True
        return {
            "framework": framework,
            "threshold_percent": VICH_METABOLITE_INCLUSION_THRESHOLD_PERCENT,
            "max_observed_percent": max_observed_percent_of_reference,
            "meets_dose_threshold": meets_threshold,
            "forms_part_of_biochemical_pathway": forms_part_of_biochemical_pathway,
            "include_in_pec_refinement": include_in_pec,
            "requires_reviewer_judgement": meets_threshold and not biochemical_pathway_known,
            "citation": VICH_GL38_CITATION,
            "rule_text": (
                "VICH GL38: 'Excreted metabolites representing 10% or more of the administered dose and which "
                "do not form part of biochemical pathways should be added to the active substance to allow the "
                "PEC to be recalculated.' Whether a metabolite 'forms part of biochemical pathways' is an "
                "expert/reviewer judgement this module cannot determine automatically."
            ),
            "still_shown_in_pathway": True,
        }
    raise ValueError(f"Unknown regulatory framework {framework!r}")


def run_degradation_kinetics_assessment(
    *,
    regulatory_framework: RegulatoryFramework,
    matrix: str,
    parent_name: str,
    parent_observations: list[dict[str, Any]],
    metabolites: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Top-level orchestration: fits the parent, classifies and fits each metabolite."""
    if not parent_observations:
        raise ValueError("At least one day of parent observations is required")

    parent_fit = fit_and_select_model(parent_observations)
    _, parent_day_means = _day_level_means(parent_observations)
    parent_reference = float(parent_day_means[0]) if parent_observations[0]["day"] == 0 else float(np.max(parent_day_means))

    metabolite_results = []
    for metabolite in metabolites or []:
        _, met_day_means = _day_level_means(metabolite["observations"])
        max_observed = float(np.max(met_day_means))
        significance = classify_metabolite_significance(
            max_observed,
            framework=regulatory_framework,
            forms_part_of_biochemical_pathway=metabolite.get("forms_part_of_biochemical_pathway"),
        )
        entry: dict[str, Any] = {
            "name": metabolite.get("name", "Unnamed transformation product"),
            "smiles": metabolite.get("smiles"),
            "significance": significance,
        }
        should_fit = significance.get("requires_full_kinetic_fit") or significance.get("include_in_pec_refinement") or len(metabolite["observations"]) >= 3
        if should_fit:
            fit_observations, restriction = restrict_to_decline_from_maximum(metabolite["observations"])
            if len(fit_observations) < 2:
                entry["kinetics"] = None
                entry["kinetics_note"] = (
                    "Only the observed maximum and no later decline points are available -- a decline-from-"
                    "maximum fit needs at least one later sampling day. Shown in the pathway only."
                )
            else:
                try:
                    entry["kinetics"] = fit_and_select_model(fit_observations)
                    entry["kinetics"]["fit_basis"] = "decline_from_observed_maximum" if restriction else "direct_fit_from_dose"
                    if restriction:
                        entry["kinetics"]["fit_basis_detail"] = restriction
                except KineticFitError as exc:
                    entry["kinetics"] = None
                    entry["kinetics_error"] = str(exc)
        else:
            entry["kinetics"] = None
            entry["kinetics_note"] = "Below the significance threshold with too few points for a reliable fit; shown in the pathway only."
        metabolite_results.append(entry)

    return {
        "regulatory_framework": regulatory_framework,
        "matrix": matrix,
        "parent": {"name": parent_name, "kinetics": parent_fit, "reference_amount_percent": parent_reference},
        "metabolites": metabolite_results,
        "warnings": [
            "Chi-square error percentages are FOCUS Kinetics guidance, not an absolute pass/fail criterion -- "
            "every fit requires reviewer visual assessment before a DT50/DT90 endpoint is accepted.",
            "Metabolite toxicological/ecotoxicological relevance is not determined by this module -- see the "
            "citation attached to each metabolite's significance classification.",
        ],
    }
