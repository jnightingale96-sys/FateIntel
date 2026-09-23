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


def test_eu_pesticide_scenario_gets_birds_and_mammals_screen():
    # EU pesticide scenarios previously had no equivalent of the US
    # TERRPLANT/TREX/BEEREX terrestrial ecotox suite at all, despite EFSA
    # requiring the same bird/mammal dietary risk assessment.
    plan = build_assessment_plan({
        "jurisdiction": "EU",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
    })
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN" in keys


def test_us_pesticide_scenario_does_not_get_eu_birds_and_mammals_screen():
    plan = build_assessment_plan({
        "jurisdiction": "US",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
        "use_site_category": "outdoor_terrestrial",
    })
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN" not in keys


def test_eu_pesticide_bee_attractive_scenario_gets_bee_screen():
    plan = build_assessment_plan({
        "jurisdiction": "EU",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
        "bee_attractive": True,
    })
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BEES_SCREEN" in keys


def test_eu_pesticide_non_bee_attractive_scenario_does_not_get_bee_screen():
    plan = build_assessment_plan({
        "jurisdiction": "EU",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
        "bee_attractive": False,
    })
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BEES_SCREEN" not in keys


def test_au_pesticide_scenario_does_not_get_eu_bee_screen_even_when_bee_attractive():
    # APVMA's own bee methodology has not been researched -- AU must not
    # inherit the EU-sourced bee screen the way it inherits the birds/mammals
    # screen (which is a confirmed EFSA-2009-aligned methodology match).
    plan = build_assessment_plan({
        "jurisdiction": "AU",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
        "bee_attractive": True,
    })
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BEES_SCREEN" not in keys


