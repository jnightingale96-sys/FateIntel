import math

from app.services.veterinary import (
    animal_profiles,
    biowin_manure_dt50_hours,
    correct_dt50_temperature,
    phase_i_decision,
    run_veterinary_assessment,
)


def base_intensive(**overrides):
    payload = {
        "chemical_name": "Test active",
        "animal_profile_key": "fattening_pig",
        "dose_value": 1.0,
        "dose_unit": "mg_per_kg_bw_day",
        "treatment_duration_days": 5.0,
        "fraction_treated": 0.5,
        "treatment_events_per_year": 1.0,
        "excreted_fraction": 0.30,
        "faecal_excretion_fraction": 0.30,
        "parasiticide": False,
        "body_weight_kg": 65.0,
        "turnover_per_year": 3.0,
        "nitrogen_kg_place_year": 7.5,
        "housing_factor": 1.0,
        "nitrogen_spreading_limit_kg_ha": 170.0,
        "soil_bulk_density_kg_m3": 1500.0,
        "soil_depth_m": 0.05,
        "manure_storage_days": 91.0,
        "storage_time_basis": "mean_age_half_duration",
        "biowin4_value": 3.3,
        "source_temperature_c": 25.0,
        "target_temperature_c": 10.0,
        "temperature_factor_theta": 1.047,
        "receiving_water_dilution_factor": 10.0,
        "direct_water_release_fraction": 0.0,
        "uneaten_feed_fraction": 0.0,
    }
    payload.update(overrides)
    return payload


def test_animal_library_covers_all_major_management_groups():
    rows = animal_profiles()
    groups = {row["group"] for row in rows}
    assert len(rows) >= 60
    assert {"Pigs", "Poultry", "Cattle", "Companion animals", "Aquaculture finfish", "Managed invertebrates", "Zoo and exotic animals"} <= groups


def test_official_defaults_are_not_invented_for_every_species():
    rows = {row["key"]: row for row in animal_profiles()}
    assert rows["fattening_pig"]["official_default"] is True
    assert rows["dog"]["official_default"] is False
    assert rows["dog"]["custom_required"] is True
    assert "body_weight_kg" not in rows["dog"]


def test_cold_temperature_lengthens_half_life():
    corrected = correct_dt50_temperature(42.23, 25.0, 10.0, 1.047)
    assert corrected > 42.23
    assert math.isclose(corrected, 42.23 * 1.047**15, rel_tol=1e-12)


def test_outlier_biowin_compatibility_equation():
    assert math.isclose(biowin_manure_dt50_hours(3.3744), 10 ** (6 - 3.3744) / 10, rel_tol=1e-12)


def test_phase_i_companion_animal_stops_without_specific_concern():
    result = phase_i_decision({"animal_profile_key": "dog"})
    assert result["outcome"] == "phase_i_stop"
    assert "Non-food" in result["reason"]


def test_phase_i_pasture_parasiticide_advances_to_phase_ii():
    result = phase_i_decision({"animal_profile_key": "sheep_pasture", "parasiticide": True})
    assert result["outcome"] == "phase_ii"
    assert "dung-fauna" in result["reason"]


def test_fattening_pig_initial_pec_matches_registered_equation():
    result = run_veterinary_assessment(base_intensive())
    expected = ((1 * 5 * 65 * 3 * 0.5 * 170) / (1500 * 10000 * 0.05 * 7.5 * 1)) * 1000
    assert math.isclose(result["calculations"]["pecs"]["soil_initial_ug_kg"], expected, rel_tol=1e-12)


def test_mean_storage_age_is_half_of_storage_duration():
    result = run_veterinary_assessment(base_intensive())
    assert result["calculations"]["mass_balance"]["effective_storage_days"] == 45.5
    assert result["normalised_inputs"]["manure_dt50_target_days"] > 0


def test_legacy_ld50_quotient_is_not_labelled_regulatory_rq():
    result = run_veterinary_assessment(base_intensive(earthworm_ld50_ug_kg=1000.0))
    assert result["outlier_earthworm_ld50_prioritisation_quotient"] is not None
    assert result["regulatory_rq"]["soil"] is None
    assert any("not the VICH regulatory RQ" in warning for warning in result["warnings"])


def test_aquaculture_calculates_total_residue_water_and_sediment():
    result = run_veterinary_assessment({
        **base_intensive(),
        "animal_profile_key": "salmon_net_pen",
        "dose_value": 10.0,
        "dose_unit": "mg_per_kg_bw_day",
        "treatment_duration_days": 3.0,
        "body_weight_kg": 1.0,
        "manure_storage_days": 0.0,
        "biowin4_value": None,
        "treated_biomass_kg": 1000.0,
        "facility_water_volume_l": 1_000_000.0,
        "direct_water_release_fraction": 0.1,
        "uneaten_feed_fraction": 0.05,
        "receiving_water_dilution_factor": 10.0,
        "sediment_area_m2": 1000.0,
        "sediment_depth_m": 0.05,
        "sediment_density_kg_m3": 1300.0,
    })
    pecs = result["calculations"]["pecs"]
    assert pecs["surface_water_initial_ug_l"] > 0
    assert pecs["surface_water_refined_ug_l"] > 0
    assert pecs["sediment_ug_kg"] > 0


def test_manure_dt50_does_not_trigger_soil_persistence_flag():
    result = run_veterinary_assessment(base_intensive(soil_dt50_days=None, soil_accumulation_years=1))
    assert result["normalised_inputs"]["persistence_flag_soil_dt90_over_1_year"] is False
    assert result["normalised_inputs"]["manure_dt50_target_days"] is not None


def test_soil_dt90_over_one_year_triggers_and_accumulates():
    result = run_veterinary_assessment(base_intensive(soil_dt50_days=200.0, soil_accumulation_years=10))
    assert result["normalised_inputs"]["soil_dt90_days"] > 365
    assert result["normalised_inputs"]["persistence_flag_soil_dt90_over_1_year"] is True
    accumulation = result["calculations"]["soil_accumulation"]
    assert accumulation["final_post_application_ug_kg"] > accumulation["annual_increment_ug_kg"]
    assert any("Soil DT90 exceeds 1 year" in warning for warning in result["warnings"])


def test_intensive_refinement_retains_turnover_and_events():
    result = run_veterinary_assessment(base_intensive(treatment_events_per_year=2, excreted_fraction=1.0, manure_storage_days=0, biowin4_value=None, soil_accumulation_years=1))
    mb = result["calculations"]["mass_balance"]
    expected_mass = 1.0 * 5.0 * 65.0 * 3.0 * 0.5 * 2.0
    assert math.isclose(mb["annual_administered_mass_mg_per_place"], expected_mass, rel_tol=1e-12)
    assert math.isclose(result["calculations"]["pecs"]["soil_initial_ug_kg"], result["calculations"]["pecs"]["soil_refined_ug_kg"], rel_tol=1e-12)
