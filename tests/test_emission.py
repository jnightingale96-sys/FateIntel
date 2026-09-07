import pytest
from app.services.emission import run_pharmaceutical_emission


def base_payload():
    return {
        "scenario_name": "test",
        "emission_mode": "screening_spc",
        "parent_name": "Parent",
        "parent_molecular_weight_g_mol": 200.0,
        "product_name": "Product",
        "formulation": "tablet",
        "administration_route": "oral",
        "spc_title": "Official SPC",
        "spc_identifier": "SPC-1",
        "spc_url": None,
        "spc_access_date": "2026-07-30",
        "spc_source_type": "official_regulatory",
        "consumption_source_title": "OECD",
        "consumption_source_identifier": "OECD-1",
        "therapeutic_class_ddd_per_1000_day": 1.0,
        "dose_per_administration": 1.0,
        "dose_unit": "g",
        "administrations_per_day": 1.0,
        "refined_annual_active_kg": None,
        "emitting_days_per_year": 365,
        "population": 1000,
        "wastewater_l_person_day": 200.0,
        "direct_to_sewer_fraction": 0.0,
        "systemic_fraction": 1.0,
        "parent_urine_fraction": 0.4,
        "parent_faeces_fraction": 0.1,
        "metabolites": [],
    }


def test_parent_excretion_applied_before_wwtp():
    r = run_pharmaceutical_emission(base_payload())
    parent = r["species"][0]
    assert parent["mass_g_day"] == pytest.approx(0.5)
    assert parent["influent_concentration_ug_l"] == pytest.approx(2.5)
    assert r["wastewater_flow_m3_day"] == pytest.approx(200.0)


def test_population_and_flow_scale_together():
    a = base_payload()
    b = base_payload()
    b["population"] = 10000
    ra = run_pharmaceutical_emission(a)
    rb = run_pharmaceutical_emission(b)
    assert rb["species"][0]["mass_g_day"] == pytest.approx(ra["species"][0]["mass_g_day"] * 10)
    assert rb["wastewater_flow_m3_day"] == pytest.approx(ra["wastewater_flow_m3_day"] * 10)
    assert rb["species"][0]["influent_concentration_ug_l"] == pytest.approx(ra["species"][0]["influent_concentration_ug_l"])


def test_metabolite_mass_uses_moles_and_metabolite_mw():
    p = base_payload()
    p["parent_urine_fraction"] = 0.0
    p["parent_faeces_fraction"] = 0.0
    p["metabolites"] = [{
        "species_key": "m1",
        "name": "Metabolite",
        "molecular_weight_g_mol": 100.0,
        "molar_fraction": 0.2,
        "source_title": "Study",
        "source_identifier": "DOI",
        "evidence_type": "measured",
    }]
    r = run_pharmaceutical_emission(p)
    metabolite = r["species"][1]
    # 1 g / 200 g/mol = 0.005 mol; 20% = 0.001 mol; ×100 g/mol = 0.1 g
    assert metabolite["mass_g_day"] == pytest.approx(0.1)


def test_fraction_overallocation_rejected():
    p = base_payload()
    p["parent_urine_fraction"] = 0.8
    p["parent_faeces_fraction"] = 0.3
    with pytest.raises(ValueError):
        run_pharmaceutical_emission(p)


def test_ten_kg_year_example_is_micrograms_not_milligrams_per_litre():
    p = base_payload()
    p.update({
        "emission_mode": "refined_annual_use",
        "refined_annual_active_kg": 10.0,
        "population": 100000,
        "wastewater_l_person_day": 200.0,
        "parent_molecular_weight_g_mol": 236.27,
        "parent_urine_fraction": 0.51,
        "parent_faeces_fraction": 0.0,
    })
    r = run_pharmaceutical_emission(p)
    parent = r["species"][0]
    assert parent["mass_kg_day"] == pytest.approx(5.1 / 365.0)
    assert parent["influent_concentration_ug_l"] == pytest.approx(0.6986301369863014)
