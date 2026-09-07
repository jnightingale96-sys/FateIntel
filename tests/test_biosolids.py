from app.services.biosolids import run_biosolids_land_application


def test_biosolids_mass_balance_and_accumulation():
    out = run_biosolids_land_application({
        "source_mode":"wwtp_chemical_mass", "chemical_mass_to_sludge_kg_day":0.01,
        "biosolids_dry_solids_kg_day":1000, "biosolids_concentration_mg_kg_dw":None,
        "biosolids_application_t_dw_ha_year":None, "operating_days_per_year":365,
        "fraction_sludge_land_applied":1, "land_application_area_ha":100,
        "storage_days":0, "storage_dt50_days":None, "soil_mixing_depth_m":0.2,
        "soil_bulk_density_kg_m3":1500, "soil_dt50_days":40, "assessment_years":10,
        "runoff_fraction":0, "leaching_fraction":0,
    })
    assert out["annual_chemical_mass_land_applied_kg"] == 3.65
    assert out["single_application_increment_mg_kg"] > 0
    assert out["final_post_application_mg_kg"] >= out["single_application_increment_mg_kg"]
    assert len(out["annual_series"]) == 10


def test_biosolids_concentration_mode():
    out = run_biosolids_land_application({
        "source_mode":"biosolids_concentration", "chemical_mass_to_sludge_kg_day":None,
        "biosolids_dry_solids_kg_day":None, "biosolids_concentration_mg_kg_dw":10,
        "biosolids_application_t_dw_ha_year":5, "operating_days_per_year":365,
        "fraction_sludge_land_applied":1, "land_application_area_ha":1,
        "storage_days":0, "storage_dt50_days":None, "soil_mixing_depth_m":0.2,
        "soil_bulk_density_kg_m3":1500, "soil_dt50_days":None, "assessment_years":1,
        "runoff_fraction":0, "leaching_fraction":0,
    })
    assert abs(out["annual_chemical_loading_kg_ha"] - 0.05) < 1e-12
