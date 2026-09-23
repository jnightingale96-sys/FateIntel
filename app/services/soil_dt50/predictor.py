"""
FateIntel soil biotransformation half-life (DT50) provider.

Engine: PEPPER soil model (Fenner Lab, Eawag / UZH) - Gaussian Process
Regressor (Matern nu=0.5 kernel, heteroscedastic noise from Bayesian-inferred
between-soil variability) on 2D PaDEL descriptors, trained on 867 pesticides
and pesticide transformation products (6,309 OECD 307 half-lives, EAWAG-SOIL
package in enviPath).

    Hafner J., Cordero J., Fenner K. et al. (2026) Confidently Uncertain:
    Probabilistic Machine Learning to Predict Soil Biotransformation
    Half-Lives. Environ. Sci. Technol. 60(14), 11077.

What this module adds for FateIntel:
  * a lean, pepper-lab-free runtime (sklearn + rdkit + padelpy/Java)
  * look-up of measured data when the compound is in EAWAG-SOIL
  * structural applicability domain (Tanimoto to training set) on top of the GPR sd
  * single-soil predictive interval (mean uncertainty + between-soil variability)
  * persistence probabilities for any regulatory thresholds
  * FOCUS/EFSA temperature, moisture and depth corrections to site conditions
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict, field
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator
from scipy.stats import norm

from .descriptors import prepare_structure, padel_descriptors, PreparedStructure
from . import corrections

MODEL_DIR = Path(__file__).resolve().parents[2] / "data" / "soil_dt50"
ARTIFACT = MODEL_DIR / "pepper_soil_gpr_padel.joblib"
MODEL_CARD = MODEL_DIR / "model_card.json"

# Regulatory soil persistence thresholds (days)
THRESHOLDS = {
    "REACH": (120.0, 180.0),        # Annex XIII P / vP (soil)
    "EU_PPP": (120.0, 180.0),       # Reg. 1107/2009 Annex II 3.7.2 (soil)
    "Stockholm": (180.0, None),     # POP screening criterion, soil
}

Z90 = norm.ppf(0.95)


@dataclass
class ChemicalInput:
    smiles: str
    id: str | None = None
    name: str | None = None


@dataclass
class SiteConditions:
    temperature_c: float | None = None
    moisture: float | None = None          # e.g. % MWHC or vol. water content
    moisture_ref: float | None = None      # same units, at pF2 / field capacity
    depth_cm: float | None = None
    ea_j_mol: float = corrections.EA_DEFAULT
    walker_b: float = corrections.B_WALKER_DEFAULT


@dataclass
class DT50Result:
    id: str | None
    name: str | None
    input_smiles: str
    smiles: str | None
    status: str                                   # ok | outside_domain | failed
    warnings: list[str] = field(default_factory=list)
    recommended: dict | None = None               # value FateIntel should carry forward
    prediction: dict | None = None
    experimental: dict | None = None
    persistence: dict | None = None
    applicability: dict | None = None
    site: dict | None = None
    provenance: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _r(x, n=3):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None if x is None or math.isnan(x) else x
    return round(float(x), n)


class SoilDT50Predictor:
    """Load once, reuse (the artifact is ~10 MB and holds the fitted GPR)."""

    def __init__(self, artifact_path: str | Path = ARTIFACT):
        a = joblib.load(artifact_path)
        self.scaler = a["scaler"]
        self.scaler_features: list[str] = list(a["scaler_features"])
        self.model_features: list[str] = list(a["model_features"])
        self.gpr = a["gpr"]
        self.train = a["training_set"].copy()          # SMILES, name, logDT50_mean, logDT50_std, n
        self.sigma_soil_default: float = float(a["sigma_soil_median"])
        self.confidence_bins: dict = a["confidence_bins"]
        self.screening_p_P: float = float(a.get("screening_p_P", 0.10))
        self.meta: dict = a["meta"]
        self._train_index = {s: i for i, s in enumerate(self.train["SMILES"])}

    # ------------------------------------------------------------------ AD
    @cached_property
    def _fpgen(self):
        return rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

    @cached_property
    def _train_fps(self):
        return [self._fpgen.GetFingerprint(Chem.MolFromSmiles(s)) for s in self.train["SMILES"]]

    def _similarity(self, smiles: str) -> dict:
        fp = self._fpgen.GetFingerprint(Chem.MolFromSmiles(smiles))
        sims = np.array(DataStructs.BulkTanimotoSimilarity(fp, self._train_fps))
        order = np.argsort(-sims)[:3]
        return {
            "max_tanimoto": _r(sims[order[0]]),
            "n_training_analogues_ge_0.5": int((sims >= 0.5).sum()),
            "nearest_training_compounds": [
                {"name": self.train["compound_name"].iloc[i], "smiles": self.train["SMILES"].iloc[i],
                 "tanimoto": _r(sims[i]),
                 "measured_DT50_days": _r(10 ** self.train["logDT50_mean"].iloc[i], 1)}
                for i in order
            ],
        }

    def _confidence(self, sd_mean: float, max_tan: float) -> str:
        """Rule calibrated on repeated 5-fold CV (see model card, by_confidence_class)."""
        cb = self.confidence_bins
        if sd_mean <= cb["high_sd"] or max_tan >= cb["high_tanimoto"]:
            return "high"
        if sd_mean > cb["low_sd"] or max_tan < cb["low_tanimoto"]:
            return "low"
        return "medium"

    # ------------------------------------------------------------ core GPR
    def _predict_features(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        # PEPPER: descriptors missing for a new compound are set to 0 before scaling
        X = X.reindex(columns=self.scaler_features).fillna(0.0)
        Xs = pd.DataFrame(self.scaler.transform(X.values), columns=self.scaler_features, index=X.index)
        Xm = Xs[self.model_features].values
        mu, sd = self.gpr.predict(Xm, return_std=True)
        return np.asarray(mu).ravel(), np.asarray(sd).ravel()

    # ---------------------------------------------------------- public API
    def predict(self, chemicals: Sequence[ChemicalInput | dict | str],
                conditions: SiteConditions | dict | None = None,
                regime: str = "REACH",
                thresholds: tuple[float, float | None] | None = None,
                sigma_soil: float | None = None,
                prefer_experimental: bool = True,
                strip_counterions: bool = True) -> list[DT50Result]:
        chems = [self._coerce(c) for c in chemicals]
        if isinstance(conditions, dict):
            conditions = SiteConditions(**conditions)
        t_p, t_vp = thresholds or THRESHOLDS.get(regime, THRESHOLDS["REACH"])
        s_soil = self.sigma_soil_default if sigma_soil is None else float(sigma_soil)

        prepared: list[PreparedStructure] = [prepare_structure(c.smiles, strip_counterions) for c in chems]
        valid_smiles = [p.smiles for p in prepared if p.valid]
        preds: dict[str, tuple[float, float]] = {}
        if valid_smiles:
            desc = padel_descriptors(valid_smiles)
            if not desc.empty:
                mu, sd = self._predict_features(desc)
                preds = {s: (m, d) for s, m, d in zip(desc.index, mu, sd)}

        results = []
        for c, p in zip(chems, prepared):
            res = DT50Result(id=c.id, name=c.name, input_smiles=c.smiles, smiles=p.smiles,
                             status="ok", warnings=list(p.warnings), provenance=self._provenance())
            if not p.valid:
                res.status = "outside_domain"
                results.append(res)
                continue
            if p.smiles not in preds:
                res.status = "failed"
                res.warnings.append("PaDEL descriptors could not be calculated")
                results.append(res)
                continue

            mu, sd_mean = preds[p.smiles]
            sd_single = math.sqrt(sd_mean ** 2 + s_soil ** 2)
            res.prediction = {
                "logDT50_mean": _r(mu), "logDT50_sd_of_mean": _r(sd_mean),
                "DT50_days": _r(10 ** mu, 2),
                "DT50_mean_90CI_days": [_r(10 ** (mu - Z90 * sd_mean), 2), _r(10 ** (mu + Z90 * sd_mean), 2)],
                "DT50_single_soil_90PI_days": [_r(10 ** (mu - Z90 * sd_single), 2), _r(10 ** (mu + Z90 * sd_single), 2)],
                "sigma_between_soils_used": _r(s_soil),
                "reference_conditions": "aerobic laboratory soil (OECD 307), ~20 °C, ~pF2; primary (parent) disappearance",
            }

            # measured data where the compound is part of EAWAG-SOIL
            ti = self._train_index.get(p.smiles)
            if ti is not None:
                row = self.train.iloc[ti]
                res.experimental = {
                    "source": "EAWAG-SOIL (enviPath) - Bayesian-inferred across studies",
                    "compound_name": row["compound_name"],
                    "logDT50_mean": _r(row["logDT50_mean"]), "logDT50_sd_between_soils": _r(row["logDT50_std"]),
                    "DT50_days": _r(10 ** row["logDT50_mean"], 2), "n_half_lives": int(row["n"]),
                }
                res.warnings.append("compound is in the training set - prediction is a fitted, not an independent, value")

            use_exp = prefer_experimental and res.experimental is not None
            if use_exp:
                m_use = res.experimental["logDT50_mean"]
                s_use = max(res.experimental["logDT50_sd_between_soils"] / math.sqrt(max(res.experimental["n_half_lives"], 1)), 0.02)
            else:
                m_use, s_use = mu, sd_mean

            res.persistence = self._persistence(m_use, s_use, t_p, t_vp, regime if thresholds is None else "custom")
            res.persistence["screening_flag_potential_P"] = bool(res.persistence["p_P"] >= self.screening_p_P)
            res.persistence["screening_rule"] = f"p_P >= {self.screening_p_P} (CV sensitivity ~0.88, specificity ~0.51 at 120 d)"
            if self._is_perfluoroalkyl(p.smiles):
                # expert override: perfluoroalkyl chains do not biodegrade in soil; PEPPER training has ~no PFAS
                res.persistence.update({"class_central": "vP", "class_precautionary_upper95": "vP",
                                        "screening_flag_potential_P": True,
                                        "override": "perfluoroalkyl moiety - classified vP by expert rule, "
                                                    "numeric DT50 not reliable"})
            sim = self._similarity(p.smiles)
            sim["prediction_confidence"] = self._confidence(sd_mean, sim["max_tanimoto"])
            sim["notes"] = self._domain_notes(p.smiles)
            res.applicability = sim
            if sim["prediction_confidence"] == "low" and not use_exp:
                res.warnings.append("low-confidence prediction - consider testing or read-across")

            dt50_ref = 10 ** m_use
            res.recommended = {
                "DT50_ref_days": _r(dt50_ref, 2),
                "logDT50": _r(m_use), "logDT50_sd": _r(s_use),
                "basis": "measured (EAWAG-SOIL)" if use_exp else "predicted (PEPPER GPR)",
                "confidence": "measured" if use_exp else sim["prediction_confidence"],
            }
            if conditions is not None:
                if (conditions.moisture is None) != (conditions.moisture_ref is None):
                    res.warnings.append(
                        "moisture correction NOT applied: it needs both moisture and moisture_ref (same units)")
                dt50_site, f = corrections.to_site_conditions(
                    dt50_ref, temp_c=conditions.temperature_c, theta=conditions.moisture,
                    theta_ref=conditions.moisture_ref, depth_cm=conditions.depth_cm,
                    ea=conditions.ea_j_mol, b=conditions.walker_b)
                res.site = {"conditions": asdict(conditions),
                            "factors": {k: _r(v, 4) for k, v in f.items()},
                            "DT50_site_days": _r(dt50_site, 2),
                            "k_site_per_day": _r(math.log(2) / dt50_site, 6) if math.isfinite(dt50_site) else 0.0}
            results.append(res)
        return results

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _coerce(c) -> ChemicalInput:
        if isinstance(c, ChemicalInput):
            return c
        if isinstance(c, str):
            return ChemicalInput(smiles=c)
        return ChemicalInput(**{k: c.get(k) for k in ("smiles", "id", "name")})

    @staticmethod
    def _persistence(mu, sd, t_p, t_vp, regime) -> dict:
        z = lambda t: (math.log10(t) - mu) / sd
        p_P = 1 - norm.cdf(z(t_p))
        out = {"regime": regime, "threshold_P_days": t_p, "threshold_vP_days": t_vp,
               "p_nP": _r(1 - p_P), "p_P": _r(p_P)}
        cls = "P" if mu > math.log10(t_p) else "nP"
        upper = mu + norm.ppf(0.975) * sd
        cls_prec = "P" if upper > math.log10(t_p) else "nP"
        if t_vp:
            p_vP = 1 - norm.cdf(z(t_vp))
            out["p_vP"] = _r(p_vP)
            if mu > math.log10(t_vp):
                cls = "vP"
            if upper > math.log10(t_vp):
                cls_prec = "vP"
        out["class_central"] = cls
        out["class_precautionary_upper95"] = cls_prec
        return out

    @staticmethod
    def _is_perfluoroalkyl(smiles: str) -> bool:
        # >= C3 fully fluorinated chain (CF3-CF2-CF2- or -CF2-CF2-CF2-)
        return Chem.MolFromSmiles(smiles).HasSubstructMatch(
            Chem.MolFromSmarts("C(F)(F)C(F)(F)C(F)(F)"))

    @staticmethod
    def _domain_notes(smiles: str) -> list[str]:
        mol = Chem.MolFromSmiles(smiles)
        notes = []
        n_f = sum(a.GetSymbol() == "F" for a in mol.GetAtoms())
        if mol.HasSubstructMatch(Chem.MolFromSmarts("C(F)(F)C(F)(F)")) or n_f >= 6:
            notes.append("perfluoroalkyl moiety - training set has few PFAS; treat terminal perfluorinated "
                         "products as very persistent regardless of prediction")
        if any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()) and not mol.HasSubstructMatch(Chem.MolFromSmarts("[N+](=O)[O-]")):
            notes.append("permanently charged species - sparsely represented in training data")
        if mol.GetNumHeavyAtoms() > 50:
            notes.append("large molecule (>50 heavy atoms) - sparsely represented in training data")
        return notes

    def _provenance(self) -> dict:
        return {"provider": "fateintel.soil_dt50", "engine": self.meta["engine"],
                "model_version": self.meta["version"], "citation": self.meta["citation"]}

    def model_card(self) -> dict:
        return json.loads(MODEL_CARD.read_text(encoding="utf-8")) if MODEL_CARD.exists() else self.meta


_default: SoilDT50Predictor | None = None


def get_predictor() -> SoilDT50Predictor:
    global _default
    if _default is None:
        _default = SoilDT50Predictor()
    return _default
