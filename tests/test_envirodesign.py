import pytest

from app.services.envirodesign import RDKIT_AVAILABLE, analyse_structure, compare_candidates, manifest, pathway_retention


CARBAMAZEPINE = "NC(=O)N1c2ccccc2C=Cc2ccccc21"

native_rdkit = pytest.mark.skipif(not RDKIT_AVAILABLE, reason="optional native RDKit backend disabled/unavailable; browser/WASM is primary")


def test_manifest_contains_reconstructed_fragment_inventory():
    data = manifest()
    assert data["biowin"]["fragment_count"] == 41
    assert data["envipath"]["integration_status"] == "manual_import_and_adapter_contract_only"
    assert "not EPA source code" in data["biowin"]["source_status"]


@native_rdkit
def test_carbamazepine_identity_and_attribution_are_consistent():
    result = analyse_structure(CARBAMAZEPINE, "Carbamazepine")
    assert result["structure"]["molecular_formula"] == "C15H12N2O"
    assert result["structure"]["molecular_weight_g_mol"] == pytest.approx(236.274, rel=1e-5)
    assert result["biowin_screen"]["biowin3_ultimate_score"] == pytest.approx(2.70147568562)
    assert result["biowin_screen"]["biowin4_primary_score"] == pytest.approx(3.550131268856)
    keys = {row["key"] for row in result["structure"]["features"]}
    assert "carboxamide" in keys
    assert "polycyclic_aromatic_scaffold" in keys
    assert "tertiary_amine" not in keys  # the ring amide N must not be mislabelled as a basic amine
    assert "<svg" in result["structure_svg"]


@native_rdkit
def test_exact_aromatic_chloride_fragment_is_explainable():
    result = analyse_structure("Clc1ccccc1", "Chlorobenzene", include_svg=False)
    rows = result["biowin_screen"]["components"]
    chloride = next(row for row in rows if row["description"] == "Aromatic chloride [-Cl]")
    assert chloride["count"] == 1
    assert chloride["biowin3_contribution"] == pytest.approx(-0.20660)
    assert chloride["biowin4_contribution"] == pytest.approx(-0.16534)


@native_rdkit
def test_candidate_comparison_checks_protected_substructure_without_asserting_winner():
    result = compare_candidates(
        CARBAMAZEPINE,
        [{"name": "Hydrogenated analogue", "smiles": "NC(=O)N1c2ccccc2CCc2ccccc21"}],
        ["C(=O)N"],
    )
    row = result["candidates"][0]
    assert row["protected_substructures"][0]["preserved"] is True
    assert row["screening_direction"] in {
        "higher_in_both_screening_models",
        "lower_in_both_screening_models",
        "mixed_primary_vs_ultimate_direction",
    }
    assert result["ranking_rule"].startswith("No single winner")


@native_rdkit
def test_pathway_retention_keeps_matrix_and_status():
    result = pathway_retention(
        CARBAMAZEPINE,
        [{
            "name": "Hypothetical reduced product",
            "smiles": "NC(=O)N1c2ccccc2CCc2ccccc21",
            "status": "predicted",
            "matrix": "activated sludge",
            "source": "manual test",
        }],
    )
    product = result["products"][0]
    assert product["status"] == "predicted"
    assert product["matrix"] == "activated sludge"
    assert 0 < product["parent_heavy_atom_fraction_retained"] <= 1
    assert result["envipath_integration"]["status"] == "manual_import_and_adapter_contract_only"
