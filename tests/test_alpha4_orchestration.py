from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import EvidenceRecord, ModelRun, OrchestratedAssessmentRecord, Source
from app.services.identity import identity_hash
from app.services.orchestration import (
    build_assessment_record,
    build_tier_sequence,
    characterise_risk,
    check_endpoint_compatibility,
    compare_jurisdictional_results,
    evaluate_tier_gate,
    harmonise_quantity,
    model_port_compatibility,
    record_hash,
    semantic_contract_catalogue,
)


ROOT = Path(__file__).resolve().parents[1]


def quantity(
    value: float,
    unit: str = "µg/L",
    *,
    compartment: str = "surface_water",
    phase: str = "total",
    basis: str = "volume",
    temporal_statistic: str = "mean",
    averaging_period_days: float | None = 1,
    spatial_scale: str = "local",
    substance_basis: str = "parent",
) -> dict:
    return {
        "value": value,
        "unit": unit,
        "endpoint_kind": "concentration",
        "compartment": compartment,
        "phase": phase,
        "basis": basis,
        "temporal_statistic": temporal_statistic,
        "averaging_period_days": averaging_period_days,
        "spatial_scale": spatial_scale,
        "substance_basis": substance_basis,
    }


def risk_input(value: float = 0.5, benchmark: float = 1.0, *, verified: bool = True) -> dict:
    data = {
        "name": "Aquatic chronic RQ",
        "metric": "pec_pnec_rq",
        "exposure": quantity(value),
        "benchmark": quantity(benchmark),
        "threshold": 1,
        "benchmark_type": "PNEC freshwater",
        "benchmark_source": "QA reviewed endpoint fixture",
        "guidance_reference": "QA method reference",
        "model_key": "ENVIROCHEM_CATCHMENT_RIVER_NETWORK",
    }
    if verified:
        data.update({
            "exposure_run_id": 999,
            "exposure_output_hash": "a" * 64,
            "exposure_value_verified": True,
            "benchmark_value_verified": True,
        })
    return data


def test_harmonises_supported_units_without_changing_scientific_basis():
    converted = harmonise_quantity(quantity(1000, "ng/L"), "µg/L")
    assert converted["value"] == pytest.approx(1)
    assert converted["unit"] == "µg/L"
    assert converted["compartment"] == "surface_water"
    assert converted["conversion"]["lossless_basis_change"] is True

    solid = quantity(
        1,
        "ng/g",
        compartment="soil",
        phase="bulk",
        basis="dry_weight",
        temporal_statistic="annual_average",
        averaging_period_days=365,
        spatial_scale="site",
    )
    assert harmonise_quantity(solid, "µg/kg")["value"] == pytest.approx(1)


def test_harmonisation_rejects_wrong_dimension_for_compartment():
    with pytest.raises(ValueError, match="requires solid_concentration"):
        harmonise_quantity(quantity(1, "µg/L", compartment="soil"), "µg/kg")


@pytest.mark.parametrize(
    ("changed", "expected_code"),
    [
        ({"phase": "dissolved"}, "phase_mismatch"),
        ({"temporal_statistic": "peak"}, "temporal_statistic_mismatch"),
        ({"averaging_period_days": 365}, "averaging_period_mismatch"),
        ({"spatial_scale": "regional"}, "spatial_scale_mismatch"),
        ({"substance_basis": "total_residue"}, "substance_basis_mismatch"),
    ],
)
def test_compatibility_fails_closed_on_scientific_basis_mismatch(changed, expected_code):
    source = quantity(1000, "ng/L")
    target = {**quantity(0, "µg/L"), **changed}
    target.pop("value")
    result = check_endpoint_compatibility(source, target)
    assert result["compatible"] is False
    assert expected_code in {reason["code"] for reason in result["reasons"]}


def test_compatible_endpoint_is_converted_to_target_unit():
    source = quantity(1000, "ng/L")
    target = quantity(0, "µg/L")
    target.pop("value")
    result = check_endpoint_compatibility(source, target)
    assert result["compatible"] is True
    assert result["harmonised_source"]["value"] == pytest.approx(1)


