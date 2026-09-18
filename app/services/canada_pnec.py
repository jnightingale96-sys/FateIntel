"""Canada (ECCC/CEPA) assessment-factor-based PNEC derivation.

Source: Health Canada / Environment and Climate Change Canada, "Use of
assessment factors in ecological risk assessment for deriving predicted
no-effect concentrations" (Fact sheet series: Topics in risk assessment of
substances under the Canadian Environmental Protection Act, 1999), which
describes the method published in Okonski et al. (2020). Every table and
formula here is quoted directly from that fact sheet, verified against its
own worked example (CTV 15 mg/L, FES 10, FSV 5, FMOA 1 -> PNEC 0.3 mg/L).

Unlike the EU/AU assessment-factor tradition of picking one AF from a single
banded table based on how many trophic levels are covered, ECCC's method
(Okonski et al., 2020) derives the AF as the product of three independently
justified sub-factors:

  AF = FES (endpoint standardisation) x FSV (species variation) x FMOA (mode of action)
  PNEC = CTV / AF

This module computes FES, FSV and FMOA from the same yes/no questions and
lookup tables the fact sheet itself gives, and composes them into an AF a
reviewer can then pass straight to :func:`app.reach.pnec.derive_pnec` (this
module does not duplicate that function's unit handling or freshwater
scoping -- it only derives the Canadian assessment factor and states its
own rationale for the record).

Every selection here is still reviewer-made, not inferred: FSV is looked up
from a reviewer-stated species/category count, and FMOA is reviewer-selected
from the fact sheet's own four named categories -- this module performs no
mode-of-action classification of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


GUIDANCE_REFERENCE = (
    "Health Canada / ECCC fact sheet: Use of assessment factors in ecological risk assessment for "
    "deriving predicted no-effect concentrations (CEPA 1999), method of Okonski et al. (2020)"
)


class CanadaPnecInputError(ValueError):
    """Raised when an input falls outside the domain the fact sheet's tables define."""


def endpoint_standardization_factor(
    *,
    short_to_long_term_extrapolation_needed: bool,
    lethal_to_sublethal_extrapolation_needed: bool,
    median_to_no_effect_extrapolation_needed: bool,
) -> Decimal:
    """FES: 10 if all three extrapolations are needed, 1 if none, 5 otherwise.

    Directly reproduces the fact sheet's own three-row table (all yes -> 10;
    all no -> 1; any other mix of yes/no -> 5).
    """

    answers = [
        short_to_long_term_extrapolation_needed,
        lethal_to_sublethal_extrapolation_needed,
        median_to_no_effect_extrapolation_needed,
    ]
    if all(answers):
        return Decimal("10")
    if not any(answers):
        return Decimal("1")
    return Decimal("5")


_FSV_TABLE: dict[int, dict[str, Decimal | None]] = {
    1: {"1": Decimal("50"), "2-3": Decimal("20"), "4-6": Decimal("10"), "7+": Decimal("5")},
    2: {"1": None, "2-3": Decimal("10"), "4-6": Decimal("5"), "7+": Decimal("2")},
    3: {"1": None, "2-3": Decimal("5"), "4-6": Decimal("2"), "7+": Decimal("1")},
}


def _species_bin(species_count: int) -> str:
    if species_count <= 0:
        raise CanadaPnecInputError("species_count must be a positive integer")
    if species_count == 1:
        return "1"
    if species_count <= 3:
        return "2-3"
    if species_count <= 6:
        return "4-6"
    return "7+"


def species_variation_factor(*, organism_categories: int, species_count: int) -> Decimal:
    """FSV, from the fact sheet's organism-category x species-count table.

    ``organism_categories`` is the count of the three organism categories
    the fact sheet names (primary producers, invertebrates, vertebrates)
    actually represented in the dataset (1, 2 or 3). Some combinations are
    marked "x" (undefined) in the source table -- e.g. 3 categories can
    never be covered by a single species -- and raise here rather than
    silently picking a nearby value.
    """

    if organism_categories not in _FSV_TABLE:
        raise CanadaPnecInputError("organism_categories must be 1, 2 or 3")
    bin_key = _species_bin(species_count)
    value = _FSV_TABLE[organism_categories][bin_key]
    if value is None:
        raise CanadaPnecInputError(
            f"{organism_categories} organism categories cannot be represented by {species_count} "
            "species (undefined combination in the fact sheet's own table)"
        )
    return value


ModeOfActionCategory = Literal[
    "narcotic",
    "non_narcotic_expressed_in_dataset",
    "non_narcotic_not_fully_expressed",
    "narcotic_short_term_non_narcotic_long_term_not_expressed",
]

_FMOA_TABLE: dict[str, Decimal] = {
    "narcotic": Decimal("1"),
    "non_narcotic_expressed_in_dataset": Decimal("2"),
    "non_narcotic_not_fully_expressed": Decimal("5"),
    "narcotic_short_term_non_narcotic_long_term_not_expressed": Decimal("10"),
}


def mode_of_action_factor(category: ModeOfActionCategory) -> Decimal:
    """FMOA, reviewer-selected from the fact sheet's own four named categories."""

    try:
        return _FMOA_TABLE[category]
    except KeyError as exc:
        allowed = ", ".join(_FMOA_TABLE)
        raise CanadaPnecInputError(f"category must be one of: {allowed}") from exc


@dataclass(frozen=True)
class AssessmentFactorResult:
    fes: Decimal
    fsv: Decimal
    fmoa: Decimal
    assessment_factor: Decimal
    guidance_reference: str = GUIDANCE_REFERENCE

    def rationale(self) -> str:
        return (
            f"ECCC/CEPA assessment factor = FES({self.fes}) x FSV({self.fsv}) x FMOA({self.fmoa}) "
            f"= {self.assessment_factor}, per {GUIDANCE_REFERENCE}."
        )


def assessment_factor(*, fes: Decimal, fsv: Decimal, fmoa: Decimal) -> AssessmentFactorResult:
    """Combine the three sub-factors into the overall ECCC assessment factor."""

    total = fes * fsv * fmoa
    return AssessmentFactorResult(fes=fes, fsv=fsv, fmoa=fmoa, assessment_factor=total)


def pnec_from_critical_toxicity_value(
    *, critical_toxicity_value: float, factor: AssessmentFactorResult
) -> Decimal:
    """PNEC = CTV / (FES x FSV x FMOA). Same unit as the supplied CTV.

    This is a direct arithmetic convenience matching the fact sheet's own
    worked example; for a canonical-unit, freshwater-scoped record with
    provenance, prefer passing ``factor.assessment_factor`` and
    ``factor.rationale()`` into :func:`app.reach.pnec.derive_pnec` instead.
    """

    if critical_toxicity_value <= 0:
        raise CanadaPnecInputError("critical_toxicity_value must be a positive number")
    ctv = Decimal(str(critical_toxicity_value))
    return ctv / factor.assessment_factor
