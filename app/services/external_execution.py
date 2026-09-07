"""Controlled bridge to separately installed official modelling tools.

The bridge deliberately contains no EPA executable, model equation or copied
input database.  It can only run an operator-configured local executable with a
fixed argument/output contract.  GUI-only installations remain manual handoff
workflows and their original output files are imported separately.
"""

from __future__ import annotations

import hashlib
import json
import os
import string
import subprocess
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from ..config import PROJECT_ROOT, settings


EPA_EXECUTION_MODEL_KEYS = frozenset({"PWC", "CHEMSTEER", "CEM", "EFAST"})
BRIDGE_VERSION = "ENVIROCHEM_EXTERNAL_EXECUTION_BRIDGE_1.0"
LOG_EXCERPT_BYTES = 256 * 1024
ALLOWED_ARGUMENT_PLACEHOLDERS = frozenset({"manifest", "output_dir", "workspace"})


class ExternalExecutionError(RuntimeError):
    """Raised when a configured external execution fails a safety precondition."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_string_list(raw: str | None, label: str) -> tuple[list[str] | None, str | None]:
    if raw is None or not raw.strip():
        return None, None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"{label} is not valid JSON: {exc.msg}"
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None, f"{label} must be a JSON array of strings"
    return value, None


def _validate_argument_templates(arguments: list[str] | None) -> str | None:
    if arguments is None:
        return None
    formatter = string.Formatter()
    try:
        fields = {
            field_name
            for argument in arguments
            for _, field_name, _, _ in formatter.parse(argument)
            if field_name
        }
    except ValueError as exc:
        return f"Command argument template is invalid: {exc}"
    unsupported = fields - ALLOWED_ARGUMENT_PLACEHOLDERS
    if unsupported:
        return f"Unsupported command placeholder(s): {', '.join(sorted(unsupported))}"
    return None


def _validate_output_globs(patterns: list[str] | None) -> str | None:
    if patterns is None:
        return None
    if not patterns:
        return "At least one output glob is required"
    for pattern in patterns:
        candidate = Path(pattern)
        if candidate.is_absolute() or ".." in candidate.parts:
            return f"Output glob must remain inside the run workspace: {pattern}"
    return None


def external_tool_status(model_key: str) -> dict[str, Any]:
    """Return an honest readiness result for one separately installed tool."""

    key = model_key.upper()
    supported = key in EPA_EXECUTION_MODEL_KEYS
    configured_path = settings.external_model_path(key) if supported else None
    candidate = configured_path.expanduser() if configured_path else None
    resolved = candidate.resolve(strict=False) if candidate else None
    path_exists = bool(resolved and resolved.exists())
    path_kind = (
        "file" if path_exists and resolved.is_file()
        else "directory" if path_exists and resolved.is_dir()
        else "missing" if resolved
        else "not_configured"
    )
    executable_hash = None
    if path_kind == "file" and resolved is not None and not resolved.is_symlink():
        executable_hash = sha256_file(resolved)

    arguments_raw = settings.external_model_command_args_json(key) if supported else None
    globs_raw = settings.external_model_output_globs_json(key) if supported else None
    arguments, arguments_error = _parse_string_list(arguments_raw, f"ENVIROCHEM_{key}_COMMAND_ARGS_JSON")
    output_globs, globs_error = _parse_string_list(globs_raw, f"ENVIROCHEM_{key}_OUTPUT_GLOBS_JSON")
    template_error = _validate_argument_templates(arguments)
    output_glob_error = _validate_output_globs(output_globs)

    missing: list[str] = []
    if not supported:
        missing.append("No local-process bridge is defined for this model")
    if not settings.envirochem_external_execution_enabled:
        missing.append("ENVIROCHEM_EXTERNAL_EXECUTION_ENABLED is false")
    if not configured_path:
        missing.append(f"ENVIROCHEM_{key}_PATH is not configured")
    elif not path_exists:
        missing.append("Configured installation path does not exist")
    elif path_kind != "file":
        missing.append("Configured path must identify the exact executable, not only its folder")
    elif resolved and resolved.is_symlink():
        missing.append("Configured executable must not be a symbolic link")
    if arguments is None:
        missing.append(f"ENVIROCHEM_{key}_COMMAND_ARGS_JSON is not configured")
    if output_globs is None:
        missing.append(f"ENVIROCHEM_{key}_OUTPUT_GLOBS_JSON is not configured")
    for error in (arguments_error, globs_error, template_error, output_glob_error):
        if error:
            missing.append(error)

    execution_ready = supported and not missing
    if execution_ready:
        state = "execution_ready"
    elif path_exists:
        state = "installation_detected_manual_handoff"
    else:
        state = "manual_handoff"
    return {
        "bridge_version": BRIDGE_VERSION,
        "model_key": key,
        "supported": supported,
        "configuration_state": state,
        "execution_ready": execution_ready,
        "execution_enabled": settings.envirochem_external_execution_enabled,
        "configured_path": str(resolved) if resolved else None,
        "path_exists": path_exists,
        "path_kind": path_kind,
        "executable_sha256": executable_hash,
        "command_arguments_configured": arguments is not None and arguments_error is None,
        "output_globs": output_globs or [],
        "timeout_seconds": settings.envirochem_external_execution_timeout_seconds,
        "missing_requirements": list(dict.fromkeys(missing)),
        "default_route": "controlled_local_process" if execution_ready else "manual_official_execution_and_hashed_import",
        "safety_controls": [
            "No shell invocation",
            "Executable path is fixed in server configuration",
            "Executable SHA-256 must be acknowledged for each run",
            "Arguments and output patterns are fixed in server configuration",
            "Each run uses an isolated workspace and fixed timeout",
            "Official software and databases are never bundled by EnviroChem",
        ],
    }


def _render_arguments(arguments: list[str], replacements: dict[str, str]) -> list[str]:
    return [argument.format_map(replacements) for argument in arguments]


def _safe_environment(workspace: Path, model_key: str, workflow_id: int) -> dict[str, str]:
    retained = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in {
            "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
            "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
        }
    }
    retained.update({
        "ENVIROCHEM_EXTERNAL_WORKSPACE": str(workspace),
        "ENVIROCHEM_EXTERNAL_MODEL_KEY": model_key,
        "ENVIROCHEM_EXTERNAL_WORKFLOW_ID": str(workflow_id),
    })
    return retained


def _read_excerpt(path: Path) -> tuple[str, bool]:
    with path.open("rb") as handle:
        payload = handle.read(LOG_EXCERPT_BYTES + 1)
    truncated = len(payload) > LOG_EXCERPT_BYTES
    return payload[:LOG_EXCERPT_BYTES].decode("utf-8", errors="replace"), truncated


def _collect_artifacts(workspace: Path, patterns: list[str]) -> list[dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    excluded = {"input_manifest.json", "bridge_stdout.log", "bridge_stderr.log"}
    workspace_resolved = workspace.resolve()
    for pattern in patterns:
        for candidate in workspace.glob(pattern):
            if not candidate.is_file() or candidate.is_symlink() or candidate.name in excluded:
                continue
            resolved = candidate.resolve()
            if not resolved.is_relative_to(workspace_resolved):
                continue
            relative = resolved.relative_to(workspace_resolved).as_posix()
            artifacts[relative] = {
                "relative_path": relative,
                "size_bytes": resolved.stat().st_size,
                "sha256": sha256_file(resolved),
            }
    return [artifacts[key] for key in sorted(artifacts)]


def execute_configured_tool(
    *,
    model_key: str,
    workflow_id: int,
    manifest: dict[str, Any],
    expected_executable_sha256: str,
    operator: str,
    installed_version: str,
) -> dict[str, Any]:
    """Execute a pinned operator-configured process and capture its provenance."""

    key = model_key.upper()
    status = external_tool_status(key)
    if not status["execution_ready"]:
        raise ExternalExecutionError("; ".join(status["missing_requirements"]))
    actual_hash = str(status["executable_sha256"] or "")
    if expected_executable_sha256.casefold() != actual_hash.casefold():
        raise ExternalExecutionError("Executable SHA-256 changed or does not match the acknowledged value")

    executable = Path(str(status["configured_path"])).resolve(strict=True)
    arguments, error = _parse_string_list(
        settings.external_model_command_args_json(key),
        f"ENVIROCHEM_{key}_COMMAND_ARGS_JSON",
    )
    if error or arguments is None:
        raise ExternalExecutionError(error or "Command arguments are not configured")
    output_globs = list(status["output_globs"])

    run_root = PROJECT_ROOT / "data" / "external_runs" / f"workflow_{workflow_id}"
    run_root.mkdir(parents=True, exist_ok=True)
    workspace = run_root / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:10]}"
    workspace.mkdir(parents=False, exist_ok=False)
    output_dir = workspace / "output"
    output_dir.mkdir()
    manifest_path = workspace / "input_manifest.json"
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True, default=str).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    replacements = {
        "manifest": str(manifest_path),
        "output_dir": str(output_dir),
        "workspace": str(workspace),
    }
    rendered_arguments = _render_arguments(arguments, replacements)
    stdout_path = workspace / "bridge_stdout.log"
    stderr_path = workspace / "bridge_stderr.log"
    started_at = _utc_now()
    started = perf_counter()
    timed_out = False
    exit_code: int | None = None
    launch_error: str | None = None
    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            completed = subprocess.run(
                [str(executable), *rendered_arguments],
                cwd=workspace,
                env=_safe_environment(workspace, key, workflow_id),
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                shell=False,
                timeout=settings.envirochem_external_execution_timeout_seconds,
                check=False,
            )
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    except OSError as exc:
        launch_error = f"{exc.__class__.__name__}: {exc}"
    finished_at = _utc_now()
    duration_seconds = round(perf_counter() - started, 6)
    stdout_text, stdout_truncated = _read_excerpt(stdout_path)
    stderr_text, stderr_truncated = _read_excerpt(stderr_path)
    artifacts = _collect_artifacts(workspace, output_globs)
    succeeded = exit_code == 0 and not timed_out and not launch_error and bool(artifacts)
    result_status = (
        "succeeded" if succeeded
        else "timed_out" if timed_out
        else "launch_failed" if launch_error
        else "failed_no_outputs" if exit_code == 0 and not artifacts
        else "failed"
    )
    artifact_set_hash = _sha256_bytes(json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return {
        "bridge_version": BRIDGE_VERSION,
        "real_execution": True,
        "model_key": key,
        "workflow_id": workflow_id,
        "status": result_status,
        "succeeded": succeeded,
        "operator": operator,
        "installed_version": installed_version,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "launch_error": launch_error,
        "workspace": str(workspace),
        "executable_path": str(executable),
        "executable_sha256": actual_hash,
        "input_manifest_sha256": _sha256_bytes(manifest_bytes),
        "argument_template_sha256": _sha256_bytes(json.dumps(arguments, separators=(",", ":")).encode("utf-8")),
        "argument_count": len(rendered_arguments),
        "stdout": {
            "sha256": sha256_file(stdout_path), "excerpt": stdout_text,
            "excerpt_truncated": stdout_truncated, "size_bytes": stdout_path.stat().st_size,
        },
        "stderr": {
            "sha256": sha256_file(stderr_path), "excerpt": stderr_text,
            "excerpt_truncated": stderr_truncated, "size_bytes": stderr_path.stat().st_size,
        },
        "artifacts": artifacts,
        "artifact_set_sha256": artifact_set_hash,
    }


def build_handoff_bundle(
    *,
    workflow: dict[str, Any],
    profile: dict[str, Any] | None,
    tool_status: dict[str, Any] | None,
) -> bytes:
    """Build a non-copyrighted handoff package for an official GUI/manual run."""

    manifest = workflow["manifest"]
    expected = workflow["expected_outputs"]
    template = {name: None for name in expected}
    model_name = (profile or {}).get("name", workflow["model_key"])
    official_page = (profile or {}).get("official_page", "Not recorded")
    instructions = f"""# Official model execution handoff