def test_model_port_contracts_only_auto_chain_verified_ports():
    catalogue = semantic_contract_catalogue()
    assert catalogue["coverage"]["registered_models"] >= 34
    assert catalogue["coverage"]["untyped_models"] > 0

    verified = model_port_compatibility(
        "ACTIVITY_SIMPLETREAT",
        "effluent_concentration",
        "ENVIROCHEM_CATCHMENT_RIVER_NETWORK",
        "effluent_concentration",
    )
    assert verified["compatible"] is True

    draft = model_port_compatibility(
        "PWC", "surface_water_peak", "ENVIROCHEM_TOXSWA_PROCESS_SCREEN", "surface_water_load"
    )
    assert draft["compatible"] is False
    assert draft["reasons"][0]["code"] == "unverified_model_contract"

    untyped = model_port_compatibility(
        "EPI_SUITE", "water_concentration", "ENVIROCHEM_CATCHMENT_RIVER_NETWORK", "effluent_concentration"
    )
    assert untyped["compatible"] is False
    assert untyped["reasons"][0]["code"] == "untyped_model_contract"


def test_risk_calculation_is_numeric_but_not_decision_eligible_without_provenance():
    unverified = characterise_risk(risk_input(0.5, 1, verified=False))
    assert unverified["value"] == pytest.approx(0.5)
    assert unverified["concern_triggered"] is False
    assert unverified["decision_eligible"] is False

    verified = characterise_risk(risk_input(2, 1, verified=True))
    assert verified["value"] == pytest.approx(2)
    assert verified["concern_triggered"] is True
    assert verified["decision_eligible"] is True


def test_pesticide_loc_and_margin_of_exposure_require_programme_thresholds():
    loc = risk_input(0.2, 1, verified=True)
    loc["metric"] = "pesticide_rq_loc"
    loc["threshold"] = None
    with pytest.raises(ValueError, match="programme-specific threshold"):
        characterise_risk(loc)

    moe = risk_input(1, 100, verified=True)
    moe.update({"metric": "margin_of_exposure", "threshold": 100})
    result = characterise_risk(moe)
    assert result["value"] == pytest.approx(100)
    assert result["concern_triggered"] is False


def test_tier_sequences_separate_eu_and_us_pesticide_programmes():
    common = {
        "contaminant_group": "pesticide",
        "scenario": "agricultural_spray",
        "maximum_tier": 4,
        "application_method": "aerial",
        "use_site_category": "outdoor_terrestrial",
        "bee_attractive": True,
    }
    eu = build_tier_sequence({**common, "jurisdiction": "EU"})
    us = build_tier_sequence({**common, "jurisdiction": "US"})
    assert [stage["tier"] for stage in eu] == [0, 1, 2, 3, 4]
    assert eu[2]["regulatory_programme"]["key"] == "EU_PPP_FOCUS"
    assert "PEARL" in {model["key"] for model in eu[2]["models"]}
    assert "PWC" not in {model["key"] for stage in eu for model in stage["models"]}
    assert us[2]["regulatory_programme"]["key"] == "US_FIFRA"
    assert "PWC" in {model["key"] for model in us[2]["models"]}
    assert "PEARL" not in {model["key"] for stage in us for model in stage["models"]}


def test_tier_gate_uses_risk_uncertainty_data_gaps_and_connections():
    below = characterise_risk(risk_input(0.5, 1, verified=True))
    stopped = evaluate_tier_gate(
        current_tier=1,
        maximum_tier=4,
        uncertainty="low",
        data_gaps=[],
        risk_results=[below],
    )
    assert stopped["action"] == "stop_screening"

    advanced = evaluate_tier_gate(
        current_tier=1,
        maximum_tier=4,
        uncertainty="moderate",
        data_gaps=[{"code": "FATE", "blocks_conclusion": True, "required_by_tier": 1}],
        risk_results=[below],
    )
    assert advanced["action"] == "advance"
    assert advanced["next_tier"] == 2

    blocked = evaluate_tier_gate(
        current_tier=2,
        maximum_tier=4,
        uncertainty="low",
        data_gaps=[],
        risk_results=[below],
        connection_results=[{"compatible": False}],
    )
    assert blocked["action"] == "resolve_incompatibility"


