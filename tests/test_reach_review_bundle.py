from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.reach.exporter import (
    BundleVerificationError,
    REVIEW_SCHEMA,
    build_review_bundle,
    verify_review_bundle,
)
from app.reach.pnec import derive_pnec
from app.reach.units import convert_concentration, normalise_concentration_unit
from app.services.identity import identity_hash


@pytest.mark.parametrize(
    ("value", "unit", "expected_ug_l"),
    [
        (1000, "ng/L", 1),
        (1, "ug/L", 1),
        (1, "µg/L", 1),
        (1, "μg/L", 1),
        (1, "mg/L", 1000),
        (1, "g/L", 1_000_000),
    ],
)
def test_concentration_normalisation(value, unit, expected_ug_l):
    assert float(convert_concentration(value, unit)) == pytest.approx(expected_ug_l)


@pytest.mark.parametrize(
    ("value", "unit"),
    [(0, "mg/L"), (-1, "mg/L"), (float("nan"), "mg/L"), (1, "ppm")],
)
def test_concentration_normalisation_rejects_unsafe_inputs(value, unit):
    with pytest.raises(ValueError):
        convert_concentration(value, unit)


def test_pnec_uses_explicit_factor_and_records_review_boundary():
    result = derive_pnec(
        endpoint_value=1,
        endpoint_unit="mg/L",
        endpoint_type="EC50",
        assessment_factor=1000,
        assessment_factor_rationale="Three-trophic-level acute dataset selected by the QA reviewer.",
        guidance_reference="ECHA IR&CSA Chapter R.10; reviewer must confirm applicability",
    )
    assert result["critical_endpoint"]["normalised_value"] == pytest.approx(1000)
    assert result["pnec"] == {"value": 1.0, "unit": "µg/L"}
    assert result["assessment_factor_source"] == "reviewer_supplied"
    assert result["regulatory_status"] == "review_required_not_authoritative_selection"


def test_pnec_never_silently_replaces_an_invalid_factor():
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        derive_pnec(
            endpoint_value=1,
            endpoint_unit="mg/L",
            endpoint_type="EC50",
            assessment_factor=0,
            assessment_factor_rationale="The reviewer supplied an invalid assessment factor.",
            guidance_reference="QA reference",
        )


def _review_record(name: str = "Diclofenac") -> dict:
    return {
        "schema": REVIEW_SCHEMA,
        "schema_version": "1.0",
        "prepared_at": "2026-08-16T12:00:00Z",
        "release": {"version": "2.20-beta", "build_id": "qa"},
        "scope": {
            "kind": "reach_preparation_review_bundle",
            "submission_ready": False,
            "iuclid_format": False,
            "purpose": "QA",
        },
        "project": {"id": 1, "name": "QA", "jurisdiction": "EU", "purpose": "QA"},
        "chemical": {
            "id": 2,
            "preferred_name": name,
            "cas_number": "15307-86-5",
            "molecular_formula": "C14H11Cl2NO2",
            "molecular_weight_g_mol": 296.15,
            "smiles": "O=C(O)Cc1ccccc1Nc1c(Cl)cccc1Cl",
            "inchikey": "DCOPUUMXTXDBNB-UHFFFAOYSA-N",
            "substance_form": "parent",
            "identity_hash": "a" * 64,
            "identity_source": {"source_key": "qa", "confirmed_at": "2026-08-16T12:00:00Z"},
        },
        "assessment_profile": {
            "id": 3,
            "review_status": "reviewed",
            "reviewer_confirmation": True,
            "profile_hash": "b" * 64,
            "log_kow": 4.5,
            "soil_dt50_days": 30,
        },
        "pnec_derivation": {
            "target_compartment": "freshwater",
            "critical_endpoint": {
                "evidence_id": 4,
                "endpoint_type": "EC50",
                "value": 1.0,
                "unit": "mg/L",
                "normalised_value": 1000.0,
                "normalised_unit": "µg/L",
            },
            "assessment_factor": 1000,
            "assessment_factor_rationale": "QA reviewer-selected factor.",
            "guidance_reference": "ECHA R.10",
            "pnec": {"value": 1.0, "unit": "µg/L"},
        },
        "evidence": [{
            "id": 4,
            "property_code": "ECOTOX.AQUATIC.EC50",
            "endpoint_kind": "EC50",
            "original_value": 1.0,
            "original_unit": "mg/L",
            "reliability_score": 1,
            "source": {"title": "QA evidence", "identifier": "QA-1"},
        }],
        "model_runs": [],
        "review": {
            "reviewer_name": "QA Reviewer",
            "reviewer_role": "Scientist",
            "confirmed_at": "2026-08-16T12:00:00Z",
            "statement": "Preparation review only.",
        },
    }


