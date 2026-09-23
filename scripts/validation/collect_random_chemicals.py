"""Validation pass 2 (collection): random REAL chemicals from the local ECOTOX index, resolved via the app's own
PubChem resolver AND independently via EPA CompTox; experimental properties pulled from CompTox. Cached to jsonl.
Never touches the app database."""
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])
RUNS = _P(ROOT) / "data" / "validation_runs"  # gitignored working area; collected records land here
RUNS.mkdir(parents=True, exist_ok=True)
import json, os, random, re, sys, time
sys.path.insert(0, ROOT)
import httpx
from app.services.identity import resolve_pubchem_identity

OUT = os.path.join(str(RUNS), "val2_records.jsonl")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
SEED = 20260923

key = None
for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
    if line.startswith("COMPTOX_API_KEY="):
        key = line.split("=", 1)[1].strip()
H = {"x-api-key": key, "User-Agent": "FateIntel-validation/1.0"}
B = "https://comptox.epa.gov/ctx-api"

idx = json.load(open(os.path.join(ROOT, "data", "ecotox_index.json")))
cas_all = sorted(idx["offsets"])
rng = random.Random(SEED)
sample = rng.sample(cas_all, N)

done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding="utf-8"):
        done.add(json.loads(l)["cas"])

def cas_ok(c):
    m = re.fullmatch(r"(\d{2,7})-(\d{2})-(\d)", c)
    if not m: return False
    digits = (m.group(1) + m.group(2))[::-1]
    return sum((i + 1) * int(d) for i, d in enumerate(digits)) % 10 == int(m.group(3))

def get(client, url, retries=3):
    for a in range(retries):
        try:
            r = client.get(url, headers=H, timeout=25)
            if r.status_code == 429:
                time.sleep(3 + 2 * a); continue
            return r
        except httpx.HTTPError:
            time.sleep(2)
    return None

with httpx.Client() as client, open(OUT, "a", encoding="utf-8") as out:
    for cas in sample:
        if cas in done: continue
        rec = {"cas": cas, "cas_checksum_ok": cas_ok(cas), "n_ecotox": len(idx["offsets"][cas])}
        # --- independent: EPA CompTox
        r = get(client, f"{B}/chemical/search/equal/{cas}")
        if r is not None and r.status_code == 200 and r.json():
            m = r.json()[0]; rec["ct_dtxsid"] = m["dtxsid"]; rec["ct_name"] = m.get("preferredName")
            d = get(client, f"{B}/chemical/detail/search/by-dtxsid/{m['dtxsid']}")
            if d is not None and d.status_code == 200:
                dj = d.json(); rec["ct_formula"] = dj.get("molFormula"); rec["ct_mass"] = dj.get("averageMass"); rec["ct_inchikey"] = dj.get("inchikey"); rec["ct_smiles"] = dj.get("smiles")
            e = get(client, f"{B}/chemical/property/experimental/search/by-dtxsid/{m['dtxsid']}")
            if e is not None and e.status_code == 200:
                props = {}
                for p in e.json():
                    if p.get("propValue") is None: continue
                    props.setdefault(p["propName"], []).append(p["propValue"])
                keep = {k: v for k, v in props.items() if k in ("LogKow: Octanol-Water", "Soil Adsorp. Coeff. (Koc)", "Bioconcentration Factor", "Bioaccumulation Factor", "Water Solubility", "Henry's Law Constant", "Vapor Pressure", "pKa Acidic Apparent", "pKa Basic Apparent", "Melting Point", "Boiling Point")}
                rec["ct_exp"] = keep
        else:
            rec["ct_status"] = None if r is None else r.status_code
        # --- the app's own resolver
        try:
            c = resolve_pubchem_identity(cas, "cas")
            rec["app"] = {k: c.get(k) for k in ("pubchem_cid", "preferred_name", "cas_number", "molecular_formula", "molecular_weight_g_mol", "inchikey", "smiles", "xlogp_candidate")}
        except Exception as ex:
            rec["app_error"] = f"{type(ex).__name__}: {ex}"[:200]
        time.sleep(0.45)
        out.write(json.dumps(rec) + "\n"); out.flush()
print("done", N)
