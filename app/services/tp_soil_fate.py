"""Soil fate of a parent and its main-stage transformation products (TPs): concentration versus time from rate kinetics.

Theoretical screening tool. Each substance needs only what the owner named: molecular weight, log P, pKa and a soil
DT50 (Koc is derived from log P and pKa by ``sorption.run_sorption_model``). Predictions are proxies and most of the
estimators behind them were built on one chemical class; every input carries a source label and none is invented.

Model (single first-order kinetics, molar basis; each product has ONE source, the parent or another product, so chains
parent -> TP1 -> TP2 and branches are allowed, reversible steps are not):

    dP/dt  = -kP P                              P(t)  = P0 exp(-kP t)
    dMj/dt =  ffj kP P - kj Mj                  Mj(t) = ffj kP P0 (exp(-kP t) - exp(-kj t)) / (kj - kP)   (kj != kP)
                                                Mj(t) = ffj kP P0 t exp(-kP t)                           (kj == kP)
    t_max  = ln(kj / kP) / (kj - kP)            (1 / kP when kj == kP)

Products formed from other products (dMj/dt = ffj ks Ms - kj Mj, ks the source's rate constant) are solved as the
linear system dY/dt = A Y with the matrix exponential, Y(t) = expm(A t) Y(0); direct products of the parent keep the
closed forms above for peak time and height, deeper generations are located numerically.

Mass = moles x MW, so a TP is converted with the molar-mass ratio MW_TP / MW_parent (EFSA 2017, soil PEC guidance,
section 2.8: dose x formation fraction x MW_TP / MW_parent).

Regulatory anchors, each read in primary text (2026-09-24):
  * OECD TG 307 (2025) para 51: "a major transformation product is any product representing >= 10% of applied dose at
    any time during the study"; formation and decline are plotted against time. The flag here uses the MOLAR percentage of
    the parent dose (the guideline speaks of applied radioactivity/dose, so this is a screening analogue).
  * EFSA soil PEC guidance (2017) section 3.2.3, formation fraction stepped approach: 1.0 unless measured, then the
    maximum of the dossier values, then their arithmetic mean. The default here is the first step -- a conservative
    worst case per product; defaulted fractions are NOT additive across products.
  * Mobility uses the CLP log Koc criteria already encoded in ``pathway_plausibility`` (single reused copy).
NOT encoded because it was not confirmed in primary text: the 0.1 ug/L metabolite groundwater relevance trigger.

Temperature: DT50s are moved between temperatures with the FOCUS/EFSA Arrhenius factor (Ea 65.4 kJ/mol, no degradation
at or below 0 C) from ``soil_dt50.corrections``. The target is a region or an explicit temperature (EU = 10 C, the
owner-stated value shared with ``biowin_dt50``); with neither, the OECD 307 reference of 20 C is used and labelled so.
Animal, wastewater and manure are entry routes (they set the initial soil concentration); they are not modelled here.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.linalg import expm
from scipy.optimize import minimize_scalar

from .biowin_dt50 import REGION_TEMPERATURE_C, dt50_from_biowin4
from .pathway_plausibility import LOG_KOC_M_THRESHOLD, LOG_KOC_VM_THRESHOLD
from .soil_dt50 import corrections
from .sorption import run_sorption_model

REFERENCE_TEMPERATURE_C = 20.0
DT50_SOURCES = ("measured", "pepper_prediction", "opera_prediction", "biowin_screen", "user_estimate")
MAX_DURATION_DAYS = 3650.0
MAJOR_TP_PERCENT = 10.0  # OECD TG 307 para 51
FF_DEFAULT_NOTE = "formation fraction defaulted to 1.0 (EFSA 2017 soil PEC guidance, first step): a conservative worst case for this product alone"


class TpFateInputError(ValueError):
    """Raised for inputs that cannot be modelled; the message says what to fix."""


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise TpFateInputError(f"{label} must be a positive finite number")
    return float(value)


def _structure_properties(entry: dict[str, Any], label: str) -> tuple[float, float | None, list[str]]:
    """Molecular weight and log P: supplied values win; a SMILES fills gaps with RDKit (Crippen log P is a proxy)."""

    notes: list[str] = []
    mw = entry.get("molecular_weight_g_mol")
    log_p = entry.get("log_p")
    smiles = entry.get("smiles")
    if smiles and (mw is None or log_p is None):
        try:
            from rdkit import Chem
            from rdkit.Chem import Crippen, Descriptors
        except ImportError as exc:  # pragma: no cover - rdkit is a project dependency
            raise TpFateInputError(f"{label}: RDKit is unavailable, so supply molecular_weight_g_mol and log_p directly") from exc
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise TpFateInputError(f"{label}: SMILES {smiles!r} could not be parsed")
        if mw is None:
            mw = Descriptors.MolWt(mol)
            notes.append("MW from the SMILES (RDKit)")
        if log_p is None:
            log_p = Crippen.MolLogP(mol)
            notes.append("log P is the RDKit Crippen estimate: a proxy, not a measured or KOWWIN value")
    if mw is None:
        raise TpFateInputError(f"{label}: molecular_weight_g_mol (or a SMILES) is required")
    if log_p is not None and (isinstance(log_p, bool) or not isinstance(log_p, (int, float)) or not math.isfinite(log_p)):
        raise TpFateInputError(f"{label}: log_p must be a finite number")
    return _positive(mw, f"{label}: molecular_weight_g_mol"), (float(log_p) if log_p is not None else None), notes


def _pepper_dt50(entry: dict[str, Any], label: str) -> tuple[float, str, str, dict[str, Any]]:
    """Soil DT50 at the 20 C reference from the PEPPER provider, for a structure; measured EAWAG-SOIL value wins if present.

    Runs only where the provider is allowed (same licence gate as ``/api/providers/soil-dt50``) and installed.
    PEPPER predicts the disappearance of a compound as a parent in aerobic laboratory soil (OECD 307); using it for a
    transformation product's own decline is an extension, and it does not predict formation.
    """

    from . import soil_dt50

    smiles = entry.get("smiles")
    if not smiles:
        raise TpFateInputError(f"{label}: a SMILES is required to predict a DT50 with PEPPER")
    gate_open, licence_status = soil_dt50.commercial_gate()
    if not gate_open:
        raise TpFateInputError(f"{label}: the PEPPER soil DT50 model is closed here ({licence_status}); supply a DT50 instead")
    availability = soil_dt50.availability()
    if not availability["available"]:
        raise TpFateInputError(f"{label}: PEPPER dependencies are missing ({', '.join(availability['missing'])}); supply a DT50 instead")
    from .soil_dt50.predictor import get_predictor

    result = get_predictor().predict([{"smiles": smiles, "name": entry.get("name")}])[0]
    if result.status != "ok" or not result.recommended:
        raise TpFateInputError(f"{label}: PEPPER could not predict this structure ({result.status}); supply a DT50 instead")
    recommended = result.recommended
    measured = str(recommended.get("basis", "")).startswith("measured")
    uncertainty = {
        "logDT50_sd": recommended.get("logDT50_sd"), "confidence": recommended.get("confidence"),
        "mean_90CI_days": (result.prediction or {}).get("DT50_mean_90CI_days"),
        "single_soil_90PI_days": (result.prediction or {}).get("DT50_single_soil_90PI_days"),
        "max_tanimoto_to_training_set": (result.applicability or {}).get("max_tanimoto"), "warnings": list(result.warnings),
        "source": "pepper", "log10_sd_mean": recommended.get("logDT50_sd"),
    }
    sigma_soils = (result.prediction or {}).get("sigma_between_soils_used")
    sd_mean = recommended.get("logDT50_sd")
    uncertainty["log10_sd_single_soil"] = (
        math.sqrt(sd_mean ** 2 + sigma_soils ** 2) if sd_mean is not None and sigma_soils is not None else sd_mean
    )
    note = (
        f"PEPPER {recommended['DT50_ref_days']} d at 20 C ({recommended['basis']}; confidence {recommended.get('confidence')})"
        + ("" if measured else "; MODEL ESTIMATE, not an OECD-accepted QSAR -- prefer a measured OECD 307 value")
    )
    return float(recommended["DT50_ref_days"]), ("measured" if measured else "pepper_prediction"), note, uncertainty


def _dt50_at_target(entry: dict[str, Any], label: str, target_c: float) -> dict[str, Any]:
    """The substance's soil DT50 (days) at the target temperature, with its source label and derivation."""

    uncertainty = None
    if entry.get("dt50_days") is not None:
        source = entry.get("dt50_source") or "user_estimate"
        if source not in DT50_SOURCES:
            raise TpFateInputError(f"{label}: dt50_source must be one of {DT50_SOURCES}")
        dt50 = _positive(entry["dt50_days"], f"{label}: dt50_days")
        from_c = float(entry.get("dt50_temperature_c", REFERENCE_TEMPERATURE_C))
        note = f"supplied DT50 {dt50:g} d at {from_c:g} C"
        uncertainty = _range_to_uncertainty(entry, dt50, label)
    elif entry.get("dt50_from_pepper"):
        dt50, source, note, uncertainty = _pepper_dt50(entry, label)
        from_c = REFERENCE_TEMPERATURE_C
    elif entry.get("biowin4_score") is not None:
        est = dt50_from_biowin4(entry["biowin4_score"], output_unit="days")
        source, dt50, from_c = "biowin_screen", est["dt50"], est["reference_temperature_c"]
        note = f"BIOWIN4 screen {est['dt50']:.4g} d at {from_c:g} C (unsourced owner relation; prefer a measured DT50)"
    else:
        raise TpFateInputError(f"{label}: give dt50_days (with dt50_source), biowin4_score, or a SMILES with dt50_from_pepper")
    if source == "biowin_screen" and entry.get("dt50_days") is not None:
        note += " (BIOWIN screen: unsourced owner relation; prefer a measured DT50)"
    f_from = corrections.temperature_factor(from_c)
    f_to = corrections.temperature_factor(target_c)
    if f_from == 0:
        raise TpFateInputError(f"{label}: a DT50 stated at {from_c:g} C (<= 0 C) cannot be normalised")
    at_target = math.inf if f_to == 0 else dt50 * f_from / f_to
    return {"dt50_days": at_target, "dt50_source": source, "dt50_basis": note, "dt50_input_days": dt50, "dt50_input_temperature_c": from_c, "dt50_uncertainty": uncertainty}


