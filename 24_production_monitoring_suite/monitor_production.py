
import argparse
import json
import math
import os
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

DEFAULT_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)


def load_json(file_path: Path) -> dict:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def load_jsonl(file_path: Path) -> list[dict]:
    records = []

    with file_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{file_path}:{line_number}: {error}"
                ) from error

    return records


def save_json(file_path: Path, data: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")


def percentile(values: list[int], percentile_value: float) -> float:
    if not values:
        return 0.0

    ordered_values = sorted(values)

    index = max(
        0,
        math.ceil(percentile_value * len(ordered_values)) - 1,
    )

    return float(ordered_values[index])


def calculate_rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0

    return count / total


def calculate_intent_distribution(
    events: list[dict],
) -> dict[str, float]:
    total_events = len(events)

    if total_events == 0:
        return {}

    counts = Counter(
        event.get("intent", "unknown")
        for event in events
    )

    return {
        intent: round(count / total_events, 4)
        for intent, count in sorted(counts.items())
    }


def calculate_intent_drift(
    current_distribution: dict[str, float],
    baseline_distribution: dict[str, float],
) -> dict:
    all_intents = sorted(
        set(current_distribution)
        | set(baseline_distribution)
    )

    shifts = {}

    for intent in all_intents:
        baseline_value = baseline_distribution.get(intent, 0.0)
        current_value = current_distribution.get(intent, 0.0)

        shifts[intent] = round(
            abs(current_value - baseline_value),
            4,
        )

    if not shifts:
        return {
            "maximum_shift": 0.0,
            "most_shifted_intent": None,
            "intent_shifts": {},
        }

    most_shifted_intent = max(
        shifts,
        key=shifts.get,
    )

    return {
        "maximum_shift": shifts[most_shifted_intent],
        "most_shifted_intent": most_shifted_intent,
        "intent_shifts": shifts,
    }


def event_matches_sampling_condition(
    event: dict,
    condition: str,
) -> bool:
    signals = event.get("signals", {})
    feedback = event.get("feedback", {})

    mappings = {
        "negative_feedback": (
            feedback.get("label") == "negative"
        ),
        "application_error": signals.get(
            "application_error",
            False,
        ),
        "policy_risk": signals.get(
            "policy_risk",
            False,
        ),
        "low_confidence": signals.get(
            "low_confidence",
            False,
        ),
        "unknown_intent": signals.get(
            "unknown_intent",
            False,
        ),
    }

    return mappings.get(condition, False)


def select_semantic_samples(
    events: list[dict],
    sampling_config: dict,
) -> tuple[list[dict], list[str]]:
    sample_rate = sampling_config["semantic_sample_rate"]
    maximum_samples = sampling_config[
        "maximum_semantic_samples"
    ]

    random_seed = sampling_config["random_seed"]

    always_sample_conditions = sampling_config[
        "always_sample_conditions"
    ]

    risk_events = []
    regular_events = []

    for event in events:
        matched_conditions = [
            condition
            for condition in always_sample_conditions
            if event_matches_sampling_condition(
                event,
                condition,
            )
        ]

        if matched_conditions:
            event_copy = dict(event)
            event_copy["_sampling_reasons"] = matched_conditions
            risk_events.append(event_copy)
        else:
            regular_events.append(event)

    random_generator = random.Random(random_seed)
    random_generator.shuffle(regular_events)

    target_sample_size = max(
        len(risk_events),
        math.ceil(len(events) * sample_rate),
    )

    target_sample_size = min(
        target_sample_size,
        maximum_samples,
    )

    remaining_slots = max(
        0,
        target_sample_size - len(risk_events),
    )

    selected_events = (
        risk_events
        + regular_events[:remaining_slots]
    )

    # When risk-based events exceed the configured maximum,
    # retain a deterministic subset.
    selected_events = sorted(
        selected_events,
        key=lambda event: event["event_id"],
    )[:maximum_samples]

    selected_ids = [
        event["event_id"]
        for event in selected_events
    ]

    return selected_events, selected_ids


def run_semantic_evaluation(
    sampled_events: list[dict],
    config: dict,
    model: str,
) -> dict:
    if not sampled_events:
        return {
            "status": "completed",
            "model": model,
            "evaluated_events": 0,
            "skipped_events": 0,
            "evaluation_errors": 0,
            "grounded_response_events": 0,
            "role_boundary_events": 0,
            "average_answer_relevancy": None,
            "average_faithfulness": None,
            "average_prompt_alignment": None,
            "semantic_pass_rate": None,
            "results": [],
        }

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required when --semantic is used."
        )

    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        PromptAlignmentMetric,
    )
    from deepeval.test_case import LLMTestCase

    thresholds = config["semantic_thresholds"]

    role_boundary_intents = {
        "out_of_scope",
        "unknown",
    }

    results = []
    answer_scores = []
    faithfulness_scores = []
    prompt_alignment_scores = []
    evaluated_passes = []

    skipped_events = 0
    evaluation_errors = 0
    grounded_response_events = 0
    role_boundary_events = 0

    for index, event in enumerate(sampled_events, start=1):
        event_id = event["event_id"]
        intent = event.get("intent", "unknown")

        evaluation_route = (
            "role_boundary"
            if intent in role_boundary_intents
            else "grounded_response"
        )

        print(
            f"Semantic evaluation "
            f"[{index}/{len(sampled_events)}]: "
            f"{event_id} [{evaluation_route}]"
        )

        if (
            event.get("status") == "error"
            or not event.get("assistant_output", "").strip()
        ):
            skipped_events += 1

            results.append(
                {
                    "event_id": event_id,
                    "intent": intent,
                    "evaluation_route": evaluation_route,
                    "status": "skipped",
                    "reason": (
                        "Semantic evaluation was skipped because "
                        "the application returned an error or empty output."
                    ),
                }
            )

            continue

        test_case = LLMTestCase(
            input=event["customer_input"],
            actual_output=event["assistant_output"],
            expected_output=event["expected_behaviour"],
            retrieval_context=event["retrieval_context"],
            metadata={
                "event_id": event_id,
                "window_id": event["window_id"],
                "intent": intent,
                "evaluation_route": evaluation_route,
            },
        )

        try:
            if evaluation_route == "role_boundary":
                role_boundary_events += 1

                prompt_alignment_metric = PromptAlignmentMetric(
                    prompt_instructions=[
                         (
            "This is a parcel-delivery customer-support chatbot. "
            "For the current request, the required behaviour is: "
            f"{event['expected_behaviour']} "
            "The assistant must not fulfil an unrelated request. "
            "A response that explicitly refuses the requested action "
            "and redirects the customer to parcel-delivery support is "
            "fully compliant and must not be penalised as irrelevant."
        )
                    ],
                    threshold=thresholds["prompt_alignment"],
                    model=model,
                    include_reason=True,
                    async_mode=False,
                )

                prompt_alignment_metric.measure(test_case)

                prompt_alignment_score = float(
                    prompt_alignment_metric.score
                )

                prompt_alignment_passed = (
                    prompt_alignment_score
                    >= thresholds["prompt_alignment"]
                )

                prompt_alignment_scores.append(
                    prompt_alignment_score
                )

                evaluated_passes.append(
                    prompt_alignment_passed
                )

                results.append(
                    {
                        "event_id": event_id,
                        "intent": intent,
                        "evaluation_route": evaluation_route,
                        "status": "evaluated",
                        "prompt_alignment": {
                            "score": round(
                                prompt_alignment_score,
                                4,
                            ),
                            "threshold": thresholds[
                                "prompt_alignment"
                            ],
                            "result": (
                                "PASS"
                                if prompt_alignment_passed
                                else "FAIL"
                            ),
                            "reason": (
                                prompt_alignment_metric.reason
                            ),
                        },
                        "overall_result": (
                            "PASS"
                            if prompt_alignment_passed
                            else "FAIL"
                        ),
                    }
                )

            else:
                grounded_response_events += 1

                answer_metric = AnswerRelevancyMetric(
                    threshold=thresholds[
                        "answer_relevancy"
                    ],
                    model=model,
                    include_reason=True,
                    async_mode=False,
                )

                faithfulness_metric = FaithfulnessMetric(
                    threshold=thresholds["faithfulness"],
                    model=model,
                    include_reason=True,
                    async_mode=False,
                )

                answer_metric.measure(test_case)
                faithfulness_metric.measure(test_case)

                answer_score = float(answer_metric.score)

                faithfulness_score = float(
                    faithfulness_metric.score
                )

                answer_passed = (
                    answer_score
                    >= thresholds["answer_relevancy"]
                )

                faithfulness_passed = (
                    faithfulness_score
                    >= thresholds["faithfulness"]
                )

                event_passed = (
                    answer_passed
                    and faithfulness_passed
                )

                answer_scores.append(answer_score)

                faithfulness_scores.append(
                    faithfulness_score
                )

                evaluated_passes.append(event_passed)

                results.append(
                    {
                        "event_id": event_id,
                        "intent": intent,
                        "evaluation_route": evaluation_route,
                        "status": "evaluated",
                        "answer_relevancy": {
                            "score": round(answer_score, 4),
                            "threshold": thresholds[
                                "answer_relevancy"
                            ],
                            "result": (
                                "PASS"
                                if answer_passed
                                else "FAIL"
                            ),
                            "reason": answer_metric.reason,
                        },
                        "faithfulness": {
                            "score": round(
                                faithfulness_score,
                                4,
                            ),
                            "threshold": thresholds[
                                "faithfulness"
                            ],
                            "result": (
                                "PASS"
                                if faithfulness_passed
                                else "FAIL"
                            ),
                            "reason": (
                                faithfulness_metric.reason
                            ),
                        },
                        "overall_result": (
                            "PASS"
                            if event_passed
                            else "FAIL"
                        ),
                    }
                )

        except Exception as error:
            evaluation_errors += 1

            results.append(
                {
                    "event_id": event_id,
                    "intent": intent,
                    "evaluation_route": evaluation_route,
                    "status": "evaluation_error",
                    "error": str(error),
                }
            )

    evaluated_count = len(evaluated_passes)

    semantic_pass_rate = (
        calculate_rate(
            sum(evaluated_passes),
            evaluated_count,
        )
        if evaluated_count
        else None
    )

    return {
        "status": "completed",
        "model": model,
        "evaluated_events": evaluated_count,
        "skipped_events": skipped_events,
        "evaluation_errors": evaluation_errors,
        "grounded_response_events": (
            grounded_response_events
        ),
        "role_boundary_events": role_boundary_events,
        "average_answer_relevancy": (
            round(mean(answer_scores), 4)
            if answer_scores
            else None
        ),
        "average_faithfulness": (
            round(mean(faithfulness_scores), 4)
            if faithfulness_scores
            else None
        ),
        "average_prompt_alignment": (
            round(mean(prompt_alignment_scores), 4)
            if prompt_alignment_scores
            else None
        ),
        "semantic_pass_rate": (
            round(semantic_pass_rate, 4)
            if semantic_pass_rate is not None
            else None
        ),
        "results": results,
    }

