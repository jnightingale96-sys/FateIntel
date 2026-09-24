import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services import analytical_identification as ai


CARBAMAZEPINE_INCHIKEY = "FFGPTBGBLSHEPO-UHFFFAOYSA-N"
UNKNOWN_INCHIKEY = "ZZZZZZZZZZZZZZ-UHFFFAOYSA-N"


def sample_massbank_record(*, accession="MSBNK-TEST-QA0001", ion_mode="POSITIVE"):
    return {
        "accession": accession,
        "title": "Carbamazepine; LC-ESI-QFT; MS2",
        "compound": {
            "formula": "C15H12N2O",
            "mass": 236.09496,
            "smiles": "NC(=O)N1c2ccccc2C=Cc2ccccc21",
            "inchi": "InChI=1S/C15H12N2O/...",
        },
        "acquisition": {
            "instrument": "Exploris 480 Orbitrap",
            "instrument_type": "LC-ESI-QFT",
            "mass_spectrometry": {
                "ms_type": "MS2",
                "ion_mode": ion_mode,
                "subtags": [
                    {"subtag": "IONIZATION", "value": "ESI"},
                    {"subtag": "FRAGMENTATION_MODE", "value": "HCD"},
                    {"subtag": "COLLISION_ENERGY", "value": "Ramp 20%-70%"},
                    {"subtag": "RESOLUTION", "value": "30000"},
                ],
            },
            "chromatography": [
                {"subtag": "COLUMN_NAME", "value": "Acquity UPLC BEH C18, 3.0 x 100 mm"},
                {"subtag": "FLOW_RATE", "value": "0.4 mL/min"},
                {"subtag": "RETENTION_TIME", "value": "10.37"},
                {"subtag": "SOLVENT", "value": "A 1mM ammonium fluoride in water"},
                {"subtag": "SOLVENT", "value": "B MeOH"},
            ],
        },
        "mass_spectrometry": {
            "focused_ion": [
                {"subtag": "PRECURSOR_M/Z", "value": "237.102"},
                {"subtag": "PRECURSOR_TYPE", "value": "[M+H]+"},
            ],
        },
        "peak": {
            "numPeak": 2,
            "peak": {
                "header": ["m/z", "int.", "rel."],
                "values": [
                    {"mz": 194.0967, "intensity": 267271264, "rel": 808},
                    {"mz": 237.1025, "intensity": 330135392, "rel": 999},
                ],
            },
        },
    }


@pytest.fixture()
def fixture_reference_data(monkeypatch, tmp_path):
    """Swap the module-level EAWAGTPS/SusDat data for a small deterministic fixture."""
    eawagtps_fixture = {
        CARBAMAZEPINE_INCHIKEY: [
            {
                "tp_name": "Carbamazepine-10,11-epoxide",
                "tp_inchikey": "ZRWWEEVEIOGMMT-UHFFFAOYSA-N",
                "tp_smiles": "NC(=O)N1C2=C(C=CC=C2)C2OC2C2=C1C=CC=C2",
                "tp_formula": "C15H12N2O2",
                "tp_exact_mass_da": 252.0899,
                "tp_cas": "36507-30-9",
                "tp_pubchem_cid": "2555",
                "transformation_type": "epoxidation",
                "ionization": "positive",
                "mass_diff_da": 15.9949,
                "formula_diff": "O1",
                "tanimoto_dissimilarity": 0.11,
                "source_key": "norman_eawagtps",
                "source_record_id": "916",
                "source_url": "https://zenodo.org/records/10628455",
            }
        ]
    }
    monkeypatch.setattr(ai, "_EAWAGTPS_BY_PARENT", eawagtps_fixture)

    susdat_record = {
        "inchikey": CARBAMAZEPINE_INCHIKEY,
        "precursor_m_plus_h_da": 237.102239,
        "precursor_m_minus_h_da": 235.087687,
        "predicted_esi_mode": "Both Polarities",
        "probability_positive_esi": 0.021,
        "probability_negative_esi": 0.0,
        "predicted_chromatography": "RPLC",
        "probability_gc": 0.016,
        "probability_rplc": 0.984,
        "preferable_platform": "RPLC_+ESI",
        "source_key": "norman_susdat",
        "source_url": "https://www.norman-network.com/nds/SLE/",
    }
    data_path = tmp_path / "susdat_fixture.jsonl"
    line = json.dumps(susdat_record) + "\n"
    data_path.write_text(line, encoding="utf-8")
    monkeypatch.setattr(ai, "_SUSDAT_INDEX", {"offsets": {CARBAMAZEPINE_INCHIKEY: 0}})
    monkeypatch.setattr(ai, "SUSDAT_DATA_PATH", data_path)
    return eawagtps_fixture, susdat_record


