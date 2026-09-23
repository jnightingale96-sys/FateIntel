"""
Rebuild the FateIntel soil DT50 artifact from the PEPPER paper data.

Steps
  1. Load PaDEL descriptors + Bayesian-inferred targets (PEPPER pipeline output)
  2. Re-implement PEPPER preprocessing (NA-drop, min-max, variance 0.02,
     Spearman/Ward de-correlation 0.01) + GPR (C*Matern nu=0.5, alpha = sd^2)
  3. Check fidelity against the pepper-lab final model pickle
  4. Repeated 5-fold CV -> accuracy, calibration, confidence bins
  5. Fit on all data and write artifact + model card

Usage:
  python scripts/build_artifact.py --pepper-data ~/build/pepper_data \
      --cpd ~/pepper/data/soil/cpd_data_soil_all_data.tsv
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform
from scipy.stats import norm, spearmanr
from sklearn.feature_selection import VarianceThreshold
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel as C, Matern
from sklearn.model_selection import KFold
from sklearn.preprocessing import MinMaxScaler

OUT = Path(__file__).resolve().parents[2] / "app" / "data" / "soil_dt50"


def decorrelate(X: pd.DataFrame, thr=0.01) -> list[str]:
    corr = X.corr("spearman").to_numpy()
    corr = (corr + corr.T) / 2
    np.fill_diagonal(corr, 1)
    corr = np.nan_to_num(corr)
    link = hierarchy.ward(squareform(1 - np.abs(corr), checks=False))
    ids = hierarchy.fcluster(link, thr, criterion="distance")
    groups = defaultdict(list)
    for i, c in enumerate(ids):
        groups[c].append(i)
    return list(X.columns[[v[0] for v in groups.values()]])


def fit(Xraw: pd.DataFrame, y: np.ndarray, ysd: np.ndarray):
    scaler = MinMaxScaler().fit(Xraw.values)
    Xs = pd.DataFrame(scaler.transform(Xraw.values), columns=Xraw.columns)
    vt = VarianceThreshold(0.02).fit(Xs)
    Xv = Xs.loc[:, vt.get_support()]
    feats = decorrelate(Xv)
    gpr = GaussianProcessRegressor(
        kernel=C(2.0, (1e-3, 1e3)) * Matern(length_scale=2.5, length_scale_bounds=(1e-3, 1e3), nu=0.5),
        normalize_y=True, n_restarts_optimizer=0, alpha=ysd ** 2)
    gpr.fit(Xs[feats].values, y)
    return scaler, list(Xraw.columns), feats, gpr


def predict(model, Xraw):
    scaler, sfeats, feats, gpr = model
    Xs = pd.DataFrame(scaler.transform(Xraw.reindex(columns=sfeats).fillna(0).values), columns=sfeats)
    mu, sd = gpr.predict(Xs[feats].values, return_std=True)
    return mu.ravel(), sd.ravel()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pepper-data", required=True)
    ap.add_argument("--cpd", required=True)
    ap.add_argument("--repeats", type=int, default=5)
    a = ap.parse_args()
    pd_dir = Path(a.pepper_data)

    padel = pd.read_csv(next(pd_dir.rglob("*PaDEL*soil*all_data*.tsv")), sep="\t")
    model_data = pd.read_csv(next(pd_dir.rglob("model_data_soil_all_data.tsv")), sep="\t")
    cpd = pd.read_csv(a.cpd, sep="\t")
    print("padel", padel.shape, "model_data", model_data.shape)

    df = model_data[["SMILES", "compound_name", "logDT50_mean", "logDT50_std"]].merge(padel, on="SMILES", how="inner")
    df = df.drop_duplicates("SMILES").reset_index(drop=True)
    X = df.drop(columns=["SMILES", "compound_name", "logDT50_mean", "logDT50_std"])
    X = X.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="any")
    y, ysd = df["logDT50_mean"].values, df["logDT50_std"].values
    print("training compounds", len(df), "raw PaDEL features without NA", X.shape[1])

    # ---- cross-validation
    rows = []
    for rep in range(a.repeats):
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(X):
            m = fit(X.iloc[tr], y[tr], ysd[tr])
            mu, sd = predict(m, X.iloc[te])
            for i, mu_i, sd_i in zip(te, mu, sd):
                rows.append((rep, i, mu_i, sd_i))
        print(f"CV repeat {rep+1}/{a.repeats} done")
    cv = pd.DataFrame(rows, columns=["rep", "i", "mu", "sd"])
    cv["y"], cv["ysd"] = y[cv.i], ysd[cv.i]
    cv["err"] = cv.mu - cv.y
    cv["abserr"] = cv.err.abs()

    def metrics(d):
        ss_res = (d.err ** 2).sum(); ss_tot = ((d.y - d.y.mean()) ** 2).sum()
        z = d.err / np.sqrt(d.sd ** 2)
        return {
            "n": int(len(d) / a.repeats),
            "RMSE_log": round(float(np.sqrt((d.err ** 2).mean())), 3),
            "MAE_log": round(float(d.abserr.mean()), 3),
            "R2": round(float(1 - ss_res / ss_tot), 3),
            "spearman": round(float(spearmanr(d.mu, d.y).statistic), 3),
            "within_factor_3": round(float((d.abserr <= np.log10(3)).mean()), 3),
            "within_factor_10": round(float((d.abserr <= 1).mean()), 3),
            "coverage_90CI_of_mean": round(float((np.abs(z) <= norm.ppf(0.95)).mean()), 3),
        }

    overall = metrics(cv)
    print("CV overall", overall)

    # confidence bins from predicted sd
    q = cv.sd.quantile([0.33, 0.66]).values
    bins = {}
    for lab, mask in [("sd<=q33", cv.sd <= q[0]), ("q33<sd<=q66", (cv.sd > q[0]) & (cv.sd <= q[1])), ("sd>q66", cv.sd > q[1])]:
        bins[lab] = metrics(cv[mask])
    print("by sd tertile", json.dumps(bins, indent=1))

    # structural similarity of each held-out compound to its training fold is costly to track per fold;
    # use leave-one-out nearest-neighbour Tanimoto within the full set as the AD proxy
    from rdkit import Chem, DataStructs
    from rdkit.Chem import rdFingerprintGenerator
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    fps = [gen.GetFingerprint(Chem.MolFromSmiles(s)) for s in df.SMILES]
    nn = np.array([max(s for j, s in enumerate(DataStructs.BulkTanimotoSimilarity(fp, fps)) if j != i)
                   for i, fp in enumerate(fps)])
    cv["nn"] = nn[cv.i]
    # rule chosen from the CV error profile (lowest-sd octile and close analogues are clearly better)
    RULE = {"high_sd": 0.60, "high_tanimoto": 0.75, "low_sd": 0.74, "low_tanimoto": 0.35}
    high = (cv.sd <= RULE["high_sd"]) | (cv.nn >= RULE["high_tanimoto"])
    low = ~high & ((cv.sd > RULE["low_sd"]) | (cv.nn < RULE["low_tanimoto"]))
    med = ~high & ~low
    conf = {"high": metrics(cv[high]), "medium": metrics(cv[med]), "low": metrics(cv[low])}
    for k in conf:
        conf[k]["share_of_predictions"] = round(float({"high": high, "medium": med, "low": low}[k].mean()), 3)
    print("confidence classes", json.dumps(conf, indent=1))

    # persistence classification accuracy (REACH P: 120 d)
    lp = np.log10(120)
    obsP, predP = cv.y > lp, cv.mu > lp
    upper = cv.mu + norm.ppf(0.975) * cv.sd
    cls = {
        "observed_P_share": round(float(obsP.mean()), 3),
        "central_sensitivity": round(float((predP & obsP).sum() / obsP.sum()), 3),
        "central_specificity": round(float((~predP & ~obsP).sum() / (~obsP).sum()), 3),
        "precautionary_upper95_sensitivity": round(float(((upper > lp) & obsP).sum() / obsP.sum()), 3),
        "precautionary_upper95_specificity": round(float(((upper <= lp) & ~obsP).sum() / (~obsP).sum()), 3),
    }
    pP = 1 - norm.cdf((lp - cv.mu) / cv.sd)
    cls["screening_by_p_P"] = {
        str(t): {"sensitivity": round(float(((pP >= t) & obsP).sum() / obsP.sum()), 3),
                 "specificity": round(float(((pP < t) & ~obsP).sum() / (~obsP).sum()), 3),
                 "share_flagged": round(float((pP >= t).mean()), 3)}
        for t in (0.05, 0.1, 0.2, 0.3, 0.5)}
    SCREEN_T = 0.10
    print("P classification", cls)

    # ---- final fit
    final = fit(X, y, ysd)
    mu_all, sd_all = predict(final, X)
    print("final model: n features used", len(final[2]), "kernel", final[3].kernel_)

    # fidelity against pepper-lab pickle (if present)
    fidelity = None
    pk = list(pd_dir.rglob("final_model_GPR.pkl"))
    if pk:
        sys.path.insert(0, "")
        pm = joblib.load(pk[0])
        feats_p = list(pm.feature_names_used_for_training)
        fidelity = {"pepper_n_features": len(feats_p), "ours_n_features": len(final[2]),
                    "same_feature_set": set(feats_p) == set(final[2])}
        Xs = pd.DataFrame(pm.feature_preprocessor.transform(
            X.reindex(columns=pm.feature_preprocessor.feature_names_in_).fillna(0)),
            columns=pm.feature_preprocessor.feature_names_in_)
        mp, sp = pm.regressor.predict(Xs[feats_p].values, return_std=True)
        fidelity["max_abs_diff_mean"] = round(float(np.max(np.abs(mp.ravel() - mu_all))), 5)
        fidelity["max_abs_diff_sd"] = round(float(np.max(np.abs(sp.ravel() - sd_all))), 5)
        print("fidelity vs pepper-lab", fidelity)

    cpd_small = cpd[["cropped_canonical_SMILES_no_stereo", "DT50_count"]].rename(
        columns={"cropped_canonical_SMILES_no_stereo": "SMILES", "DT50_count": "n"}).drop_duplicates("SMILES")
    train = df[["SMILES", "compound_name", "logDT50_mean", "logDT50_std"]].merge(cpd_small, on="SMILES", how="left")
    train["n"] = train["n"].fillna(1).astype(int)

    meta = {
        "engine": "PEPPER soil GPR (PaDEL 2D)",
        "version": f"pepper-soil-gpr-padel-1.0.0+fateintel.{dt.date.today():%Y%m%d}",
        "citation": "Hafner J, Cordero J, et al., Fenner K (2026) Confidently Uncertain: Probabilistic Machine "
                    "Learning to Predict Soil Biotransformation Half-Lives. Environ Sci Technol 60(14):11077. "
                    "Data: Latino et al. (2017) Eawag-Soil in enviPath, Environ Sci Process Impacts 19:449.",
        "code_licence": "pepper-lab MIT (FennerLabs); FateIntel wrapper - yours",
        "trained_on": {"n_compounds": int(len(df)), "n_half_lives": int(train.n.sum()),
                       "source": "EAWAG-SOIL package (enviPath), OECD 307 aerobic lab soil studies, EU pesticides + TPs",
                       "target": "Bayesian-inferred mean log10 DT50 (days) across soils",
                       "incubation_temperature_median_C": 20},
        "features": {"type": "PaDEL-Descriptor 2D", "n_after_preprocessing": len(final[2])},
        "regressor": {"type": "GaussianProcessRegressor", "kernel_fitted": str(final[3].kernel_),
                      "noise": "per-compound alpha = (between-soil log sd)^2"},
        "cross_validation": {"scheme": f"{a.repeats}x repeated 5-fold, random splits by compound",
                             "overall": overall, "by_predicted_sd_tertile": bins,
                             "by_confidence_class": conf, "persistence_classification_REACH_120d": cls},
        "confidence_rule": {"high": f"sd_of_mean <= {RULE['high_sd']} or max Tanimoto >= {RULE['high_tanimoto']}",
                            "low": f"(not high) and (sd_of_mean > {RULE['low_sd']} or max Tanimoto < {RULE['low_tanimoto']})",
                            "medium": "otherwise"},
        "persistence_screening_flag": {"rule": f"p_P >= {SCREEN_T}",
                                       "purpose": "prioritise for OECD 307 testing; tuned for high sensitivity",
                                       **cls["screening_by_p_P"][str(SCREEN_T)]},
        "fidelity_vs_pepper_lab": fidelity,
        "applicability_domain": ["single-component organic molecules, MW < 1200 Da",
                                 "best for pesticide-like chemistry; industrial chemicals, pharmaceuticals, PFAS, "
                                 "surfactants and ionic/permanently charged species are sparsely represented",
                                 "primary (parent) disappearance, not mineralisation; aerobic only"],
        "built": dt.datetime.now().isoformat(timespec="seconds"),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "scaler": final[0], "scaler_features": final[1], "model_features": final[2], "gpr": final[3],
        "training_set": train, "sigma_soil_median": float(np.median(ysd)),
        "confidence_bins": RULE, "screening_p_P": SCREEN_T,
        "meta": meta,
    }, OUT / "pepper_soil_gpr_padel.joblib", compress=3)
    (OUT / "model_card.json").write_text(json.dumps(meta, indent=2))
    cv.to_csv(OUT.parent.parent / "scripts" / "cv_predictions.csv", index=False)
    print("artifact written to", OUT)


if __name__ == "__main__":
    main()
