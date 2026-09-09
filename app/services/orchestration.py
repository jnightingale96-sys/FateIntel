"""Jurisdiction-aware tier orchestration and scientific compatibility controls.

This module is deliberately conservative.  It builds a complete assessment
record and supports cross-framework comparison, but it never turns an adapted
or cross-jurisdiction workflow into a regulatory claim.  Unknown units,
untyped model ports and incompatible endpoint bases remain visible blockers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable

from .registry import MODELS, build_assessment_plan


ORCHESTRATION_VERSION = "FATEINTEL_ORCHESTRATION_0.1.0"
RISK_RULESET_VERSION = "FATEINTEL_RISK_CHARACTERISATION_0.1.0"
MODEL_CONTRACT_SCHEMA_VERSION = "FATEINTEL_MODEL_PORTS_0.1.0"

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "model_semantic_contracts.json"


def _unit_token(value: str) -> str:
    token = (
        str(value or "")
        .strip()
        .replace("³", "3")
        .replace("−", "-")
        .replace("·", "/")
        .replace(" ", "")
        .replace("_", "")
        .casefold()
    )
    # Unicode case-folding maps the micro sign to Greek mu; collapse both
    # spellings after case-folding so µg/L and μg/L remain equivalent.
    return token.replace("μ", "µ")


# token -> (dimension, canonical unit, multiplier to canonical unit)
UNIT_DEFINITIONS: dict[str, tuple[str, str, float]] = {
    "ng/l": ("aqueous_concentration", "µg/L", 1e-3),
    "ug/l": ("aqueous_concentration", "µg/L", 1.0),
    "µg/l": ("aqueous_concentration", "µg/L", 1.0),
    "mg/l": ("aqueous_concentration", "µg/L", 1e3),
    "g/l": ("aqueous_concentration", "µg/L", 1e6),
    "ng/kg": ("solid_concentration", "µg/kg", 1e-3),
    "ng/g": ("solid_concentration", "µg/kg", 1.0),
    "ug/kg": ("solid_concentration", "µg/kg", 1.0),
    "µg/kg": ("solid_concentration", "µg/kg", 1.0),
    "mg/kg": ("solid_concentration", "µg/kg", 1e3),
    "g/kg": ("solid_concentration", "µg/kg", 1e6),
    "ng/m3": ("air_concentration", "µg/m3", 1e-3),
    "ug/m3": ("air_concentration", "µg/m3", 1.0),
    "µg/m3": ("air_concentration", "µg/m3", 1.0),
    "mg/m3": ("air_concentration", "µg/m3", 1e3),
    "ug/day": ("mass_rate", "kg/day", 1e-9),
    "µg/day": ("mass_rate", "kg/day", 1e-9),
    "mg/day": ("mass_rate", "kg/day", 1e-6),
    "g/day": ("mass_rate", "kg/day", 1e-3),
    "kg/day": ("mass_rate", "kg/day", 1.0),
    "g/ha": ("areal_loading", "kg/ha", 1e-3),
    "kg/ha": ("areal_loading", "kg/ha", 1.0),
    "ug/kgbw/day": ("dose", "mg/kg bw/day", 1e-3),
    "µg/kgbw/day": ("dose", "mg/kg bw/day", 1e-3),
    "mg/kgbw/day": ("dose", "mg/kg bw/day", 1.0),
    "ng/kgbw/day": ("dose", "mg/kg bw/day", 1e-6),
    "h": ("time", "days", 1 / 24),
    "hour": ("time", "days", 1 / 24),
    "hours": ("time", "days", 1 / 24),
    "d": ("time", "days", 1.0),
    "day": ("time", "days", 1.0),
    "days": ("time", "days", 1.0),
    "%": ("fraction", "fraction", 1e-2),
    "fraction": ("fraction", "fraction", 1.0),
    "1": ("dimensionless", "1", 1.0),
    "dimensionless": ("dimensionless", "1", 1.0),
    "l/kg": ("partition_coefficient", "L/kg", 1.0),
    "ml/g": ("partition_coefficient", "L/kg", 1.0),
}


WATER_COMPARTMENTS = {
    "water", "surface_water", "groundwater", "porewater",
    "wwtp_influent", "wwtp_effluent", "drinking_water",
}
SOLID_COMPARTMENTS = {"soil", "sediment", "sludge", "biosolids", "biota", "food"}


RISK_METRICS = {
    "pec_pnec_rq": {
        "direction": "lower_is_safer",
        "default_threshold": 1.0,
        "description": "Environmental predicted exposure concentration divided by a reviewed PNEC.",
    },
    "pesticide_rq_loc": {
        "direction": "lower_is_safer",
        "default_threshold": None,
        "description": "Pesticide exposure/effect quotient compared with a programme-specific level of concern.",
    },
    "hazard_quotient": {
        "direction": "lower_is_safer",
        "default_threshold": 1.0,
        "description": "Exposure divided by a reviewed health or ecological benchmark.",
    },
    "risk_characterisation_ratio": {
        "direction": "lower_is_safer",
        "default_threshold": 1.0,
        "description": "Exposure divided by a DNEL or equivalent benchmark.",
    },
    "drinking_water_ratio": {
        "direction": "lower_is_safer",
        "default_threshold": 1.0,
        "description": "Drinking-water concentration divided by the applicable reviewed benchmark.",
    },
    "margin_of_exposure": {
        "direction": "higher_is_safer",
        "default_threshold": None,
        "description": "Point of departure divided by exposure and compared with a required minimum margin.",
    },
}


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def record_hash(data: dict[str, Any]) -> str:
    return sha256(_canonical_json(data).encode("utf-8")).hexdigest()


def _finite_number(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _unit_definition(unit: str) -> tuple[str, str, float]:
    definition = UNIT_DEFINITIONS.get(_unit_token(unit))
    if definition is None:
        raise ValueError(f"Unsupported unit: {unit}")
    return definition


def _expected_dimension(quantity: dict[str, Any]) -> str | None:
    kind = str(quantity.get("endpoint_kind") or "").casefold()
    compartment = str(quantity.get("compartment") or "").casefold()
    if kind == "concentration":
        if compartment in WATER_COMPARTMENTS:
            return "aqueous_concentration"
        if compartment in SOLID_COMPARTMENTS:
            return "solid_concentration"
        if compartment == "air":
            return "air_concentration"
        return None
    return {
        "mass_rate": "mass_rate",
        "areal_loading": "areal_loading",
        "dose": "dose",
        "half_life": "time",
        "duration": "time",
        "fraction": "fraction",
        "risk_quotient": "dimensionless",
        "partition_coefficient": "partition_coefficient",
    }.get(kind)


def harmonise_quantity(quantity: dict[str, Any], target_unit: str | None = None) -> dict[str, Any]:
    """Convert a quantity without changing its scientific basis metadata."""

    value = _finite_number(quantity.get("value"), "value")
    source_dimension, canonical_unit, source_factor = _unit_definition(str(quantity.get("unit") or ""))
    expected_dimension = _expected_dimension(quantity)
    if expected_dimension is not None and expected_dimension != source_dimension:
        raise ValueError(
            f"Unit {quantity.get('unit')} has dimension {source_dimension}, but "
            f"{quantity.get('endpoint_kind')} in {quantity.get('compartment')} requires {expected_dimension}"
        )

    destination_unit = target_unit or canonical_unit
    target_dimension, _, target_factor = _unit_definition(destination_unit)
    if target_dimension != source_dimension:
        raise ValueError(
            f"Cannot convert {source_dimension} ({quantity.get('unit')}) to "
            f"{target_dimension} ({destination_unit})"
        )

    converted = value * source_factor / target_factor
    return {
        **quantity,
        "value": converted,
        "unit": destination_unit,
        "dimension": source_dimension,
        "original": {"value": value, "unit": quantity.get("unit")},
        "conversion": {
            "source_unit": quantity.get("unit"),
            "target_unit": destination_unit,
            "multiplier": source_factor / target_factor,
            "lossless_basis_change": True,
        },
    }


def _metadata_value(data: dict[str, Any], key: str) -> str:
    return str(data.get(key) or "unspecified").strip().casefold()


def check_endpoint_compatibility(
    source: dict[str, Any],
    target: dict[str, Any],
    *,
    allow_unspecified: bool = False,
) -> dict[str, Any]:
    """Fail closed when a model output cannot satisfy a downstream input port."""

    reasons: list[dict[str, str]] = []
    warnings: list[str] = []

    source_kind = _metadata_value(source, "endpoint_kind")
    target_kind = _metadata_value(target, "endpoint_kind")
    if source_kind != target_kind:
        reasons.append({
            "code": "endpoint_kind_mismatch",
            "message": f"Source endpoint kind {source_kind} does not match target {target_kind}.",
        })

    fields = (
        "compartment", "phase", "basis", "temporal_statistic",
        "spatial_scale", "substance_basis",
    )
    for field in fields:
        left = _metadata_value(source, field)
        right = _metadata_value(target, field)
        if left == right:
            continue
        if "unspecified" in {left, right}:
            message = f"{field.replace('_', ' ').title()} is unspecified on one side of the proposed connection."
            if allow_unspecified:
                warnings.append(message)
            else:
                reasons.append({"code": f"{field}_unspecified", "message": message})
        else:
            reasons.append({
                "code": f"{field}_mismatch",
                "message": f"Source {field} {left} does not match target {right}.",
            })

    source_period = source.get("averaging_period_days")
    target_period = target.get("averaging_period_days")
    if source_period is not None or target_period is not None:
        if source_period is None or target_period is None:
            message = "Averaging period is missing on one side of the proposed connection."
            if allow_unspecified:
                warnings.append(message)
            else:
                reasons.append({"code": "averaging_period_unspecified", "message": message})
        elif not math.isclose(
            _finite_number(source_period, "source averaging period"),
            _finite_number(target_period, "target averaging period"),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            reasons.append({
                "code": "averaging_period_mismatch",
                "message": f"Source averaging period {source_period} days does not match target {target_period} days.",
            })

    harmonised = None
    try:
        source_dimension, _, _ = _unit_definition(str(source.get("unit") or ""))
        target_dimension, _, _ = _unit_definition(str(target.get("unit") or ""))
        if source_dimension != target_dimension:
            reasons.append({
                "code": "dimension_mismatch",
                "message": f"Source unit dimension {source_dimension} does not match target {target_dimension}.",
            })
        elif "value" in source:
            harmonised = harmonise_quantity(source, str(target.get("unit")))
    except ValueError as exc:
        reasons.append({"code": "unit_not_harmonisable", "message": str(exc)})

    return {
        "compatible": not reasons,
        "status": "compatible" if not reasons else "blocked",
        "reasons": reasons,
        "warnings": warnings,
        "harmonised_source": harmonised,
        "rule": "Exact scientific bases are required; unit conversion alone cannot repair a compartment, phase, time, scale or substance-basis mismatch.",
    }


def _load_semantic_contracts() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def semantic_contract_catalogue() -> dict[str, Any]:
    payload = _load_semantic_contracts()
    typed = payload.get("contracts", {})
    registry = {model["key"]: model for model in MODELS}
    rows = []
    for key, model in registry.items():
        contract = typed.get(key)
        rows.append({
            "model_key": key,
            "model_name": model["name"],
            "implementation": model["implementation"],
            "registry_status": model["status"],
            "semantic_status": contract.get("status") if contract else "untyped",
            "inputs": contract.get("inputs", []) if contract else [],
            "outputs": contract.get("outputs", []) if contract else [],
            "automatic_connection_allowed": bool(contract and contract.get("status") == "verified"),
        })
    return {
        "schema_version": payload["schema_version"],
        "contracts": rows,
        "coverage": {
            "registered_models": len(registry),
            "typed_models": len(typed),
            "verified_models": sum(1 for row in rows if row["semantic_status"] == "verified"),
            "untyped_models": sum(1 for row in rows if row["semantic_status"] == "untyped"),
        },
    }


def model_port_compatibility(
    source_model_key: str,
    source_port_key: str,
    target_model_key: str,
    target_port_key: str,
    *,
    value: float = 1.0,
    allow_draft_contracts: bool = False,
) -> dict[str, Any]:
    contracts = _load_semantic_contracts().get("contracts", {})
    source_model = contracts.get(source_model_key)
    target_model = contracts.get(target_model_key)
    if source_model is None or target_model is None:
        missing = [key for key, contract in ((source_model_key, source_model), (target_model_key, target_model)) if contract is None]
        return {
            "compatible": False,
            "status": "blocked",
            "reasons": [{
                "code": "untyped_model_contract",
                "message": "No semantic input/output contract is registered for: " + ", ".join(missing),
            }],
            "warnings": [],
            "harmonised_source": None,
        }
    if not allow_draft_contracts and (
        source_model.get("status") != "verified" or target_model.get("status") != "verified"
    ):
        return {
            "compatible": False,
            "status": "blocked",
            "reasons": [{
                "code": "unverified_model_contract",
                "message": "Automatic chaining requires verified semantic contracts on both models.",
            }],
            "warnings": [],
            "harmonised_source": None,
        }
    source = next((port for port in source_model.get("outputs", []) if port["port_key"] == source_port_key), None)
    target = next((port for port in target_model.get("inputs", []) if port["port_key"] == target_port_key), None)
    if source is None or target is None:
        return {
            "compatible": False,
            "status": "blocked",
            "reasons": [{
                "code": "unknown_model_port",
                "message": "The requested source output or target input port does not exist.",
            }],
            "warnings": [],
            "harmonised_source": None,
        }
    return {
        **check_endpoint_compatibility({**source, "value": value}, target),
        "source_model_key": source_model_key,
        "source_port_key": source_port_key,
        "target_model_key": target_model_key,
        "target_port_key": target_port_key,
        "contract_status": {
            "source": source_model.get("status"),
            "target": target_model.get("status"),
        },
    }


def characterise_risk(data: dict[str, Any]) -> dict[str, Any]:
    metric = str(data.get("metric") or "")
    if metric not in RISK_METRICS:
        raise ValueError(f"Unsupported risk metric: {metric}")
    exposure = dict(data["exposure"])
    benchmark = dict(data["benchmark"])
    compatibility = check_endpoint_compatibility(exposure, benchmark)
    has_internal_reference = bool(data.get("exposure_run_id") or data.get("exposure_workflow_id"))
    has_output_hash = bool(data.get("exposure_output_hash"))
    exposure_provenance_verified = (
        has_internal_reference
        and has_output_hash
        and bool(data.get("exposure_value_verified"))
    )
    benchmark_required = metric in {"pec_pnec_rq", "pesticide_rq_loc"}
    benchmark_provenance_verified = (
        bool(data.get("benchmark_value_verified"))
        if benchmark_required
        else True
    )
    provenance_verified = exposure_provenance_verified and benchmark_provenance_verified
    if not compatibility["compatible"]:
        return {
            "name": data.get("name") or metric,
            "metric": metric,
            "status": "incompatible",
            "value": None,
            "threshold": data.get("threshold"),
            "concern_triggered": None,
            "compatibility": compatibility,
            "decision_eligible": False,
            "exposure_provenance_status": "verified_internal_reference" if exposure_provenance_verified else "unverified",
            "benchmark_provenance_status": "verified_reviewed_evidence" if benchmark_provenance_verified else "unverified",
            "conclusion": "Risk was not calculated because exposure and benchmark bases are incompatible.",
            "ruleset_version": RISK_RULESET_VERSION,
        }

    exposure_in_benchmark_unit = harmonise_quantity(exposure, benchmark["unit"])
    exposure_value = exposure_in_benchmark_unit["value"]
    benchmark_value = _finite_number(benchmark.get("value"), "benchmark value")
    if benchmark_value <= 0:
        raise ValueError("benchmark value must be greater than zero")
    if exposure_value < 0:
        raise ValueError("exposure value cannot be negative")

    default_threshold = RISK_METRICS[metric]["default_threshold"]
    threshold = data.get("threshold", default_threshold)
    if threshold is None:
        raise ValueError(f"A programme-specific threshold is required for {metric}")
    threshold = _finite_number(threshold, "threshold")
    if threshold <= 0:
        raise ValueError("threshold must be greater than zero")

    if metric == "margin_of_exposure":
        if exposure_value == 0:
            value = None
            concern = False
            status = "no_exposure"
            conclusion = "Exposure is zero; a finite margin of exposure is not calculated."
        else:
            value = benchmark_value / exposure_value
            concern = value < threshold
            status = "triggered" if concern else "below_trigger"
            conclusion = (
                f"Margin of exposure {value:.6g} is {'below' if concern else 'at or above'} "
                f"the required minimum {threshold:.6g}."
            )
    else:
        value = exposure_value / benchmark_value
        concern = value >= threshold
        status = "triggered" if concern else "below_trigger"
        conclusion = (
            f"{metric.replace('_', ' ').title()} {value:.6g} is "
            f"{'at or above' if concern else 'below'} the decision threshold {threshold:.6g}."
        )

    return {
        "name": data.get("name") or metric,
        "metric": metric,
        "status": status,
        "value": value,
        "threshold": threshold,
        "concern_triggered": concern,
        "exposure_harmonised": exposure_in_benchmark_unit,
        "benchmark": benchmark,
        "benchmark_type": data.get("benchmark_type"),
        "benchmark_source": data.get("benchmark_source"),
        "guidance_reference": data.get("guidance_reference"),
        "benchmark_evidence": data.get("benchmark_evidence", []),
        "benchmark_evidence_review_confirmed": bool(data.get("benchmark_evidence_review_confirmed")),
        "benchmark_derivation": data.get("benchmark_derivation"),
        "compatibility": compatibility,
        "decision_eligible": provenance_verified,
        "exposure_provenance_status": "verified_internal_reference" if exposure_provenance_verified else "calculated_without_verified_internal_exposure_reference",
        "benchmark_provenance_status": (
            "verified_reviewed_evidence"
            if benchmark_provenance_verified
            else "calculated_without_verified_reviewed_benchmark_evidence"
        ),
        "exposure_provenance": {
            "model_key": data.get("model_key"),
            "run_id": data.get("exposure_run_id"),
            "workflow_id": data.get("exposure_workflow_id"),
            "output_hash": data.get("exposure_output_hash"),
            "endpoint_key": data.get("exposure_endpoint_key"),
        },
        "conclusion": conclusion,
        "ruleset_version": RISK_RULESET_VERSION,
    }


def evaluate_tier_gate(
    *,
    current_tier: int,
    maximum_tier: int,
    uncertainty: str,
    data_gaps: Iterable[dict[str, Any]],
    risk_results: Iterable[dict[str, Any]],
    connection_results: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    gaps = [
        gap for gap in data_gaps
        if gap.get("required_by_tier") is None or int(gap["required_by_tier"]) <= current_tier
    ]
    results = list(risk_results)
    connections = list(connection_results)
    blocking_gaps = [gap for gap in gaps if gap.get("blocks_conclusion", True)]
    invalid_risk = [result for result in results if result.get("status") == "incompatible"]
    invalid_connections = [result for result in connections if not result.get("compatible")]
    valid_risk = [
        result for result in results
        if result.get("concern_triggered") is not None and result.get("decision_eligible", True)
    ]
    triggered = [result for result in valid_risk if result["concern_triggered"]]

    reasons: list[str] = []
    if current_tier == 0 and not blocking_gaps:
        action = "advance"
        reasons.append("Identity and initial data sufficiency contain no blocking gap; begin Tier 1 screening.")
    elif invalid_risk or invalid_connections:
        action = "resolve_incompatibility"
        reasons.append("At least one risk result or model connection uses incompatible scientific bases.")
    elif not valid_risk:
        action = "collect_inputs"
        reasons.append("No compatible risk characterisation is available at the current tier.")
    elif triggered:
        action = "advance" if current_tier < maximum_tier else "expert_review"
        reasons.append("At least one applicable risk metric meets or exceeds its refinement trigger.")
    elif blocking_gaps:
        action = "advance" if current_tier < maximum_tier else "expert_review"
        reasons.append("Blocking evidence or model-output gaps prevent a final conclusion.")
    elif uncertainty in {"high", "unknown"}:
        action = "advance" if current_tier < maximum_tier else "expert_review"
        reasons.append(f"{uncertainty.title()} uncertainty requires refinement or expert review.")
    else:
        action = "stop_screening"
        reasons.append("All compatible metrics are below their triggers and no blocking gap remains.")

    next_tier = current_tier + 1 if action == "advance" and current_tier < maximum_tier else None
    return {
        "current_tier": current_tier,
        "maximum_tier": maximum_tier,
        "action": action,
        "next_tier": next_tier,
        "reasons": reasons,
        "blocking_data_gap_count": len(blocking_gaps),
        "compatible_risk_count": len(valid_risk),
        "triggered_risk_count": len(triggered),
        "blocked_connection_count": len(invalid_connections),
        "automatic_final_regulatory_conclusion": False,
    }


def build_tier_sequence(context: dict[str, Any]) -> list[dict[str, Any]]:
    maximum_tier = int(context["maximum_tier"])
    previous: set[str] = set()
    sequence: list[dict[str, Any]] = []
    for tier in range(0, maximum_tier + 1):
        if tier == 0:
            sequence.append({
                "tier": 0,
                "title": "Identity and data sufficiency",
                "regulatory_programme": None,
                "models": [],
                "introduced_models": [],
                "required_inputs": [
                    "confirmed immutable chemical identity",
                    "chemical/use classification",
                    "release scenario and jurisdiction",
                    "initial evidence inventory",
                ],
                "warnings": [],
            })
            continue
        plan_payload = {
            "jurisdiction": context["jurisdiction"],
            "contaminant_group": context["contaminant_group"],
            "scenario": context["scenario"],
            "tier": tier,
            "application_method": context.get("application_method"),
            "use_site_category": context.get("use_site_category"),
            "bee_attractive": context.get("bee_attractive", False),
        }
        plan = build_assessment_plan(plan_payload)
        applicable = [model for model in plan["models"] if model["applicable"]]
        keys = {model["key"] for model in applicable}
        sequence.append({
            "tier": tier,
            "title": {
                1: "Conservative screening",
                2: "Standard models and reviewed inputs",
                3: "Refined and spatial assessment",
                4: "Monitoring-informed/site-specific assessment",
            }[tier],
            "regulatory_programme": plan["regulatory_programme"],
            "models": applicable,
            "introduced_models": sorted(keys - previous),
            "required_inputs": plan["required_inputs"],
            "warnings": plan["warnings"],
        })
        previous = keys
    return sequence


def classify_regulatory_status(
    *,
    context: dict[str, Any],
    current_models: Iterable[dict[str, Any]],
    model_results: Iterable[dict[str, Any]],
    data_gaps: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    mode = context["assessment_mode"]
    results = list(model_results)
    gaps = list(data_gaps)
    current_models = list(current_models)

    if mode == "comparative":
        return {
            "code": "cross_jurisdiction_comparative",
            "label": "Cross-jurisdiction scientific comparison",
            "regulatory_aligned": False,
            "reason": "Comparative results are scientific refinements and are not an accepted submission merely because official models are included.",
        }
    if mode == "hybrid":
        return {
            "code": "research_only_hybrid",
            "label": "Research-only hybrid assessment",
            "regulatory_aligned": False,
            "reason": "The assessment deliberately combines methods outside one prescribed jurisdictional pathway.",
        }

    if any(result.get("jurisdiction") != context["jurisdiction"] for result in results):
        return {
            "code": "cross_jurisdiction_result_present",
            "label": "Cross-jurisdiction result present",
            "regulatory_aligned": False,
            "reason": "At least one result originates from a different jurisdiction.",
        }

    if any(model.get("status") == "adapter_planned" for model in current_models):
        return {
            "code": "incomplete_model_coverage",
            "label": "Incomplete model coverage",
            "regulatory_aligned": False,
            "reason": "At least one selected model remains a planned adapter rather than a completed workflow.",
        }

    blocking_gaps = [gap for gap in gaps if gap.get("blocks_conclusion", True)]
    if blocking_gaps:
        return {
            "code": "regulatory_pathway_incomplete",
            "label": "Regulatory pathway incomplete",
            "regulatory_aligned": False,
            "reason": "Blocking evidence or workflow gaps remain.",
        }

    if not results:
        return {
            "code": "regulatory_pathway_preparation",
            "label": "Regulatory pathway preparation",
            "regulatory_aligned": False,
            "reason": "A jurisdictional route exists, but no completed reviewed model results have been supplied.",
        }

    required_model_keys = {model["key"] for model in current_models}
    supplied_model_keys = {result.get("model_key") for result in results}
    missing_model_keys = sorted(required_model_keys - supplied_model_keys)
    if missing_model_keys:
        return {
            "code": "regulatory_evidence_requires_review",
            "label": "Regulatory evidence requires review",
            "regulatory_aligned": False,
            "reason": "Applicable current-tier model results are missing: " + ", ".join(missing_model_keys),
        }

    acceptable_statuses = {"completed", "reviewed"}
    aligned = all(
        result.get("execution_status") in acceptable_statuses
        and result.get("alignment_claim") == "regulatory_accepted"
        and result.get("guidance_reference")
        and (result.get("run_id") or result.get("workflow_id"))
        for result in results
    )
    if aligned:
        return {
            "code": "regulatory_aligned_workflow",
            "label": "Regulatory-aligned workflow",
            "regulatory_aligned": True,
            "reason": "Every supplied result is completed or reviewed, has internal provenance and carries an explicit accepted-method guidance basis.",
        }
    return {
        "code": "regulatory_evidence_requires_review",
        "label": "Regulatory evidence requires review",
        "regulatory_aligned": False,
        "reason": "One or more model results lack reviewed execution provenance or an explicit accepted-method basis.",
    }


def compare_jurisdictional_results(data: dict[str, Any]) -> dict[str, Any]:
    left = data["left"]
    right = data["right"]
    if left["jurisdiction"] == right["jurisdiction"]:
        raise ValueError("Cross-jurisdiction comparison requires two different jurisdictions")
    compatibility = check_endpoint_compatibility(left["quantity"], right["quantity"])
    if not compatibility["compatible"]:
        return {
            "status": "blocked",
            "regulatory_status": "cross_jurisdiction_comparative",
            "compatibility": compatibility,
            "comparison": None,
        }
    right_unit = right["quantity"]["unit"]
    left_harmonised = harmonise_quantity(left["quantity"], right_unit)
    right_harmonised = harmonise_quantity(right["quantity"], right_unit)
    left_value = left_harmonised["value"]
    right_value = right_harmonised["value"]
    ratio = None if right_value == 0 else left_value / right_value
    percent_difference = None if right_value == 0 else ((left_value - right_value) / right_value) * 100
    return {
        "status": "comparable",
        "regulatory_status": "cross_jurisdiction_comparative",
        "compatibility": compatibility,
        "comparison": {
            "left": {**left, "quantity": left_harmonised},
            "right": {**right, "quantity": right_harmonised},
            "left_to_right_ratio": ratio,
            "percent_difference_relative_to_right": percent_difference,
        },
        "boundary": "This comparison is a scientific refinement and is not automatically accepted by either jurisdiction.",
    }


def _assessment_graph(
    *,
    context: dict[str, Any],
    identity: dict[str, Any],
    tier_sequence: list[dict[str, Any]],
    risk_results: list[dict[str, Any]],
    connection_results: list[dict[str, Any]],
    gate: dict[str, Any],
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = [
        {"id": "chemical", "type": "chemical", "label": identity.get("preferred_name") or "Confirmed chemical", "data": {"identity_hash": identity.get("identity_hash")}},
        {"id": "context", "type": "assessment_context", "label": f"{context['jurisdiction']} · {context['scenario']}", "data": context},
    ]
    edges: list[dict[str, str]] = [
        {"source": "chemical", "target": "context", "relation": "assessed_under"},
    ]
    for stage in tier_sequence:
        tier_id = f"tier:{stage['tier']}"
        nodes.append({"id": tier_id, "type": "tier", "label": f"Tier {stage['tier']} · {stage['title']}", "data": {"required_inputs": stage["required_inputs"], "warnings": stage["warnings"]}})
        if stage["tier"] == 0:
            edges.append({"source": "context", "target": tier_id, "relation": "starts_at"})
        else:
            edges.append({"source": f"tier:{stage['tier'] - 1}", "target": tier_id, "relation": "may_advance_to"})
        for model in stage["models"]:
            model_id = f"tier:{stage['tier']}:model:{model['key']}"
            nodes.append({"id": model_id, "type": "model", "label": model["name"], "data": {"model_key": model["key"], "implementation": model["implementation"], "status": model["status"]}})
            edges.append({"source": tier_id, "target": model_id, "relation": "uses"})
    for index, result in enumerate(risk_results, start=1):
        risk_id = f"risk:{index}"
        nodes.append({"id": risk_id, "type": "risk_characterisation", "label": result["name"], "data": result})
        edges.append({"source": f"tier:{context['current_tier']}", "target": risk_id, "relation": "characterised_by"})
    for index, connection in enumerate(connection_results, start=1):
        connection_id = f"connection:{index}"
        nodes.append({
            "id": connection_id,
            "type": "model_connection",
            "label": "Compatible model transfer" if connection.get("compatible") else "Blocked model transfer",
            "data": connection,
        })
        edges.append({"source": f"tier:{context['current_tier']}", "target": connection_id, "relation": "evaluates_connection"})
    nodes.append({"id": "decision", "type": "tier_decision", "label": gate["action"].replace("_", " ").title(), "data": gate})
    edges.append({"source": f"tier:{context['current_tier']}", "target": "decision", "relation": "results_in"})
    return {"nodes": nodes, "edges": edges}


def build_assessment_record(
    data: dict[str, Any],
    identity: dict[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    context = {
        "jurisdiction": data["jurisdiction"],
        "contaminant_group": data["contaminant_group"],
        "scenario": data["scenario"],
        "current_tier": int(data["current_tier"]),
        "maximum_tier": int(data["maximum_tier"]),
        "assessment_mode": data["assessment_mode"],
        "application_method": data.get("application_method"),
        "use_site_category": data.get("use_site_category"),
        "bee_attractive": bool(data.get("bee_attractive", False)),
    }
    tier_sequence = build_tier_sequence(context)
    risk_results = [characterise_risk(item) for item in data.get("risk_characterisations", [])]
    connection_results = [
        model_port_compatibility(
            item["source_model_key"],
            item["source_port_key"],
            item["target_model_key"],
            item["target_port_key"],
            value=item.get("value", 1.0),
            allow_draft_contracts=item.get("allow_draft_contracts", False),
        )
        for item in data.get("model_connections", [])
    ]
    data_gaps = list(data.get("data_gaps", []))
    gate = evaluate_tier_gate(
        current_tier=context["current_tier"],
        maximum_tier=context["maximum_tier"],
        uncertainty=data.get("uncertainty", "unknown"),
        data_gaps=data_gaps,
        risk_results=risk_results,
        connection_results=connection_results,
    )
    current_stage = next(stage for stage in tier_sequence if stage["tier"] == context["current_tier"])
    regulatory_status = classify_regulatory_status(
        context=context,
        current_models=current_stage["models"],
        model_results=data.get("model_results", []),
        data_gaps=data_gaps,
    )

    valid_risks = [
        result for result in risk_results
        if result.get("concern_triggered") is not None and result.get("decision_eligible", True)
    ]
    if any(result.get("concern_triggered") for result in valid_risks):
        conclusion_code = "potential_concern"
        conclusion_text = "At least one compatible risk metric triggers refinement or expert review."
    elif not valid_risks:
        conclusion_code = "cannot_conclude"
        conclusion_text = "No compatible risk characterisation is available; a final risk conclusion cannot be drawn."
    elif gate["action"] in {"advance", "expert_review", "resolve_incompatibility"}:
        conclusion_code = "provisional_below_trigger"
        conclusion_text = "Available metrics are below their triggers, but uncertainty, incompatibility or data gaps prevent closure."
    else:
        conclusion_code = "below_trigger_at_current_tier"
        conclusion_text = "Compatible metrics are below their current-tier triggers; competent review is still required before regulatory use."

    record = {
        "schema_version": ORCHESTRATION_VERSION,
        "risk_ruleset_version": RISK_RULESET_VERSION,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        "project_id": data.get("project_id"),
        "chemical_id": data.get("chemical_id"),
        "identity": identity,
        "context": context,
        "uncertainty": data.get("uncertainty", "unknown"),
        "data_gaps": data_gaps,
        "tier_sequence": tier_sequence,
        "current_tier_decision": gate,
        "model_results": list(data.get("model_results", [])),
        "model_connections": connection_results,
        "risk_characterisations": risk_results,
        "regulatory_status": regulatory_status,
        "overall_conclusion": {
            "code": conclusion_code,
            "text": conclusion_text,
            "final_regulatory_decision": False,
            "competent_person_review_required": True,
        },
    }
    record["graph"] = _assessment_graph(
        context=context,
        identity=identity,
        tier_sequence=tier_sequence,
        risk_results=risk_results,
        connection_results=connection_results,
        gate=gate,
    )
    record["record_hash"] = record_hash(record)
    return record


def orchestration_manifest() -> dict[str, Any]:
    return {
        "orchestration_version": ORCHESTRATION_VERSION,
        "risk_ruleset_version": RISK_RULESET_VERSION,
        "model_contract_schema_version": MODEL_CONTRACT_SCHEMA_VERSION,
        "assessment_modes": ["regulatory", "comparative", "hybrid"],
        "risk_metrics": RISK_METRICS,
        "canonical_units": sorted({definition[1] for definition in UNIT_DEFINITIONS.values()}),
        "scientific_boundaries": [
            "Unit conversion never repairs a compartment, phase, time, scale or substance-basis mismatch.",
            "A PEC/PNEC or pesticide RQ controls a tier gate only after both the exposure output and effect benchmark are provenance-verified.",
            "Cross-jurisdiction comparisons remain scientific refinements unless separately accepted by the receiving authority.",
            "No automatic final regulatory conclusion is produced.",
            "Untyped or draft model ports cannot be chained automatically.",
        ],
    }
