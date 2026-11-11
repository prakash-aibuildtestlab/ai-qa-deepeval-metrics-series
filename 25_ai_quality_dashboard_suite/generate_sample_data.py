import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"


def write_json(file_name, payload):
    file_path = DATA_DIR / file_name

    file_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    return file_path


def build_pre_release_results():
    return {
        "source_stage": "pre_release_evaluation",
        "evaluation_run_id": "EVAL-2026-11-12-001",
        "evaluation_status": "COMPLETED",
        "total_tests": 8,
        "passed": 8,
        "failed": 0,
        "errors": 0,
        "pass_rate": 1.0,
        "critical_tests": 4,
        "critical_failures": 0,
        "metrics": {
            "knowledge_retention": 1.0,
            "turn_relevancy": 1.0,
            "conversation_completeness": 1.0,
            "role_adherence": 1.0,
        },
        "quality_status": "PASS",
    }


def build_cicd_results():
    return {
        "source_stage": "cicd_quality_gate",
        "pipeline_id": "PIPELINE-2026-11-12-001",
        "pipeline_status": "COMPLETED",
        "release_gate": "PASS",
        "total_test_executions": 20,
        "passed": 20,
        "failed": 0,
        "errors": 0,
        "pass_rate": 1.0,
        "stages": {
            "smoke": {
                "tests": 4,
                "passed": 4,
                "pass_rate": 1.0,
                "result": "PASS",
            },
            "critical": {
                "tests": 4,
                "passed": 4,
                "pass_rate": 1.0,
                "result": "PASS",
            },
            "safety": {
                "tests": 4,
                "passed": 4,
                "pass_rate": 1.0,
                "result": "PASS",
            },
            "regression": {
                "tests": 8,
                "passed": 8,
                "pass_rate": 1.0,
                "result": "PASS",
            },
        },
        "blocking_reasons": [],
    }


def build_production_results():
    return {
        "source_stage": "production_monitoring",
        "window_id": "degraded-2026-11-11",
        "monitoring_status": "ALERT",
        "total_events": 12,
        "operational_metrics": {
            "error_rate": 0.0833,
            "p95_latency_ms": 6200,
            "negative_feedback_rate": 0.5833,
        },
        "safety_metrics": {
            "policy_violations": 6,
            "pii_incidents": 1,
            "unsupported_action_claims": 1,
        },
        "semantic_metrics": {
            "answer_relevancy": 0.75,
            "faithfulness": 0.0,
            "prompt_alignment": 0.6,
            "semantic_pass_rate": 0.3333,
        },
        "alerts": {
            "total": 12,
            "critical": 3,
            "high": 5,
            "medium": 4,
            "low": 0,
        },
        "critical_alert_types": [
            "policy_violation",
            "pii_incident",
            "unsupported_action_claim",
        ],
    }


def build_human_review_results():
    return {
        "source_stage": "human_review",
        "review_status": "COMPLETED",
        "reviews_applied": 1,
        "pending_reviews": 0,
        "automated_semantic_pass_rate": 0.8,
        "adjudicated_semantic_pass_rate": 1.0,
        "evaluator_false_positives": 1,
        "evaluator_false_negatives": 0,
        "reviews": [
            {
                "event_id": "HEALTHY-018",
                "automated_verdict": "FAIL",
                "human_verdict": "PASS",
                "final_verdict": "PASS",
                "classification": "evaluator_false_positive",
                "reviewer_role": "AI QA reviewer",
                "reason": (
                    "The response complied with the approved "
                    "address-change policy."
                ),
            }
        ],
    }


def build_regression_feedback_results():
    return {
        "source_stage": "production_regression_feedback",
        "source_window_id": "degraded-2026-11-11",
        "total_regression_cases": 7,
        "critical_cases": 2,
        "high_cases": 5,
        "medium_cases": 0,
        "low_cases": 0,
        "ready_for_next_release": 7,
        "cases": [
            {
                "test_id": "PROD-REG-001",
                "source_event_id": "DEGRADED-002",
                "severity": "high",
                "risk_types": [
                    "policy_risk",
                    "grounded_response_semantic_failure",
                ],
            },
            {
                "test_id": "PROD-REG-002",
                "source_event_id": "DEGRADED-003",
                "severity": "high",
                "risk_types": [
                    "policy_risk",
                    "grounded_response_semantic_failure",
                ],
            },
            {
                "test_id": "PROD-REG-003",
                "source_event_id": "DEGRADED-004",
                "severity": "critical",
                "risk_types": [
                    "pii_incident",
                    "policy_risk",
                    "grounded_response_semantic_failure",
                ],
            },
            {
                "test_id": "PROD-REG-004",
                "source_event_id": "DEGRADED-005",
                "severity": "critical",
                "risk_types": [
                    "unsupported_action_claim",
                    "policy_risk",
                    "grounded_response_semantic_failure",
                ],
            },
            {
                "test_id": "PROD-REG-005",
                "source_event_id": "DEGRADED-006",
                "severity": "high",
                "risk_types": [
                    "policy_risk",
                    "role_boundary_semantic_failure",
                ],
            },
            {
                "test_id": "PROD-REG-006",
                "source_event_id": "DEGRADED-007",
                "severity": "high",
                "risk_types": [
                    "application_error",
                ],
            },
            {
                "test_id": "PROD-REG-007",
                "source_event_id": "DEGRADED-010",
                "severity": "high",
                "risk_types": [
                    "policy_risk",
                    "role_boundary_semantic_failure",
                ],
            },
        ],
    }


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "pre_release_results.json": (
            build_pre_release_results()
        ),
        "cicd_quality_gate_results.json": (
            build_cicd_results()
        ),
        "production_monitoring_results.json": (
            build_production_results()
        ),
        "human_review_results.json": (
            build_human_review_results()
        ),
        "regression_feedback_results.json": (
            build_regression_feedback_results()
        ),
    }

    print("AI Quality Dashboard — Sample Data Generation")
    print("=" * 70)

    for file_name, payload in outputs.items():
        file_path = write_json(file_name, payload)
        print(f"Generated: {file_path}")

    print("=" * 70)
    print(f"Data files generated: {len(outputs)}")


if __name__ == "__main__":
    main()