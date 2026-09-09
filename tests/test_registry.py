from app.services.registry import build_assessment_plan


def test_uk_pharmaceutical_wastewater_plan():
    plan = build_assessment_plan({
        "jurisdiction": "UK",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 2,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "SIMPLETREAT" in keys
    assert "ACTIVITY_SIMPLETREAT" in keys
    assert "ENVIROCHEM_CATCHMENT_RIVER_NETWORK" in keys


def test_uk_pharmaceutical_high_tier_adds_spatial_river_models():
    plan = build_assessment_plan({
        "jurisdiction": "UK",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 3,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "GREATER" in keys
    assert "EPIE" in keys


def test_us_pesticide_refined_plan():
    plan = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 3,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "PWC" in keys
    assert "PRZM" in keys
    assert "EXAMS" not in keys


def test_us_industrial_plan_has_native_screen_and_chemsteer_contract():
    plan = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "industrial_organic",
        "scenario": "industrial_effluent",
        "tier": 2,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN" in keys
    assert "CHEMSTEER" in keys
    assert "CEM" not in keys


def test_us_consumer_and_disposal_routing_is_explicit():
    consumer = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "detergent_cleaner",
        "scenario": "household_use",
        "tier": 2,
    })
    disposal = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "industrial_organic",
        "scenario": "product_disposal",
        "tier": 2,
    })
    assert {"CEM", "EFAST"}.issubset({x["key"] for x in consumer["models"]})
    assert "EFAST" in {x["key"] for x in disposal["models"]}


def test_focus_dependency_and_macro_order_for_refined_eu_pesticide():
    plan = build_assessment_plan({
        "jurisdiction": "EU",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 3,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "SPIN" in keys and "MACRO" in keys and "SWASH" in keys and "TOXSWA" in keys
    assert keys.index("SPIN") < keys.index("MACRO")
    assert keys.index("SPIN") < keys.index("SWASH")


def test_industrial_discharge_adds_multimedia_refinement():
    plan = build_assessment_plan({
        "jurisdiction": "EU",
        "contaminant_group": "industrial_organic",
        "scenario": "industrial_effluent",
        "tier": 2,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "ENVIROCHEM_CATCHMENT_RIVER_NETWORK" in keys
    assert "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN" in keys
    assert "SIMPLEBOX" in keys
    assert "SWASH" not in keys
    assert "TOXSWA" not in keys


def test_nonstandard_group_warns():
    plan = build_assessment_plan({
        "jurisdiction": "EU",
        "contaminant_group": "metal_inorganic",
        "scenario": "soil_incorporation",
        "tier": 2,
    })
    assert plan["warnings"]


def test_us_pharmaceutical_soil_scenarios_get_a_leaching_model():
    # Previously the US branch had no soil/groundwater-leaching model at all
    # for pharmaceutical biosolids/irrigation scenarios, while the equivalent
    # EU scenario gets PEARL/PELMO/MACRO -- a real coverage gap, not an
    # intentional jurisdiction difference. PRZM is EPA's real root-zone
    # transport tool and is not a full groundwater fate model like PEARL, so
    # its leaching-only scope must be disclosed via a warning, not presented
    # as equivalent.
    for scenario in ("biosolids_to_soil", "wastewater_irrigation"):
        for group in ("human_pharmaceutical", "veterinary_pharmaceutical"):
            plan = build_assessment_plan({
                "jurisdiction": "US",
                "contaminant_group": group,
                "scenario": scenario,
                "tier": 2,
            })
            applicable_keys = {x["key"] for x in plan["models"] if x["applicable"]}
            assert "PRZM" in applicable_keys, (scenario, group)
            assert any("not a full groundwater fate model" in w for w in plan["warnings"])


def test_native_water_sediment_screen_is_not_gated_to_eu():
    # ENVIROCHEM_TOXSWA_PROCESS_SCREEN declares EU/UK/US/CH applicability in
    # its own MODELS entry; the selection logic previously excluded US anyway
    # with no stated reason.
    us_plan = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 2,
    })
    assert "ENVIROCHEM_TOXSWA_PROCESS_SCREEN" in {x["key"] for x in us_plan["models"]}


def test_us_soil_incorporated_pesticide_gets_terrestrial_ecotox_models():
    # "Direct to soil" (soil_incorporation) previously selected only PWC in
    # the US -- none of TerrPlant/T-REX, which "Agricultural spray" gets
    # automatically, even though a soil-incorporated pesticide use triggers
    # the same terrestrial/avian/mammalian exposure pathway.
    plan = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "pesticide",
        "scenario": "soil_incorporation",
        "tier": 2,
        "use_site_category": "outdoor_terrestrial",
    })
    keys = {x["key"] for x in plan["models"]}
    assert {"TERRPLANT", "TREX"}.issubset(keys)
