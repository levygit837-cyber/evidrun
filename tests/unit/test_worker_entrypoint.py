"""The supervised executor takes its data dir off stdin, never argv.

A database path in argv is readable by every other process on the machine, which the
WS-02 brief forbids. These pin the handshake that avoids it, and the readiness banner the
supervisor waits on — a malformed or secret-bearing banner is how `ready` would start
meaning nothing.
"""

from __future__ import annotations

import io
import json
from collections.abc import Coroutine
from pathlib import Path

import pytest

from evidrun.entrypoints.worker import app as worker_app
from evidrun.entrypoints.worker.app import (
    WORKER_PROTOCOL,
    announce_ready,
    build_parser,
    read_handshake,
)
from evidrun.settings import Settings


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


def test_readiness_banner_carries_no_path(capsys: pytest.CaptureFixture[str]) -> None:
    """The regression guard: readiness must not carry a path field back out.

    Asserting on the field set, not on a path the function never saw: `announce_ready`
    takes only a worker id, so comparing against some unrelated temp dir would pass no
    matter what the banner contained.
    """

    announce_ready("host:1:worker_01")
    message = json.loads(capsys.readouterr().out)
    assert set(message) == {"protocol", "schema_version", "pid", "worker_id"}


def test_main_uses_the_handshake_dir_not_argv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`main` must prefer the stdin dir; reading argv instead is the whole bug.

    Nothing else covers that wiring, so `main` could quietly go back to `--data-dir` and
    every other test here would still pass.
    """

    handshake_dir = tmp_path / "handshake"
    handshake_dir.mkdir()
    monkeypatch.setattr(
        "sys.argv", ["evidrun-worker", "--desktop-handshake", "--data-dir", str(tmp_path)]
    )
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"data_dir": str(handshake_dir)}) + "\n")
    )
    seen: list[Path | None] = []
    load = Settings.load

    def capture(data_dir: Path | None) -> Settings:
        seen.append(data_dir)
        return load(data_dir)

    def skip_polling(coroutine: Coroutine[object, object, None]) -> None:
        """Stand in for `asyncio.run`, closing the coroutine so it is never awaited.

        Returning rather than raising lets `main` reach its `finally` and dispose the
        database it opened.
        """

        coroutine.close()

    monkeypatch.setattr("evidrun.entrypoints.worker.app.Settings.load", capture)
    monkeypatch.setattr("evidrun.entrypoints.worker.app.asyncio.run", skip_polling)
    worker_app.main()
    assert seen and seen[0] == handshake_dir


def test_handshake_with_once_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """A supervisor waiting on readiness that `--once` never sends would time out.

    Refusing loudly beats completing in silence and letting the supervisor report a
    failure that did not happen.
    """

    monkeypatch.setattr("sys.argv", ["evidrun-worker", "--desktop-handshake", "--once"])
    with pytest.raises(SystemExit) as refusal:
        worker_app.main()
    assert refusal.value.code == 2


def test_desktop_handshake_is_opt_in() -> None:
    """A terminal keeps using `--data-dir`; only a supervisor asks for the handshake."""

    assert build_parser().parse_args([]).desktop_handshake is False
    assert build_parser().parse_args(["--desktop-handshake"]).desktop_handshake is True