def test_unsigned_bundle_is_complete_reviewable_and_verifiable():
    bundle = build_review_bundle(
        _review_record(),
        exporter_version="2.20-beta",
        created_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )
    result = verify_review_bundle(bundle.data)
    assert result["valid"] is True
    assert result["signature_status"] == "unsigned"
    assert result["boundary"] == "NOT_IUCLID_NOT_SUBMISSION_READY"
    with zipfile.ZipFile(BytesIO(bundle.data)) as archive:
        assert set(archive.namelist()) == {
            "README.txt", "reach-review.json", "reach-review.xml",
            "csr-review.html", "manifest.json",
        }
        assert b"NOT an IUCLID dossier" in archive.read("README.txt")
        assert b"IUCLID_Dossier" not in archive.read("reach-review.xml")


def test_html_summary_escapes_untrusted_values():
    bundle = build_review_bundle(
        _review_record('<script>alert("x")</script>'),
        exporter_version="2.20-beta",
    )
    with zipfile.ZipFile(BytesIO(bundle.data)) as archive:
        html = archive.read("csr-review.html").decode("utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_verifier_detects_payload_tampering():
    original = build_review_bundle(_review_record(), exporter_version="2.20-beta").data
    output = BytesIO()
    with zipfile.ZipFile(BytesIO(original)) as source, zipfile.ZipFile(output, "w") as target:
        for name in source.namelist():
            payload = source.read(name)
            if name == "README.txt":
                payload += b"tampered"
            target.writestr(name, payload)
    result = verify_review_bundle(output.getvalue())
    assert result["valid"] is False
    assert "sha256 mismatch: README.txt" in result["issues"]


def test_verifier_rejects_zip_path_traversal():
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../manifest.json", b"{}")
    with pytest.raises(BundleVerificationError, match="unsafe file path"):
        verify_review_bundle(output.getvalue())


def test_rsa_pss_signature_round_trip_and_wrong_key_detection():
    cryptography = pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    bundle = build_review_bundle(
        _review_record(),
        exporter_version="2.20-beta",
        signing_mode="rsa",
        private_key_pem=private_pem,
    )
    without_key = verify_review_bundle(bundle.data)
    assert without_key["integrity_valid"] is True
    assert without_key["valid"] is False
    assert without_key["signature_status"] == "public_key_required"
    verified = verify_review_bundle(bundle.data, public_key_pem=public_pem)
    assert verified["valid"] is True
    assert verified["signature_verified"] is True

    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_public = wrong.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    rejected = verify_review_bundle(bundle.data, public_key_pem=wrong_public)
    assert rejected["valid"] is False
    assert "public key fingerprint does not match the manifest" in rejected["issues"]


def _diclofenac_candidate() -> dict:
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
        "warnings": ["QA identity candidate"],
    }
    candidate["identity_hash"] = identity_hash(candidate)
    return candidate


