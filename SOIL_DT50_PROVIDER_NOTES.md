# Soil DT50 provider (PEPPER GPR) — integration notes, 2026-09-23

## What this is

The user built a provider around **PEPPER** (Fenner Lab, Eawag/UZH): a Gaussian-process regressor on 2D PaDEL
descriptors, trained on EAWAG-SOIL (Latino et al. 2017), predicting the mean log10 aerobic-soil DT50 with an
uncertainty. Delivered as `fateintel_soil_dt50.zip`; integrated here under `app/services/soil_dt50/`, model artifact
in `app/data/soil_dt50/`, mounted at `/api/providers/soil-dt50/` (`predict`, `correct`, `model-card`, `capabilities`).

## How to describe it (agreed wording, and what is whose)

**Published, citable:** the PEPPER model (Hafner et al., ES&T 60(14):11077, 2026; the provider reproduces the
authors' final model — same 291 features, max difference 0.0); the training data (Latino et al. 2017); the
temperature / moisture / depth corrections (standard FOCUS/EFSA: Arrhenius Ea 65.4 kJ/mol = Q10 2.58, Walker B 0.7,
FOCUS depth bands).

**The user's own methods, not published — say so:** the high/medium/low confidence rule and cut-offs; the 10% P(P)
screening flag; the single-soil prediction interval (adds the median between-soil spread); using measured values when
the compound is in the training set; the PFAS override and salt handling. The cross-validation figures in the model
card are the user's internal check, not the paper's — cite the paper's own performance.

**Suggested wording:** "Soil DT50 was predicted with the PEPPER probabilistic model (Hafner et al., 2026; trained on
EAWAG-SOIL, Latino et al., 2017) and corrected to site conditions following FOCUS/EFSA guidance. Confidence classes and
a persistence screening threshold were derived by the authors from repeated cross-validation."

**"Validated" needs qualifying.** Peer-reviewed, moderate performance (R² 0.31, Spearman 0.57, 53% within ×3, 84% within
×10, 90% CI coverage 87% — the user's cross-validation). It is **not** an OECD-accepted QSAR, has no QMRF, is not in
the OECD QSAR Toolbox, and has not been tested outside pesticide chemistry. The gap is closed by testing against measured
data from outside the training set (non-pesticides, warm-climate soils; the user's Middle East dataset would serve).

## What was checked here (independently of the provider's own tests)

- **Fidelity across scikit-learn versions.** The artifact was pickled with 1.6.1; this repo runs Python 3.14, where 1.6.1
  has no wheel, so it runs on **1.9.1**. The provider's 14 tests pass, and all seven demo compounds reproduce the
  author's stored output with a maximum difference of **0.0** (mean, sd, P(P), reference and site DT50). That comparison
  is now a permanent test (`tests/test_soil_dt50_provider.py`, reference in `tests/data/`). Requirements are therefore
  `scikit-learn>=1.6`, not the exact pin.
- **Corrections** against hand formulas (Arrhenius, Q10 = 2.58, Walker, FOCUS depth-band edges, round trip,
  no degradation at ≤ 0 °C).
- **Persistence probabilities** equal the normal tail of the reported mean and sd; the CI nests inside the single-soil
  interval; measured data win over the prediction by default and can be switched off.

## Changes made to the provider during integration

- Paths adapted; heavy dependencies imported lazily so the app starts without them; `capabilities` reports what is
  missing and the router answers 503 (not a crash).
- **Licence gate** (same shape as enviPath): the artifact embeds the EAWAG-SOIL training set (structures and measured
  DT50s, used for the measured lookup and nearest analogues), whose commercial terms are unconfirmed. `predict` and
  `model-card` are refused (403) outside local/test unless `SOIL_DT50_COMMERCIAL_LICENSE_CONFIRMED` is set.
  `correct` (pure FOCUS/EFSA arithmetic) is never gated. **The shipped 4 MB model file itself sits in the repo — if the
  repo is ever shared or distributed, that file is the licensing question.**
- A moisture value without a reference (or vice versa) used to be **silently ignored**; it now adds a warning
  (provider and `correct` endpoint).
- `to_evidence_candidate()` turns a result into a `FATE.SOIL_DT50` evidence candidate: measured → "database record",
  otherwise a labelled "MODEL ESTIMATE", always `needs_professional_review`, DOI never invented. Registered as
  `pepper_soil_dt50` in the evidence-source registry (not searchable by name: it needs a structure).

## Review observations (not changed; worth knowing)

- The README says 867 compounds / 6,309 half-lives; the model card says 864 / 6,252. Presumably curation filtering —
  worth stating which number the paper uses.
- The user's cross-validation splits at random by compound. For pesticide series that is optimistic (close analogues
  land on both sides of the split), and the confidence bins were calibrated on the same CV. A scaffold- or cluster-split
  would be a stricter internal check.
- Carbamazepine comes out at ~21 d (medium confidence) — pharmaceuticals are outside the training chemistry, so treat as
  a screen; PFOA's numeric 28.8 d is correctly overridden to vP and flagged unreliable.

## Not done / open

- **BIOWIN4 → screening DT50: implemented** (`app/services/biowin_dt50.py`, `/api/providers/biowin-dt50/estimate`, `/regions`).
  Owner relation DT50 [hours, **25 °C**] = 10^(5 − BIOWIN4) (25 °C confirmed by the owner 2026-09-24); identical to the
  existing veterinary manure relation. **Unit checked against EPA's own EPI Suite output** (5 → hours, 4 → days, 3 → weeks,
  2 → months, 1 → longer): read in hours it gives 1 h / 10 h / ~4 d / ~6 wk / ~14 months and fits at both ends; read in days
  it is 1–2 classes too slow. (An earlier note here that days matched the scale labels was wrong.) Re-expressed at a
  per-region target temperature with theta 1.047 (EU = 10 °C, owner-stated; any other region must be supplied, none guessed).
  **No literature source attached**; EPI Suite score expected (the app's own BIOWIN4 is a reconstruction and is flagged).
  Emits a reviewable candidate (manure by default, water optional); measured DT50 always wins.
- **OPERA biodegradation via CompTox** (`/chemical/fate/search/by-dtxsid/{dtxsid}`): predicted half-life and ready
  biodegradability with applicability-domain verdicts exist, and 160 chemicals have OPERA/SRC 98-008 survey values.
  These are *not* soil DT50s (atrazine: 4.9 d, flagged outside the training domain). Not wired in — the user is working on
  biodegradation and asked to move on.
- **EFSA OpenFoodTox 3.0** (Zenodo 19388272, CC BY-ND 4.0): the only open structured pesticide soil-fate source found; the
  DT50 values are in the 1 GB IUCLID archive (the Excel export has none). Not parsed; NoDerivatives licence needs a
  decision before any subset ships in a paid tier.
- No soil DT50 is fed into PEARL/PELMO/the native soil screen automatically — it enters as a reviewable evidence
  candidate only.
- Optional dependencies live in `requirements-soil-dt50.txt` (plus a Java runtime for PaDEL).