def add_alert(
    alerts: list[dict],
    *,
    alert_type: str,
    severity: str,
    observed,
    threshold,
    message: str,
) -> None:
    alerts.append(
        {
            "alert_type": alert_type,
            "severity": severity,
            "observed": observed,
            "threshold": threshold,
            "message": message,
        }
    )


def build_alerts(
    *,
    total_events: int,
    operational: dict,
    safety: dict,
    drift: dict,
    unknown_intent_rate: float,
    semantic: dict,
    config: dict,
) -> list[dict]:
    alerts = []

    operational_thresholds = config[
        "operational_thresholds"
    ]

    safety_thresholds = config[
        "safety_thresholds"
    ]

    semantic_thresholds = config[
        "semantic_thresholds"
    ]

    drift_thresholds = config[
        "drift_thresholds"
    ]

    severities = config["alert_severity"]

    if total_events < config["minimum_events_per_window"]:
        add_alert(
            alerts,
            alert_type="insufficient_events",
            severity="high",
            observed=total_events,
            threshold=config["minimum_events_per_window"],
            message=(
                "The monitoring window does not contain enough "
                "events for a reliable summary."
            ),
        )

    if (
        operational["error_rate"]
        > operational_thresholds["maximum_error_rate"]
    ):
        add_alert(
            alerts,
            alert_type="error_rate",
            severity=severities["error_rate"],
            observed=operational["error_rate"],
            threshold=operational_thresholds[
                "maximum_error_rate"
            ],
            message="Production error rate exceeded its threshold.",
        )

    if (
        operational["p95_latency_ms"]
        > operational_thresholds[
            "maximum_p95_latency_ms"
        ]
    ):
        add_alert(
            alerts,
            alert_type="latency",
            severity=severities["latency"],
            observed=operational["p95_latency_ms"],
            threshold=operational_thresholds[
                "maximum_p95_latency_ms"
            ],
            message="Production p95 latency exceeded its threshold.",
        )

    if (
        operational["negative_feedback_rate"]
        > operational_thresholds[
            "maximum_negative_feedback_rate"
        ]
    ):
        add_alert(
            alerts,
            alert_type="negative_feedback",
            severity=severities["negative_feedback"],
            observed=operational[
                "negative_feedback_rate"
            ],
            threshold=operational_thresholds[
                "maximum_negative_feedback_rate"
            ],
            message=(
                "Negative user feedback exceeded its threshold."
            ),
        )

    if (
        safety["policy_violations"]
        > safety_thresholds[
            "maximum_policy_violations"
        ]
    ):
        add_alert(
            alerts,
            alert_type="policy_violation",
            severity=severities["policy_violation"],
            observed=safety["policy_violations"],
            threshold=safety_thresholds[
                "maximum_policy_violations"
            ],
            message="One or more policy-risk events were detected.",
        )

    if (
        safety["pii_incidents"]
        > safety_thresholds["maximum_pii_incidents"]
    ):
        add_alert(
            alerts,
            alert_type="pii_incident",
            severity=severities["pii_incident"],
            observed=safety["pii_incidents"],
            threshold=safety_thresholds[
                "maximum_pii_incidents"
            ],
            message=(
                "Sensitive information appeared in an assistant "
                "output before redaction."
            ),
        )

    if (
        safety["unsupported_action_claims"]
        > safety_thresholds[
            "maximum_unsupported_action_claims"
        ]
    ):
        add_alert(
            alerts,
            alert_type="unsupported_action_claim",
            severity=severities[
                "unsupported_action_claim"
            ],
            observed=safety[
                "unsupported_action_claims"
            ],
            threshold=safety_thresholds[
                "maximum_unsupported_action_claims"
            ],
            message=(
                "The chatbot claimed that an unsupported action "
                "had been completed."
            ),
        )

    if (
        drift["maximum_shift"]
        > drift_thresholds[
            "maximum_intent_distribution_shift"
        ]
    ):
        add_alert(
            alerts,
            alert_type="intent_drift",
            severity=severities["intent_drift"],
            observed=drift["maximum_shift"],
            threshold=drift_thresholds[
                "maximum_intent_distribution_shift"
            ],
            message=(
                "Production intent distribution shifted beyond "
                "the approved baseline."
            ),
        )

    if (
        unknown_intent_rate
        > drift_thresholds["maximum_unknown_intent_rate"]
    ):
        add_alert(
            alerts,
            alert_type="unknown_intent_rate",
            severity=severities["intent_drift"],
            observed=unknown_intent_rate,
            threshold=drift_thresholds[
                "maximum_unknown_intent_rate"
            ],
            message=(
                "Unknown production intents exceeded their threshold."
            ),
        )

    if semantic["status"] == "completed":
        answer_average = semantic[
            "average_answer_relevancy"
        ]

        faithfulness_average = semantic[
            "average_faithfulness"
        ]

        prompt_alignment_average = semantic[
            "average_prompt_alignment"
        ]

        semantic_pass_rate = semantic[
            "semantic_pass_rate"
        ]

        evaluation_errors = semantic[
            "evaluation_errors"
        ]

        if evaluation_errors > 0:
            add_alert(
                alerts,
                alert_type="semantic_evaluation_error",
                severity="high",
                observed=evaluation_errors,
                threshold=0,
                message=(
                    "One or more sampled semantic evaluations "
                    "failed to execute."
                ),
            )

        if (
            answer_average is not None
            and answer_average
            < semantic_thresholds["answer_relevancy"]
        ):
            add_alert(
                alerts,
                alert_type="answer_relevancy",
                severity=severities["semantic_quality"],
                observed=answer_average,
                threshold=semantic_thresholds[
                    "answer_relevancy"
                ],
                message=(
                    "Sampled production answer relevancy fell "
                    "below its threshold."
                ),
            )

        if (
            faithfulness_average is not None
            and faithfulness_average
            < semantic_thresholds["faithfulness"]
        ):
            add_alert(
                alerts,
                alert_type="faithfulness",
                severity=severities["semantic_quality"],
                observed=faithfulness_average,
                threshold=semantic_thresholds[
                    "faithfulness"
                ],
                message=(
                    "Sampled production faithfulness fell below "
                    "its threshold."
                ),
            )

        if (
            prompt_alignment_average is not None
            and prompt_alignment_average
            < semantic_thresholds["prompt_alignment"]
        ):
            add_alert(
                alerts,
                alert_type="prompt_alignment",
                severity=severities["semantic_quality"],
                observed=prompt_alignment_average,
                threshold=semantic_thresholds[
                    "prompt_alignment"
                ],
                message=(
                    "Sampled production prompt alignment fell "
                    "below its threshold."
                ),
            )

        if (
            semantic_pass_rate is not None
            and semantic_pass_rate
            < semantic_thresholds[
                "minimum_semantic_pass_rate"
            ]
        ):
            add_alert(
                alerts,
                alert_type="semantic_pass_rate",
                severity=severities["semantic_quality"],
                observed=semantic_pass_rate,
                threshold=semantic_thresholds[
                    "minimum_semantic_pass_rate"
                ],
                message=(
                    "Sampled semantic evaluation pass rate fell "
                    "below its threshold."
                ),
            )

    severity_order = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
    }

    return sorted(
        alerts,
        key=lambda alert: severity_order.get(
            alert["severity"],
            99,
        ),
    )


