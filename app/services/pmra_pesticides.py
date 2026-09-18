"""PMRA (Pest Management Regulatory Agency, Health Canada) pesticide
environmental risk-quotient characterisation.

Source, verified live this session: PMRA Guidance Document, "A Framework for
Risk Assessment and Risk Management of Pest Control Products" (Health
Canada, 12 April 2024), Section 6.1.2 "Assessing risks to the environment"
(https://www.canada.ca/.../risk-management-pest-control-products.html, read
in full in-browser, not summarised secondhand). Quoted directly from that
section:

    "Risks may be quantified using a risk quotient approach. A risk quotient
    (RQ) is calculated by dividing the exposure estimate by an appropriate
    toxicity value (RQ = exposure/toxicity). The RQ is then compared to the
    level of concern (LOC), which is set at one for the majority of
    organisms, with a few validated exceptions."

This is a genuinely different convention from APVMA (au_apvma.py: fixed
0.1/1.0 aquatic triggers) and from EPA's own tiered 0.5/0.2/0.1/0.05 LOC
ladder -- PMRA's own framework document states a single default LOC of 1
for most receptor groups, with named exceptions validated case by case.

One such exception is confirmed and reproduced here: honey bees. PMRA is a
named co-author agency (with US EPA and California DPR) of "Guidance for
Assessing Pesticide Risks to Bees" (June 19, 2014) -- read in full this
session via the saved PDF, not a secondhand summary -- which states in
Section 4.1.2:

    "RQ values are then compared to Levels of Concerns (LOCs). The LOCs for
    acute and chronic exposure are 0.4 and 1.0, respectively."

and Section 3.2.3 ("PMRA Toxicity Testing Requirements for Bees") confirms
PMRA applies this same tiered RQ/LOC process, not merely defers to EPA's.
This is a tri-agency framework, not an EPA framework PMRA happens to also
use -- both agencies co-developed it (acknowledgement page names PMRA
scientists Connie Hart and Wayne Hou as contributors).

Scope boundary, stated plainly: the general LOC=1 default applies to most
receptor groups (aquatic organisms, birds, mammals, terrestrial plants,
sediment/soil organisms) per the framework document, but the *specific
validated exceptions* beyond bees (e.g. any endangered-species or
restricted-use LOC banding, mirroring the terminology PMRA re-evaluation
decisions use) were not found with citable numeric values this session --
this module does not guess at them. A reviewer who has a citable PMRA
document naming a different LOC for a specific receptor group should pass
it directly via ``custom_loc`` rather than have this module invent one.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


GUIDANCE_REFERENCE = (
    "PMRA Guidance Document, A Framework for Risk Assessment and Risk Management of Pest Control "
    "Products (Health Canada, 12 April 2024), Section 6.1.2"
)

BEE_GUIDANCE_REFERENCE = (
    "Guidance for Assessing Pesticide Risks to Bees (US EPA, Health Canada PMRA, California DPR, "
    "19 June 2014), Section 4.1.2"
)

DEFAULT_LOC = Decimal("1")
BEE_LOC_ACUTE = Decimal("0.4")
BEE_LOC_CHRONIC = Decimal("1.0")

ExposureType = Literal["acute", "chronic"]


class PmraInputError(ValueError):
    """Raised when an input to a PMRA risk-quotient calculation is invalid."""


def risk_quotient(*, exposure_estimate: float, toxicity_value: float) -> Decimal:
    """RQ = exposure / toxicity, PMRA's own general risk-quotient formula."""

    if exposure_estimate <= 0:
        raise PmraInputError("exposure_estimate must be a positive number")
    if toxicity_value <= 0:
        raise PmraInputError("toxicity_value must be a positive number")
    return Decimal(str(exposure_estimate)) / Decimal(str(toxicity_value))


@dataclass(frozen=True)
class PmraRiskResult:
    rq: Decimal
    loc: Decimal
    exceeds_loc: bool
    receptor_group: str
    guidance_reference: str


def characterise_general_risk(
    *,
    exposure_estimate: float,
    toxicity_value: float,
    receptor_group: str,
    custom_loc: float | None = None,
) -> PmraRiskResult:
    """Compare a PMRA RQ against the default LOC of 1, or a reviewer-supplied exception.

    ``custom_loc`` must be a citable, PMRA-validated exception for the named
    ``receptor_group`` -- this module does not infer or look one up itself
    beyond the bee exception in :func:`characterise_bee_risk`.
    """

    rq = risk_quotient(exposure_estimate=exposure_estimate, toxicity_value=toxicity_value)
    loc = DEFAULT_LOC if custom_loc is None else Decimal(str(custom_loc))
    if loc <= 0:
        raise PmraInputError("custom_loc must be a positive number")
    return PmraRiskResult(
        rq=rq,
        loc=loc,
        exceeds_loc=rq >= loc,
        receptor_group=receptor_group,
        guidance_reference=GUIDANCE_REFERENCE,
    )


def characterise_bee_risk(
    *, exposure_estimate: float, toxicity_value: float, exposure_type: ExposureType
) -> PmraRiskResult:
    """Compare a bee RQ against PMRA's confirmed tri-agency LOC (0.4 acute / 1.0 chronic).

    ``exposure_estimate`` and ``toxicity_value`` must already be on the same
    basis (e.g. EEC vs. LD50 for acute contact/oral, or EEC vs. NOAEC for
    chronic) -- this module performs no Bee-REX-style exposure modelling of
    its own; a reviewer supplies both sides of the ratio directly, matching
    the reviewer-supplied-not-inferred convention this app's PNEC/RQ helpers
    all follow.
    """

    if exposure_type not in {"acute", "chronic"}:
        raise PmraInputError('exposure_type must be "acute" or "chronic"')
    rq = risk_quotient(exposure_estimate=exposure_estimate, toxicity_value=toxicity_value)
    loc = BEE_LOC_ACUTE if exposure_type == "acute" else BEE_LOC_CHRONIC
    return PmraRiskResult(
        rq=rq,
        loc=loc,
        exceeds_loc=rq >= loc,
        receptor_group="bees",
        guidance_reference=BEE_GUIDANCE_REFERENCE,
    )