Workflow: {workflow['id']}  
Model: {model_name}  
Jurisdiction: {workflow['jurisdiction']}  
Scenario: {workflow['scenario_name']}  
Input SHA-256: {workflow['input_hash']}

## Controlled procedure

1. Obtain and install the official software from: {official_page}
2. Confirm the installed model and scenario/database versions.
3. Review every unresolved input in `manifest.json`; do not invent defaults.
4. Run the unmodified official tool on an authorised workstation.
5. Retain the complete original output set and run log.
6. In EnviroChem, use **Import official output files** and map the reviewed endpoints.
7. A scientist who did not merely prepare the inputs records the review decision.

This ZIP contains no official executable, proprietary database, copied model code or
claim of EPA endorsement. Preparing this package is not a completed model run.
"""
    files = {
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True, default=str).encode("utf-8"),
        "expected_outputs.json": json.dumps(expected, indent=2, sort_keys=True).encode("utf-8"),
        "structured_outputs_template.json": json.dumps(template, indent=2, sort_keys=True).encode("utf-8"),
        "EXECUTION_CHECKLIST.md": instructions.encode("utf-8"),
        "local_bridge_status.json": json.dumps(tool_status or {}, indent=2, sort_keys=True, default=str).encode("utf-8"),
    }
    checksums = "".join(f"{_sha256_bytes(payload)}  {name}\n" for name, payload in sorted(files.items()))
    files["SHA256SUMS.txt"] = checksums.encode("utf-8")
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()
