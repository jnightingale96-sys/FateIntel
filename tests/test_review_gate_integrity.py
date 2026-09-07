"""Adversarial regression coverage for the Alpha 3.2.1 and 3.2.2 hotfixes.

Alpha 3.2.1's external audit demonstrated, end to end, that:
(a) every field in the pesticide-model forms accepted the literal string
    "not-a-number" and still reached workflow status "prepared";
(b) a workflow could be marked "reviewed" after importing nothing but
    `nonsense=1` via the plain /import-output route.

A second, independent audit of the Alpha 3.2.1 fix then demonstrated that it
was itself incomplete:
(c) an invalid enum value (an application method outside the registered list)
    still reached "prepared";
(d) the literal strings "NaN"/"Infinity" still reached "prepared", since
    Python's float() accepts both without raising;
(e) output-completeness enforcement was silently absent for any model outside
    the 12-key MODEL_PROFILES set -- reproduced live with PEARL: prepared with
    valid inputs, imported an unrelated file/output mapping none of PEARL's
    expected outputs, and reached "reviewed";
(f) a workflow already "reviewed" could be silently reverted to
    "output_imported" by a later plain-text import, overwriting the accepted
    output record.

A third, independent audit of the Alpha 3.2.2 fix then demonstrated that it
was itself incomplete in four further ways:
(g) a workflow already "reviewed" could have its decision silently changed by
    a second /review call (e.g. reviewed -> rejected), overwriting the
    reviewer and notes on a closed record;
(h) the JSON boolean `true` reached a numeric field's requirement, since
    Python's float(True) == 1.0 succeeds without raising (bool is a subclass
    of int);
(i) TOXSWA's conditional time_series_if_requested output blocked acceptance
    even when no time series was requested, because the generic output-
    completeness fallback treated every entry in a contract's expected_outputs
    as unconditionally mandatory.

Every one of these ten was independently reproduced against the live app
before its respective hotfix, and all are captured here as permanent
regressions to guard against reintroducing any of them.
"""
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _chemical(client: TestClient) -> dict:
    return next(row for row in client.get("/api/chemicals").json() if row["preferred_name"] == "Carbamazepine")


def _project(client: TestClient, label: str, jurisdiction: str = "US") -> dict:
    return client.post("/api/projects", json={"name": f"{label} {uuid4().hex[:8]}", "jurisdiction": jurisdiction}).json()


def _prepare(client: TestClient, model_key: str, input_data: dict, jurisdiction: str = "US", tier: int = 2) -> dict:
    project = _project(client, f"{model_key} review-gate QA", jurisdiction)
    response = client.post("/api/model-workflows", json={
        "project_id": project["id"],
        "chemical_id": _chemical(client)["id"],
        "model_key": model_key,
        "jurisdiction": jurisdiction,
        "tier": tier,
        "scenario_name": f"{model_key} review-gate QA",
        "input_data": input_data,
    })
    assert response.status_code == 200, response.text
    return response.json()


NONSENSE_AGDRIFT_INPUTS = {
    "contaminant_group": "pesticide",
    "application_parameters": {"application_method": "not-a-number", "boom_height_m": "not-a-number", "droplet_size_category": "not-a-number", "application_rate_kg_ha": "not-a-number"},
    "meteorological_conditions": {"wind_speed_m_s": "not-a-number"},
    "buffer_and_geometry": {"buffer_distance_m": "not-a-number", "waterbody_width_m": "not-a-number"},
}

NONSENSE_PWC_INPUTS = {
    "contaminant_group": "pesticide",
    "application_pattern": {"application_rate_kg_ha": "not-a-number", "number_of_applications": "not-a-number", "application_method": "aerial"},
    "pwc3_us_scenario": {"scenario_id": "x", "crop": "x"},
    "soil_and_crop_inputs": {"crop": "x"},
    "weather_series": {"weather_station_id": "x"},
    "soil_dt50": {"value_days": "not-a-number", "source": "x"},
    "koc_or_kd": {"value": "not-a-number", "unit": "L/kg"},
    "aquatic_fate_inputs": {},
    "groundwater_and_waterbody_configuration": {"waterbody_type": "index_pond", "depth_m": "not-a-number"},
}


