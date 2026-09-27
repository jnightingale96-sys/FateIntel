"""OPERA local predicted-property fallback: mocked subprocess calls throughout, so tests never depend on a real
OPERA/PaDEL/MATLAB Runtime install or invoke a real subprocess.

The real, live-verified recipe (see the module docstring and SOIL_DT50_PROVIDER_NOTES.md) is: run PaDEL ourselves
for 2D descriptors and for fingerprints, align the two CSVs by molecule name, then call OPERA with -d/-fp -- never
OPERA's own -s/SMILES mode, which hangs indefinitely on this build. These tests exercise that plumbing directly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.services import opera_local as o

CARBAMAZEPINE = "NC(=O)N1c2ccccc2C=Cc2ccccc21"
ETHANOL = "CCO"


@pytest.fixture
def toolchain_dir(tmp_path):
    """A fake OPERA install: OPERA.exe + its bundled PaDEL jar/xml, all empty placeholder files."""

    app_dir = tmp_path / "app" / "application"
    app_dir.mkdir(parents=True)
    exe = app_dir / "OPERA.exe"
    exe.write_bytes(b"")
    (app_dir / "padel-full-1.00.jar").write_bytes(b"")
    (app_dir / "desc_fp.xml").write_text("<Root/>", encoding="utf-8")
    return exe


def _settings(exe_path: Path, **overrides) -> Settings:
    return Settings(_env_file=None, opera_exe_path=str(exe_path), **overrides)


# ------------------------------------------------------------------------------------------------- toolchain / capabilities

def test_paths_requires_the_bundled_padel_jar_and_desc_fp_xml_next_to_opera_exe(tmp_path, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "/usr/bin/java")
    bare_exe = tmp_path / "OPERA.exe"
    bare_exe.write_bytes(b"")  # no padel jar / desc_fp.xml alongside it
    with pytest.raises(o.OperaUnavailableError, match="PaDEL jar"):
        o._paths(_settings(bare_exe))


def test_paths_requires_java_on_path(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: None)
    with pytest.raises(o.OperaUnavailableError, match="java"):
        o._paths(_settings(toolchain_dir))


def test_paths_succeeds_and_reports_the_whole_toolchain(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "/usr/bin/java")
    toolchain = o._paths(_settings(toolchain_dir))
    assert toolchain.opera_exe == toolchain_dir
    assert toolchain.padel_jar.name == "padel-full-1.00.jar"
    assert toolchain.desc_fp_xml.name == "desc_fp.xml"
    assert toolchain.java_exe == "/usr/bin/java"


def test_capabilities_reports_unavailable_reason_without_raising(tmp_path):
    caps = o.capabilities(Settings(_env_file=None, opera_exe_path=None))
    assert caps["available"] is False and caps["executable_found"] is False
    assert "OPERA_EXE_PATH" in caps["reason"]


def test_capabilities_disabled_by_configuration_takes_precedence(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "/usr/bin/java")
    caps = o.capabilities(_settings(toolchain_dir, opera_enabled=False))
    assert caps["enabled"] is False and caps["available"] is False
    assert caps["reason"] == "disabled by configuration"


def test_capabilities_reports_padel_jar_and_java_when_available(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "/usr/bin/java")
    caps = o.capabilities(_settings(toolchain_dir))
    assert caps["available"] is True
    assert caps["padel_jar"].endswith("padel-full-1.00.jar")
    assert caps["java_executable"] == "/usr/bin/java"


# ------------------------------------------------------------------------------------------------------ parsing (unchanged)

def test_parse_output_row_converts_log_biodeg_half_life_to_days_and_reads_ad_flags():
    row = {
        "LogP_pred": "2.45", "LogP_predRange": "[2.1:2.8]", "AD_LogP": "1", "AD_index_LogP": "0.9", "Conf_index_LogP": "0.8",
        "BioDeg_LogHalfLife_pred": "1.0", "BioDeg_predRange": "[0.5:1.5]", "AD_BioDeg": "0", "AD_index_BioDeg": "0.3", "Conf_index_BioDeg": "0.4",
    }
    parsed = o.parse_output_row(row)
    assert parsed["logp"]["value"] == pytest.approx(2.45) and parsed["logp"]["applicability_domain"] == "inside"
    assert parsed["biodeg_half_life"]["value"] == pytest.approx(10.0) and parsed["biodeg_half_life"]["unit"] == "days"
    assert parsed["biodeg_half_life"]["applicability_domain"] == "outside"
    assert parsed["pka_a"] is None and parsed["pka_b"] is None  # not present in this row -> never guessed


# --------------------------------------------------------------------------------------------------- _align_by_name

def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def test_align_by_name_inner_joins_and_preserves_the_requested_order(tmp_path):
    csv_2d = tmp_path / "2d.csv"
    csv_fp = tmp_path / "fp.csv"
    _write_csv(csv_2d, ["Name", "ALogP"], [["m1", "1.1"], ["m0", "0.0"], ["m2", "2.2"]])
    _write_csv(csv_fp, ["Name", "FP1"], [["m0", "0"], ["m2", "1"]])  # m1 missing from the fingerprints output

    aligned_2d, aligned_fp = tmp_path / "a2d.csv", tmp_path / "afp.csv"
    matched = o._align_by_name(csv_2d, csv_fp, aligned_2d, aligned_fp, order=["m0", "m1", "m2"])

    assert matched == ["m0", "m2"]  # m1 dropped (present in only one PaDEL output), order preserved otherwise
    assert aligned_2d.read_text(encoding="utf-8").strip().splitlines() == ["Name,ALogP", "m0,0.0", "m2,2.2"]
    assert aligned_fp.read_text(encoding="utf-8").strip().splitlines() == ["Name,FP1", "m0,0", "m2,1"]


def test_align_by_name_returns_empty_when_nothing_is_common_to_both(tmp_path):
    csv_2d = tmp_path / "2d.csv"
    csv_fp = tmp_path / "fp.csv"
    _write_csv(csv_2d, ["Name", "ALogP"], [["m0", "0.0"]])
    _write_csv(csv_fp, ["Name", "FP1"], [["m1", "1"]])
    matched = o._align_by_name(csv_2d, csv_fp, tmp_path / "a2d.csv", tmp_path / "afp.csv", order=["m0", "m1"])
    assert matched == []


# ---------------------------------------------------------------------------------------- _run_opera / predict (mocked subprocess)

class _FakeCompleted(SimpleNamespace):
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _fake_subprocess_run_factory(*, opera_returns_fail=False, opera_missing_output=False):
    """A drop-in for subprocess.run that branches on which real command it was given, and writes the CSV that
    real command would have written -- so _run_opera's full plumbing (PaDEL x2 -> align -> OPERA -> parse) runs
    for real, with only the three external processes themselves faked out."""

    def _fake_run(command, **kwargs):
        exe = str(command[0])
        if exe.endswith("java") or exe.endswith("java.exe"):
            out_csv = Path(command[command.index("-file") + 1])
            fingerprints = "-fingerprints" in command
            smi_file = Path(command[command.index("-dir") + 1])
            ids = [line.split("\t")[1].strip() for line in smi_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            if fingerprints:
                _write_csv(out_csv, ["Name", "FP1"], [[mol_id, "1"] for mol_id in ids])
            else:
                _write_csv(out_csv, ["Name", "ALogP"], [[mol_id, "1.0"] for mol_id in ids])
            return _FakeCompleted(returncode=0, stdout="", stderr="")
        # OPERA itself
        out_csv = Path(command[command.index("-o") + 1])
        aligned_2d = Path(command[command.index("-d") + 1])
        ids = [row.split(",")[0] for row in aligned_2d.read_text(encoding="utf-8").splitlines()[1:] if row.strip()]
        if opera_returns_fail:
            return _FakeCompleted(returncode=1, stdout="simulated OPERA failure\n", stderr="")
        if opera_missing_output:
            return _FakeCompleted(returncode=0, stdout="", stderr="")  # no file written
        header = "MoleculeID,LogP_pred,LogP_predRange,AD_LogP,AD_index_LogP,Conf_index_LogP"
        rows = [f"{mol_id},2.5,[2.0:3.0],1,0.9,0.8" for mol_id in ids]
        out_csv.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
        return _FakeCompleted(returncode=0, stdout="", stderr="")

    return _fake_run


def test_run_opera_full_pipeline_padel_then_align_then_opera(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "java")
    monkeypatch.setattr(o.subprocess, "run", _fake_subprocess_run_factory())
    results = o._run_opera([CARBAMAZEPINE, ETHANOL], _settings(toolchain_dir))
    assert set(results) == {CARBAMAZEPINE, ETHANOL}
    assert results[CARBAMAZEPINE]["logp"]["value"] == pytest.approx(2.5)
    assert results[CARBAMAZEPINE]["logp"]["applicability_domain"] == "inside"


def test_run_opera_raises_a_clear_error_when_opera_itself_fails(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "java")
    monkeypatch.setattr(o.subprocess, "run", _fake_subprocess_run_factory(opera_returns_fail=True))
    with pytest.raises(o.OperaRunError, match="OPERA exited with code 1"):
        o._run_opera([CARBAMAZEPINE], _settings(toolchain_dir))


def test_run_opera_raises_when_opera_produces_no_output_file(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "java")
    monkeypatch.setattr(o.subprocess, "run", _fake_subprocess_run_factory(opera_missing_output=True))
    with pytest.raises(o.OperaRunError, match="no output file"):
        o._run_opera([CARBAMAZEPINE], _settings(toolchain_dir))


def test_run_padel_raises_on_timeout_not_a_hang(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "java")

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 1))

    monkeypatch.setattr(o.subprocess, "run", _timeout)
    with pytest.raises(o.OperaRunError, match="did not finish within"):
        o._run_opera([CARBAMAZEPINE], _settings(toolchain_dir))


def test_predict_caches_by_canonical_smiles_and_skips_a_second_real_run(toolchain_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "java")
    calls = {"n": 0}
    fake = _fake_subprocess_run_factory()

    def _counting_run(*args, **kwargs):
        calls["n"] += 1
        return fake(*args, **kwargs)

    monkeypatch.setattr(o.subprocess, "run", _counting_run)
    cache_path = tmp_path / "cache.json"
    first = o.predict([CARBAMAZEPINE], _settings(toolchain_dir), cache_path=cache_path)
    calls_after_first = calls["n"]
    second = o.predict([CARBAMAZEPINE], _settings(toolchain_dir), cache_path=cache_path)
    assert calls["n"] == calls_after_first  # nothing re-run: served from the on-disk cache
    assert first[CARBAMAZEPINE]["logp"]["value"] == second[CARBAMAZEPINE]["logp"]["value"]


def test_predict_raises_unavailable_before_running_anything_when_not_configured():
    with pytest.raises(o.OperaUnavailableError):
        o.predict([CARBAMAZEPINE], Settings(_env_file=None, opera_exe_path=None))


def test_predict_raises_when_disabled_by_configuration(toolchain_dir, monkeypatch):
    monkeypatch.setattr(o.shutil, "which", lambda name: "java")
    with pytest.raises(o.OperaUnavailableError, match="disabled"):
        o.predict([CARBAMAZEPINE], _settings(toolchain_dir, opera_enabled=False))


# ---------------------------------------------------------------------------------------------------------------- API routes

def test_capabilities_and_predict_routes(toolchain_dir, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(o.shutil, "which", lambda name: "java")
    monkeypatch.setattr(o.subprocess, "run", _fake_subprocess_run_factory())
    monkeypatch.setattr(o.settings, "opera_exe_path", str(toolchain_dir))
    monkeypatch.setattr(o, "CACHE_PATH", toolchain_dir.parent / "route_cache.json")

    with TestClient(app) as client:
        caps = client.get("/api/providers/opera/capabilities")
        result = client.post("/api/providers/opera/predict", json={"smiles": [CARBAMAZEPINE]})
    assert caps.status_code == 200 and caps.json()["available"] is True
    assert result.status_code == 200
    body = result.json()
    assert body["results"][0]["smiles"] == CARBAMAZEPINE
    assert body["results"][0]["prediction"]["logp"]["value"] == pytest.approx(2.5)


def test_predict_route_returns_503_when_unavailable(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(o.settings, "opera_exe_path", None)
    with TestClient(app) as client:
        result = client.post("/api/providers/opera/predict", json={"smiles": [CARBAMAZEPINE]})
    assert result.status_code == 503
