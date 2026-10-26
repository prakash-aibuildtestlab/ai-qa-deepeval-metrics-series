import os
from pathlib import Path
import json
from deepeval.metrics import SummarizationMetric
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv
from openai import OpenAI


# Load the API key from the repository-level .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


REPORT_PATH = Path(__file__).parent / "flight_disruption_report.txt"
SOURCE_REPORT = REPORT_PATH.read_text(encoding="utf-8")


def generate_summary(source_text):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an airline operations assistant.

Summarize the disruption report below accurately and concisely.
Include the important information needed by an operations manager.
Do not add information that is not in the report.

DISRUPTION REPORT:
{source_text}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


actual_summary = generate_summary(SOURCE_REPORT)

print("Original Report:")
print("-" * 60)
print(SOURCE_REPORT)

print("\nAI-Generated Summary:")
print("-" * 60)
print(actual_summary)

test_case = LLMTestCase(
    input=SOURCE_REPORT,
    actual_output=actual_summary,
)

summarization_metric = SummarizationMetric(
    threshold=0.8,
    model="gpt-4o-mini",
    assessment_questions=[
        (
            "Does the summary state that Flight SB218 was delayed because "
            "of a hydraulic monitoring system fault?"
        ),
        "Does the summary state that the total delay was five and a half hours?",
        "Does the summary mention that all 186 passengers were notified?",
        "Does the summary mention the AUD 25 meal vouchers?",
        (
            "Does the summary mention that twelve connecting passengers "
            "were moved to alternative services?"
        ),
        (
            "Does the summary mention that seven passengers received "
            "a full refund?"
        ),
        (
            "Does the summary explain that hotel accommodation was not "
            "provided because no overnight stay was required?"
        ),
        (
            "Does the summary state that no checked baggage was reported "
            "lost or damaged?"
        ),
        (
            "Does the summary state that passenger safety was the reason "
            "for the delay?"
        ),
    ],
    include_reason=True,
    async_mode=False,
)

summarization_metric.measure(test_case)

result = (
    "PASS"
    if summarization_metric.score >= summarization_metric.threshold
    else "FAIL"
)

print("\nSummarization Evaluation")
print("-" * 60)
print(f"Score: {summarization_metric.score:.2f}")
print(f"Threshold: {summarization_metric.threshold:.2f}")
print(f"Result: {result}")
print(f"Reason: {summarization_metric.reason}")
print(f"Score Breakdown: {summarization_metric.score_breakdown}")

incomplete_summary = """
Flight SB218 from Melbourne to Singapore was delayed by five and a half
hours because of a hydraulic monitoring system fault. It eventually
departed at 3:00 PM, and all 186 passengers were notified by email and SMS.
"""

incomplete_test_case = LLMTestCase(
    input=SOURCE_REPORT,
    actual_output=incomplete_summary,
)

incomplete_metric = SummarizationMetric(
    threshold=0.8,
    model="gpt-4o-mini",
    assessment_questions=[
        (
            "Does the summary state that Flight SB218 was delayed because "
            "of a hydraulic monitoring system fault?"
        ),
        "Does the summary state that the total delay was five and a half hours?",
        "Does the summary mention that all 186 passengers were notified?",
        "Does the summary mention the AUD 25 meal vouchers?",
        (
            "Does the summary mention that twelve connecting passengers "
            "were moved to alternative services?"
        ),
        (
            "Does the summary mention that seven passengers received "
            "a full refund?"
        ),
        (
            "Does the summary explain that hotel accommodation was not "
            "provided because no overnight stay was required?"
        ),
        (
            "Does the summary state that no checked baggage was reported "
            "lost or damaged?"
        ),
        (
            "Does the summary state that passenger safety was the reason "
            "for the delay?"
        ),
    ],
    include_reason=True,
    async_mode=False,
)

incomplete_metric.measure(incomplete_test_case)

incomplete_result = (
    "PASS"
    if incomplete_metric.score >= incomplete_metric.threshold
    else "FAIL"
)

print("\nNegative Test — Accurate but Incomplete Summary")
print("-" * 60)
print(f"Summary: {incomplete_summary.strip()}")
print(f"\nScore: {incomplete_metric.score:.2f}")
print(f"Threshold: {incomplete_metric.threshold:.2f}")
print(f"Result: {incomplete_result}")
print(f"Reason: {incomplete_metric.reason}")
print(f"Score Breakdown: {incomplete_metric.score_breakdown}")

incorrect_summary = """
Flight SB218 was delayed for eight hours because of an engine failure.
Two hundred passengers were notified only after arriving at the airport.
Passengers received AUD 100 vouchers, and no refunds or alternative
flights were offered. Several bags were lost during the disruption.
"""

incorrect_test_case = LLMTestCase(
    input=SOURCE_REPORT,
    actual_output=incorrect_summary,
)

incorrect_metric = SummarizationMetric(
    threshold=0.8,
    model="gpt-4o-mini",
    assessment_questions=summarization_metric.assessment_questions,
    include_reason=True,
    async_mode=False,
)

incorrect_metric.measure(incorrect_test_case)

incorrect_result = (
    "PASS"
    if incorrect_metric.score >= incorrect_metric.threshold
    else "FAIL"
)

print("\nNegative Test — Detailed but Incorrect Summary")
print("-" * 60)
print(f"Summary: {incorrect_summary.strip()}")
print(f"\nScore: {incorrect_metric.score:.2f}")
print(f"Threshold: {incorrect_metric.threshold:.2f}")
print(f"Result: {incorrect_result}")
print(f"Reason: {incorrect_metric.reason}")
print(f"Score Breakdown: {incorrect_metric.score_breakdown}")

all_results = [
    {
        "test_id": "SUM01",
        "scenario": "AI-generated comprehensive summary",
        "summary": actual_summary,
        "score": float(summarization_metric.score),
        "threshold": summarization_metric.threshold,
        "result": result,
        "reason": summarization_metric.reason,
        "score_breakdown": summarization_metric.score_breakdown,
    },
    {
        "test_id": "SUM02",
        "scenario": "Accurate but incomplete summary",
        "summary": incomplete_summary.strip(),
        "score": float(incomplete_metric.score),
        "threshold": incomplete_metric.threshold,
        "result": incomplete_result,
        "reason": incomplete_metric.reason,
        "score_breakdown": incomplete_metric.score_breakdown,
    },
    {
        "test_id": "SUM03",
        "scenario": "Detailed but incorrect summary",
        "summary": incorrect_summary.strip(),
        "score": float(incorrect_metric.score),
        "threshold": incorrect_metric.threshold,
        "result": incorrect_result,
        "reason": incorrect_metric.reason,
        "score_breakdown": incorrect_metric.score_breakdown,
    },
]

results_path = Path(__file__).parent / "summarization_results.json"

with open(results_path, "w", encoding="utf-8") as file:
    json.dump(all_results, file, indent=2)

passed = sum(1 for item in all_results if item["result"] == "PASS")
failed = len(all_results) - passed

print("\nTest Summary")
print("=" * 60)
print(f"Total: {len(all_results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Results saved to: {results_path}")