def _create_reviewed_diclofenac(client: TestClient) -> tuple[int, int, int, int]:
    project = client.post("/api/projects", json={
        "name": f"REACH-Diclofenac-{uuid4()}",
        "jurisdiction": "EU",
        "purpose": "v2.20 REACH review-bundle QA",
    }).json()
    confirmed = client.post("/api/chemicals/from-resolved-identity", json={
        "project_id": project["id"],
        "candidate": _diclofenac_candidate(),
        "user_confirmed": True,
    })
    assert confirmed.status_code == 201, confirmed.text
    chemical_id = confirmed.json()["chemical"]["id"]
    saved = client.put(
        f"/api/projects/{project['id']}/chemicals/{chemical_id}/assessment-profile",
        json={
            "ionisation_class": "acid",
            "log_kow": 4.5,
            "pkaa": 4.15,
            "water_solubility_mg_l": 0.01,
            "vapour_pressure_pa": 0.0001,
            "soil_dt50_days": 30,
            "wwtp_biodegradation_fraction": 0.2,
            "wwtp_primary_sludge_fraction": 0.1,
            "wwtp_secondary_sludge_fraction": 0.1,
            "wwtp_volatilisation_fraction": 0,
            "source_summary": "QA-only reviewed values for REACH bundle binding.",
            "provenance": {"status": "qa_fixture_not_regulatory"},
            "reviewer_confirmation": True,
        },
    )
    assert saved.status_code == 200, saved.text
    evidence = client.post("/api/evidence", json={
        "project_id": project["id"],
        "chemical_id": chemical_id,
        "source": {
            "source_type": "test_report",
            "title": "Diclofenac acute aquatic QA endpoint",
            "organisation": "QA",
            "publication_year": 2026,
            "identifier": f"REACH-QA-{uuid4()}",
            "url": "https://example.invalid/qa",
            "access_date": "2026-08-16",
        },
        "property_code": "ECOTOX.AQUATIC.EC50",
        "evidence_type": "measured",
        "original_value": 1,
        "original_unit": "mg/L",
        "endpoint_kind": "EC50",
        "test_guideline": "QA guideline",
        "reliability_score": 1,
        "representative_group_key": f"reach-qa-{uuid4()}",
        "include_by_default": True,
        "notes": "QA-only; not a regulatory selected value.",
    })
    assert evidence.status_code == 201, evidence.text
    return project["id"], chemical_id, saved.json()["id"], evidence.json()["id"]


def test_api_exports_diclofenac_review_bundle_and_audits_it():
    with TestClient(app) as client:
        project_id, chemical_id, profile_id, evidence_id = _create_reviewed_diclofenac(client)
        preview = client.post("/api/reach/pnec/derive", json={
            "endpoint_value": 1,
            "endpoint_unit": "mg/L",
            "endpoint_type": "EC50",
            "assessment_factor": 1000,
            "assessment_factor_rationale": "QA reviewer selected this explicit factor.",
            "guidance_reference": "ECHA IR&CSA Chapter R.10",
        })
        assert preview.status_code == 200, preview.text
        assert preview.json()["pnec"]["value"] == pytest.approx(1)

        response = client.post("/api/reach/review-bundles", json={
            "project_id": project_id,
            "chemical_id": chemical_id,
            "assessment_profile_id": profile_id,
            "selected_evidence_ids": [evidence_id],
            "selected_model_run_ids": [],
            "pnec": {
                "critical_evidence_id": evidence_id,
                "assessment_factor": 1000,
                "assessment_factor_rationale": "QA reviewer selected this explicit factor.",
                "guidance_reference": "ECHA IR&CSA Chapter R.10",
            },
            "reviewer_name": "QA Reviewer",
            "reviewer_role": "Environmental scientist",
            "reviewer_confirmation": True,
            "signing_mode": "unsigned",
        })
        assert response.status_code == 200, response.text
        assert response.headers["X-EnviroChem-Submission-Status"] == "NOT_IUCLID_NOT_SUBMISSION_READY"
        assert response.headers["X-EnviroChem-Signing-Mode"] == "unsigned"
        result = verify_review_bundle(response.content)
        assert result["valid"] is True
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            review = json.loads(archive.read("reach-review.json"))
        assert review["chemical"]["preferred_name"] == "Diclofenac"
        assert review["pnec_derivation"]["critical_endpoint"]["evidence_id"] == evidence_id
        assert review["assessment_profile"]["review_status"] == "reviewed"

        uploaded = client.post(
            "/api/reach/review-bundles/verify",
            files={"bundle": ("review.zip", response.content, "application/zip")},
        )
        assert uploaded.status_code == 200, uploaded.text
        assert uploaded.json()["valid"] is True

        audit = client.get(f"/api/projects/{project_id}/audit").json()
        exported = next(item for item in audit if item["action"] == "exported")
        assert exported["entity_type"] == "reach_review_bundle"
        assert exported["payload"]["chemical_id"] == chemical_id
        assert exported["payload"]["boundary"] == "NOT_IUCLID_NOT_SUBMISSION_READY"


