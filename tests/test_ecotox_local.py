"""Tests for the local EPA ECOTOX reference connector and its importer helpers."""

from __future__ import annotations

import json

import pytest

from app.services.ecotox_local import is_imported, search_ecotox_local
from scripts.import_ecotox import format_cas


def test_format_cas_inserts_dashes_in_correct_positions():
    assert format_cas("50000") == "50-00-0"
    assert format_cas("1336363") == "1336-36-3"


def test_format_cas_rejects_non_digit_or_too_short_input():
    assert format_cas("") is None
    assert format_cas("NR") is None
    assert format_cas("1") is None


def _write_fixture(tmp_path, records):
    jsonl_path = tmp_path / "ecotox_reference.jsonl"
    index: dict[str, list[int]] = {}
    offset = 0
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            line = json.dumps(record) + "\n"
            index.setdefault(record["cas_number"], []).append(offset)
            handle.write(line)
            offset += len(line.encode("utf-8"))
    index_path = tmp_path / "ecotox_index.json"
    index_path.write_text(
        json.dumps({"record_count": len(records), "chemical_count": len(index), "offsets": index}),
        encoding="utf-8",
    )
    return jsonl_path, index_path


_SAMPLE_RECORD = {
    "cas_number": "50-00-0",
    "chemical_name": "Formaldehyde",
    "dtxsid": "DTXSID7020637",
    "endpoint": "EC50",
    "effect": "ENZ",
    "measurement": "GENZ",
    "response_site": "NR",
    "conc1_mean": 39000.0,
    "conc1_unit": "ug/L",
    "obs_duration_mean": 1.0,
    "obs_duration_unit": "h",
    "species_common_name": "Water Flea",
    "species_latin_name": "Daphnia magna",
    "species_ecotox_group": "Crustaceans;Standard Test Species",
    "media_type": "FW",
    "exposure_type": "S",
    "study_duration_mean": None,
    "study_duration_unit": "NC",
    "test_location": "LAB",
    "reference_author": "Janssen,C.R., and G. Persoone",
    "reference_title": "Rapid Toxicity Screening Tests for Aquatic Biota",
    "reference_source": "Environ. Toxicol. Chem.12:711-717",
    "reference_year": "1993",
    "reference_doi": None,
    "result_id": "118291",
    "test_id": "1083681",
    "source_key": "epa_ecotox",
    "source_url": "https://cfpub.epa.gov/ecotox/",
}


def test_search_returns_not_imported_status_when_files_absent(tmp_path):
    result = search_ecotox_local(
        "Formaldehyde", cas_number="50-00-0",
        jsonl_path=tmp_path / "missing.jsonl", index_path=tmp_path / "missing.json",
    )
    assert result["status"] == "not_imported"
    assert result["candidates"] == []
    assert "import_ecotox.py" in result["warnings"][0]


def test_is_imported_reflects_file_presence(tmp_path):
    jsonl_path, index_path = _write_fixture(tmp_path, [_SAMPLE_RECORD])
    assert is_imported(index_path, jsonl_path) is True
    assert is_imported(tmp_path / "nope.json", tmp_path / "nope.jsonl") is False


def test_search_requires_cas_number(tmp_path):
    jsonl_path, index_path = _write_fixture(tmp_path, [_SAMPLE_RECORD])
    result = search_ecotox_local(
        "Formaldehyde", cas_number=None, jsonl_path=jsonl_path, index_path=index_path,
    )
    assert result["status"] == "cas_number_required"


def test_search_returns_no_match_for_unknown_cas(tmp_path):
    jsonl_path, index_path = _write_fixture(tmp_path, [_SAMPLE_RECORD])
    result = search_ecotox_local(
        "Some Other Chemical", cas_number="999-99-9", jsonl_path=jsonl_path, index_path=index_path,
    )
    assert result["status"] == "no_match"
    assert result["candidates"] == []