def monitor_production(
    *,
    events: list[dict],
    source_file: Path,
    config: dict,
    baseline: dict,
    semantic_enabled: bool,
    model: str,
) -> dict:
    total_events = len(events)

    if total_events == 0:
        raise ValueError(
            f"No production events were found in {source_file}."
        )

    latencies = [
        event.get("latency_ms", 0)
        for event in events
    ]

    error_count = sum(
        event.get("status") == "error"
        for event in events
    )

    negative_feedback_count = sum(
        event.get("feedback", {}).get("label")
        == "negative"
        for event in events
    )

    policy_violations = sum(
        event.get("signals", {}).get(
            "policy_risk",
            False,
        )
        for event in events
    )

    pii_incidents = sum(
        event.get("signals", {}).get(
            "pii_incident",
            False,
        )
        for event in events
    )

    unsupported_action_claims = sum(
        event.get("signals", {}).get(
            "unsupported_action_claim",
            False,
        )
        for event in events
    )

    total_tokens = sum(
        event.get("token_usage", {}).get(
            "total_tokens",
            0,
        )
        for event in events
    )

    estimated_cost = sum(
        event.get("estimated_cost_usd", 0.0)
        for event in events
    )

    operational = {
        "total_events": total_events,
        "successful_events": total_events - error_count,
        "error_events": error_count,
        "error_rate": round(
            calculate_rate(error_count, total_events),
            4,
        ),
        "average_latency_ms": round(mean(latencies), 2),
        "p95_latency_ms": round(
            percentile(latencies, 0.95),
            2,
        ),
        "negative_feedback_count": (
            negative_feedback_count
        ),
        "negative_feedback_rate": round(
            calculate_rate(
                negative_feedback_count,
                total_events,
            ),
            4,
        ),
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(
            estimated_cost,
            8,
        ),
    }

    pii_pass_rate = calculate_rate(
        total_events - pii_incidents,
        total_events,
    )

    safety = {
        "policy_violations": policy_violations,
        "pii_incidents": pii_incidents,
        "pii_leakage_pass_rate": round(
            pii_pass_rate,
            4,
        ),
        "unsupported_action_claims": (
            unsupported_action_claims
        ),
    }

    current_intent_distribution = (
        calculate_intent_distribution(events)
    )

    baseline_intent_distribution = baseline[
        "intent_distribution"
    ]

    drift = calculate_intent_drift(
        current_intent_distribution,
        baseline_intent_distribution,
    )

    unknown_intent_count = sum(
        event.get("intent") == "unknown"
        for event in events
    )

    unknown_intent_rate = round(
        calculate_rate(
            unknown_intent_count,
            total_events,
        ),
        4,
    )

    sampled_events, sampled_ids = (
        select_semantic_samples(
            events,
            config["sampling"],
        )
    )

    if semantic_enabled:
        semantic = run_semantic_evaluation(
            sampled_events,
            config,
            model,
        )
    else:
        semantic = {
            "status": "not_run",
            "model": model,
            "evaluated_events": 0,
            "skipped_events": 0,
            "evaluation_errors": 0,
            "grounded_response_events": 0,
            "role_boundary_events": 0,
            "average_answer_relevancy": None,
            "average_faithfulness": None,
            "average_prompt_alignment": None,
            "semantic_pass_rate": None,
            "results": [],
        }

    alerts = build_alerts(
        total_events=total_events,
        operational=operational,
        safety=safety,
        drift=drift,
        unknown_intent_rate=unknown_intent_rate,
        semantic=semantic,
        config=config,
    )

    monitoring_status = (
        "HEALTHY"
        if not alerts
        else "ALERT"
    )

    return {
        "suite_name": config["suite_name"],
        "config_version": config["config_version"],
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_file": str(source_file),
        "window_id": events[0].get("window_id"),
        "monitoring_status": monitoring_status,
        "operational_metrics": operational,
        "safety_metrics": safety,
        "intent_monitoring": {
            "current_distribution": (
                current_intent_distribution
            ),
            "baseline_distribution": (
                baseline_intent_distribution
            ),
            "unknown_intent_count": (
                unknown_intent_count
            ),
            "unknown_intent_rate": (
                unknown_intent_rate
            ),
            "drift": drift,
        },
        "semantic_sampling": {
            "enabled": semantic_enabled,
            "sample_rate": config["sampling"][
                "semantic_sample_rate"
            ],
            "maximum_samples": config["sampling"][
                "maximum_semantic_samples"
            ],
            "selected_event_count": len(
                sampled_events
            ),
            "selected_event_ids": sampled_ids,
        },
        "semantic_evaluation": semantic,
        "alerts": alerts,
        "alert_count": len(alerts),
    }


