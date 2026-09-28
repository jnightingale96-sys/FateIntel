"""Japan CSCL ecological-risk assessment factor tiers, confirmed from real primary MoE documents.

Upgrades the "structure confirmed, current numeric criteria not verified" caveat on `JP_CSCL_PARTIAL`
(`app/services/registry.py`, `REGION_RESEARCH_JP_CN_KR_IN.md`) -- that finding was sourced to a 2012 NITE
conference slide deck describing the Hazard-Class x Exposure-Class *screening* stage, not the actual PNEC
assessment-factor numbers used once a substance reaches risk assessment. This module is sourced instead to two
real, current, English-language Ministry of the Environment publications in the "Profiles of the Initial
Environmental Risk Assessment of Chemicals" series (env.go.jp/en/chemi/chemicals/profile_erac/), each a per-
substance worked example showing the actual assessment factor MoE applied:

  - Carbamazepine (CAS 298-46-4), CSCL Reference No. 9-630, Vol. 21:
    <https://www.env.go.jp/content/000212115.pdf> (fetched and read 2026-09-27). Four reliable acute L(E)C50
    values across four species (green alga, crustacean, fish, fresh-water polyp) -> assessment factor 100.
    Three reliable chronic NOEC values across three trophic levels (alga, crustacean, fish) -> assessment
    factor 10, and that lower (chronic) PNEC was the one actually used.
  - 1,1,1,2-Tetrafluoroethane (CAS 811-97-2), CSCL Reference No. 2-3585, Vol. 4 (fetched 2026-09-27,
    <https://www.env.go.jp/content/900450513.pdf>): no PNEC could be set at all because no toxicity data
    applicable to initial assessment existed -- confirming the method never invents a PNEC from absent data,
    the same discipline this project applies to itself.

**What is confirmed**: exactly the two assessment-factor tiers documented above (100 for acute data spanning
several species/trophic levels; 10 for chronic data spanning several trophic levels), read directly from two
real worked examples. **What is NOT confirmed**: any tier for a single-species-only dataset (the EU TGD
convention this app already implements elsewhere uses 1000 for that case, but no primary Japanese example
showing that specific tier was found this session) -- this module deliberately offers no such tier rather than
assume EU practice applies. Two-species and mixed acute/chronic datasets, QSAR-only data and field-data
adjustments are likewise not covered.

**The final risk judgment is a genuine qualitative call MoE itself makes, not a mechanical PEC/PNEC>1 trigger**
-- both source documents above use a four-way judgment (○ no need for further work / ▲ requiring information
collection / ■ candidate for further work / X impossibility of risk characterization), and the Carbamazepine
example was judged ▲ despite a PEC/PNEC ratio of only 0.02-0.002, because a separate river-monitoring survey
found a locally higher value. This module therefore computes only the PNEC and reports the PEC/PNEC ratio for
the reviewer's own judgment -- it never assigns one of the four MoE judgment symbols itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


CARBAMAZEPINE_SOURCE = (
    "Ministry of the Environment, Japan, \"Profiles of the Initial Environmental Risk Assessment of Chemicals\", "
    "Vol. 21, Carbamazepine (CAS 298-46-4, CSCL Reference No. 9-630) -- "
    "https://www.env.go.jp/content/000212115.pdf"
)
TETRAFLUOROETHANE_SOURCE = (
    "Ministry of the Environment, Japan, \"Profiles of the Initial Environmental Risk Assessment of Chemicals\", "
    "Vol. 4, 1,1,1,2-Tetrafluoroethane (CAS 811-97-2, CSCL Reference No. 2-3585) -- "
    "https://www.env.go.jp/content/900450513.pdf"
)
GUIDANCE_REFERENCE = (
    f"Assessment-factor tiers confirmed from two real MoE worked examples: {CARBAMAZEPINE_SOURCE}; "
    f"{TETRAFLUOROETHANE_SOURCE}. Not the CSCL statute or a MoE methodology manual itself -- this module reports "
    "what two real risk-assessment profiles actually did, not a general rule stated in guidance text."
)

# Confirmed via the Carbamazepine profile: 4 species (alga, crustacean, fish, hydra), acute L(E)C50 -> AF 100.
AF_ACUTE_MULTI_SPECIES = Decimal("100")
# Confirmed via the Carbamazepine profile: 3 trophic levels (alga, crustacean, fish), chronic NOEC -> AF 10.
AF_CHRONIC_MULTI_SPECIES = Decimal("10")

DataType = Literal["acute_multi_species", "chronic_multi_species"]

RISK_JUDGMENT_SYMBOLS = {
    "no_need_for_further_work": "○ (no need for further work)",
    "requiring_information_collection": "▲ (requiring information collection)",
    "candidate_for_further_work": "■ (candidate for further work)",
    "impossibility_of_risk_characterization": "× (impossibility of risk characterization)",
}


class JapanCsclInputError(ValueError):
    """Raised when an input falls outside what this module's two confirmed tiers cover."""


@dataclass(frozen=True)
class JapanCsclPnecResult:
    pnec_ug_per_l: Decimal
    lowest_toxicity_value_ug_per_l: Decimal
    data_type: DataType
    assessment_factor: Decimal
    guidance_reference: str = GUIDANCE_REFERENCE
    method: str = "japan_cscl_assessment_factor"


def derive_pnec_japan_cscl(
    *,
    lowest_toxicity_value_ug_per_l: float,
    data_type: DataType,
) -> JapanCsclPnecResult:
    """PNEC = lowest reliable toxicity value / the confirmed Japan CSCL assessment factor for that data type.

    ``data_type`` must be one of the two tiers this module actually confirmed from a real worked example --
    see the module docstring for exactly what was and was not verified. This function does not judge risk (no
    PEC is taken and no PEC/PNEC ratio is computed): pass the result to the reviewer's own PEC/PNEC comparison,
    the same hand-off every other PNEC-derivation module in this app uses.
    """

    value = Decimal(str(lowest_toxicity_value_ug_per_l))
    if value <= 0:
        raise JapanCsclInputError("lowest_toxicity_value_ug_per_l must be a positive number")
    if data_type == "acute_multi_species":
        af = AF_ACUTE_MULTI_SPECIES
    elif data_type == "chronic_multi_species":
        af = AF_CHRONIC_MULTI_SPECIES
    else:
        raise JapanCsclInputError(
            "data_type must be 'acute_multi_species' or 'chronic_multi_species' -- these are the only two tiers "
            "confirmed from a real MoE worked example; a single-species or mixed dataset is not covered"
        )
    return JapanCsclPnecResult(
        pnec_ug_per_l=value / af,
        lowest_toxicity_value_ug_per_l=value,
        data_type=data_type,
        assessment_factor=af,
    )