def test_cross_jurisdiction_comparison_never_claims_regulatory_alignment():
    compared = compare_jurisdictional_results({
        "left": {
            "jurisdiction": "EU",
            "model_key": "PEARL",
            "quantity": quantity(2, "µg/L", compartment="groundwater", phase="dissolved", temporal_statistic="annual_average", averaging_period_days=365, spatial_scale="site"),
            "scenario_reference": "FOCUS QA scenario",
        },
        "right": {
            "jurisdiction": "US",
            "model_key": "PWC",
            "quantity": quantity(1000, "ng/L", compartment="groundwater", phase="dissolved", temporal_statistic="annual_average", averaging_period_days=365, spatial_scale="site"),
            "scenario_reference": "EPA QA scenario",
        },
    })
    assert compared["status"] == "comparable"
    assert compared["comparison"]["left_to_right_ratio"] == pytest.approx(2)
    assert compared["regulatory_status"] == "cross_jurisdiction_comparative"


def test_assessment_record_is_content_addressed_and_never_auto_final():
    record = build_assessment_record(
        {
            "project_id": 1,
            "chemical_id": 2,
            "jurisdiction": "EU",
            "contaminant_group": "human_pharmaceutical",
            "scenario": "surface_water_discharge",
            "current_tier": 1,
            "maximum_tier": 4,
            "assessment_mode": "hybrid",
            "uncertainty": "low",
            "data_gaps": [],
            "model_results": [],
            "risk_characterisations": [risk_input()],
            "model_connections": [],
        },
        {"preferred_name": "QA substance", "identity_hash": "b" * 64},
        created_at="2026-09-08T00:00:00+00:00",
    )
    stored_hash = record.pop("record_hash")
    assert record_hash(record) == stored_hash
    assert record["regulatory_status"]["code"] == "research_only_hybrid"
    assert record["overall_conclusion"]["final_regulatory_decision"] is False
    assert {node["type"] for node in record["graph"]["nodes"]} >= {
        "chemical", "assessment_context", "tier", "risk_characterisation", "tier_decision"
    }


def diclofenac_candidate() -> dict:
    candidate = {
        "source_key": "pubchem",
        "source_record_id": "CID:3033",
        "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/3033",
        "pubchem_cid": 3033,
        "query_text": "diclofenac",
        "query_mode": "iupac",
        "preferred_name": "Diclofenac",
        "cas_number": "15307-86-5",
        "cas_candidates": ["15307-86-5"],
        "molecular_formula": "C14H11Cl2NO2",
        "molecular_weight_g_mol": 296.15,
        "smiles": "O=C(O)Cc1ccccc1Nc1c(Cl)cccc1Cl",
        "inchikey": "DCOPUUMXTXDBNB-UHFFFAOYSA-N",
        "substance_form": "parent",
        "warnings": ["Alpha 4 QA identity candidate"],
    }
    candidate["identity_hash"] = identity_hash(candidate)
    return candidate


def create_assessment_fixture(client: TestClient) -> tuple[int, int, int, int]:
    project_response = client.post("/api/projects", json={
        "name": f"Alpha4-{uuid4()}",
        "jurisdiction": "EU",
        "purpose": "FateIntel orchestration QA",
    })
    assert project_response.status_code == 201, project_response.text
    project_id = project_response.json()["id"]
    confirmed = client.post("/api/chemicals/from-resolved-identity", json={
        "project_id": project_id,
        "candidate": diclofenac_candidate(),
        "user_confirmed": True,
    })
    assert confirmed.status_code == 201, confirmed.text
    chemical_id = confirmed.json()["chemical"]["id"]
    with SessionLocal() as db:
        source = Source(
            source_type="journal_article",
            title="Alpha 4 reviewed aquatic endpoint fixture",
            organisation="FateIntel QA",
            publication_year=2026,
            identifier="QA:ALPHA4:EC50",
            url="https://example.test/alpha4-ec50",
            access_date="2026-09-08",
        )
        db.add(source)
        db.flush()
        evidence = EvidenceRecord(
            chemical_id=chemical_id,
            source_id=source.id,
            property_code="ECOTOX.AQUATIC.EC50",
            evidence_type="measured",
            original_value=1.0,
            original_unit="mg/L",
            endpoint_kind="EC50",
            test_guideline="OECD 202",
            reliability_score=1,
            representative_group_key="alpha4-aquatic-qa",
            include_by_default=True,
            notes="Synthetic evidence record used only for software regression testing.",
        )
        run = ModelRun(
            project_id=project_id,
            chemical_id=chemical_id,
            model_key="ENVIROCHEM_CATCHMENT_RIVER_NETWORK",
            model_version="alpha4-qa",
            scenario_name="QA river exposure",
            status="completed",
            input_json=json.dumps({"fixture": True}),
            output_json=json.dumps({"surface_water_mean_ug_l": 0.5}),
            assumptions_json=json.dumps({"fixture": "not regulatory"}),
        )
        db.add_all([evidence, run])
        db.commit()
        db.refresh(evidence)
        db.refresh(run)
        evidence_id = evidence.id
        run_id = run.id
    return project_id, chemical_id, run_id, evidence_id