def test_nonnumeric_agdrift_inputs_never_reach_prepared():
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", NONSENSE_AGDRIFT_INPUTS)
        assert workflow["status"] != "prepared", "nonsense numeric strings must not satisfy AgDRIFT's required inputs"
        assert workflow["manifest"]["missing_inputs"], "at least one field must be reported missing/invalid"


def test_nonnumeric_pwc_inputs_never_reach_prepared():
    with TestClient(app) as client:
        workflow = _prepare(client, "PWC", NONSENSE_PWC_INPUTS)
        assert workflow["status"] != "prepared"
        missing = workflow["manifest"]["missing_inputs"]
        assert any("must be numeric" in item for item in missing), missing


def test_plain_text_import_can_never_reach_reviewed_for_any_model():
    # Exact reproduction of the audited AgDRIFT bypass: prepare with garbage,
    # import only "nonsense=1" via the plain /import-output route, attempt to
    # accept the review. Must be rejected, not silently marked "reviewed".
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", {
            "contaminant_group": "pesticide",
            "application_parameters": {"a": 1}, "meteorological_conditions": {"a": 1}, "buffer_and_geometry": {"a": 1},
        })
        imported = client.post(f"/api/model-workflows/{workflow['id']}/import-output", json={"raw_output_text": "nonsense=1"})
        assert imported.status_code == 200, imported.text
        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "adversarial bypass attempt",
        })
        assert reviewed.status_code == 409, reviewed.text
        assert "genuine" in reviewed.json()["detail"].lower()


def test_hashed_file_import_now_available_to_a_previously_blocked_model():
    # Before this hotfix, /import-output-files was hard-restricted to
    # EPA_EXECUTION_MODEL_KEYS ({PWC, CHEMSTEER, CEM, EFAST}); AgDRIFT (outside
    # that set) had no way to produce genuine provenance at all. Confirm the
    # route is now open to it, and that a genuine import can actually reach
    # "reviewed" -- the fix must open a real path, not just close the old one.
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", {
            "contaminant_group": "pesticide",
            "application_parameters": {"application_method": "aerial", "boom_height_m": 2, "droplet_size_category": "medium", "application_rate_kg_ha": 1.1},
            "meteorological_conditions": {"wind_speed_m_s": 3},
            "buffer_and_geometry": {"buffer_distance_m": 30, "waterbody_width_m": 10},
        })
        assert workflow["status"] == "prepared", workflow

        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Adversarial-test genuine import",
                "structured_outputs_json": json.dumps({
                    "off_site_deposition_fraction": 0.02, "downwind_deposition_curve": "QA curve",
                }),
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("agdrift_result.txt", b"off_site_deposition_fraction=0.02", "text/plain")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["output_record"]["execution_provenance"]["real_execution"] is True

        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "genuine hashed-file import",
        })
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "reviewed"


VALID_AGDRIFT_INPUTS = {
    "contaminant_group": "pesticide",
    "application_parameters": {"application_method": "aerial", "boom_height_m": 2, "droplet_size_category": "medium", "application_rate_kg_ha": 1.1},
    "meteorological_conditions": {"wind_speed_m_s": 3},
    "buffer_and_geometry": {"buffer_distance_m": 30, "waterbody_width_m": 10},
}


def test_invalid_enum_value_never_reaches_prepared():
    # Exact reproduction of the second-round audit: an application method
    # outside AgDRIFT's registered enum must not satisfy the field's
    # requirement just because a value was supplied.
    with TestClient(app) as client:
        bad_inputs = json.loads(json.dumps(VALID_AGDRIFT_INPUTS))
        bad_inputs["application_parameters"]["application_method"] = "NOT_A_REAL_METHOD"
        workflow = _prepare(client, "AGDRIFT", bad_inputs)
        assert workflow["status"] != "prepared"
        missing = workflow["manifest"]["missing_inputs"]
        assert any("invalid option" in item for item in missing), missing


