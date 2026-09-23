"""Tests for the formal PBT/vPvB (REACH Annex XIII) and PMT/vPvM (CLP 2023/707) classifier."""

from __future__ import annotations

import pytest

from app.services.pathway_plausibility import (
    BCF_B_THRESHOLD_L_PER_KG,
    BCF_VB_THRESHOLD_L_PER_KG,
    LOG_KOC_M_THRESHOLD,
    LOG_KOC_VM_THRESHOLD,
)
from app.services.pbt_pmt_classifier import (
    INCONCLUSIVE,
    MET,
    MISSING,
    NOT_MET,
    ClassifierInputError,
    classify_pbt_and_vpvb,
    classify_pmt_and_vpvm,
)


# ---------------------------------------------------------------------------
# PBT / vPvB
# ---------------------------------------------------------------------------


def test_pbt_met_when_p_b_and_t_all_met():
    result = classify_pbt_and_vpvb(
        half_life_days={"soil": 150},  # > 120 day P threshold
        bcf_l_per_kg=3000,  # > 2,000 B threshold, not > 5,000 vB threshold
        noec_or_ec10_mg_l=0.005,  # < 0.01 T threshold
    )
    assert result["persistence"]["outcome"] == MET
    assert result["bioaccumulation"]["outcome"] == MET
    assert result["toxicity"]["outcome"] == MET
    assert result["pbt"] == MET
    # vPvB is inconclusive: only 1 of 5 compartments supplied for vP, and BCF doesn't clear the vB bar.
    assert result["very_bioaccumulation"]["outcome"] == INCONCLUSIVE
    assert result["vpvb"] == INCONCLUSIVE


def test_vpvb_met_when_all_compartments_exceed_vp_and_bcf_exceeds_vb():
    result = classify_pbt_and_vpvb(
        half_life_days={
            "marine_water": 70, "freshwater_or_estuarine_water": 70,
            "marine_sediment": 200, "freshwater_or_estuarine_sediment": 200, "soil": 200,
        },
        bcf_l_per_kg=6000,  # > 5,000 vB threshold
    )
    assert result["very_persistence"]["outcome"] == MET
    assert result["very_bioaccumulation"]["outcome"] == MET
    assert result["vpvb"] == MET
    # PBT itself is MISSING, not MET: no toxicity data supplied at all.
    assert result["persistence"]["outcome"] == MET  # marine_water 70 > 60 P threshold too
    assert result["toxicity"]["outcome"] == MISSING
    assert result["pbt"] == MISSING


def test_pbt_not_met_when_every_compartment_is_measured_and_none_exceed_the_p_threshold():
    result = classify_pbt_and_vpvb(
        half_life_days={
            "marine_water": 10, "freshwater_or_estuarine_water": 10,
            "marine_sediment": 50, "freshwater_or_estuarine_sediment": 50, "soil": 50,
        },
    )
    assert result["persistence"]["outcome"] == NOT_MET
    # A conclusive NOT_MET on P settles the whole PBT determination even though B and T are unknown.
    assert result["bioaccumulation"]["outcome"] == MISSING
    assert result["toxicity"]["outcome"] == MISSING
    assert result["pbt"] == NOT_MET


def test_persistence_partial_data_is_inconclusive_not_not_met():
    result = classify_pbt_and_vpvb(half_life_days={"soil": 50})  # below the 120-day P threshold
    assert result["persistence"]["outcome"] == INCONCLUSIVE
    assert "1 of 5" in result["persistence"]["note"]


def test_bioaccumulation_below_threshold_is_inconclusive_not_not_met():
    # Below the numeric B threshold is never reported as a conclusive "not bioaccumulative" -- Annex XIII's
    # own weight-of-evidence assessment (Section 3.2.2) allows other evidence this classifier doesn't see.
    result = classify_pbt_and_vpvb(bcf_l_per_kg=BCF_B_THRESHOLD_L_PER_KG - 1)
    assert result["bioaccumulation"]["outcome"] == INCONCLUSIVE
    assert result["bioaccumulation"]["note"] is not None


def test_toxicity_recognises_each_cmr_and_stot_re_flag_independently():
    for kwargs in [
        {"carcinogenic_category_1a_1b": True},
        {"germ_cell_mutagen_category_1a_1b": True},
        {"reproductive_toxicant_category_1a_1b_2": True},
        {"stot_re_category_1_2": True},
    ]:
        result = classify_pbt_and_vpvb(**kwargs)
        assert result["toxicity"]["outcome"] == MET, kwargs


def test_pbt_reuses_the_exact_thresholds_pathway_plausibility_already_ships():
    # Guards against the two modules' numbers quietly drifting apart.
    just_above_b = classify_pbt_and_vpvb(bcf_l_per_kg=BCF_B_THRESHOLD_L_PER_KG + 1)
    just_at_b = classify_pbt_and_vpvb(bcf_l_per_kg=BCF_B_THRESHOLD_L_PER_KG)
    assert just_above_b["bioaccumulation"]["outcome"] == MET
    assert just_at_b["bioaccumulation"]["outcome"] == INCONCLUSIVE
    just_above_vb = classify_pbt_and_vpvb(bcf_l_per_kg=BCF_VB_THRESHOLD_L_PER_KG + 1)
    assert just_above_vb["very_bioaccumulation"]["outcome"] == MET