def test_ionisation_and_platform_returns_reference_values(fixture_reference_data):
    result = ai.ionisation_and_platform(CARBAMAZEPINE_INCHIKEY)
    assert result["found"] is True
    assert result["precursor_m_plus_h_da"] == 237.102239
    assert result["preferable_platform"] == "RPLC_+ESI"
    assert result["evidence_status"] == "model_predicted"


def test_ionisation_and_platform_reports_absence_explicitly(fixture_reference_data):
    result = ai.ionisation_and_platform(UNKNOWN_INCHIKEY)
    assert result["found"] is False
    assert "not in the NORMAN SusDat" in result["message"]


def test_known_transformation_products_returns_curated_pairs(fixture_reference_data):
    result = ai.known_transformation_products(CARBAMAZEPINE_INCHIKEY)
    assert result["found"] is True
    assert result["known_transformation_product_count"] == 1
    tp = result["known_transformation_products"][0]
    assert tp["tp_name"] == "Carbamazepine-10,11-epoxide"
    assert tp["evidence_status"] == "database_curated"


def test_known_transformation_products_reports_absence_explicitly(fixture_reference_data):
    result = ai.known_transformation_products(UNKNOWN_INCHIKEY)
    assert result["found"] is False
    assert result["known_transformation_products"] == []
    assert "No known transformation products" in result["message"]


def test_known_product_ions_normalises_a_real_match():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/MassBank-api/records"
        assert request.url.params["inchi_key"] == CARBAMAZEPINE_INCHIKEY
        return httpx.Response(200, json=[sample_massbank_record()])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, massbank_base_url="https://massbank.example")
    result = ai.known_product_ions(CARBAMAZEPINE_INCHIKEY, configuration=configuration, client=client)
    client.close()

    assert result["found"] is True
    assert result["match_count"] == 1
    spectrum = result["spectra"][0]
    assert spectrum["accession"] == "MSBNK-TEST-QA0001"
    assert spectrum["retention_time_min"] == 10.37
    assert spectrum["column"] == "Acquity UPLC BEH C18, 3.0 x 100 mm"
    assert spectrum["ion_mode"] == "POSITIVE"
    assert spectrum["precursor_mz"] == 237.102
    assert spectrum["product_ion_count"] == 2
    assert spectrum["product_ions"][0]["mz"] == 237.1025
    assert spectrum["evidence_status"] == "database_curated"
    assert spectrum["source_url"] == "https://massbank.eu/MassBank/RecordDisplay?id=MSBNK-TEST-QA0001"


def test_known_product_ions_reports_no_match_without_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, massbank_base_url="https://massbank.example")
    result = ai.known_product_ions(UNKNOWN_INCHIKEY, configuration=configuration, client=client)
    client.close()

    assert result["found"] is False
    assert result["match_count"] == 0
    assert result["spectra"] == []
    assert "No reference product-ion spectrum" in result["message"]


def test_known_product_ions_filters_by_ion_mode():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                sample_massbank_record(accession="MSBNK-TEST-POS", ion_mode="POSITIVE"),
                sample_massbank_record(accession="MSBNK-TEST-NEG", ion_mode="NEGATIVE"),
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, massbank_base_url="https://massbank.example")
    result = ai.known_product_ions(
        CARBAMAZEPINE_INCHIKEY, ion_mode="negative", configuration=configuration, client=client,
    )
    client.close()

    assert result["match_count"] == 1
    assert result["spectra"][0]["accession"] == "MSBNK-TEST-NEG"


def test_known_product_ions_reports_provider_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, massbank_base_url="https://massbank.example")
    from app.exceptions import ExternalDataSourceError

    with pytest.raises(ExternalDataSourceError, match="MassBank search failed"):
        ai.known_product_ions(CARBAMAZEPINE_INCHIKEY, configuration=configuration, client=client)
    client.close()


