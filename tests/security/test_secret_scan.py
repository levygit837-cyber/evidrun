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