def test_au_industrial_scenario_gets_aicis_pathway_and_native_models():
    # AICIS has no distinct proprietary exposure model -- this should route
    # to the same core PEC/PNEC method via native screens, not a fabricated
    # "AICIS adapter".
    plan = build_assessment_plan({
        "jurisdiction": "AU",
        "contaminant_group": "industrial_organic",
        "scenario": "industrial_effluent",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "AU_AICIS_INDUSTRIAL"
    keys = {x["key"] for x in plan["models"]}
    assert "SIMPLEBOX" in keys
    assert "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN" in keys
    # Nothing EU-FOCUS-specific or US-EPA-specific should appear for AU.
    assert not keys.intersection({"PEARL", "TOXSWA", "SWASH", "PWC", "PRZM", "TERRPLANT"})


def test_au_pesticide_scenario_gets_partial_apvma_pathway_not_mislabelled_as_aicis():
    # Pesticides in Australia are regulated by APVMA, not AICIS. APVMA's
    # terrestrial-vertebrates TER methodology is confirmed EFSA-2009-aligned
    # with the same triggers eu_birds_mammals.py already implements, so this
    # scenario should genuinely select that screen -- but the regulatory
    # programme must still name this as partial, not full APVMA coverage.
    plan = build_assessment_plan({
        "jurisdiction": "AU",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "AU_APVMA_PARTIAL"
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN" in keys
    assert not keys.intersection({"PEARL", "TOXSWA", "PWC", "PRZM"})


def test_au_veterinary_pharmaceutical_gets_partial_apvma_pathway_without_bird_mammal_screen():
    # APVMA also regulates veterinary medicines (same Environment Part 7
    # framework as pesticides), so this should get its own partial-coverage
    # key -- but the dietary bird/mammal TER screen is spray-residue-specific
    # and must NOT be selected for a manure/excreta-route veterinary product.
    plan = build_assessment_plan({
        "jurisdiction": "AU",
        "contaminant_group": "veterinary_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "AU_APVMA_VETERINARY_PARTIAL"
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN" not in keys


def test_au_human_pharmaceutical_has_no_tga_era_requirement():
    # Confirmed live (2026-09-18): the TGA has no environmental risk
    # assessment requirement for human medicines in Australia at all --
    # this is a genuinely confirmed absence, not an unresearched gap, so it
    # gets its own distinct key rather than reusing a "not mapped" pattern.
    plan = build_assessment_plan({
        "jurisdiction": "AU",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "AU_TGA_NO_ERA_REQUIREMENT"


def test_au_framework_is_registered():
    from app.services.registry import FRAMEWORKS
    keys = {f["key"] for f in FRAMEWORKS}
    assert "AU" in keys


def test_ca_industrial_scenario_gets_eccc_pathway_and_native_models():
    plan = build_assessment_plan({
        "jurisdiction": "CA",
        "contaminant_group": "industrial_organic",
        "scenario": "industrial_effluent",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "CA_ECCC_CEPA_INDUSTRIAL"
    keys = {x["key"] for x in plan["models"]}
    assert "SIMPLEBOX" in keys
    assert "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN" in keys
    assert not keys.intersection({"PEARL", "TOXSWA", "SWASH", "PWC", "PRZM", "TERRPLANT"})


def test_ca_pesticide_scenario_gets_partial_pmra_pathway_not_mislabelled_as_eccc():
    # Pesticides in Canada are regulated by the PMRA, not ECCC -- this must
    # not silently claim ECCC/CEPA coverage it doesn't have. PMRA's own
    # general RQ/LOC=1 framework and its confirmed bee LOC exception are
    # implemented (pmra_pesticides.py), but as a risk-characterisation
    # helper, not a MODELS registry entry -- no bird/mammal-style screen is
    # auto-selected here since PMRA's own exposure model isn't reused from
    # elsewhere the way APVMA's confirmed EFSA-2009 alignment was for AU.
    plan = build_assessment_plan({
        "jurisdiction": "CA",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "CA_PMRA_PARTIAL"
    keys = {x["key"] for x in plan["models"]}
    assert "ENVIROCHEM_EU_BIRDS_MAMMALS_SCREEN" not in keys
    assert not keys.intersection({"PEARL", "TOXSWA", "PWC", "PRZM"})


def test_ca_pharmaceutical_scenario_gets_partial_dsl_conditional_pathway():
    # A pharmaceutical active ingredient not already on Canada's Domestic
    # Substances List is reviewed under the same ECCC/CEPA New Substances
    # Notification pathway as industrial chemicals -- a real, if
    # conditional, pathway, not a bare "not mapped" gap.
    plan = build_assessment_plan({
        "jurisdiction": "CA",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "CA_HEALTH_CANADA_PARTIAL"


def test_ca_framework_is_registered():
    from app.services.registry import FRAMEWORKS
    keys = {f["key"] for f in FRAMEWORKS}
    assert "CA" in keys


def test_nz_industrial_scenario_gets_hsno_pathway_and_native_models():
    plan = build_assessment_plan({
        "jurisdiction": "NZ",
        "contaminant_group": "industrial_organic",
        "scenario": "industrial_effluent",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "NZ_EPA_HSNO"
    keys = {x["key"] for x in plan["models"]}
    assert "SIMPLEBOX" in keys
    assert "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN" in keys
    assert not keys.intersection({"PEARL", "TOXSWA", "SWASH", "PWC", "PRZM", "TERRPLANT"})


def test_nz_pesticide_scenario_gets_the_same_hsno_pathway_unlike_au_and_ca():
    # Unlike AU (AICIS/APVMA) and CA (ECCC/PMRA), NZ regulates industrial
    # chemicals and pesticides under the SAME Act and regulator -- this
    # must genuinely route to NZ_EPA_HSNO, not an "unmapped" placeholder.
    plan = build_assessment_plan({
        "jurisdiction": "NZ",
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "NZ_EPA_HSNO"


def test_nz_human_pharmaceutical_is_honestly_unmapped():
    # Human medicines are explicitly excluded from HSNO by the Act itself.
    plan = build_assessment_plan({
        "jurisdiction": "NZ",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "municipal_wastewater",
        "tier": 2,
    })
    assert plan["regulatory_programme"]["key"] == "NZ_MOH_NOT_MAPPED"


def test_nz_framework_is_registered():
    from app.services.registry import FRAMEWORKS
    keys = {f["key"] for f in FRAMEWORKS}
    assert "NZ" in keys


def test_every_contaminant_group_has_a_taxonomy_entry():
    from app.services.registry import CONTAMINANT_GROUPS, CONTAMINANT_TAXONOMY
    assert set(CONTAMINANT_GROUPS) == set(CONTAMINANT_TAXONOMY)


def test_radionuclide_and_mixture_are_hard_blocked_in_every_jurisdiction():
    from app.services.registry import FRAMEWORKS
    for framework in FRAMEWORKS:
        for group in ("radionuclide", "contaminated_mixture"):
            plan = build_assessment_plan({
                "jurisdiction": framework["key"],
                "contaminant_group": group,
                "scenario": "municipal_wastewater",
                "tier": 2,
            })
            assert plan["models"] == []
            assert plan["regulatory_programme"]["key"] == "NOT_YET_IMPLEMENTED"
            assert plan["warnings"]


def test_radionuclide_warning_names_the_external_route():
    plan = build_assessment_plan({
        "jurisdiction": "UK", "contaminant_group": "radionuclide",
        "scenario": "soil_incorporation", "tier": 1,
    })
    assert "EXTERNAL MODEL REQUIRED" in plan["warnings"][0]


def test_legacy_organics_keep_native_screening_with_an_honest_scope_warning():
    for group in ("pah", "legacy_pop_organic", "organotin"):
        plan = build_assessment_plan({
            "jurisdiction": "EU", "contaminant_group": group,
            "scenario": "industrial_effluent", "tier": 2,
        })
        keys = [x["key"] for x in plan["models"]]
        assert "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN" in keys
        assert any("SCREENING / COMPARATIVE USE" in w for w in plan["warnings"])


def test_metal_is_still_kept_out_of_organic_only_models():
    plan = build_assessment_plan({
        "jurisdiction": "EU", "contaminant_group": "metal_inorganic",
        "scenario": "industrial_effluent", "tier": 2,
    })
    keys = [x["key"] for x in plan["models"]]
    assert "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN" not in keys
    assert "ENVIROCHEM_CATCHMENT_RIVER_NETWORK" not in keys
