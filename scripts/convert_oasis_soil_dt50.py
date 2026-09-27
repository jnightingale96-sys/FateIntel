"""One-off conversion: the raw OASIS soil-DT50 export (CSV) -> app/data/oasis_soil_dt50.json, keyed by canonical SMILES.

Not a runtime dependency; run again only if the source CSV is re-exported. The CSV itself (record_id, cas_number,
smiles, names, dt50_mean_days, dt50_min_days, dt50_max_days, mean_qualifier) came from a read-only export of the
"Biodegradation in soil OASIS" table in a locally restored QSAR Toolbox 4.9 database (LMC Bourgas, v1.1, 2009);
see app/services/oasis_soil_dt50.py for the full provenance and licence caveat.

Usage: python scripts/convert_oasis_soil_dt50.py --source path/to/oasis_soil_dt50.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from rdkit import Chem

OUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "oasis_soil_dt50.json"


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
        entry = {
            "cas_number": row.get("cas_number") or None,
            "names": row.get("names") or None,
            "dt50_mean_days": float(row["dt50_mean_days"]) if row.get("dt50_mean_days") else None,
            "dt50_min_days": float(row["dt50_min_days"]) if row.get("dt50_min_days") else None,
            "dt50_max_days": float(row["dt50_max_days"]) if row.get("dt50_max_days") else None,
            "qualifier": int(row["mean_qualifier"]) if row.get("mean_qualifier") else 0,
            "record_id": row.get("record_id"),
        }
        records.setdefault(key, []).append(entry)
        by_inchikey.setdefault(inchikey, []).append({**entry, "canonical_smiles": key})
    out_path.write_text(json.dumps({"version": "1.0", "source": "oasis_soil_dt50", "records": records, "by_inchikey": by_inchikey}, indent=0), encoding="utf-8")
    print(f"{len(rows)} rows -> {len(records)} distinct structures, {skipped} skipped (no parseable SMILES); wrote {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    convert(args.source, args.out)
