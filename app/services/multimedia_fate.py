from __future__ import annotations

import math
from typing import Any

import numpy as np


MODEL_KEY = "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN"
MODEL_VERSION = "1.0.0"
SUPPORTED_MEDIA = {"air", "freshwater", "soil", "sediment"}


def _degradation_rate(half_life_days: float | None) -> float:
    if half_life_days is None:
        return 0.0
    if half_life_days <= 0:
        raise ValueError("Half-lives must be positive when supplied")
    return math.log(2.0) / half_life_days


def _reported_concentration(medium: str, mass_kg: float, compartment: dict[str, Any]) -> tuple[float, str]:
    volume_m3 = float(compartment["volume_m3"])
    if medium == "air":
        return mass_kg * 1.0e9 / volume_m3, "ug/m3"
    if medium == "freshwater":
        return mass_kg * 1.0e6 / volume_m3, "ug/L"
    density = compartment.get("bulk_density_kg_m3")
    if density is None or float(density) <= 0:
        raise ValueError(f"bulk_density_kg_m3 is required for {medium}")
    return mass_kg * 1.0e9 / (volume_m3 * float(density)), "ug/kg"


def run_multimedia_fate_screen(data: dict[str, Any]) -> dict[str, Any]:
    """Solve a transparent steady-state multimedia mass balance.

    The model accepts reviewed first-order intermedia transfer coefficients.
    It deliberately does not claim to reproduce the SimpleBox fugacity and
    landscape parameterisation.  The matrix form is useful as a fully
    auditable Tier 1-2 screen and as an input-readiness check for SimpleBox.
    """

    compartments = data.get("compartments") or []
    if len(compartments) < 2:
        raise ValueError("At least two environmental compartments are required")

    keys = [str(item["key"]) for item in compartments]
    if len(keys) != len(set(keys)):
        raise ValueError("Compartment keys must be unique")
    unsupported = sorted(set(keys) - SUPPORTED_MEDIA)
    if unsupported:
        raise ValueError(f"Unsupported compartments: {', '.join(unsupported)}")
    for item in compartments:
        if float(item["volume_m3"]) <= 0:
            raise ValueError("Compartment volumes must be positive")
        if float(item.get("advective_loss_per_day", 0.0)) < 0:
            raise ValueError("Advective loss rates cannot be negative")

    index = {key: position for position, key in enumerate(keys)}
    n_compartments = len(keys)
    matrix = np.zeros((n_compartments, n_compartments), dtype=float)
    emissions = np.zeros(n_compartments, dtype=float)
    degradation_rates = np.zeros(n_compartments, dtype=float)
    advective_rates = np.zeros(n_compartments, dtype=float)
    outgoing_transfer_rates = np.zeros(n_compartments, dtype=float)

    supplied_emissions = data.get("emissions_kg_day") or {}
    unknown_emissions = sorted(set(supplied_emissions) - set(keys))
    if unknown_emissions:
        raise ValueError(f"Emissions reference unknown compartments: {', '.join(unknown_emissions)}")
    for key, value in supplied_emissions.items():
        if float(value) < 0:
            raise ValueError("Emission rates cannot be negative")
        emissions[index[key]] = float(value)
    if float(emissions.sum()) <= 0:
        raise ValueError("At least one positive emission rate is required")

    for item in compartments:
        position = index[item["key"]]
        degradation_rates[position] = _degradation_rate(item.get("half_life_days"))
        advective_rates[position] = float(item.get("advective_loss_per_day", 0.0))

    transfer_rows: list[dict[str, Any]] = []
    seen_transfers: set[tuple[str, str]] = set()
    for transfer in data.get("transfers") or []:
        source = str(transfer["source"])
        target = str(transfer["target"])
        rate = float(transfer["rate_per_day"])
        if source not in index or target not in index:
            raise ValueError("Every transfer source and target must be a registered compartment")
        if source == target:
            raise ValueError("Intermedia transfers require different source and target compartments")
        if rate < 0:
            raise ValueError("Intermedia transfer rates cannot be negative")
        pair = (source, target)
        if pair in seen_transfers:
            raise ValueError(f"Duplicate intermedia transfer: {source} -> {target}")
        seen_transfers.add(pair)
        source_position = index[source]
        target_position = index[target]
        outgoing_transfer_rates[source_position] += rate
        matrix[target_position, source_position] -= rate
        transfer_rows.append({"source": source, "target": target, "rate_per_day": rate})

    for position in range(n_compartments):
        matrix[position, position] += (
            degradation_rates[position]
            + advective_rates[position]
            + outgoing_transfer_rates[position]
        )

    try:
        condition_number = float(np.linalg.cond(matrix))
        if not math.isfinite(condition_number) or condition_number > 1.0e12:
            raise ValueError("The steady-state system is singular or insufficiently constrained by terminal losses")
        masses = np.linalg.solve(matrix, emissions)
    except np.linalg.LinAlgError as exc:
        raise ValueError("The steady-state system cannot be solved; add degradation or advective loss") from exc

    if np.any(masses < -1.0e-10):
        raise ValueError("The supplied transfer system produced a non-physical negative mass")
    masses = np.maximum(masses, 0.0)

    compartment_results: list[dict[str, Any]] = []
    degradation_total = 0.0
    advective_total = 0.0
    for item in compartments:
        key = str(item["key"])
        position = index[key]
        mass_kg = float(masses[position])
        concentration, unit = _reported_concentration(key, mass_kg, item)
        degraded_kg_day = mass_kg * degradation_rates[position]
        advected_kg_day = mass_kg * advective_rates[position]
        degradation_total += degraded_kg_day
        advective_total += advected_kg_day
        compartment_results.append({
            "key": key,
            "mass_kg": mass_kg,
            "concentration": concentration,
            "concentration_unit": unit,
            "degradation_loss_kg_day": degraded_kg_day,
            "advective_loss_kg_day": advected_kg_day,
            "degradation_rate_per_day": float(degradation_rates[position]),
            "advective_loss_per_day": float(advective_rates[position]),
        })

    transfer_fluxes = []
    for transfer in transfer_rows:
        flux = float(masses[index[transfer["source"]]]) * transfer["rate_per_day"]
        transfer_fluxes.append({**transfer, "flux_kg_day": flux})

    input_total = float(emissions.sum())
    terminal_loss = degradation_total + advective_total
    balance_error = input_total - terminal_loss
    balance_relative = balance_error / input_total
    warnings = [
        "This native screen solves a user-parameterised first-order multimedia mass balance; it is not an execution of SimpleBox 4.0 or EUSES.",
        "Intermedia transfer rates require reviewed evidence or a documented estimation method and must not be silently inferred from logKow alone.",
    ]
    if condition_number > 1.0e8:
        warnings.append("The transfer matrix is poorly conditioned; interpret individual compartment concentrations cautiously.")
    if abs(balance_relative) > 1.0e-8:
        warnings.append("Numerical mass-balance closure exceeded the preferred tolerance.")

    return {
        "model_key": MODEL_KEY,
        "model_version": MODEL_VERSION,
        "calculation_type": "steady_state_linear_multimedia_mass_balance",
        "compartments": compartment_results,
        "intermedia_fluxes": transfer_fluxes,
        "mass_balance": {
            "emission_input_kg_day": input_total,
            "degradation_loss_kg_day": degradation_total,
            "advective_loss_kg_day": advective_total,
            "closure_error_kg_day": balance_error,
            "relative_closure_error": balance_relative,
        },
        "matrix_condition_number": condition_number,
        "official_model_readiness": {
            "simplebox_adapter_available": True,
            "required_refinement": "Translate emissions, landscape settings, partition data and degradation evidence into a versioned official SimpleBox workflow.",
        },
        "warnings": warnings,
    }