def test_source_registry_never_marks_licensed_spectral_libraries_as_searchable():
    registry = ai.source_registry()
    licensed = {row["key"]: row for row in registry if row["key"] in {"nist_tandem_ms_library", "mzcloud", "metlin"}}
    assert set(licensed) == {"nist_tandem_ms_library", "mzcloud", "metlin"}
    for row in licensed.values():
        assert row["search_enabled"] is False
        assert row["access_mode"] == "blocked"
        assert row["commercial_status"] == "commercial_licence_required"


def test_analytical_sources_route_lists_registry():
    with TestClient(app) as client:
        response = client.get("/api/analytical-sources")
    assert response.status_code == 200
    keys = {row["key"] for row in response.json()["sources"]}
    assert {"norman_susdat", "norman_eawagtps", "massbank_eu"} <= keys


def test_identification_route_returns_bundled_profile_for_seeded_chemical(monkeypatch):
    stub_profile = {
        "inchikey": CARBAMAZEPINE_INCHIKEY,
        "generated_at": "2026-09-08T00:00:00+00:00",
        "ionisation_and_platform": {"found": True},
        "known_product_ions": {"found": True, "spectra": []},
        "known_transformation_products": {"found": True, "known_transformation_products": []},
    }
    monkeypatch.setattr("app.main.build_identification_profile", lambda *args, **kwargs: stub_profile)

    with TestClient(app) as client:
        chemicals = client.get("/api/chemicals").json()
        carbamazepine = next(row for row in chemicals if row["inchikey"] == CARBAMAZEPINE_INCHIKEY)
        response = client.get(f"/api/chemicals/{carbamazepine['id']}/identification")

    assert response.status_code == 200
    assert response.json()["inchikey"] == CARBAMAZEPINE_INCHIKEY


def test_identification_by_inchikey_route_does_not_require_a_stored_chemical(monkeypatch):
    tp_inchikey = "ZRWWEEVEIOGMMT-UHFFFAOYSA-N"
    stub_profile = {
        "inchikey": tp_inchikey,
        "generated_at": "2026-09-08T00:00:00+00:00",
        "ionisation_and_platform": {"found": False},
        "known_product_ions": {"found": False, "spectra": []},
        "known_transformation_products": {"found": False, "known_transformation_products": []},
    }
    monkeypatch.setattr("app.main.build_identification_profile", lambda *args, **kwargs: stub_profile)

    with TestClient(app) as client:
        response = client.get(f"/api/analytical-identification/{tp_inchikey}")

    assert response.status_code == 200
    assert response.json()["inchikey"] == tp_inchikey


def test_identification_route_404s_for_unknown_chemical():
    with TestClient(app) as client:
        response = client.get("/api/chemicals/999999/identification")
    assert response.status_code == 404


def test_identification_route_422s_when_chemical_has_no_inchikey():
    from uuid import uuid4

    from app.database import SessionLocal
    from app.models import Chemical

    db = SessionLocal()
    try:
        chemical = Chemical(preferred_name=f"No InChIKey Test Chemical QA {uuid4().hex[:8]}", inchikey=None)
        db.add(chemical)
        db.commit()
        chemical_id = chemical.id

        with TestClient(app) as client:
            response = client.get(f"/api/chemicals/{chemical_id}/identification")
        assert response.status_code == 422
    finally:
        db.delete(db.get(Chemical, chemical_id))
        db.commit()
        db.close()


def test_identification_profile_keeps_local_sections_when_massbank_is_down():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal error")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    configuration = Settings(_env_file=None, massbank_base_url="https://massbank.example")
    profile = ai.identification_profile(CARBAMAZEPINE_INCHIKEY, configuration=configuration, client=client)
    client.close()
    ions = profile["known_product_ions"]
    assert ions["found"] is False and ions["unavailable"] is True and ions["spectra"] == []
    assert "not a 'no spectrum' result" in ions["message"] and "HTTP 500" in ions["message"]
    assert profile["known_transformation_products"]["found"] is True  # local EAWAGTPS data is unaffected
    assert profile["ionisation_and_platform"]["found"] is True


def test_transformation_products_route_is_local_only_and_returns_smiles():
    with TestClient(app) as client:
        response = client.get(f"/api/analytical-identification/{CARBAMAZEPINE_INCHIKEY}/transformation-products")
        unknown = client.get(f"/api/analytical-identification/{UNKNOWN_INCHIKEY}/transformation-products")
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True and any(row["tp_name"] == "Carbamazepine-10,11-epoxide" and row["tp_smiles"] for row in body["known_transformation_products"])
    assert unknown.status_code == 200 and unknown.json()["found"] is False
