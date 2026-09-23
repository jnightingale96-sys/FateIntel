# FateIntel: soil degradation (DT50) provider

This provider predicts the aerobic soil biotransformation half-life (DT50) of organic chemicals. Each prediction carries calibrated uncertainty, persistence probabilities and FOCUS/EFSA site corrections.

## Engine

The engine is **PEPPER** from the Fenner Lab (Eawag/UZH). As far as I know it is the best openly available structure-based soil DT50 model as of 2026.

- It is a Gaussian Process Regressor on 2D PaDEL descriptors, with kernel C × Matern(ν = 0.5).
- Each compound's noise term is its Bayesian-inferred variance between soils.
- It is trained on **867 pesticides and pesticide transformation products** (6,309 OECD 307 half-lives, EAWAG-SOIL in enviPath).
- It predicts the *mean* log DT50 across soils and a standard deviation for that mean. From these the provider computes P(nP), P(P) and P(vP).

> Hafner J, Cordero J, … Fenner K (2026). *Confidently Uncertain: Probabilistic Machine Learning to Predict Soil Biotransformation Half-Lives.* Environ. Sci. Technol. 60(14):11077.
> Latino DARS, Wicker J, … Fenner K (2017). *Eawag-Soil in enviPath.* Environ. Sci.: Processes Impacts 19:449.

## What the FateIntel wrapper adds

| Feature | Detail |
|---|---|
| Lean runtime | Needs only sklearn, rdkit, padelpy and Java; pepper-lab is not needed at runtime and nothing writes to disk. The artifact reproduces the pepper-lab final model (see `fidelity_vs_pepper_lab` in the model card). |
| Measured-data lookup | If the compound is in EAWAG-SOIL, the measured Bayesian mean is returned and used as the recommended value by default. |
| Applicability domain | PEPPER's pre-checks (single component, organic, MW < 1200) plus Morgan-fingerprint Tanimoto to the training set. Three nearest analogues are returned with their measured DT50s. Confidence (high/medium/low) is calibrated from cross-validation. |
| Two uncertainty types | The 90% CI of the mean DT50 (epistemic) and a 90% prediction interval for a single soil, which adds between-soil variability (default σ = median of the training set). |
| Persistence | P(nP)/P(P)/P(vP) for REACH, EU PPP, Stockholm or custom thresholds. Gives a central class and a precautionary class based on the upper 95% limit. |
| Site corrections | Arrhenius temperature correction (Ea = 65.4 kJ/mol, no degradation at ≤ 0 °C), Walker moisture correction (B = 0.7) and FOCUS depth factors. Also normalises measured DT50s back to 20 °C. |
| Salts | The largest organic fragment is neutralised and a warning is added. This is relevant for pharmaceuticals and veterinary medicines. |

## Install

```bash
pip install -r requirements.txt     # plus a Java runtime (JRE 8+) for PaDEL
```

## Use

```python
from fateintel_soil_dt50 import SoilDT50Predictor, SiteConditions

p = SoilDT50Predictor()             # load once at app start-up
res = p.predict(
    [{"id": "c1", "name": "carbamazepine", "smiles": "NC(=O)N1c2ccccc2C=Cc2ccccc21"}],
    conditions=SiteConditions(temperature_c=24, moisture=28, moisture_ref=35),
    regime="REACH")
res[0].to_dict()
```

FastAPI:

```python
from fateintel_soil_dt50.api import router as soil_dt50_router
app.include_router(soil_dt50_router, prefix="/api/providers")
# POST /api/providers/soil-dt50/predict   GET /api/providers/soil-dt50/model-card
```

Batch CLI:

```bash
python -m fateintel_soil_dt50 chemicals.csv -o dt50.csv --temp 24 --moisture 28 --moisture-ref 35
```

## Output (per chemical)

- `recommended`: the value FateIntel should carry forward: `DT50_ref_days`, `logDT50`, `logDT50_sd`, `basis` (measured/predicted) and `confidence`.
- `prediction`: the raw PEPPER output, with the CI of the mean and the single-soil prediction interval.
- `experimental`: measured EAWAG-SOIL data, when available.
- `persistence`: probabilities, central class and precautionary class.
- `applicability`: max Tanimoto, nearest analogues, confidence and domain notes.
- `site`: correction factors, site DT50 and first-order k.
- `provenance`: engine, version and citation (for the audit trail).

## Validation (5× repeated 5-fold CV, 864 compounds, log10 DT50 in days)

**Fidelity:** the runtime reproduces the pepper-lab final model exactly: the same 291 features, and a maximum difference of 0.0 in both mean and sd.

| Subset | Share | RMSE | Within ×3 | Within ×10 | 90% CI coverage |
|---|---|---|---|---|---|
| All | 100% | 0.80 | 53% | 84% | 87% |
| Confidence **high** | 30% | 0.64 | 64% | 88% | 89% |
| Confidence medium | 53% | 0.85 | 49% | 82% | 85% |
| Confidence low | 17% | 0.89 | 49% | 79% | 88% |

Overall R² = 0.31 and Spearman = 0.57. The uncertainty is well calibrated: the nominal 90% interval contains the measured mean about 87% of the time.

**Persistence (REACH, 120 d):**
- Classifying on the central estimate alone misses most persistent compounds (sensitivity 0.13, specificity 0.99).
- The provider therefore raises `screening_flag_potential_P` when **P(P) ≥ 0.10**. At that threshold, sensitivity is 0.88 and specificity 0.51, and about 55% of compounds are flagged.
- This makes it a prioritisation filter, not a classifier.

Full metrics are in `fateintel_soil_dt50/model/model_card.json`, and the per-compound CV predictions are in `scripts/cv_predictions.csv`.

## Limits (read before regulatory use)

- The training chemistry is EU pesticides and their transformation products. Pharmaceuticals, industrial chemicals, surfactants, PFAS and permanently charged species are sparse, so rely on the confidence flag and the nearest-analogue list.
- The endpoint is **primary disappearance of the parent** in aerobic laboratory soil. It is not mineralisation, not field dissipation, and not anaerobic.
- Predictions are for reference conditions. Apply `conditions` for the site (important for warm climates: at 28 °C, DT50 is roughly half the 20 °C value).
- Treat this as a screening/prioritisation tool (Tier 1). For registration dossiers, measured OECD 307 data take precedence.
- **Licensing:** pepper-lab is MIT. Check the enviPath/EAWAG-SOIL data terms before commercial (paid-tier) use; this is a natural item for the enviPath partnership discussion.

## Rebuilding the model

```bash
git clone https://github.com/FennerLabs/pepper && (fetch LFS data files)
python pepper/scripts/build_fateintel.py         # PaDEL descriptors + pepper-lab final model
python scripts/build_artifact.py --pepper-data ~/build/pepper_data --cpd pepper/data/soil/cpd_data_soil_all_data.tsv
```
