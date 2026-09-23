"""Collect a RANDOM sample of real chemicals that have experimental Koc in EPA CompTox (OPERA), plus their logKow/pKa."""
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])
RUNS = _P(ROOT) / "data" / "validation_runs"  # gitignored working area; collected records land here
RUNS.mkdir(parents=True, exist_ok=True)
import json, os, random, sys, time, statistics as st
import httpx
HERE = str(RUNS)
OUT = os.path.join(HERE, "val4_records.jsonl")
key = [l.split("=", 1)[1].strip() for l in open(os.path.join(ROOT, ".env"), encoding="utf-8") if l.startswith("COMPTOX_API_KEY=")][0]
H = {"x-api-key": key}; B = "https://comptox.epa.gov/ctx-api"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
with httpx.Client(timeout=40) as c:
    rng = json.loads(c.get(f"{B}/chemical/property/experimental/search/by-range/Soil%20Adsorp.%20Coeff.%20(Koc)/0/100000000", headers=H).text)
    by = {}
    for r in rng: by.setdefault(r["dtxsid"], []).append(r["propValue"])
    ids = sorted(by); random.Random(20260923).shuffle(ids); ids = ids[:N]
    done = set(json.loads(l)["dtxsid"] for l in open(OUT, encoding="utf-8")) if os.path.exists(OUT) else set()
    with open(OUT, "a", encoding="utf-8") as out:
        for d in ids:
            if d in done: continue
            rec = {"dtxsid": d, "koc_values": by[d]}
            for attempt in range(3):
                try:
                    e = c.get(f"{B}/chemical/property/experimental/search/by-dtxsid/{d}", headers=H)
                    if e.status_code == 200:
                        props = {}
                        for p in e.json():
                            if p.get("propValue") is not None: props.setdefault(p["propName"], []).append(p["propValue"])
                        rec["exp"] = {k: v for k, v in props.items() if k in ("LogKow: Octanol-Water", "pKa Acidic Apparent", "pKa Basic Apparent", "Water Solubility", "Melting Point")}
                        rec["smiles"] = next((p.get("smiles") for p in e.json()), None)
                        break
                except httpx.HTTPError:
                    time.sleep(2)
            dd = c.get(f"{B}/chemical/detail/search/by-dtxsid/{d}", headers=H)
            if dd.status_code == 200:
                j = dd.json(); rec["name"] = j.get("preferredName"); rec["casrn"] = j.get("casrn"); rec["formula"] = j.get("molFormula")
            out.write(json.dumps(rec) + "\n"); out.flush(); time.sleep(0.15)
print("done")
