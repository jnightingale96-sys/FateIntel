import math
from app.services.sorption import (
    franco_trapp, li_neutral, ecetoc_base_workbook, droge_goss_cation, run_sorption_model
)

def test_acid_matches_supplied_workbook():
    r = franco_trapp("acid", 2.28, 13.94, 7.2, 0.01, 0.016)
    assert math.isclose(r["koc_l_kg"], 220.90214562591845, rel_tol=1e-12)

def test_neutral_workbook_literal_matches_cells_e3_f3():
    r = li_neutral(2.28, 0.016, "workbook_literal")
    assert math.isclose(r["koc_l_kg"], 171.6485018866575, rel_tol=1e-12)

def test_neutral_publication_variant_uses_actual_toc():
    r = li_neutral(2.28, 0.016, "publication")
    assert math.isclose(r["koc_l_kg"], 151.5653816226443, rel_tol=1e-12)

def test_base_ecetoc_matches_cells_g3_h3():
    r = ecetoc_base_workbook(2.28, 0.016)
    assert math.isclose(r["koc_l_kg"], 3067.6089769179366, rel_tol=1e-12)

def test_auto_classification():
    assert run_sorption_model({
        "mode":"auto", "log_kow":2.28, "pkaa":4.5, "pkab":None,
        "soil_ph":7.2, "organic_carbon_fraction":0.016,
        "ionic_strength_mol_l":0.01
    })["ionisation_class"] == "acid"


def test_neutral_run_defaults_to_exact_workbook_variant():
    r = run_sorption_model({
        "mode":"neutral", "log_kow":2.28, "pkaa":None, "pkab":None,
        "soil_ph":7.2, "organic_carbon_fraction":0.016,
        "ionic_strength_mol_l":0.01
    })
    assert r["selected"]["model_key"] == "LI_NEUTRAL_WORKBOOK_LITERAL"
    assert math.isclose(r["selected"]["koc_l_kg"], 171.6485018866575, rel_tol=1e-12)

def test_neutral_run_can_select_publication_variant():
    r = run_sorption_model({
        "mode":"neutral", "neutral_variant":"publication", "log_kow":2.28,
        "pkaa":None, "pkab":None, "soil_ph":7.2,
        "organic_carbon_fraction":0.016, "ionic_strength_mol_l":0.01
    })
    assert r["selected"]["model_key"] == "LI_NEUTRAL_PUBLICATION"


def test_droge_goss_atenolol_matches_supplied_workbook():
    r = droge_goss_cation({
        "organic_carbon_fraction": 0.0164,
        "cec_total_mol_c_kg": 0.43,
        "molecular_formula": "C14H22N2O3",
        "bond_count": 40,
        "ring_count": 0,
        "n_h_attached_to_cationic_n": 2,
        "oh_groups": 1,
        "nh2_groups": 1,
        "ether_groups": 1,
        "ester_groups": 0,
        "ketone_groups": 0,
        "amide_groups": 0,
        "single_ring_charged_pyridines": 0,
        "chloro_groups": 0,
        "carboxamide_groups": 1,
        "multi_ring_charged_n": 0,
        "electrolyte_system": "5 mM CaCl2",
    })
    assert math.isclose(r["kd_l_kg"], 91.95990999034083, rel_tol=1e-12)


def test_droge_goss_bisoprolol_matches_supplied_workbook():
    r = droge_goss_cation({
        "organic_carbon_fraction": 0.0164,
        "cec_total_mol_c_kg": 0.43,
        "molecular_formula": "C18H31NO4",
        "bond_count": 53,
        "ring_count": 0,
        "n_h_attached_to_cationic_n": 2,
        "oh_groups": 1,
        "nh2_groups": 0,
        "ether_groups": 3,
        "ester_groups": 0,
        "ketone_groups": 0,
        "amide_groups": 0,
        "single_ring_charged_pyridines": 0,
        "chloro_groups": 0,
        "carboxamide_groups": 0,
        "multi_ring_charged_n": 0,
        "electrolyte_system": "5 mM CaCl2",
    })
    assert math.isclose(r["kd_l_kg"], 156.84524965285158, rel_tol=1e-12)


def test_base_defaults_to_droge_goss_and_keeps_ecetoc_comparison():
    r = run_sorption_model({
        "mode": "base", "log_kow": 0.16, "pkab": 9.6, "pkaa": None,
        "soil_ph": 7.2, "organic_carbon_fraction": 0.0164,
        "ionic_strength_mol_l": 0.01, "cec_total_mol_c_kg": 0.43,
        "molecular_formula": "C14H22N2O3", "bond_count": 40,
        "n_h_attached_to_cationic_n": 2, "oh_groups": 1, "nh2_groups": 1,
        "ether_groups": 1, "carboxamide_groups": 1,
    })
    assert r["selected"]["model_key"] == "DROGE_GOSS_CATION_WORKBOOK"
    assert any(x["model_key"] == "ECETOC_BASE_WORKBOOK" for x in r["comparisons"])


def test_droge_goss_rejects_manual_formula_atom_conflict():
    import pytest
    with pytest.raises(ValueError, match="Manual atom counts conflict"):
        droge_goss_cation({
            "organic_carbon_fraction": 0.0164,
            "cec_total_mol_c_kg": 0.43,
            "molecular_formula": "C13H21NO3",
            "atom_c": 18,
            "ring_count": 1,
            "n_h_attached_to_cationic_n": 0,
        })


def test_droge_goss_calls_do_not_shift_functional_groups_between_compounds():
    common = {
        "organic_carbon_fraction": 0.0164, "cec_total_mol_c_kg": 0.43,
        "molecular_formula": "C20H23N", "bond_count": 44, "ring_count": 3,
        "n_h_attached_to_cationic_n": 0,
    }
    first = droge_goss_cation({**common, "oh_groups": 0, "amide_groups": 0})
    _ = droge_goss_cation({**common, "oh_groups": 3, "amide_groups": 2})
    repeated = droge_goss_cation({**common, "oh_groups": 0, "amide_groups": 0})
    assert math.isclose(first["kd_l_kg"], repeated["kd_l_kg"], rel_tol=1e-15)
