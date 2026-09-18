"""APVMA (Australian Pesticides and Veterinary Medicines Authority) pesticide
environmental risk-quotient triggers.

Source: APVMA's own published risk-assessment guidance, confirmed this
session via APVMA's Risk Assessment Manual, Environment and its Appendix A
(Terrestrial vertebrates), plus APVMA's own aquatic exposure/runoff
methodology publications. APVMA runs no proprietary PEC/PNEC-derivation
method of its own for most receptor groups -- it explicitly adapts existing
tools instead:

- **Aquatic**: RQ = PEC / toxicity value, compared against a fixed trigger
  of 0.1 (acute) or 1.0 (chronic) -- RQ at or above the trigger is deemed
  unacceptable. Confirmed directly from APVMA's own risk-analysis-process
  guidance, not assumed.
- **Terrestrial vertebrates (birds/mammals)**: APVMA's own Appendix A
  states its dietary TER methodology is "in line with current EFSA (2009)
  guidance" -- and the same trigger values were confirmed: TER >= 10 for
  acute (screening step), TER >= 5 for the reproductive/chronic endpoint.
  These are the exact thresholds already implemented in
  ``app/services/eu_birds_mammals.py`` (``ACUTE_TER_TRIGGER`` = 10,
  ``REPRODUCTIVE_TER_TRIGGER`` = 5) -- APVMA pesticide assessments should
  use that module directly rather than a duplicate reimplementation here;
  duplicating a formula that is already correct would only add a second
  place for the two to silently drift apart.

Scope boundary, stated plainly. APVMA's guidance also covers spray drift
(AgDRIFT-derived curves with APVMA's own droplet-size percentile
modifications), runoff (a REXTOX sub-model adaptation), bees, soil
organisms and non-target plants -- none of those are reproduced here. Each
would need its own AU-specific default-parameter table verified against
APVMA's own publications the way the aquatic trigger and the birds/mammals
trigger reuse were, not assumed from the pattern of the two pieces that
have been confirmed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


GUIDANCE_REFERENCE = "APVMA Risk Assessment Manual, Environment (risk-analysis-process guidance, confirmed live)"

AQUATIC_RQ_TRIGGER_ACUTE = Decimal("0.1")
AQUATIC_RQ_TRIGGER_CHRONIC = Decimal("1.0")


class ApvmaInputError(ValueError):
    """Raised when an input to an APVMA risk-quotient calculation is invalid."""


def aquatic_risk_quotient(*, predicted_environmental_concentration: float, toxicity_value: float) -> Decimal:
    """RQ = PEC / toxicity value, APVMA's own aquatic risk-quotient formula."""

    if predicted_environmental_concentration <= 0:
        raise ApvmaInputError("predicted_environmental_concentration must be a positive number")
    if toxicity_value <= 0:
        raise ApvmaInputError("toxicity_value must be a positive number")
    return Decimal(str(predicted_environmental_concentration)) / Decimal(str(toxicity_value))


@dataclass(frozen=True)
class AquaticRiskResult:
    rq: Decimal
    trigger: Decimal
    unacceptable: bool
    exposure_type: str
    guidance_reference: str = GUIDANCE_REFERENCE


def characterise_aquatic_risk(
    *,
    predicted_environmental_concentration: float,
    toxicity_value: float,
    exposure_type: str,
) -> AquaticRiskResult:
    """Compare an aquatic RQ against APVMA's fixed acute/chronic trigger.

    ``exposure_type`` must be ``"acute"`` or ``"chronic"`` -- APVMA uses
    0.1 for acute toxicity data (LC50/EC50) and 1.0 for chronic (NOEC/NOEL/
    NOER), confirmed from APVMA's own published guidance, not inferred.
    """

    if exposure_type not in {"acute", "chronic"}:
        raise ApvmaInputError('exposure_type must be "acute" or "chronic"')
    trigger = AQUATIC_RQ_TRIGGER_ACUTE if exposure_type == "acute" else AQUATIC_RQ_TRIGGER_CHRONIC
    rq = aquatic_risk_quotient(
        predicted_environmental_concentration=predicted_environmental_concentration,
        toxicity_value=toxicity_value,
    )
    return AquaticRiskResult(rq=rq, trigger=trigger, unacceptable=rq >= trigger, exposure_type=exposure_type)