def _koc(entry: dict[str, Any], log_p: float | None, soil: dict[str, Any], label: str) -> dict[str, Any] | None:
    if log_p is None or soil.get("organic_carbon_fraction") is None:
        return None
    payload: dict[str, Any] = {
        "log_kow": log_p, "organic_carbon_fraction": float(soil["organic_carbon_fraction"]),
        "soil_ph": float(soil.get("soil_ph", 7.0)), "pkaa": entry.get("pka_a"), "pkab": entry.get("pka_b"),
        "base_variant": "droge_goss" if soil.get("cec_total_mol_c_kg") else "franco_trapp",
        "cec_total_mol_c_kg": soil.get("cec_total_mol_c_kg"),
    }
    try:
        result = run_sorption_model(payload)
    except ValueError as exc:
        return {"available": False, "reason": f"{label}: {exc}"}
    selected = result["selected"]
    log_koc = selected["log_koc"]
    return {
        "available": True, "ionisation_class": result["ionisation_class"], "model": selected["model_name"],
        "koc_l_kg": selected["koc_l_kg"], "log_koc": log_koc, "warnings": selected.get("warnings", []),
        "very_mobile_clp": log_koc < LOG_KOC_VM_THRESHOLD, "mobile_clp": log_koc < LOG_KOC_M_THRESHOLD,
        "mobility_note": "CLP mobility uses the lowest log Koc over pH 4-9 for ionisable substances; this is a single-pH value.",
    }


