"""Validation pass 2 (analysis) over val2_records.jsonl."""
from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])
RUNS = _P(ROOT) / "data" / "validation_runs"  # gitignored working area; collected records land here
RUNS.mkdir(parents=True, exist_ok=True)
import json, math, os, re, statistics as st, sys
sys.path.insert(0, ROOT)
from collections import Counter
from app.services import sorption as so
from app.services.pbt_pmt_classifier import classify_pbt_and_vpvb, classify_pmt_and_vpvm

HERE = str(RUNS)
recs = [json.loads(l) for l in open(os.path.join(HERE, "val2_records.jsonl"), encoding="utf-8")]
print("records:", len(recs))

# ---- atomic weights (IUPAC standard, abridged) for independent MW-from-formula
AW = {"H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.086, "P": 30.974, "S": 32.06,
      "Cl": 35.45, "K": 39.098, "Ca": 40.078, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38,
      "As": 74.922, "Br": 79.904, "Se": 78.971, "Sr": 87.62, "Mo": 95.95, "Ag": 107.868, "Cd": 112.414, "Sn": 118.71, "Sb": 121.76, "I": 126.904,
      "Ba": 137.327, "W": 183.84, "Pt": 195.084, "Au": 196.967, "Hg": 200.592, "Pb": 207.2, "B": 10.81, "Li": 6.94, "Be": 9.012, "Ti": 47.867,
      "V": 50.942, "Ga": 69.723, "Ge": 72.630, "Zr": 91.224, "Ce": 140.116, "La": 138.905, "Tl": 204.38, "Bi": 208.98, "U": 238.029}

def formula_mass(f):
    if not f or any(c in f for c in ".()[]·"): return None
    toks = re.findall(r"([A-Z][a-z]?)(\d*)", f)
    if "".join(a + b for a, b in toks) != f: return None
    m = 0.0
    for el, n in toks:
        if el not in AW: return None
        m += AW[el] * (int(n) if n else 1)
    return m

def cas_ok(c): return c and re.fullmatch(r"\d{2,7}-\d{2}-\d", c) is not None

# ================= identity =================
status = Counter(); disagree = []; mw_bad = []; cas_bad = []
for r in recs:
    if not r["cas_checksum_ok"]: cas_bad.append(r["cas"])
    ct = "ct_dtxsid" in r; ap = "app" in r
    status[(("CT" if ct else "-"), ("APP" if ap else ("APP-ERR:" + r.get("app_error", "")[:40] if "app_error" in r else "-")))] += 1
    if ct and ap and r.get("ct_inchikey") and r["app"].get("inchikey"):
        same_conn = r["ct_inchikey"][:14] == r["app"]["inchikey"][:14]
        same_formula = (r.get("ct_formula") == r["app"].get("molecular_formula"))
        mass_ct = r.get("ct_mass"); mass_app = r["app"].get("molecular_weight_g_mol")
        same_mass = mass_ct is not None and mass_app is not None and abs(mass_ct - mass_app) < 0.1
        if not (same_conn and same_formula and same_mass):
            disagree.append((r["cas"], r.get("ct_name"), r["app"].get("preferred_name"), same_conn, same_formula, round(mass_ct or 0, 2), round(mass_app or 0, 2)))
    for src, f, m in (("CT", r.get("ct_formula"), r.get("ct_mass")), ("APP", r.get("app", {}).get("molecular_formula"), r.get("app", {}).get("molecular_weight_g_mol"))):
        calc = formula_mass(f)
        if calc and m and abs(calc - m) > 0.05 * max(1, m / 100) and abs(calc - m) > 0.1:
            mw_bad.append((r["cas"], src, f, round(calc, 3), round(m, 3)))
print("\n== IDENTITY ==")
print("CAS check-digit failures:", cas_bad)
print("resolver outcome matrix:", dict(status))
print(f"CompTox vs app-resolver disagreements: {len(disagree)}")
for d in disagree[:25]: print("  ", d)
print(f"MW-vs-formula inconsistencies (independent atomic weights): {len(mw_bad)}")
for d in mw_bad[:15]: print("  ", d)
errs = Counter(r.get("app_error", "")[:70] for r in recs if "app_error" in r)
print("app resolver errors:", dict(errs))

# ================= XLogP vs experimental logKow =================
print("\n== PubChem XLogP vs experimental logKow (CompTox median) ==")
pairs = []
for r in recs:
    x = r.get("app", {}).get("xlogp_candidate"); e = (r.get("ct_exp") or {}).get("LogKow: Octanol-Water")
    if x is not None and e:
        pairs.append((r["cas"], r.get("ct_name"), float(x), st.median(e)))
if pairs:
    d = [p[2] - p[3] for p in pairs]
    print(f"n={len(pairs)} bias={st.mean(d):+.2f} MAE={st.mean(abs(x) for x in d):.2f} RMSE={math.sqrt(st.mean(x*x for x in d)):.2f}  within0.5={sum(abs(x)<=0.5 for x in d)/len(d):.0%} within1={sum(abs(x)<=1 for x in d)/len(d):.0%}")
    for p in sorted(pairs, key=lambda p: -abs(p[2] - p[3]))[:8]: print("   worst:", p[0], p[1], f"XLogP={p[2]} exp={p[3]}")

