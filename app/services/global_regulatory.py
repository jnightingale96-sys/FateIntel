from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REGION_LABELS = {
    "GLOBAL": "International / global baseline",
    "EU": "European Union / EEA",
    "UK": "United Kingdom (Great Britain)",
    "CH": "Switzerland",
    "US": "United States",
    "CA": "Canada",
    "AU": "Australia",
    "NZ": "New Zealand",
    "JP": "Japan",
    "CN": "China",
    "KR": "South Korea",
    "TW": "Taiwan",
    "IN": "India",
    "SG": "Singapore",
    "MY": "Malaysia",
    "TH": "Thailand",
    "ID": "Indonesia",
    "PH": "Philippines",
    "VN": "Vietnam",
    "BR": "Brazil",
    "MX": "Mexico",
    "CO": "Colombia",
    "CL": "Chile",
    "PE": "Peru",
    "ZA": "South Africa",
    "NG": "Nigeria",
    "KE": "Kenya",
    "GH": "Ghana",
    "MA": "Morocco",
    "EG": "Egypt",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "IL": "Israel",
    "EAEU": "Eurasian Economic Union",
    "TR": "Türkiye",
    "UA": "Ukraine",
    "ANDEAN": "Andean Community",
    "GCC": "Gulf Cooperation Council",
    "CILSS": "CILSS member states",
    "CEMAC": "Central African Economic and Monetary Community",
}

REGION_RULES: dict[str, list[str]] = {
    "EU": ["European Union", "European Union / EEA"],
    "UK": ["United Kingdom", "United Kingdom (Great Britain)"],
    "CH": ["Switzerland"],
    "US": ["United States", "US EPA"],
    "CA": ["Canada"],
    "AU": ["Australia"],
    "NZ": ["New Zealand"],
    "JP": ["Japan"],
    "CN": ["China"],
    "KR": ["South Korea"],
    "TW": ["Taiwan"],
    "IN": ["India"],
    "SG": ["Singapore"],
    "MY": ["Malaysia"],
    "TH": ["Thailand"],
    "ID": ["Indonesia"],
    "PH": ["Philippines"],
    "VN": ["Vietnam"],
    "BR": ["Brazil"],
    "MX": ["Mexico"],
    "CO": ["Colombia"],
    "CL": ["Chile"],
    "PE": ["Peru"],
    "ZA": ["South Africa"],
    "NG": ["Nigeria"],
    "KE": ["Kenya"],
    "GH": ["Ghana"],
    "MA": ["Morocco"],
    "EG": ["Egypt"],
    "SA": ["Saudi Arabia"],
    "AE": ["United Arab Emirates"],
    "IL": ["Israel"],
    "EAEU": ["Eurasian Economic Union"],
    "TR": ["Türkiye"],
    "UA": ["Ukraine"],
    "ANDEAN": ["Andean Community"],
    "GCC": ["Gulf Cooperation Council"],
    "CILSS": ["CILSS member states"],
    "CEMAC": ["Central African Economic and Monetary Community"],
}

PRODUCT_CLASS_ALIASES = {
    "industrial_organic": "industrial_chemicals",
    "industrial_chemicals": "industrial_chemicals",
    "pesticide": "pesticides",
    "pesticides": "pesticides",
    "biocide": "biocides",
    "biocides": "biocides",
    "human_pharmaceutical": "human_pharmaceuticals",
    "human_pharmaceuticals": "human_pharmaceuticals",
    "veterinary_pharmaceutical": "veterinary_pharmaceuticals",
    "veterinary_pharmaceuticals": "veterinary_pharmaceuticals",
    "personal_care_cosmetic": "cosmetics",
    "cosmetics": "cosmetics",
    "detergent_cleaner": "industrial_chemicals",
    "laboratory": "workplace",
    "workplace": "workplace",
    "food_feed": "food_feed",
    "medical_device": "medical_devices",
    "medical_devices": "medical_devices",
    "nanomaterial": "nanomaterials",
    "nanomaterials": "nanomaterials",
    "mixture_formulation": "cross_cutting",
    "emerging_contaminant": "cross_cutting",
    "pfas_persistent_mobile": "cross_cutting",
    "metal_inorganic": "cross_cutting",
}

