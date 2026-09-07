"""Small, dependency-light helpers used by the Windows launcher.

The commands in this module deliberately avoid importing the FastAPI application.
They can therefore resolve configuration and inspect ports before Uvicorn starts.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
import webbrowser
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .config import settings


def port_is_available(port: int, host: str = "127.0.0.1") -> bool:
    """Return whether a TCP listener can bind to ``host:port``."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        try:
            candidate.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(start: int, attempts: int = 50) -> int:
    """Return the first available port after ``start`` within ``attempts``."""

    if not 1 <= start <= 65535:
        raise ValueError("start must be between 1 and 65535")
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    stop = min(65535, start + attempts)
    for port in range(start + 1, stop + 1):
        if port_is_available(port):
            return port
    raise RuntimeError(f"No available port found after {start} within {attempts} attempts")


def matching_envirochem_build(
    port: int,
    expected_build_id: str,
    *,
    timeout_seconds: float = 1.5,
) -> bool:
    """Return whether ``port`` serves the expected EnviroChem build."""

    try:
        with urlopen(  # noqa: S310 - the launcher probes loopback only
            f"http://127.0.0.1:{port}/api/build",
            timeout=timeout_seconds,
        ) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False
    return payload.get("build_id") == expected_build_id


def wait_for_ready_and_open(
    port: int,
    url: str,
    *,
    timeout_seconds: float = 180.0,
    poll_seconds: float = 1.0,
) -> bool:
    """Wait for the local readiness endpoint and then open ``url``.

    The launcher formerly used a hidden PowerShell polling process. This
    standard-library helper keeps startup within the same Python trust boundary
    as the application and avoids a security-sensitive hidden shell command.
    """

    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if timeout_seconds <= 0 or poll_seconds <= 0:
        raise ValueError("timeout_seconds and poll_seconds must be positive")

    deadline = time.monotonic() + timeout_seconds
    health_url = f"http://127.0.0.1:{port}/api/ready"
    while time.monotonic() < deadline:
        try:
            with urlopen(  # noqa: S310 - the launcher probes loopback only
                health_url,
                timeout=min(2.0, poll_seconds + 1.0),
            ) as response:
                if response.status == 200:
                    webbrowser.open(url, new=2)
                    return True
        except (HTTPError, URLError, TimeoutError, OSError):
            pass
        time.sleep(poll_seconds)
    return False


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EnviroChem launcher support")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("configured-port")

    available = commands.add_parser("port-available")
    available.add_argument("--port", type=int, required=True)

    probe = commands.add_parser("probe-build")
    probe.add_argument("--port", type=int, required=True)
    probe.add_argument("--build", required=True)

    find = commands.add_parser("find-port")
    find.add_argument("--start", type=int, required=True)
    find.add_argument("--attempts", type=int, default=50)

    ready = commands.add_parser("open-when-ready")
    ready.add_argument("--port", type=int, required=True)
    ready.add_argument("--url", required=True)
    ready.add_argument("--timeout", type=float, default=180.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "configured-port":
        print(settings.envirochem_port)
        return 0
    if args.command == "port-available":
        return 0 if port_is_available(args.port) else 1
    if args.command == "probe-build":
        return 0 if matching_envirochem_build(args.port, args.build) else 1
    if args.command == "find-port":
        try:
            print(find_available_port(args.start, args.attempts))
        except (ValueError, RuntimeError) as exc:
            print(str(exc))
            return 1
        return 0
    if args.command == "open-when-ready":
        try:
            opened = wait_for_ready_and_open(args.port, args.url, timeout_seconds=args.timeout)
        except ValueError as exc:
            print(str(exc))
            return 2
        return 0 if opened else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