def test_nan_and_infinity_strings_never_reach_prepared():
    # Exact reproduction of the second-round audit: float("NaN") and
    # float("Infinity") both succeed in Python without raising, so a naive
    # try/except ValueError guard alone is not enough.
    with TestClient(app) as client:
        bad_inputs = json.loads(json.dumps(VALID_AGDRIFT_INPUTS))
        bad_inputs["application_parameters"]["boom_height_m"] = "NaN"
        bad_inputs["application_parameters"]["application_rate_kg_ha"] = "Infinity"
        workflow = _prepare(client, "AGDRIFT", bad_inputs)
        assert workflow["status"] != "prepared"
        missing = workflow["manifest"]["missing_inputs"]
        assert any("finite number" in item for item in missing), missing


def test_pearl_output_completeness_is_enforced():
    # Exact reproduction of the second-round audit: PEARL is not one of the
    # 12 MODEL_PROFILES keys, so validate_external_model_output() previously
    # returned None for it and the review gate's missing-outputs check
    # silently defaulted to an empty list. Prepare with valid required
    # sections, import a file whose structured outputs map none of PEARL's
    # expected_outputs, and confirm acceptance is now refused.
    with TestClient(app) as client:
        workflow = _prepare(client, "PEARL", {
            "application_pattern": {"a": 1}, "soil_dt50": {"a": 1}, "koc_or_kd": {"a": 1},
            "freundlich_exponent": {"a": 1}, "vapour_pressure": {"a": 1}, "water_solubility": {"a": 1},
            "crop_and_scenario": {"a": 1}, "weather_scenario": {"a": 1}, "plant_uptake_coefficient_tscf": {"a": 1},
        }, jurisdiction="EU")
        assert workflow["status"] == "prepared", workflow

        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Adversarial-test unrelated import",
                "structured_outputs_json": json.dumps({"unrelated_key": "unrelated_value"}),
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("unrelated.txt", b"nothing to do with PEARL outputs", "text/plain")},
        )
        assert imported.status_code == 200, imported.text
        validation = imported.json()["output_record"].get("model_specific_validation")
        assert validation is not None, "PEARL must now receive an output-completeness check"
        assert validation["missing_recommended_outputs"], validation

        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "adversarial bypass attempt",
        })
        assert reviewed.status_code == 409, reviewed.text


def test_reviewed_workflow_cannot_be_overwritten_by_a_later_import():
    # Exact reproduction of the second-round audit: a genuinely reviewed
    # AgDRIFT workflow must not be silently revertible to "output_imported"
    # by a subsequent plain-text /import-output call on the same id.
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", VALID_AGDRIFT_INPUTS)
        assert workflow["status"] == "prepared", workflow

        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Genuine import before immutability check",
                "structured_outputs_json": json.dumps({
                    "off_site_deposition_fraction": 0.02, "downwind_deposition_curve": "QA curve",
                }),
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("agdrift_result.txt", b"off_site_deposition_fraction=0.02", "text/plain")},
        )
        assert imported.status_code == 200, imported.text

        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "genuine",
        })
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "reviewed"
        original_output_hash = reviewed.json()["output_hash"]

        reimport_plain = client.post(f"/api/model-workflows/{workflow['id']}/import-output", json={"raw_output_text": "nonsense=1"})
        assert reimport_plain.status_code == 409, reimport_plain.text

        reimport_files = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Attempted overwrite of a closed review record",
                "structured_outputs_json": "{}",
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("overwrite_attempt.txt", b"anything", "text/plain")},
        )
        assert reimport_files.status_code == 409, reimport_files.text

        after = client.get(f"/api/model-workflows/{workflow['id']}")
        assert after.json()["status"] == "reviewed"
        assert after.json()["output_hash"] == original_output_hash