def assessment_payload(
    project_id: int, chemical_id: int, run_id: int, evidence_id: int
) -> dict:
    risk = risk_input(0.5, 1, verified=False)
    risk["exposure_run_id"] = run_id
    risk["exposure_endpoint_key"] = "surface_water_mean_ug_l"
    risk.update({
        "benchmark_evidence_ids": [evidence_id],
        "critical_benchmark_evidence_id": evidence_id,
        "benchmark_evidence_review_confirmed": True,
        "assessment_factor": 1000,
        "assessment_factor_rationale": "One acute trophic endpoint is available in this synthetic QA dataset.",
    })
    return {
        "project_id": project_id,
        "chemical_id": chemical_id,
        "jurisdiction": "EU",
        "contaminant_group": "human_pharmaceutical",
        "scenario": "surface_water_discharge",
        "current_tier": 1,
        "maximum_tier": 4,
        "assessment_mode": "regulatory",
        "uncertainty": "low",
        "data_gaps": [],
        "model_connections": [],
        "model_results": [{
            "model_key": "ENVIROCHEM_CATCHMENT_RIVER_NETWORK",
            "jurisdiction": "EU",
            "tier": 1,
            "execution_status": "not_started",
            "alignment_claim": "research_screen",
            "guidance_reference": "QA method basis",
            "run_id": run_id,
            "outputs": [],
        }],
        "risk_characterisations": [risk],
    }


