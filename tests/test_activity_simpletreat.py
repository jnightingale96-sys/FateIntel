import pytest
from app.services.wwtp import run_activity_simpletreat, WORKBOOK_9BOX_CARBAMAZEPINE_FRACTIONS


def payload():
    return {
        "influent_mass_kg_day": 0.001,
        "wastewater_flow_m3_day": 200.0,
        "model_mode": "supplied_workbook_9box_preset",
        "biodegradation_fraction": 0.0,
        "primary_sludge_fraction": 0.0,
        "secondary_sludge_fraction": 0.0,
        "volatilisation_fraction": 0.0,
        "post_wwtp_biodegradation_fraction": 0.0,
        "receiving_water_dilution_factor": 10.0,
        "sludge_to_soil_fraction": 0.1,
        "mixed_soil_mass_kg": 2_000_000.0,
        "emitting_days_per_year": 365,
        "aquatic_pnec_ug_l": 1.0,
        "soil_pnec_ug_kg": 100.0,
        "species_key": "parent",
        "species_name": "Carbamazepine",
    }


def test_workbook_9box_fractions_close_and_use_917187_percent_effluent():
    assert sum(WORKBOOK_9BOX_CARBAMAZEPINE_FRACTIONS.values()) == pytest.approx(1.0)
    r = run_activity_simpletreat(payload())
    assert r["pathway_fractions"]["effluent"] == pytest.approx(0.9171874114453539)
    assert r["mass_balance_closure_fraction"] == pytest.approx(1.0)


def test_post_wwtp_biodegradation_before_dilution():
    p = payload()
    p["post_wwtp_biodegradation_fraction"] = 0.5
    r = run_activity_simpletreat(p)
    expected = r["effluent_concentration_ug_l"] * 0.5 / 10
    assert r["surface_water_pec_ug_l"] == pytest.approx(expected)


def test_workbook_preset_rejects_non_carbamazepine_identity():
    p = payload()
    p.update({
        "chemical_name": "Diclofenac",
        "chemical_cas_number": "15307-86-5",
        "chemical_inchikey": "DCOPUUMXTXDBNB-UHFFFAOYSA-N",
    })
    with pytest.raises(ValueError, match="Carbamazepine-parent verification fixture only"):
        run_activity_simpletreat(p)


def test_workbook_preset_rejects_carbamazepine_metabolite():
    p = payload()
    p["species_key"] = "carbamazepine-10-11-epoxide"
    with pytest.raises(ValueError, match="Carbamazepine-parent verification fixture only"):
        run_activity_simpletreat(p)
