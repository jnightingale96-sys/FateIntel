from app.services.adapters import ADAPTER_CONTRACTS, prepare_workflow_manifest, normalise_imported_output
from app.services.registry import MODELS


EXPECTED_KEYS = {
    "SIMPLETREAT", "ACTIVITY_SIMPLETREAT", "SIMPLEBOX", "ENVIROCHEM_MULTIMEDIA_FATE_SCREEN",
    "EPI_SUITE", "SPIN", "PEARL", "TOXSWA", "GREATER", "EPIE", "ENVIROCHEM_CATCHMENT_RIVER_NETWORK", "PELMO", "MACRO",
    "PRZM", "EXAMS", "PWC", "AGDRIFT", "TERRPLANT", "TREX", "BEEREX", "ENVIROCHEM_DUAL_WASTEWATER_IRRIGATION",
    "ENVIROCHEM_US_INDUSTRIAL_EXPOSURE_SCREEN", "CHEMSTEER", "CEM", "EFAST",
    "ENVIROCHEM_SOIL_SCREEN", "ENVIROCHEM_PLANT_UPTAKE", "ENVIROCHEM_TOXSWA_PROCESS_SCREEN",
    "ENVIROCHEM_BIOSOLIDS_LAND_APPLICATION", "SWASH",
    "ENVIRODESIGN_BIOWIN34_ATTRIBUTION", "ENVIRODESIGN_PATHWAY_RETENTION",
    "ENVIRODESIGN_CANDIDATE_COMPARISON",
    "BIOTRANSFORMER_ENVMICRO", "ENVIPATH_ENVMICRO",
}


def model(key: str):
    return next(x for x in MODELS if x["key"] == key)


def test_all_registered_models_have_adapter_contracts():
    assert {x["key"] for x in MODELS} == EXPECTED_KEYS
    assert set(ADAPTER_CONTRACTS) == EXPECTED_KEYS
    for key, contract in ADAPTER_CONTRACTS.items():
        assert contract["required_inputs"]
        assert contract["expected_outputs"]
        assert contract["workflow_steps"]
        assert contract["accepted_output_formats"]


def test_pearl_manifest_reports_missing_inputs_and_hashes():
    payload = {
        "project_id": 1,
        "chemical_id": 1,
        "model_key": "PEARL",
        "jurisdiction": "EU",
        "tier": 2,
        "scenario_name": "FOCUS groundwater screen",
        "input_data": {"soil_dt50": {"value": 35, "unit": "days"}},
        "executable_path": r"C:\\FOCUS\\PEARL",
    }
    manifest = prepare_workflow_manifest(payload, model("PEARL"))
    assert manifest["model"]["key"] == "PEARL"
    assert "koc_or_kd" in manifest["missing_inputs"]
    assert len(manifest["input_hash"]) == 64
    assert manifest["execution"]["mode"] == "managed_adapter"


def test_generic_key_value_output_import_is_hashed():
    output = normalise_imported_output(
        "groundwater_concentration=0.12\nleaching_flux: 4.6\ncomment=screening run",
        None,
    )
    assert output["structured_outputs"]["groundwater_concentration"] == 0.12
    assert output["structured_outputs"]["leaching_flux"] == 4.6
    assert output["structured_outputs"]["comment"] == "screening run"
    assert len(output["output_hash"]) == 64