def test_api_rejects_non_ecotoxicity_critical_evidence_and_missing_signer(monkeypatch):
    with TestClient(app) as client:
        project_id, chemical_id, profile_id, _ = _create_reviewed_diclofenac(client)
        fate = client.post("/api/evidence", json={
            "project_id": project_id,
            "chemical_id": chemical_id,
            "source": {"source_type": "test_report", "title": "Fate-only QA evidence"},
            "property_code": "FATE.SOIL_DT50",
            "evidence_type": "measured",
            "original_value": 30,
            "original_unit": "days",
            "representative_group_key": f"fate-{uuid4()}",
        }).json()
        base = {
            "project_id": project_id,
            "chemical_id": chemical_id,
            "assessment_profile_id": profile_id,
            "selected_evidence_ids": [fate["id"]],
            "selected_model_run_ids": [],
            "pnec": {
                "critical_evidence_id": fate["id"],
                "assessment_factor": 1000,
                "assessment_factor_rationale": "QA reviewer selected this explicit factor.",
                "guidance_reference": "ECHA IR&CSA Chapter R.10",
            },
            "reviewer_name": "QA Reviewer",
            "reviewer_role": "Environmental scientist",
            "reviewer_confirmation": True,
            "signing_mode": "unsigned",
        }
        rejected = client.post("/api/reach/review-bundles", json=base)
        assert rejected.status_code == 422
        assert "Critical PNEC evidence" in rejected.text

        mismatch = client.post("/api/evidence", json={
            "project_id": project_id,
            "chemical_id": chemical_id,
            "source": {"source_type": "test_report", "title": "Mismatched endpoint QA evidence"},
            "property_code": "ECOTOX.AQUATIC.EC50",
            "evidence_type": "measured",
            "original_value": 1,
            "original_unit": "mg/L",
            "endpoint_kind": "NOEC",
            "representative_group_key": f"mismatch-{uuid4()}",
        }).json()
        base["selected_evidence_ids"] = [mismatch["id"]]
        base["pnec"]["critical_evidence_id"] = mismatch["id"]
        mismatch_rejected = client.post("/api/reach/review-bundles", json=base)
        assert mismatch_rejected.status_code == 422
        assert "endpoint_kind conflicts" in mismatch_rejected.text

        ecotox = client.post("/api/evidence", json={
            "project_id": project_id,
            "chemical_id": chemical_id,
            "source": {"source_type": "test_report", "title": "Aquatic QA evidence"},
            "property_code": "ECOTOX.AQUATIC.EC50",
            "evidence_type": "measured",
            "original_value": 1,
            "original_unit": "mg/L",
            "endpoint_kind": "EC50",
            "representative_group_key": f"ecotox-{uuid4()}",
        }).json()
        base["selected_evidence_ids"] = [ecotox["id"]]
        base["pnec"]["critical_evidence_id"] = ecotox["id"]
        base["signing_mode"] = "rsa"
        monkeypatch.setattr("app.main.settings.reach_manifest_private_key_path", None)
        missing_signer = client.post("/api/reach/review-bundles", json=base)
        assert missing_signer.status_code == 503
        assert missing_signer.json()["error"]["code"] == "reach_signing_unavailable"


def test_unit_label_normaliser_has_a_single_microgram_canonical_form():
    assert normalise_concentration_unit(" uG / L ") == "µg/L"


def test_expert_ui_exposes_the_non_submission_reach_workflow():
    root = Path(__file__).resolve().parents[1]
    html = (root / "app" / "static" / "expert.html").read_text(encoding="utf-8")
    javascript = (root / "app" / "static" / "expert-app.js").read_text(encoding="utf-8")
    assert 'data-page="reach"' in html
    assert 'id="reach-bundle-form"' in html
    assert "not an IUCLID dossier" in html
    assert 'fetch("/api/reach/review-bundles"' in javascript
    assert "selected_evidence_ids" in javascript
    assert "X-EnviroChem-Manifest-SHA256" in javascript
