"""Soil degradation (DT50) provider -- PEPPER probabilistic GPR engine (Fenner Lab, Eawag/UZH).

Heavy dependencies (scikit-learn, RDKit, padelpy + a Java runtime) are imported lazily by ``predictor`` so the
application starts without them; ``availability()`` reports what is missing. ``corrections`` has no dependencies.
"""
from __future__ import annotations

import shutil
from importlib.util import find_spec

from ...config import Settings, settings

PROVIDER_KEY = "soil_dt50_pepper"
PROVIDER_VERSION = "fateintel-soil-dt50-1.0.0"
CITATION = (
    "Hafner J, Cordero J, et al., Fenner K (2026) Confidently Uncertain: Probabilistic Machine Learning to Predict "
    "Soil Biotransformation Half-Lives. Environ Sci Technol 60(14):11077. Training data: Latino DARS et al. (2017) "
    "Eawag-Soil in enviPath, Environ Sci Process Impacts 19:449."
)
REQUIRED_MODULES = ("sklearn", "rdkit", "padelpy", "pandas", "joblib")


def commercial_gate(configuration: Settings = settings) -> tuple[bool, str]:
    """The model artifact embeds the EAWAG-SOIL training set (structures and measured DT50s, used for the measured-
    value lookup and nearest-analogue output). Its redistribution terms are not confirmed, so -- exactly like the
    enviPath adapter -- it runs in local/test evaluation and is closed elsewhere until an operator confirms a licence."""
    if configuration.soil_dt50_commercial_license_confirmed:
        return True, "commercial_licence_confirmed_by_operator"
    if configuration.envirochem_environment in {"local", "test"} and not configuration.commercial_license_gate_strict:
        return True, "academic_or_development_evaluation_only"
    return False, "eawag_soil_training_data_licence_required_for_staging_or_production"


def availability() -> dict:
    missing = [m for m in REQUIRED_MODULES if find_spec(m) is None]
    if shutil.which("java") is None:
        missing.append("java runtime (PaDEL)")
    return {"available": not missing, "missing": missing}


def capabilities(configuration: Settings = settings) -> dict:
    gate_open, licence_status = commercial_gate(configuration)
    avail = availability()
    return {
        "provider_key": PROVIDER_KEY, "provider_version": PROVIDER_VERSION,
        "enabled": bool(configuration.soil_dt50_enabled and gate_open and avail["available"]),
        "configured": bool(configuration.soil_dt50_enabled), "licence_status": licence_status, **avail,
        "endpoint": "primary disappearance of the parent in aerobic laboratory soil (OECD 307), reference ~20 C / pF2",
        "not_provided": ["mineralisation", "field dissipation", "anaerobic degradation", "transformation products",
                         "regulatory (OECD-accepted) QSAR status: no QMRF exists for this model"],
        "citation": CITATION,
    }
