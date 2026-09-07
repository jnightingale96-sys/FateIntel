from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from ..config import settings

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "focus_install_manifest.json"


def manifest() -> dict[str, Any]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def installation_status() -> dict[str, Any]:
    data = manifest()
    rows = []
    for item in data["models"]:
        configured_path = settings.external_model_path(item["key"])
        configured = str(configured_path) if configured_path else None
        candidate = Path(configured or item["default_path"])
        rows.append({
            **item,
            "configured_path": str(candidate),
            "path_exists": candidate.exists(),
            "configured_by_environment": bool(configured),
        })
    installed = {row["key"]: row["path_exists"] for row in rows}
    return {
        **data,
        "models": rows,
        "ready_for_spin": installed["SPIN"],
        "ready_for_pearl": installed["SPIN"] and installed["PEARL"],
        "ready_for_macro_groundwater": installed["SPIN"] and installed["MACRO"],
        "ready_for_macro_surface_water": installed["SPIN"] and installed["SWASH"] and installed["MACRO"],
        "ready_for_toxswa": installed["SPIN"] and installed["SWASH"] and installed["TOXSWA"],
    }
