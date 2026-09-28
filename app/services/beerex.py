"""Tri-agency (US EPA / PMRA / California DPR) Bee-REX Tier 1 exposure screen for honey bees.

FateIntel previously had the RISK side of this triad (PMRA's LOC 0.4 acute / 1.0 chronic,
`app/services/pmra_pesticides.py`) but no genuine EXPOSURE model to feed it -- a reviewer had to supply the
dose themselves. This module is the missing exposure side: USEPA/PMRA/CADPR's own Bee-REX Tier 1 screening
method, read directly from the primary source (not recalled or taken from a secondary description).

Source: USEPA, PMRA and California DPR, "Guidance for Assessing Pesticide Risks to Bees" (19 June 2014),
<https://www.epa.gov/sites/production/files/2014-06/documents/pollinator_risk_assessment_guidance_06_19_14.pdf>,
fetched and read in full (59 pages) 2026-09-28, Appendix 3 "Bee REX" (pp. 48-59). Bee-REX itself is a
screening-level individual-bee (not colony-level) Tier 1 tool; its own documented limitation (p.48) is that it
does not quantify exposure via dust from seed-treatment abrasion, or via water/puddles/guttation fluid.

Three of the four application-method pathways Bee-REX covers are implemented here, each with a real, closed-form
Tier 1 equation given in the primary text:

- **Foliar spray** (`foliar_spray_*`): dietary residue is the upper-bound "tall grass" surrogate from the T-REX
  model (98 ug a.i./g per 1 kg a.i./ha); contact exposure is Koch & Weisser (1997)'s upper-bound value
  (2.4 ug a.i./bee per 1 kg a.i./ha). Both are surrogates for concentration in nectar/pollen and direct-spray
  deposition on a foraging bee respectively -- not measured values.
- **Seed treatment** (`seed_treatment_*`): a fixed ICP-BR (2010) upper-bound concentration of 1 mg a.i./kg
  (= 1 ug a.i./g) in nectar and pollen, independent of application rate -- the guidance's own stated approach for
  this method, "with no need for adjustment based on application rate or chemical properties."
- **Soil treatment** (`soil_treatment_*`): the modified Briggs et al. (1982, 1983) plant-uptake ("Briggs")
  model, relating log Kow to a root/stem concentration factor and Koc-based soil-pore-water partitioning, using
  the guidance's own conservative fixed soil parameters (foc=0.01, bulk density 1.5 g-dw/cm3, water content
  0.2 cm3/cm3). The guidance names five of its own limitations for this model (single plant type, narrow
  chemical-class calibration set, non-ionic-organics-only, xylem-only transport, shoot-concentration-as-nectar/
  pollen-surrogate) -- reported here, not silently applied as if exact.

**Tree trunk applications are deliberately NOT implemented**: the guidance itself states no standard equation is
given ("a standard equation is not provided here" -- tree leaf/flower mass varies by species and age and must
come from an external source per application) -- there is nothing primary-sourced to implement.

Dietary doses use the adult (0.292 g/day) and larval (0.124 g/day) worker-bee consumption rates Appendix 3
Table 1 uses for its own RQ derivations (Table 2 in the same appendix also gives caste/task-specific rates for a
refined assessment -- not reproduced here, since Table 1's Tier I screen uses only these two).

Risk quotients (RQ = exposure / toxicity endpoint) are compared against the same Level of Concern values already
used in `pmra_pesticides.py` (LOC 0.4 acute, 1.0 chronic) -- this module does not re-derive or duplicate that
comparison logic, it only computes the exposure/dose side and the resulting RQ; a reviewer supplies the toxicity
endpoint, exactly as every other risk-characterisation module in this app requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


GUIDANCE_REFERENCE = (
    "USEPA, PMRA and California DPR, \"Guidance for Assessing Pesticide Risks to Bees\" (19 June 2014), "
    "Appendix 3 \"Bee REX\""
)

LOC_ACUTE = Decimal("0.4")
LOC_CHRONIC = Decimal("1.0")

ADULT_CONSUMPTION_G_PER_DAY = Decimal("0.292")
LARVAL_CONSUMPTION_G_PER_DAY = Decimal("0.124")

# Foliar spray: T-REX tall-grass upper-bound residue surrogate for nectar/pollen; Koch & Weisser (1997) contact value.
FOLIAR_DIETARY_RESIDUE_UG_PER_G_PER_KG_HA = Decimal("98")
FOLIAR_CONTACT_UG_PER_BEE_PER_KG_HA = Decimal("2.4")

# Seed treatment: ICP-BR (2010) fixed upper-bound concentration, independent of application rate.
SEED_TREATMENT_RESIDUE_UG_PER_G = Decimal("1")

# Soil treatment (modified Briggs model): the guidance's own conservative, PRZM-consistent defaults.
SOIL_FOC = Decimal("0.01")
SOIL_BULK_DENSITY_G_DW_PER_CM3 = Decimal("1.5")
SOIL_WATER_CONTENT_CM3_PER_CM3 = Decimal("0.2")
# The guidance's own worked conversion at 15 cm (6 in) mixing depth and the bulk density above.
SOIL_CSOIL_UG_PER_G_PER_KG_HA = Decimal("0.45")

Pathway = Literal["foliar_spray", "seed_treatment", "soil_treatment"]
BeeLifeStage = Literal["adult", "larval"]


class BeeRexInputError(ValueError):
    """Raised when an input is not a finite positive number where one is required."""


def _decimal(value: int | float | str | Decimal, *, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001 - any conversion failure is a bad input, not a bug here
        raise BeeRexInputError(f"{name} must be a finite number") from exc
    if not result.is_finite():
        raise BeeRexInputError(f"{name} must be a finite number")
    return result


def _positive_decimal(value: int | float | str | Decimal, *, name: str) -> Decimal:
    result = _decimal(value, name=name)
    if result <= 0:
        raise BeeRexInputError(f"{name} must be a positive number")
    return result


@dataclass(frozen=True)
class BeeRexResult:
    pathway: Pathway
    exposure_route: Literal["contact", "diet"]
    life_stage: BeeLifeStage | None
    exposure_estimate: Decimal
    exposure_unit: str
    toxicity_endpoint: Decimal
    risk_quotient: Decimal
    loc: Decimal
    exceeds_loc: bool
    guidance_reference: str = GUIDANCE_REFERENCE


def _rq_result(*, pathway: Pathway, route: Literal["contact", "diet"], life_stage: BeeLifeStage | None,
                exposure: Decimal, unit: str, endpoint: Decimal, chronic: bool) -> BeeRexResult:
    loc = LOC_CHRONIC if chronic else LOC_ACUTE
    rq = exposure / endpoint
    return BeeRexResult(
        pathway=pathway, exposure_route=route, life_stage=life_stage,
        exposure_estimate=exposure, exposure_unit=unit, toxicity_endpoint=endpoint,
        risk_quotient=rq, loc=loc, exceeds_loc=bool(rq >= loc),
    )


# ------------------------------------------------------------------------------------------------- foliar spray

def foliar_spray_dietary_residue_ug_per_g(*, application_rate_kg_ha: float) -> Decimal:
    """Upper-bound pesticide concentration in nectar/pollen (T-REX tall-grass surrogate), ug a.i./g."""

    rate = _positive_decimal(application_rate_kg_ha, name="application_rate_kg_ha")
    return FOLIAR_DIETARY_RESIDUE_UG_PER_G_PER_KG_HA * rate


def foliar_spray_contact_dose_ug_per_bee(*, application_rate_kg_ha: float) -> Decimal:
    """Upper-bound direct-spray contact dose, ug a.i./bee (Koch & Weisser, 1997)."""

    rate = _positive_decimal(application_rate_kg_ha, name="application_rate_kg_ha")
    return FOLIAR_CONTACT_UG_PER_BEE_PER_KG_HA * rate


def foliar_spray_dietary_dose_ug_per_bee(*, application_rate_kg_ha: float, life_stage: BeeLifeStage) -> Decimal:
    """Dietary dose (residue x consumption rate), ug a.i./bee/day, for the given life stage."""

    residue = foliar_spray_dietary_residue_ug_per_g(application_rate_kg_ha=application_rate_kg_ha)
    consumption = ADULT_CONSUMPTION_G_PER_DAY if life_stage == "adult" else LARVAL_CONSUMPTION_G_PER_DAY
    return residue * consumption


def foliar_spray_contact_rq(*, application_rate_kg_ha: float, contact_ld50_ug_per_bee: float) -> BeeRexResult:
    dose = foliar_spray_contact_dose_ug_per_bee(application_rate_kg_ha=application_rate_kg_ha)
    endpoint = _positive_decimal(contact_ld50_ug_per_bee, name="contact_ld50_ug_per_bee")
    return _rq_result(pathway="foliar_spray", route="contact", life_stage=None, exposure=dose,
                       unit="ug a.i./bee", endpoint=endpoint, chronic=False)


def foliar_spray_dietary_rq(*, application_rate_kg_ha: float, life_stage: BeeLifeStage,
                             toxicity_endpoint_ug_per_bee: float, chronic: bool) -> BeeRexResult:
    dose = foliar_spray_dietary_dose_ug_per_bee(application_rate_kg_ha=application_rate_kg_ha, life_stage=life_stage)
    endpoint = _positive_decimal(toxicity_endpoint_ug_per_bee, name="toxicity_endpoint_ug_per_bee")
    return _rq_result(pathway="foliar_spray", route="diet", life_stage=life_stage, exposure=dose,
                       unit="ug a.i./bee/day", endpoint=endpoint, chronic=chronic)


# ---------------------------------------------------------------------------------------------- seed treatment

def seed_treatment_dietary_dose_ug_per_bee(*, life_stage: BeeLifeStage) -> Decimal:
    """Fixed ICP-BR (2010) upper-bound dietary dose -- independent of application rate or chemical properties."""

    consumption = ADULT_CONSUMPTION_G_PER_DAY if life_stage == "adult" else LARVAL_CONSUMPTION_G_PER_DAY
    return SEED_TREATMENT_RESIDUE_UG_PER_G * consumption


def seed_treatment_dietary_rq(*, life_stage: BeeLifeStage, toxicity_endpoint_ug_per_bee: float,
                               chronic: bool) -> BeeRexResult:
    dose = seed_treatment_dietary_dose_ug_per_bee(life_stage=life_stage)
    endpoint = _positive_decimal(toxicity_endpoint_ug_per_bee, name="toxicity_endpoint_ug_per_bee")
    return _rq_result(pathway="seed_treatment", route="diet", life_stage=life_stage, exposure=dose,
                       unit="ug a.i./bee/day", endpoint=endpoint, chronic=chronic)


# ---------------------------------------------------------------------------------------------- soil treatment

def briggs_transpiration_stream_concentration_factor(*, log_kow: float) -> Decimal:
    """TSCF (Equation 2): -0.0648 x (log Kow)^2 + 0.241 x log Kow + 0.5822."""

    kow = _decimal(log_kow, name="log_kow")
    return Decimal("-0.0648") * kow * kow + Decimal("0.241") * kow + Decimal("0.5822")


def briggs_root_concentration_factor(*, log_kow: float) -> Decimal:
    """The bracketed 10^(0.95 x log Kow - 2.05) + 0.82 term of Equation 1 (Briggs et al. 1982's own RCF form)."""

    kow = _decimal(log_kow, name="log_kow")
    exponent = Decimal("0.95") * kow - Decimal("2.05")
    return Decimal(str(10.0 ** float(exponent))) + Decimal("0.82")


def soil_treatment_stem_concentration_ug_per_g(
    *, application_rate_kg_ha: float, log_kow: float, koc_l_per_kg: float,
) -> Decimal:
    """Cstem (Equation 1): the modified-Briggs estimate of pesticide concentration in plant stems/shoots, used
    as the surrogate for concentration in nectar and pollen for a soil-applied, systemic pesticide.

    Uses the guidance's own conservative fixed soil parameters (SOIL_FOC, SOIL_BULK_DENSITY_G_DW_PER_CM3,
    SOIL_WATER_CONTENT_CM3_PER_CM3) and its own worked application-rate-to-soil-concentration conversion
    (SOIL_CSOIL_UG_PER_G_PER_KG_HA), not general-purpose soil-partitioning constants from elsewhere in this app.
    """

    rate = _positive_decimal(application_rate_kg_ha, name="application_rate_kg_ha")
    koc = _positive_decimal(koc_l_per_kg, name="koc_l_per_kg")
    c_soil = SOIL_CSOIL_UG_PER_G_PER_KG_HA * rate
    rcf = briggs_root_concentration_factor(log_kow=log_kow)
    tscf = briggs_transpiration_stream_concentration_factor(log_kow=log_kow)
    partition = SOIL_BULK_DENSITY_G_DW_PER_CM3 / (
        SOIL_WATER_CONTENT_CM3_PER_CM3 + SOIL_BULK_DENSITY_G_DW_PER_CM3 * koc * SOIL_FOC
    )
    return rcf * tscf * partition * c_soil


def soil_treatment_dietary_dose_ug_per_bee(
    *, application_rate_kg_ha: float, log_kow: float, koc_l_per_kg: float, life_stage: BeeLifeStage,
) -> Decimal:
    residue = soil_treatment_stem_concentration_ug_per_g(
        application_rate_kg_ha=application_rate_kg_ha, log_kow=log_kow, koc_l_per_kg=koc_l_per_kg,
    )
    consumption = ADULT_CONSUMPTION_G_PER_DAY if life_stage == "adult" else LARVAL_CONSUMPTION_G_PER_DAY
    return residue * consumption


def soil_treatment_dietary_rq(
    *, application_rate_kg_ha: float, log_kow: float, koc_l_per_kg: float, life_stage: BeeLifeStage,
    toxicity_endpoint_ug_per_bee: float, chronic: bool,
) -> BeeRexResult:
    if log_kow >= 5:
        # The guidance's own stated bound on the Briggs model's calibration data set (Section 1.3.2): systemic
        # transport is assumed for the Tier I approach, but only within log Kow < 5, the range the empirical
        # Briggs data set covers. Reported as a hard refusal, not a silently out-of-domain number.
        raise BeeRexInputError(
            "The modified-Briggs soil-treatment model's calibration data set is bounded to log Kow < 5 "
            "(Guidance for Assessing Pesticide Risks to Bees, Section 1.3.2); this substance's log Kow is outside "
            "that domain, so no soil-treatment exposure estimate is offered."
        )
    dose = soil_treatment_dietary_dose_ug_per_bee(
        application_rate_kg_ha=application_rate_kg_ha, log_kow=log_kow, koc_l_per_kg=koc_l_per_kg,
        life_stage=life_stage,
    )
    endpoint = _positive_decimal(toxicity_endpoint_ug_per_bee, name="toxicity_endpoint_ug_per_bee")
    return _rq_result(pathway="soil_treatment", route="diet", life_stage=life_stage, exposure=dose,
                       unit="ug a.i./bee/day", endpoint=endpoint, chronic=chronic)
