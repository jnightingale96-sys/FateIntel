from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import settings

# Native Python RDKit is optional. On managed Windows machines App Control may
# block rdBase DLLs even though pip installation succeeds. EnviroChem therefore
# does not touch native RDKit unless explicitly enabled; the local UI uses the
# official RDKit.js WebAssembly distribution as its primary structure engine.
NATIVE_RDKIT_REQUESTED = settings.envirochem_native_rdkit
RDKIT_AVAILABLE = False
RDKIT_IMPORT_ERROR: str | None = None
Chem = Crippen = Descriptors = Lipinski = rdFMCS = rdMolDescriptors = rdMolDraw2D = None
if NATIVE_RDKIT_REQUESTED:
    try:
        from rdkit import Chem
        from rdkit.Chem import Crippen, Descriptors, Lipinski, rdFMCS, rdMolDescriptors
        from rdkit.Chem.Draw import rdMolDraw2D
        RDKIT_AVAILABLE = True
    except Exception as exc:  # pragma: no cover - platform/DLL failures must not prevent core startup
        RDKIT_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
else:
    RDKIT_IMPORT_ERROR = "Native Python RDKit disabled by default; browser RDKit.js/WebAssembly is the local primary engine."


def _require_rdkit() -> None:
    if not RDKIT_AVAILABLE:
        raise ValueError(
            "The optional native Python RDKit backend is unavailable. "
            "Use the EnviroDesign browser/WASM engine in the local interface, or explicitly enable the native backend on a machine whose application-control policy permits RDKit DLLs. "
            f"Native backend status: {RDKIT_IMPORT_ERROR}"
        )

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BIOWIN_DATA = json.loads((DATA_DIR / "biowin34_fragments.json").read_text(encoding="utf-8"))
ENVIPATH_MANIFEST = json.loads((DATA_DIR / "envipath_manifest.json").read_text(encoding="utf-8"))
MODEL_COVERAGE = json.loads((DATA_DIR / "biowin_model_coverage.json").read_text(encoding="utf-8"))

MODEL_VERSION = "envirodesign-structural-attribution-0.2.0"

# These are transparent structure-inventory alerts, not BIOWIN coefficients.
FEATURE_SMARTS = {
    # Human-readable structural regions. These are inventory alerts, not fitted
    # BIOWIN coefficients. Exact BIOWIN terms are reported separately.
    "benzene_like_aromatic_ring": "c1ccccc1",
    "carboxamide": "[CX3](=[OX1])[NX3]",
    "ester": "[CX3](=[OX1])[OX2][#6]",
    "ether": "[OD2]([#6])[#6]",
    "alcohol": "[OX2H][#6]",
    "aldehyde": "[CX3H1](=O)[#6]",
    "aliphatic_alkene": "[C;!a]=[C;!a]",
    "tertiary_amine": "[NX3;H0;!$(N-C=[O,S,N])]([#6])([#6])[#6]",
    "aromatic_halogen": "[c][F,Cl,Br,I]",
    "nitro": "[N+](=O)[O-]",
    "nitrile": "[C]#N",
    "azo": "[N]=[N]",
    "sulfonamide": "S(=O)(=O)N",
    "quaternary_carbon": "[CX4;H0]([#6])([#6])([#6])[#6]",
    "hydrolysable_carbamate": "[OX2][CX3](=[OX1])[NX3]",
}


def manifest() -> dict[str, Any]:
    return {
        "model_version": MODEL_VERSION,
        "runtime": {
            "preferred_engine": "rdkit-js-wasm-browser",
            "browser_wasm_delivery": "remote official RDKit.js distribution for this prototype build",
            "native_python_rdkit_requested": NATIVE_RDKIT_REQUESTED,
            "rdkit_available": RDKIT_AVAILABLE,
            "rdkit_import_error": RDKIT_IMPORT_ERROR,
        },
        "biowin": {
            "name": BIOWIN_DATA["model_name"],
            "source_status": BIOWIN_DATA["source_status"],
            "fragment_count": len(BIOWIN_DATA["fragments"]),
            "limitations": BIOWIN_DATA["limitations"],
            "coverage": MODEL_COVERAGE,
        },
        "envipath": ENVIPATH_MANIFEST,
        "scientific_rule": (
            "EnviroDesign generates explainable screening hypotheses. It does not claim that a matched "
            "fragment is a demonstrated causal driver of persistence, and it does not replace measured "
            "biodegradation, transformation-product or efficacy data."
        ),
    }


