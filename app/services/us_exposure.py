"""Transparent US industrial exposure foundations.

This module deliberately does not reproduce ChemSTEER, CEM or E-FAST.  It
provides a conservative, inspectable mass-flow, worker-dose and soil-to-
groundwater screen plus a versioned catalogue that can prepare and review
external EPA model workflows.
"""

from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "us_exposure_sources.json"
DIRECT_MEDIA = ("air", "water", "soil")
MANAGED_MEDIA = ("landfill", "incineration", "offsite_treatment")
ALL_MEDIA = DIRECT_MEDIA + MANAGED_MEDIA


@lru_cache(maxsize=1)
def _catalogue() -> dict[str, Any]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "envirochem.us_exposure_sources":
        raise RuntimeError("Unexpected US exposure source catalogue schema")
    scenarios = data.get("scenarios", [])
    if len(scenarios) != 60 or len({row["key"] for row in scenarios}) != 60:
        raise RuntimeError("US exposure source catalogue must contain 60 unique scenarios")
    if sum(row["publication_status"] == "published" for row in scenarios) != 12:
        raise RuntimeError("US exposure catalogue must identify exactly 12 published ESDs")
    return data


def manifest() -> dict[str, Any]:
    data = _catalogue()
    status_counts: dict[str, int] = {}
    for row in data["scenarios"]:
        status = row["publication_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema": data["schema"],
        "schema_version": data["schema_version"],
        "catalogue_version": data["catalogue_version"],
        "scientific_position": data["scientific_position"],
        "archive": data["archive"],
        "document_count": len(data["documents"]),
        "scenario_count": len(data["scenarios"]),
        "scenario_status_counts": status_counts,
        "default_scenario_count": sum(bool(row["default_enabled"]) for row in data["scenarios"]),
        "native_screen": {
            "key": "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN",
            "version": "0.2.0-alpha",
            "regulatory_equivalence": False,
            "purpose": "transparent source-term, release-routing, worker-dose and groundwater-leaching screening",
        },
        "external_workflows": ["PWC", "CHEMSTEER", "CEM", "EFAST"],
    }


def source_catalogue() -> list[dict[str, Any]]:
    return [dict(row) for row in _catalogue()["documents"]]


def scenario_catalogue(
    *,
    status: str | None = None,
    include_reference_only: bool = False,
) -> list[dict[str, Any]]:
    rows = _catalogue()["scenarios"]
    if status is not None:
        normalised = status.strip().lower()
        if normalised not in {"published", "draft"}:
            raise ValueError("status must be published or draft")
        rows = [row for row in rows if row["publication_status"] == normalised]
    elif not include_reference_only:
        rows = [row for row in rows if row["default_enabled"]]
    return [dict(row) for row in rows]


def scenario_by_key(key: str) -> dict[str, Any] | None:
    return next((dict(row) for row in _catalogue()["scenarios"] if row["key"] == key), None)


COMPLETENESS_SECTIONS: tuple[tuple[str, str], ...] = (
    ("identity_confirmed", "Confirmed chemical identity and substance form"),
    ("uses_and_volumes", "Uses, sites, production/import volumes and operating pattern"),
    ("manufacturing_processing", "Manufacturing, processing and industrial source terms"),
    ("worker_exposure", "Worker inhalation and dermal exposure"),
    ("consumer_exposure", "Consumer/product exposure where relevant"),
    ("environmental_releases", "Air, water and soil releases"),
    ("waste_disposal", "Landfill, incineration and off-site waste treatment"),
    ("fate_transport", "Environmental fate and transport"),
    ("ecological_effects", "Ecological effects and PNECs/equivalent benchmarks"),
    ("human_health_hazards", "Human-health hazards and points of departure"),
    ("vulnerable_populations", "Relevant life stages and susceptible populations"),
    ("monitoring_validation", "Monitoring, model evaluation or analogue support"),
    ("uncertainty_characterisation", "Assumptions, variability, uncertainty and sensitivity"),
    ("risk_characterisation", "Exposure-to-hazard comparison and decision context"),
    ("source_provenance", "Versioned source, parameter and reviewer provenance"),
)


