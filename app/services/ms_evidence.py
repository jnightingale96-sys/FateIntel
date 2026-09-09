"""Metabolite / transformation-product analytical evidence: mzML import and review.

Scope boundary (deliberate, not a placeholder). This module reads an mzML
file and surfaces exactly what the instrument already selected for MS/MS
fragmentation: each MS2 acquisition event, its own retention time, precursor
m/z, product-ion spectrum, and an extracted-ion chromatogram (XIC) computed
from the file's own MS1 scans. It does NOT perform:

- untargeted feature detection/alignment across files (OpenMS/MZmine/
  MS-DIAL's job -- a real algorithmic undertaking, not reimplemented here);
- molecular-formula assignment or structure elucidation (SIRIUS's job);
- any promotion to "confirmed structure" -- per the Schymanski confidence
  framework, that requires an authentic-standard comparison a human
  reviewer makes, which this module cannot and does not assert.

What it produces is the first rung of that ladder: a reviewable, evidence-
grade candidate list (feature/exact-mass of interest), not an identification.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any

import numpy as np
from pyteomics import mzml


MAX_FILE_BYTES = 500 * 1024 * 1024  # conservative first-slice import limit, not a batch-processing pipeline
DEFAULT_XIC_PPM_TOLERANCE = 10.0
MIN_XIC_TOLERANCE_DA = 0.005


class MzMLParseError(ValueError):
    pass


def sha256_of(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _rt_minutes(spectrum: dict[str, Any]) -> float | None:
    scans = ((spectrum.get("scanList") or {}).get("scan")) or []
    if not scans:
        return None
    rt = scans[0].get("scan start time")
    if rt is None:
        return None
    unit = str(getattr(rt, "unit_info", "") or "").lower()
    value = float(rt)
    if unit.startswith("second"):
        return value / 60.0
    return value


def _precursor_info(spectrum: dict[str, Any]) -> dict[str, Any] | None:
    precursors = ((spectrum.get("precursorList") or {}).get("precursor")) or []
    if not precursors:
        return None
    selected = ((precursors[0].get("selectedIonList") or {}).get("selectedIon")) or []
    if not selected:
        return None
    ion = selected[0]
    mz = ion.get("selected ion m/z")
    if mz is None:
        return None
    collision_energy = (precursors[0].get("activation") or {}).get("collision energy")
    charge = ion.get("charge state")
    return {
        "mz": float(mz),
        "charge": int(charge) if charge is not None else None,
        "collision_energy": float(collision_energy) if collision_energy is not None else None,
    }


def _extract_xic(
    ms1_scans: list[tuple[float, np.ndarray, np.ndarray]],
    target_mz: float,
    *,
    ppm_tolerance: float = DEFAULT_XIC_PPM_TOLERANCE,
) -> list[dict[str, float]]:
    """Sum MS1 intensity within a ppm window of target_mz at every MS1 scan.

    This is the standard extracted-ion-chromatogram definition -- one point
    per MS1 scan across the whole run -- not a smoothed or peak-picked curve.
    """
    tolerance_da = max(target_mz * ppm_tolerance / 1e6, MIN_XIC_TOLERANCE_DA)
    lower, upper = target_mz - tolerance_da, target_mz + tolerance_da
    points = []
    for rt, mz_array, intensity_array in ms1_scans:
        if mz_array.size == 0:
            points.append({"retention_time_min": round(rt, 4), "intensity": 0.0})
            continue
        mask = (mz_array >= lower) & (mz_array <= upper)
        points.append({"retention_time_min": round(rt, 4), "intensity": round(float(intensity_array[mask].sum()), 2)})
    return points


def parse_mzml(raw: bytes) -> dict[str, Any]:
    """Parse one mzML file into a file-level TIC plus a list of MS2 features.

    Single streaming pass. MS1 arrays are kept only long enough to build the
    file's TIC and each MS2 event's XIC, then this function returns without
    retaining them -- not persisted raw. Product-ion spectra are kept in
    full (typically tens to a few hundred peaks; not the memory concern
    whole-run MS1 data would be).
    """
    if len(raw) > MAX_FILE_BYTES:
        raise MzMLParseError(f"mzML file exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB import limit for this workbench")

    ms1_scans: list[tuple[float, np.ndarray, np.ndarray]] = []
    ms2_events: list[dict[str, Any]] = []
    positive_count = 0
    negative_count = 0

    try:
        with mzml.read(io.BytesIO(raw)) as reader:
            for spectrum in reader:
                rt = _rt_minutes(spectrum)
                if rt is None:
                    continue
                if "positive scan" in spectrum:
                    positive_count += 1
                elif "negative scan" in spectrum:
                    negative_count += 1
                mz_array = spectrum.get("m/z array")
                intensity_array = spectrum.get("intensity array")
                if mz_array is None or intensity_array is None:
                    continue
                level = spectrum.get("ms level")
                if level == 1:
                    ms1_scans.append((rt, np.asarray(mz_array, dtype=float), np.asarray(intensity_array, dtype=float)))
                elif level == 2:
                    precursor = _precursor_info(spectrum)
                    if precursor is None:
                        continue
                    intensity_array = np.asarray(intensity_array, dtype=float)
                    mz_array = np.asarray(mz_array, dtype=float)
                    order = np.argsort(intensity_array)[::-1]
                    product_ions = [
                        {"mz": round(float(mz_array[i]), 5), "intensity": round(float(intensity_array[i]), 2)}
                        for i in order
                    ]
                    ms2_events.append({
                        "retention_time_min": rt,
                        "precursor_mz": precursor["mz"],
                        "precursor_charge": precursor["charge"],
                        "collision_energy": precursor["collision_energy"],
                        "scan_id": spectrum.get("id"),
                        "product_ions": product_ions,
                    })
    except MzMLParseError:
        raise
    except Exception as exc:  # pyteomics raises its own error types on malformed input
        raise MzMLParseError(f"Could not parse this file as mzML: {exc}") from exc

    if not ms1_scans and not ms2_events:
        raise MzMLParseError("No MS1 or MS2 spectra were found in this file")

    ms1_scans.sort(key=lambda row: row[0])
    tic = [
        {"retention_time_min": round(rt, 4), "intensity": round(float(intensity.sum()), 2)}
        for rt, _, intensity in ms1_scans
    ]

    ionisation_mode = None
    if positive_count and not negative_count:
        ionisation_mode = "positive"
    elif negative_count and not positive_count:
        ionisation_mode = "negative"
    elif positive_count and negative_count:
        ionisation_mode = "mixed"

    ms2_events.sort(key=lambda row: row["retention_time_min"])
    for index, event in enumerate(ms2_events):
        event["feature_index"] = index
        event["xic"] = _extract_xic(ms1_scans, event["precursor_mz"])
        event["base_peak_mz"] = event["product_ions"][0]["mz"] if event["product_ions"] else None

    return {
        "ms1_scan_count": len(ms1_scans),
        "ms2_scan_count": len(ms2_events),
        "ionisation_mode": ionisation_mode,
        "tic": tic,
        "features": ms2_events,
    }


def workbench_capabilities() -> dict[str, Any]:
    """Describe this module's scope and boundary for the UI/API to surface honestly."""
    return {
        "provides": [
            "mzML import with content-hashed, immutable raw-file provenance",
            "every MS2 acquisition event as a reviewable candidate (retention time, precursor m/z, charge, collision energy)",
            "product-ion spectrum per candidate, sorted by intensity",
            "an extracted-ion chromatogram (XIC) per candidate from the file's own MS1 scans",
            "file-level total-ion chromatogram (TIC) for run overview",
        ],
        "does_not_provide": [
            "untargeted feature detection/alignment across multiple files (use OpenMS, MZmine or MS-DIAL upstream)",
            "molecular-formula assignment or structure elucidation (use SIRIUS or similar upstream)",
            "Thermo .RAW conversion (use ThermoRawFileParser or msconvert to produce mzML first)",
            "any 'confirmed structure' conclusion -- confirmation requires an authentic-standard MS/MS and retention-time match under the same method, which is a reviewer's judgement, never automatic",
        ],
        "confidence_framework": "Schymanski et al. (2014) five-level HRMS confidence scale",
        "accepted_formats": ["mzml"],
        "max_file_bytes": MAX_FILE_BYTES,
    }
