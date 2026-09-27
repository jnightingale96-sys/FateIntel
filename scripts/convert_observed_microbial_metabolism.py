"""One-off conversion: the raw observed-microbial-metabolism export (CSV) -> app/data/observed_microbial_metabolism.json.

Not a runtime dependency; run again only if the source CSV is re-exported. The CSV (map_id, precursor_cas,
precursor_smiles, product_cas, product_smiles, quantity_percent, remark) came from a read-only export of the
"Observed Microbial metabolism" table in a locally restored QSAR Toolbox 4.9 database (LMC Bourgas + US EPA
ORD/NERL and ORD/NHEERL/MED, METAPATH platform, largely sourced from UM-BBD and the literature); see
app/services/analytical_identification.py's ``_OBSERVED_MICROBIAL_METABOLISM`` section for the full provenance
and licence caveat.

Every edge is a real, curated precursor -> product pair (not a predicted one); ``quantity_percent`` is present
for only 34 of 36,967 rows (no formation-fraction/yield data for the rest -- a known pair, not a known amount,
same limitation NORMAN EAWAGTPS already has). Keyed by the PRECURSOR's canonical InChIKey, which may itself be a
pathway intermediate, not only a root parent -- so the same lookup can be re-run on a product's own InChIKey to
follow a chain, exactly like the EAWAGTPS hand-off already does.

Usage: python scripts/convert_observed_microbial_metabolism.py --source path/to/observed_microbial_metabolism_raw.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

OUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "observed_microbial_metabolism.json"


def _structure(smiles: str) -> dict | None:
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return None
    return {
        "smiles": Chem.MolToSmiles(mol), "inchikey": Chem.MolToInchiKey(mol),
        "formula": rdMolDescriptors.CalcMolFormula(mol), "exact_mass_da": round(Descriptors.ExactMolWt(mol), 4),
    }


def convert(source: Path, out_path: Path = OUT_PATH) -> None:
    rows = list(csv.DictReader(source.open(encoding="utf-8")))
    by_parent: dict[str, dict[str, dict]] = defaultdict(dict)  # parent_inchikey -> product_inchikey -> entry
    skipped = 0
    for row in rows:
        precursor = _structure((row.get("precursor_smiles") or "").strip())
        product = _structure((row.get("product_smiles") or "").strip())
        if precursor is None or product is None or precursor["inchikey"] == product["inchikey"]:
            skipped += 1
            continue
        bucket = by_parent[precursor["inchikey"]]
        existing = bucket.get(product["inchikey"])
        map_id = row.get("map_id")
        if existing is not None:
            if map_id and map_id not in existing["source_record_ids"]:
                existing["source_record_ids"].append(map_id)
            continue
        bucket[product["inchikey"]] = {
            "tp_smiles": product["smiles"], "tp_inchikey": product["inchikey"], "tp_formula": product["formula"],
            "tp_exact_mass_da": product["exact_mass_da"], "tp_cas": (row.get("product_cas") or "0") if (row.get("product_cas") or "0") != "0" else None,
            "quantity_percent": float(row["quantity_percent"]) if row.get("quantity_percent") else None,
            "source_record_ids": [map_id] if map_id else [],
        }
    total_edges = sum(len(v) for v in by_parent.values())
    out_path.write_text(json.dumps({
        "version": "1.0", "source": "observed_microbial_metabolism",
        "by_parent_inchikey": {k: list(v.values()) for k, v in by_parent.items()},
    }, indent=0), encoding="utf-8")
    print(f"{len(rows)} rows -> {len(by_parent)} precursor structures, {total_edges} distinct edges, {skipped} skipped; wrote {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    convert(args.source, args.out)