def assess_completeness(data: dict[str, Any]) -> dict[str, Any]:
    sections = [
        {"key": key, "label": label, "complete": bool(data.get(key))}
        for key, label in COMPLETENESS_SECTIONS
    ]
    missing = [row for row in sections if not row["complete"]]
    return {
        "sections": sections,
        "complete_count": len(sections) - len(missing),
        "total_count": len(sections),
        "completion_fraction": (len(sections) - len(missing)) / len(sections),
        "missing": missing,
        "assessment_complete": not missing,
        "note": (
            "This is a completeness control, not a determination of regulatory "
            "adequacy. Relevance and depth remain chemical-, use- and programme-specific."
        ),
    }


def _worker_task(task: dict[str, Any]) -> dict[str, Any]:
    duration = float(task["task_duration_hours"])
    if task["inhalation_mode"] == "measured_air":
        concentration = float(task["measured_air_concentration_mg_m3"])
        concentration_basis = "measured_or_user_supplied_air_concentration"
        generation_rate = None
    else:
        handled_mg = float(task["chemical_handled_kg_per_shift"]) * 1_000_000.0
        uncontrolled_airborne_mg = (
            handled_mg
            * float(task["airborne_release_fraction"])
            * (1.0 - float(task["local_exhaust_control_fraction"]))
        )
        generation_rate = uncontrolled_airborne_mg / duration
        room_volume = float(task["room_volume_m3"])
        air_exchange = float(task["air_exchange_rate_per_hour"])
        loss_rate = room_volume * air_exchange
        steady_state = generation_rate / loss_rate
        dimensionless_time = air_exchange * duration
        build_up_factor = 1.0 - (1.0 - math.exp(-dimensionless_time)) / dimensionless_time
        concentration = steady_state * build_up_factor
        concentration_basis = "well_mixed_room_time_average_screen"

    inhaled_mg_shift = (
        concentration
        * float(task["inhalation_rate_m3_hour"])
        * duration
        / float(task["respirator_apf"])
    )
    inhaled_absorbed = inhaled_mg_shift * float(task["inhalation_absorption_fraction"])
    dermal_applied = float(task["dermal_contact_mg_shift"]) / float(task["glove_protection_factor"])
    dermal_absorbed = dermal_applied * float(task["dermal_absorption_fraction"])
    absorbed_shift = inhaled_absorbed + dermal_absorbed
    body_weight = float(task["body_weight_kg"])
    days = float(task["exposure_days_year"])
    return {
        "task_name": task["task_name"],
        "inhalation_mode": task["inhalation_mode"],
        "air_concentration_mg_m3": concentration,
        "air_concentration_basis": concentration_basis,
        "generation_rate_mg_hour": generation_rate,
        "inhaled_external_mg_shift": inhaled_mg_shift,
        "inhaled_absorbed_mg_shift": inhaled_absorbed,
        "dermal_external_mg_shift": dermal_applied,
        "dermal_absorbed_mg_shift": dermal_absorbed,
        "total_absorbed_mg_shift": absorbed_shift,
        "acute_absorbed_dose_mg_kg_shift": absorbed_shift / body_weight,
        "annual_absorbed_dose_mg_kg_year": absorbed_shift * days / body_weight,
        "average_daily_absorbed_dose_mg_kg_day": absorbed_shift * days / body_weight / 365.0,
        "exposure_days_year": days,
        "ppe": {
            "respirator_apf": float(task["respirator_apf"]),
            "glove_protection_factor": float(task["glove_protection_factor"]),
        },
    }