def test_search_finds_real_candidate_and_maps_endpoint_to_property_code(tmp_path):
    jsonl_path, index_path = _write_fixture(tmp_path, [_SAMPLE_RECORD])
    result = search_ecotox_local(
        "Formaldehyde", cas_number="50-00-0", jsonl_path=jsonl_path, index_path=index_path,
    )
    assert result["status"] == "ok"
    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["property_code"] == "ECOTOX.AQUATIC.EC50"
    assert candidate["value"] == pytest.approx(39000.0)
    assert candidate["unit"] == "ug/L"
    assert candidate["cas_number"] == "50-00-0"
    assert candidate["source_key"] == "epa_ecotox"
    assert candidate["needs_professional_review"] is True
    assert "Daphnia magna" in candidate["snippet"]


def test_search_filters_by_requested_endpoint_codes(tmp_path):
    noec_record = dict(_SAMPLE_RECORD, endpoint="NOEC", result_id="999999")
    jsonl_path, index_path = _write_fixture(tmp_path, [_SAMPLE_RECORD, noec_record])

    only_noec = search_ecotox_local(
        "Formaldehyde", cas_number="50-00-0", endpoint_codes=["ECOTOX.AQUATIC.NOEC"],
        jsonl_path=jsonl_path, index_path=index_path,
    )
    assert len(only_noec["candidates"]) == 1
    assert only_noec["candidates"][0]["property_code"] == "ECOTOX.AQUATIC.NOEC"


def test_search_respects_limit(tmp_path):
    records = [dict(_SAMPLE_RECORD, result_id=str(i)) for i in range(5)]
    jsonl_path, index_path = _write_fixture(tmp_path, records)
    result = search_ecotox_local(
        "Formaldehyde", cas_number="50-00-0", limit=2, jsonl_path=jsonl_path, index_path=index_path,
    )
    assert len(result["candidates"]) == 2
    assert result["total_available"] == 5


# ---- unit basis advisory (found by a random-chemical validation run over 3,140 real ECOTOX candidates) ----
from app.services.ecotox_local import unit_advisory


@pytest.mark.parametrize("unit", ["ug/L", "mg/L", "ng/L", "g/L", "ppm", "ppb", "ug/ml", "AI ug/L", "AI mg/L"])
def test_aqueous_mass_concentration_units_carry_no_advisory(unit):
    assert unit_advisory(unit) is None


@pytest.mark.parametrize("unit", ["mM", "uM", "mmol/L", "M", "AI mM"])
def test_molar_units_say_they_need_a_molecular_weight(unit):
    text = unit_advisory(unit)
    assert text is not None and "MOLAR" in text and "molecular weight" in text


@pytest.mark.parametrize("unit", ["mg/kg bdwt", "g/kg diet", "neq/g", "%", "ug/cell", "mg/kg", "lb/acre", "ml/L"])
def test_non_aqueous_units_are_flagged_as_not_a_pnec_input(unit):
    text = unit_advisory(unit)
    assert text is not None and "NOT AN AQUEOUS CONCENTRATION" in text and "PNEC" in text


def test_missing_unit_is_flagged():
    assert "UNIT NOT REPORTED" in unit_advisory(None)
    assert "UNIT NOT REPORTED" in unit_advisory("  ")


def test_candidate_notes_carry_the_unit_advisory_and_keep_the_record(tmp_path):
    record = dict(_SAMPLE_RECORD, conc1_unit="g/kg diet", conc1_mean=12.0)
    jsonl_path, index_path = _write_fixture(tmp_path, [record])
    result = search_ecotox_local("Formaldehyde", cas_number="50-00-0", jsonl_path=jsonl_path, index_path=index_path)
    assert len(result["candidates"]) == 1  # never dropped
    notes = result["candidates"][0]["notes"]
    assert notes.startswith("NOT AN AQUEOUS CONCENTRATION") and "species:" in notes


def test_candidate_with_an_aqueous_unit_has_no_advisory_prefix(tmp_path):
    record = dict(_SAMPLE_RECORD, conc1_unit="mg/L")
    jsonl_path, index_path = _write_fixture(tmp_path, [record])
    result = search_ecotox_local("Formaldehyde", cas_number="50-00-0", jsonl_path=jsonl_path, index_path=index_path)
    assert result["candidates"][0]["notes"].startswith("species:")
