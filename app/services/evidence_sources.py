from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from hashlib import sha256
import html
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import quote
import xml.etree.ElementTree as ET

import httpx

BASE_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BASE_DIR / "data" / "evidence_source_registry.json"
SOURCE_REGISTRY: list[dict[str, Any]] = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
SOURCE_BY_KEY = {row["key"]: row for row in SOURCE_REGISTRY}

DEFAULT_TIMEOUT_S = 14.0

ENDPOINT_CATALOG: list[dict[str, Any]] = [
    {"code": "FATE.MANURE_DT50", "label": "Manure / slurry degradation DT50", "unit_family": "time"},
    {"code": "FATE.SOIL_DT50", "label": "Soil degradation DT50", "unit_family": "time"},
    {"code": "FATE.WATER_SEDIMENT_DT50", "label": "Water–sediment DT50", "unit_family": "time"},
    {"code": "FATE.WATER_DT50", "label": "Water-phase degradation DT50", "unit_family": "time"},
    {"code": "FATE.HYDROLYSIS_DT50", "label": "Hydrolysis DT50", "unit_family": "time"},
    {"code": "FATE.PHOTOLYSIS_DT50", "label": "Photolysis DT50", "unit_family": "time"},
    {"code": "FATE.BIODEGRADATION", "label": "Biodegradation", "unit_family": "mixed"},
    {"code": "FATE.WWTP_REMOVAL", "label": "Wastewater-treatment removal", "unit_family": "percent"},
    {"code": "SORPTION.KOC", "label": "Organic-carbon normalized sorption Koc", "unit_family": "volume_mass"},
    {"code": "SORPTION.KD", "label": "Distribution coefficient Kd", "unit_family": "volume_mass"},
    {"code": "SORPTION.KF", "label": "Freundlich coefficient Kf", "unit_family": "mixed"},
    {"code": "BIOACCUMULATION.BCF", "label": "Bioconcentration factor", "unit_family": "volume_mass"},
    {"code": "PHYS.WATER_SOLUBILITY", "label": "Water solubility", "unit_family": "mass_volume"},
    {"code": "PHYS.VAPOUR_PRESSURE", "label": "Vapour pressure", "unit_family": "pressure"},
    {"code": "PHYS.LOGKOW", "label": "log Kow / log P", "unit_family": "dimensionless"},
    {"code": "PHYS.PKA", "label": "Dissociation constant pKa", "unit_family": "dimensionless"},
    {"code": "ECOTOX.AQUATIC.LC50", "label": "Aquatic LC50", "unit_family": "mass_volume"},
    {"code": "ECOTOX.AQUATIC.EC50", "label": "Aquatic EC50", "unit_family": "mass_volume"},
    {"code": "ECOTOX.AQUATIC.NOEC", "label": "Aquatic NOEC", "unit_family": "mass_volume"},
    {"code": "ECOTOX.AQUATIC.EC10", "label": "Aquatic EC10", "unit_family": "mass_volume"},
]

_ENDPOINT_BY_CODE = {row["code"]: row for row in ENDPOINT_CATALOG}

_TIME_UNITS = {
    "h": "hours", "hr": "hours", "hrs": "hours", "hour": "hours", "hours": "hours",
    "d": "days", "day": "days", "days": "days",
    "wk": "weeks", "week": "weeks", "weeks": "weeks",
    "mo": "months", "month": "months", "months": "months",
    "y": "years", "yr": "years", "year": "years", "years": "years",
}

_MATRIX_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("manure", ("manure", "slurry", "dung", "faeces", "feces", "excreta")),
    ("activated_sludge", ("activated sludge", "sewage sludge", "wastewater", "wwtp", "sewage treatment")),
    ("water_sediment", ("water-sediment", "water sediment", "sediment-water", "sediment water")),
    ("sediment", ("sediment",)),
    ("soil", ("soil", "soils")),
    ("surface_water", ("surface water", "aqueous", "water phase", "water-phase")),
]

_CONTEXT_ENDPOINTS: list[tuple[str, tuple[str, ...]]] = [
    ("FATE.MANURE_DT50", ("manure", "slurry", "dung", "faeces", "feces", "excreta")),
    ("FATE.HYDROLYSIS_DT50", ("hydrolysis", "hydrolytic", "hydrolysed", "hydrolyzed")),
    ("FATE.PHOTOLYSIS_DT50", ("photolysis", "photolytic", "photodegradation", "photo-degradation")),
    ("FATE.WATER_SEDIMENT_DT50", ("water-sediment", "water sediment", "sediment-water", "sediment water")),
    ("FATE.SOIL_DT50", ("soil", "soils")),
    ("FATE.WATER_DT50", ("aqueous", "water phase", "surface water", "water-phase")),
]

