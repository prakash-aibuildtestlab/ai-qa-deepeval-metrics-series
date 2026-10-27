import os
from pathlib import Path
from typing import Literal
import json

from deepeval.metrics import JsonCorrectnessMetric
from deepeval.test_case import LLMTestCase
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr


# Load the API key from the repository-level .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


REPORT_PATH = Path(__file__).parent / "incident_report.txt"
INCIDENT_REPORT = REPORT_PATH.read_text()


class IncidentSchema(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    incident_id: StrictStr
    affected_service: StrictStr
    severity: Literal["low", "medium", "high", "critical"]
    customer_impact: StrictStr
    records_exposed: StrictInt
    requires_escalation: StrictBool
    status: Literal["investigating", "contained", "resolved"]


def generate_incident_json(report):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a cybersecurity incident-data extraction assistant.

Extract information from the incident report and return only valid JSON.
Do not use Markdown or wrap the JSON in code fences.

Use exactly these fields:

- incident_id: string
- affected_service: string
- severity: low, medium, high or critical
- customer_impact: string
- records_exposed: integer
- requires_escalation: boolean
- status: investigating, contained or resolved

INCIDENT REPORT:
{report}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


actual_output = generate_incident_json(INCIDENT_REPORT)

print("Original Incident Report:")
print("-" * 60)
print(INCIDENT_REPORT)

print("\nAI-Generated Structured Output:")
print("-" * 60)
print(actual_output)


test_case = LLMTestCase(
    input=INCIDENT_REPORT,
    actual_output=actual_output,
)


json_metric = JsonCorrectnessMetric(
    expected_schema=IncidentSchema,
    threshold=1.0,
    include_reason=True,
    model="gpt-4o-mini",
    async_mode=False,
)


json_metric.measure(test_case)

result = (
    "PASS"
    if json_metric.score >= json_metric.threshold
    else "FAIL"
)


print("\nJSON Correctness Evaluation")
print("-" * 60)
print(f"Score: {json_metric.score:.2f}")
print(f"Threshold: {json_metric.threshold:.2f}")
print(f"Result: {result}")
print(f"Reason: {json_metric.reason}")

def evaluate_json_output(output):
    evaluation_case = LLMTestCase(
        input=INCIDENT_REPORT,
        actual_output=output,
    )

    metric = JsonCorrectnessMetric(
        expected_schema=IncidentSchema,
        threshold=1.0,
        include_reason=True,
        model="gpt-4o-mini",
        async_mode=False,
    )

    metric.measure(evaluation_case)

    evaluation_result = (
        "PASS"
        if metric.score >= metric.threshold
        else "FAIL"
    )

    return metric, evaluation_result


# Test 2: Invalid schema
invalid_schema_output = """
{
  "incident_id": "INC-2048",
  "severity": "urgent",
  "customer_impact": "Login problem",
  "records_exposed": "zero",
  "requires_escalation": "yes",
  "status": "contained",
  "response_team": "Security Operations"
}
"""


invalid_metric, invalid_result = evaluate_json_output(
    invalid_schema_output
)

print("\nNegative Test — Invalid JSON Schema")
print("-" * 60)
print(f"Actual Output:\n{invalid_schema_output.strip()}")
print(f"\nScore: {invalid_metric.score:.2f}")
print(f"Threshold: {invalid_metric.threshold:.2f}")
print(f"Result: {invalid_result}")
print(f"Reason: {invalid_metric.reason}")





# Test 3: Valid schema but factually incorrect values
factually_wrong_output = """
{
  "incident_id": "INC-9999",
  "affected_service": "Payment Gateway",
  "severity": "low",
  "customer_impact": "No customers were affected.",
  "records_exposed": 500,
  "requires_escalation": false,
  "status": "resolved"
}
"""


wrong_values_metric, wrong_values_result = evaluate_json_output(
    factually_wrong_output
)

print("\nLimitation Test — Valid Schema but Incorrect Values")
print("-" * 60)
print(f"Actual Output:\n{factually_wrong_output.strip()}")
print(f"\nScore: {wrong_values_metric.score:.2f}")
print(f"Threshold: {wrong_values_metric.threshold:.2f}")
print(f"Result: {wrong_values_result}")
print(f"Reason: {wrong_values_metric.reason}")

all_results = [
    {
        "test_id": "JSON01",
        "scenario": "Valid and factually accurate JSON",
        "actual_output": actual_output,
        "score": json_metric.score,
        "threshold": json_metric.threshold,
        "result": result,
        "reason": json_metric.reason,
    },
    {
        "test_id": "JSON02",
        "scenario": "Invalid JSON schema",
        "actual_output": invalid_schema_output.strip(),
        "score": invalid_metric.score,
        "threshold": invalid_metric.threshold,
        "result": invalid_result,
        "reason": invalid_metric.reason,
    },
    {
        "test_id": "JSON03",
        "scenario": "Valid schema but factually incorrect values",
        "actual_output": factually_wrong_output.strip(),
        "score": wrong_values_metric.score,
        "threshold": wrong_values_metric.threshold,
        "result": wrong_values_result,
        "reason": wrong_values_metric.reason,
    },
]


results_path = Path(__file__).parent / "json_correctness_results.json"

with open(results_path, "w") as file:
    json.dump(all_results, file, indent=2)


passed = sum(
    1 for item in all_results
    if item["result"] == "PASS"
)

failed = len(all_results) - passed


print("\nTest Summary")
print("=" * 60)
print(f"Total: {len(all_results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Results saved to: {results_path}")