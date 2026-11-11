import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(file_path: Path) -> dict:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def load_jsonl(file_path: Path) -> list[dict]:
    records = []

    with file_path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records


def save_json(file_path: Path, data: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def determine_severity(event: dict) -> str:
    signals = event["signals"]

    if (
        signals.get("pii_incident")
        or signals.get("unsupported_action_claim")
    ):
        return "critical"

    if (
        signals.get("application_error")
        or signals.get("policy_risk")
    ):
        return "high"

    return "medium"


def create_failure_reasons(
    event: dict,
    semantic_result: dict | None,
) -> list[str]:
    signals = event["signals"]
    reasons = []

    if signals.get("pii_incident"):
        reasons.append("pii_incident")

    if signals.get("unsupported_action_claim"):
        reasons.append("unsupported_action_claim")

    if signals.get("application_error"):
        reasons.append("application_error")

    if signals.get("policy_risk"):
        reasons.append("policy_risk")

    if (
        semantic_result
        and semantic_result.get("status") == "evaluated"
        and semantic_result.get("overall_result") == "FAIL"
    ):
        route = semantic_result["evaluation_route"]
        reasons.append(f"{route}_semantic_failure")

    return reasons


def create_regression_dataset(
    events: list[dict],
    monitoring_report: dict,
) -> dict:
    semantic_results = {
        result["event_id"]: result
        for result in monitoring_report[
            "semantic_evaluation"
        ]["results"]
    }

    regression_cases = []

    for event in events:
        event_id = event["event_id"]
        semantic_result = semantic_results.get(event_id)

        failure_reasons = create_failure_reasons(
            event,
            semantic_result,
        )

        if not failure_reasons:
            continue

        regression_number = len(regression_cases) + 1

        regression_case = {
            "regression_id": (
                f"PROD-REG-{regression_number:03d}"
            ),
            "source_event_id": event_id,
            "source_window_id": event["window_id"],
            "intent": event["intent"],
            "severity": determine_severity(event),
            "customer_input": event["customer_input"],
            "actual_production_output": (
                event["assistant_output"]
            ),
            "expected_behaviour": (
                event["expected_behaviour"]
            ),
            "retrieval_context": (
                event["retrieval_context"]
            ),
            "failure_reasons": failure_reasons,
            "evaluation_route": (
                semantic_result.get("evaluation_route")
                if semantic_result
                else None
            ),
            "automated_semantic_result": (
                semantic_result.get("overall_result")
                if semantic_result
                and semantic_result.get("status")
                == "evaluated"
                else None
            ),
            "regression_status": "pending_fix",
            "release_blocking": (
                determine_severity(event)
                in {"critical", "high"}
            ),
            "data_classification": (
                "synthetic_anonymised_demo_data"
            ),
        }

        regression_cases.append(regression_case)

    return {
        "dataset_name": (
            "Production-Incident Regression Dataset"
        ),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_window_id": monitoring_report["window_id"],
        "source_monitoring_status": monitoring_report[
            "monitoring_status"
        ],
        "total_regression_cases": len(regression_cases),
        "regression_cases": regression_cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert confirmed production failures into "
            "regression test cases."
        )
    )

    parser.add_argument(
        "--events",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--report",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    events = load_jsonl(args.events)
    report = load_json(args.report)

    regression_dataset = create_regression_dataset(
        events,
        report,
    )

    save_json(args.output, regression_dataset)

    print("Production-to-Regression Feedback Loop")
    print("=" * 70)
    print(
        "Source window:",
        regression_dataset["source_window_id"],
    )
    print(
        "Regression cases created:",
        regression_dataset["total_regression_cases"],
    )

    for case in regression_dataset["regression_cases"]:
        print(
            case["regression_id"],
            "|",
            case["source_event_id"],
            "|",
            case["severity"].upper(),
            "|",
            ", ".join(case["failure_reasons"]),
        )

    print(f"Dataset saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()