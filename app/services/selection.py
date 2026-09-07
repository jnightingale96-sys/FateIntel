from __future__ import annotations
import hashlib
import json
import math
from collections import defaultdict
from statistics import median
from ..models import EvidenceRecord

R = 8.314462618

def arrhenius_dt50(
    value_days: float,
    source_temperature_c: float,
    target_temperature_c: float,
    activation_energy_kj_mol: float,
) -> float:
    ts = source_temperature_c + 273.15
    tt = target_temperature_c + 273.15
    exponent = (activation_energy_kj_mol * 1000 / R) * ((1 / tt) - (1 / ts))
    return value_days * math.exp(exponent)

def geometric_mean(values: list[float]) -> float:
    if not values or any(v <= 0 for v in values):
        raise ValueError("Geometric mean requires positive values")
    return math.exp(sum(math.log(v) for v in values) / len(values))

def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)

def calculate_selection(
    evidence: list[EvidenceRecord],
    target_temperature_c: float,
    activation_energy_kj_mol: float,
    max_reliability_score: int,
) -> dict:
    members = []
    groups: dict[str, list[float]] = defaultdict(list)

    for record in evidence:
        reasons = []
        if record.property_code != "FATE.SOIL_DT50":
            reasons.append("Wrong property")
        if record.original_value <= 0:
            reasons.append("Non-positive value")
        if record.original_unit.lower() not in {"day", "days", "d"}:
            reasons.append("Unsupported unit")
        if not record.include_by_default:
            reasons.append("Marked excluded")
        if record.reliability_score is None:
            reasons.append("Reliability not assigned")
        elif record.reliability_score > max_reliability_score:
            reasons.append("Reliability exceeds threshold")
        if record.temperature_c is None:
            reasons.append("Temperature missing")
        if not record.representative_group_key:
            reasons.append("Independent soil/test-unit key missing")

        if reasons:
            members.append({
                "evidence_id": record.id,
                "decision": "excluded",
                "reason": "; ".join(reasons),
                "normalised_value_days": None,
                "representative_value_days": None,
                "transformations": [],
            })
            continue

        normalised = arrhenius_dt50(
            record.original_value,
            record.temperature_c,
            target_temperature_c,
            activation_energy_kj_mol,
        )
        groups[record.representative_group_key].append(normalised)
        members.append({
            "evidence_id": record.id,
            "decision": "included",
            "reason": "Eligible under pilot ruleset",
            "normalised_value_days": normalised,
            "representative_value_days": None,
            "group_key": record.representative_group_key,
            "transformations": [{
                "type": "arrhenius_temperature_normalisation",
                "source_temperature_c": record.temperature_c,
                "target_temperature_c": target_temperature_c,
                "activation_energy_kj_mol": activation_energy_kj_mol,
            }],
        })

    group_values = {
        group: geometric_mean(values)
        for group, values in groups.items()
    }

    for member in members:
        if member["decision"] == "included":
            member["representative_value_days"] = group_values[member["group_key"]]

    representative_values = list(group_values.values())
    if not representative_values:
        return {
            "selected_value_days": None,
            "members": members,
            "group_values": {},
            "statistics": {},
            "reason": "No eligible independent soil/test units remained.",
        }

    selected = geometric_mean(representative_values)
    stats = {
        "n_evidence_records": sum(1 for m in members if m["decision"] == "included"),
        "n_independent_groups": len(representative_values),
        "minimum_days": min(representative_values),
        "p10_days": percentile(representative_values, 0.10),
        "median_days": median(representative_values),
        "geometric_mean_days": selected,
        "p90_days": percentile(representative_values, 0.90),
        "maximum_days": max(representative_values),
        "fold_range": max(representative_values) / min(representative_values),
    }

    return {
        "selected_value_days": selected,
        "members": members,
        "group_values": group_values,
        "statistics": stats,
        "reason": (
            "Geometric mean across independent soil/test-unit representative values "
            "after Arrhenius normalisation."
        ),
    }

def evidence_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