def test_orchestration_api_persists_identity_bound_record_and_immutable_review_successor():
    with TestClient(app) as client:
        project_id, chemical_id, run_id, evidence_id = create_assessment_fixture(client)
        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)

        preview = client.post("/api/orchestration/preview", json=payload)
        assert preview.status_code == 200, preview.text
        assert preview.json()["risk_characterisations"][0]["decision_eligible"] is True
        assert preview.json()["risk_characterisations"][0]["benchmark_derivation"]["critical_evidence_id"] == evidence_id
        assert preview.json()["current_tier_decision"]["action"] == "stop_screening"

        created = client.post("/api/orchestration/assessments", json=payload)
        assert created.status_code == 201, created.text
        created_body = created.json()
        assert len(created_body["record_hash"]) == 64
        assert created_body["record"]["identity"]["identity_snapshot_id"]
        assert created_body["record"]["overall_conclusion"]["final_regulatory_decision"] is False

        fetched = client.get(f"/api/orchestration/assessments/{created_body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["record_hash"] == created_body["record_hash"]

        finalised = client.post(
            f"/api/orchestration/assessments/{created_body['id']}/finalise",
            json={
                "reviewer": "QA Scientist",
                "decision": "accepted_for_stated_purpose",
                "rationale": "The record is accepted only as a non-regulatory orchestration regression fixture.",
                "stated_purpose": "Alpha 4 software quality assurance",
            },
        )
        assert finalised.status_code == 201, finalised.text
        final_body = finalised.json()
        assert final_body["supersedes_id"] == created_body["id"]
        assert final_body["record_hash"] != created_body["record_hash"]
        assert final_body["record"]["overall_conclusion"]["final_regulatory_decision"] is False

        duplicate_finalisation = client.post(
            f"/api/orchestration/assessments/{created_body['id']}/finalise",
            json={
                "reviewer": "Second Reviewer",
                "decision": "needs_refinement",
                "rationale": "A second finalisation of the same immutable snapshot must not be accepted.",
                "stated_purpose": "Alpha 4 duplicate-finalisation regression",
            },
        )
        assert duplicate_finalisation.status_code == 409

        original_again = client.get(f"/api/orchestration/assessments/{created_body['id']}").json()
        assert original_again["status"] == "assessment_snapshot"
        assert original_again["review_decision"] is None

        exported = client.get(f"/api/orchestration/assessments/{final_body['id']}/export")
        assert exported.status_code == 200
        assert exported.headers["content-disposition"].startswith("attachment; filename=\"FateIntel_assessment_")
        assert exported.json()["record_hash"] == final_body["record_hash"]

        with SessionLocal() as db:
            row = db.get(OrchestratedAssessmentRecord, created_body["id"])
            assert row.record_hash == created_body["record_hash"]
            row.status = "mutated"
            with pytest.raises(ValueError, match="immutable"):
                db.commit()
            db.rollback()


def test_orchestration_api_rejects_false_or_mismatched_provenance():
    with TestClient(app) as client:
        project_id, chemical_id, run_id, evidence_id = create_assessment_fixture(client)
        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)
        payload["risk_characterisations"][0]["exposure_output_hash"] = "f" * 64
        rejected = client.post("/api/orchestration/preview", json=payload)
        assert rejected.status_code == 422
        assert "does not match" in rejected.text

        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)
        payload["risk_characterisations"][0]["exposure"]["value"] = 0.6
        rejected = client.post("/api/orchestration/preview", json=payload)
        assert rejected.status_code == 422
        assert "does not match stored endpoint" in rejected.text

        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)
        payload["model_results"][0]["model_key"] = "SIMPLETREAT"
        rejected = client.post("/api/orchestration/preview", json=payload)
        assert rejected.status_code == 422
        assert "not part of this jurisdiction, use, release and tier route" in rejected.text

        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)
        payload["model_results"][0]["alignment_claim"] = "regulatory_accepted"
        preview = client.post("/api/orchestration/preview", json=payload)
        assert preview.status_code == 200, preview.text
        result = preview.json()["model_results"][0]
        assert result["alignment_claim"] == "research_screen"
        assert "downgraded" in result["alignment_validation"]

        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)
        payload["risk_characterisations"][0]["benchmark"]["value"] = 2
        rejected = client.post("/api/orchestration/preview", json=payload)
        assert rejected.status_code == 422
        assert "does not match the selected critical endpoint" in rejected.text

        payload = assessment_payload(project_id, chemical_id, run_id, evidence_id)
        risk = payload["risk_characterisations"][0]
        for key in (
            "benchmark_evidence_ids", "critical_benchmark_evidence_id",
            "benchmark_evidence_review_confirmed", "assessment_factor",
            "assessment_factor_rationale",
        ):
            risk.pop(key, None)
        exploratory = client.post("/api/orchestration/preview", json=payload)
        assert exploratory.status_code == 200, exploratory.text
        assert exploratory.json()["risk_characterisations"][0]["decision_eligible"] is False
        assert exploratory.json()["current_tier_decision"]["action"] == "collect_inputs"


def test_orchestration_endpoints_report_boundaries_and_contract_coverage():
    with TestClient(app) as client:
        manifest = client.get("/api/orchestration/manifest")
        assert manifest.status_code == 200
        assert manifest.json()["scientific_boundaries"]
        contracts = client.get("/api/orchestration/model-contracts")
        assert contracts.status_code == 200
        assert contracts.json()["coverage"]["untyped_models"] > 0
        plan = client.post("/api/orchestration/plan", json={
            "jurisdiction": "US",
            "contaminant_group": "pesticide",
            "scenario": "groundwater_leaching",
            "maximum_tier": 4,
        })
        assert plan.status_code == 200, plan.text
        assert "PWC" in {
            model["key"]
            for stage in plan.json()["tier_sequence"]
            for model in stage["models"]
        }


def test_expert_workspace_wires_the_alpha4_orchestration_contract():
    html = (ROOT / "app" / "static" / "expert.html").read_text(encoding="utf-8")
    javascript = (ROOT / "app" / "static" / "expert-app.js").read_text(encoding="utf-8")
    for token in (
        'data-page="orchestration"', 'id="page-orchestration"',
        'id="orchestration-form"', 'id="compatibility-form"',
        'id="orchestration-history"', "no automatic regulatory conclusion",
    ):
        assert token in html
    for endpoint in (
        "/api/orchestration/manifest", "/api/orchestration/model-contracts",
        "/api/orchestration/preview", "/api/orchestration/assessments",
        "/api/orchestration/model-compatibility",
    ):
        assert endpoint in javascript
    assert "FateIntel has not issued a final regulatory decision" in javascript
