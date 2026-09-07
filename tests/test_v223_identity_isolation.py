from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.identity import core_identity_hash, identity_hash


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


CHEMICAL_FIXTURES = [
    ("Diclofenac", "human pharmaceutical", "C14H11Cl2NO2", 296.15, "O=C(O)Cc1ccccc1Nc1c(Cl)cccc1Cl"),
    ("Ibuprofen", "human pharmaceutical", "C13H18O2", 206.28, "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),
    ("Caffeine", "human pharmaceutical", "C8H10N4O2", 194.19, "Cn1c(=O)c2c(ncn2C)n(C)c1=O"),
    ("Sulfamethoxazole", "antibiotic", "C10H11N3O3S", 253.28, "Cc1noc(NS(=O)(=O)c2ccc(N)cc2)n1"),
    ("Metformin", "ionisable pharmaceutical", "C4H11N5", 129.17, "CN(C)C(=N)NC(=N)N"),
    ("Atrazine", "pesticide", "C8H14ClN5", 215.68, "CCNc1nc(Cl)nc(NC(C)C)n1"),
    ("Glyphosate", "pesticide", "C3H8NO5P", 169.07, "O=C(O)CNCP(=O)(O)O"),
    ("Carbaryl", "pesticide", "C12H11NO2", 201.22, "CNC(=O)Oc1cccc2ccccc12"),
    ("Permethrin", "pesticide", "C21H20Cl2O3", 391.29, "CC1(C)C(C(=O)OCc2cccc(Oc3ccccc3)c2)C1(Cl)Cl"),
    ("Triclosan", "biocide", "C12H7Cl3O2", 289.54, "Oc1cc(Cl)c(Oc2cc(Cl)cc(Cl)c2)cc1"),
    ("Benzene", "volatile industrial organic", "C6H6", 78.11, "c1ccccc1"),
    ("Toluene", "volatile industrial organic", "C7H8", 92.14, "Cc1ccccc1"),
    ("Phenol", "industrial organic", "C6H6O", 94.11, "Oc1ccccc1"),
    ("Bisphenol A", "consumer/article chemical", "C15H16O2", 228.29, "CC(c1ccc(O)cc1)(c2ccc(O)cc2)C"),
    ("EDTA", "chelating agent", "C10H16N2O8", 292.24, "O=C(O)CN(CC(=O)O)CCN(CC(=O)O)CC(=O)O"),
    ("PFOS", "persistent mobile substance", "C8HF17O3S", 500.13, "OS(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F"),
    ("Copper", "metal/inorganic", "Cu", 63.55, "[Cu]"),
    ("Naproxen", "human pharmaceutical", "C14H14O3", 230.26, "COc1ccc2cc(ccc2c1)C(C)C(=O)O"),
    ("Erythromycin", "veterinary/human antibiotic", "C37H67NO13", 733.94, "CC1OC(CC(C)C(O)C(C)C(=O)C(C)C(O)CN(C)C)OC)C(O)C1O"),
    ("Acetaminophen", "human pharmaceutical", "C8H9NO2", 151.16, "CC(=O)Nc1ccc(O)cc1"),
]


def candidate(namespace: str, index: int, row: tuple[str, str, str, float, str]) -> dict:
    name, category, formula, molecular_weight, smiles = row
    result = {
        "source_key": "pubchem",
        "source_record_id": f"QA:{namespace}:{index}",
        "source_url": f"https://example.invalid/identity/{namespace}/{index}",
        "query_text": name,
        "query_mode": "iupac",
        "preferred_name": f"{name} · isolation QA {namespace}",
        "cas_number": f"9{index:04d}-{int(namespace[:2], 16):02d}-{index % 10}",
        "cas_candidates": [],
        "molecular_formula": formula,
        "molecular_weight_g_mol": molecular_weight,
        "smiles": smiles,
        "inchikey": f"QA{namespace.upper()}{index:02d}-STATEISOLATION-X",
        "substance_form": "parent",
        "fixture_category": category,
        "warnings": ["State-isolation QA fixture; not a regulatory identity source."],
    }
    result["identity_hash"] = identity_hash(result)
    result["core_identity_hash"] = core_identity_hash(result)
    return result


def test_guided_startup_is_neutral_and_demo_is_explicit():
    assert 'id="project-pill">No assessment selected' in HTML
    assert 'id="identity-summary">No chemical selected' in HTML
    assert 'id="identity-input" placeholder=' in HTML
    assert 'id="identity-input" value="298-46-4"' not in HTML
    assert 'id="identity-structure" src="/static/chemical-placeholder.svg"' in HTML
    assert "renderNeutralWorkspace" in JS
    assert "loadInitialWorkspace" in JS
    ensure_workspace = JS[JS.index("async function ensureWorkspace") : JS.index("function setWorkspaceUrl")]
    assert "Carbamazepine" not in ensure_workspace
    assert "chemicals[0]" not in ensure_workspace
    assert "The selected project/chemical binding is no longer available" in ensure_workspace


def test_twenty_chemical_sequence_has_no_profile_evidence_or_run_identity_leakage():
    namespace = uuid4().hex[:8]
    with TestClient(app) as client:
        project_response = client.post(
            "/api/projects",
            json={
                "name": f"Twenty-chemical-isolation-{namespace}",
                "jurisdiction": "EU/US QA",
                "purpose": "Cross-chemical state-isolation regression",
            },
        )
        assert project_response.status_code == 201
        project = project_response.json()

        confirmed: list[dict] = []
        source_candidates: list[dict] = []
        for index, row in enumerate(CHEMICAL_FIXTURES, start=1):
            resolved = candidate(namespace, index, row)
            response = client.post(
                "/api/chemicals/from-resolved-identity",
                json={
                    "project_id": project["id"],
                    "candidate": resolved,
                    "user_confirmed": True,
                },
            )
            assert response.status_code == 201, response.text
            payload = response.json()
            assert payload["profile"]["review_status"] == "draft"
            assert payload["profile"]["log_kow"] is None
            assert payload["chemical"]["preferred_name"] == resolved["preferred_name"]
            assert payload["chemical"]["identity_snapshot"]["identity_hash"] == resolved["identity_hash"]
            confirmed.append(payload)
            source_candidates.append(resolved)

        assert len({item["chemical"]["id"] for item in confirmed}) == 20
        assert len({item["profile"]["id"] for item in confirmed}) == 20

        first = confirmed[0]
        reviewed = client.put(
            f"/api/projects/{project['id']}/chemicals/{first['chemical']['id']}/assessment-profile",
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
                "wwtp_volatilisation_fraction": 0.0,
                "source_summary": "QA-only state-isolation values; not regulatory selections.",
                "provenance": {"status": "qa_fixture_not_regulatory"},
                "reviewer_confirmation": True,
            },
        )
        assert reviewed.status_code == 200, reviewed.text

        second = confirmed[1]
        second_profile = client.get(
            f"/api/projects/{project['id']}/chemicals/{second['chemical']['id']}/assessment-profile"
        )
        assert second_profile.status_code == 200
        assert second_profile.json()["review_status"] == "draft"
        assert second_profile.json()["log_kow"] is None

        evidence = client.post(
            "/api/evidence",
            json={
                "project_id": project["id"],
                "chemical_id": first["chemical"]["id"],
                "source": {"title": "QA identity-isolation evidence"},
                "property_code": "FATE.SOIL_DT50",
                "evidence_type": "measured",
                "original_value": 30,
                "original_unit": "days",
                "representative_group_key": f"qa-{namespace}",
            },
        )
        assert evidence.status_code == 201, evidence.text
        second_evidence = client.get(
            f"/api/projects/{project['id']}/chemicals/{second['chemical']['id']}/evidence"
        )
        assert second_evidence.status_code == 200
        assert second_evidence.json() == []

        persisted = client.post(
            "/api/envirodesign/persist-browser",
            json={
                "model_key": "ENVIRODESIGN_BROWSER_WASM",
                "project_id": project["id"],
                "chemical_id": first["chemical"]["id"],
                "scenario_name": "Identity-binding QA",
                "inputs": {"smiles": source_candidates[0]["smiles"]},
                "outputs": {"model_version": "qa-only", "warnings": []},
            },
        )
        assert persisted.status_code == 200, persisted.text
        binding = client.get(
            f"/api/model-runs/{persisted.json()['model_run_id']}/identity-binding"
        )
        assert binding.status_code == 200, binding.text
        assert binding.json()["chemical_id"] == first["chemical"]["id"]
        assert binding.json()["identity_hash"] == source_candidates[0]["identity_hash"]
        assert binding.json()["preferred_name"] == source_candidates[0]["preferred_name"]


def test_cas_and_inchikey_cross_record_conflict_is_rejected():
    namespace = uuid4().hex[:8]
    with TestClient(app) as client:
        project = client.post(
            "/api/projects",
            json={"name": f"Identity-conflict-{namespace}"},
        ).json()
        first = candidate(namespace, 1, CHEMICAL_FIXTURES[0])
        second = candidate(namespace, 2, CHEMICAL_FIXTURES[1])
        for resolved in (first, second):
            response = client.post(
                "/api/chemicals/from-resolved-identity",
                json={"project_id": project["id"], "candidate": resolved, "user_confirmed": True},
            )
            assert response.status_code == 201, response.text

        conflicting = dict(first)
        conflicting["inchikey"] = second["inchikey"]
        conflicting["identity_hash"] = identity_hash(conflicting)
        conflicting["core_identity_hash"] = core_identity_hash(conflicting)
        response = client.post(
            "/api/chemicals/from-resolved-identity",
            json={"project_id": project["id"], "candidate": conflicting, "user_confirmed": True},
        )
        assert response.status_code == 409
        assert "CAS number and InChIKey resolve to different stored chemical records" in response.text
