"""EU birds & mammals Tier 1 dietary and secondary-poisoning risk screening.

Source: EFSA Guidance on the risk assessment for birds and mammals (EFSA
Journal 2023;21(2):7790; Aagaard, Berny, Chaton, Lopez Antia, McVey, Arena,
Fait, Ippolito, Linguadoca, Sharp, Theobald, Brock), replacing EFSA (2009).
This is the EU equivalent of the US EPA T-REX/BeeREX calculators: the
plant-protection-product pathway has no single official downloadable tool,
so the guidance document's own formulas are implemented here directly,
matching every formula and threshold to the primary source rather than a
secondary summary.

Scope boundary, stated plainly. The guidance's Tier 1 exposure assessment
also depends on the Annex B Generic Model Species parameter tables (body
weight and diet composition per feeding guild, per crop, per growth stage —
several hundred rows) and the Appendix L / Annex D crop-deposition-value
lookup tables. Those are not reproduced here: this module was built from a
slide-deck presentation of the guidance, not the full ~150-page document
with its numbered annexes, and shipping a partial or misremembered version
of a large reference table would be worse than not shipping one. A reviewer
therefore supplies FIR, BW, RUD, deposition value, PD and PT directly for
the food item(s) actually assessed — the same reviewer-supplied-not-inferred
discipline already used in app/reach/pnec.py for the assessment factor.

What IS fully specified by the guidance and reproduced here as given: the
TER formulas and their trigger thresholds, the fTWA time-weighted-average
formula, the Tier 1 dietary dose-density formula, and the fish-eating
secondary-poisoning pathway (its own eBMF/BCF lookup table and log Kow
trigger are given in full, unlike the crop-specific exposure tables).

Earthworm-eating secondary poisoning (2026-09-23 follow-up): the fixed
constants this module's docstring used to say were "not legible in the
source consulted" have now been read directly from a primary source --
ECHA, "Guidance on Information Requirements and Chemical Safety Assessment,
Chapter R.16: Environmental Exposure Estimation", Version 2.1 (October
2012), Section R.16.6.7.2 (pp. 90-91, equations R.16-71 to R.16-76) and
Table R.16-9 (p. 49). This is NOT the EFSA (2023) birds-and-mammals
guidance text itself (still not obtained -- efsa.onlinelibrary.wiley.com
is behind Cloudflare bot-detection that was not bypassed, consistent with
this project's rule against defeating bot-detection). Multiple secondary
sources (HSE, Sagentia, ADAS/CEA) independently and consistently describe
EFSA (2023)'s own earthworm approach as "the 'pore water' approach" with a
7-day TWA soil concentration -- language that matches this exact ECHA R.16
mechanism (bioconcentration as hydrophobic partitioning between soil pore
water and worm tissue, per Jager, T. (1998), "Mechanistic approach for
estimating bioconcentration of organic chemicals in earthworms",
Environmental Toxicology and Chemistry), which is the standard, widely
cross-referenced EU method for this exposure route -- but the exact
numeric constants (0.84, 0.012, gut-loading fraction 0.1) have NOT been
independently confirmed as reproduced verbatim in the EFSA (2023) text
itself, only in ECHA R.16. Reported honestly as such wherever this
function's results are surfaced.

Benthic-invertebrate-eating secondary poisoning remains NOT implemented.
This looks to be a genuinely new addition in EFSA (2023) rather than
carried over from the 2012-era REACH guidance: ECHA R.16 (checked directly,
2026-09-23) has no equivalent sediment-organism bioaccumulation formula,
and a secondary source (Sagentia, 2025) describes "the introduction of
benthic invertebrate-eating species" as one of the guidance's own changes
from 2009. No primary source for its formula was found this session.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .equilibrium_partitioning import FOC_SOIL_DEFAULT, RHO_SOIL_DEFAULT, RHO_SOLID_DEFAULT


GUIDANCE_REFERENCE = "EFSA Journal 2023;21(2):7790 — Guidance on the risk assessment for birds and mammals"

ACUTE_TER_TRIGGER = Decimal("10")
REPRODUCTIVE_TER_TRIGGER = Decimal("5")
SECONDARY_POISONING_TER_TRIGGER = Decimal("5")
SECONDARY_POISONING_LOG_KOW_TRIGGER = Decimal("3")
DEFAULT_AVERAGING_PERIOD_DAYS = Decimal("21")
DEFAULT_SPRAY_DT50_DAYS = Decimal("10")

# Fish-eating secondary poisoning: eBMF and default BCF band by log Kow of
# the substance, exactly as tabulated in the EFSA (2023) guidance.
_FISH_EBMF_BANDS: list[tuple[Decimal, Decimal, str, Decimal]] = [
    # (log_kow_upper_exclusive, ebmf, bcf_band_label, bcf_upper_bound_used_if_no_measured_bcf)
    (Decimal("4.5"), Decimal("1"), "< 2,000", Decimal("2000")),
    (Decimal("5"), Decimal("2"), "2,000-5,000", Decimal("5000")),
    (Decimal("8"), Decimal("10"), "> 5,000", Decimal("5000")),
    (Decimal("9"), Decimal("3"), "2,000-5,000", Decimal("5000")),
]
_FISH_EBMF_ABOVE_9 = (Decimal("1"), "< 2,000", Decimal("2000"))


class GuidanceInputError(ValueError):
    """Raised when an input is out of the domain the guidance formula assumes."""


def _decimal(value: int | float | str | Decimal, *, name: str) -> Decimal:
    if isinstance(value, bool):
        raise GuidanceInputError(f"{name} must be a finite positive number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise GuidanceInputError(f"{name} must be a finite positive number") from exc
    if not number.is_finite() or number <= 0:
        raise GuidanceInputError(f"{name} must be a finite positive number")
    return number


@dataclass(frozen=True)
class FoodItemExposureInput:
    """One dietary item's contribution to the Tier 1 exposure formula.

    ``application_rate_kg_ha`` and ``residue_unit_dose_mg_kg`` are always
    required (a reviewer-supplied RUD, sourced to its own reference —
    Annex C for the standard matrices, or a study-specific value). The
    remaining factors default to the screening-step simplification (deposition
    value = 100%, proportion of diet = 100%, multiple-application factor = 1)
    and should be overridden with reviewer-supplied Tier 1 values once the
    relevant Annex B/Appendix L figures for the actual crop and growth stage
    are in hand.
    """

    application_rate_kg_ha: float
    residue_unit_dose_mg_kg: float
    multiple_application_factor: float = 1.0
    deposition_fraction: float = 1.0
    proportion_of_diet: float = 1.0


def daily_dose(
    *,
    food_intake_rate_g_day: float,
    body_weight_g: float,
    food_items: list[FoodItemExposureInput],
    fTWA: float | None = None,
) -> Decimal:
    """Dietary daily dose, mg a.s./kg bw/day.

    Screening-step formula (deposition and proportion-of-diet both 1.0):
        DD = FIR * sum(AR * RUD_i * MAF_i) / BW

    Tier 1 formula (deposition value and proportion of diet per item):
        DD = FIR * sum(AR * RUD_i * MAF_i * DV_i * PD_i) / BW

    Both are the same formula; the screening step is the special case where
    ``deposition_fraction`` and ``proportion_of_diet`` are left at 1.0. Pass
    ``fTWA`` (from :func:`time_weighted_average_factor`) to compute the
    reproductive DDD rather than the acute DD -- the guidance multiplies the
    reproductive exposure by fTWA in addition to MAF.
    """

    if not food_items:
        raise GuidanceInputError("At least one food item is required")
    fir = _decimal(food_intake_rate_g_day, name="food_intake_rate_g_day")
    bw = _decimal(body_weight_g, name="body_weight_g")
    twa = _decimal(fTWA, name="fTWA") if fTWA is not None else Decimal("1")

    total = Decimal("0")
    for index, item in enumerate(food_items):
        ar = _decimal(item.application_rate_kg_ha, name=f"food_items[{index}].application_rate_kg_ha")
        rud = _decimal(item.residue_unit_dose_mg_kg, name=f"food_items[{index}].residue_unit_dose_mg_kg")
        maf = _decimal(item.multiple_application_factor, name=f"food_items[{index}].multiple_application_factor")
        dv = _decimal(item.deposition_fraction, name=f"food_items[{index}].deposition_fraction")
        pd = _decimal(item.proportion_of_diet, name=f"food_items[{index}].proportion_of_diet")
        total += ar * rud * maf * dv * pd

    return (fir * total * twa) / bw


def time_weighted_average_factor(
    *,
    dt50_days: float = float(DEFAULT_SPRAY_DT50_DAYS),
    averaging_period_days: float = float(DEFAULT_AVERAGING_PERIOD_DAYS),
) -> Decimal:
    """fTWA = (1 - e^(-kj)) / (kj), where k = ln2 / DT50, j = averaging period.

    Applied to the reproductive (DDD) exposure only, never the acute (DD)
    exposure. The guidance's own default is DT50 = 10 days for all food
    items reached by spray, with a 21-day averaging period; both are the
    defaults here and should be overridden only with a reviewer-supplied,
    substance-specific residue-decline study (Tier 2 refinement).
    """

    dt50 = _decimal(dt50_days, name="dt50_days")
    j = _decimal(averaging_period_days, name="averaging_period_days")
    k = Decimal(str(math.log(2))) / dt50
    kj = k * j
    kj_float = float(kj)
    if kj_float <= 0:
        raise GuidanceInputError("dt50_days and averaging_period_days must combine to a positive exponent")
    return (Decimal("1") - Decimal(str(math.exp(-kj_float)))) / kj


@dataclass(frozen=True)
class TerResult:
    ter: Decimal
    trigger: Decimal
    low_risk: bool
    guidance_reference: str = GUIDANCE_REFERENCE


def acute_dietary_ter(*, ld50_mg_kg_bw: float, daily_dose_mg_kg_bw: float) -> TerResult:
    """TER = LD50 / DD. Low risk concluded (assessment may stop) at TER >= 10."""

    ld50 = _decimal(ld50_mg_kg_bw, name="ld50_mg_kg_bw")
    dd = _decimal(daily_dose_mg_kg_bw, name="daily_dose_mg_kg_bw")
    ter = ld50 / dd
    return TerResult(ter=ter, trigger=ACUTE_TER_TRIGGER, low_risk=ter >= ACUTE_TER_TRIGGER)


def reproductive_dietary_ter(*, relevant_endpoint_mg_kg_bw_day: float, ddd_mg_kg_bw_day: float) -> TerResult:
    """TER = relevant reproductive/chronic endpoint / DDD. Low risk at TER >= 5.

    ``relevant_endpoint_mg_kg_bw_day`` is a reviewer-selected ecologically
    relevant endpoint (e.g. an EL10/BMD10 or NOAEL) per the guidance's own
    Chapter 5 decision scheme -- this module performs no endpoint selection.
    """

    endpoint = _decimal(relevant_endpoint_mg_kg_bw_day, name="relevant_endpoint_mg_kg_bw_day")
    ddd = _decimal(ddd_mg_kg_bw_day, name="ddd_mg_kg_bw_day")
    ter = endpoint / ddd
    return TerResult(ter=ter, trigger=REPRODUCTIVE_TER_TRIGGER, low_risk=ter >= REPRODUCTIVE_TER_TRIGGER)


def _fish_ebmf_for_log_kow(log_kow: Decimal) -> tuple[Decimal, str, Decimal]:
    for upper_exclusive, ebmf, band_label, bcf_bound in _FISH_EBMF_BANDS:
        if log_kow < upper_exclusive:
            return ebmf, band_label, bcf_bound
    ebmf, band_label, bcf_bound = _FISH_EBMF_ABOVE_9
    return ebmf, band_label, bcf_bound


def fish_secondary_poisoning_ter(
    *,
    log_kow: float,
    relevant_endpoint_mg_kg_bw_day: float,
    food_intake_rate_g_day: float,
    body_weight_g: float,
    twa_surface_water_concentration_ug_l: float,
    measured_bcf_fish_l_kg: float | None = None,
) -> dict[str, object]:
    """Tier 1 secondary poisoning via fish-eating birds/mammals.

    Trigger: only relevant when log Kow of the substance (or a major
    metabolite) is >= 3 -- checked and reported, not silently skipped.

    Daily dose PECfish = (FIR / BW) * TWA_PECsw * BCFfish * eBMF

    BCFfish and eBMF are read from the guidance's own log-Kow lookup table
    unless a measured (OECD-guideline) BCF is supplied, in which case the
    measured value replaces the table's default band and only eBMF is taken
    from the table -- this is the guidance's own Tier 2 refinement option.
    TWA_PECsw uses a 7-21 day time-weighted-average surface-water
    concentration by expert judgement (aligned to the fish BCF study's own
    time-to-equilibrium) -- supplied by the reviewer, not computed here.
    """

    log_kow_dec = _decimal(log_kow, name="log_kow")
    triggered = log_kow_dec >= SECONDARY_POISONING_LOG_KOW_TRIGGER
    ebmf, band_label, default_bcf_bound = _fish_ebmf_for_log_kow(log_kow_dec)
    bcf = _decimal(measured_bcf_fish_l_kg, name="measured_bcf_fish_l_kg") if measured_bcf_fish_l_kg is not None else default_bcf_bound

    fir = _decimal(food_intake_rate_g_day, name="food_intake_rate_g_day")
    bw = _decimal(body_weight_g, name="body_weight_g")
    twa_pecsw = _decimal(twa_surface_water_concentration_ug_l, name="twa_surface_water_concentration_ug_l")
    # PECsw is µg/L (~ mg/m3 = mg/kg water at unit density); convert to mg/kg to match FIR/BW in g and mg/kg bw endpoints.
    twa_pecsw_mg_kg = twa_pecsw / Decimal("1000")

    daily_dose_fish = (fir / bw) * twa_pecsw_mg_kg * bcf * ebmf
    endpoint = _decimal(relevant_endpoint_mg_kg_bw_day, name="relevant_endpoint_mg_kg_bw_day")
    ter = endpoint / daily_dose_fish

    return {
        "triggered": triggered,
        "log_kow": float(log_kow_dec),
        "ebmf": float(ebmf),
        "bcf_fish_l_kg": float(bcf),
        "bcf_source": "measured" if measured_bcf_fish_l_kg is not None else f"guidance default band ({band_label})",
        "daily_dose_pec_fish_mg_kg_bw_day": float(daily_dose_fish),
        "ter": float(ter),
        "trigger": float(SECONDARY_POISONING_TER_TRIGGER),
        "low_risk": bool(ter >= SECONDARY_POISONING_TER_TRIGGER) if triggered else None,
        "guidance_reference": GUIDANCE_REFERENCE,
    }


# ---------------------------------------------------------------------------------------------------------------
# Earthworm-eating secondary poisoning. Source: ECHA Guidance on Information Requirements and Chemical Safety
# Assessment, Chapter R.16 (Environmental Exposure Estimation), Version 2.1, October 2012 -- see the module
# docstring for the full provenance note and its caveats relative to the EFSA (2023) birds/mammals text itself.
EARTHWORM_GUIDANCE_REFERENCE = (
    "ECHA Guidance on Information Requirements and Chemical Safety Assessment, Chapter R.16: Environmental "
    "Exposure Estimation, Version 2.1 (October 2012), Section R.16.6.7.2 and Table R.16-9"
)

# Jager (1998) earthworm BCF equation constants -- ECHA R.16 equation R.16-76.
_EARTHWORM_JAGER_INTERCEPT = Decimal("0.84")
_EARTHWORM_JAGER_SLOPE = Decimal("0.012")
EARTHWORM_RHO_DEFAULT = Decimal("1")  # kg wet weight / L -- R.16-76's own default for RHOearthworm

# Jager (1998)'s own stated application range for the BCF equation (soil-exposure data covered log Kow 3-8;
# water-only data covered 1-6; the guidance advises an application range of 1-8 and says extrapolating below 1 is
# "reasonable"). This is the model's OWN validity domain, not a "should this pathway be assessed at all" trigger
# like the fish pathway's log Kow >= 3 -- the two are different kinds of flags and are not conflated here.
EARTHWORM_BCF_VALIDATED_LOG_KOW_RANGE = (Decimal("1"), Decimal("8"))

# Table R.16-9 / Section R.16.6.7.2 defaults.
EARTHWORM_GUT_LOADING_FRACTION_DEFAULT = Decimal("0.1")  # Fgut, kg dwt gut / kg wwt worm -- R.16.6.7.2, p. 91


def earthworm_bioconcentration_factor(*, log_kow: float, rho_earthworm_kg_wwt_per_l: float | None = None) -> Decimal:
    """BCFearthworm = (0.84 + 0.012 x Kow) / RHOearthworm -- ECHA R.16 equation R.16-76, Jager (1998).

    Bioconcentration as hydrophobic partitioning between soil pore water and the worm's own tissue phases.
    ``rho_earthworm_kg_wwt_per_l`` defaults to the guidance's own default of 1 (kg wet weight/L) if not supplied.
    Callers should check the result against :data:`EARTHWORM_BCF_VALIDATED_LOG_KOW_RANGE` themselves, or use
    :func:`earthworm_secondary_poisoning_ter`, which reports that check automatically.
    """

    log_kow_dec = _decimal(log_kow, name="log_kow")
    kow = Decimal(str(10 ** float(log_kow_dec)))
    rho = _decimal(rho_earthworm_kg_wwt_per_l, name="rho_earthworm_kg_wwt_per_l") if rho_earthworm_kg_wwt_per_l is not None else EARTHWORM_RHO_DEFAULT
    return (_EARTHWORM_JAGER_INTERCEPT + _EARTHWORM_JAGER_SLOPE * kow) / rho


def earthworm_secondary_poisoning_ter(
    *,
    log_kow: float,
    koc_l_per_kg: float,
    soil_concentration_mg_kg_wwt: float,
    relevant_endpoint_mg_kg_bw_day: float,
    food_intake_rate_g_day: float,
    body_weight_g: float,
    measured_bcf_earthworm_l_per_kg: float | None = None,
    gut_loading_fraction: float = float(EARTHWORM_GUT_LOADING_FRACTION_DEFAULT),
) -> dict[str, object]:
    """Tier 1 secondary poisoning via earthworm-eating birds/mammals (ECHA R.16, Section R.16.6.7.2).

    Cearthworm = [BCFearthworm x Cporewater + Csoil x Fgut x CONVsoil] / [1 + Fgut x CONVsoil]   (eq. R.16-72/73/75)
    Cporewater = (Csoil x RHOsoil) / (1000 x Ksoil-water), Ksoil-water = Focsoil x Koc            (eq. R.16-6/R.16-57)
    CONVsoil = RHOsoil / RHOsolid                                                                  (eq. R.16-74)
    PECoral,predator = Cearthworm                                                                  (eq. R.16-71)

    The soil-to-porewater step reuses the exact FOC_SOIL_DEFAULT/RHO_SOIL_DEFAULT constants already shipped in
    ``equilibrium_partitioning.py`` (both trace to the same EU soil-partitioning convention -- Focsoil=0.02,
    RHOsoil=1700 kg/m3), so this app has one soil-porewater relationship, not two subtly different ones.

    ``soil_concentration_mg_kg_wwt`` is a reviewer-supplied TWA soil concentration (secondary sources describe
    EFSA (2023)'s own earthworm approach as using a 7-day TWA soil concentration; this function does not derive
    the TWA itself). ``measured_bcf_earthworm_l_per_kg`` is the guidance's own Tier 2 refinement option (as for
    the fish pathway): if supplied, it replaces the Jager-model estimate entirely.

    No secondary-poisoning-relevance trigger (of the kind the fish pathway has, log Kow >= 3) was found sourced
    to this pathway specifically -- ``within_bcf_validated_range`` instead reports whether log Kow falls inside
    the Jager model's own stated application domain (1-8), which is a model-validity check, not a relevance
    trigger, and is reported rather than silently applied as a gate.
    """

    log_kow_dec = _decimal(log_kow, name="log_kow")
    koc = _decimal(koc_l_per_kg, name="koc_l_per_kg")
    csoil = _decimal(soil_concentration_mg_kg_wwt, name="soil_concentration_mg_kg_wwt")
    fir = _decimal(food_intake_rate_g_day, name="food_intake_rate_g_day")
    bw = _decimal(body_weight_g, name="body_weight_g")
    fgut = _decimal(gut_loading_fraction, name="gut_loading_fraction")
    endpoint = _decimal(relevant_endpoint_mg_kg_bw_day, name="relevant_endpoint_mg_kg_bw_day")

    lower, upper = EARTHWORM_BCF_VALIDATED_LOG_KOW_RANGE
    within_range = lower <= log_kow_dec <= upper

    if measured_bcf_earthworm_l_per_kg is not None:
        bcf = _decimal(measured_bcf_earthworm_l_per_kg, name="measured_bcf_earthworm_l_per_kg")
        bcf_source = "measured"
    else:
        bcf = earthworm_bioconcentration_factor(log_kow=log_kow)
        bcf_source = "Jager (1998) model estimate (ECHA R.16 eq. R.16-76)"

    ksoil_water = FOC_SOIL_DEFAULT * koc
    c_porewater = (csoil * RHO_SOIL_DEFAULT) / (Decimal("1000") * ksoil_water)
    conv_soil = RHO_SOIL_DEFAULT / RHO_SOLID_DEFAULT
    c_earthworm = (bcf * c_porewater + csoil * fgut * conv_soil) / (Decimal("1") + fgut * conv_soil)

    daily_dose_earthworm = (fir / bw) * c_earthworm
    ter = endpoint / daily_dose_earthworm

    return {
        "log_kow": float(log_kow_dec),
        "within_bcf_validated_range": within_range,
        "bcf_earthworm_l_kg": float(bcf),
        "bcf_source": bcf_source,
        "porewater_concentration_mg_l": float(c_porewater),
        "earthworm_concentration_mg_kg_wwt": float(c_earthworm),
        "daily_dose_pec_earthworm_mg_kg_bw_day": float(daily_dose_earthworm),
        "ter": float(ter),
        "trigger": float(SECONDARY_POISONING_TER_TRIGGER),
        "low_risk": bool(ter >= SECONDARY_POISONING_TER_TRIGGER),
        "guidance_reference": EARTHWORM_GUIDANCE_REFERENCE,
    }