def _groundwater_leaching_screen(
    soil_release_kg_day: float,
    operating_days: float,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Conservative equilibrium/retarded-flow soil-to-groundwater screen.

    This is deliberately inspectable and is not PWC, PRZM or an EPA-endorsed
    leaching model.  It estimates annual source-zone pore-water concentration,
    then applies retarded travel time and first-order soil transformation to a
    stated assessment depth.  Preferential flow is not represented.
    """

    area_m2 = float(inputs["soil_release_area_ha"]) * 10_000.0
    source_depth_m = float(inputs["source_zone_depth_m"])
    assessment_depth_m = float(inputs["assessment_depth_m"])
    bulk_density_kg_m3 = float(inputs["soil_bulk_density_kg_m3"])
    theta = float(inputs["volumetric_water_content"])
    recharge_mm_year = float(inputs["annual_recharge_mm"])
    koc_l_kg = float(inputs["koc_l_kg"])
    foc = float(inputs["soil_organic_carbon_fraction"])
    dt50_days = float(inputs["soil_dt50_days"])
    attenuation = float(inputs["additional_attenuation_fraction"])

    annual_soil_release_kg = soil_release_kg_day * operating_days
    annual_load_mg_m2 = annual_soil_release_kg * 1_000_000.0 / area_m2
    soil_mass_kg_m2 = bulk_density_kg_m3 * source_depth_m
    source_zone_water_l_m2 = theta * source_depth_m * 1000.0
    kd_l_kg = koc_l_kg * foc
    equilibrium_capacity_l_m2 = source_zone_water_l_m2 + kd_l_kg * soil_mass_kg_m2
    source_porewater_mg_l = annual_load_mg_m2 / equilibrium_capacity_l_m2

    recharge_m_day = recharge_mm_year / 1000.0 / 365.0
    travel_distance_m = max(0.0, assessment_depth_m - source_depth_m / 2.0)
    unretarded_travel_days = travel_distance_m * theta / recharge_m_day
    bulk_density_kg_l = bulk_density_kg_m3 / 1000.0
    retardation_factor = 1.0 + bulk_density_kg_l * kd_l_kg / theta
    retarded_travel_days = unretarded_travel_days * retardation_factor
    transformation_survival_fraction = math.exp(-math.log(2.0) * retarded_travel_days / dt50_days)
    groundwater_mg_l = source_porewater_mg_l * transformation_survival_fraction * attenuation
    annual_recharge_l_m2 = recharge_mm_year
    annual_leached_mg_m2 = min(annual_load_mg_m2, groundwater_mg_l * annual_recharge_l_m2)

    return {
        "status": "screened",
        "regulatory_equivalence": False,
        "method": "equilibrium_source_zone_plus_retarded_first_order_vertical_transport",
        "soil_release_kg_day": soil_release_kg_day,
        "annual_soil_release_kg": annual_soil_release_kg,
        "annual_surface_loading_mg_m2": annual_load_mg_m2,
        "kd_l_kg": kd_l_kg,
        "source_zone_soil_mass_kg_m2": soil_mass_kg_m2,
        "source_zone_water_l_m2": source_zone_water_l_m2,
        "source_porewater_concentration_mg_l": source_porewater_mg_l,
        "unretarded_travel_time_days": unretarded_travel_days,
        "retardation_factor": retardation_factor,
        "retarded_travel_time_days": retarded_travel_days,
        "transformation_survival_fraction": transformation_survival_fraction,
        "additional_attenuation_fraction": attenuation,
        "screened_groundwater_concentration_ug_l": groundwater_mg_l * 1000.0,
        "annual_leached_mass_mg_m2": annual_leached_mg_m2,
        "parameter_source": inputs["parameter_source"],
        "inputs": inputs,
        "equations": {
            "kd": "Koc × soil organic-carbon fraction",
            "source_porewater": "annual surface load / (source-zone water + Kd × source-zone soil mass)",
            "retardation": "1 + bulk density × Kd / volumetric water content",
            "travel_time": "vertical water travel time × retardation factor",
            "groundwater": "source pore-water concentration × first-order survival × additional attenuation",
        },
        "limitations": [
            "This is an EnviroChem screening calculation, not PWC, PRZM or an EPA regulatory result.",
            "Preferential flow, macropores, runoff, erosion, layered soils, transient weather and crop processes are not represented.",
            "The annual release is treated as a source-zone equilibrium loading; event timing and multi-year accumulation require refinement.",
            "Additional attenuation defaults to 1.0 and must not be reduced without a documented site-specific basis.",
        ],
    }


def run_industrial_exposure_screen(data: dict[str, Any]) -> dict[str, Any]:
    throughput = float(data["chemical_throughput_kg_day"])
    operating_days = float(data["operating_days_year"])
    event_fraction_sum = sum(float(row["loss_fraction"]) for row in data["release_events"])
    if event_fraction_sum > 1.0 + 1e-12:
        raise ValueError(
            "Release-event loss fractions share the same throughput basis and cannot sum to more than 1"
        )

    media_daily = {key: 0.0 for key in ALL_MEDIA}
    event_rows: list[dict[str, Any]] = []
    for event in data["release_events"]:
        gross = throughput * float(event["loss_fraction"])
        controlled_fraction = float(event["control_efficiency_fraction"])
        captured = gross * controlled_fraction
        post_control = gross - captured
        for medium, fraction in event["media_fractions"].items():
            media_daily[medium] += post_control * float(fraction)
        destination = event.get("control_destination")
        if captured:
            if destination not in MANAGED_MEDIA:
                raise ValueError("A controlled release event must state a managed-waste control destination")
            media_daily[destination] += captured
        event_rows.append({
            "event_key": event["event_key"],
            "name": event["name"],
            "gross_event_mass_kg_day": gross,
            "post_control_mass_kg_day": post_control,
            "captured_mass_kg_day": captured,
            "control_destination": destination,
            "media_mass_kg_day": {
                medium: post_control * float(fraction)
                for medium, fraction in event["media_fractions"].items()
            },
            "evidence_status": event["evidence_status"],
            "source_reference": event.get("source_reference"),
        })

    routed = sum(media_daily.values())
    retained = throughput - throughput * event_fraction_sum
    closure_error = throughput - routed - retained
    workers = [_worker_task(task) for task in data.get("worker_tasks", [])]
    groundwater = None
    if data.get("groundwater_screen") is not None:
        groundwater = _groundwater_leaching_screen(
            media_daily["soil"], operating_days, data["groundwater_screen"]
        )
    scenario = scenario_by_key(data.get("source_scenario_key")) if data.get("source_scenario_key") else None
    scenario_warning = None
    if scenario and scenario["publication_status"] != "published":
        scenario_warning = "A draft/reference-only EPA scenario was selected explicitly; it is not an enabled default."

    complete_flags = {
        "identity_confirmed": True,
        "uses_and_volumes": throughput > 0 and operating_days > 0,
        "manufacturing_processing": bool(data["release_events"]),
        "worker_exposure": bool(workers),
        "consumer_exposure": bool(data.get("consumer_exposure_addressed")),
        "environmental_releases": any(media_daily[key] > 0 for key in DIRECT_MEDIA),
        "waste_disposal": any(media_daily[key] > 0 for key in MANAGED_MEDIA),
        "fate_transport": bool(groundwater) or bool(data.get("fate_transport_addressed")),
        "ecological_effects": bool(data.get("ecological_effects_addressed")),
        "human_health_hazards": bool(data.get("human_health_hazards_addressed")),
        "vulnerable_populations": bool(data.get("vulnerable_populations_addressed")),
        "monitoring_validation": bool(data.get("monitoring_validation_addressed")),
        "uncertainty_characterisation": bool(data.get("uncertainty_notes")),
        "risk_characterisation": bool(data.get("risk_characterisation_addressed")),
        "source_provenance": bool(data.get("citations")),
    }
    warnings = [
        "Native research screen only; this is not a ChemSTEER, CEM or E-FAST calculation.",
        "Every event fraction is applied to the same daily chemical-throughput basis; overlapping events would double count.",
        "Well-mixed-room estimates omit near-field peaks and must not replace measured task data where available.",
        "Managed-waste routing is a transfer, not proof of destruction or zero downstream release.",
    ]
    if scenario_warning:
        warnings.append(scenario_warning)
    if not workers:
        warnings.append("No occupational task was supplied; worker exposure remains incomplete.")
    if media_daily["soil"] > 0 and groundwater is None:
        warnings.append("A direct soil release was calculated but groundwater leaching was not screened.")
    if groundwater:
        warnings.extend(groundwater["limitations"])

    return {
        "model_key": "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN",
        "model_version": "0.2.0-alpha",
        "regulatory_equivalence": False,
        "scenario": scenario,
        "review_status": "scientist_reviewed" if data.get("scientist_review_confirmed") else "unreviewed_screen",
        "release_events": event_rows,
        "releases": {
            "daily_kg": media_daily,
            "annual_kg": {key: value * operating_days for key, value in media_daily.items()},
            "direct_environmental_release_kg_day": sum(media_daily[key] for key in DIRECT_MEDIA),
            "managed_waste_transfer_kg_day": sum(media_daily[key] for key in MANAGED_MEDIA),
            "retained_or_unmodelled_process_mass_kg_day": retained,
        },
        "mass_balance": {
            "input_kg_day": throughput,
            "routed_kg_day": routed,
            "retained_kg_day": retained,
            "closure_error_kg_day": closure_error,
            "closure_error_fraction": closure_error / throughput,
            "event_loss_fraction_sum": event_fraction_sum,
        },
        "worker_exposure": workers,
        "groundwater_leaching": groundwater or {
            "status": "not_assessed",
            "reason": "No groundwater-screen inputs were supplied.",
            "soil_release_kg_day": media_daily["soil"],
        },
        "completeness": assess_completeness(complete_flags),
        "citations": data.get("citations", []),
        "uncertainty_notes": data.get("uncertainty_notes"),
        "warnings": warnings,
    }