def browser_config() -> dict[str, Any]:
    """Data required by the browser/WebAssembly EnviroDesign engine.

    This endpoint is intentionally independent of native Python RDKit so that
    managed Windows machines can run the structural screen without importing
    blocked native DLLs.
    """
    return {
        "model_version": MODEL_VERSION,
        "biowin": BIOWIN_DATA,
        "model_coverage": MODEL_COVERAGE,
        "feature_smarts": FEATURE_SMARTS,
        "engine": {
            "preferred": "rdkit-js-wasm-browser",
            "native_python_optional": True,
            "scientific_status": "screening reconstruction; not regulatory-equivalent EPA BIOWIN output",
        },
    }


def _mol(smiles: str) -> Chem.Mol:
    _require_rdkit()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("SMILES could not be parsed by RDKit")
    return mol


def _matches(mol: Chem.Mol, smarts: str) -> list[tuple[int, ...]]:
    query = Chem.MolFromSmarts(smarts)
    if query is None:
        return []
    return list(mol.GetSubstructMatches(query, uniquify=True))


def _beta_lactam_atoms(mol: Chem.Mol) -> list[int]:
    """Identify cyclic amide C-N units contained in a four-membered ring."""
    ring_info = mol.GetRingInfo()
    four_rings = [set(ring) for ring in ring_info.AtomRings() if len(ring) == 4]
    atoms: set[int] = set()
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() != 6:
            continue
        carbonyl_oxygen = any(
            bond.GetBondType() == Chem.BondType.DOUBLE and bond.GetOtherAtom(atom).GetAtomicNum() == 8
            for bond in atom.GetBonds()
        )
        if not carbonyl_oxygen:
            continue
        for neighbour in atom.GetNeighbors():
            if neighbour.GetAtomicNum() != 7:
                continue
            for ring in four_rings:
                if atom.GetIdx() in ring and neighbour.GetIdx() in ring:
                    atoms.update(ring)
    return sorted(atoms)


def _structure_inventory(mol: Chem.Mol) -> dict[str, Any]:
    heavy = mol.GetNumHeavyAtoms()
    aromatic_atoms = [atom.GetIdx() for atom in mol.GetAtoms() if atom.GetIsAromatic()]
    halogens = [atom.GetIdx() for atom in mol.GetAtoms() if atom.GetAtomicNum() in {9, 17, 35, 53}]
    hetero = [atom.GetIdx() for atom in mol.GetAtoms() if atom.GetAtomicNum() not in {1, 6}]
    rings = [set(ring) for ring in mol.GetRingInfo().AtomRings()]
    atom_ring_membership: dict[int, int] = {}
    for ring in rings:
        for idx in ring:
            atom_ring_membership[idx] = atom_ring_membership.get(idx, 0) + 1
    fused_atoms = sorted(idx for idx, n in atom_ring_membership.items() if n > 1)

    features: list[dict[str, Any]] = []
    for key, smarts in FEATURE_SMARTS.items():
        matches = _matches(mol, smarts)
        if matches:
            # A carbonyl attached to two nitrogens can produce two SMARTS tuples even
            # though it is one carbonyl centre. Count distinct centres for this alert.
            count = len({match[0] for match in matches}) if key == "carboxamide" else len(matches)
            features.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "count": count,
                "atom_indices": sorted({idx for match in matches for idx in match}),
                "basis": "transparent RDKit structure alert; no fitted BIOWIN coefficient",
            })

    beta_atoms = _beta_lactam_atoms(mol)
    if beta_atoms:
        features.append({
            "key": "beta_lactam",
            "label": "β-lactam ring",
            "count": 1,
            "atom_indices": beta_atoms,
            "basis": "four-membered cyclic amide alert; primary ring opening and ultimate mineralisation must be separated",
        })

    if rdMolDescriptors.CalcNumAromaticRings(mol) >= 2:
        features.append({
            "key": "polycyclic_aromatic_scaffold",
            "label": "Polycyclic aromatic scaffold",
            "count": rdMolDescriptors.CalcNumAromaticRings(mol),
            "atom_indices": aromatic_atoms,
            "basis": "structure-inventory alert; requires analogue/pathway evidence before causal interpretation",
        })
    if fused_atoms:
        features.append({
            "key": "fused_ring_junctions",
            "label": "Fused ring junctions",
            "count": len(fused_atoms),
            "atom_indices": fused_atoms,
            "basis": "structure-inventory alert; may indicate a rigid scaffold but is not itself a persistence endpoint",
        })
    if heavy and len(aromatic_atoms) / heavy >= 0.55:
        features.append({
            "key": "high_aromatic_atom_fraction",
            "label": "High aromatic atom fraction",
            "count": len(aromatic_atoms),
            "atom_indices": aromatic_atoms,
            "basis": "descriptor alert; interpretation requires model and analogue support",
        })
    if halogens:
        features.append({
            "key": "halogenated_structure",
            "label": "Halogenated structure",
            "count": len(halogens),
            "atom_indices": halogens,
            "basis": "elemental structure alert; individual halogens and attachment contexts differ",
        })

    return {
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight_g_mol": Descriptors.MolWt(mol),
        "exact_mass": Descriptors.ExactMolWt(mol),
        "logp_rdkit": Crippen.MolLogP(mol),
        "tpsa_a2": rdMolDescriptors.CalcTPSA(mol),
        "h_bond_donors": Lipinski.NumHDonors(mol),
        "h_bond_acceptors": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "ring_count": rdMolDescriptors.CalcNumRings(mol),
        "aromatic_ring_count": rdMolDescriptors.CalcNumAromaticRings(mol),
        "aromatic_atom_fraction": (len(aromatic_atoms) / heavy) if heavy else 0.0,
        "heavy_atom_count": heavy,
        "hetero_atom_count": len(hetero),
        "features": features,
    }


