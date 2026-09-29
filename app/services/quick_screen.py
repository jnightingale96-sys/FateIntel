"""Quick risk screen for any chemical -- one orchestrated call across identity, real ecotoxicity data and the
existing exposure/PEC engine, for a chemical that has no FateIntel project of its own yet.

This is a genuinely new capability, not a repackaging: every other risk-derivation path in this app (the
guided assessment flow, `app.reach.pnec.derive_pnec`, the gold-standard validation cases built this session)
requires a human reviewer to read real evidence and choose an assessment factor before a PNEC exists. Nothing
in this app previously took "a chemical name" straight through to a risk quotient with no reviewer step at all.

**This module does exactly that, and is explicit about the trade-off.** The PNEC and PEC it produces are
computed, not reviewed -- every result is stamped `"reviewed": false` and `"screening_estimate": true`, and
the API route returns HTTP 200 with that stamp rather than silently looking like a reviewed conclusion. This
mirrors how a BIOWIN/PEPPER "MODEL ESTIMATE" is already labelled elsewhere in this app (`needs_professional_review:
true`) -- a screening number that says plainly it is one, not a number dressed up as more than it is.

**Hazard side**: `app/services/evidence_sources.py`'s `epa_ecotox` source (the local US EPA ECOTOX Knowledgebase
bulk import) is used because it is the one live-searchable source in this app that reliably returns real,
structured, numeric aquatic ecotoxicity values (measured NOEC/EC10/EC50/LC50, species, matrix) for an arbitrary
chemical -- confirmed this session: PubChem and Europe PMC's own live searches return identity/literature-citation
data for most compounds, not extracted numeric ecotox values, for the endpoint codes this module needs. The
assessment-factor band applied is the SAME EU TGD convention used by every reviewer-facing PNEC tool in this
app (`app.reach.pnec`, `equilibrium_partitioning.py`, `japan_cscl.py`): AF 10 for chronic NOEC/EC10 data from
three or more distinct species, AF 100 for one or two chronic values, AF 1000 when only acute EC50/LC50 data
exists. Unlike those reviewer-facing tools, this module selects the AF itself rather than asking a reviewer to
state a rationale -- that is the one discipline this module deliberately trades away, and the trade is named,
not hidden.

**Exposure side**: reuses `app.services.emission.run_pharmaceutical_emission` directly (the same real,
validated pipeline exercised in the gold-standard cases) -- it is general enough to run a plain "how much of
this chemical goes to a wastewater catchment" scenario for a non-pharmaceutical substance via its
`refined_annual_use`/`direct_daily_use` modes, not just the EMA-specific pharmaceutical modes. This module
never invents a release quantity: the caller supplies a real annual or daily mass, and the standard EU
TGD/EMA-convention reference-catchment defaults (10,000 inhabitants, 200 L/inhabitant/day, 10x dilution -- the
same defaults already verified against the primary EMA guideline this session) apply unless overridden.

**What this module does NOT do**: derive a soil/sediment PEC or DT50-based fate (water-compartment risk only,
for now); predict a PNEC when no measured ecotoxicity data exists anywhere (reports the gap, never invents a
QSAR-predicted toxicity value -- no such predictor exists in this app); resolve chemical identity itself (the
caller/route does that with the existing `app.services.identity` functions, so this module only ever deals
with an already-confirmed name/CAS/SMILES).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from .emission import run_pharmaceutical_emission
from .evidence_sources import search_sources

CHRONIC_PROPERTY_CODES = {"ECOTOX.AQUATIC.NOEC", "ECOTOX.AQUATIC.EC10"}
ACUTE_PROPERTY_CODES = {"ECOTOX.AQUATIC.EC50", "ECOTOX.AQUATIC.LC50"}

AF_THREE_OR_MORE_CHRONIC_SPECIES = Decimal("10")
AF_ONE_OR_TWO_CHRONIC_VALUES = Decimal("100")
AF_ACUTE_ONLY = Decimal("1000")
CHRONIC_SPECIES_FOR_LOWEST_AF = 3

# Same reference-catchment defaults as EMA's own Phase I screen (Guideline on the Environmental Risk
# Assessment of Medicinal Products for Human Use, Revision 1, effective 1 Sept 2024) and the EU TGD's own
# standard STP scenario -- not invented for this module, reused because they are the established convention.
DEFAULT_STP_CAPACITY_INHABITANTS = 10_000
DEFAULT_WASTEWATER_L_PERSON_DAY = 200.0
DEFAULT_DILUTION_FACTOR = 10.0

_SPECIES_RE = re.compile(r"species:\s*([^|]+?)\s*(?:\||$)")


class QuickScreenInputError(ValueError):
    """Raised when a required input is missing or out of range."""


@dataclass(frozen=True)
class ScreeningPnecResult:
    pnec_ug_l: Decimal | None
    basis: str
    assessment_factor: Decimal | None
    critical_value_ug_l: Decimal | None
    critical_endpoint: str | None
    species_considered: list[str] = field(default_factory=list)
    candidates_used: int = 0
    data_gap: str | None = None


def _species_from_candidate(candidate: dict[str, Any]) -> str | None:
    match = _SPECIES_RE.search(candidate.get("snippet") or "")
    return match.group(1).strip() if match else None


def _to_ug_l(value: float, unit: str) -> Decimal | None:
    factors = {"ug/l": Decimal("1"), "µg/l": Decimal("1"), "mg/l": Decimal("1000"), "ng/l": Decimal("0.001")}
    factor = factors.get(unit.strip().lower())
    if factor is None:
        return None
    return Decimal(str(value)) * factor


def derive_screening_pnec(candidates: list[dict[str, Any]]) -> ScreeningPnecResult:
    """Auto-selects a screening PNEC from real ECOTOX.AQUATIC.* evidence candidates.

    Never invents a value: if no aquatic ecotoxicity candidate was found at all, returns a result with
    ``pnec_ug_l=None`` and an explicit ``data_gap`` message instead of a number.
    """

    chronic: list[tuple[Decimal, dict[str, Any], str | None]] = []
    acute: list[tuple[Decimal, dict[str, Any], str | None]] = []
    for candidate in candidates:
        code = candidate.get("property_code")
        if code not in CHRONIC_PROPERTY_CODES and code not in ACUTE_PROPERTY_CODES:
            continue
        ug_l = _to_ug_l(candidate.get("value"), candidate.get("unit") or "")
        if ug_l is None or ug_l <= 0:
            continue
        species = _species_from_candidate(candidate)
        bucket = chronic if code in CHRONIC_PROPERTY_CODES else acute
        bucket.append((ug_l, candidate, species))

    if not chronic and not acute:
        return ScreeningPnecResult(
            pnec_ug_l=None, basis="no_aquatic_ecotoxicity_data_found", assessment_factor=None,
            critical_value_ug_l=None, critical_endpoint=None,
            data_gap="No aquatic ecotoxicity data (NOEC, EC10, EC50 or LC50) was found for this substance in "
                     "the searched sources (EPA ECOTOX Knowledgebase). A screening PNEC cannot be derived "
                     "without real toxicity data -- this module does not predict one.",
        )

    if chronic:
        distinct_species = {species for _, _, species in chronic if species}
        af = AF_THREE_OR_MORE_CHRONIC_SPECIES if len(distinct_species) >= CHRONIC_SPECIES_FOR_LOWEST_AF else AF_ONE_OR_TWO_CHRONIC_VALUES
        value, candidate, species = min(chronic, key=lambda row: row[0])
        basis = (
            f"chronic NOEC/EC10 data from {len(distinct_species)} distinct species "
            f"(EU TGD convention: AF={af} for {'>=3' if af == AF_THREE_OR_MORE_CHRONIC_SPECIES else '1-2'} species)"
        )
        species_list = sorted(s for s in distinct_species) or ([species] if species else [])
    else:
        af = AF_ACUTE_ONLY
        value, candidate, species = min(acute, key=lambda row: row[0])
        basis = "acute EC50/LC50 data only, no chronic data found (EU TGD convention: AF=1000)"
        species_list = [species] if species else []

    return ScreeningPnecResult(
        pnec_ug_l=value / af,
        basis=basis,
        assessment_factor=af,
        critical_value_ug_l=value,
        critical_endpoint=f"{candidate.get('endpoint_label')} ({candidate.get('source_record_id')})",
        species_considered=species_list,
        candidates_used=len(chronic) + len(acute),
    )


def screen_chemical_risk(
    *,
    chemical_name: str,
    cas_number: str | None,
    smiles: str | None,
    release_kg_year: float | None,
    scenario: Literal["generic_wwtp", "ema_phase_i_pharma"] = "generic_wwtp",
    maximum_daily_dose_mg: float | None = None,
    market_penetration_fraction: float = 0.01,
    population: int = DEFAULT_STP_CAPACITY_INHABITANTS,
    wastewater_l_person_day: float = DEFAULT_WASTEWATER_L_PERSON_DAY,
    dilution_factor: float = DEFAULT_DILUTION_FACTOR,
    parent_molecular_weight_g_mol: float = 100.0,
) -> dict[str, Any]:
    """Orchestrates a Tier-1-style screening risk quotient for any chemical, from real (not predicted)
    ecotoxicity data and a caller-supplied release quantity. Returns a dict, never a bare number, and always
    carries ``screening_estimate: True`` -- see the module docstring for exactly what that means and does not
    mean.
    """

    if scenario == "generic_wwtp" and (release_kg_year is None or release_kg_year <= 0):
        raise QuickScreenInputError("release_kg_year must be a positive number for the generic_wwtp scenario")
    if scenario == "ema_phase_i_pharma" and not maximum_daily_dose_mg:
        raise QuickScreenInputError("maximum_daily_dose_mg is required for the ema_phase_i_pharma scenario")

    hazard = search_sources(
        chemical_name=chemical_name, cas_number=cas_number, source_keys=["epa_ecotox"], limit_per_source=100,
    )
    pnec = derive_screening_pnec(hazard["candidates"])

    if scenario == "ema_phase_i_pharma":
        emission_payload = {
            "project_id": 0, "chemical_id": 0, "scenario_name": f"Quick screen: {chemical_name} (EMA Phase I)",
            "emission_mode": "ema_phase_i", "parent_name": chemical_name,
            "parent_molecular_weight_g_mol": parent_molecular_weight_g_mol,
            "product_name": None, "formulation": "tablet", "administration_route": "oral",
            "spc_title": None, "spc_identifier": None, "spc_url": None, "spc_access_date": None,
            "spc_source_type": "other", "consumption_source_title": "EMA human medicinal-product ERA Phase I default assumptions",
            "consumption_source_identifier": None,
            "therapeutic_class_ddd_per_1000_day": 0, "dose_per_administration": 1, "dose_unit": "mg", "administrations_per_day": 1,
            "oecd_class_key": None, "oecd_country": None,
            "refined_annual_active_kg": None, "daily_active_amount": None, "daily_active_unit": "mg", "emitting_days_per_year": 365,
            "maximum_daily_dose_mg": maximum_daily_dose_mg, "ema_fpen_mode": "default",
            "market_penetration_fraction": market_penetration_fraction,
            "prevalence_fraction": None, "treatment_days": None, "treatments_per_year": None,
            "regulatory_stp_capacity_inhabitants": population, "dilution_factor": dilution_factor,
            "population": population, "wastewater_l_person_day": wastewater_l_person_day,
            "wastewater_flow_m3_day_override": None,
            "direct_to_sewer_fraction": 0.0, "systemic_fraction": 1.0,
            "parent_urine_fraction": 0.51, "parent_faeces_fraction": 0.0, "metabolites": [],
        }
        emission = run_pharmaceutical_emission(emission_payload)
        pec_surface_water_ug_l = emission["regulatory"]["pec_surface_water_ug_l"]
        exposure_basis = "EMA Phase I regulatory screen (no metabolism, no STP removal) -- see emission.regulatory for the full calculation"
    else:
        annual_kg = release_kg_year
        emission_payload = {
            "project_id": 0, "chemical_id": 0, "scenario_name": f"Quick screen: {chemical_name} (generic WWTP catchment)",
            "emission_mode": "refined_annual_use", "parent_name": chemical_name,
            "parent_molecular_weight_g_mol": parent_molecular_weight_g_mol,
            "product_name": None, "formulation": "tablet", "administration_route": "other",
            "spc_title": None, "spc_identifier": None, "spc_url": None, "spc_access_date": None,
            "spc_source_type": "other", "consumption_source_title": "User-supplied annual release quantity",
            "consumption_source_identifier": None,
            "therapeutic_class_ddd_per_1000_day": 0, "dose_per_administration": 1, "dose_unit": "mg", "administrations_per_day": 1,
            "oecd_class_key": None, "oecd_country": None,
            "refined_annual_active_kg": annual_kg, "daily_active_amount": None, "daily_active_unit": "mg", "emitting_days_per_year": 365,
            "maximum_daily_dose_mg": None, "ema_fpen_mode": "default", "market_penetration_fraction": 0.01,
            "prevalence_fraction": None, "treatment_days": None, "treatments_per_year": None,
            "regulatory_stp_capacity_inhabitants": population, "dilution_factor": dilution_factor,
            "population": population, "wastewater_l_person_day": wastewater_l_person_day,
            "wastewater_flow_m3_day_override": None,
            "direct_to_sewer_fraction": 1.0, "systemic_fraction": 0.0,
            "parent_urine_fraction": 0.51, "parent_faeces_fraction": 0.0, "metabolites": [],
        }
        emission = run_pharmaceutical_emission(emission_payload)
        influent_ug_l = emission["influent"]["parent_concentration_ug_l"]
        pec_surface_water_ug_l = influent_ug_l / dilution_factor
        exposure_basis = (
            f"Generic reference-catchment screen: user-supplied {release_kg_year:g} kg/year, "
            f"{population:,} inhabitants, {wastewater_l_person_day:g} L/inhabitant/day, no STP removal assumed "
            f"(conservative), {dilution_factor:g}x receiving-water dilution"
        )

    rq = (float(pec_surface_water_ug_l) / float(pnec.pnec_ug_l)) if pnec.pnec_ug_l else None
    if rq is None:
        risk_band = "cannot_be_characterised"
    elif rq >= 1:
        risk_band = "risk_not_excluded"
    else:
        risk_band = "low"

    return {
        "chemical_name": chemical_name, "cas_number": cas_number, "smiles": smiles,
        "screening_estimate": True, "reviewed": False,
        "hazard": {
            "pnec_ug_l": float(pnec.pnec_ug_l) if pnec.pnec_ug_l else None,
            "basis": pnec.basis, "assessment_factor": float(pnec.assessment_factor) if pnec.assessment_factor else None,
            "critical_value_ug_l": float(pnec.critical_value_ug_l) if pnec.critical_value_ug_l else None,
            "critical_endpoint": pnec.critical_endpoint, "species_considered": pnec.species_considered,
            "candidates_found": pnec.candidates_used, "data_gap": pnec.data_gap,
            "source": "US EPA ECOTOX Knowledgebase (local import, live search)",
        },
        "exposure": {
            "scenario": scenario, "pec_surface_water_ug_l": pec_surface_water_ug_l, "basis": exposure_basis,
            "emission_run": emission,
        },
        "risk": {
            "risk_quotient": rq, "risk_band": risk_band,
            "note": "Screening estimate only -- not a reviewed assessment. Every input above is traceable to a real source or a stated, overridable convention; none is invented. A qualified reviewer must confirm the critical study, assessment factor and exposure scenario before this number is used for any regulatory or commercial decision.",
        },
    }
