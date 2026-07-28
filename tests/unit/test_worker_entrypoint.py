"""The supervised executor takes its data dir off stdin, never argv.

A database path in argv is readable by every other process on the machine, which the
WS-02 brief forbids. These pin the handshake that avoids it, and the readiness banner the
supervisor waits on — a malformed or secret-bearing banner is how `ready` would start
meaning nothing.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from evidrun.entrypoints.worker.app import (
    WORKER_PROTOCOL,
    announce_ready,
    build_parser,
    read_handshake,
)


def test_data_dir_arrives_over_stdin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"data_dir": str(tmp_path)}) + "\n"))
    assert read_handshake() == tmp_path


def test_empty_handshake_falls_back_instead_of_guessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A supervisor that sends nothing usable must not make the worker invent a path."""

    monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
    assert read_handshake() is None


def test_handshake_without_data_dir_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"unrelated": 1}) + "\n"))
    assert read_handshake() is None


def test_readiness_banner_is_the_worker_protocol(capsys: pytest.CaptureFixture[str]) -> None:
    announce_ready("host:1:worker_01")
    message = json.loads(capsys.readouterr().out)
    assert message["protocol"] == WORKER_PROTOCOL
    assert message["schema_version"] == "1"
    assert message["worker_id"] == "host:1:worker_01"
    assert message["pid"] > 0


def test_readiness_banner_carries_no_path(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The regression guard: readiness must not leak the data dir back out."""

    announce_ready("host:1:worker_01")
    assert str(tmp_path) not in capsys.readouterr().out


def test_desktop_handshake_is_opt_in() -> None:
    """A terminal keeps using `--data-dir`; only a supervisor asks for the handshake."""

    assert build_parser().parse_args([]).desktop_handshake is False
    assert build_parser().parse_args(["--desktop-handshake"]).desktop_handshake is True