def _fragment_attribution(mol: Chem.Mol) -> dict[str, Any]:
    b3 = float(BIOWIN_DATA["terms"]["intercept"]["biowin3"])
    b4 = float(BIOWIN_DATA["terms"]["intercept"]["biowin4"])
    mw = Descriptors.MolWt(mol)
    mw3 = mw * float(BIOWIN_DATA["terms"]["MW"]["biowin3"])
    mw4 = mw * float(BIOWIN_DATA["terms"]["MW"]["biowin4"])
    b3 += mw3
    b4 += mw4

    attributions: list[dict[str, Any]] = []
    for fragment in BIOWIN_DATA["fragments"]:
        matches = _matches(mol, fragment["smarts"])
        if not matches:
            continue
        count = len(matches)
        c3 = count * float(fragment["biowin3_coefficient"])
        c4 = count * float(fragment["biowin4_coefficient"])
        b3 += c3
        b4 += c4
        attributions.append({
            "fragment_id": fragment["id"],
            "description": fragment["description"],
            "smarts": fragment["smarts"],
            "count": count,
            "biowin3_contribution": c3,
            "biowin4_contribution": c4,
            "atom_indices": sorted({idx for match in matches for idx in match}),
            "source_status": fragment["source_status"],
        })

    components = [
        {
            "description": "Equation intercept",
            "count": 1,
            "biowin3_contribution": BIOWIN_DATA["terms"]["intercept"]["biowin3"],
            "biowin4_contribution": BIOWIN_DATA["terms"]["intercept"]["biowin4"],
            "atom_indices": [],
        },
        {
            "description": "Molecular-weight term",
            "count": 1,
            "biowin3_contribution": mw3,
            "biowin4_contribution": mw4,
            "atom_indices": list(range(mol.GetNumAtoms())),
        },
    ] + attributions

    return {
        "biowin3_ultimate_score": b3,
        "biowin4_primary_score": b4,
        "matched_fragment_count": len(attributions),
        "matched_occurrence_count": sum(item["count"] for item in attributions),
        "components": sorted(
            components,
            key=lambda row: max(abs(float(row["biowin3_contribution"])), abs(float(row["biowin4_contribution"]))),
            reverse=True,
        ),
        "interpretation": (
            "Higher scores indicate a faster predicted timeframe within this approximate reconstruction. "
            "Do not map these values to regulatory-equivalent BIOWIN categories until validated against "
            "official EPI Suite detailed output."
        ),
    }


