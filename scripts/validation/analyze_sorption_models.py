from pathlib import Path as _P
ROOT = str(_P(__file__).resolve().parents[2])
RUNS = _P(ROOT) / "data" / "validation_runs"  # gitignored working area; collected records land here
RUNS.mkdir(parents=True, exist_ok=True)
import json, math, os, statistics as st, sys
sys.path.insert(0, ROOT)
from collections import Counter
from app.services import sorption as so
recs = [json.loads(l) for l in open(os.path.join(str(RUNS), "val4_records.jsonl"), encoding="utf-8")]
print("sampled:", len(recs))
rows = []
implausible = []   # experimental log Kow values the app now refuses (outside -10..20); dropped as data-hygiene, then counted
for r in recs:
    ex = r.get("exp") or {}
    lk = ex.get("LogKow: Octanol-Water")
    if lk:
        bad = [v for v in lk if not -10 <= v <= 20]
        if bad: implausible.append((r.get("casrn"), r.get("name"), bad))
        lk = [v for v in lk if -10 <= v <= 20]
    if not lk or not r.get("koc_values"): continue
    lkow = st.median(lk); exp = math.log10(st.median(r["koc_values"]))
    pa, pb = ex.get("pKa Acidic Apparent"), ex.get("pKa Basic Apparent")
    cls = "amphoteric" if (pa and pb) else "acid" if pa else "base" if pb else "neutral"
    row = {"cas": r.get("casrn"), "name": r.get("name"), "cls": cls, "lkow": lkow, "exp": exp}
    row["ecetoc"] = so.ecetoc_base_workbook(lkow, 0.02)["log_koc"]
    if lkow > 0.85:
        row["li_pub"] = so.li_neutral(lkow, 0.02, "publication")["log_koc"]
        row["li_wb"] = so.li_neutral(lkow, 0.02, "workbook_literal")["log_koc"]
    if cls in ("acid", "base"):
        pk = st.median(pa if cls == "acid" else pb)
        row["pka"] = pk
        try: row["ft"] = so.franco_trapp(cls, lkow, pk, 7.0, 0.01, 0.02)["log_koc"]
        except Exception: pass
    rows.append(row)
print("chemicals with an implausible experimental log Kow value in CompTox (dropped):", len(implausible), implausible[:5])
print("with logKow+Koc:", len(rows), dict(Counter(x["cls"] for x in rows)))
def S(key, sub):
    d = [x[key] - x["exp"] for x in sub if key in x]
    if len(d) < 3: return None
    return f"n={len(d):3d} bias={st.mean(d):+.2f} MAE={st.mean(abs(v) for v in d):.2f} RMSE={math.sqrt(st.mean(v*v for v in d)):.2f} <=0.5:{sum(abs(v)<=0.5 for v in d)/len(d):4.0%} <=1.0:{sum(abs(v)<=1 for v in d)/len(d):4.0%}"
for cls in ("neutral", "acid", "base", None):
    sub = [x for x in rows if cls is None or x["cls"] == cls]
    print(f"\n-- class {cls or 'ALL'} ({len(sub)})")
    for key, lab in (("ecetoc", "ECETOC base regression"), ("li_wb", "Li workbook-literal (app neutral default)"), ("li_pub", "Li 2020 publication"), ("ft", "Franco-Trapp @pH7, I=0.01")):
        s = S(key, sub)
        if s: print(f"   {lab:44s} {s}")
# by logKow band, neutral only
print("\n-- neutral: residual by logKow band (Li workbook-literal / Li publication / ECETOC)")
for lo, hi in ((-3, 1), (1, 2.5), (2.5, 4), (4, 9)):
    sub = [x for x in rows if x["cls"] == "neutral" and lo <= x["lkow"] < hi]
    if len(sub) >= 3: print(f"   logKow [{lo},{hi}) n={len(sub):3d}  ", " | ".join(f"{k}: {st.mean(x[k]-x['exp'] for x in sub if k in x):+.2f}" for k in ("li_wb", "li_pub", "ecetoc") if any(k in x for x in sub)))

print("\n-- worst Li (publication) residuals")
for x in sorted([x for x in rows if "li_pub" in x], key=lambda x: -abs(x["li_pub"] - x["exp"]))[:10]:
    print(f"   {x['cas']:12s} {str(x['name'])[:42]:42s} {x['cls']:8s} logKow={x['lkow']:6.2f} expLogKoc={x['exp']:5.2f} li={x['li_pub']:5.2f} err={x['li_pub']-x['exp']:+.2f}")