def test_reviewed_workflow_decision_cannot_be_changed_by_a_second_review_call():
    # Exact reproduction of the third-round audit: the import routes were
    # guarded against overwriting a closed workflow, but /review itself was
    # not -- a second /review call (reviewed -> rejected) returned 200 and
    # silently overwrote the reviewer, decision and notes on a closed record.
    with TestClient(app) as client:
        workflow = _prepare(client, "AGDRIFT", VALID_AGDRIFT_INPUTS)
        assert workflow["status"] == "prepared", workflow

        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Genuine import before double-review check",
                "structured_outputs_json": json.dumps({
                    "off_site_deposition_fraction": 0.02, "downwind_deposition_curve": "QA curve",
                }),
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("agdrift_result.txt", b"off_site_deposition_fraction=0.02", "text/plain")},
        )
        assert imported.status_code == 200, imported.text

        first_review = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "genuine",
        })
        assert first_review.status_code == 200, first_review.text
        assert first_review.json()["status"] == "reviewed"

        second_review = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA2", "decision": "rejected", "notes": "changed my mind",
        })
        assert second_review.status_code == 409, second_review.text

        after = client.get(f"/api/model-workflows/{workflow['id']}")
        assert after.json()["status"] == "reviewed"
        assert after.json()["reviewer"] == "QA"
        assert after.json()["review_notes"] == "genuine"


def test_boolean_value_never_satisfies_a_numeric_field():
    # Exact reproduction of the third-round audit: bool is a subclass of int
    # in Python, so float(True) == 1.0 succeeds without raising -- a naive
    # try/except (TypeError, ValueError) guard around float() alone lets a
    # JSON boolean silently satisfy a numeric field's requirement.
    with TestClient(app) as client:
        bad_inputs = json.loads(json.dumps(VALID_AGDRIFT_INPUTS))
        bad_inputs["application_parameters"]["boom_height_m"] = True
        workflow = _prepare(client, "AGDRIFT", bad_inputs)
        assert workflow["status"] != "prepared"
        missing = workflow["manifest"]["missing_inputs"]
        assert any("boom_height_m" in item and "must be numeric" in item for item in missing), missing


def test_toxswa_optional_time_series_does_not_block_acceptance():
    # Exact reproduction of the third-round audit: TOXSWA's expected_outputs
    # includes "time_series_if_requested", which is conditional on the
    # operator actually requesting a time-series export. The generic
    # output-completeness fallback for models outside MODEL_PROFILES
    # previously treated every entry in a contract's expected_outputs as
    # unconditionally mandatory, blocking acceptance of a genuine run that
    # simply never requested a time series.
    with TestClient(app) as client:
        workflow = _prepare(client, "TOXSWA", {
            "contaminant_group": "pesticide",
            "spin_substance_record": {"a": 1}, "swash_surface_water_scenario": {"a": 1},
            "application_pattern": {"a": 1}, "drift_deposition": {"a": 1},
            "macro_m2t_or_przm_p2t_when_applicable": {"a": 1}, "water_and_sediment_dt50": {"a": 1},
            "freundlich_sorption_parameters": {"a": 1},
            "molar_mass_vapour_pressure_solubility_diffusion": {"a": 1},
            "metabolite_scheme_if_applicable": {"a": 1},
        }, jurisdiction="EU", tier=3)
        assert workflow["status"] == "prepared", workflow

        imported = client.post(
            f"/api/model-workflows/{workflow['id']}/import-output-files",
            data={
                "model_version": "QA build", "executable_version": "QA build",
                "operator": "QA operator", "execution_notes": "Genuine run, no time series requested",
                "structured_outputs_json": json.dumps({
                    "global_max_pecsw": 0.01, "global_max_pecsed": 0.02, "twaecsw": 0.005, "twaecsed": 0.006,
                    "water_mass_balance": "balanced", "sediment_mass_balance": "balanced",
                }),
                "confirm_genuine_execution": "true", "confirm_authorised_installation": "true",
            },
            files={"files": ("toxswa_result.sum", b"global_max_pecsw=0.01", "text/plain")},
        )
        assert imported.status_code == 200, imported.text
        validation = imported.json()["output_record"]["model_specific_validation"]
        assert validation["missing_recommended_outputs"] == [], validation
        assert "time_series_if_requested" in validation["recommended_structured_outputs"]

        reviewed = client.post(f"/api/model-workflows/{workflow['id']}/review", json={
            "reviewer": "QA", "decision": "accepted", "notes": "genuine, no time series requested",
        })
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "reviewed"
