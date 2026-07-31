from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_secrets.py"
FIXTURES = ROOT / "tests" / "security" / "fixtures"
CONFIG = FIXTURES / "secret-scan-test.toml"


def run_scan(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (
            sys.executable,
            str(SCRIPT),
            "--root",
            str(ROOT),
            "--config",
            str(CONFIG),
            "--path",
            str(path.relative_to(ROOT)),
        ),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_secret_scanner_reports_location_without_revealing_value() -> None:
    result = run_scan(FIXTURES / "secret-positive.txt")

    assert result.returncode == 1
    assert "security.secret_detected" in result.stderr
    assert "rule=openai-api-key" in result.stderr
    assert "tests/security/fixtures/secret-positive.txt:1:" in result.stderr
    assert "sk-proj-" not in result.stdout
    assert "sk-proj-" not in result.stderr


def test_secret_scanner_accepts_explicit_placeholders_offline() -> None:
    result = run_scan(FIXTURES / "secret-negative.txt")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "secret scan: 1 file(s), 0 finding(s)"


def test_secret_scanner_checks_binary_and_non_utf8_content(tmp_path: Path) -> None:
    config = tmp_path / "secret-scan.toml"
    config.write_text('schema_version = "1"\nallow = []\n', encoding="utf-8")
    candidate = tmp_path / "payload.bin"
    api_key = b"sk-proj-" + b"A" * 32
    candidate.write_bytes(b"\x00\xff" + api_key + b"\n")

    result = subprocess.run(
        (
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--path",
            candidate.name,
        ),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "rule=openai-api-key" in result.stderr
    assert api_key.decode() not in result.stderr


def test_secret_scanner_fails_closed_when_explicit_path_is_missing(tmp_path: Path) -> None:
    config = tmp_path / "secret-scan.toml"
    config.write_text('schema_version = "1"\nallow = []\n', encoding="utf-8")

    result = subprocess.run(
        (
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--config",
            str(config),
            "--path",
            "missing.txt",
        ),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "secret scan configuration error: FileNotFoundError" in result.stderr


def test_secret_scanner_fails_closed_when_tracked_path_is_missing(tmp_path: Path) -> None:
    config = tmp_path / "secret-scan.toml"
    config.write_text('schema_version = "1"\nallow = []\n', encoding="utf-8")
    candidate = tmp_path / "tracked.txt"
    candidate.write_text("safe", encoding="utf-8")
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    subprocess.run(("git", "add", candidate.name), cwd=tmp_path, check=True)
    candidate.unlink()

    result = subprocess.run(
        (sys.executable, str(SCRIPT), "--root", str(tmp_path), "--config", str(config)),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "secret scan configuration error: FileNotFoundError" in result.stderr


def test_secret_scanner_checks_tracked_symlink_content(tmp_path: Path) -> None:
    config = tmp_path / "secret-scan.toml"
    config.write_text('schema_version = "1"\nallow = []\n', encoding="utf-8")
    api_key = "sk-proj-" + "A" * 32
    candidate = tmp_path / "credential-link"
    candidate.symlink_to(api_key)
    subprocess.run(("git", "init", "-q"), cwd=tmp_path, check=True)
    subprocess.run(("git", "add", candidate.name), cwd=tmp_path, check=True)

    result = subprocess.run(
        (sys.executable, str(SCRIPT), "--root", str(tmp_path), "--config", str(config)),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "rule=openai-api-key" in result.stderr
    assert api_key not in result.stderr