def test_pbt_rejects_unknown_half_life_compartment():
    with pytest.raises(ClassifierInputError):
        classify_pbt_and_vpvb(half_life_days={"air": 100})


def test_pbt_rejects_non_positive_bcf_and_noec():
    with pytest.raises(ClassifierInputError):
        classify_pbt_and_vpvb(bcf_l_per_kg=0)
    with pytest.raises(ClassifierInputError):
        classify_pbt_and_vpvb(noec_or_ec10_mg_l=-1)


# ---------------------------------------------------------------------------
# PMT / vPvM
# ---------------------------------------------------------------------------


def test_pmt_met_when_p_m_and_t_all_met_including_endocrine_disruptor():
    result = classify_pmt_and_vpvm(
        half_life_days={"soil": 200},  # > 120 P threshold and > 180 vP threshold
        log_koc=1.5,  # < 3 M threshold and < 2 vM threshold
        endocrine_disruptor_category_1=True,
    )
    assert result["persistence"]["outcome"] == MET
    assert result["mobility"]["outcome"] == MET
    assert result["toxicity"]["outcome"] == MET
    assert "endocrine disruptor" in result["toxicity"]["basis"][0]
    assert result["pmt"] == MET
    assert result["very_persistence"]["outcome"] == MET
    assert result["very_mobility"]["outcome"] == MET
    assert result["vpvm"] == MET


def test_pmt_mobility_reuses_the_exact_koc_thresholds_pathway_plausibility_already_ships():
    just_below_m = classify_pmt_and_vpvm(log_koc=LOG_KOC_M_THRESHOLD - 0.01)
    at_m = classify_pmt_and_vpvm(log_koc=LOG_KOC_M_THRESHOLD)
    assert just_below_m["mobility"]["outcome"] == MET
    assert at_m["mobility"]["outcome"] == INCONCLUSIVE
    just_below_vm = classify_pmt_and_vpvm(log_koc=LOG_KOC_VM_THRESHOLD - 0.01)
    assert just_below_vm["very_mobility"]["outcome"] == MET


def test_pbt_classifier_has_no_endocrine_disruptor_parameter():
    # REACH Annex XIII's PBT toxicity criterion (Section 1.1.3) has no endocrine-disruption limb, unlike
    # CLP's PMT criterion (4.4.2.1.3(d)) -- confirm the parameter genuinely isn't accepted here, not just
    # ignored, so a caller can't silently believe it affected a PBT/vPvB result.
    with pytest.raises(TypeError):
        classify_pbt_and_vpvb(endocrine_disruptor_category_1=True)  # type: ignore[call-arg]


def test_pmt_rejects_unknown_half_life_compartment():
    with pytest.raises(ClassifierInputError):
        classify_pmt_and_vpvm(half_life_days={"air": 100})


def test_every_result_carries_its_source_and_the_weight_of_evidence_caveat():
    pbt_result = classify_pbt_and_vpvb()
    pmt_result = classify_pmt_and_vpvm()
    assert "Annex XIII" in pbt_result["source"]
    assert "weight-of-evidence" in pbt_result["caveat"]
    assert "2023/707" in pmt_result["source"]
    assert "weight-of-evidence" in pmt_result["caveat"]


# ---- organic-substances-only scope (found when aluminium's experimental BCF of 73,300 came back "vB") ----
from app.services.pbt_pmt_classifier import NOT_APPLICABLE


@pytest.mark.parametrize("group", ["metal_inorganic", "radionuclide"])
def test_pbt_and_vpvb_are_not_applicable_to_non_organic_groups_whatever_the_data_say(group):
    result = classify_pbt_and_vpvb(
        bcf_l_per_kg=73300, half_life_days={"soil": 1000}, noec_or_ec10_mg_l=0.001, substance_group=group,
    )
    assert result["pbt"] == NOT_APPLICABLE and result["vpvb"] == NOT_APPLICABLE
    assert result["bioaccumulation"]["outcome"] == NOT_APPLICABLE
    assert "organic" in result["scope_note"] and "weight-of-evidence" in result["caveat"]


@pytest.mark.parametrize("group", ["metal_inorganic", "radionuclide"])
def test_pmt_and_vpvm_are_not_applicable_to_non_organic_groups(group):
    result = classify_pmt_and_vpvm(log_koc=0.5, half_life_days={"soil": 1000}, substance_group=group)
    assert result["pmt"] == NOT_APPLICABLE and result["vpvm"] == NOT_APPLICABLE
    assert result["mobility"]["outcome"] == NOT_APPLICABLE


@pytest.mark.parametrize("group", [None, "industrial_organic", "pesticide", "organotin", "pfas_persistent_mobile"])
def test_organic_and_organometal_groups_are_still_classified(group):
    result = classify_pbt_and_vpvb(bcf_l_per_kg=6000, substance_group=group)
    assert result["very_bioaccumulation"]["outcome"] == MET
