"""One-off importer: EPA ECOTOX Knowledgebase bulk ASCII export -> local reference files.

Not a runtime dependency and not shipped in git (see .gitignore: data/ecotox_reference.jsonl,
data/ecotox_index.json). ECOTOX refreshes quarterly (https://cfpub.epa.gov/ecotox/), so this is
meant to be re-run periodically against a fresh download, the same way a reviewer would refresh
any other external database snapshot -- not committed as a static asset that goes stale silently.

Usage:

    python scripts/import_ecotox.py --source path/to/ecotox_ascii_MM_DD_YYYY/

``--source`` is the directory produced by extracting EPA's own bulk download zip
(https://cfpub.epa.gov/ecotox/, "ASCII Download" -> "Download .zip file"; confirmed live URL
pattern this session: https://gaftp.epa.gov/ecotox/ecotox_ascii_MM_DD_YYYY.zip). It must contain
tests.txt, results.txt, validation/chemicals.txt, validation/species.txt and
validation/references.txt, all pipe(|)-delimited, as EPA ships them.

Scope, deliberately narrow. FateIntel's ENDPOINT_CATALOG only has slots for aquatic
LC50/EC50/NOEC/EC10 (app/services/evidence_sources.py). This importer keeps only:

  - results.endpoint in {LC50, EC50, NOEC, EC10} (ECOTOX's own literal codes -- confirmed this
    session directly from validation/endpoint_codes.txt, no fuzzy mapping needed), and
  - the parent test's media_type in {AQU, FW, SW} (aqueous / fresh water / salt water --
    confirmed from validation/media_type_codes.txt), which excludes soil/terrestrial-medium
    tests that also carry these same endpoint codes (ECOTOX's LC50/EC50/NOEC/EC10 span both
    aquatic and terrestrial studies; mislabelling a terrestrial dietary-dose NOEC as
    "ECOTOX.AQUATIC.NOEC" would be a real correctness bug, not a simplification).

Rows are NOT filtered by concentration unit -- ECOTOX carries many units (mg/L, ppm, uM, etc.)
beyond the ng/L-g/L family app.reach.units currently normalises, and a reviewer may still find
value in a candidate FateIntel can't auto-convert yet. Unit handling stays a review-time decision,
matching every other evidence candidate in this app.

Verified against the actual bulk export this session (2026-09-19): ~725,600 tests, ~1,250,600
results, ~18,550 chemicals; ~347,000 tests have an aquatic media_type; combining both filters
keeps a five-figure subset of results -- these numbers will drift with each quarterly refresh,
which is expected and fine.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "data"

TARGET_ENDPOINTS = {"LC50", "EC50", "NOEC", "EC10"}
AQUATIC_MEDIA_TYPES = {"AQU", "FW", "SW"}

CITATION = (
    "US EPA ECOTOX Knowledgebase bulk ASCII export (https://cfpub.epa.gov/ecotox/), "
    "aquatic-medium LC50/EC50/NOEC/EC10 subset"
)


def _read_pipe_table(path: Path) -> csv.DictReader:
    handle = path.open(encoding="utf-8", newline="", errors="replace")
    return csv.DictReader(handle, delimiter="|")


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _to_float(value: str | None) -> float | None:
    value = _blank_to_none(value)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def format_cas(digits: str | None) -> str | None:
    """"1336363" -> "1336-36-3". ECOTOX stores CAS numbers with no separators."""

    digits = (digits or "").strip()
    if not digits.isdigit() or len(digits) < 3:
        return None
    return f"{digits[:-3]}-{digits[-3:-1]}-{digits[-1]}"


def load_chemicals(path: Path) -> dict[str, dict[str, Any]]:
    chemicals: dict[str, dict[str, Any]] = {}
    for row in _read_pipe_table(path):
        cas_digits = row.get("cas_number")
        if not cas_digits:
            continue
        chemicals[cas_digits] = {
            "chemical_name": _blank_to_none(row.get("chemical_name")),
            "dtxsid": _blank_to_none(row.get("dtxsid")),
        }
    return chemicals


def load_species(path: Path) -> dict[str, dict[str, Any]]:
    species: dict[str, dict[str, Any]] = {}
    for row in _read_pipe_table(path):
        number = row.get("species_number")
        if not number:
            continue
        species[number] = {
            "common_name": _blank_to_none(row.get("common_name")),
            "latin_name": _blank_to_none(row.get("latin_name")),
            "ecotox_group": _blank_to_none(row.get("ecotox_group")),
        }
    return species


def load_references(path: Path) -> dict[str, dict[str, Any]]:
    references: dict[str, dict[str, Any]] = {}
    for row in _read_pipe_table(path):
        number = row.get("reference_number")
        if not number:
            continue
        references[number] = {
            "author": _blank_to_none(row.get("author")),
            "title": _blank_to_none(row.get("title")),
            "source": _blank_to_none(row.get("source")),
            "publication_year": _blank_to_none(row.get("publication_year")),
            "doi": _blank_to_none(row.get("doi")),
        }
    return references


def load_aquatic_tests(path: Path) -> dict[str, dict[str, Any]]:
    """test_id -> the fields needed downstream, for tests whose media_type is aquatic only."""

    tests: dict[str, dict[str, Any]] = {}
    for row in _read_pipe_table(path):
        if row.get("media_type") not in AQUATIC_MEDIA_TYPES:
            continue
        test_id = row.get("test_id")
        if not test_id:
            continue
        tests[test_id] = {
            "test_cas": row.get("test_cas"),
            "species_number": row.get("species_number"),
            "reference_number": row.get("reference_number"),
            "media_type": row.get("media_type"),
            "exposure_type": _blank_to_none(row.get("exposure_type")),
            "study_duration_mean": _to_float(row.get("study_duration_mean")),
            "study_duration_unit": _blank_to_none(row.get("study_duration_unit")),
            "test_location": _blank_to_none(row.get("test_location")),
        }
    return tests


def convert(
    *,
    source_dir: Path,
    jsonl_dest: Path,
    index_dest: Path,
) -> tuple[int, int]:
    print("Loading validation/chemicals.txt ...", file=sys.stderr)
    chemicals = load_chemicals(source_dir / "validation" / "chemicals.txt")
    print(f"  {len(chemicals)} chemicals", file=sys.stderr)

    print("Loading validation/species.txt ...", file=sys.stderr)
    species = load_species(source_dir / "validation" / "species.txt")
    print(f"  {len(species)} species", file=sys.stderr)

    print("Loading validation/references.txt ...", file=sys.stderr)
    references = load_references(source_dir / "validation" / "references.txt")
    print(f"  {len(references)} references", file=sys.stderr)

    print("Loading tests.txt (aquatic media_type only) ...", file=sys.stderr)
    tests = load_aquatic_tests(source_dir / "tests.txt")
    print(f"  {len(tests)} aquatic-medium tests", file=sys.stderr)

    print("Streaming results.txt, filtering and joining ...", file=sys.stderr)
    index: dict[str, list[int]] = {}
    row_count = 0
    chemical_count: set[str] = set()

    jsonl_dest.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_dest.open("w", encoding="utf-8", newline="\n") as out:
        offset = 0
        for row in _read_pipe_table(source_dir / "results.txt"):
            endpoint = row.get("endpoint")
            if endpoint not in TARGET_ENDPOINTS:
                continue
            test = tests.get(row.get("test_id") or "")
            if test is None:
                continue
            cas_digits = test["test_cas"]
            cas_dashed = format_cas(cas_digits)
            if cas_dashed is None:
                continue
            chemical = chemicals.get(cas_digits, {})
            sp = species.get(test["species_number"] or "", {})
            ref = references.get(test["reference_number"] or "", {})

            record: dict[str, Any] = {
                "cas_number": cas_dashed,
                "chemical_name": chemical.get("chemical_name"),
                "dtxsid": chemical.get("dtxsid"),
                "endpoint": endpoint,
                "effect": _blank_to_none(row.get("effect")),
                "measurement": _blank_to_none(row.get("measurement")),
                "response_site": _blank_to_none(row.get("response_site")),
                "conc1_mean": _to_float(row.get("conc1_mean")),
                "conc1_unit": _blank_to_none(row.get("conc1_unit")),
                "obs_duration_mean": _to_float(row.get("obs_duration_mean")),
                "obs_duration_unit": _blank_to_none(row.get("obs_duration_unit")),
                "species_common_name": sp.get("common_name"),
                "species_latin_name": sp.get("latin_name"),
                "species_ecotox_group": sp.get("ecotox_group"),
                "media_type": test["media_type"],
                "exposure_type": test["exposure_type"],
                "study_duration_mean": test["study_duration_mean"],
                "study_duration_unit": test["study_duration_unit"],
                "test_location": test["test_location"],
                "reference_author": ref.get("author"),
                "reference_title": ref.get("title"),
                "reference_source": ref.get("source"),
                "reference_year": ref.get("publication_year"),
                "reference_doi": ref.get("doi"),
                "result_id": row.get("result_id"),
                "test_id": row.get("test_id"),
                "source_key": "epa_ecotox",
                "source_url": "https://cfpub.epa.gov/ecotox/",
            }
            line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
            index.setdefault(cas_dashed, []).append(offset)
            out.write(line)
            offset += len(line.encode("utf-8"))
            row_count += 1
            chemical_count.add(cas_dashed)

    index_payload = {
        "citation": CITATION,
        "source_url": "https://cfpub.epa.gov/ecotox/",
        "record_count": row_count,
        "chemical_count": len(chemical_count),
        "data_file": jsonl_dest.name,
        "offsets": index,
    }
    index_dest.write_text(json.dumps(index_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return row_count, len(chemical_count)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--source", type=Path, required=True,
        help="Path to the extracted ecotox_ascii_MM_DD_YYYY directory (must contain tests.txt, results.txt, validation/)",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Default: ./data")
    args = parser.parse_args()

    required = ["tests.txt", "results.txt", "validation/chemicals.txt", "validation/species.txt", "validation/references.txt"]
    missing = [name for name in required if not (args.source / name).exists()]
    if missing:
        raise SystemExit(f"--source is missing expected files: {missing}")

    row_count, chemical_count = convert(
        source_dir=args.source,
        jsonl_dest=args.output_dir / "ecotox_reference.jsonl",
        index_dest=args.output_dir / "ecotox_index.json",
    )
    print(
        f"Wrote {row_count} aquatic LC50/EC50/NOEC/EC10 records across {chemical_count} chemicals to "
        f"{args.output_dir / 'ecotox_reference.jsonl'} (indexed by {args.output_dir / 'ecotox_index.json'})"
    )


if __name__ == "__main__":
    main()