def parent_moles_fraction(t: float, k_parent: float) -> float:
    return math.exp(-k_parent * t)


def product_moles_fraction(t: float, k_parent: float, k_product: float, formation_fraction: float) -> float:
    """Moles of product per mole of parent applied, at time t (closed form, see the module docstring)."""

    if math.isclose(k_parent, k_product, rel_tol=1e-9):
        return formation_fraction * k_parent * t * math.exp(-k_parent * t)
    return formation_fraction * k_parent * (math.exp(-k_parent * t) - math.exp(-k_product * t)) / (k_product - k_parent)


def time_of_peak(k_parent: float, k_product: float) -> float:
    if math.isclose(k_parent, k_product, rel_tol=1e-9):
        return 1.0 / k_parent
    return math.log(k_product / k_parent) / (k_product - k_parent)


Z90 = 1.6448536269514722  # one-sided 95th percentile of the standard normal: a 90 % interval spans +-Z90 sd
BAND_BASES = ("single_soil", "mean")
BAND_PERCENTILES = (5.0, 50.0, 95.0)
BAND_TIME_POINTS = 121


def _range_to_uncertainty(entry: dict[str, Any], dt50: float, label: str) -> dict[str, Any] | None:
    """A user-supplied 90 % range for a DT50 (same temperature basis as the DT50) as a log10 standard deviation."""

    bounds = entry.get("dt50_range_days")
    if bounds is None:
        return None
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        raise TpFateInputError(f"{label}: dt50_range_days must be [low, high]")
    low, high = _positive(bounds[0], f"{label}: dt50_range_days low"), _positive(bounds[1], f"{label}: dt50_range_days high")
    if not low < dt50 < high:
        raise TpFateInputError(f"{label}: dt50_range_days must satisfy low < DT50 < high")
    sd = (math.log10(high) - math.log10(low)) / (2.0 * Z90)
    return {"source": "user_range", "range_days": [low, high], "log10_sd_mean": sd, "log10_sd_single_soil": sd, "confidence": "user range (90 %)"}


