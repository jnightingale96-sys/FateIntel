from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import csv
import re
import shlex
import subprocess
from typing import Iterable, Sequence

import numpy as np

from .types import HydrologySeries, SoilProfile


_DEPTH_COLUMN = re.compile(
    r"^(?P<name>WC|Q|RWU|T)\s*(?:\[|\(|_)?\s*(?P<value>-?\d+(?:\.\d+)?)\s*(?:\]|\))?$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class SwapImportMetadata:
    """Metadata retained when importing SWAP user-defined CSV output."""

    dates: tuple[date, ...]
    interval_days: float
    water_content_columns: tuple[str, ...]
    flux_columns: tuple[str, ...]
    root_uptake_columns: tuple[str, ...]
    temperature_columns: tuple[str, ...]
    bottom_flux_column: str
    state_sampling: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SwapImportResult:
    hydrology: HydrologySeries
    metadata: SwapImportMetadata


@dataclass(frozen=True)
class SwapRunResult:
    returncode: int
    stdout: str
    stderr: str
    log_path: Path | None
    output_csv_path: Path | None


def build_swap_csv_output_block(
    n_layers: int,
    *,
    output_interval_days: float = 1.0,
    include_pressure_head: bool = False,
) -> str:
    """
    Build the SWAP *.swp output block required by PEARLpy.

    SWAP time-depth fluxes are requested for the top of each soil cell. BOT is
    requested separately to populate the lower profile boundary.
    """
    if n_layers <= 0:
        raise ValueError("n_layers must be positive")
    if output_interval_days <= 0:
        raise ValueError("output_interval_days must be positive")

    variables = [
        "BOT",
        f"WC[1:{n_layers}]",
        f"Q[1:{n_layers}]",
        f"RWU[1:{n_layers}]",
        f"T[1:{n_layers}]",
    ]
    if include_pressure_head:
        variables.append(f"H[1:{n_layers}]")

    return "\n".join(
        [
            "* PEARLpy SWAP coupling output",
            "SWMONTH = 0",
            f"PERIOD = {output_interval_days:g}",
            "SWRES = 0",
            "SWODAT = 0",
            "SWCSV = 1",
            f"INLIST_CSV = '{','.join(variables)}'",
        ]
    )


def write_swap_csv_output_block(
    path: str | Path,
    n_layers: int,
    *,
    output_interval_days: float = 1.0,
    include_pressure_head: bool = False,
) -> Path:
    target = Path(path)
    target.write_text(
        build_swap_csv_output_block(
            n_layers,
            output_interval_days=output_interval_days,
            include_pressure_head=include_pressure_head,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def run_swap_executable(
    executable: str | Path,
    swp_file: str | Path,
    *,
    output_csv: str | Path | None = None,
    timeout_s: float = 3600.0,
) -> SwapRunResult:
    """
    Run the official SWAP executable.

    The executable and input data are not distributed with PEARLpy. This
    function only orchestrates a locally installed/downloaded SWAP copy.
    """
    exe = Path(executable).expanduser().resolve()
    swp = Path(swp_file).expanduser().resolve()

    if not exe.exists():
        raise FileNotFoundError(f"SWAP executable not found: {exe}")
    if not swp.exists():
        raise FileNotFoundError(f"SWAP input file not found: {swp}")

    proc = subprocess.run(
        [str(exe), swp.name],
        cwd=swp.parent,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )

    log_candidate = swp.with_suffix(".log")
    csv_candidate = Path(output_csv).resolve() if output_csv else None

    return SwapRunResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        log_path=log_candidate if log_candidate.exists() else None,
        output_csv_path=csv_candidate if csv_candidate and csv_candidate.exists() else None,
    )


def _tokenize(line: str) -> list[str]:
    """Accept both documented comma CSV and whitespace-rendered examples."""
    stripped = line.strip()
    if "," in stripped:
        return [part.strip() for part in next(csv.reader([stripped]))]
    return shlex.split(stripped)


def _read_swap_table(path: Path) -> tuple[list[str], list[list[str]]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = None
    header = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        tokens = _tokenize(line)
        if tokens and tokens[0].upper() in {"DATE", "DATETIME", "TIME"}:
            header_index = idx
            header = tokens
            break

    if header_index is None or header is None:
        raise ValueError("Could not find SWAP DATE header row")

    rows: list[list[str]] = []
    for line in lines[header_index + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        tokens = _tokenize(line)
        if len(tokens) < len(header):
            continue
        rows.append(tokens[: len(header)])

    if not rows:
        raise ValueError("No SWAP data rows found after header")
    return header, rows


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.strip()[:10])


def _discover_depth_columns(
    header: Sequence[str],
    prefix: str,
    *,
    expected: int,
) -> list[str]:
    matches: list[tuple[float, str]] = []
    for column in header:
        m = _DEPTH_COLUMN.match(column.strip())
        if not m or m.group("name").upper() != prefix.upper():
            continue
        coordinate = float(m.group("value"))
        # SWAP headers usually contain negative depth; absolute depth gives
        # shallow-to-deep ordering. Compartment numbers are also sorted correctly.
        matches.append((abs(coordinate), column))

    matches.sort(key=lambda item: item[0])
    columns = [column for _, column in matches]
    if len(columns) != expected:
        raise ValueError(
            f"Expected {expected} {prefix} columns, found {len(columns)}: {columns}"
        )
    return columns


def _constant_interval_days(dates: Sequence[date], tolerance: float = 1e-9) -> float:
    if len(dates) < 2:
        raise ValueError("At least two SWAP dates are required")
    deltas = np.array([(b - a).days for a, b in zip(dates[:-1], dates[1:])], dtype=float)
    if np.any(deltas <= 0):
        raise ValueError("SWAP dates must be strictly increasing")
    if not np.allclose(deltas, deltas[0], atol=tolerance, rtol=0.0):
        raise ValueError(
            "Current PEARLpy HydrologySeries requires a constant SWAP output interval"
        )
    return float(deltas[0])


def load_swap_csv(
    path: str | Path,
    soil: SoilProfile,
    *,
    state_sampling: str = "end",
    bottom_flux_column: str = "BOT",
    bottom_flux_sign: float = 1.0,
    q_flux_sign: float = 1.0,
    drop_initial_row: bool = True,
) -> SwapImportResult:
    """
    Convert SWAP user-defined CSV output to PEARLpy hydrology.

    Required SWAP variables
    -----------------------
    WC[n]  : volumetric water content, state at output time
    Q[n]   : vertical water flux at top of each model cell, cm per interval
    RWU[n] : root water uptake, cm per interval
    T[n]   : soil temperature, degree C
    BOT    : net bottom-boundary flow, cm per interval

    Units are converted to:
    - Q: m d-1
    - RWU: d-1 (volumetric sink)
    - WC: m3 m-3
    - T: degree C

    `drop_initial_row=True` follows the standard SWAP CSV layout, in which the
    first data row is the initial state and subsequent rows represent intervals.
    """
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if state_sampling not in {"end", "midpoint"}:
        raise ValueError("state_sampling must be 'end' or 'midpoint'")
    if bottom_flux_sign == 0 or q_flux_sign == 0:
        raise ValueError("Flux sign multipliers cannot be zero")

    header, rows = _read_swap_table(source)
    index = {name: i for i, name in enumerate(header)}

    date_column = header[0]
    dates = [_parse_date(row[index[date_column]]) for row in rows]
    interval_days = _constant_interval_days(dates)

    n = soil.n_layers
    wc_cols = _discover_depth_columns(header, "WC", expected=n)
    q_cols = _discover_depth_columns(header, "Q", expected=n)
    rwu_cols = _discover_depth_columns(header, "RWU", expected=n)
    temp_cols = _discover_depth_columns(header, "T", expected=n)

    if bottom_flux_column not in index:
        candidates = [c for c in header if c.upper() == bottom_flux_column.upper()]
        if not candidates:
            raise ValueError(f"Bottom flux column {bottom_flux_column!r} was not found")
        bottom_flux_column = candidates[0]

    def numeric_matrix(columns: Sequence[str]) -> np.ndarray:
        return np.asarray(
            [[float(row[index[column]]) for column in columns] for row in rows],
            dtype=float,
        )

    wc_all = numeric_matrix(wc_cols)
    q_all_cm = numeric_matrix(q_cols)
    rwu_all_cm = numeric_matrix(rwu_cols)
    temp_all = numeric_matrix(temp_cols)
    bottom_all_cm = np.asarray(
        [float(row[index[bottom_flux_column]]) for row in rows],
        dtype=float,
    )

    start = 1 if drop_initial_row else 0
    if drop_initial_row and len(rows) < 2:
        raise ValueError("Cannot drop initial row from a one-row SWAP file")

    if state_sampling == "end":
        theta = wc_all[start:]
        temperature = temp_all[start:]
    else:
        if not drop_initial_row:
            raise ValueError("midpoint state sampling requires drop_initial_row=True")
        theta = 0.5 * (wc_all[:-1] + wc_all[1:])
        temperature = 0.5 * (temp_all[:-1] + temp_all[1:])

    q_interval_cm = q_all_cm[start:] * q_flux_sign
    bottom_interval_cm = bottom_all_cm[start:] * bottom_flux_sign
    rwu_interval_cm = rwu_all_cm[start:]

    # Q[n] is at the top of each cell. BOT supplies the N+1 lower boundary.
    q_interfaces_m_d = np.empty((theta.shape[0], n + 1), dtype=float)
    q_interfaces_m_d[:, :n] = q_interval_cm / 100.0 / interval_days
    q_interfaces_m_d[:, n] = bottom_interval_cm / 100.0 / interval_days

    # Convert areic water depth per interval to volumetric sink per day.
    root_uptake_d1 = (
        rwu_interval_cm
        / 100.0
        / soil.thickness_m[np.newaxis, :]
        / interval_days
    )

    if np.any(root_uptake_d1 < -1e-15):
        raise ValueError("SWAP root uptake contains negative values")
    root_uptake_d1 = np.maximum(root_uptake_d1, 0.0)

    warnings: list[str] = []
    if np.any(temperature <= -90):
        raise ValueError(
            "SWAP temperature output contains sentinel values; enable heat simulation"
        )
    if state_sampling == "end":
        warnings.append(
            "WC and T are used at interval end; select midpoint sampling for a sensitivity test"
        )

    hydrology = HydrologySeries(
        dt_d=interval_days,
        theta=theta,
        water_flux_interfaces_m_d=q_interfaces_m_d,
        temperature_c=temperature,
        root_water_uptake_d1=root_uptake_d1,
    )

    used_dates = dates[start:]
    return SwapImportResult(
        hydrology=hydrology,
        metadata=SwapImportMetadata(
            dates=tuple(used_dates),
            interval_days=interval_days,
            water_content_columns=tuple(wc_cols),
            flux_columns=tuple(q_cols),
            root_uptake_columns=tuple(rwu_cols),
            temperature_columns=tuple(temp_cols),
            bottom_flux_column=bottom_flux_column,
            state_sampling=state_sampling,
            warnings=tuple(warnings),
        ),
    )