DT50_RE = re.compile(
    r"(?P<label>DT\s*50|DT₅₀|half[-\s]?life|t\s*1\s*/\s*2)"
    r"(?:\s*(?:of|=|:|was|is|approximately|approx\.?|about|~))?\s*"
    r"(?P<qualifier>[<>≤≥~]?)\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>hours?|hrs?|hr|h|days?|d|weeks?|wk|months?|mo|years?|yrs?|yr|y)\b",
    flags=re.IGNORECASE,
)

KOC_RE = re.compile(r"\bK\s*oc\b\s*(?:=|:|of|was|is)?\s*(?P<qualifier>[<>≤≥~]?)\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>L\s*/\s*kg|mL\s*/\s*g|L\s*kg[-−]?1)?", flags=re.IGNORECASE)
KD_RE = re.compile(r"\bK\s*d\b\s*(?:=|:|of|was|is)?\s*(?P<qualifier>[<>≤≥~]?)\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>L\s*/\s*kg|mL\s*/\s*g|L\s*kg[-−]?1)?", flags=re.IGNORECASE)
BCF_RE = re.compile(r"\bBCF\b\s*(?:=|:|of|was|is)?\s*(?P<qualifier>[<>≤≥~]?)\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>L\s*/\s*kg|L\s*kg[-−]?1)?", flags=re.IGNORECASE)
ECOTOX_RE = re.compile(
    r"\b(?P<label>LC\s*50|EC\s*50|EC\s*10|NOEC)\b\s*(?:=|:|of|was|is)?\s*"
    r"(?P<qualifier>[<>≤≥~]?)\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>ng\s*/\s*L|µg\s*/\s*L|ug\s*/\s*L|mg\s*/\s*L|g\s*/\s*L|ng\s*L[-−]?1|µg\s*L[-−]?1|ug\s*L[-−]?1|mg\s*L[-−]?1)",
    flags=re.IGNORECASE,
)
BIODEG_PERCENT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*%\s*(?:biodegrad(?:ed|ation)|mineralis(?:ed|ation)|mineraliz(?:ed|ation))",
    flags=re.IGNORECASE,
)
TEMP_RE = re.compile(r"(?P<value>-?\d+(?:\.\d+)?)\s*°?\s*C\b", flags=re.IGNORECASE)
PH_RE = re.compile(r"\bpH\s*(?:=|:)?\s*(?P<value>\d+(?:\.\d+)?)\b", flags=re.IGNORECASE)
GUIDELINE_RE = re.compile(r"\b(?P<scheme>OECD|OPPTS|OCSPP|ISO|ASTM|FDA)\s*(?:Test\s*(?:No\.?|Guideline)?\s*)?(?P<number>\d{2,4}[A-Za-z]?(?:[-/.]\d+)?)\b", flags=re.IGNORECASE)
WWTP_REMOVAL_RE = re.compile(
    r"(?:(?P<value1>\d+(?:\.\d+)?)\s*%\s*(?:overall\s+)?(?:removal|removed|elimination|eliminated)|"
    r"(?:removal|elimination)(?:\s+efficiency)?\s*(?:of|=|:|was|is)?\s*(?P<value2>\d+(?:\.\d+)?)\s*%)",
    flags=re.IGNORECASE,
)
NUMBER_RE = r"[+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?"
LOGKOW_RE = re.compile(
    rf"\b(?:log\s*K\s*ow|log\s*P|XlogP(?:3-AA|3)?)\b\s*(?:=|:|of|was|is)?\s*(?P<value>{NUMBER_RE})",
    flags=re.IGNORECASE,
)
PKA_RE = re.compile(
    rf"\bpK\s*a\b\s*(?:=|:|of|was|is)?\s*(?P<value>{NUMBER_RE})",
    flags=re.IGNORECASE,
)
SOLUBILITY_RE = re.compile(
    rf"\b(?:water\s+solubility|solubility(?:\s+in\s+water)?)\b\s*(?:=|:|of|was|is)?\s*(?P<value>{NUMBER_RE})\s*(?P<unit>ng\s*/\s*L|µg\s*/\s*L|ug\s*/\s*L|mg\s*/\s*L|g\s*/\s*L|mg\s*/\s*mL|g\s*/\s*100\s*mL)",
    flags=re.IGNORECASE,
)
VAPOUR_PRESSURE_RE = re.compile(
    rf"\b(?:vapou?r\s+pressure)\b\s*(?:=|:|of|was|is)?\s*(?P<value>{NUMBER_RE})\s*(?P<unit>Pa|kPa|hPa|mPa|mm\s*Hg|Torr|atm)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceCandidate:
    candidate_id: str
    source_key: str
    source_name: str
    source_record_id: str | None
    source_url: str | None
    chemical_name: str
    cas_number: str | None
    property_code: str
    endpoint_label: str
    value: float | None
    unit: str | None
    qualifier: str
    matrix: str | None
    temperature_c: float | None
    ph: float | None
    guideline: str | None
    evidence_type: str
    publication_title: str | None
    publication_year: int | None
    doi: str | None
    pmid: str | None
    pmcid: str | None
    original_source: str | None
    rights_status: str
    import_allowed: bool
    needs_professional_review: bool
    extraction_status: str
    snippet: str
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def source_registry() -> list[dict[str, Any]]:
    return SOURCE_REGISTRY


def endpoint_catalog() -> list[dict[str, Any]]:
    return ENDPOINT_CATALOG


def get_source(key: str) -> dict[str, Any]:
    try:
        return SOURCE_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"Unknown evidence source: {key}") from exc


