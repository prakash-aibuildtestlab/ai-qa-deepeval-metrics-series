import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from generate_quality_dashboard import (
    build_quality_summary,
    load_json,
    render_html_dashboard,
)


ROOT = Path(__file__).resolve().parent


def load_test_inputs():
    config = load_json(
        ROOT / "dashboard_config.json"
    )

    sources = config["data_sources"]

    return {
        "config": config,
        "pre_release": load_json(
            ROOT / sources["pre_release"]
        ),
        "cicd": load_json(
            ROOT / sources["cicd"]
        ),
        "production": load_json(
            ROOT / sources["production"]
        ),
        "human_review": load_json(
            ROOT / sources["human_review"]
        ),
        "regression_feedback": load_json(
            ROOT / sources["regression_feedback"]
        ),
    }


def build_sample_summary():
    inputs = load_test_inputs()

    return build_quality_summary(
        config=inputs["config"],
        pre_release=inputs["pre_release"],
        cicd=inputs["cicd"],
        production=inputs["production"],
        human_review=inputs["human_review"],
        regression_feedback=(
            inputs["regression_feedback"]
        ),
    )


def test_degraded_production_blocks_quality_decision():
    summary = build_sample_summary()

    assert summary["overall_decision"] == "BLOCK"

    assert (
        summary["check_summary"]["blocking_failures"]
        == 3
    )


def test_expected_blocking_reasons_are_reported():
    summary = build_sample_summary()

    blocking_check_ids = {
        reason["check_id"]
        for reason in summary["blocking_reasons"]
    }

    assert blocking_check_ids == {
        "CHECK-009",
        "CHECK-010",
        "CHECK-011",
    }


def test_pre_release_and_cicd_can_pass_while_production_fails():
    summary = build_sample_summary()
    lifecycle = summary["lifecycle_summary"]

    assert lifecycle["pre_release_status"] == "PASS"
    assert lifecycle["cicd_release_gate"] == "PASS"
    assert lifecycle["production_status"] == "ALERT"

    assert summary["overall_decision"] == "BLOCK"


def test_quality_score_uses_blocking_weights():
    summary = build_sample_summary()

    assert summary["quality_score"] == 41.18

    assert summary["check_summary"] == {
        "total": 12,
        "passed": 5,
        "failed": 7,
        "blocking_failures": 3,
    }


def test_non_blocking_failures_create_conditional_decision():
    inputs = load_test_inputs()
    production = deepcopy(inputs["production"])

    production["alerts"]["critical"] = 0
    production["safety_metrics"]["pii_incidents"] = 0

    production["safety_metrics"][
        "unsupported_action_claims"
    ] = 0

    summary = build_quality_summary(
        config=inputs["config"],
        pre_release=inputs["pre_release"],
        cicd=inputs["cicd"],
        production=production,
        human_review=inputs["human_review"],
        regression_feedback=(
            inputs["regression_feedback"]
        ),
    )

    assert summary["overall_decision"] == "CONDITIONAL"

    assert (
        summary["check_summary"]["blocking_failures"]
        == 0
    )

    assert summary["check_summary"]["failed"] > 0


def test_healthy_results_create_approve_decision():
    inputs = load_test_inputs()
    production = deepcopy(inputs["production"])

    production["monitoring_status"] = "HEALTHY"

    production["operational_metrics"].update(
        {
            "error_rate": 0.01,
            "p95_latency_ms": 1800,
            "negative_feedback_rate": 0.05,
        }
    )

    production["semantic_metrics"].update(
        {
            "answer_relevancy": 1.0,
            "faithfulness": 0.95,
            "prompt_alignment": 0.95,
            "semantic_pass_rate": 0.9,
        }
    )

    production["safety_metrics"].update(
        {
            "policy_violations": 0,
            "pii_incidents": 0,
            "unsupported_action_claims": 0,
        }
    )

    production["alerts"].update(
        {
            "total": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
    )

    summary = build_quality_summary(
        config=inputs["config"],
        pre_release=inputs["pre_release"],
        cicd=inputs["cicd"],
        production=production,
        human_review=inputs["human_review"],
        regression_feedback=(
            inputs["regression_feedback"]
        ),
    )

    assert summary["overall_decision"] == "APPROVE"
    assert summary["quality_score"] == 100.0
    assert summary["blocking_reasons"] == []


def test_html_dashboard_contains_governance_results(
    tmp_path,
):
    summary = build_sample_summary()
    output_path = tmp_path / "quality_dashboard.html"

    render_html_dashboard(
        summary,
        output_path,
    )

    dashboard_html = output_path.read_text(
        encoding="utf-8"
    )

    assert output_path.exists()
    assert "AI Quality Governance Dashboard" in dashboard_html
    assert "Overall quality decision" in dashboard_html
    assert "BLOCK" in dashboard_html
    assert "Production PII incidents" in dashboard_html
    assert "Unsupported action claims" in dashboard_html

def test_reporting_mode_returns_zero_exit_code():
    result = subprocess.run(
        [
            sys.executable,
            "generate_quality_dashboard.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0

    assert (
        "Overall decision: BLOCK"
        in result.stdout
    )

    assert (
        "Quality gate enforcement: "
        "NOT REQUESTED (reporting mode)"
        in result.stdout
    )


def test_enforcement_mode_returns_one_for_block():
    result = subprocess.run(
        [
            sys.executable,
            "generate_quality_dashboard.py",
            "--enforce-gate",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1

    assert (
        "Overall decision: BLOCK"
        in result.stdout
    )

    assert (
        "BLOCK returned exit code 1"
        in result.stdout
    )