from __future__ import annotations

from typing import Any


def _frequency_per_year(value: float, unit: str) -> float:
    factors = {"day": 365.0, "week": 52.0, "month": 12.0, "year": 1.0, "one_off": 1.0}
    return value * factors[unit]


def build_home_use_summary(data: dict[str, Any]) -> dict[str, Any]:
    annual_uses = _frequency_per_year(data["frequency_value"], data["frequency_unit"])
    annual_amount = data["amount_value"] * annual_uses
    route = data["release_route"]

    primary_path = {
        "down_drain": "wastewater treatment, followed by possible discharge to rivers or transfer to sewage sludge",
        "outdoor_soil": "soil, with possible movement to plants, groundwater, runoff or sediment",
        "outdoor_surface": "runoff to drains and surface water, plus residues on soil or hard surfaces",
        "spray_air": "air and nearby surfaces, followed by deposition to soil and water",
        "hazardous_waste": "managed waste treatment rather than direct environmental release",
        "general_bin": "solid-waste handling, with possible landfill or incineration",
    }[route]

    fate_flags: list[dict[str, str]] = []
    confidence_reasons: list[str] = []

    dt50 = data.get("soil_dt50_days")
    koc = data.get("koc_l_kg")
    logkow = data.get("log_kow")

    if dt50 is None:
        fate_flags.append({"topic": "Persistence", "level": "unknown", "text": "No reviewed degradation half-life was supplied."})
    elif dt50 >= 120:
        fate_flags.append({"topic": "Persistence", "level": "high", "text": "Slow degradation may allow repeated-use accumulation."})
        confidence_reasons.append("soil DT50 supplied")
    elif dt50 >= 30:
        fate_flags.append({"topic": "Persistence", "level": "moderate", "text": "The chemical may remain long enough for transport or repeated-use accumulation."})
        confidence_reasons.append("soil DT50 supplied")
    else:
        fate_flags.append({"topic": "Persistence", "level": "lower", "text": "The supplied soil half-life suggests comparatively faster degradation."})
        confidence_reasons.append("soil DT50 supplied")

    if koc is None:
        fate_flags.append({"topic": "Mobility", "level": "unknown", "text": "No reviewed Koc was supplied."})
    elif koc < 50:
        fate_flags.append({"topic": "Mobility", "level": "high", "text": "Weak sorption suggests greater potential to remain in water and move through soil."})
        confidence_reasons.append("Koc supplied")
    elif koc < 500:
        fate_flags.append({"topic": "Mobility", "level": "moderate", "text": "The chemical may divide between water and soil or sludge solids."})
        confidence_reasons.append("Koc supplied")
    else:
        fate_flags.append({"topic": "Mobility", "level": "lower", "text": "Strong sorption suggests transfer to soil, sediment or sludge solids may dominate."})
        confidence_reasons.append("Koc supplied")

    if logkow is None:
        fate_flags.append({"topic": "Hydrophobicity", "level": "unknown", "text": "No reviewed logKow/logP was supplied."})
    elif logkow >= 4:
        fate_flags.append({"topic": "Hydrophobicity", "level": "high", "text": "The supplied logKow indicates strong affinity for organic matter and lipids."})
        confidence_reasons.append("logKow supplied")
    elif logkow >= 2:
        fate_flags.append({"topic": "Hydrophobicity", "level": "moderate", "text": "Both dissolved and solid-associated transport may matter."})
        confidence_reasons.append("logKow supplied")
    else:
        fate_flags.append({"topic": "Hydrophobicity", "level": "lower", "text": "The chemical is more likely to remain in water unless ionisation or specific binding changes its behaviour."})
        confidence_reasons.append("logKow supplied")

    direct_release = route in {"down_drain", "outdoor_soil", "outdoor_surface", "spray_air"}
    advice = []
    if direct_release:
        advice.append("Avoid disposing of unused product directly to drains, soil or surface water.")
    if route == "down_drain":
        advice.append("Use only the required quantity and follow the product disposal instructions for residues.")
    elif route in {"outdoor_soil", "outdoor_surface", "spray_air"}:
        advice.append("Avoid application before heavy rain and keep the product away from drains and watercourses.")
    elif route == "general_bin":
        advice.append("Check whether the product should be taken to a household hazardous-waste collection point.")
    else:
        advice.append("Keep the product in its labelled container and follow the local hazardous-waste route.")

    known = len(confidence_reasons)
    confidence = "low" if known == 0 else "moderate" if known < 3 else "higher"

    reviewed_fields = set(data.get("reviewed_property_fields") or [])
    input_basis = [
        {
            "field": "chemical_identity",
            "source": "confirmed_project_chemical" if data.get("identity_binding") else "user_supplied_text",
            "status": "confirmed" if data.get("identity_binding") else "unverified",
        },
        {
            "field": "log_kow",
            "source": "reviewed_assessment_profile" if "log_kow" in reviewed_fields else "user_supplied_or_missing",
            "status": "reviewed" if "log_kow" in reviewed_fields else "not_reviewed_here",
        },
        {
            "field": "soil_dt50_days",
            "source": "reviewed_assessment_profile" if "soil_dt50_days" in reviewed_fields else "user_supplied_or_missing",
            "status": "reviewed" if "soil_dt50_days" in reviewed_fields else "not_reviewed_here",
        },
        {
            "field": "koc_l_kg",
            "source": "user_supplied_or_missing",
            "status": "not_reviewed_here",
        },
    ]

    return {
        "product_identifier": data.get("product_identifier"),
        "product_name": data.get("product_name") or "Unspecified product",
        "chemical_name": data.get("chemical_name") or "Unresolved chemical",
        "annual_use": {"value": annual_amount, "unit": data["amount_unit"], "uses_per_year": annual_uses},
        "primary_environmental_path": primary_path,
        "fate_flags": fate_flags,
        "advice": advice,
        "confidence": confidence,
        "confidence_basis": confidence_reasons or ["No reviewed fate-property values supplied"],
        "identity_binding": data.get("identity_binding"),
        "input_basis": input_basis,
        "scope": {
            "screening_type": "qualitative_household_use_fate_summary",
            "active_ingredient_mass_calculated": False,
            "pec_calculated": False,
            "pnec_used": False,
            "risk_quotient_calculated": False,
            "requires_human_review": True,
        },
        "warnings": [
            "A product identifier or barcode does not establish its active ingredient unless a reviewed product registry is connected.",
            "This summary does not scale one household use to a treatment-plant population and does not calculate PEC, PNEC or a risk quotient.",
        ],
        "plain_language_summary": (
            f"Based on the selected use, the main route is {primary_path}. "
            f"The estimated annual use is {annual_amount:.3g} {data['amount_unit']}. "
            "This is a screening explanation and not a regulatory conclusion."
        ),
    }
