from __future__ import annotations

import math
from collections import Counter, deque
from typing import Any


MODEL_KEY = "ENVIROCHEM_CATCHMENT_RIVER_NETWORK"
MODEL_VERSION = "1.0.0"


def _effluent_load_kg_day(concentration_ug_l: float, flow_m3_day: float) -> float:
    return concentration_ug_l * flow_m3_day * 1.0e-6


def _concentration_ug_l(load_kg_day: float, flow_m3_day: float) -> float:
    return load_kg_day * 1.0e6 / flow_m3_day


def _topological_order(segments: list[dict[str, Any]]) -> tuple[list[str], dict[str, list[str]]]:
    keys = [str(segment["segment_id"]) for segment in segments]
    if len(keys) != len(set(keys)):
        raise ValueError("River segment identifiers must be unique")
    known = set(keys)
    upstream_map: dict[str, list[str]] = {}
    children: dict[str, list[str]] = {key: [] for key in keys}
    indegree: dict[str, int] = {}
    references: list[str] = []

    for segment in segments:
        key = str(segment["segment_id"])
        upstream = [str(value) for value in segment.get("upstream_ids") or []]
        if key in upstream:
            raise ValueError(f"River segment {key} cannot be upstream of itself")
        unknown = sorted(set(upstream) - known)
        if unknown:
            raise ValueError(f"River segment {key} references unknown upstream segments: {', '.join(unknown)}")
        if len(upstream) != len(set(upstream)):
            raise ValueError(f"River segment {key} contains duplicate upstream references")
        upstream_map[key] = upstream
        indegree[key] = len(upstream)
        for parent in upstream:
            children[parent].append(key)
            references.append(parent)

    duplicated_routes = sorted(key for key, count in Counter(references).items() if count > 1)
    if duplicated_routes:
        raise ValueError(
            "A segment cannot discharge into more than one downstream segment without an explicit flow split: "
            + ", ".join(duplicated_routes)
        )

    queue = deque(key for key in keys if indegree[key] == 0)
    order: list[str] = []
    while queue:
        key = queue.popleft()
        order.append(key)
        for child in children[key]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(keys):
        raise ValueError("River network contains a cycle")
    return order, children