CORE_BASELINE_IDS = ["INT-001", "INT-002", "INT-003", "INT-004", "INT-005", "INT-006"]
SECTOR_BASELINE = {
    "pesticides": ["INT-011", "INT-012", "INT-014"],
    "human_pharmaceuticals": ["INT-025"],
    "veterinary_pharmaceuticals": ["INT-023", "INT-024"],
    "food_feed": ["INT-008", "INT-013", "INT-014"],
    "workplace": ["INT-031"],
    "medical_devices": ["INT-029", "INT-030"],
}
SPECIALIST_BY_SCENARIO = {
    "municipal_wastewater": ["XCT-001"],
    "industrial_effluent": ["XCT-001", "XCT-007"],
    "wastewater_irrigation": ["XCT-001", "XCT-005", "XCT-007"],
    "biosolids_to_soil": ["XCT-001", "XCT-005"],
    "agricultural_spray": ["XCT-001", "XCT-005", "XCT-007"],
    "soil_incorporation": ["XCT-001", "XCT-005"],
    "surface_water_discharge": ["XCT-001", "XCT-005"],
    "groundwater_leaching": ["XCT-001", "XCT-005"],
    "laboratory_use": ["XCT-007"],
    "household_use": ["XCT-007"],
    "product_disposal": ["INT-021"],
}


@lru_cache(maxsize=1)
def frameworks() -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / "global_regulatory_frameworks.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def change_watch() -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / "global_change_watch.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def endpoint_checklist() -> list[dict[str, Any]]:
    return json.loads((DATA_DIR / "global_endpoint_checklist.json").read_text(encoding="utf-8"))


def get_framework(framework_id: str) -> dict[str, Any] | None:
    return next((row for row in frameworks() if row["id"] == framework_id), None)


