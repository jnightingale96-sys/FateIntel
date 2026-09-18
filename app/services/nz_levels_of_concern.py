"""New Zealand EPA (HSNO Act) Level-of-Concern risk characterisation.

Source: "Risk Assessment Methodology for Hazardous Substances" (NZ EPA Te
Mana Rauhi Taiao, December 2022, Version 1.1) -- Table 9 "Levels of concern"
and Table 10 "Indicative levels of risk from level of concern". Every value
here is quoted directly from that document, read in full this session.

NZ's approach is structurally different from the EU/Australia/Canada
tradition of deriving a PNEC from a toxicity value and an assessment
factor. Instead NZ EPA compares a risk quotient (RQ = PEC / toxicity
value) directly against a fixed, receptor- and exposure-type-specific
Level of Concern (LOC) -- there is no intermediate PNEC, and critically the
LOC values are NOT normalised to a universal "RQ > 1 is of concern"
convention the way EU/AU/CA PEC/PNEC ratios are. The document says so
explicitly: "In general, we use these values directly ... rather than
normalise them to where an RQ > 1 is of concern." Some LOC values are far
below 1 (e.g. 0.05 for acute risk to threatened aquatic species) and one is
above 1 (2, for terrestrial invertebrates) -- reproduced here exactly as
tabulated, not adjusted toward a round number.

A second, distinctive feature of this document (Table 10): once the RQ
exceeds its LOC, the *ratio* RQ/LOC is itself used to indicate the level of
risk (negligible / low / medium / high), a graded scale the EU/AU/CA
tradition does not have in the same form.

Scope boundary, stated plainly. NZ EPA's own document is a patchwork:
it names, and NZ-specific-parameterises, a long list of already-official
models for the exposure (PEC) side -- GENEEC2, AgDRIFT, AgDISP, REXTOX,
Sci-Grow, the EFSA 2009 bird model (NZ EPA's own errata confirm they have
since built their own replacement bird-risk tool, not yet folded into this
document), US EPA BeeRex, ESCORT2, BBA spray-drift curves, ECHA sediment
guidance. None of those NZ-parameterised exposure models are implemented
here -- this module is the risk-characterisation (RQ-vs-LOC) layer only,
exactly like app/reach/pnec.py is the PNEC layer without embedding an
exposure model. A reviewer supplies the PEC and the toxicity value; this
module does the LOC lookup and RQ/risk-level classification, nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


GUIDANCE_REFERENCE = (
    "NZ EPA Te Mana Rauhi Taiao, Risk Assessment Methodology for Hazardous Substances "
    "(December 2022, Version 1.1), Table 9 (Levels of concern) and Table 10 "
    "(Indicative levels of risk from level of concern)"
)

RiskLevel = Literal["negligible", "low", "medium", "high"]

ReceptorExposure = Literal[
    "human_health",
    "aquatic_acute",
    "aquatic_chronic",
    "sediment_organisms",
    "soil_organisms_acute",
    "soil_organisms_chronic",
    "terrestrial_vertebrates_acute",
    "terrestrial_vertebrates_chronic",
    "bees_acute",
    "bees_chronic",
    "terrestrial_invertebrates",
    "non_target_plants_ec25",
    "non_target_plants_ec50",
    "non_target_plants_threatened",
]


class NzLocInputError(ValueError):
    """Raised when a receptor/exposure or threatened-species combination is undefined."""


@dataclass(frozen=True)
class _LocEntry:
    normal: Decimal | None  # None means Table 9 gives no "normal species" value for this row
    threatened: Decimal | None  # None means "not applicable" per Table 9


# Table 9, reproduced exactly. "aquatic" excludes algae for the threatened-species column.
_LOC_TABLE: dict[ReceptorExposure, _LocEntry] = {
    "human_health": _LocEntry(normal=Decimal("1"), threatened=None),
    "aquatic_acute": _LocEntry(normal=Decimal("0.1"), threatened=Decimal("0.05")),
    "aquatic_chronic": _LocEntry(normal=Decimal("1"), threatened=Decimal("0.1")),
    "sediment_organisms": _LocEntry(normal=Decimal("1"), threatened=None),
    "soil_organisms_acute": _LocEntry(normal=Decimal("0.1"), threatened=Decimal("0.01")),
    "soil_organisms_chronic": _LocEntry(normal=Decimal("0.2"), threatened=Decimal("0.02")),
    "terrestrial_vertebrates_acute": _LocEntry(normal=Decimal("0.1"), threatened=Decimal("0.05")),
    "terrestrial_vertebrates_chronic": _LocEntry(normal=Decimal("0.2"), threatened=Decimal("0.1")),
    "bees_acute": _LocEntry(normal=Decimal("0.4"), threatened=None),
    "bees_chronic": _LocEntry(normal=Decimal("1"), threatened=None),
    "terrestrial_invertebrates": _LocEntry(normal=Decimal("2"), threatened=None),
    "non_target_plants_ec25": _LocEntry(normal=Decimal("1"), threatened=None),
    "non_target_plants_ec50": _LocEntry(normal=Decimal("0.2"), threatened=None),
    # "Acute (based on NOEC or EC50/10)" in Table 9 has no "normal" entry ("-") and only
    # applies to threatened species, at LOC 1 -- reproduced as its own key rather than
    # forcing it into the two-column shape the other rows use. The value lives in the
    # "threatened" slot since that is the only column Table 9 actually gives for this row.
    "non_target_plants_threatened": _LocEntry(normal=None, threatened=Decimal("1")),
}

_NON_TARGET_PLANT_KEYS = {"non_target_plants_ec25", "non_target_plants_ec50"}


def level_of_concern(receptor_exposure: ReceptorExposure, *, threatened_species: bool = False) -> Decimal:
    """Look up the LOC trigger value for a receptor/exposure type from Table 9.

    ``threatened_species`` selects the more protective column where Table 9
    provides one. Raises if the combination is marked "N/A" in the source
    table (e.g. bees have no threatened-species column) rather than
    silently falling back to the normal-species value.
    """

    if receptor_exposure not in _LOC_TABLE:
        raise NzLocInputError(f"Unknown receptor_exposure: {receptor_exposure}")
    if receptor_exposure == "non_target_plants_threatened" and not threatened_species:
        raise NzLocInputError(
            "non_target_plants_threatened only applies when threatened_species=True "
            "(Table 9 gives no 'normal species' LOC for the NOEC/EC50-over-10 basis)"
        )
    entry = _LOC_TABLE[receptor_exposure]
    if not threatened_species:
        return entry.normal
    if entry.threatened is None:
        raise NzLocInputError(
            f"Table 9 gives no threatened-species LOC for {receptor_exposure!r} (marked N/A)"
        )
    return entry.threatened


def risk_quotient(*, predicted_environmental_concentration: float, toxicity_value: float) -> Decimal:
    """RQ = PEC / toxicity value (Table 8's RQ_environment = PEC / PNEC, generalised).

    ``toxicity_value`` may be a raw endpoint (e.g. LC50, NOEC) or an
    already-derived PNEC -- NZ EPA's own guidance notes some of the named
    exposure models already build an assessment factor into their output,
    in which case the step is not repeated (see the module docstring).
    """

    if predicted_environmental_concentration <= 0:
        raise NzLocInputError("predicted_environmental_concentration must be a positive number")
    if toxicity_value <= 0:
        raise NzLocInputError("toxicity_value must be a positive number")
    return Decimal(str(predicted_environmental_concentration)) / Decimal(str(toxicity_value))


def risk_level(rq: Decimal, loc: Decimal) -> RiskLevel:
    """Table 10: negligible < 1xLOC <= low < 10xLOC <= medium < 100xLOC <= high."""

    ratio = rq / loc
    if ratio < 1:
        return "negligible"
    if ratio < 10:
        return "low"
    if ratio < 100:
        return "medium"
    return "high"


@dataclass(frozen=True)
class LevelOfConcernResult:
    receptor_exposure: ReceptorExposure
    threatened_species: bool
    rq: Decimal
    loc: Decimal
    risk_level: RiskLevel
    guidance_reference: str = GUIDANCE_REFERENCE


def characterise_risk(
    *,
    receptor_exposure: ReceptorExposure,
    predicted_environmental_concentration: float,
    toxicity_value: float,
    threatened_species: bool = False,
) -> LevelOfConcernResult:
    """Full NZ EPA RQ-vs-LOC characterisation for one receptor/exposure pathway."""

    rq = risk_quotient(
        predicted_environmental_concentration=predicted_environmental_concentration,
        toxicity_value=toxicity_value,
    )
    loc = level_of_concern(receptor_exposure, threatened_species=threatened_species)
    return LevelOfConcernResult(
        receptor_exposure=receptor_exposure,
        threatened_species=threatened_species,
        rq=rq,
        loc=loc,
        risk_level=risk_level(rq, loc),
    )
