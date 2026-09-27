"""Predicted properties from a locally installed OPERA (NIEHS/NICEATM QSAR suite) command-line build.

OPERA is the structure-only fallback: when a substance has a SMILES but no measured or supplied properties, this module
asks OPERA for log P, pKa, biodegradation half-life and log Koc, each with OPERA's own applicability-domain (AD) verdict
and confidence index. Nothing here is a measurement; every value is labelled a prediction and carries its AD flag.

OPERA 2.9 is a MATLAB-compiled application. It is run as a subprocess with its bundled MATLAB Runtime prepended to
PATH **for that child process only** (nothing system-wide is changed).

**Descriptors are calculated by running PaDEL ourselves, not by OPERA's own ``-s``/SMILES-input mode.** Confirmed
2026-09-25 and again 2026-09-27 (a real 1,500-molecule batch, 6m19s, all 17 endpoints): OPERA's ``-s`` path calls
PaDEL internally and hangs indefinitely on this build ("Loaded structures: NaN. PaDEL calculating 2D descriptors..."
then nothing further, ever). The reliable path -- used here -- is to run PaDEL directly for 2D descriptors and for
fingerprints (both bundled next to ``OPERA.exe``: ``padel-full-1.00.jar``, ``desc_fp.xml``), align the two CSVs by
molecule name (PaDEL can drop a structure from one output and not the other), then call OPERA with ``-d``/``-fp``
(pre-calculated descriptors) instead of ``-s``. This needs a ``java`` executable on PATH.

One further one-time machine-level gotcha (not something this module manages): OPERA's MATLAB Runtime caches the
app's install folder in ``%LOCALAPPDATA%\\MathWorks\\MatlabRuntimeCache\\R2024b\\OPERA_installdir.txt``. If that
file's content does not match the real ``OPERA.exe`` folder (trailing backslash required), every call fails fast
with a clear "Default install folder was changed during installation" error -- fix that file's content once, by
hand; it is outside this module's control and is not a hang.

Configuration (all optional; the feature is simply unavailable when the executable is not configured):
  OPERA_EXE_PATH         full path to OPERA.exe (e.g. C:\\israel_opera\\app\\application\\OPERA.exe)
  OPERA_RUNTIME_DIR      MATLAB Runtime R2024b root; defaults to <exe folder>/../R2024b when present
  OPERA_ENABLED          set false to switch the fallback off
  OPERA_TIMEOUT_SECONDS  per-subprocess-call limit (PaDEL x2, OPERA x1), default 900

PaDEL's jar (``padel-full-1.00.jar``) and fingerprint descriptor-type file (``desc_fp.xml``) are expected next to
``OPERA.exe`` -- true of the standard OPERA 2.9 CLI distribution, which bundles its own PaDEL. ``java`` is resolved
from PATH.

Output columns used (OPERA 2.9, verified 2026-09-25 on carbamazepine, its epoxide and ethanol): ``LogP_pred``,
``pKa_a_pred``/``pKa_b_pred``, ``BioDeg_LogHalfLife_pred`` (log10 days), ``LogKoc_pred`` (log10 L/kg), each with a
``*Range`` ``[low:high]``, an ``AD_*`` flag (1 = inside the applicability domain), ``AD_index_*`` and ``Conf_index_*``.
The BioDeg half-life is a generic ready-biodegradation-style figure, NOT a soil DT50, and is only reported.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, NamedTuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import Settings, settings

OPERA_VERSION = "2.9"
SOURCE_LABEL = "OPERA 2.9 (NIEHS/NICEATM QSAR suite), predicted"
ENDPOINT_FLAGS = ("-logP", "-pKa", "-BioDeg", "-logKoc")
MAX_BATCH = 25
CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "opera_cache.json"
# PaDEL flags verified against the real 2026-09-27 run (align_and_run_opera.py): -removesalt/-standardizenitro/
# -detectaromaticity match OPERA's own expectations for these descriptors; -retainorder keeps row order == input
# order, so the "Name" column is exactly the ID we assign in the .smi file; -threads 1 avoids JVM thread contention
# for the small batches this module runs (<= MAX_BATCH molecules at a time).
PADEL_COMMON_FLAGS = ("-removesalt", "-standardizenitro", "-detectaromaticity", "-retainorder", "-threads", "1")
_RUN_LOCK = threading.Lock()
_CACHE_LOCK = threading.Lock()


class OperaUnavailableError(RuntimeError):
    """OPERA is not configured, disabled or not found on this machine."""


class OperaRunError(RuntimeError):
    """OPERA started but did not produce usable output."""


class OperaToolchain(NamedTuple):
    """Everything a real run needs: OPERA itself, its bundled PaDEL, and a java runtime to drive PaDEL."""

    opera_exe: Path
    runtime_dir: Path | None
    padel_jar: Path | None
    desc_fp_xml: Path | None
    java_exe: str | None


def _paths(configuration: Settings = settings) -> OperaToolchain:
    exe = getattr(configuration, "opera_exe_path", None)
    if not exe:
        raise OperaUnavailableError("OPERA is not configured: set OPERA_EXE_PATH to the OPERA.exe location.")
    exe_path = Path(exe)
    if not exe_path.is_file():
        raise OperaUnavailableError(f"OPERA_EXE_PATH does not point to a file: {exe_path}")
    runtime = getattr(configuration, "opera_runtime_dir", None)
    runtime_path = Path(runtime) if runtime else exe_path.parent.parent / "R2024b"
    padel_jar = exe_path.parent / "padel-full-1.00.jar"
    desc_fp_xml = exe_path.parent / "desc_fp.xml"
    java_exe = shutil.which("java")
    if not padel_jar.is_file():
        raise OperaUnavailableError(
            f"OPERA's bundled PaDEL jar was not found next to OPERA.exe: {padel_jar}. "
            "This module runs PaDEL itself (OPERA's own -s/SMILES mode hangs) and needs it there."
        )
    if not desc_fp_xml.is_file():
        raise OperaUnavailableError(f"OPERA's bundled PaDEL fingerprint descriptor file was not found: {desc_fp_xml}.")
    if not java_exe:
        raise OperaUnavailableError("No 'java' executable found on PATH: it is needed to run PaDEL for OPERA's descriptors.")
    return OperaToolchain(exe_path, runtime_path if runtime_path.is_dir() else None, padel_jar, desc_fp_xml, java_exe)


def capabilities(configuration: Settings = settings) -> dict[str, Any]:
    enabled = bool(getattr(configuration, "opera_enabled", True))
    try:
        toolchain = _paths(configuration)
        found, reason = True, None
    except OperaUnavailableError as exc:
        toolchain, found, reason = None, False, str(exc)
    return {
        "provider": "opera", "version": OPERA_VERSION, "enabled": enabled, "executable_found": found,
        "available": bool(enabled and found), "executable": str(toolchain.opera_exe) if toolchain else None,
        "bundled_matlab_runtime": str(toolchain.runtime_dir) if toolchain and toolchain.runtime_dir else None,
        "padel_jar": str(toolchain.padel_jar) if toolchain else None,
        "java_executable": toolchain.java_exe if toolchain else None,
        "reason": "disabled by configuration" if not enabled else reason,
        "endpoints": ["logP", "pKa", "BioDeg", "logKoc"], "typical_seconds_per_batch": 35,
        "note": (
            "Predictions only, each with OPERA's applicability-domain flag; measured values always take precedence. "
            "Descriptors are computed by running PaDEL directly, then handed to OPERA with -d/-fp (OPERA's own "
            "-s/SMILES mode hangs on this build)."
        ),
    }


# --------------------------------------------------------------------------------------------------- parsing
def _number(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _range(value: Any) -> list[float] | None:
    text = str(value or "").strip()
    if not (text.startswith("[") and text.endswith("]") and ":" in text):
        return None
    low, _, high = text[1:-1].partition(":")
    low_n, high_n = _number(low), _number(high)
    return [low_n, high_n] if low_n is not None and high_n is not None else None


def _block(row: dict[str, str], value_col: str, range_col: str, ad_col: str, ad_index_col: str, conf_col: str) -> dict[str, Any] | None:
    value = _number(row.get(value_col))
    if value is None:
        return None
    ad = _number(row.get(ad_col))
    return {
        "value": value, "range": _range(row.get(range_col)),
        "applicability_domain": None if ad is None else ("inside" if ad >= 1 else "outside"),
        "ad_index": _number(row.get(ad_index_col)), "confidence_index": _number(row.get(conf_col)),
    }


def parse_output_row(row: dict[str, str]) -> dict[str, Any]:
    """One OPERA CSV row -> the record this module returns (missing endpoints are None, never guessed)."""

    biodeg = _block(row, "BioDeg_LogHalfLife_pred", "BioDeg_predRange", "AD_BioDeg", "AD_index_BioDeg", "Conf_index_BioDeg")
    if biodeg is not None:
        biodeg = {**biodeg, "log10_days": biodeg["value"], "value": 10.0 ** biodeg["value"], "unit": "days",
                  "range": [10.0 ** x for x in biodeg["range"]] if biodeg["range"] else None}
    logkoc = _block(row, "LogKoc_pred", "Koc_predRange", "AD_Koc", "AD_index_Koc", "Conf_index_Koc")
    pka_ad = ("AD_pKa", "AD_index_pKa", "Conf_index_pKa")
    return {
        "source": SOURCE_LABEL,
        "logp": _block(row, "LogP_pred", "LogP_predRange", "AD_LogP", "AD_index_LogP", "Conf_index_LogP"),
        "pka_a": _block(row, "pKa_a_pred", "pKa_a_predRange", *pka_ad),
        "pka_b": _block(row, "pKa_b_pred", "pKa_b_predRange", *pka_ad),
        "biodeg_half_life": biodeg,
        "logkoc": logkoc,
    }


# --------------------------------------------------------------------------------------------------- cache
def _canonical(smiles: str) -> str | None:
    try:
        from rdkit import Chem
    except ImportError:  # pragma: no cover - rdkit is a project dependency
        return smiles.strip() or None
    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToSmiles(mol) if mol is not None else None


def _load_cache(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("version") == OPERA_VERSION else {"version": OPERA_VERSION, "records": {}}
    except (OSError, ValueError):
        return {"version": OPERA_VERSION, "records": {}}


def _save_cache(path: Path, cache: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass  # a cache that cannot be written just costs time next run


# --------------------------------------------------------------------------------------------------- running
def _matlab_env(runtime: Path | None) -> dict[str, str]:
    env = dict(os.environ)
    if runtime is not None:  # the bundled MATLAB Runtime, for this child process only
        env["PATH"] = os.pathsep.join([str(runtime / "runtime" / "win64"), str(runtime / "bin" / "win64"), str(runtime / "extern" / "bin" / "win64"), env.get("PATH", "")])
    return env


def _run_padel(java_exe: str, jar: Path, desc_fp_xml: Path, smi_file: Path, out_csv: Path, *, fingerprints: bool, timeout: float) -> None:
    """Runs OPERA's own bundled PaDEL directly (see module docstring for why: OPERA's ``-s`` mode hangs)."""

    mode_flags = ["-fingerprints", "-descriptortypes", str(desc_fp_xml)] if fingerprints else ["-2d"]
    command = [java_exe, "-jar", str(jar), *mode_flags, *PADEL_COMMON_FLAGS, "-dir", str(smi_file), "-file", str(out_csv)]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    label = "fingerprints" if fingerprints else "2D descriptors"
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, creationflags=flags)
    except subprocess.TimeoutExpired as exc:
        raise OperaRunError(f"PaDEL ({label}) did not finish within {timeout:g} s.") from exc
    except OSError as exc:
        raise OperaRunError(f"PaDEL ({label}) could not be started: {exc}") from exc
    if not out_csv.is_file() or out_csv.stat().st_size == 0:
        detail = (completed.stdout or completed.stderr or "").strip().splitlines()[-5:]
        raise OperaRunError(f"PaDEL ({label}) produced no output (exit {completed.returncode}). {' '.join(detail)}".strip())


def _align_by_name(csv_2d: Path, csv_fp: Path, aligned_2d: Path, aligned_fp: Path, order: list[str]) -> list[str]:
    """Inner-joins the two PaDEL outputs on their ``Name`` column (PaDEL can drop a structure from one output and
    not the other), preserving ``order`` (our own assigned molecule IDs) wherever both sides have that name."""

    def _read(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
        with path.open(encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            return fieldnames, {row.get("Name", ""): row for row in reader}

    fields_2d, rows_2d = _read(csv_2d)
    fields_fp, rows_fp = _read(csv_fp)
    common = [name for name in order if name in rows_2d and name in rows_fp]
    with aligned_2d.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields_2d)
        writer.writeheader()
        writer.writerows(rows_2d[name] for name in common)
    with aligned_fp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields_fp)
        writer.writeheader()
        writer.writerows(rows_fp[name] for name in common)
    return common


def _run_opera(canonical: list[str], configuration: Settings) -> dict[str, dict[str, Any]]:
    toolchain = _paths(configuration)
    timeout = float(getattr(configuration, "opera_timeout_seconds", 900) or 900)
    ids = [f"m{index}" for index in range(len(canonical))]
    with tempfile.TemporaryDirectory(prefix="opera_") as folder:
        work = Path(folder)
        smi_file = work / "in.smi"
        smi_file.write_text("".join(f"{smiles}\t{mol_id}\n" for smiles, mol_id in zip(canonical, ids)), encoding="ascii", errors="replace")

        desc_2d, desc_fp = work / "desc_2d.csv", work / "desc_fp.csv"
        _run_padel(toolchain.java_exe, toolchain.padel_jar, toolchain.desc_fp_xml, smi_file, desc_2d, fingerprints=False, timeout=timeout)
        _run_padel(toolchain.java_exe, toolchain.padel_jar, toolchain.desc_fp_xml, smi_file, desc_fp, fingerprints=True, timeout=timeout)

        aligned_2d, aligned_fp = work / "desc_2d_aligned.csv", work / "desc_fp_aligned.csv"
        matched_ids = _align_by_name(desc_2d, desc_fp, aligned_2d, aligned_fp, ids)
        if not matched_ids:
            raise OperaRunError("PaDEL produced no structure common to both the 2D-descriptor and fingerprint outputs.")

        out_file = work / "out.csv"
        command = [str(toolchain.opera_exe), "-d", str(aligned_2d), "-fp", str(aligned_fp), "-o", str(out_file), *ENDPOINT_FLAGS, "-v", "0"]
        env = _matlab_env(toolchain.runtime_dir)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            with _RUN_LOCK:
                completed = subprocess.run(command, cwd=str(work), env=env, capture_output=True, text=True, timeout=timeout, creationflags=flags)
        except subprocess.TimeoutExpired as exc:
            raise OperaRunError(f"OPERA did not finish within {timeout:g} s.") from exc
        except OSError as exc:
            raise OperaRunError(f"OPERA could not be started: {exc}") from exc
        if completed.returncode != 0 or not out_file.is_file():
            detail = (completed.stdout or completed.stderr or "").strip().splitlines()[-5:]
            raise OperaRunError(f"OPERA exited with code {completed.returncode} and no output file. {' '.join(detail)}".strip())
        with out_file.open(encoding="utf-8", errors="replace", newline="") as handle:
            rows = {row.get("MoleculeID", ""): row for row in csv.DictReader(handle)}
    results: dict[str, dict[str, Any]] = {}
    for smiles, mol_id in zip(canonical, ids):
        row = rows.get(mol_id)
        if row is not None:
            results[smiles] = parse_output_row(row)
    return results


def predict(smiles_list: list[str], configuration: Settings = settings, *, cache_path: Path | None = None) -> dict[str, dict[str, Any] | None]:
    """Predictions keyed by the SMILES as given (None for a structure that cannot be parsed or predicted)."""

    if not getattr(configuration, "opera_enabled", True):
        raise OperaUnavailableError("OPERA is disabled by configuration (OPERA_ENABLED=false).")
    _paths(configuration)  # fail early and clearly when it is not configured
    cache_file = cache_path or CACHE_PATH
    canonical = {smiles: _canonical(smiles) for smiles in dict.fromkeys(smiles_list)}
    with _CACHE_LOCK:
        cache = _load_cache(cache_file)
    missing = sorted({c for c in canonical.values() if c and c not in cache["records"]})
    if missing:
        fresh = _run_opera(missing, configuration)
        with _CACHE_LOCK:
            cache = _load_cache(cache_file)
            cache["records"].update({smiles: record for smiles, record in fresh.items()})
            _save_cache(cache_file, cache)
    return {smiles: (cache["records"].get(c) if c else None) for smiles, c in canonical.items()}


# --------------------------------------------------------------------------------------------------- API
router = APIRouter(prefix="/opera", tags=["predicted-properties"])


class OperaPredictRequest(BaseModel):
    smiles: list[str] = Field(min_length=1, max_length=MAX_BATCH)


@router.get("/capabilities")
def get_capabilities() -> dict[str, Any]:
    return capabilities()


@router.post("/predict")
def post_predict(request: OperaPredictRequest) -> dict[str, Any]:
    try:
        results = predict(request.smiles)
    except OperaUnavailableError as exc:
        raise HTTPException(503, str(exc)) from exc
    except OperaRunError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"source": SOURCE_LABEL, "results": [{"smiles": s, "prediction": r} for s, r in results.items()]}
