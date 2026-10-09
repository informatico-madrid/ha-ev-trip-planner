"""Regression checks for reproducible lint policy and real CI reports."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.layer3a_summary import main

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("source", "status", "diagnostic"),
    [
        (
            "from typing import Optional\n\ndef same(value: Optional[str]) -> Optional[str]:\n    return value\n",
            0,
            "All checks passed",
        ),
        ("print(undefined_name)\n", 1, "F821"),
        ("import unused_module\n", 1, "F401"),
    ],
)
def test_ruff_policy_is_stable_and_still_rejects_errors(
    tmp_path, source, status, diagnostic
):
    path = tmp_path / "example.py"
    path.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(ROOT / "pyproject.toml"),
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == status, result.stderr
    assert diagnostic in result.stdout


@pytest.mark.parametrize(("passed", "failed", "status"), [(25, 0, 0), (24, 1, 1)])
def test_antipattern_summary_reports_findings(tmp_path, capsys, passed, failed, status):
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "tier_a_summary": {
                    "passed": passed,
                    "failed": failed,
                    "total": passed + failed,
                }
            }
        ),
        encoding="utf-8",
    )
    assert main(str(report)) == status
    assert f"{failed} with findings" in capsys.readouterr().out


def test_missing_antipattern_report_is_an_execution_error(tmp_path, capsys):
    assert main(str(tmp_path / "missing.json")) == 2
    assert "Invalid Layer 3A report" in capsys.readouterr().err


def test_essential_ci_keeps_functional_checks_and_advanced_checks_remain_local():
    ci = subprocess.run(
        ["make", "-n", "quality-gate-ci", "PYTEST_WORKERS=2"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    local = subprocess.run(
        ["make", "-n", "layer3a"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "ruff check custom_components/" in ci
    assert "pyright --pythonpath" in ci
    assert "pytest tests/unit tests/integration" in ci
    for tool in (
        "pylint",
        "solid_metrics.py",
        "principles_checker.py",
        "antipattern_checker.py",
    ):
        assert tool not in ci
        assert tool in local
    assert "security_scanner.py" not in ci