# ================= sorption vs experimental Koc =================
print("\n== Sorption models vs experimental (OPERA) Koc, pH 7, fOC 0.02 ==")
rows = []
for r in recs:
    ex = r.get("ct_exp") or {}
    koc = ex.get("Soil Adsorp. Coeff. (Koc)"); lk = ex.get("LogKow: Octanol-Water")
    lk = [v for v in (lk or []) if -10 <= v <= 20]   # implausible source values are refused by the app; drop them here
    if not koc or not lk: continue
    lkow = st.median(lk); logkoc_exp = math.log10(st.median(koc))
    pka_a = ex.get("pKa Acidic Apparent"); pka_b = ex.get("pKa Basic Apparent")
    cls = "neutral"
    if pka_a and not pka_b: cls = "acid"
    elif pka_b and not pka_a: cls = "base"
    elif pka_a and pka_b: cls = "amphoteric"
    row = {"cas": r["cas"], "name": r.get("ct_name"), "cls": cls, "lkow": lkow, "exp": logkoc_exp}
    row["ecetoc"] = so.ecetoc_base_workbook(lkow, 0.02)["log_koc"]
    if lkow > 0.85: row["li"] = so.li_neutral(lkow, 0.02)["log_koc"]
    if cls in ("acid", "base"):
        pk = st.median(pka_a if cls == "acid" else pka_b)
        try: row["ft"] = so.franco_trapp(cls, lkow, pk, 7.0, 0.01, 0.02)["log_koc"]
        except Exception as ex_: row["ft_err"] = str(ex_)[:60]
    else:
        row["ft_neutral_acid_line"] = 0.54 * lkow + 1.11   # FT neutral-acid regression, shown only as a reference line for neutrals
        row["ft_neutral_base_line"] = 0.42 * lkow + 1.34
    rows.append(row)
print("chemicals with both experimental Koc and logKow:", len(rows), Counter(r["cls"] for r in rows))
def stats(key, subset):
    d = [x[key] - x["exp"] for x in subset if key in x]
    if not d: return None
    return f"n={len(d)} bias={st.mean(d):+.2f} MAE={st.mean(abs(v) for v in d):.2f} RMSE={math.sqrt(st.mean(v*v for v in d)):.2f} within0.5={sum(abs(v)<=0.5 for v in d)/len(d):.0%} within1={sum(abs(v)<=1 for v in d)/len(d):.0%}"
for key in ("ecetoc", "li", "ft", "ft_neutral_acid_line", "ft_neutral_base_line"):
    for cls in ("neutral", "acid", "base", None):
        sub = [x for x in rows if (cls is None or x["cls"] == cls)]
        s = stats(key, sub)
        if s and cls in ("neutral", "acid", "base", None): print(f"  {key:22s} class={str(cls):8s} {s}")
for x in sorted(rows, key=lambda x: -abs(x["ecetoc"] - x["exp"]))[:6]:
    print("   ecetoc worst:", x["cas"], x["name"], x["cls"], f"logKow={x['lkow']:.2f} exp logKoc={x['exp']:.2f} ecetoc={x['ecetoc']:.2f}")

# ================= classifiers on experimental data =================
print("\n== B / vB (BCF) and M / vM (Koc) from experimental medians ==")
flag_b = flag_vb = flag_m = flag_vm = n_bcf = n_koc = 0; flagged = []
for r in recs:
    ex = r.get("ct_exp") or {}
    if ex.get("Bioconcentration Factor"):
        n_bcf += 1
        bcf = st.median(ex["Bioconcentration Factor"])
        res = classify_pbt_and_vpvb(bcf_l_per_kg=bcf)
        b = res["bioaccumulation"]["outcome"] == "CRITERION_MET"; vb = res["very_bioaccumulation"]["outcome"] == "CRITERION_MET"
        flag_b += b; flag_vb += vb
        if b: flagged.append((r["cas"], r.get("ct_name"), round(bcf), "vB" if vb else "B"))
    if ex.get("Soil Adsorp. Coeff. (Koc)"):
        n_koc += 1
        lk = math.log10(st.median(ex["Soil Adsorp. Coeff. (Koc)"]))
        res = classify_pmt_and_vpvm(log_koc=lk)
        flag_m += res["mobility"]["outcome"] == "CRITERION_MET"; flag_vm += res["very_mobility"]["outcome"] == "CRITERION_MET"
print(f"BCF available for {n_bcf}: B {flag_b}, vB {flag_vb}. Koc available for {n_koc}: M {flag_m}, vM {flag_vm}")
for f in flagged[:15]: print("   B-flagged:", f)

# ================= ECOTOX record sanity =================
print("\n== ECOTOX local records sanity for the sample ==")
sys.path.insert(0, ROOT)
from app.services.ecotox_local import search_ecotox_local
units = Counter(); neg = zero = nonnum = tot = 0; extreme = []
for r in recs:
    res = search_ecotox_local(r.get("ct_name") or "x", cas_number=r["cas"], limit=200)
    for c in res.get("candidates", []):
        tot += 1; units[c["unit"]] += 1
        v = c["value"]
        if v is None: nonnum += 1
        elif v < 0: neg += 1
        elif v == 0: zero += 1
        elif c["unit"] in ("mg/L", "ppm", "ug/L", "ppb") and (v > 1e6): extreme.append((r["cas"], c["endpoint_label"], v, c["unit"]))
print(f"candidates examined: {tot}; null value: {nonnum}; negative: {neg}; zero: {zero}; >1e6 in mass/vol units: {len(extreme)}")
print("unit distribution (top 12):", units.most_common(12))
for e in extreme[:8]: print("   extreme:", e)
