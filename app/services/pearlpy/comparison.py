from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import csv
import json
from typing import Iterable

import numpy as np

from .types import SimulationResult, SoilProfile


@dataclass(frozen=True)
class VariableMetrics:
    count: int
    mean_bias: float
    mean_absolute_error: float
    root_mean_square_error: float
    max_absolute_error: float
    median_absolute_percentage_error: float
    pearson_r: float | None


@dataclass(frozen=True)
class ComparisonReport:
    mass: VariableMetrics | None
    liquid_concentration: VariableMetrics | None
    matched_rows: int
    unmatched_reference_rows: int

    def to_dict(self) -> dict:
        return {
            "mass": asdict(self.mass) if self.mass else None,
            "liquid_concentration": (
                asdict(self.liquid_concentration)
                if self.liquid_concentration
                else None
            ),
            "matched_rows": self.matched_rows,
            "unmatched_reference_rows": self.unmatched_reference_rows,
        }

    def write_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target


def _metrics(reference: np.ndarray, predicted: np.ndarray) -> VariableMetrics:
    mask = np.isfinite(reference) & np.isfinite(predicted)
    ref = reference[mask]
    pred = predicted[mask]
    if ref.size == 0:
        raise ValueError("No finite paired data for comparison")

    error = pred - ref
    abs_error = np.abs(error)
    nonzero = np.abs(ref) > 1e-30
    mdape = (
        float(np.median(abs_error[nonzero] / np.abs(ref[nonzero])) * 100.0)
        if np.any(nonzero)
        else float("nan")
    )
    pearson = None
    if ref.size > 1 and np.std(ref) > 0 and np.std(pred) > 0:
        pearson = float(np.corrcoef(ref, pred)[0, 1])

    return VariableMetrics(
        count=int(ref.size),
        mean_bias=float(np.mean(error)),
        mean_absolute_error=float(np.mean(abs_error)),
        root_mean_square_error=float(np.sqrt(np.mean(error**2))),
        max_absolute_error=float(np.max(abs_error)),
        median_absolute_percentage_error=mdape,
        pearson_r=pearson,
    )


def export_normalized_result_csv(
    result: SimulationResult,
    soil: SoilProfile,
    path: str | Path,
) -> Path:
    """
    Export PEARLpy output in the long reference format used for comparisons.

    Required comparison columns:
      time_d, layer, depth_m, mass_kg_m2, liquid_concentration_kg_m3
    """
    target = Path(path)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "time_d",
                "layer",
                "depth_m",
                "mass_kg_m2",
                "liquid_concentration_kg_m3",
            ]
        )
        for ti, time_d in enumerate(result.time_d):
            for layer in range(soil.n_layers):
                writer.writerow(
                    [
                        float(time_d),
                        layer + 1,
                        float(soil.centre_depth_m[layer]),
                        float(result.layer_mass_kg_m2[ti, layer]),
                        float(result.liquid_concentration_kg_m3[ti, layer]),
                    ]
                )
    return target


def compare_result_to_reference_csv(
    result: SimulationResult,
    soil: SoilProfile,
    reference_csv: str | Path,
    *,
    time_shift_d: float = 0.0,
    time_tolerance_d: float = 1e-6,
    depth_tolerance_m: float = 1e-6,
) -> ComparisonReport:
    """
    Compare PEARLpy to a normalized official/reference CSV.

    `time_shift_d` is useful because the FOCUSPEARL manual states that detailed
    output time is written at the middle of the print interval.
    """
    source = Path(reference_csv)
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    predicted_times = result.time_d + time_shift_d
    predicted_depths = soil.centre_depth_m

    mass_ref: list[float] = []
    mass_pred: list[float] = []
    conc_ref: list[float] = []
    conc_pred: list[float] = []
    unmatched = 0

    for row in rows:
        time = float(row["time_d"])
        depth = float(row["depth_m"])

        t_idx = int(np.argmin(np.abs(predicted_times - time)))
        z_idx = int(np.argmin(np.abs(predicted_depths - depth)))

        if (
            abs(predicted_times[t_idx] - time) > time_tolerance_d
            or abs(predicted_depths[z_idx] - depth) > depth_tolerance_m
        ):
            unmatched += 1
            continue

        mass_value = row.get("mass_kg_m2", "")
        if mass_value not in {"", None}:
            mass_ref.append(float(mass_value))
            mass_pred.append(float(result.layer_mass_kg_m2[t_idx, z_idx]))

        concentration_value = row.get("liquid_concentration_kg_m3", "")
        if concentration_value not in {"", None}:
            conc_ref.append(float(concentration_value))
            conc_pred.append(
                float(result.liquid_concentration_kg_m3[t_idx, z_idx])
            )

    matched = len(rows) - unmatched
    return ComparisonReport(
        mass=(
            _metrics(np.asarray(mass_ref), np.asarray(mass_pred))
            if mass_ref
            else None
        ),
        liquid_concentration=(
            _metrics(np.asarray(conc_ref), np.asarray(conc_pred))
            if conc_ref
            else None
        ),
        matched_rows=matched,
        unmatched_reference_rows=unmatched,
    )
