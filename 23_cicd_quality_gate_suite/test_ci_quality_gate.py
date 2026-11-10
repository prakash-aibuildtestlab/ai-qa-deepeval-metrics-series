import json
from pathlib import Path

import pytest

import generate_ci_summary as ci_summary


CONFIG_FILE = (
    Path(__file__).resolve().parent
    / "quality_gate_config.json"
)


def load_config() -> dict:
    with CONFIG_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def create_pytest_report(
    base_directory: Path,
    stage: dict,
    *,
    total: int,
    passed: int,
    failed: int = 0,
    errors: int = 0,
    skipped: int = 0,
    exit_code: int = 0,
) -> Path:
    report_path = (
        base_directory
        / stage["report_file"]
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "exitcode": exit_code,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "error": errors,
            "skipped": skipped,
        },
    }

    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    return report_path


@pytest.fixture
def config() -> dict:
    return load_config()


@pytest.fixture
def smoke_stage(config: dict) -> dict:
    return next(
        stage
        for stage in config["stages"]
        if stage["name"] == "smoke"
    )


def test_configuration_contains_required_stages(
    config: dict,
) -> None:
    stage_names = {
        stage["name"]
        for stage in config["stages"]
    }

    assert stage_names == {
        "smoke",
        "critical",
        "safety",
        "regression",
    }


def test_all_release_stages_are_blocking(
    config: dict,
) -> None:
    assert all(
        stage["blocking"]
        for stage in config["stages"]
    )


def test_all_blocking_stages_require_complete_pass(
    config: dict,
) -> None:
    blocking_stages = [
        stage
        for stage in config["stages"]
        if stage["blocking"]
    ]

    assert blocking_stages

    assert all(
        stage["minimum_pass_rate"] == 1.0
        for stage in blocking_stages
    )


def test_complete_stage_pass_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    smoke_stage: dict,
) -> None:
    monkeypatch.setattr(
        ci_summary,
        "MODULE_DIR",
        tmp_path,
    )

    create_pytest_report(
        tmp_path,
        smoke_stage,
        total=4,
        passed=4,
    )

    result = ci_summary.calculate_stage_result(
        smoke_stage
    )

    assert result["result"] == "PASS"
    assert result["pass_rate"] == 1.0
    assert result["reasons"] == []


def test_partial_pass_blocks_release_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    smoke_stage: dict,
) -> None:
    monkeypatch.setattr(
        ci_summary,
        "MODULE_DIR",
        tmp_path,
    )

    create_pytest_report(
        tmp_path,
        smoke_stage,
        total=8,
        passed=7,
        failed=1,
        exit_code=1,
    )

    result = ci_summary.calculate_stage_result(
        smoke_stage
    )

    assert result["result"] == "BLOCK"
    assert result["pass_rate"] == pytest.approx(
        0.875
    )
    assert any(
        "below the required" in reason
        for reason in result["reasons"]
    )


def test_missing_report_blocks_release_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    smoke_stage: dict,
) -> None:
    monkeypatch.setattr(
        ci_summary,
        "MODULE_DIR",
        tmp_path,
    )

    result = ci_summary.calculate_stage_result(
        smoke_stage
    )

    assert result["result"] == "BLOCK"
    assert result["report_found"] is False
    assert result["reasons"] == [
        "Pytest JSON report was not found."
    ]


def test_pytest_error_blocks_release_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    smoke_stage: dict,
) -> None:
    monkeypatch.setattr(
        ci_summary,
        "MODULE_DIR",
        tmp_path,
    )

    create_pytest_report(
        tmp_path,
        smoke_stage,
        total=4,
        passed=3,
        errors=1,
        exit_code=1,
    )

    result = ci_summary.calculate_stage_result(
        smoke_stage
    )

    assert result["result"] == "BLOCK"
    assert result["errors"] == 1
    assert any(
        "test error" in reason
        for reason in result["reasons"]
    )


def test_zero_tests_blocks_release_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    smoke_stage: dict,
) -> None:
    monkeypatch.setattr(
        ci_summary,
        "MODULE_DIR",
        tmp_path,
    )

    create_pytest_report(
        tmp_path,
        smoke_stage,
        total=0,
        passed=0,
    )

    result = ci_summary.calculate_stage_result(
        smoke_stage
    )

    assert result["result"] == "BLOCK"
    assert any(
        "No tests were executed" in reason
        for reason in result["reasons"]
    )