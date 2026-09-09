from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "specialist_substance_group_requirements.json"


@lru_cache(maxsize=1)
def specialist_substance_group_requirements() -> dict:
    """Return the reviewed, specification-only specialist substance-group registry.

    The registry deliberately contains no executable regulatory classification or
    risk rules.  Its status and per-rule implementation fields are part of the API
    contract so callers cannot mistake documented requirements for calculations.
    """

    with DATA_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("status") != "specification_only":
        raise RuntimeError("Specialist substance-group registry must fail closed")
    return payload