def run_catchment_river_network(data: dict[str, Any]) -> dict[str, Any]:
    """Route point-source loads through an auditable directed river network."""

    segments = data.get("segments") or []
    if not segments:
        raise ValueError("At least one river segment is required")
    order, children = _topological_order(segments)
    by_key = {str(segment["segment_id"]): segment for segment in segments}

    default_dt50 = data.get("default_water_dt50_days")
    if default_dt50 is not None and float(default_dt50) <= 0:
        raise ValueError("The default water DT50 must be positive")
    pnec = data.get("aquatic_pnec_ug_l")
    if pnec is not None and float(pnec) <= 0:
        raise ValueError("The aquatic PNEC must be positive")

    routed_output: dict[str, float] = {}
    results: list[dict[str, Any]] = []
    total_local_input = 0.0
    total_loss = 0.0
    flow_warnings: list[str] = []

    for key in order:
        segment = by_key[key]
        flow = float(segment["flow_m3_day"])
        travel_time = float(segment["travel_time_days"])
        if flow <= 0 or travel_time < 0:
            raise ValueError("Segment flow must be positive and travel time cannot be negative")

        half_life = segment.get("water_dt50_days")
        if half_life is None:
            half_life = default_dt50
        if half_life is None or float(half_life) <= 0:
            raise ValueError(f"A positive water DT50 is required for river segment {key}")
        other_loss = float(segment.get("other_loss_rate_per_day", 0.0))
        if other_loss < 0:
            raise ValueError("Other loss rates cannot be negative")
        rate = math.log(2.0) / float(half_life) + other_loss

        local_direct = float(segment.get("local_load_kg_day", 0.0))
        effluent_concentration = float(segment.get("local_effluent_concentration_ug_l", 0.0))
        effluent_flow = float(segment.get("local_effluent_flow_m3_day", 0.0))
        if min(local_direct, effluent_concentration, effluent_flow) < 0:
            raise ValueError("Local loads, effluent concentrations and effluent flows cannot be negative")
        local_effluent = _effluent_load_kg_day(effluent_concentration, effluent_flow)
        local_input = local_direct + local_effluent
        upstream_input = sum(routed_output[parent] for parent in segment.get("upstream_ids") or [])
        inlet_load = upstream_input + local_input

        upstream_flow_sum = sum(float(by_key[parent]["flow_m3_day"]) for parent in segment.get("upstream_ids") or [])
        if upstream_flow_sum > flow * (1.0 + 1.0e-9):
            flow_warnings.append(
                f"Segment {key} flow is lower than the sum of its upstream flows; concentrations use the supplied segment flow."
            )
        known_inflow = upstream_flow_sum + effluent_flow
        if known_inflow > 0 and flow > known_inflow * 10.0:
            flow_warnings.append(
                f"Segment {key} flow is more than 10 times its known upstream plus local-effluent flow "
                f"({flow / known_inflow:.3g}x); confirm flow units or document tributary/baseflow inputs."
            )
        if effluent_flow > flow * (1.0 + 1.0e-9):
            flow_warnings.append(f"Segment {key} effluent flow exceeds the supplied total river flow.")

        attenuation = math.exp(-rate * travel_time)
        outlet_load = inlet_load * attenuation
        loss = inlet_load - outlet_load
        if rate * travel_time > 1.0e-12:
            mean_load = inlet_load * (1.0 - attenuation) / (rate * travel_time)
        else:
            mean_load = inlet_load

        inlet_concentration = _concentration_ug_l(inlet_load, flow)
        outlet_concentration = _concentration_ug_l(outlet_load, flow)
        mean_concentration = _concentration_ug_l(mean_load, flow)
        result = {
            "segment_id": key,
            "upstream_ids": list(segment.get("upstream_ids") or []),
            "flow_m3_day": flow,
            "travel_time_days": travel_time,
            "local_direct_load_kg_day": local_direct,
            "local_effluent_load_kg_day": local_effluent,
            "upstream_load_kg_day": upstream_input,
            "inlet_load_kg_day": inlet_load,
            "outlet_load_kg_day": outlet_load,
            "transformation_and_sink_loss_kg_day": loss,
            "inlet_concentration_ug_l": inlet_concentration,
            "mean_concentration_ug_l": mean_concentration,
            "outlet_concentration_ug_l": outlet_concentration,
            "combined_loss_rate_per_day": rate,
            "attenuation_fraction": attenuation,
            "risk_quotient_mean": mean_concentration / float(pnec) if pnec is not None else None,
        }
        results.append(result)
        routed_output[key] = outlet_load
        total_local_input += local_input
        total_loss += loss

    terminal_keys = [key for key in order if not children[key]]
    terminal_output = sum(routed_output[key] for key in terminal_keys)
    closure_error = total_local_input - total_loss - terminal_output
    peak_result = max(results, key=lambda row: row["mean_concentration_ug_l"])
    exceedance_segments = []
    if pnec is not None:
        exceedance_segments = [
            row["segment_id"] for row in results if row["mean_concentration_ug_l"] > float(pnec)
        ]

    warnings = [
        "This is a transparent native catchment screen, not an execution of GREAT-ER or ePiE.",
        "The model represents first-order in-stream attenuation and point-source loading; hydrodynamic dispersion, time-varying flow and sediment exchange require refinement.",
        *flow_warnings,
    ]
    if abs(closure_error) > max(1.0e-12, total_local_input * 1.0e-9):
        warnings.append("Network mass-balance closure exceeded the preferred tolerance.")

    return {
        "model_key": MODEL_KEY,
        "model_version": MODEL_VERSION,
        "calculation_type": "steady_state_directed_river_network",
        "segments": results,
        "network_summary": {
            "segment_count": len(results),
            "terminal_segments": terminal_keys,
            "total_local_input_kg_day": total_local_input,
            "total_transformation_and_sink_loss_kg_day": total_loss,
            "terminal_output_kg_day": terminal_output,
            "mass_balance_error_kg_day": closure_error,
            "peak_mean_concentration_ug_l": peak_result["mean_concentration_ug_l"],
            "peak_segment_id": peak_result["segment_id"],
            "segments_above_pnec": exceedance_segments,
        },
        "official_model_readiness": {
            "greater_adapter_available": True,
            "epie_adapter_available": True,
            "required_refinement": "Supply reviewed river geometry, hydrology, georeferenced WWTP loads and model-specific fate inputs before an official or high-resolution workflow is represented as executed.",
        },
        "warnings": warnings,
    }
