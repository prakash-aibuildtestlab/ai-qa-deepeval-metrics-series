import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(file_path: Path) -> dict:
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def save_json(file_path: Path, data: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def apply_human_reviews(
    report: dict,
    review_data: dict,
) -> dict:
    adjudicated_report = copy.deepcopy(report)

    semantic = adjudicated_report["semantic_evaluation"]
    results = semantic["results"]

    results_by_event = {
        result["event_id"]: result
        for result in results
    }

    reviews_applied = 0
    unmatched_reviews = []

    for review in review_data["reviews"]:
        event_id = review["event_id"]
        metric_name = review["metric"]

        result = results_by_event.get(event_id)

        if result is None:
            unmatched_reviews.append(
                {
                    "review_id": review["review_id"],
                    "event_id": event_id,
                    "reason": "Event was not found in the semantic report.",
                }
            )
            continue

        if metric_name not in result:
            unmatched_reviews.append(
                {
                    "review_id": review["review_id"],
                    "event_id": event_id,
                    "reason": (
                        f"Metric '{metric_name}' was not found "
                        "in the event result."
                    ),
                }
            )
            continue

        automated_overall_result = result["overall_result"]
        final_verdict = review["final_adjudication"]["verdict"]

        result["automated_overall_result"] = (
            automated_overall_result
        )

        result["human_review"] = {
            "review_id": review["review_id"],
            "metric": metric_name,
            "automated_metric_result": (
                result[metric_name]["result"]
            ),
            "human_verdict": review["human_review"]["verdict"],
            "human_reason": review["human_review"]["reason"],
            "final_verdict": final_verdict,
            "classification": review[
                "final_adjudication"
            ]["classification"],
        }

        result["adjudicated_overall_result"] = final_verdict
        reviews_applied += 1

    evaluated_results = [
        result
        for result in results
        if result.get("status") == "evaluated"
    ]

    automated_passes = sum(
        (
            result.get("automated_overall_result")
            or result.get("overall_result")
        )
        == "PASS"
        for result in evaluated_results
    )

    adjudicated_passes = sum(
        result.get(
            "adjudicated_overall_result",
            result.get("overall_result"),
        )
        == "PASS"
        for result in evaluated_results
    )

    evaluated_count = len(evaluated_results)

    automated_pass_rate = (
        automated_passes / evaluated_count
        if evaluated_count
        else None
    )

    adjudicated_pass_rate = (
        adjudicated_passes / evaluated_count
        if evaluated_count
        else None
    )

    semantic["automated_semantic_pass_rate"] = (
        round(automated_pass_rate, 4)
        if automated_pass_rate is not None
        else None
    )

    semantic["adjudicated_semantic_pass_rate"] = (
        round(adjudicated_pass_rate, 4)
        if adjudicated_pass_rate is not None
        else None
    )

    semantic["human_reviews_applied"] = reviews_applied

    adjudicated_report["adjudication"] = {
        "status": "completed",
        "review_set_name": review_data["review_set_name"],
        "review_status": review_data["review_status"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reviews_applied": reviews_applied,
        "unmatched_review_count": len(unmatched_reviews),
        "unmatched_reviews": unmatched_reviews,
    }

    return adjudicated_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply human-review decisions to a production "
            "monitoring report."
        )
    )

    parser.add_argument(
        "--report",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--reviews",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    report = load_json(args.report)
    review_data = load_json(args.reviews)

    adjudicated_report = apply_human_reviews(
        report,
        review_data,
    )

    save_json(args.output, adjudicated_report)

    semantic = adjudicated_report["semantic_evaluation"]
    adjudication = adjudicated_report["adjudication"]

    print("Production Monitoring Human Review")
    print("=" * 70)
    print(
        "Reviews applied:",
        adjudication["reviews_applied"],
    )
    print(
        "Unmatched reviews:",
        adjudication["unmatched_review_count"],
    )
    print(
        "Automated semantic pass rate:",
        f"{semantic['automated_semantic_pass_rate']:.2%}",
    )
    print(
        "Adjudicated semantic pass rate:",
        f"{semantic['adjudicated_semantic_pass_rate']:.2%}",
    )
    print(f"Report saved to: {args.output.resolve()}")


if __name__ == "__main__":
    main()