def _design_hypotheses(inventory: dict[str, Any], attribution: dict[str, Any]) -> list[dict[str, Any]]:
    feature_keys = {feature["key"] for feature in inventory["features"]}
    negative_fragments = [
        row for row in attribution["components"]
        if row.get("atom_indices") and (
            float(row["biowin3_contribution"]) < 0 or float(row["biowin4_contribution"]) < 0
        ) and row["description"] != "Molecular-weight term"
    ]
    suggestions: list[dict[str, Any]] = []

    if "aromatic_halogen" in feature_keys or "halogenated_structure" in feature_keys:
        suggestions.append({
            "feature": "Halogenated aromatic or aliphatic region",
            "hypothesis": "Explore removal, relocation or a non-halogen bioisostere at an R&D-permitted position.",
            "why": "The supplied BIOWIN reconstruction contains several attachment-specific halogen fragments with negative coefficients.",
            "tradeoffs": ["potency or selectivity", "metabolic stability", "pKa/logD", "groundwater mobility", "transformation-product toxicity"],
            "confidence": "moderate when the exact fitted SMARTS is matched; otherwise low",
        })
    if "polycyclic_aromatic_scaffold" in feature_keys or "high_aromatic_atom_fraction" in feature_keys:
        suggestions.append({
            "feature": "Rigid aromatic scaffold",
            "hypothesis": "Test analogues that reduce aromaticity, interrupt ring fusion or introduce an accessible transformation handle outside the protected pharmacophore.",
            "why": "The structure inventory shows a high aromatic burden. Causal attribution requires matched analogues or observed pathway retention.",
            "tradeoffs": ["target binding", "photochemistry", "oxidative metabolism", "synthetic feasibility", "aqueous solubility"],
            "confidence": "low until supported by analogue or pathway evidence",
        })
    if "tertiary_amine" in feature_keys:
        suggestions.append({
            "feature": "Tertiary amine",
            "hypothesis": "Explore pKa-tuned or sterically less shielded analogues while keeping the required charge state and pharmacology constrained.",
            "why": "The supplied BIOWIN 3/4 reconstruction assigns negative coefficients to its tertiary-amine fragment.",
            "tradeoffs": ["membrane permeability", "receptor binding", "ion trapping", "sorption to solids", "toxicity"],
            "confidence": "moderate for model direction; biological outcome unknown",
        })
    if "quaternary_carbon" in feature_keys:
        suggestions.append({
            "feature": "Fully substituted carbon centre",
            "hypothesis": "Where function allows, test reduced branching or greater accessibility near potential transformation sites.",
            "why": "A carbon with four single bonds and no hydrogens is represented by a negative fragment in the supplied reconstruction.",
            "tradeoffs": ["conformation", "stability", "selectivity", "manufacturability"],
            "confidence": "moderate for exact fragment match",
        })
    if "beta_lactam" in feature_keys:
        suggestions.append({
            "feature": "β-lactam ring",
            "hypothesis": "Treat ring opening as a primary-degradation and bioactivity-loss pathway, then separately assess the opened products for ultimate degradation.",
            "why": "The ordinary BIOWIN amide fragment does not encode four-membered-ring strain.",
            "tradeoffs": ["antibacterial activity", "hydrolysis stability", "persistent ring-opened products"],
            "confidence": "high structural alert; environmental rate remains evidence-dependent",
        })
    if inventory["molecular_weight_g_mol"] > 400:
        suggestions.append({
            "feature": "High molecular weight",
            "hypothesis": "Assess whether non-essential mass can be removed without compromising the required function.",
            "why": "Molecular weight contributes negatively to both reconstructed models.",
            "tradeoffs": ["function", "exposure", "bioavailability", "synthesis"],
            "confidence": "model-based screening only",
        })
    for row in negative_fragments[:3]:
        suggestions.append({
            "feature": row["description"],
            "hypothesis": "Create a matched molecular pair that changes this feature while preserving the user-locked functional core.",
            "why": (
                f"Direct matched contribution: BIOWIN 3 {row['biowin3_contribution']:+.3f}; "
                f"BIOWIN 4 {row['biowin4_contribution']:+.3f}."
            ),
            "tradeoffs": ["whole-molecule fate", "functional performance", "new transformation products"],
            "confidence": "moderate for score attribution; causal persistence remains unproven",
        })

    if not suggestions:
        suggestions.append({
            "feature": "No decisive fitted hotspot",
            "hypothesis": "Prioritise matched analogues and observed transformation products rather than forcing a structural substitution.",
            "why": "The available reconstructed fragment set did not identify a strong, direct negative hotspot for this structure.",
            "tradeoffs": ["additional evidence generation", "analogue selection"],
            "confidence": "high that more evidence is needed",
        })
    # Preserve order while removing duplicate feature labels.
    unique: dict[str, dict[str, Any]] = {}
    for item in suggestions:
        unique.setdefault(item["feature"], item)
    return list(unique.values())


