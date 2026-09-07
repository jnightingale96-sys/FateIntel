from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "oecd_pharma_consumption_2025.json"
OECD_DATAFLOW = "OECD.ELS.HD,HEALTH_PHMC@DF_PHMC_CONSUM,1.1"
OECD_API_BASE = "https://sdmx.oecd.org/public/rest/data"


def oecd_2025_registry() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def oecd_2025_lookup(class_key: str, country: str) -> dict[str, Any]:
    data = oecd_2025_registry()
    classes = data["classes"]
    if class_key not in classes:
        raise ValueError(f"OECD 2025 Figure 9.6 does not contain class: {class_key}")
    row = classes[class_key]
    values = row["values_2023_or_nearest"]
    if country == "highest_available":
        country, value = max(
            ((name, val) for name, val in values.items() if name != "OECD32"),
            key=lambda item: item[1],
        )
    else:
        if country not in values:
            raise ValueError(f"No OECD 2025 Figure 9.6 value for {row['label']} in {country}")
        value = values[country]
    return {
        "class_key": class_key,
        "class_label": row["label"],
        "atc_codes": row["atc_codes"],
        "country": country,
        "ddd_per_1000_people_day": float(value),
        "unit": data["source"]["unit"],
        "source": data["source"],
        "country_note": data.get("country_notes", {}).get(country),
        "screening_warning": (
            "This is therapeutic-class consumption, not compound-specific measured use. "
            "Assigning the full class DDD rate to one active substance is a conservative prioritisation screen."
        ),
    }


def oecd_live_query_url(atc_code: str, year: int | None = None) -> str:
    """Build the official OECD SDMX query for a pharmaceutical ATC category.

    The query is intentionally returned/stored so the exact source request can be
    audited. OECD's current dataflow is broader than the four classes printed in
    Health at a Glance Figure 9.6.
    """
    code = (atc_code or "").strip().upper()
    if not code or not all(ch.isalnum() for ch in code):
        raise ValueError("ATC code must be alphanumeric, e.g. N03 or N06A")
    params = {
        "dimensionAtObservation": "AllDimensions",
        "format": "csvfilewithlabels",
    }
    if year is not None:
        if year < 1990 or year > 2100:
            raise ValueError("Year is outside the supported range")
        params["startPeriod"] = str(year)
        params["endPeriod"] = str(year)
    return f"{OECD_API_BASE}/{OECD_DATAFLOW}/....{code}?{urllib.parse.urlencode(params)}"


def fetch_oecd_live(atc_code: str, year: int | None = None, timeout_s: float = 12.0) -> dict[str, Any]:
    """Fetch OECD pharmaceutical-consumption rows when the user's network permits it.

    No fetched value is silently selected as a model input. This helper returns
    raw labelled SDMX rows plus the auditable query URL for review.
    """
    url = oecd_live_query_url(atc_code, year)
    request = urllib.request.Request(url, headers={"User-Agent": "EnviroChem/2.17"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            text = response.read().decode("utf-8-sig", "replace")
    except Exception as exc:  # pragma: no cover - network-dependent
        raise RuntimeError(f"OECD SDMX request failed: {exc}") from exc
    rows = list(csv.DictReader(io.StringIO(text)))
    return {
        "query_url": url,
        "atc_code": atc_code.upper(),
        "requested_year": year,
        "rows": rows,
        "row_count": len(rows),
        "source_note": "Official OECD Data Explorer SDMX pharmaceutical-consumption data; review country coverage and units before use.",
    }
