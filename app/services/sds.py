from __future__ import annotations

import re
from typing import Any

SECTION_RE = re.compile(r"(?im)^\s*(?:section\s*)?(\d{1,2})[\s.:-]+([^\n\r]+)")
H_STATEMENT_RE = re.compile(r"\bH\d{3}[A-Z]?\b")
P_STATEMENT_RE = re.compile(r"\bP\d{3}(?:\+P\d{3})*\b")
WEL_RE = re.compile(r"(?i)(?:workplace exposure limit|WEL|OEL)[^\n\r]{0,160}")


def split_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        number = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[number] = text[start:end].strip()
    return sections


def _snippet(text: str, terms: list[str], limit: int = 450) -> str | None:
    lower = text.lower()
    positions = [lower.find(term.lower()) for term in terms]
    positions = [p for p in positions if p >= 0]
    if not positions:
        return None
    p = min(positions)
    start = max(0, p - 90)
    return re.sub(r"\s+", " ", text[start:p + limit]).strip()


def parse_sds_text(text: str) -> dict[str, Any]:
    clean = text.replace("\x00", " ")
    sections = split_sections(clean)
    hazard_text = sections.get("2", clean)
    controls_text = sections.get("8", clean)
    first_aid_text = sections.get("4", clean)
    spill_text = sections.get("6", clean)
    handling_text = sections.get("7", clean)
    disposal_text = sections.get("13", clean)

    h_codes = sorted(set(H_STATEMENT_RE.findall(hazard_text)))
    p_codes = sorted(set(P_STATEMENT_RE.findall(hazard_text)))
    signal_word = None
    for word in ("Danger", "Warning"):
        if re.search(rf"\b{word}\b", hazard_text, re.I):
            signal_word = word
            break

    return {
        "sections_found": sorted(sections.keys(), key=lambda x: int(x)),
        "hazard_statement_codes": h_codes,
        "precautionary_statement_codes": p_codes,
        "signal_word": signal_word,
        "exposure_limit_mentions": WEL_RE.findall(controls_text),
        "ppe_excerpt": _snippet(controls_text, ["personal protective", "glove", "eye protection", "respiratory"]),
        "first_aid_excerpt": _snippet(first_aid_text, ["inhalation", "skin contact", "eye contact", "ingestion"]),
        "spill_excerpt": _snippet(spill_text, ["spill", "leak", "contain"]),
        "handling_excerpt": _snippet(handling_text, ["handling", "storage", "incompatible"]),
        "disposal_excerpt": _snippet(disposal_text, ["disposal", "waste", "container"]),
    }


def build_coshh_draft(parsed: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    controls: list[str] = []
    if context["open_handling"]:
        controls.append("Use local exhaust ventilation or a suitable fume cupboard where inhalation exposure is plausible.")
    if context["heating_or_aerosol"]:
        controls.append("Treat heating, spraying, sonication or aerosol generation as an enhanced inhalation-exposure task.")
    controls.append("Use the PPE specified by the current supplier SDS and confirm material compatibility before work.")
    controls.append("Keep quantities at the bench to the minimum required for the task.")
    controls.append("Collect chemical waste through the laboratory's approved waste stream; do not assume drain disposal is acceptable.")

    hazard_count = len(parsed["hazard_statement_codes"])
    initial_risk = "high" if context["heating_or_aerosol"] and context["open_handling"] else "moderate" if hazard_count else "unresolved"
    residual_risk = "moderate" if initial_risk == "high" else "low_to_moderate" if initial_risk == "moderate" else "unresolved"

    missing = []
    if not parsed["hazard_statement_codes"]:
        missing.append("No H-statements were reliably extracted; review SDS Section 2 manually.")
    if not parsed["ppe_excerpt"]:
        missing.append("No PPE excerpt was reliably extracted; review SDS Section 8 manually.")
    if not parsed["disposal_excerpt"]:
        missing.append("No disposal excerpt was reliably extracted; review SDS Section 13 manually.")

    return {
        "title": f"Draft COSHH assessment — {context['substance_name']}",
        "status": "draft_for_competent_person_review",
        "task": context["task_description"],
        "quantity": context["quantity"],
        "frequency": context["frequency"],
        "persons_at_risk": context["persons_at_risk"],
        "hazards": {
            "signal_word": parsed["signal_word"],
            "h_statements": parsed["hazard_statement_codes"],
            "p_statements": parsed["precautionary_statement_codes"],
            "exposure_limits": parsed["exposure_limit_mentions"],
        },
        "exposure_routes": ["inhalation", "skin", "eyes", "ingestion"],
        "initial_risk": initial_risk,
        "recommended_controls": controls,
        "residual_risk": residual_risk,
        "emergency_information": {
            "first_aid": parsed["first_aid_excerpt"],
            "spill": parsed["spill_excerpt"],
        },
        "handling_and_storage": parsed["handling_excerpt"],
        "waste_disposal": parsed["disposal_excerpt"],
        "manual_review_items": missing,
        "approval_statement": (
            "This document is an automated draft. A competent person must check the SDS, the actual task, exposure conditions, controls, waste route and emergency arrangements before approval and signature."
        ),
    }
