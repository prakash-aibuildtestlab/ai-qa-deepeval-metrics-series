from pathlib import Path

from apply_human_reviews import apply_human_reviews
from create_regression_cases import create_regression_dataset
from monitor_production import (
    load_json,
    load_jsonl,
    monitor_production,
)


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"


def test_healthy_window_has_no_deterministic_alerts():
    config = load_json(
        ROOT / "monitoring_config.json"
    )
    baseline = load_json(
        ROOT / "production_baseline.json"
    )
    events = load_jsonl(
        DATA_DIR / "healthy_production_events.jsonl"
    )

    report = monitor_production(
        events=events,
        source_file=(
            DATA_DIR / "healthy_production_events.jsonl"
        ),
        config=config,
        baseline=baseline,
        semantic_enabled=False,
        model="gpt-4o-mini",
    )

    assert report["monitoring_status"] == "HEALTHY"
    assert report["alert_count"] == 0

    assert (
        report["operational_metrics"]["error_rate"]
        == 0
    )

    assert (
        report["safety_metrics"]["pii_incidents"]
        == 0
    )


def test_degraded_window_generates_expected_alerts():
    config = load_json(
        ROOT / "monitoring_config.json"
    )
    baseline = load_json(
        ROOT / "production_baseline.json"
    )
    events = load_jsonl(
        DATA_DIR / "degraded_production_events.jsonl"
    )

    report = monitor_production(
        events=events,
        source_file=(
            DATA_DIR / "degraded_production_events.jsonl"
        ),
        config=config,
        baseline=baseline,
        semantic_enabled=False,
        model="gpt-4o-mini",
    )

    alert_types = {
        alert["alert_type"]
        for alert in report["alerts"]
    }

    expected_alert_types = {
        "policy_violation",
        "pii_incident",
        "unsupported_action_claim",
        "error_rate",
        "latency",
        "negative_feedback",
        "intent_drift",
        "unknown_intent_rate",
    }

    assert report["monitoring_status"] == "ALERT"

    assert expected_alert_types.issubset(
        alert_types
    )


def test_human_review_corrects_evaluator_false_positive():
    report = load_json(
        REPORTS_DIR / "healthy_monitoring_routed.json"
    )

    reviews = load_json(
        ROOT / "human_review_labels.json"
    )

    adjudicated = apply_human_reviews(
        report,
        reviews,
    )

    semantic = adjudicated["semantic_evaluation"]

    assert semantic["human_reviews_applied"] == 1

    assert (
        semantic["automated_semantic_pass_rate"]
        == 0.8
    )

    assert (
        semantic["adjudicated_semantic_pass_rate"]
        == 1.0
    )

    reviewed_event = next(
        result
        for result in semantic["results"]
        if result["event_id"] == "HEALTHY-018"
    )

    assert (
        reviewed_event["automated_overall_result"]
        == "FAIL"
    )

    assert (
        reviewed_event["adjudicated_overall_result"]
        == "PASS"
    )

    assert (
        reviewed_event["human_review"]["classification"]
        == "evaluator_false_positive"
    )


def test_confirmed_failures_become_regression_cases():
    events = load_jsonl(
        DATA_DIR / "degraded_production_events.jsonl"
    )

    monitoring_report = load_json(
        REPORTS_DIR / "degraded_monitoring_routed.json"
    )

    dataset = create_regression_dataset(
        events,
        monitoring_report,
    )

    cases = dataset["regression_cases"]

    source_event_ids = {
        case["source_event_id"]
        for case in cases
    }

    assert dataset["total_regression_cases"] == 7

    assert source_event_ids == {
        "DEGRADED-002",
        "DEGRADED-003",
        "DEGRADED-004",
        "DEGRADED-005",
        "DEGRADED-006",
        "DEGRADED-007",
        "DEGRADED-010",
    }

    critical_cases = {
        case["source_event_id"]
        for case in cases
        if case["severity"] == "critical"
    }

    assert critical_cases == {
        "DEGRADED-004",
        "DEGRADED-005",
    }


def test_regression_dataset_contains_no_raw_payment_data():
    dataset = load_json(
        DATA_DIR / "production_regression_cases.json"
    )

    pii_case = next(
        case
        for case in dataset["regression_cases"]
        if case["source_event_id"] == "DEGRADED-004"
    )

    stored_output = pii_case[
        "actual_production_output"
    ]

    assert "4111 1111 1111 1111" not in stored_output
    assert "4111111111111111" not in stored_output

    assert (
        "redacted" in stored_output.lower()
        or "masked" in stored_output.lower()
    )