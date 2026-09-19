"""Sediment and soil PNEC derivation via the equilibrium partitioning method (EPM).

Source: EU Technical Guidance Document (EC, 2003) equations, read in full this session
from ECETOC Technical Report No. 92, "Soil and Sediment Risk Assessment of Organic
Chemicals" (December 2004), Appendix A ("Risk Assessment for the Local Soil Compartment")
and Appendix B ("Risk Assessment for the Local Sediment Environment") -- these appendices
reproduce the TGD's own equations verbatim, including its worked-example simplifications,
which were used here to cross-check every constant below (not copied blind).

This closes the highest-leverage gap named in FateIntel's own coverage review: `app.reach.pnec`
only derives a freshwater PNEC from a reviewer-supplied assessment factor; sediment and soil
compartments had no PNEC path at all. The EPM does not add a new assessment-factor judgement --
it is a fixed partitioning conversion from an already-derived PNECwater, using the organic-carbon
partition coefficient (Koc) and the TGD's own default physical constants for suspended matter
and soil. Where a chemical has real sediment- or soil-toxicity data instead, ECETOC TR No. 92
Tables 2/3 give assessment factors for a direct (non-EPM) derivation from that data -- this
module does not implement that path; a reviewer with real sediment/soil toxicity data should use
`app.reach.pnec.derive_pnec` -style explicit-AF arithmetic directly, not this EPM conversion.

Important, explicitly NOT auto-applied here: the TGD multiplies the PEC/PNEC ratio for sediment
and soil by an extra factor of 10 when log Kow > 5, to account for possible additional exposure
via ingestion of sorbed material. ECETOC's own Task Force (TR No. 92, Sections 4.4.2/5.3.2)
concluded this factor is arbitrary, is applied to the wrong side of the ratio (their own
re-derivation from Di Toro et al 1991's theory puts the correct maximum at 2.5, not 10), and its
magnitude is not supported by the data reviewed. Given that documented controversy, this module
never silently applies it -- a reviewer who wants to apply the TGD's own convention (or ECETOC's
critique of it) does so explicitly via the optional `high_log_kow_factor` argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


GUIDANCE_REFERENCE = (
    "EU Technical Guidance Document (EC, 2003), equilibrium partitioning method, as reproduced "
    "in ECETOC Technical Report No. 92 (2004) Appendix A.2 (soil) and Appendix B.2 (sediment)"
)

# Sediment / suspended-matter defaults (ECETOC TR No. 92 Appendix B, Table 5 defaults).
FOC_SUSPENDED_MATTER_DEFAULT = Decimal("0.1")
FWATER_SUSPENDED_DEFAULT = Decimal("0.9")
FSOLID_SUSPENDED_DEFAULT = Decimal("0.1")
RHO_SOLID_DEFAULT = Decimal("2500")
RHO_SUSPENDED_WET_DEFAULT = Decimal("1150")
SEDIMENT_WET_TO_DRY_FACTOR = Decimal("2.6")

# Soil defaults (ECETOC TR No. 92 Appendix A, TGD defaults).
FOC_SOIL_DEFAULT = Decimal("0.02")
RHO_SOIL_DEFAULT = Decimal("1700")


class EquilibriumPartitioningInputError(ValueError):
    """Raised when an input to an EPM PNEC conversion is invalid."""


def _positive_decimal(value: float | Decimal, name: str) -> Decimal:
    dec = Decimal(str(value))
    if dec <= 0:
        raise EquilibriumPartitioningInputError(f"{name} must be a positive number")
    return dec


@dataclass(frozen=True)
class SedimentPnecResult:
    pnec_sediment_wet_mg_per_kg: Decimal
    pnec_sediment_dry_mg_per_kg: Decimal
    pnec_water_mg_per_l: Decimal
    koc_l_per_kg: Decimal
    ksusp_water: Decimal
    high_log_kow_factor_applied: Decimal
    guidance_reference: str = GUIDANCE_REFERENCE
    method: str = "equilibrium_partitioning"


def derive_pnec_sediment_from_water(
    *,
    pnec_water_mg_per_l: float,
    koc_l_per_kg: float,
    high_log_kow_factor: float | None = None,
) -> SedimentPnecResult:
    """PNECsediment from PNECwater via the TGD equilibrium partitioning method.

    Reproduces TGD eq 70 / ECETOC TR No. 92 Appendix B.2 exactly, using the TGD's own default
    suspended-matter constants (Fwatersusp=0.9, Fsolidsusp=0.1, RHOsolid=2500, RHOsusp=1150,
    Focsusp=0.1). Cross-checked against the source document's own worked simplification,
    PNECsediment = PNECwater x (0.783 + 0.0217 x Koc) -- this function computes the unrounded
    form of that same expression, not the rounded constants.

    Returns a PNEC on both the wet-sediment basis the TGD equation itself produces and, via the
    TGD's fixed 2.6 wet:dry conversion factor, the dry-sediment basis most monitoring data and
    sediment toxicity results are reported in.

    ``high_log_kow_factor``, if supplied, is applied as a straight multiplier to the result --
    this module does not choose or default one itself (see module docstring for why).
    """

    pnec_water = _positive_decimal(pnec_water_mg_per_l, "pnec_water_mg_per_l")
    koc = _positive_decimal(koc_l_per_kg, "koc_l_per_kg")

    kp_susp = FOC_SUSPENDED_MATTER_DEFAULT * koc
    ksusp_water = FWATER_SUSPENDED_DEFAULT + (
        FSOLID_SUSPENDED_DEFAULT * kp_susp * RHO_SOLID_DEFAULT / Decimal("1000")
    )
    pnec_sediment_wet = (ksusp_water * pnec_water * Decimal("1000")) / RHO_SUSPENDED_WET_DEFAULT

    factor = Decimal("1") if high_log_kow_factor is None else _positive_decimal(
        high_log_kow_factor, "high_log_kow_factor"
    )
    pnec_sediment_wet *= factor
    pnec_sediment_dry = pnec_sediment_wet * SEDIMENT_WET_TO_DRY_FACTOR

    return SedimentPnecResult(
        pnec_sediment_wet_mg_per_kg=pnec_sediment_wet,
        pnec_sediment_dry_mg_per_kg=pnec_sediment_dry,
        pnec_water_mg_per_l=pnec_water,
        koc_l_per_kg=koc,
        ksusp_water=ksusp_water,
        high_log_kow_factor_applied=factor,
    )


@dataclass(frozen=True)
class SoilPnecResult:
    pnec_soil_mg_per_kg: Decimal
    pnec_water_mg_per_l: Decimal
    koc_l_per_kg: Decimal
    ksoil_water: Decimal
    high_log_kow_factor_applied: Decimal
    guidance_reference: str = GUIDANCE_REFERENCE
    method: str = "equilibrium_partitioning"


def derive_pnec_soil_from_water(
    *,
    pnec_water_mg_per_l: float,
    koc_l_per_kg: float,
    high_log_kow_factor: float | None = None,
) -> SoilPnecResult:
    """PNECsoil from PNECwater via the TGD equilibrium partitioning method.

    Reproduces TGD eq 72 / ECETOC TR No. 92 Appendix A.2 exactly: PNECsoil =
    (Ksoil-water x PNECwater x 1000) / RHOsoil, with Ksoil-water = Focsoil x Koc, using the TGD's
    default soil constants (Focsoil=0.02, RHOsoil=1700). The source document's own algebraic
    simplification of these defaults, PNECsoil = Koc x PNECwater / 85, was used to verify this
    function's arithmetic and matches exactly.

    ``high_log_kow_factor`` behaves as in :func:`derive_pnec_sediment_from_water` -- never
    defaulted, only applied when a reviewer explicitly supplies it.
    """

    pnec_water = _positive_decimal(pnec_water_mg_per_l, "pnec_water_mg_per_l")
    koc = _positive_decimal(koc_l_per_kg, "koc_l_per_kg")

    ksoil_water = FOC_SOIL_DEFAULT * koc
    pnec_soil = (ksoil_water * pnec_water * Decimal("1000")) / RHO_SOIL_DEFAULT

    factor = Decimal("1") if high_log_kow_factor is None else _positive_decimal(
        high_log_kow_factor, "high_log_kow_factor"
    )
    pnec_soil *= factor

    return SoilPnecResult(
        pnec_soil_mg_per_kg=pnec_soil,
        pnec_water_mg_per_l=pnec_water,
        koc_l_per_kg=koc,
        ksoil_water=ksoil_water,
        high_log_kow_factor_applied=factor,
    )
