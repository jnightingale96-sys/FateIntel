# Scientific validation pass — 2026-09-23

Part of the 90-day commercial-validation plan (Weeks 2-6: gold-standard cases and reproducibility). Two questions:
does the app's arithmetic hold up against independent calculation, and does the app behave sensibly on real chemicals
it has never been tuned on?

**Scope, stated plainly.** This is code-versus-independent-calculation and app-versus-external-data. It is *not* the
plan's gate 1 as written ("compare against an independent expert's manual workflow") — no human expert was involved.
The three gold-case doses and WWTP fractions are illustrative test inputs (typical labelled maxima recalled from memory,
not verified against a current SmPC; removal fractions that are not measured plant data). What was verified is the
calculation chain, not a regulatory conclusion.

## 1. Independent recalculation (now permanent: `tests/test_scientific_invariants.py`, 27 tests)

Each check compares the app with a *separately written* hand formula, closed form, different numerical method, or
published literature value. Random inputs use fixed seeds.

| Area | Checked against | Result |
|---|---|---|
| EMA Phase I PECsw (carbamazepine, diclofenac, ibuprofen + 150 random dose/Fpen/volume/dilution/STP-capacity sets) | hand formula DOSE×Fpen/(WASTEW×DILUTION) | exact (rel 1e-12) |
| Emission molar accounting (150 random route/excretion/metabolite splits) | hand split; parent+metabolites ≤ administered | exact |
| Gold chain: emission → WWTP → PEC → RQ, 3 substances | independent hand chain | exact; bit-identical across runs |
| Carbamazepine-only WWTP preset | refusal on another substance | refuses correctly |
| Multimedia fate (150 random 2-4 compartment systems) | independent linear solve, scipy ODE integration to steady state, linearity in emissions, mass closure | all agree; singular systems correctly refused |
| Kinetics SFO / FOMC / DFOP | closed forms (ln2/k, ln10/k, Gustafson–Holden), `brentq` root finding | exact; SFO fits recover DT50 within 10% at 1% noise 25/25 (FOMC ≥24/25) |
| Franco–Trapp sorption | published regressions recovered far from pKa; Kd = Koc·fOC; acid Koc non-increasing in pH | exact |
| McGowan volume | Abraham & McGowan (1987): benzene 0.7164, methane 0.2495, ethanol 0.4491 | agree to 4 d.p. |
| Biosolids, plant uptake (Briggs 0.784 peak), river network, PNEC unit/AF arithmetic, EqP soil = Koc·PNECw/85 | closed forms / conservation | exact |

Three checks initially "failed" in my scratch harness and were my own errors, not app bugs: I mis-recalled methane's
McGowan volume (0.3358; the literature value 0.2495 matches the app), I swapped neutral/ionised ends for bases in
the Franco–Trapp limit test, and I applied a tolerance that ignored the workbook's documented ionic-strength activity
term. Each was corrected against the app's actual documented behaviour before anything was reported.

## 2. Random real chemicals (scripts in `scripts/validation/`, records gitignored)

150 CAS numbers sampled at random (fixed seed) from the local ECOTOX index; each resolved through the **app's own**
PubChem resolver and, independently, through EPA CompTox. A second random sample of 250 chemicals that have
experimental soil Koc in CompTox/OPERA (223 usable) tested the sorption models.

**Identity.** All 150 CAS check digits valid. 137 resolved; 12 have no single-compound PubChem record (UVCBs, mixtures,
trade names such as CAS 68585-34-2); 1 correctly refused as ambiguous. Of 137, 132 agree with CompTox on InChIKey
connectivity, formula and mass; 5 differ for explainable reasons (a Cr(VI) ion, a coordination compound, a glucose
form, tetraethyl lead 323.0 vs 323.4, and one imidazolium salt where CompTox's own mass, 277.25, is inconsistent with the
formula PubChem gives, 275.23). No wrong-compound matches. PubChem XLogP vs experimental log Kow (n=65): MAE 0.38, 82%
within 0.5 — large errors only for extreme halogenated hydrophobes (decaBDE 10.4 vs 8.3), which is why the app never
auto-selects XLogP.

