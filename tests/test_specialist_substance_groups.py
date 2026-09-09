from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.specialist_groups import specialist_substance_group_requirements


def test_specialist_group_registry_is_fail_closed_and_source_complete():
    payload = specialist_substance_group_requirements()

    assert payload["status"] == "specification_only"
    assert payload["implementation_boundary"]["executable_rules"] is False
    assert payload["implementation_boundary"]["regulatory_decision_support"] is False
    assert set(payload["specialist_groups"]) == {"nanomaterials", "pfas"}

    sources = payload["sources"]
    source_ids = [source["id"] for source in sources]
    assert len(source_ids) == len(set(source_ids))
    assert all(source["url"].startswith("https://") for source in sources)

    referenced: set[str] = set()

    def collect(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "source_ids":
                    referenced.update(nested)
                else:
                    collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(payload["specialist_groups"])
    assert referenced <= set(source_ids)


def test_specialist_group_modules_remain_explicitly_unimplemented():
    groups = specialist_substance_group_requirements()["specialist_groups"]
    for group in groups.values():
        assert group["runtime_status"] == "specified_not_implemented"
        assert group["required_software_modules"]
        assert {
            module["status"] for module in group["required_software_modules"]
        } == {"specified_not_implemented"}


def test_specialist_group_registry_api_preserves_boundary():
    with TestClient(app) as client:
        response = client.get("/api/orchestration/specialist-substance-groups")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "specification_only"
    assert body["implementation_boundary"]["automatic_pmt_vpvm_classification"] is False
    assert body["specialist_groups"]["pfas"]["pmt_vpvm_screen"]["runtime_status"] == "specified_not_implemented"
