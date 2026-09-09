"""One-off converter: NORMAN EAWAGTPS + SusDat CSV exports -> app/data/*.json.

Not a runtime dependency -- run manually whenever a newer NORMAN snapshot should
replace the shipped reference files:

    python scripts/convert_norman_references.py \
        --eawagtps path/to/EawagTPandParents.csv \
        --susdat path/to/susdat_snapshot.csv

EAWAGTPS (NORMAN Suspect List Exchange S66, https://zenodo.org/records/10628455)
stores one row per (entity, pair) combination: a parent appears once per known
transformation product, and a TP row carries the full transformation metadata
(reaction type, mass/formula difference, ionisation) for that specific
parent->TP pair. This script keeps only real, curated pairs -- nothing here is
predicted or inferred.

SusDat (S0) stores one row per substance, including OPERA-style predicted ESI
mode/platform fields. Only the columns this feature actually uses are kept, to
avoid shipping SusDat's ~90 QSAR/toxicity columns that are out of scope here.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"

EAWAGTPS_CITATION = (
    "NORMAN Network Suspect List Exchange -- EAWAGTPS (S66): curated parent/"
    "transformation-product pairs originating from Eawag. "
    "https://doi.org/10.5281/zenodo.10628455"
)
EAWAGTPS_SOURCE_URL = "https://zenodo.org/records/10628455"
SUSDAT_CITATION = (
    "NORMAN Network Suspect List Exchange -- SusDat (S0): substance identity plus "
    "OPERA-model-predicted ionisation mode and chromatographic platform. "
    "https://www.norman-network.com/nds/SLE/"
)
SUSDAT_SOURCE_URL = "https://www.norman-network.com/nds/SLE/"


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def convert_eawagtps(source: Path, dest: Path) -> int:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        eawag_id = row.get("Eawag_ID")
        if eawag_id and eawag_id not in by_id:
            by_id[eawag_id] = row

    by_parent_inchikey: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("ParentOrTP") != "TP":
            continue
        parent_id = row.get("Eawag_ID_of_Pair")
        parent_row = by_id.get(parent_id or "")
        parent_inchikey = _text((parent_row or {}).get("InChIKey"))
        tp_inchikey = _text(row.get("InChIKey"))
        if not parent_inchikey or not tp_inchikey:
            continue
        entry = {
            "tp_name": _text(row.get("Name")),
            "tp_inchikey": tp_inchikey,
            "tp_smiles": _text(row.get("SMILES")),
            "tp_formula": _text(row.get("MolecularFormula")),
            "tp_exact_mass_da": _float(row.get("ExactMass")),
            "tp_cas": _text(row.get("CAS")),
            "tp_pubchem_cid": _text(row.get("PubChem_CID")),
            "transformation_type": _text(row.get("Transformation")),
            "ionization": _text(row.get("Ionization")),
            "mass_diff_da": _float(row.get("Mass_Diff")),
            "formula_diff": _text(row.get("Form_Diff")),
            "tanimoto_dissimilarity": _float(row.get("TanimotoDissimilarity")),
            "source_key": "norman_eawagtps",
            "source_record_id": row.get("Eawag_ID"),
            "source_url": EAWAGTPS_SOURCE_URL,
        }
        by_parent_inchikey.setdefault(parent_inchikey, []).append(entry)

    for entries in by_parent_inchikey.values():
        entries.sort(key=lambda entry: (entry["tp_name"] or "", entry["source_record_id"] or ""))

    payload = {
        "citation": EAWAGTPS_CITATION,
        "source_url": EAWAGTPS_SOURCE_URL,
        "pair_count": sum(len(v) for v in by_parent_inchikey.values()),
        "parent_count": len(by_parent_inchikey),
        "by_parent_inchikey": by_parent_inchikey,
    }
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload["pair_count"]


SUSDAT_FIELDS = {
    "StdInChIKey": "inchikey",
    "M+H+": "precursor_m_plus_h_da",
    "M-H-": "precursor_m_minus_h_da",
    "Pred. ESI mode": "predicted_esi_mode",
    "Prob. +ESI": "probability_positive_esi",
    "Prob. -ESI": "probability_negative_esi",
    "Pred. Chromatography": "predicted_chromatography",
    "Prob. of GC": "probability_gc",
    "Prob. RPLC": "probability_rplc",
    "Preferable Platform by decision Tree": "preferable_platform",
}


def convert_susdat(source: Path, data_dest: Path, index_dest: Path) -> int:
    """Write SusDat as one compact JSON object per line plus a small inchikey->byte-offset index.

    SusDat covers ~109k substances; even slimmed to the columns this feature needs, a single
    eagerly-loaded JSON dict comes out to tens of megabytes, which is too much to parse into
    memory on every app start/reload for a feature that only ever needs one record at a time.
    The index (inchikey -> byte offset into the JSONL file) is the only piece kept in memory;
    a lookup seeks straight to its line rather than scanning or loading the rest.
    """
    seen: set[str] = set()
    index: dict[str, int] = {}
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [key for key in SUSDAT_FIELDS if key not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"SusDat source is missing expected columns: {missing}")
        with data_dest.open("w", encoding="utf-8", newline="\n") as out:
            offset = 0
            for row in reader:
                inchikey = _text(row.get("StdInChIKey"))
                if not inchikey or inchikey in seen:
                    continue
                seen.add(inchikey)
                record: dict[str, Any] = {
                    "inchikey": inchikey,
                    "source_key": "norman_susdat",
                    "source_url": SUSDAT_SOURCE_URL,
                }
                for source_col, dest_key in SUSDAT_FIELDS.items():
                    if source_col == "StdInChIKey":
                        continue
                    raw = row.get(source_col)
                    if dest_key.startswith("probability_") or dest_key.startswith("precursor_"):
                        record[dest_key] = _float(raw)
                    else:
                        record[dest_key] = _text(raw)
                line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
                index[inchikey] = offset
                out.write(line)
                offset += len(line.encode("utf-8"))

    index_payload = {
        "citation": SUSDAT_CITATION,
        "source_url": SUSDAT_SOURCE_URL,
        "record_count": len(index),
        "data_file": data_dest.name,
        "offsets": index,
    }
    index_dest.write_text(json.dumps(index_payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return len(index)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eawagtps", type=Path, required=True, help="Path to EawagTPandParents.csv")
    parser.add_argument("--susdat", type=Path, required=True, help="Path to a NORMAN SusDat CSV snapshot")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pair_count = convert_eawagtps(args.eawagtps, DATA_DIR / "eawag_transformation_products.json")
    print(f"Wrote {pair_count} known parent->TP pairs to app/data/eawag_transformation_products.json")

    record_count = convert_susdat(
        args.susdat,
        DATA_DIR / "norman_susdat_reference.jsonl",
        DATA_DIR / "norman_susdat_index.json",
    )
    print(
        f"Wrote {record_count} SusDat identification records to "
        "app/data/norman_susdat_reference.jsonl (indexed by app/data/norman_susdat_index.json)"
    )


if __name__ == "__main__":
    main()
