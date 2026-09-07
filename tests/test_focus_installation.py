from app.services.focus_installation import manifest, installation_status
from app.services.registry import build_assessment_plan


def test_focus_manifest_order_and_versions():
    data = manifest()
    assert [x["key"] for x in data["models"]] == ["SPIN","PEARL","SWASH","MACRO","TOXSWA"]
    assert next(x for x in data["models"] if x["key"]=="PEARL")["version"].startswith("5.5.5")
    assert next(x for x in data["models"] if x["key"]=="MACRO")["version"].startswith("5.5.4a")


def test_eu_surface_plan_includes_swash_before_toxswa():
    plan = build_assessment_plan({"jurisdiction":"EU","contaminant_group":"pesticide","scenario":"agricultural_spray","tier":3})
    keys=[x["key"] for x in plan["models"]]
    assert "SWASH" in keys and "TOXSWA" in keys
    assert keys.index("SWASH") < keys.index("TOXSWA")


def test_installation_status_is_honest():
    status=installation_status()
    assert "ready_for_pearl" in status and "ready_for_toxswa" in status
    assert "ready_for_macro_groundwater" in status and "ready_for_macro_surface_water" in status