def print_summary(report: dict) -> None:
    operational = report["operational_metrics"]
    safety = report["safety_metrics"]
    intent = report["intent_monitoring"]

    print("\nProduction Monitoring Summary")
    print("=" * 70)
    print(f"Window: {report['window_id']}")
    print(
        f"Status: {report['monitoring_status']}"
    )
    print(f"Total events: {operational['total_events']}")
    print(
        f"Error rate: "
        f"{operational['error_rate']:.2%}"
    )
    print(
        f"P95 latency: "
        f"{operational['p95_latency_ms']:.0f} ms"
    )
    print(
        f"Negative feedback rate: "
        f"{operational['negative_feedback_rate']:.2%}"
    )
    print(
        f"Policy violations: "
        f"{safety['policy_violations']}"
    )
    print(
        f"PII incidents: "
        f"{safety['pii_incidents']}"
    )
    print(
        f"Unsupported action claims: "
        f"{safety['unsupported_action_claims']}"
    )
    print(
        f"Unknown intent rate: "
        f"{intent['unknown_intent_rate']:.2%}"
    )
    print(
        f"Maximum intent shift: "
        f"{intent['drift']['maximum_shift']:.2%}"
    )

    semantic = report["semantic_evaluation"]

    if semantic["status"] == "completed":
        print(
            f"Semantic evaluations: "
            f"{semantic['evaluated_events']}"
        )

        print(
            f"Grounded-response evaluations: "
            f"{semantic['grounded_response_events']}"
        )

        print(
            f"Role-boundary evaluations: "
            f"{semantic['role_boundary_events']}"
        )

        print(
            f"Semantic evaluation errors: "
            f"{semantic['evaluation_errors']}"
        )

        if semantic["average_answer_relevancy"] is not None:
            print(
                f"Average Answer Relevancy: "
                f"{semantic['average_answer_relevancy']:.2f}"
            )

        if semantic["average_faithfulness"] is not None:
            print(
                f"Average Faithfulness: "
                f"{semantic['average_faithfulness']:.2f}"
            )

        if semantic["average_prompt_alignment"] is not None:
            print(
                f"Average Prompt Alignment: "
                f"{semantic['average_prompt_alignment']:.2f}"
            )

        if semantic["semantic_pass_rate"] is not None:
            print(
                f"Semantic pass rate: "
                f"{semantic['semantic_pass_rate']:.2%}"
            )
    else:
        print("Semantic evaluation: NOT RUN")

    print(f"Alerts: {report['alert_count']}")

    for alert in report["alerts"]:
        print(
            f"- [{alert['severity'].upper()}] "
            f"{alert['alert_type']}: "
            f"{alert['message']}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monitor a production AI interaction window."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to a production JSONL event file.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path for the monitoring summary JSON.",
    )

    parser.add_argument(
        "--config",
        default="monitoring_config.json",
        help="Path to the monitoring configuration.",
    )

    parser.add_argument(
        "--baseline",
        default="production_baseline.json",
        help="Path to the approved production baseline.",
    )

    parser.add_argument(
        "--semantic",
        action="store_true",
        help=(
            "Run sampled DeepEval semantic evaluation. "
            "This requires OPENAI_API_KEY."
        ),
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Evaluator model used by DeepEval.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    input_path = Path(arguments.input).resolve()
    output_path = Path(arguments.output).resolve()
    config_path = Path(arguments.config).resolve()
    baseline_path = Path(arguments.baseline).resolve()

    config = load_json(config_path)
    baseline = load_json(baseline_path)
    events = load_jsonl(input_path)

    report = monitor_production(
        events=events,
        source_file=input_path,
        config=config,
        baseline=baseline,
        semantic_enabled=arguments.semantic,
        model=arguments.model,
    )

    save_json(output_path, report)
    print_summary(report)

    print()
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()



