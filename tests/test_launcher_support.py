import io
import json
from pathlib import Path
import socket

import pytest

from app import launcher_support


class _Response:
    def __init__(self, payload: dict, status: int = 200):
        self.status = status
        self._body = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body.read()


def test_matching_build_requires_exact_build_identifier(monkeypatch):
    monkeypatch.setattr(
        launcher_support,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"build_id": "expected-build"}),
    )
    assert launcher_support.matching_envirochem_build(8792, "expected-build") is True
    assert launcher_support.matching_envirochem_build(8792, "different-build") is False


def test_port_probe_and_alternate_port_selection():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        occupied_port = listener.getsockname()[1]
        listener.listen()
        assert launcher_support.port_is_available(occupied_port) is False

        if occupied_port == 65535:
            pytest.skip("No higher TCP port is available for this boundary case")
        alternate = launcher_support.find_available_port(occupied_port, attempts=20)

    assert alternate > occupied_port
    assert launcher_support.port_is_available(alternate) is True


def test_launcher_avoids_quoted_for_f_command_path_bug():
    launcher = (
        Path(launcher_support.__file__).resolve().parents[1]
        / "START_ENVIROCHEM_CONSOLE.cmd"
    ).read_text(encoding="utf-8")
    assert "for /f" not in launcher.lower()
    assert 'setlocal EnableExtensions EnableDelayedExpansion' in launcher
    assert 'set /p "PORT="<"!PORT_FILE!"' in launcher


def test_browser_readiness_helper_does_not_share_server_log_handle():
    launcher = (
        Path(launcher_support.__file__).resolve().parents[1]
        / "START_ENVIROCHEM_CONSOLE.cmd"
    ).read_text(encoding="utf-8")
    readiness_line = next(
        line
        for line in launcher.splitlines()
        if line.lstrip().lower().startswith('start "" /b')
        and "open-when-ready" in line
    )
    uvicorn_line = next(
        line for line in launcher.splitlines() if "-m uvicorn app.main:app" in line
    )

    assert '>>"%LOG%"' not in readiness_line
    assert readiness_line.lower().endswith(">nul 2>&1")
    assert '>>"%LOG%" 2>&1' in uvicorn_line


def test_wait_for_ready_opens_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(
        launcher_support,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"status": "ready"}),
    )
    monkeypatch.setattr(
        launcher_support.webbrowser,
        "open",
        lambda url, new=0: opened.append((url, new)),
    )

    assert launcher_support.wait_for_ready_and_open(
        8792,
        "http://127.0.0.1:8792/",
    ) is True
    assert opened == [("http://127.0.0.1:8792/", 2)]


def test_wait_for_ready_validates_port():
    with pytest.raises(ValueError, match="port"):
        launcher_support.wait_for_ready_and_open(0, "http://127.0.0.1/")
