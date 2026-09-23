from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])
RUNS = _P(ROOT) / "data" / "validation_runs"  # gitignored working area; collected records land here
RUNS.mkdir(parents=True, exist_ok=True)
import json, os, sys, time
sys.path.insert(0, ROOT)
from app.services.identity import resolve_pubchem_identity
p = os.path.join(str(RUNS), "val2_records.jsonl")
recs = [json.loads(l) for l in open(p, encoding="utf-8")]
fixed = still = 0
for r in recs:
    e = r.get("app_error", "")
    if "app" in r or not any(t in e for t in ("503", "Timeout", "404")): continue
    time.sleep(1.2)
    try:
        c = resolve_pubchem_identity(r["cas"], "cas")
        r["app"] = {k: c.get(k) for k in ("pubchem_cid", "preferred_name", "cas_number", "molecular_formula", "molecular_weight_g_mol", "inchikey", "smiles", "xlogp_candidate")}
        r.pop("app_error", None); r["app_retry"] = "resolved_after_fix"; fixed += 1
    except Exception as ex:
        r["app_error"] = f"{type(ex).__name__}: {ex}"[:200]; r["app_retry"] = "still_failing"; still += 1
open(p, "w", encoding="utf-8").write("\n".join(json.dumps(r) for r in recs) + "\n")
print("resolved after fix:", fixed, "still failing:", still)
