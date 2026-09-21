"""POPs regulatory-status flag from a sourced, NON-EXHAUSTIVE seed list.

Answers one question: "does this substance appear on the Stockholm Convention annexes or in EU Regulation
(EU) 2019/1021 as recorded in app/data/pops_reference.json?" It applies no criteria, calculates no risk and
never says a substance is NOT a POP: a miss is reported as NOT_DETERMINED. Read the `_meta.caveats` in the
data file: the seed list was read through an automated summariser, EU text is the original 2019 version, and
only the Stockholm Convention and EU were researched (UK, US and other national regimes were not).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

REFERENCE_PATH = Path(__file__).resolve().parents[1] / "data" / "pops_reference.json"

STOCKHOLM_ANNEX_MEANING = {
    "A": "Elimination (production and use to be eliminated)",
    "B": "Restriction (production and use restricted to permitted purposes)",
    "C": "Unintentional production (releases to be reduced or eliminated)",
}

SEED_LIST_LIMITS = (
    "Non-exhaustive seed list. NOT_DETERMINED means only that the substance is not in the list; it is not "
    "evidence that it is not a POP under the Stockholm Convention, the EU regulation, the CLRTAP Protocol or "
    "national law."
)


@lru_cache(maxsize=1)
def _reference() -> dict[str, Any]:
    data = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    for entry in data["entries"]:
        entry["_patterns"] = [re.compile(rf"(?<![a-z0-9])(?:{alias})(?![a-z0-9])") for alias in entry["aliases"]]
    return data


def reference_metadata() -> dict[str, Any]:
    return _reference()["_meta"]


def _normalise_cas(cas: str | None) -> str | None:
    text = (cas or "").strip()
    return text or None


def _match_by_cas(cas: str) -> list[dict[str, Any]]:
    return [e for e in _reference()["entries"] if cas in e["cas"]]


def _match_by_name(name: str) -> list[dict[str, Any]]:
    lowered = (name or "").strip().lower()
    if not lowered:
        return []
    return [e for e in _reference()["entries"] if any(p.search(lowered) for p in e["_patterns"])]


def _describe(entry: dict[str, Any]) -> dict[str, Any]:
    eu = entry["eu"]
    confirmed_annex_i = eu["status"] in (
        "CONFIRMED_ORIGINAL_2019_TEXT", "LISTED_PER_EU_MATRIX_CONSOLIDATED_READ",
    ) and (eu["annex"] or "").startswith("I")
    return {
        "key": entry["key"],
        "name": entry["name"],
        "substance_class": entry["substance_class"],
        "stockholm_convention": {
            "annexes": entry["stockholm_annexes"],
            "meaning": {a: STOCKHOLM_ANNEX_MEANING[a] for a in entry["stockholm_annexes"]},
            "source": _reference()["_meta"]["stockholm_source"],
        },
        "eu_pops_regulation_2019_1021": {
            "annex": eu["annex"],
            "status": eu["status"],
            "exemptions": eu["exemptions"],
            "source": _reference()["_meta"]["eu_source"],
        },
        "waste_management": (
            "EU Annexes IV (waste concentration limits) and V (permitted treatment) of Regulation 2019/1021 "
            "govern waste consisting of, containing or contaminated by this substance. Per-substance limits are "
            "NOT encoded here: consult the consolidated regulation."
            if confirmed_annex_i else
            "NOT ESTABLISHED for this substance in the research so far (EU listing not confirmed)."
        ),
        "cas_numbers": entry["cas"],
    }


def pops_status(
    *, cas_number: str | None = None, name: str | None = None, jurisdiction: str | None = None,
) -> dict[str, Any]:
    """Look a substance up by CAS and/or name. Fail-closed: conflicts and misses are reported, never resolved."""
    cas = _normalise_cas(cas_number)
    if cas is None and not (name or "").strip():
        return {"status": "NOT_DETERMINED", "match_basis": None, "matches": [],
                "reason": "No CAS number or name supplied.", "seed_list_limits": SEED_LIST_LIMITS}

    by_cas = _match_by_cas(cas) if cas else []
    by_name = _match_by_name(name or "")

    if by_cas and by_name and not {e["key"] for e in by_cas} & {e["key"] for e in by_name}:
        return {
            "status": "IDENTITY_CONFLICT", "match_basis": None, "matches": [],
            "reason": (f"CAS {cas} matches {[e['name'] for e in by_cas]} but the name matches "
                       f"{[e['name'] for e in by_name]}. Resolve the substance identity before a POPs flag is given."),
            "seed_list_limits": SEED_LIST_LIMITS,
        }

    if by_cas:
        matches, basis = by_cas, "cas"
        note = "Matched on CAS number."
    elif by_name:
        matches, basis = by_name, "name"
        note = ("Matched on name only. Confirm the substance identity by CAS number before relying on this flag: "
                "names can be ambiguous, and class entries (PCBs, dioxins, PBDEs) cover many individual substances.")
    else:
        return {"status": "NOT_DETERMINED", "match_basis": None, "matches": [],
                "reason": "Not in the seed list.", "seed_list_limits": SEED_LIST_LIMITS}

    result: dict[str, Any] = {
        "status": "POPS_REGULATORY_STATUS_DETECTED",
        "match_basis": basis,
        "confidence_note": note,
        "matches": [_describe(e) for e in matches],
        "seed_list_limits": SEED_LIST_LIMITS,
        "reference_retrieved": _reference()["_meta"]["retrieved"],
    }
    if jurisdiction:
        result["national_implementation"] = (
            "Regulation (EU) 2019/1021 (directly applicable)" if jurisdiction == "EU"
            else "NOT RESEARCHED: national implementation of the Stockholm listing was not verified for "
                 f"{jurisdiction}. The Convention listing above is global; do not assume the national position."
        )
    return result