def _svg(mol: Chem.Mol, attribution: dict[str, Any], inventory: dict[str, Any]) -> str:
    negative_atoms: set[int] = set()
    positive_atoms: set[int] = set()
    for component in attribution["components"]:
        if component["description"] in {"Equation intercept", "Molecular-weight term"}:
            continue
        target = negative_atoms if (
            component["biowin3_contribution"] < 0 or component["biowin4_contribution"] < 0
        ) else positive_atoms
        target.update(component.get("atom_indices", []))
    alert_atoms = {
        idx for feature in inventory["features"]
        for idx in feature["atom_indices"]
    }
    all_atoms = sorted(negative_atoms | positive_atoms | alert_atoms)
    colours: dict[int, tuple[float, float, float]] = {}
    for idx in alert_atoms:
        colours[idx] = (0.17, 0.58, 0.48)
    for idx in positive_atoms:
        colours[idx] = (0.24, 0.68, 0.40)
    for idx in negative_atoms:
        colours[idx] = (0.91, 0.47, 0.19)

    drawer = rdMolDraw2D.MolDraw2DSVG(620, 350)
    options = drawer.drawOptions()
    options.clearBackground = False
    options.addAtomIndices = False
    options.legendFontSize = 14
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer,
        mol,
        highlightAtoms=all_atoms,
        highlightAtomColors=colours,
        legend="Orange: fitted negative contribution · Green: fitted positive · Teal: structural alert",
    )
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def analyse_structure(smiles: str, name: str | None = None, include_svg: bool = True) -> dict[str, Any]:
    _require_rdkit()
    mol = _mol(smiles)
    canonical = Chem.MolToSmiles(mol, canonical=True)
    inventory = _structure_inventory(mol)
    attribution = _fragment_attribution(mol)
    output = {
        "model_version": MODEL_VERSION,
        "name": name or "Unlabelled structure",
        "input_smiles": smiles,
        "canonical_smiles": canonical,
        "inchi_key": Chem.MolToInchiKey(mol),
        "structure": inventory,
        "biowin_screen": attribution,
        "design_hypotheses": _design_hypotheses(inventory, attribution),
        "confidence": {
            "identity": "high after successful RDKit parsing; stereochemistry depends on the supplied SMILES",
            "fragment_attribution": "screening",
            "causal_persistence_assignment": "not established",
            "regulatory_equivalence": "not established",
        },
        "warnings": list(BIOWIN_DATA["limitations"]) + [
            "A structural feature can correlate with a prediction without being the experimentally demonstrated cause of persistence.",
            "Primary degradation, ultimate degradation, bioactivity loss and transformation-product persistence are separate endpoints.",
        ],
    }
    if include_svg:
        output["structure_svg"] = _svg(mol, attribution, inventory)
    return output


def compare_candidates(
    original_smiles: str,
    candidates: list[dict[str, str]],
    protected_smarts: list[str] | None = None,
) -> dict[str, Any]:
    _require_rdkit()
    original = analyse_structure(original_smiles, "Original", include_svg=False)
    protected_smarts = protected_smarts or []
    original_mol = _mol(original_smiles)
    protected_queries = []
    for smarts in protected_smarts:
        query = Chem.MolFromSmarts(smarts)
        if query is None:
            raise ValueError(f"Protected SMARTS could not be parsed: {smarts}")
        if not original_mol.HasSubstructMatch(query):
            raise ValueError(f"Protected SMARTS is not present in the original structure: {smarts}")
        protected_queries.append((smarts, query))

    rows = []
    for candidate in candidates:
        analysed = analyse_structure(candidate["smiles"], candidate.get("name") or "Candidate", include_svg=False)
        mol = _mol(candidate["smiles"])
        d3 = analysed["biowin_screen"]["biowin3_ultimate_score"] - original["biowin_screen"]["biowin3_ultimate_score"]
        d4 = analysed["biowin_screen"]["biowin4_primary_score"] - original["biowin_screen"]["biowin4_primary_score"]
        if d3 > 0 and d4 > 0:
            direction = "higher_in_both_screening_models"
        elif d3 < 0 and d4 < 0:
            direction = "lower_in_both_screening_models"
        else:
            direction = "mixed_primary_vs_ultimate_direction"
        preserved = [{"smarts": smarts, "preserved": mol.HasSubstructMatch(query)} for smarts, query in protected_queries]
        tradeoffs = []
        dlogp = analysed["structure"]["logp_rdkit"] - original["structure"]["logp_rdkit"]
        dtpsa = analysed["structure"]["tpsa_a2"] - original["structure"]["tpsa_a2"]
        dmw = analysed["structure"]["molecular_weight_g_mol"] - original["structure"]["molecular_weight_g_mol"]
        if dlogp > 0.3:
            tradeoffs.append("Calculated logP increased; bioaccumulation/sorption consequences require review")
        if dlogp < -0.3:
            tradeoffs.append("Calculated logP decreased; groundwater mobility may increase")
        if abs(dtpsa) > 20:
            tradeoffs.append("Polar surface area changed substantially; function and permeability may change")
        if dmw > 50:
            tradeoffs.append("Molecular weight increased substantially")
        if any(not item["preserved"] for item in preserved):
            tradeoffs.append("At least one user-protected substructure was not preserved")
        rows.append({
            "name": analysed["name"],
            "canonical_smiles": analysed["canonical_smiles"],
            "biowin3_delta": d3,
            "biowin4_delta": d4,
            "screening_direction": direction,
            "logp_delta": dlogp,
            "tpsa_delta_a2": dtpsa,
            "molecular_weight_delta_g_mol": dmw,
            "protected_substructures": preserved,
            "tradeoffs": tradeoffs or ["No major descriptor trade-off detected by this limited comparison"],
            "analysis": analysed,
        })
    return {
        "model_version": MODEL_VERSION,
        "original": original,
        "candidates": rows,
        "ranking_rule": "No single winner is asserted. Compare model direction, property trade-offs, protected structure and full fate evidence.",
        "warnings": [
            "Improved reconstructed BIOWIN scores do not demonstrate retained efficacy or experimental biodegradability.",
            "Every candidate must be reassessed for metabolites, mobility, ecotoxicity, human safety and synthetic feasibility.",
        ],
    }


