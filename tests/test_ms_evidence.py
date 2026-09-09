"""Tests for the mzML metabolite/transformation-product evidence workbench.

The fixture below is a minimal, hand-built, schema-valid mzML document (one
MS1 scan, one MS2 scan referencing it) rather than a real instrument export --
small enough to reason about exactly, while still exercising the real
pyteomics parsing path this module relies on, not a mock of it.
"""
from __future__ import annotations

import base64
import struct
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ms_evidence import MzMLParseError, parse_mzml, sha256_of, workbench_capabilities


def _encode_f32(values: list[float]) -> str:
    return base64.b64encode(struct.pack(f"<{len(values)}f", *values)).decode("ascii")


def build_mzml(
    *,
    ms1_mz: list[float] = (100.0, 237.1022, 300.0),
    ms1_intensity: list[float] = (50.0, 900.0, 25.0),
    ms2_precursor_mz: float = 237.1022,
    ms2_mz: list[float] = (194.096, 179.073),
    ms2_intensity: list[float] = (800.0, 300.0),
    ms1_rt_min: float = 0.50,
    ms2_rt_min: float = 0.55,
) -> bytes:
    ms1_mz, ms1_intensity, ms2_mz, ms2_intensity = list(ms1_mz), list(ms1_intensity), list(ms2_mz), list(ms2_intensity)
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<indexedmzML xmlns="http://psi.hupo.org/ms/mzml">
<mzML xmlns="http://psi.hupo.org/ms/mzml" version="1.1.0" id="test">
  <cvList count="1"><cv id="MS" fullName="PSI-MS" URI="https://example.invalid/psi-ms.obo"/></cvList>
  <fileDescription><fileContent><cvParam cvRef="MS" accession="MS:1000579" name="MS1 spectrum" value=""/></fileContent></fileDescription>
  <softwareList count="1"><software id="sw" version="1.0"><cvParam cvRef="MS" accession="MS:1000799" name="custom unreleased software tool" value="testgen"/></software></softwareList>
  <instrumentConfigurationList count="1"><instrumentConfiguration id="IC1"><cvParam cvRef="MS" accession="MS:1000483" name="Thermo Fisher Scientific instrument model" value=""/></instrumentConfiguration></instrumentConfigurationList>
  <dataProcessingList count="1"><dataProcessing id="dp1"><processingMethod order="1" softwareRef="sw"><cvParam cvRef="MS" accession="MS:1000544" name="Conversion to mzML" value=""/></processingMethod></dataProcessing></dataProcessingList>
  <run id="run1" defaultInstrumentConfigurationRef="IC1">
    <spectrumList count="2" defaultDataProcessingRef="dp1">
      <spectrum index="0" id="scan=1" defaultArrayLength="{len(ms1_mz)}">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
        <cvParam cvRef="MS" accession="MS:1000130" name="positive scan" value=""/>
        <scanList count="1"><cvParam cvRef="MS" accession="MS:1000795" name="no combination" value=""/>
          <scan><cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{ms1_rt_min}" unitCvRef="UO" unitAccession="UO:0000031" unitName="minute"/></scan>
        </scanList>
        <binaryDataArrayList count="2">
          <binaryDataArray encodedLength="0"><cvParam cvRef="MS" accession="MS:1000521" name="32-bit float" value=""/><cvParam cvRef="MS" accession="MS:1000576" name="no compression" value=""/><cvParam cvRef="MS" accession="MS:1000514" name="m/z array" unitCvRef="MS" unitAccession="MS:1000040" unitName="m/z"/><binary>{_encode_f32(ms1_mz)}</binary></binaryDataArray>
          <binaryDataArray encodedLength="0"><cvParam cvRef="MS" accession="MS:1000521" name="32-bit float" value=""/><cvParam cvRef="MS" accession="MS:1000576" name="no compression" value=""/><cvParam cvRef="MS" accession="MS:1000515" name="intensity array" unitCvRef="MS" unitAccession="MS:1000131" unitName="number of counts"/><binary>{_encode_f32(ms1_intensity)}</binary></binaryDataArray>
        </binaryDataArrayList>
      </spectrum>
      <spectrum index="1" id="scan=2" defaultArrayLength="{len(ms2_mz)}">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="2"/>
        <cvParam cvRef="MS" accession="MS:1000130" name="positive scan" value=""/>
        <scanList count="1"><cvParam cvRef="MS" accession="MS:1000795" name="no combination" value=""/>
          <scan><cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{ms2_rt_min}" unitCvRef="UO" unitAccession="UO:0000031" unitName="minute"/></scan>
        </scanList>
        <precursorList count="1">
          <precursor spectrumRef="scan=1">
            <selectedIonList count="1"><selectedIon>
              <cvParam cvRef="MS" accession="MS:1000744" name="selected ion m/z" value="{ms2_precursor_mz}" unitCvRef="MS" unitAccession="MS:1000040" unitName="m/z"/>
              <cvParam cvRef="MS" accession="MS:1000041" name="charge state" value="1"/>
            </selectedIon></selectedIonList>
            <activation><cvParam cvRef="MS" accession="MS:1000045" name="collision energy" value="20" unitCvRef="UO" unitAccession="UO:0000266" unitName="electronvolt"/></activation>
          </precursor>
        </precursorList>
        <binaryDataArrayList count="2">
          <binaryDataArray encodedLength="0"><cvParam cvRef="MS" accession="MS:1000521" name="32-bit float" value=""/><cvParam cvRef="MS" accession="MS:1000576" name="no compression" value=""/><cvParam cvRef="MS" accession="MS:1000514" name="m/z array" unitCvRef="MS" unitAccession="MS:1000040" unitName="m/z"/><binary>{_encode_f32(ms2_mz)}</binary></binaryDataArray>
          <binaryDataArray encodedLength="0"><cvParam cvRef="MS" accession="MS:1000521" name="32-bit float" value=""/><cvParam cvRef="MS" accession="MS:1000576" name="no compression" value=""/><cvParam cvRef="MS" accession="MS:1000515" name="intensity array" unitCvRef="MS" unitAccession="MS:1000131" unitName="number of counts"/><binary>{_encode_f32(ms2_intensity)}</binary></binaryDataArray>
        </binaryDataArrayList>
      </spectrum>
    </spectrumList>
  </run>
