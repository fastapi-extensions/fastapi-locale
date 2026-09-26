"""Fixtures that run real processes: a Uvicorn server and the command line tool."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest

EXAMPLE = Path(__file__).parents[2] / "examples" / "basic"
STARTUP_TIMEOUT = 20.0


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``fastapi-locale`` in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "fastapi_locale.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.fixture
def cli() -> Callable[..., subprocess.CompletedProcess[str]]:
    """The command line tool as a function."""
    return run_cli


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Serve a copy of the example application with Uvicorn and return its base URL."""
    project = tmp_path_factory.mktemp("example") / "basic"
    shutil.copytree(EXAMPLE, project, ignore=shutil.ignore_patterns("*.mo", "__pycache__"))
    assert run_cli("compile", cwd=project).returncode == 0

    port = _free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port), "--log-level", "warning"],
        cwd=project,
        env={**os.environ, "PYTHONPATH": str(project)},
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + STARTUP_TIMEOUT
    try:
        while True:
            try:
                httpx.get(base_url, timeout=1.0)
                break
            except httpx.TransportError:
                if process.poll() is not None or time.monotonic() > deadline:
                    pytest.fail("the example server did not start")
                time.sleep(0.1)
        yield base_url
    finally:
        process.terminate()
        process.wait(timeout=10)
