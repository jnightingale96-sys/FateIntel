from app.services.plant_uptake import briggs_tscf, run_plant_uptake_screen


def test_briggs_peak_near_logkow_1_78():
    assert abs(briggs_tscf(1.78) - 0.784) < 1e-12


def test_neutral_plant_screen_positive_outputs():
    out = run_plant_uptake_screen({
        "model_mode":"briggs_neutral", "ionisation_class":"neutral",
        "soil_concentration_mg_kg_dw":0.01, "kd_l_kg":5, "volumetric_water_content_l_l":0.25,
        "soil_bulk_density_kg_m3":1350, "log_kow":2.45, "user_tscf":None,
        "transpiration_l_plant_day":1.5, "harvest_interval_days":90, "plant_loss_dt50_days":None,
        "root_allocation_fraction":0.2, "shoot_allocation_fraction":0.5, "edible_allocation_fraction":0.3,
        "root_fresh_mass_kg":0.5, "shoot_fresh_mass_kg":3, "edible_fresh_mass_kg":0.5,
        "root_bcf_kg_kg":None, "shoot_bcf_kg_kg":None, "edible_bcf_kg_kg":None,
    })
    assert 0 < out["tscf"] < 1
    assert out["edible_tissue_concentration_mg_kg_fw"] > 0
    assert "held constant over the harvest interval" in out["warnings"][0]
    assert any("not a regulatory crop-residue study" in warning for warning in out["warnings"])