</mzML>
</indexedmzML>
'''
    return xml.encode("utf-8")


def test_parse_mzml_extracts_ms1_tic_and_ms2_feature_with_xic():
    result = parse_mzml(build_mzml())
    assert result["ms1_scan_count"] == 1
    assert result["ms2_scan_count"] == 1
    assert result["ionisation_mode"] == "positive"
    assert result["tic"] == [{"retention_time_min": 0.5, "intensity": 975.0}]

    [feature] = result["features"]
    assert feature["precursor_mz"] == pytest.approx(237.1022, abs=1e-3)
    assert feature["precursor_charge"] == 1
    assert feature["collision_energy"] == 20.0
    assert feature["retention_time_min"] == pytest.approx(0.55, abs=1e-6)
    # Product ions sorted by intensity descending, not scan order.
    assert [ion["intensity"] for ion in feature["product_ions"]] == [800.0, 300.0]
    assert feature["base_peak_mz"] == pytest.approx(194.096, abs=1e-3)
    # The MS1 scan does carry the 237.1022 precursor mass -- the XIC must find it.
    [xic_point] = feature["xic"]
    assert xic_point["intensity"] == pytest.approx(900.0, abs=1e-6)


def test_parse_mzml_xic_excludes_out_of_tolerance_mass():
    # Precursor mass not present anywhere in the MS1 scan (only 100/237.1022/300 are) --
    # the XIC for an unrelated precursor mz must come back as zero, not a false match.
    result = parse_mzml(build_mzml(ms2_precursor_mz=150.0))
    [feature] = result["features"]
    [xic_point] = feature["xic"]
    assert xic_point["intensity"] == 0.0


def test_parse_mzml_rejects_garbage_input():
    with pytest.raises(MzMLParseError):
        parse_mzml(b"this is not xml at all")


def test_parse_mzml_rejects_empty_run():
    empty = b'''<?xml version="1.0"?><indexedmzML xmlns="http://psi.hupo.org/ms/mzml">
