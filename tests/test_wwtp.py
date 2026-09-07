from app.services.wwtp import run_wwtp

def test_mass_balance_and_risk():
    r = run_wwtp({
        "annual_use_kg":10,
        "release_fraction":0.1,
        "emitting_days_per_year":365,
        "wastewater_flow_m3_day":10000,
        "biodegradation_fraction":0.2,
        "sorption_fraction":0.1,
        "volatilisation_fraction":0.0,
        "receiving_water_dilution_factor":10,
        "sludge_to_soil_fraction":0.1,
        "mixed_soil_mass_kg":2_000_000,
        "aquatic_pnec_ug_l":0.1,
        "soil_pnec_ug_kg":100,
    })
    assert abs(r["mass_balance_closure_fraction"] - 1.0) < 1e-12
    assert r["aquatic_rq"] is not None
    assert r["soil_rq"] is not None