def _candidate_id(*parts: Any) -> str:
    raw = "|".join("" if x is None else str(x) for x in parts)
    return sha256(raw.encode("utf-8")).hexdigest()[:24]


def _plain_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _context(text: str, start: int, end: int, radius: int = 190) -> str:
    return text[max(0, start-radius): min(len(text), end+radius)].strip()


def _matrix_from_context(context: str) -> str | None:
    low = context.lower()
    for matrix, hints in _MATRIX_HINTS:
        if any(hint in low for hint in hints):
            return matrix
    return None


def _dt50_property_from_context(context: str) -> str:
    low = context.lower()
    for code, hints in _CONTEXT_ENDPOINTS:
        if any(hint in low for hint in hints):
            return code
    return "FATE.WATER_DT50"


def _first_float(regex: re.Pattern[str], context: str) -> float | None:
    match = regex.search(context)
    return float(match.group("value")) if match else None


def _guideline_from_context(context: str) -> str | None:
    match = GUIDELINE_RE.search(context)
    if not match:
        return None
    return f"{match.group('scheme').upper()} {match.group('number')}"


def _norm_qualifier(value: str | None) -> str:
    value = (value or "").strip()
    return {"≤": "<=", "≥": ">=", "~": "~"}.get(value, value or "=")


def extract_endpoint_candidates_from_text(
    text: str,
    *,
    source_key: str,
    source_name: str,
    chemical_name: str,
    cas_number: str | None = None,
    source_record_id: str | None = None,
    source_url: str | None = None,
    publication_title: str | None = None,
    publication_year: int | None = None,
    doi: str | None = None,
    pmid: str | None = None,
    pmcid: str | None = None,
    original_source: str | None = None,
    rights_status: str = "source_terms_apply",
    import_allowed: bool = True,
    extraction_status: str = "machine_extracted_unreviewed",
    endpoint_filter: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Deterministically extract endpoint *candidates* from text.

    This intentionally does not select a regulatory value. It surfaces numeric
    phrases with local context for scientist review.
    """
    clean = _plain_text(text)
    allowed = set(endpoint_filter or [])
    candidates: list[EvidenceCandidate] = []

    def keep(code: str) -> bool:
        return not allowed or code in allowed

    for match in DT50_RE.finditer(clean):
        ctx = _context(clean, match.start(), match.end())
        code = _dt50_property_from_context(ctx)
        if not keep(code):
            continue
        unit_token = re.sub(r"\s+", "", match.group("unit")).lower()
        unit = _TIME_UNITS.get(unit_token, match.group("unit"))
        candidates.append(EvidenceCandidate(
            candidate_id=_candidate_id(source_key, source_record_id, code, match.start(), match.group("value")),
            source_key=source_key, source_name=source_name, source_record_id=source_record_id,
            source_url=source_url, chemical_name=chemical_name, cas_number=cas_number,
            property_code=code, endpoint_label=_ENDPOINT_BY_CODE[code]["label"],
            value=float(match.group("value")), unit=unit, qualifier=_norm_qualifier(match.group("qualifier")),
            matrix=_matrix_from_context(ctx), temperature_c=_first_float(TEMP_RE, ctx), ph=_first_float(PH_RE, ctx),
            guideline=_guideline_from_context(ctx), evidence_type="measured_candidate", publication_title=publication_title,
            publication_year=publication_year, doi=doi, pmid=pmid, pmcid=pmcid,
            original_source=original_source, rights_status=rights_status, import_allowed=import_allowed,
            needs_professional_review=True, extraction_status=extraction_status, snippet=ctx,
        ))

    for regex, code in [(KOC_RE, "SORPTION.KOC"), (KD_RE, "SORPTION.KD"), (BCF_RE, "BIOACCUMULATION.BCF")]:
        if not keep(code):
            continue
        for match in regex.finditer(clean):
            ctx = _context(clean, match.start(), match.end())
            unit = (match.groupdict().get("unit") or ("L/kg" if code != "BIOACCUMULATION.BCF" else "L/kg")).replace(" ", "")
            candidates.append(EvidenceCandidate(
                candidate_id=_candidate_id(source_key, source_record_id, code, match.start(), match.group("value")),
                source_key=source_key, source_name=source_name, source_record_id=source_record_id,
                source_url=source_url, chemical_name=chemical_name, cas_number=cas_number,
                property_code=code, endpoint_label=_ENDPOINT_BY_CODE[code]["label"], value=float(match.group("value")),
                unit=unit, qualifier=_norm_qualifier(match.group("qualifier")), matrix=_matrix_from_context(ctx),
                temperature_c=_first_float(TEMP_RE, ctx), ph=_first_float(PH_RE, ctx), guideline=_guideline_from_context(ctx),
                evidence_type="measured_candidate", publication_title=publication_title, publication_year=publication_year,
                doi=doi, pmid=pmid, pmcid=pmcid, original_source=original_source, rights_status=rights_status,
                import_allowed=import_allowed, needs_professional_review=True, extraction_status=extraction_status,
                snippet=ctx,
            ))

    label_to_code = {"lc50": "ECOTOX.AQUATIC.LC50", "ec50": "ECOTOX.AQUATIC.EC50", "ec10": "ECOTOX.AQUATIC.EC10", "noec": "ECOTOX.AQUATIC.NOEC"}
    for match in ECOTOX_RE.finditer(clean):
        label = re.sub(r"\s+", "", match.group("label")).lower()
        code = label_to_code[label]
        if not keep(code):
            continue
        ctx = _context(clean, match.start(), match.end())
        candidates.append(EvidenceCandidate(
            candidate_id=_candidate_id(source_key, source_record_id, code, match.start(), match.group("value")),
            source_key=source_key, source_name=source_name, source_record_id=source_record_id,
            source_url=source_url, chemical_name=chemical_name, cas_number=cas_number,
            property_code=code, endpoint_label=_ENDPOINT_BY_CODE[code]["label"], value=float(match.group("value")),
            unit=re.sub(r"\s+", "", match.group("unit")).replace("ug", "µg"), qualifier=_norm_qualifier(match.group("qualifier")),
            matrix="surface_water", temperature_c=_first_float(TEMP_RE, ctx), ph=_first_float(PH_RE, ctx), guideline=_guideline_from_context(ctx),
            evidence_type="measured_candidate", publication_title=publication_title, publication_year=publication_year,
            doi=doi, pmid=pmid, pmcid=pmcid, original_source=original_source, rights_status=rights_status,
            import_allowed=import_allowed, needs_professional_review=True, extraction_status=extraction_status,
            snippet=ctx,
        ))

    if keep("FATE.WWTP_REMOVAL"):
        for match in WWTP_REMOVAL_RE.finditer(clean):
            ctx = _context(clean, match.start(), match.end())
            low = ctx.lower()
            if not any(token in low for token in ("wwtp", "wastewater", "sewage", "activated sludge", "treatment plant", "stp")):
                continue
            raw_value = match.group("value1") or match.group("value2")
            candidates.append(EvidenceCandidate(
                candidate_id=_candidate_id(source_key, source_record_id, "FATE.WWTP_REMOVAL", match.start(), raw_value),
                source_key=source_key, source_name=source_name, source_record_id=source_record_id,
                source_url=source_url, chemical_name=chemical_name, cas_number=cas_number,
                property_code="FATE.WWTP_REMOVAL", endpoint_label=_ENDPOINT_BY_CODE["FATE.WWTP_REMOVAL"]["label"],
                value=float(raw_value), unit="%", qualifier="=", matrix="activated_sludge",
                temperature_c=_first_float(TEMP_RE, ctx), ph=_first_float(PH_RE, ctx), guideline=_guideline_from_context(ctx),
                evidence_type="measured_candidate", publication_title=publication_title, publication_year=publication_year,
                doi=doi, pmid=pmid, pmcid=pmcid, original_source=original_source, rights_status=rights_status,
                import_allowed=import_allowed, needs_professional_review=True, extraction_status=extraction_status,
                snippet=ctx,
            ))

    if keep("FATE.BIODEGRADATION"):
        for match in BIODEG_PERCENT_RE.finditer(clean):
            ctx = _context(clean, match.start(), match.end())
            candidates.append(EvidenceCandidate(
                candidate_id=_candidate_id(source_key, source_record_id, "FATE.BIODEGRADATION", match.start(), match.group("value")),
                source_key=source_key, source_name=source_name, source_record_id=source_record_id,
                source_url=source_url, chemical_name=chemical_name, cas_number=cas_number,
                property_code="FATE.BIODEGRADATION", endpoint_label=_ENDPOINT_BY_CODE["FATE.BIODEGRADATION"]["label"],
                value=float(match.group("value")), unit="%", qualifier="=", matrix=_matrix_from_context(ctx),
                temperature_c=_first_float(TEMP_RE, ctx), ph=_first_float(PH_RE, ctx), guideline=_guideline_from_context(ctx),
                evidence_type="measured_candidate", publication_title=publication_title, publication_year=publication_year,
                doi=doi, pmid=pmid, pmcid=pmcid, original_source=original_source, rights_status=rights_status,
                import_allowed=import_allowed, needs_professional_review=True, extraction_status=extraction_status,
                snippet=ctx,
            ))

    for regex, code, default_unit in (
        (LOGKOW_RE, "PHYS.LOGKOW", "dimensionless"),
        (PKA_RE, "PHYS.PKA", "dimensionless"),
        (SOLUBILITY_RE, "PHYS.WATER_SOLUBILITY", None),
        (VAPOUR_PRESSURE_RE, "PHYS.VAPOUR_PRESSURE", None),
    ):
        if not keep(code):
            continue
        for match in regex.finditer(clean):
            ctx = _context(clean, match.start(), match.end())
            unit = default_unit or re.sub(r"\s+", "", match.group("unit")).replace("ug", "µg")
            candidates.append(EvidenceCandidate(
                candidate_id=_candidate_id(source_key, source_record_id, code, match.start(), match.group("value")),
                source_key=source_key, source_name=source_name, source_record_id=source_record_id,
                source_url=source_url, chemical_name=chemical_name, cas_number=cas_number,
                property_code=code, endpoint_label=_ENDPOINT_BY_CODE[code]["label"], value=float(match.group("value")),
                unit=unit, qualifier="=", matrix=None, temperature_c=_first_float(TEMP_RE, ctx),
                ph=_first_float(PH_RE, ctx), guideline=_guideline_from_context(ctx),
                evidence_type="measured_or_database_candidate", publication_title=publication_title,
                publication_year=publication_year, doi=doi, pmid=pmid, pmcid=pmcid,
                original_source=original_source, rights_status=rights_status, import_allowed=import_allowed,
                needs_professional_review=True, extraction_status=extraction_status, snippet=ctx,
                notes="Property identity and experimental/predicted status require source review before selection.",
            ))

    # De-duplicate exact source/property/value/unit/snippet combinations.
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for item in candidates:
        key = (item.source_record_id, item.property_code, item.value, item.unit, item.snippet)
        if key in seen:
            continue
        seen.add(key)
        out.append(item.to_dict())
    return out


def _client() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(DEFAULT_TIMEOUT_S, connect=7.0), follow_redirects=True, headers={"User-Agent": "EnviroChem-Studio/2.18 evidence-source-client"})


def _pubchem_cid(client: httpx.Client, chemical_name: str, cas_number: str | None) -> int:
    identifier = cas_number or chemical_name
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(identifier, safe='')}/cids/JSON"
    response = client.get(url)
    response.raise_for_status()
    cids = response.json().get("IdentifierList", {}).get("CID", [])
    if not cids:
        raise LookupError(f"PubChem did not resolve {identifier!r}")
    return int(cids[0])


def _pubchem_reference_map(record: dict[str, Any]) -> dict[int, dict[str, Any]]:
    refs: dict[int, dict[str, Any]] = {}
    for ref in record.get("Record", {}).get("Reference", []) or []:
        number = ref.get("ReferenceNumber")
        if isinstance(number, int):
            refs[number] = ref
    return refs


def _value_to_text(value: dict[str, Any]) -> str:
    if not value:
        return ""
    if value.get("StringWithMarkup"):
        return " ".join(x.get("String", "") for x in value["StringWithMarkup"] if x.get("String"))
    if "Number" in value:
        nums = value.get("Number") or []
        unit = value.get("Unit") or ""
        return " ".join(str(x) for x in nums) + (f" {unit}" if unit else "")
    if value.get("String"):
        return str(value["String"])
    return json.dumps(value, ensure_ascii=False)


def _walk_pubchem_sections(sections: list[dict[str, Any]], path: tuple[str, ...] = ()) -> Iterable[tuple[str, dict[str, Any]]]:
    for section in sections or []:
        heading = section.get("TOCHeading") or "Unlabelled"
        current_path = path + (heading,)
        for info in section.get("Information", []) or []:
            text = _value_to_text(info.get("Value") or {})
            name = info.get("Name") or ""
            description = info.get("Description") or ""
            if text or description:
                combined = " | ".join(x for x in (name, description, text) if x)
                yield " > ".join(current_path), {**info, "_text": combined}
        yield from _walk_pubchem_sections(section.get("Section", []) or [], current_path)


def search_pubchem(
    chemical_name: str,
    *,
    cas_number: str | None = None,
    endpoint_codes: Iterable[str] | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    source = get_source("pubchem")
    with _client() as client:
        cid = _pubchem_cid(client, chemical_name, cas_number)
        prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,InChIKey,CanonicalSMILES/JSON"
        properties = client.get(prop_url)
        properties.raise_for_status()
        property_rows = properties.json().get("PropertyTable", {}).get("Properties", [])
        identity = property_rows[0] if property_rows else {"CID": cid}

        record_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
        response = client.get(record_url)
        response.raise_for_status()
        record = response.json()

    refs = _pubchem_reference_map(record)
    candidates: list[dict[str, Any]] = []
    for heading, info in _walk_pubchem_sections(record.get("Record", {}).get("Section", []) or []):
        # Limit extraction to environmentally relevant and property/effects sections.
        low_heading = heading.lower()
        low_text = info.get("_text", "").lower()
        if not any(token in low_heading + " " + low_text for token in (
            "environment", "fate", "degradation", "hydrolysis", "photolysis", "biodegrad", "soil", "sediment",
            "koc", "partition", "bcf", "ecotoxic", "aquatic", "lc50", "ec50", "noec", "solubility", "vapor", "vapour"
        )):
            continue
        ref_numbers = info.get("ReferenceNumber") or []
        if isinstance(ref_numbers, int):
            ref_numbers = [ref_numbers]
        first_ref = refs.get(ref_numbers[0]) if ref_numbers else None
        original_source = None
        original_url = None
        if first_ref:
            original_source = first_ref.get("SourceName") or first_ref.get("Citation")
            original_url = first_ref.get("URL")
        found = extract_endpoint_candidates_from_text(
            info.get("_text", ""), source_key="pubchem", source_name=source["name"], chemical_name=chemical_name,
            cas_number=cas_number, source_record_id=f"CID:{cid}",
            source_url=original_url or f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
            original_source=original_source or heading, rights_status="third_party_annotation_source_terms_apply",
            import_allowed=True, extraction_status="secondary_annotation_machine_extracted_unreviewed",
            endpoint_filter=endpoint_codes,
        )
        for item in found:
            item["notes"] = f"PubChem PUG View section: {heading}. Treat as secondary aggregation; consult the cited original source."
        candidates.extend(found)
        if len(candidates) >= limit:
            break

    return {
        "source_key": "pubchem", "status": "ok", "identity": identity,
        "candidates": candidates[:limit],
        "warnings": ["PubChem annotations are secondary/third-party information. Review the original source before regulatory selection."],
    }


def _epmc_query(chemical_name: str, cas_number: str | None, endpoint_codes: Iterable[str] | None) -> str:
    chemical_terms = [f'"{chemical_name}"']
    if cas_number:
        chemical_terms.append(f'"{cas_number}"')
    endpoint_codes = set(endpoint_codes or [])
    vocab: list[str] = []
    mapping = {
        "FATE.MANURE_DT50": ["manure", "slurry", "dung", "degradation", "DT50"],
        "FATE.SOIL_DT50": ["soil", "degradation", "DT50"],
        "FATE.HYDROLYSIS_DT50": ["hydrolysis", "half-life", "DT50"],
        "FATE.PHOTOLYSIS_DT50": ["photolysis", "photodegradation", "half-life"],
        "FATE.WATER_SEDIMENT_DT50": ["water sediment", "degradation", "DT50"],
        "FATE.WATER_DT50": ["aqueous", "surface water", "degradation", "half-life"],
        "FATE.BIODEGRADATION": ["biodegradation", "ready biodegradability", "activated sludge"],
        "FATE.WWTP_REMOVAL": ["wastewater removal", "WWTP removal", "sewage treatment", "activated sludge"],
        "SORPTION.KOC": ["Koc", "sorption", "adsorption"],
        "SORPTION.KD": ["Kd", "sorption", "adsorption"],
        "BIOACCUMULATION.BCF": ["BCF", "bioconcentration"],
        "ECOTOX.AQUATIC.LC50": ["LC50", "ecotoxicity"],
        "ECOTOX.AQUATIC.EC50": ["EC50", "ecotoxicity"],
        "ECOTOX.AQUATIC.NOEC": ["NOEC", "ecotoxicity"],
    }
    if endpoint_codes:
        for code in endpoint_codes:
            vocab.extend(mapping.get(code, []))
    else:
        vocab = ["environmental fate", "degradation", "biodegradation", "hydrolysis", "photolysis", "manure", "soil", "sediment", "Koc", "ecotoxicity"]
    vocab = list(dict.fromkeys(vocab))
    chemical_clause = " OR ".join(chemical_terms)
    endpoint_clause = " OR ".join(f'"{term}"' if " " in term else term for term in vocab)
    return f"({chemical_clause}) AND ({endpoint_clause})"


def _epmc_year(row: dict[str, Any]) -> int | None:
    value = row.get("pubYear") or row.get("firstPublicationDate")
    if not value:
        return None
    match = re.search(r"\d{4}", str(value))
    return int(match.group()) if match else None


def _epmc_fulltext_text(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    # Remove reference list to reduce false extraction from cited titles.
    for refs in root.findall(".//ref-list"):
        refs.clear()
    parts = [node.text.strip() for node in root.iter() if node.text and node.text.strip()]
    return " ".join(parts)


def search_europe_pmc(
    chemical_name: str,
    *,
    cas_number: str | None = None,
    endpoint_codes: Iterable[str] | None = None,
    limit: int = 20,
    include_open_access_full_text: bool = True,
    max_full_text_articles: int = 3,
) -> dict[str, Any]:
    source = get_source("europe_pmc")
    query = _epmc_query(chemical_name, cas_number, endpoint_codes)
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": min(max(limit, 5), 40)}
    with _client() as client:
        response = client.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params=params)
        response.raise_for_status()
        results = response.json().get("resultList", {}).get("result", []) or []
        candidates: list[dict[str, Any]] = []
        studies: list[dict[str, Any]] = []
        full_text_count = 0
        for row in results:
            pmid = row.get("pmid")
            pmcid = row.get("pmcid")
            doi = row.get("doi")
            title = _plain_text(row.get("title"))
            abstract = _plain_text(row.get("abstractText"))
            source_id = pmcid or pmid or doi or row.get("id")
            url = f"https://europepmc.org/article/MED/{pmid}" if pmid else (f"https://europepmc.org/article/PMC/{pmcid}" if pmcid else None)
            study = {
                "source_record_id": source_id, "title": title, "publication_year": _epmc_year(row),
                "doi": doi, "pmid": pmid, "pmcid": pmcid, "is_open_access": str(row.get("isOpenAccess", "N")).upper() == "Y",
                "journal": row.get("journalTitle"), "author_string": row.get("authorString"), "source_url": url,
            }
            studies.append(study)
            if abstract:
                candidates.extend(extract_endpoint_candidates_from_text(
                    abstract, source_key="europe_pmc", source_name=source["name"], chemical_name=chemical_name,
                    cas_number=cas_number, source_record_id=source_id, source_url=url, publication_title=title,
                    publication_year=_epmc_year(row), doi=doi, pmid=pmid, pmcid=pmcid,
                    original_source=row.get("journalTitle"), rights_status="abstract_metadata_source_terms_apply",
                    import_allowed=True, extraction_status="abstract_machine_extracted_unreviewed",
                    endpoint_filter=endpoint_codes,
                ))
            if include_open_access_full_text and pmcid and study["is_open_access"] and full_text_count < max_full_text_articles:
                try:
                    ft = client.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
                    if ft.status_code == 200 and ft.text.strip().startswith("<"):
                        full_text_count += 1
                        full_text = _epmc_fulltext_text(ft.text)
                        candidates.extend(extract_endpoint_candidates_from_text(
                            full_text, source_key="europe_pmc", source_name=source["name"], chemical_name=chemical_name,
                            cas_number=cas_number, source_record_id=source_id, source_url=url, publication_title=title,
                            publication_year=_epmc_year(row), doi=doi, pmid=pmid, pmcid=pmcid,
                            original_source=row.get("journalTitle"), rights_status="open_access_article_licence_requires_review",
                            import_allowed=True, extraction_status="open_access_fulltext_machine_extracted_unreviewed",
                            endpoint_filter=endpoint_codes,
                        ))
                except (httpx.HTTPError, ET.ParseError):
                    pass
            if len(candidates) >= limit:
                break

    # unique candidate ids and cap
    unique: dict[str, dict[str, Any]] = {c["candidate_id"]: c for c in candidates}
    return {
        "source_key": "europe_pmc", "status": "ok", "query": query,
        "studies": studies[:limit], "candidates": list(unique.values())[:limit],
        "warnings": ["Machine-extracted literature values are candidates only. Confirm the article, matrix, endpoint definition, test conditions and article licence before use."],
    }


def search_sources(
    *,
    chemical_name: str,
    cas_number: str | None,
    source_keys: Iterable[str],
    endpoint_codes: Iterable[str] | None = None,
    limit_per_source: int = 20,
    include_open_access_full_text: bool = True,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    all_candidates: list[dict[str, Any]] = []
    for key in source_keys:
        source = get_source(key)
        if not source.get("search_enabled"):
            results.append({
                "source_key": key, "status": "not_live_searchable",
                "candidates": [], "warnings": [source.get("notes", "Source is not enabled for live search.")],
            })
            continue
        try:
            if key == "pubchem":
                result = search_pubchem(chemical_name, cas_number=cas_number, endpoint_codes=endpoint_codes, limit=limit_per_source)
            elif key == "europe_pmc":
                result = search_europe_pmc(
                    chemical_name, cas_number=cas_number, endpoint_codes=endpoint_codes,
                    limit=limit_per_source, include_open_access_full_text=include_open_access_full_text,
                )
            elif key == "epa_ecotox":
                from .ecotox_local import search_ecotox_local
                result = search_ecotox_local(
                    chemical_name, cas_number=cas_number, endpoint_codes=endpoint_codes, limit=limit_per_source,
                )
            else:
                result = {"source_key": key, "status": "not_implemented", "candidates": [], "warnings": ["Adapter registered but live search implementation is not yet enabled."]}
        except (httpx.HTTPError, LookupError, ValueError, json.JSONDecodeError) as exc:
            result = {"source_key": key, "status": "error", "candidates": [], "warnings": [f"{type(exc).__name__}: {exc}"]}
        results.append(result)
        all_candidates.extend(result.get("candidates") or [])

    return {
        "chemical_name": chemical_name, "cas_number": cas_number,
        "searched_at": date.today().isoformat(), "source_results": results,
        "candidates": all_candidates,
        "review_rule": "No machine-extracted or aggregated value is selected automatically. A scientist must review context and explicitly import evidence.",
    }


def candidate_import_policy(source_key: str, rights_asserted: bool = False) -> tuple[bool, str]:
    source = get_source(source_key)
    status = source["commercial_status"]
    if source["access_mode"] == "blocked":
        return False, "This source is blocked from EnviroChem integration."
    if status in {"commercial_licence_required", "formal_letter_of_access_required"} and not rights_asserted:
        return False, "Commercial rights/letter of access must be explicitly confirmed before importing this source into a commercial assessment database."
    return True, "Candidate may be staged for professional review; source-specific rights and original-study context still apply."


def candidate_provenance_hash(candidate: dict[str, Any]) -> str:
    return sha256(json.dumps(candidate, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