<mzML xmlns="http://psi.hupo.org/ms/mzml" version="1.1.0" id="empty">
<run id="r"><spectrumList count="0"></spectrumList></run></mzML></indexedmzML>'''
    with pytest.raises(MzMLParseError):
        parse_mzml(empty)


def test_workbench_capabilities_discloses_scope_boundary():
    caps = workbench_capabilities()
    assert "confirmed structure" in " ".join(caps["does_not_provide"]).lower() or any(
        "confirmed" in item for item in caps["does_not_provide"]
    )
    assert "Schymanski" in caps["confidence_framework"]


def _unique_rt() -> float:
    """A retention time unlikely to collide with a prior test run's content hash.

    This project has no fixture-reset DB between runs (see other test files'
    uuid4() use for the same reason) -- a fixed literal here would 409 on
    content-hash conflict the second time the suite runs.
    """
    return 0.5 + (uuid4().int % 10_000) / 1_000_000


def _project_and_chemical(client: TestClient) -> tuple[int, int]:
    project = client.post("/api/projects", json={"name": f"MS evidence QA {uuid4().hex[:8]}", "jurisdiction": "EU"}).json()
    chemical = next(row for row in client.get("/api/chemicals").json() if row["preferred_name"] == "Carbamazepine")
    return project["id"], chemical["id"]


def test_import_route_persists_raw_file_and_features():
    with TestClient(app) as client:
        project_id, chemical_id = _project_and_chemical(client)
        response = client.post(
            "/api/ms-evidence/import",
            files={"mzml_file": ("sample.mzML", build_mzml(ms2_rt_min=_unique_rt()), "application/xml")},
            data={"project_id": project_id, "chemical_id": chemical_id},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ms1_scan_count"] == 1
        assert payload["ms2_scan_count"] == 1
        assert len(payload["features"]) == 1
        file_id = payload["id"]
        feature_id = payload["features"][0]["id"]

        listed = client.get("/api/ms-evidence/files", params={"project_id": project_id}).json()
        assert any(row["id"] == file_id for row in listed)

        detail = client.get(f"/api/ms-evidence/features/{feature_id}").json()
        assert detail["product_ions"][0]["intensity"] == 800.0
        assert len(detail["xic"]) == 1


def test_duplicate_import_is_rejected_by_content_hash():
    with TestClient(app) as client:
        raw = build_mzml(ms2_rt_min=_unique_rt())
        first = client.post("/api/ms-evidence/import", files={"mzml_file": ("a.mzML", raw, "application/xml")})
        assert first.status_code == 200
        second = client.post("/api/ms-evidence/import", files={"mzml_file": ("a-renamed.mzML", raw, "application/xml")})
        assert second.status_code == 409


def test_review_endpoint_records_reviewer_confidence_level():
    with TestClient(app) as client:
        imported = client.post(
            "/api/ms-evidence/import",
            files={"mzml_file": ("review-case.mzML", build_mzml(ms2_rt_min=_unique_rt()), "application/xml")},
        ).json()
        feature_id = imported["features"][0]["id"]
        assert imported["features"][0]["confidence_level"] == "feature_of_interest"

        response = client.patch(
            f"/api/ms-evidence/features/{feature_id}/review",
            json={"confidence_level": "tentative_candidate", "reviewer_note": "Matches predicted hydroxylation TP mass."},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["confidence_level"] == "tentative_candidate"
        assert body["reviewer_note"] == "Matches predicted hydroxylation TP mass."

        refetched = client.get(f"/api/ms-evidence/features/{feature_id}").json()
        assert refetched["confidence_level"] == "tentative_candidate"


def test_review_endpoint_rejects_unknown_confidence_level():
    with TestClient(app) as client:
        imported = client.post(
            "/api/ms-evidence/import",
            files={"mzml_file": ("bad-level.mzML", build_mzml(ms2_rt_min=_unique_rt()), "application/xml")},
        ).json()
        feature_id = imported["features"][0]["id"]
        response = client.patch(
            f"/api/ms-evidence/features/{feature_id}/review",
            json={"confidence_level": "definitely_confirmed_trust_me"},
        )
        assert response.status_code == 422


def test_sha256_of_is_deterministic():
    raw = build_mzml()
    assert sha256_of(raw) == sha256_of(raw)
    assert sha256_of(raw) != sha256_of(build_mzml(ms2_precursor_mz=999.0))