def filter_frameworks(
    jurisdiction: str | None = None,
    product_class: str | None = None,
    verification_tier: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    rows = frameworks()
    if jurisdiction:
        j = jurisdiction.strip().lower()
        rows = [
            row for row in rows
            if j in row["jurisdiction"].lower()
            or j in row["authority"].lower()
            or j == row["region_group"].lower()
        ]
    if product_class:
        canonical = PRODUCT_CLASS_ALIASES.get(product_class, product_class)
        rows = [
            row for row in rows
            if canonical in row.get("product_classes", [])
            or "cross_cutting" in row.get("product_classes", [])
        ]
    if verification_tier:
        rows = [row for row in rows if row["verification_tier"] == verification_tier]
    if query:
        q = query.strip().lower()
        rows = [
            row for row in rows
            if q in " ".join([
                row["id"], row["jurisdiction"], row["authority"],
                row["chemical_domain"], row["framework"],
                row["implementation_note"],
            ]).lower()
        ]
    return rows


def _region_matches(row: dict[str, Any], region_key: str) -> bool:
    if region_key == "GLOBAL":
        return row["region_group"] in {"INT", "XCT"}
    labels = REGION_RULES.get(region_key, [region_key])
    haystack = f"{row['jurisdiction']} {row['authority']}".lower()
    return any(label.lower() in haystack for label in labels)


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        result.append(row)
    return result


def _change_watch_for_regions(region_keys: list[str]) -> list[dict[str, Any]]:
    selected = []
    labels = [REGION_LABELS.get(key, key).lower() for key in region_keys]
    aliases = [x.lower() for key in region_keys for x in REGION_RULES.get(key, [key])]
    for item in change_watch():
        h = f"{item['item']} {item['jurisdiction']} {item['change_trigger']}".lower()
        if item["jurisdiction"].lower() == "global" or any(label in h for label in labels + aliases):
            selected.append(item)
    return selected


def recommend_regulatory_pathway(payload: dict[str, Any]) -> dict[str, Any]:
    region_keys = payload.get("jurisdictions") or ["EU", "US"]
    product_class = PRODUCT_CLASS_ALIASES.get(payload.get("product_class", "cross_cutting"), payload.get("product_class", "cross_cutting"))
    scenario = payload.get("scenario", "municipal_wastewater")
    tier = int(payload.get("tier", 1))
    include_international = bool(payload.get("include_international", True))

    selected: list[dict[str, Any]] = []
    reasons: dict[str, str] = {}

    if include_international:
        for fid in CORE_BASELINE_IDS + SECTOR_BASELINE.get(product_class, []):
            row = get_framework(fid)
            if row:
                selected.append(row)
                reasons[fid] = "International baseline for classification, test methods, evidence quality or sector harmonisation."

    # Regional and national frameworks
    for row in frameworks():
        if row["region_group"] in {"INT", "XCT"}:
            continue
        if not any(_region_matches(row, key) for key in region_keys):
            continue
        classes = row.get("product_classes", [])
        if product_class in classes or "cross_cutting" in classes:
            selected.append(row)
            reasons[row["id"]] = f"Applicable regional/national pathway for {product_class.replace('_', ' ')}."

    # Cross-cutting specialist sources
    for fid in SPECIALIST_BY_SCENARIO.get(scenario, []):
        row = get_framework(fid)
        if row:
            selected.append(row)
            reasons[fid] = f"Specialist source relevant to the {scenario.replace('_', ' ')} scenario."

    if product_class == "nanomaterials":
        row = get_framework("XCT-004")
        if row:
            selected.append(row)
            reasons[row["id"]] = "Nanoform-specific identity and safety guidance is required."
    if product_class in {"cross_cutting", "industrial_chemicals", "human_pharmaceuticals", "veterinary_pharmaceuticals", "pesticides", "biocides"}:
        for fid in ["XCT-002", "XCT-010"]:
            row = get_framework(fid)
            if row:
                selected.append(row)
                reasons[fid] = "Persistence/mobility or transparent weight-of-evidence assessment may be triggered."

    selected = _dedupe(selected)
    selected.sort(key=lambda row: (
        {"A": 0, "B": 1, "C": 2}.get(row["verification_tier"], 3),
        row["region_group"],
        row["id"],
    ))

    tier_counts = {"A": 0, "B": 0, "C": 0}
    for row in selected:
        tier_counts[row["verification_tier"]] += 1

    warnings: list[str] = []
    if tier_counts["B"] or tier_counts["C"]:
        warnings.append(
            "One or more pathways require current local-language or competent-authority verification before filing."
        )
    if any(row["source_review_status"] != "official_source_reviewed" for row in selected):
        warnings.append(
            "The registry contains official-source navigation entries at different review depths. Only sources marked official_source_reviewed have completed source-level reading in this build."
        )
    if tier >= 3:
        warnings.append(
            "Refined and monitoring-informed tiers require jurisdiction-specific acceptance of local data, scenarios and model refinements."
        )

    return {
        "snapshot_date": "2026-07-30",
        "jurisdictions": region_keys,
        "jurisdiction_labels": [REGION_LABELS.get(key, key) for key in region_keys],
        "product_class": product_class,
        "scenario": scenario,
        "assessment_tier": tier,
        "selected_frameworks": [
            {**row, "selection_reason": reasons.get(row["id"], "Applicable source.")}
            for row in selected
        ],
        "verification_summary": tier_counts,
        "change_watch": _change_watch_for_regions(region_keys),
        "endpoint_checklist": endpoint_checklist(),
        "warnings": warnings,
        "legal_notice": "Regulatory navigation and scientific decision support only. Confirm current official text and competent-authority requirements before filing or advising a client.",
    }


def research_status() -> dict[str, Any]:
    rows = frameworks()
    status_counts: dict[str, int] = {}
    tier_counts = {"A": 0, "B": 0, "C": 0}
    for row in rows:
        status_counts[row["source_review_status"]] = status_counts.get(row["source_review_status"], 0) + 1
        tier_counts[row["verification_tier"]] += 1
    return {
        "snapshot_date": "2026-07-30",
        "framework_entries": len(rows),
        "official_urls": sum(1 for row in rows if row.get("official_url")),
        "verification_tiers": tier_counts,
        "review_status": status_counts,
        "change_watch_items": len(change_watch()),
        "implementation_rule": "Do not present a framework as fully implemented merely because its source is registered. Source review, ruleset implementation, validation and legal verification are separate statuses.",
    }