def _rate_matrices(ks: np.ndarray, ffs: list[float], sources: list[int]) -> np.ndarray:
    """Rate matrices for a stack of rate-constant vectors ks (S, n + 1): dY/dt = A Y."""

    samples, size = ks.shape
    rate = np.zeros((samples, size, size))
    rate[:, 0, 0] = -ks[:, 0]
    for j in range(1, size):
        source_index = sources[j - 1] + 1
        rate[:, j, source_index] += ffs[j - 1] * ks[:, source_index]
        rate[:, j, j] -= ks[:, j]
    return rate


def _uncertainty_band(
    parent: dict[str, Any], products: list[dict[str, Any]], sources: list[int], *, duration: float, c0: float, p0_mol: float,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Monte Carlo band: sample each uncertain DT50 log-normally and independently, rerun the kinetics, take percentiles.

    Only DT50s with a stated uncertainty are sampled (PEPPER intervals or a user 90 % range); everything else,
    including every formation fraction, is held at its central value and named as such. The 5/50/95 % lines are
    percentiles of concentration AT EACH TIME, not a single scenario. Sampling is seeded, so a result reproduces.
    """

    from scipy.stats import spearmanr

    basis = config.get("basis", "single_soil")
    if basis not in BAND_BASES:
        raise TpFateInputError(f"uncertainty.basis must be one of {BAND_BASES}")
    n_samples = int(config.get("n_samples", 400))
    if not 50 <= n_samples <= 2000:
        raise TpFateInputError("uncertainty.n_samples must be between 50 and 2000")
    seed = int(config.get("seed", 20260924))

    substances = [parent, *products]
    sd_key = "log10_sd_single_soil" if basis == "single_soil" else "log10_sd_mean"
    sampled: list[int] = []
    sds: dict[int, float] = {}
    for index, substance in enumerate(substances):
        u = substance.get("dt50_uncertainty") or {}
        sd = u.get(sd_key) if u.get(sd_key) is not None else u.get("log10_sd_mean")
        if sd is not None and sd > 0 and math.isfinite(substance["dt50_days"]):
            sampled.append(index)
            sds[index] = float(sd)
    fixed = [s["name"] for i, s in enumerate(substances) if i not in sds]
    if not sampled:
        return {"available": False, "reason": "no DT50 carries an uncertainty (use a PEPPER prediction or give dt50_range_days), or the soil is frozen", "fixed": fixed}

    rng = np.random.default_rng(seed)
    n = len(products)
    central = np.array([math.log(2.0) / s["dt50_days"] if math.isfinite(s["dt50_days"]) else 0.0 for s in substances])
    ks = np.tile(central, (n_samples, 1))
    log10_draws = {}
    for index in sampled:
        z = rng.standard_normal(n_samples)
        scale = 10.0 ** (sds[index] * z)  # multiplies the input DT50; the temperature factor is a constant, so it carries through
        ks[:, index] = central[index] / scale
        log10_draws[index] = sds[index] * z
    ffs = [p["formation_fraction"] for p in products]
    rate = _rate_matrices(ks, ffs, sources)
    grid = np.linspace(0.0, duration, BAND_TIME_POINTS)
    # Uniform time grid: one matrix exponential per sample for the step dt, then repeated multiplication. Exact
    # (exp(A (i+1) dt) e0 = exp(A dt) exp(A i dt) e0) and far cheaper than an exponential per sample and time.
    step = expm(rate * (duration / (BAND_TIME_POINTS - 1)))  # (S, n + 1, n + 1)
    conc = np.zeros((n_samples, BAND_TIME_POINTS, n + 1))
    conc[:, 0, 0] = 1.0
    for i in range(1, BAND_TIME_POINTS):
        conc[:, i, :] = np.einsum("sij,sj->si", step, conc[:, i - 1, :])
    conc = np.maximum(conc, 0.0)

    def lines(values: np.ndarray) -> dict[str, list[float]]:
        p05, p50, p95 = np.percentile(values, BAND_PERCENTILES, axis=0)
        return {"p05": p05.tolist(), "p50": p50.tolist(), "p95": p95.tolist()}

    parent_out = {"name": parent["name"], "percent_of_applied_molar": lines(conc[:, :, 0] * 100.0), "mg_kg": lines(conc[:, :, 0] * c0)}
    products_out = []
    for j, product in enumerate(products, start=1):
        mw = product["molecular_weight_g_mol"]
        series = conc[:, :, j]
        peaks = series.max(axis=1) * 100.0
        peak_times = grid[series.argmax(axis=1)]
        p05, p50, p95 = np.percentile(peaks, BAND_PERCENTILES)
        t05, t50, t95 = np.percentile(peak_times, BAND_PERCENTILES)
        drivers = []
        for index in sampled:
            if np.ptp(peaks) == 0.0:
                break
            rho = spearmanr(log10_draws[index], peaks).statistic
            if math.isfinite(rho):
                drivers.append({"substance": substances[index]["name"], "spearman_rho": float(rho)})
        drivers.sort(key=lambda d: -abs(d["spearman_rho"]))
        products_out.append({
            "name": product["name"],
            "percent_of_applied_molar": lines(series * 100.0), "mg_kg": lines(series * p0_mol * mw),
            "peak_percent_of_applied_molar": {"p05": float(p05), "p50": float(p50), "p95": float(p95)},
            "peak_time_days": {"p05": float(t05), "p50": float(t50), "p95": float(t95)},
            "probability_major_transformation_product": float(np.mean(peaks >= MAJOR_TP_PERCENT)),
            "drivers": drivers,
        })
    return {
        "available": True, "method": "Monte Carlo, independent log-normal DT50s, seeded", "n_samples": n_samples, "seed": seed,
        "basis": basis, "percentiles": list(BAND_PERCENTILES), "times_days": grid.tolist(),
        "sampled": [{"name": substances[i]["name"], "log10_sd": sds[i], "source": (substances[i].get("dt50_uncertainty") or {}).get("source", "pepper")} for i in sampled],
        "fixed": fixed, "parent": parent_out, "products": products_out,
        "notes": [
            "Percentiles are taken at each time separately; they are not one scenario and neighbouring points do not belong to one curve.",
            "Only DT50s with a stated uncertainty are sampled. Formation fractions and every fixed substance are held at their central values, so the band understates the full uncertainty.",
            "Peak time and height are resolved on a " + str(BAND_TIME_POINTS) + "-point grid (about duration/120 days).",
            "single_soil basis adds the between-soil spread to the model uncertainty (a single site); mean basis is the uncertainty of the typical soil only.",
        ],
    }



def run_tp_soil_fate(payload: dict[str, Any]) -> dict[str, Any]:
    parent_in = payload.get("parent") or {}
    products_in = payload.get("products") or []
    if not products_in:
        raise TpFateInputError("at least one transformation product is required")
    if len(products_in) > 8:
        raise TpFateInputError("at most 8 main-stage transformation products are supported")
    c0 = _positive(payload.get("initial_parent_mg_kg"), "initial_parent_mg_kg")
    duration = _positive(payload.get("duration_days", 365.0), "duration_days")
    if duration > MAX_DURATION_DAYS:
        raise TpFateInputError(f"duration_days must not exceed {MAX_DURATION_DAYS:g}")
    n_points = int(payload.get("n_points", 121))
    if not 11 <= n_points <= 1001:
        raise TpFateInputError("n_points must be between 11 and 1001")

    region = payload.get("region")
    explicit_t = payload.get("temperature_c")
    if explicit_t is not None:
        if isinstance(explicit_t, bool) or not isinstance(explicit_t, (int, float)) or not -50 < explicit_t < 60:
            raise TpFateInputError("temperature_c must be a number between -50 and 60 C")
        target_c, temperature_basis = float(explicit_t), "explicit temperature_c"
    elif region is not None:
        if region not in REGION_TEMPERATURE_C:
            raise TpFateInputError(f"no reference temperature is recorded for region {region!r}; pass temperature_c explicitly")
        target_c, temperature_basis = REGION_TEMPERATURE_C[region], f"region {region} (owner-stated)"
    else:
        target_c, temperature_basis = REFERENCE_TEMPERATURE_C, "OECD 307 reference temperature (no region or temperature given)"

    soil = payload.get("soil") or {}
    warnings: list[str] = []
    if target_c <= 0:
        warnings.append("At or below 0 C the FOCUS convention allows no degradation: DT50s are infinite and nothing forms or declines.")

    mw_p, logp_p, notes_p = _structure_properties(parent_in, "parent")
    dt_p = _dt50_at_target(parent_in, "parent", target_c)
    k_p = 0.0 if math.isinf(dt_p["dt50_days"]) else math.log(2.0) / dt_p["dt50_days"]
    parent = {
        "name": parent_in.get("name") or "parent", "molecular_weight_g_mol": mw_p, "log_p": logp_p,
        "pka_a": parent_in.get("pka_a"), "pka_b": parent_in.get("pka_b"), "property_notes": notes_p,
        **dt_p, "k_per_day": k_p, "sorption": _koc(parent_in, logp_p, soil, "parent"),
    }

    # ---- build the reaction tree: every product has exactly one source (the parent or another product) ----
    names = [(entry.get("name") or f"product {i}").strip() for i, entry in enumerate(products_in, start=1)]
    if len(set(names)) != len(names) or parent["name"] in names:
        raise TpFateInputError("substance names must be unique (parent and every product), so 'formed_from' is unambiguous")
    sources: list[int] = []  # -1 = parent, otherwise index into products
    for index, entry in enumerate(products_in):
        ref = entry.get("formed_from")
        if ref is None or ref == "parent" or ref == parent["name"]:
            sources.append(-1)
        elif ref in names:
            sources.append(names.index(ref))
        else:
            raise TpFateInputError(f"product {index + 1} ({names[index]}): formed_from {ref!r} is not the parent or a listed product")
    generations: list[int] = []
    for index in range(len(products_in)):
        depth, node, seen = 1, sources[index], {index}
        while node != -1:
            if node in seen:
                raise TpFateInputError(f"product {index + 1} ({names[index]}): formed_from creates a loop; reversible steps are not supported")
            seen.add(node)
            depth += 1
            node = sources[node]
        generations.append(depth)

    products: list[dict[str, Any]] = []
    defaulted_sources: set[int] = set()
    for index, entry in enumerate(products_in, start=1):
        label = f"product {index} ({names[index - 1]})"
        mw, log_p, notes = _structure_properties(entry, label)
        if entry.get("formation_fraction") is None:
            ff, ff_basis = 1.0, FF_DEFAULT_NOTE
            defaulted_sources.add(sources[index - 1])
        else:
            ff = float(entry["formation_fraction"])
            if isinstance(entry["formation_fraction"], bool) or not math.isfinite(ff) or not 0 < ff <= 1:
                raise TpFateInputError(f"{label}: formation_fraction must be in (0, 1] (molar)")
            ff_basis = entry.get("formation_fraction_source") or "supplied by the user"
        dt = _dt50_at_target(entry, label, target_c)
        k = 0.0 if math.isinf(dt["dt50_days"]) else math.log(2.0) / dt["dt50_days"]
        products.append({
            "name": names[index - 1], "formed_from": parent["name"] if sources[index - 1] == -1 else names[sources[index - 1]],
            "generation": generations[index - 1], "molecular_weight_g_mol": mw, "log_p": log_p,
            "pka_a": entry.get("pka_a"), "pka_b": entry.get("pka_b"), "property_notes": notes,
            "formation_fraction": ff, "formation_fraction_basis": ff_basis, **dt, "k_per_day": k,
            "sorption": _koc(entry, log_p, soil, label),
        })
    if defaulted_sources:
        warnings.append("Defaulted formation fractions are per-product worst cases and are not additive; they may sum above 1.")
    for source in {s for s in sources}:
        children = [j for j, s in enumerate(sources) if s == source]
        if source in defaulted_sources:
            continue  # this source has a defaulted (worst-case) child; the sum check would be meaningless
        total = sum(products[j]["formation_fraction"] for j in children)
        if total > 1.0 + 1e-9:
            who = parent["name"] if source == -1 else names[source]
            raise TpFateInputError(f"formation fractions from {who} sum to {total:.3f}, more than 1 (molar): a substance cannot yield more than it contains")

    # ---- linear kinetics: dY/dt = A Y, Y = moles per mole of parent applied [parent, product 1..n]; Y(t) = expm(A t) Y0 ----
    n = len(products)
    rate = np.zeros((n + 1, n + 1))
    rate[0, 0] = -k_p
    ks = [k_p] + [p["k_per_day"] for p in products]
    for j, product in enumerate(products, start=1):
        source_index = sources[j - 1] + 1  # parent -> 0, product i -> i + 1
        rate[j, source_index] += product["formation_fraction"] * ks[source_index]
        rate[j, j] -= product["k_per_day"]
    y0 = np.zeros(n + 1)
    y0[0] = 1.0

    def moles_at(t: float) -> np.ndarray:
        return expm(rate * t) @ y0

    p0_mol = c0 / mw_p  # mg/kg / (g/mol) = mmol/kg
    times = [duration * i / (n_points - 1) for i in range(n_points)]
    grid = np.array([moles_at(t) for t in times])  # (n_points, n + 1)
    parent["series_mg_kg"] = [float(v) * c0 for v in grid[:, 0]]
    dense_t = np.linspace(0.0, duration, 2001)
    dense = np.array([moles_at(t) for t in dense_t])
    for j, product in enumerate(products, start=1):
        kj, ff, mw = product["k_per_day"], product["formation_fraction"], product["molecular_weight_g_mol"]
        series = np.maximum(grid[:, j], 0.0)  # expm rounding can leave -1e-17
        product["series_mg_kg"] = [float(m) * p0_mol * mw for m in series]
        product["series_percent_of_applied_molar"] = [float(m) * 100.0 for m in series]
        if k_p == 0.0 or not np.any(dense[:, j] > 0.0):  # nothing degrades upstream, so nothing forms
            t_peak, peak_moles, within_window = None, 0.0, False
        elif sources[j - 1] == -1 and kj > 0.0:  # direct product of the parent: analytic peak
            t_peak = time_of_peak(k_p, kj)
            peak_moles = product_moles_fraction(t_peak, k_p, kj, ff)
            within_window = t_peak <= duration
        else:  # deeper generations (and non-degrading products): dense scan, then refine
            best = int(np.argmax(dense[:, j]))
            # an interior maximum must clearly exceed the end value; a plateau's rounding noise is not a peak
            within_window = bool(0 < best < len(dense_t) - 1 and dense[best, j] > dense[-1, j] * (1.0 + 1e-6))
            if within_window:
                res = minimize_scalar(lambda t: -moles_at(t)[j], bounds=(dense_t[best - 1], dense_t[best + 1]), method="bounded", options={"xatol": 1e-9})
                t_peak, peak_moles = float(res.x), float(-res.fun)
            else:
                t_peak, peak_moles = None, float(dense[best, j])
        observed_peak = max(product["series_percent_of_applied_molar"])
        product["peak"] = {
            "time_days": t_peak,
            "percent_of_applied_molar": peak_moles * 100.0 if within_window else observed_peak,
            "concentration_mg_kg": (peak_moles * p0_mol * mw) if within_window else max(product["series_mg_kg"]),
            "within_simulation_window": within_window,
        }
        product["major_transformation_product"] = {
            "flag": product["peak"]["percent_of_applied_molar"] >= MAJOR_TP_PERCENT, "threshold_percent": MAJOR_TP_PERCENT,
            "basis": "OECD TG 307 (2025) para 51: >= 10% of applied dose at any time (molar analogue)",
        }
        product["final_concentration_mg_kg"] = product["series_mg_kg"][-1]
        if not within_window and observed_peak > 0:
            warnings.append(f"{product['name']}: no interior peak within the {duration:g}-day window; the reported peak is the highest value in the window.")

    uncertainty_config = payload.get("uncertainty")
    band = None
    if uncertainty_config is not False and (uncertainty_config is None or isinstance(uncertainty_config, dict)):
        band = _uncertainty_band(parent, products, sources, duration=duration, c0=c0, p0_mol=p0_mol, config=uncertainty_config or {})
    elif uncertainty_config is not False:
        raise TpFateInputError("uncertainty must be an object, false or omitted")

    return {
        "model": "parent -> transformation products (chains and branches allowed), single first-order kinetics, molar basis",
        "target_temperature_c": target_c, "temperature_basis": temperature_basis,
        "initial_parent_mg_kg": c0, "duration_days": duration, "times_days": times,
        "parent": parent, "products": products, "uncertainty_band": band, "warnings": warnings,
        "limitations": [
            "Each product has one source (the parent or another listed product), forming a tree: no reversible steps, and no product formed from two sources.",
            "Single first-order (SFO) kinetics; biphasic behaviour (FOMC/DFOP/HS) is not represented.",
            "Later generations depend on the earlier products' DT50s and formation fractions; uncertainty compounds down the chain.",
            "Soil DT50s are estimates unless labelled measured; predictors were built on limited chemical classes.",
            "Concentrations are bulk-soil averages with no leaching, plant uptake, volatilisation or run-off.",
        ],
    }


# ---------------------------------------------------------------------------
# API (stateless: nothing is persisted)
# ---------------------------------------------------------------------------
from fastapi import APIRouter, HTTPException  # noqa: E402

router = APIRouter(prefix="/tp-soil-fate", tags=["transformation-product-fate"])


@router.get("/options")
def options() -> dict[str, Any]:
    return {
        "region_temperature_c": REGION_TEMPERATURE_C, "reference_temperature_c": REFERENCE_TEMPERATURE_C,
        "dt50_sources": list(DT50_SOURCES), "major_tp_percent": MAJOR_TP_PERCENT,
        "note": "Only owner-stated region temperatures are listed; other regions need an explicit temperature.",
    }


@router.post("/run")
def run(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = run_tp_soil_fate(payload)
    except TpFateInputError as exc:
        raise HTTPException(422, str(exc)) from exc
    # JSON has no infinity: an infinite DT50 (target at or below 0 C) is reported as null with the warning above.
    for substance in (result["parent"], *result["products"]):
        if math.isinf(substance["dt50_days"]):
            substance["dt50_days"] = None
    return result
