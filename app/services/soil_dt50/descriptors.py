"""
Structure handling and PaDEL descriptor calculation for the soil DT50 provider.

Reproduces the PEPPER (Fenner Lab, Eawag) input processing:
  * PaDEL-Descriptor 2D descriptors via padelpy (Yap 2011, doi:10.1002/jcc.21707)
  * RDKit canonical SMILES without stereochemistry (training-set representation)
  * PEPPER applicability pre-checks: single component, organic (contains C), MW < 1200 Da

Requires a Java runtime (PaDEL is a Java program).
"""
from __future__ import annotations

import os
import re
import contextlib
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors as RDDesc
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

MAX_MW = 1200.0
PADEL_BATCH = 30


@dataclass
class PreparedStructure:
    input_smiles: str
    smiles: str | None = None          # canonical, stereo-free SMILES used for modelling
    mw: float | None = None
    valid: bool = False
    warnings: list[str] = field(default_factory=list)


def _canonical_no_stereo(mol: Chem.Mol) -> str:
    mol = Chem.Mol(mol)
    Chem.rdmolops.RemoveStereochemistry(mol)
    smi = Chem.MolToSmiles(mol)
    smi = re.sub(r"[\\/]", "", smi)
    return Chem.CanonSmiles(smi)


def prepare_structure(smiles: str, strip_counterions: bool = True) -> PreparedStructure:
    """Validate and standardise one SMILES string.

    PEPPER rejects multi-component structures. For regulatory screening of salts
    (common for pharmaceuticals / veterinary medicines) the parent organic
    fragment is usually what is assessed, so by default the largest organic
    fragment is kept, neutralised, and a warning is attached.
    """
    p = PreparedStructure(input_smiles=smiles)
    if not isinstance(smiles, str) or not smiles.strip():
        p.warnings.append("no SMILES provided")
        return p
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        p.warnings.append("SMILES could not be parsed")
        return p

    if len(Chem.GetMolFrags(mol)) > 1:
        if not strip_counterions:
            p.warnings.append("composite structure (salt/mixture) - outside PEPPER domain")
            return p
        chooser = rdMolStandardize.LargestFragmentChooser(preferOrganic=True)
        mol = chooser.choose(mol)
        mol = rdMolStandardize.Uncharger().uncharge(mol)
        p.warnings.append("multi-component input: largest organic fragment used (neutralised)")

    if not any(a.GetSymbol() == "C" for a in mol.GetAtoms()):
        p.warnings.append("inorganic molecule - outside domain")
        return p

    p.mw = float(RDDesc.MolWt(mol))
    if p.mw >= MAX_MW:
        p.warnings.append(f"MW {p.mw:.0f} Da >= {MAX_MW:.0f} Da - outside domain")
        return p

    p.smiles = _canonical_no_stereo(mol)
    p.valid = True
    return p


@contextlib.contextmanager
def _quiet_java_env():
    """padelpy treats anything on stderr as a failure; JAVA_TOOL_OPTIONS makes the
    JVM print a banner to stderr, so hide it for the duration of the call."""
    saved = os.environ.pop("JAVA_TOOL_OPTIONS", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["JAVA_TOOL_OPTIONS"] = saved


def padel_descriptors(smiles_list: Iterable[str], timeout: int = 120) -> pd.DataFrame:
    """Calculate 2D PaDEL descriptors. Returns a DataFrame indexed by SMILES with
    columns prefixed 'PaDEL-' (PEPPER naming). Compounds that fail are omitted."""
    from padelpy import from_smiles

    smiles_list = list(dict.fromkeys(smiles_list))  # de-duplicate, keep order
    rows: dict[str, dict] = {}
    with _quiet_java_env():
        for i in range(0, len(smiles_list), PADEL_BATCH):
            batch = smiles_list[i:i + PADEL_BATCH]
            try:
                out = from_smiles(batch, timeout=timeout)
                if isinstance(out, dict):
                    out = [out]
                for smi, d in zip(batch, out):
                    rows[smi] = d
            except RuntimeError:
                for smi in batch:
                    try:
                        rows[smi] = from_smiles(smi, timeout=timeout)
                    except RuntimeError:
                        pass
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.columns = [f"PaDEL-{c}" for c in df.columns]
    df = df.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return df
