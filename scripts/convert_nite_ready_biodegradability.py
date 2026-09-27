"""One-off conversion: the raw NITE ready-biodegradability export (CSV) -> app/data/nite_ready_biodegradability.json.

Not a runtime dependency; run again only if the source CSV is re-exported. The CSV (record_id, cas_number, smiles,
names, biodeg_percent, biodeg_percent_min, biodeg_percent_max, duration_days, meta_data) came from a read-only export
of the "Biodegradation NITE" table in a locally restored QSAR Toolbox 4.9 database (Japan METI/CSCL, OECD TG 301C/
301D/302C/302D); see app/services/nite_ready_biodegradability.py for the full provenance and licence caveat.

Usage: python scripts/convert_nite_ready_biodegradability.py --source path/to/nite_ready_biodegradability_raw.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import sys

from rdkit import Chem

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `from app...` works when run as a plain script
from app.services.nite_ready_biodegradability import classify_ready_biodegradability  # noqa: E402

OUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "nite_ready_biodegradability.json"
META_FIELD_RE = re.compile(r'"([^"]+)"=>(?:"([^"]*)"|NULL)')


def _meta(text: str) -> dict[str, str]:
    return {key: value or "" for key, value in META_FIELD_RE.findall(text or "")}


def convert(source: Path, out_path: Path = OUT_PATH) -> None:
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    records: dict[str, list[dict]] = {}
    by_inchikey: dict[str, list[dict]] = {}
    skipped = 0
    for row in rows:
        smiles = (row.get("smiles") or "").strip()
        mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is None:
            skipped += 1
            continue
        key = Chem.MolToSmiles(mol)
        inchikey = Chem.MolToInchiKey(mol)
        meta = _meta(row.get("meta_data", ""))
        percent = float(row["biodeg_percent"]) if row.get("biodeg_percent") not in (None, "") else None
        guideline = meta.get("Test guideline") or None
        entry = {
            "cas_number": row.get("cas_number") or None,
            "names": row.get("names") or None,
            "biodeg_percent": percent,
            "biodeg_percent_min": float(row["biodeg_percent_min"]) if row.get("biodeg_percent_min") not in (None, "") else None,
            "biodeg_percent_max": float(row["biodeg_percent_max"]) if row.get("biodeg_percent_max") not in (None, "") else None,
            "duration_days": float(row["duration_days"]) if row.get("duration_days") not in (None, "") else None,
            "test_guideline": guideline,
            "endpoint_type": meta.get("Endpoint type") or None,
            "year": meta.get("Year") or None,
            "record_id": row.get("record_id"),
            "readily_biodegradable": classify_ready_biodegradability(percent, guideline),
        }
        records.setdefault(key, []).append(entry)
        by_inchikey.setdefault(inchikey, []).append({**entry, "canonical_smiles": key})
    out_path.write_text(json.dumps({"version": "1.0", "source": "nite_ready_biodegradability", "records": records, "by_inchikey": by_inchikey}, indent=0), encoding="utf-8")
    print(f"{len(rows)} rows -> {len(records)} distinct structures, {skipped} skipped (no parseable SMILES); wrote {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    convert(args.source, args.out)