def pathway_retention(parent_smiles: str, products: list[dict[str, Any]]) -> dict[str, Any]:
    parent = analyse_structure(parent_smiles, "Parent", include_svg=False)
    parent_mol = _mol(parent_smiles)
    parent_fragment_smarts = {
        row["description"]: row.get("smarts")
        for row in parent["biowin_screen"]["components"]
        if row.get("smarts")
    }
    parent_feature_keys = {feature["key"] for feature in parent["structure"]["features"]}
    rows = []
    retention_counts: dict[str, int] = {key: 0 for key in list(parent_fragment_smarts) + list(parent_feature_keys)}

    for product in products:
        analysed = analyse_structure(product["smiles"], product.get("name") or "Transformation product", include_svg=False)
        product_mol = _mol(product["smiles"])
        mcs = rdFMCS.FindMCS(
            [parent_mol, product_mol],
            timeout=3,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            bondCompare=rdFMCS.BondCompare.CompareAny,
        )
        retained_fragments = []
        for label, smarts in parent_fragment_smarts.items():
            query = Chem.MolFromSmarts(smarts)
            if query is not None and product_mol.HasSubstructMatch(query):
                retained_fragments.append(label)
                retention_counts[label] += 1
        product_features = {feature["key"] for feature in analysed["structure"]["features"]}
        retained_alerts = sorted(parent_feature_keys & product_features)
        for key in retained_alerts:
            retention_counts[key] += 1
        rows.append({
            "name": analysed["name"],
            "canonical_smiles": analysed["canonical_smiles"],
            "status": product.get("status", "predicted"),
            "matrix": product.get("matrix"),
            "source": product.get("source"),
            "dt50_days": product.get("dt50_days"),
            "mcs_smarts": mcs.smartsString,
            "parent_heavy_atom_fraction_retained": (mcs.numAtoms / parent_mol.GetNumHeavyAtoms()) if parent_mol.GetNumHeavyAtoms() else 0.0,
            "retained_biowin_fragments": retained_fragments,
            "retained_structure_alerts": retained_alerts,
            "analysis": analysed,
        })

    motif_summary = [
        {"motif": key, "products_retaining": count, "product_count": len(rows), "retention_fraction": count / len(rows) if rows else 0.0}
        for key, count in retention_counts.items() if count
    ]
    motif_summary.sort(key=lambda item: (item["products_retaining"], item["motif"]), reverse=True)
    return {
        "model_version": MODEL_VERSION,
        "parent": parent,
        "products": rows,
        "motif_retention_summary": motif_summary,
        "interpretation_rule": (
            "A motif repeatedly retained across observed or predicted products is a pathway-persistence hypothesis, "
            "not proof that the motif itself controls environmental persistence."
        ),
        "envipath_integration": {
            "status": ENVIPATH_MANIFEST["integration_status"],
            "commercial_warning": ENVIPATH_MANIFEST["commercial_warning"],
        },
    }