**Sorption vs experimental Koc (n=223, fOC 0.02, pH 7):**

| Model | n | bias (log) | MAE | within 0.5 / 1.0 log |
|---|---|---|---|---|
| Li 2020 (app neutral default) | 192 | +0.15 | 0.51 | 62% / 90% |
| Franco–Trapp (acids) | 9 | +0.08 | 0.27 | 89% / 100% |
| Franco–Trapp (bases) | 16 | −0.11 | 0.60 | 62% / 75% |
| ECETOC base regression (comparison only) | 223 | **+1.04** | 1.14 | 17% / 39% |

Aromatic amines (1-naphthylamine, benzidine) are under-predicted by 1.4-2 log units — a known limitation of partition
models (they bind covalently to organic matter), not an app defect. For log Kow ≥ 4 the neutral models over-predict by
about +0.4.

## 3. Problems found, and what was done

1. **PubChem throttling (real).** 18 of the first 44 lookups failed with 503 "ServerBusy"; the resolver had no retry.
   Added bounded retry with backoff on 429/502/503/504 and timeouts, honouring `Retry-After`. After the fix, 101 of the
   113 previously failed lookups resolved. *(`app/services/identity.py`, 7 tests.)*
2. **"Not found" reported as an outage (real).** A PubChem 404 (mixtures/UVCBs) surfaced as "temporarily unavailable",
   telling the user to retry something that can never succeed. Now: "no single-compound record for this identifier".
3. **Absurd log Kow accepted silently (real).** CompTox holds junk "experimental" values (65.0 beside a second value of
   2.68 for 2'-acetonaphthone; 86.0 for 1,2-dibromoethane; 22.8 for benzotriazole). The median 33.84 gave log Koc = 26.8
   with no warning. Sorption models now reject log Kow outside −10…20 as a data-entry/source error and warn above 8.
   (Dropping those four chemicals cut Li's RMSE from 2.0 to 0.75.) The −10…20 bounds are a sanity guard, not a claim
   about any regression's calibration range.
4. **ECETOC over-predicts (documented).** Its output now carries the measured +1.0 log bias as a warning.
5. **ECOTOX unit basis (real).** Of 3,140 "aquatic" candidates, 79% are aqueous mass concentrations, 14% molar
   (need molecular weight), and **7% are not aqueous concentrations at all** (g/kg diet, mg/kg bdwt, neq/g, %, µg/cell)
   yet carried an "Aquatic LC50" label. Kept (nothing dropped) but each candidate's notes now state the unit basis.
   `derive_pnec` already refuses these units, so no bad PNEC was reachable; the risk was a misled reviewer.
6. **PBT/vPvB classifier ignored organic-only scope (real, my own module from earlier today).** Aluminium's
   experimental BCF (73,300) came back "very bioaccumulative". Added `substance_group`; metals and radionuclides now
   return `NOT_APPLICABLE_TO_SUBSTANCE_GROUP`.

## 4. Not fixed — recommendations

- **Molar → mass conversion for ECOTOX candidates** (14% arrive in mM/µM; the identity record supplies the MW). Real
  usability gap; a feature, not a bug fix, so left for your call.
- **DFOP DT50 recovery** missed the 10% band in 3/60 noisy trials — expected (DFOP is weakly identifiable), not a defect.
- **Gold-standard gate 1** still needs an independent expert's manual workflow and SmPC-verified inputs for the three
  cases; carbamazepine's workbook fixture is the only externally sourced benchmark in the code today.
- The 12 unresolved lookups and the CompTox data-quality issues are external-source limits; the app now handles them
  honestly rather than silently.

## Reproduce

```
python -m pytest tests/test_scientific_invariants.py          # no network
python scripts/validation/collect_random_chemicals.py 150      # network; writes data/validation_runs/
python scripts/validation/retry_app_resolver.py
python scripts/validation/analyze_random_chemicals.py
python scripts/validation/collect_sorption_set.py 250
python scripts/validation/analyze_sorption_models.py
```
Collection scripts need `COMPTOX_API_KEY` in `.env` and never touch the application database.

Full suite: 969 passed, 5 skipped (was 901).
