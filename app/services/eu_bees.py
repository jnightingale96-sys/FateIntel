"""EU Tier 1 bee risk screening (honey bees, spray applications).

Source: EFSA Guidance Document on the risk assessment of plant protection products on bees (Apis mellifera,
Bombus spp. and solitary bees), EFSA Journal 2013;11(7):3295, 266 pp. Fetched from an open mirror
(apiservices.biz/documents/articles-en/EFSA_risk_assesment_July_2013.pdf -- efsa.onlinelibrary.wiley.com, the
EFSA Journal's own host, is behind Cloudflare bot-detection that was not bypassed, per this project's rule
against defeating bot-detection) and read in full via PyMuPDF. Section 3.1.2 ("Risk assessment for applications
applied as sprays for honey bees"), pp. 15-17, is reproduced here exactly -- this is the generic Tier 1 screening
procedure every substance goes through, not a compound-specific worked example.

A REVISED version of this guidance was adopted in 2023 (EFSA Journal 2023;21(5):7989) -- not obtained this
session (also on efsa.onlinelibrary.wiley.com). Partial primary text was read from an open PMC mirror
(pmc.ncbi.nlm.nih.gov/articles/PMC10173852/), confirming the 2023 revision keeps the same PEQ/HQ/ETR shape
(PEQcontact = AR x EFcontact x BSF; PEQdietary built from shortcut/"SV"-style soil-and-plant-uptake terms) but
with different trigger values tied to newer specific protection goals (10% maximum colony-size reduction) --
those 2023 numbers were not confirmed and are NOT used here. This module implements the 2013 guidance's own
Tier 1 screen, clearly labelled as such; it is not automatically the current EU regulatory trigger set.

Scope boundary, stated plainly, matching the same discipline as eu_birds_mammals.py: only SPRAY applications to
honey bees are implemented (Section 3.1.2). Granular and seed-treatment application routes have their own,
different first-tier schemes in the guidance (sections not read this session) and are NOT implemented. Bumble
bee and solitary bee assessments use different trigger values elsewhere in the guidance and are NOT implemented
either -- this module is honey-bee-only. The "SV" (shortcut value) residue-per-application-rate constants used
in the oral/larval/HPG exposure ratios come from the guidance's own Appendix J, Table J3; only the four SV values
actually needed for this Tier 1 screening step are reproduced (given directly, inline, in Section 3.1.2's own
procedural text) -- the fuller Appendix J tables (refined, crop- and scenario-specific SV/RUD values) are not
reproduced, the same "large reference table, not shipped, reviewer supplies the refined figure" boundary already
used for the Annex B/Appendix L crop tables in eu_birds_mammals.py.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal


GUIDANCE_REFERENCE = "EFSA Journal 2013;11(7):3295 — Guidance Document on the risk assessment of plant protection products on bees, Section 3.1.2"

# Trigger values, Section 3.1.2, pp. 15-17.
HQ_CONTACT_TRIGGER_DOWNWARDS = Decimal("42")
HQ_CONTACT_TRIGGER_SIDEWARD_UPWARDS = Decimal("85")
ETR_ACUTE_ORAL_TRIGGER = Decimal("0.2")
ETR_CHRONIC_ORAL_TRIGGER = Decimal("0.03")
ETR_LARVAE_TRIGGER = Decimal("0.2")
ETR_HPG_TRIGGER = Decimal("1")

# Shortcut values (SV), Table J3 of Appendix J, as quoted inline in Section 3.1.2. Spray direction: "downwards"
# is a standard ground/boom application; "sideward_upwards" is an air-assisted/orchard-type sprayer (the
# guidance's own example: "sideward/upwards (SUW) spray applications (e.g. air assisted orchard sprayer)").
SprayDirection = Literal["downwards", "sideward_upwards"]
_SV_ADULT_ORAL_AND_HPG: dict[SprayDirection, Decimal] = {"downwards": Decimal("7.55"), "sideward_upwards": Decimal("10.6")}
_SV_LARVAE: dict[SprayDirection, Decimal] = {"downwards": Decimal("4.4"), "sideward_upwards": Decimal("6.1")}


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


def _spray_direction(value: str) -> SprayDirection:
    if value not in ("downwards", "sideward_upwards"):
        raise GuidanceInputError('spray_direction must be "downwards" or "sideward_upwards"')
    return value  # type: ignore[return-value]


def honey_bee_contact_hq(*, application_rate_g_ha: float, ld50_contact_ug_bee: float, spray_direction: SprayDirection) -> dict[str, object]:
    """HQcontact = AR / LD50contact.  AR in g a.s./ha, LD50contact in microgram a.s./bee.

    Trigger: HQcontact > 42 (downwards spray) or > 85 (sideward/upwards spray) -> not negligible, refine.
    """

    direction = _spray_direction(spray_direction)
    ar = _decimal(application_rate_g_ha, name="application_rate_g_ha")
    ld50 = _decimal(ld50_contact_ug_bee, name="ld50_contact_ug_bee")
    hq = ar / ld50
    trigger = HQ_CONTACT_TRIGGER_DOWNWARDS if direction == "downwards" else HQ_CONTACT_TRIGGER_SIDEWARD_UPWARDS
    return {
        "hq_contact": float(hq),
        "trigger": float(trigger),
        "spray_direction": direction,
        "negligible_risk": bool(hq <= trigger),
        "guidance_reference": GUIDANCE_REFERENCE,
    }


def _etr(*, application_rate_kg_ha: float, endpoint_ug_bee: float, sv_table: dict[SprayDirection, Decimal], spray_direction: SprayDirection, name: str) -> tuple[Decimal, Decimal]:
    direction = _spray_direction(spray_direction)
    ar = _decimal(application_rate_kg_ha, name="application_rate_kg_ha")
    endpoint = _decimal(endpoint_ug_bee, name=name)
    sv = sv_table[direction]
    return (ar * sv) / endpoint, sv


def honey_bee_acute_oral_etr(*, application_rate_kg_ha: float, ld50_oral_ug_bee: float, spray_direction: SprayDirection) -> dict[str, object]:
    """ETRacute adult oral = AR x SV / LD50oral.  AR in kg a.s./ha, LD50oral in microgram a.s./bee.

    SV (shortcut value) = 7.55 (downwards spray) or 10.6 (sideward/upwards spray). Trigger: ETR > 0.2.
    """

    etr, sv = _etr(application_rate_kg_ha=application_rate_kg_ha, endpoint_ug_bee=ld50_oral_ug_bee,
                    sv_table=_SV_ADULT_ORAL_AND_HPG, spray_direction=spray_direction, name="ld50_oral_ug_bee")
    return {
        "etr_acute_adult_oral": float(etr), "sv": float(sv), "trigger": float(ETR_ACUTE_ORAL_TRIGGER),
        "spray_direction": spray_direction, "negligible_risk": bool(etr <= ETR_ACUTE_ORAL_TRIGGER),
        "guidance_reference": GUIDANCE_REFERENCE,
    }


def honey_bee_chronic_oral_etr(*, application_rate_kg_ha: float, lc50_oral_ug_bee_per_day: float, spray_direction: SprayDirection) -> dict[str, object]:
    """ETRchronic adult oral = AR x SV / LC50oral.  LC50oral in microgram a.s./bee/day. Trigger: ETR > 0.03."""

    etr, sv = _etr(application_rate_kg_ha=application_rate_kg_ha, endpoint_ug_bee=lc50_oral_ug_bee_per_day,
                    sv_table=_SV_ADULT_ORAL_AND_HPG, spray_direction=spray_direction, name="lc50_oral_ug_bee_per_day")
    return {
        "etr_chronic_adult_oral": float(etr), "sv": float(sv), "trigger": float(ETR_CHRONIC_ORAL_TRIGGER),
        "spray_direction": spray_direction, "negligible_risk": bool(etr <= ETR_CHRONIC_ORAL_TRIGGER),
        "guidance_reference": GUIDANCE_REFERENCE,
    }


def honey_bee_larvae_etr(*, application_rate_kg_ha: float, noec_larvae_ug_per_developmental_period: float, spray_direction: SprayDirection) -> dict[str, object]:
    """ETRlarvae = AR x SV / NOEClarvae.  NOEClarvae in microgram a.s./larva per developmental period.

    SV = 4.4 (downwards spray) or 6.1 (sideward/upwards spray). Trigger: ETR > 0.2.
    """

    etr, sv = _etr(application_rate_kg_ha=application_rate_kg_ha, endpoint_ug_bee=noec_larvae_ug_per_developmental_period,
                    sv_table=_SV_LARVAE, spray_direction=spray_direction, name="noec_larvae_ug_per_developmental_period")
    return {
        "etr_larvae": float(etr), "sv": float(sv), "trigger": float(ETR_LARVAE_TRIGGER),
        "spray_direction": spray_direction, "negligible_risk": bool(etr <= ETR_LARVAE_TRIGGER),
        "guidance_reference": GUIDANCE_REFERENCE,
    }


def honey_bee_hpg_etr(*, application_rate_kg_ha: float, noec_hpg_ug_bee_per_day: float, spray_direction: SprayDirection) -> dict[str, object]:
    """ETRhpg = AR x SV / NOEChpg -- only relevant if the adult chronic toxicity study showed a hypopharyngeal-
    gland (HPG) development effect (Section 3.1.2.f); this function does not decide that applicability itself.
    NOEChpg in microgram a.s./bee/day. Trigger: ETR > 1.
    """

    etr, sv = _etr(application_rate_kg_ha=application_rate_kg_ha, endpoint_ug_bee=noec_hpg_ug_bee_per_day,
                    sv_table=_SV_ADULT_ORAL_AND_HPG, spray_direction=spray_direction, name="noec_hpg_ug_bee_per_day")
    return {
        "etr_hpg": float(etr), "sv": float(sv), "trigger": float(ETR_HPG_TRIGGER),
        "spray_direction": spray_direction, "negligible_risk": bool(etr <= ETR_HPG_TRIGGER),
        "guidance_reference": GUIDANCE_REFERENCE,
    }


def honey_bee_tier1_screen(
    *,
    application_rate_g_ha: float,
    spray_direction: SprayDirection,
    ld50_contact_ug_bee: float,
    ld50_oral_ug_bee: float,
    lc50_oral_ug_bee_per_day: float,
    noec_larvae_ug_per_developmental_period: float,
    noec_hpg_ug_bee_per_day: float | None = None,
) -> dict[str, object]:
    """Runs the full Section 3.1.2 screening step (2.a-2.f) in one call and reports every result plainly.

    ``application_rate_g_ha`` is the single application rate the guidance uses in both forms (g/ha for the
    contact HQ, kg/ha for every ETR -- both are computed from the one figure here, converting units internally
    so a caller supplies the rate once). ``noec_hpg_ug_bee_per_day`` is optional: the guidance only calls for the
    HPG check when the adult chronic study showed an effect (Section 3.1.2.f) -- pass it only when that applies;
    if omitted, ``hpg`` in the result is ``None`` rather than a fabricated pass.

    Never gates or hides a result: every one of the four (or five) ratios is returned, each with its own
    ``negligible_risk`` flag, so a reviewer sees every trigger outcome rather than only the first one breached.
    """

    ar_g_ha = _decimal(application_rate_g_ha, name="application_rate_g_ha")
    ar_kg_ha = ar_g_ha / Decimal("1000")

    contact = honey_bee_contact_hq(application_rate_g_ha=application_rate_g_ha, ld50_contact_ug_bee=ld50_contact_ug_bee, spray_direction=spray_direction)
    acute_oral = honey_bee_acute_oral_etr(application_rate_kg_ha=float(ar_kg_ha), ld50_oral_ug_bee=ld50_oral_ug_bee, spray_direction=spray_direction)
    chronic_oral = honey_bee_chronic_oral_etr(application_rate_kg_ha=float(ar_kg_ha), lc50_oral_ug_bee_per_day=lc50_oral_ug_bee_per_day, spray_direction=spray_direction)
    larvae = honey_bee_larvae_etr(application_rate_kg_ha=float(ar_kg_ha), noec_larvae_ug_per_developmental_period=noec_larvae_ug_per_developmental_period, spray_direction=spray_direction)
    hpg = None
    if noec_hpg_ug_bee_per_day is not None:
        hpg = honey_bee_hpg_etr(application_rate_kg_ha=float(ar_kg_ha), noec_hpg_ug_bee_per_day=noec_hpg_ug_bee_per_day, spray_direction=spray_direction)

    all_results = [contact, acute_oral, chronic_oral, larvae] + ([hpg] if hpg else [])
    negligible_overall = all(r["negligible_risk"] for r in all_results)

    return {
        "contact": contact,
        "acute_adult_oral": acute_oral,
        "chronic_adult_oral": chronic_oral,
        "larvae": larvae,
        "hpg": hpg,
        "negligible_risk_overall": negligible_overall,
        "guidance_reference": GUIDANCE_REFERENCE,
    }
