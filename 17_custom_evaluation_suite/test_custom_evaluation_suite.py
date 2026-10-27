import os
from pathlib import Path
from deepeval.metrics import GEval
import re
import json
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.metrics import DAGMetric
from deepeval.metrics.dag import (
    BinaryJudgementNode,
    DeepAcyclicGraph,
)
from dotenv import load_dotenv
from openai import OpenAI


# Load the API key from the repository-level .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


POLICY_PATH = Path(__file__).parent / "incident_triage_policy.txt"
POLICY = POLICY_PATH.read_text()


INCIDENT = """
The company VPN is completely unavailable. Approximately 150 remote
employees cannot connect, and there is currently no workaround. The issue
started 40 minutes ago. There is no indication of a security breach or
exposed data.
""".strip()


EXPECTED_OUTPUT = """
Priority: P1
Assigned team: Network Operations
Escalation required: Yes
Reason: The VPN is completely unavailable and affects 150 users. Under the
policy, a complete outage affecting 100 or more users is a P1 incident, and
all P1 incidents must be escalated immediately.
""".strip()

## BaseMetric
class IncidentTriageMetric(BaseMetric):
    def __init__(self, threshold=1.0):
        self.threshold = threshold
        self.score = 0
        self.success = False
        self.reason = None
        self.error = None
        self.async_mode = False
        self.strict_mode = False
        self.include_reason = True
        self.evaluation_model = None

    def measure(self, test_case: LLMTestCase) -> float:
        try:
            output = test_case.actual_output.lower()

            priority_correct = bool(
                re.search(
                    r"priority[^\n]*\bp1\b",
                    output,
                    re.IGNORECASE,
                )
            )

            team_correct = (
                "network operations" in output
            )

            escalation_correct = bool(
                re.search(
                    r"escalation required[^\n]*"
                    r"(yes|required|immediate)",
                    output,
                    re.IGNORECASE,
                )
            )

            checks = {
                "priority": priority_correct,
                "assigned_team": team_correct,
                "escalation": escalation_correct,
            }

            weights = {
                "priority": 0.50,
                "assigned_team": 0.25,
                "escalation": 0.25,
            }

            self.score = sum(
                weights[name]
                for name, passed in checks.items()
                if passed
            )

            failed_checks = [
                name
                for name, passed in checks.items()
                if not passed
            ]

            if failed_checks:
                self.reason = (
                    "Failed deterministic checks: "
                    + ", ".join(failed_checks)
                )
            else:
                self.reason = (
                    "The response contains the required P1 priority, "
                    "Network Operations assignment and escalation decision."
                )

            self.success = self.score >= self.threshold
            return self.score

        except Exception as error:
            self.error = str(error)
            self.success = False
            raise

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        if self.error is not None:
            self.success = False
        else:
            self.success = self.score >= self.threshold

        return self.success

    @property
    def __name__(self):
        return "Incident Triage Deterministic Metric"


def generate_triage_response(incident):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an IT incident-triage assistant.

Evaluate the incident using only the policy provided below.
Do not invent rules or exceptions.

Your response must include:
- Priority
- Assigned team
- Whether escalation is required
- A short policy-based explanation

POLICY:
{POLICY}

INCIDENT:
{incident}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


actual_output = generate_triage_response(INCIDENT)


print("Incident:")
print("-" * 60)
print(INCIDENT)

print("\nExpected Decision:")
print("-" * 60)
print(EXPECTED_OUTPUT)

print("\nActual AI Output:")
print("-" * 60)
print(actual_output)

############ GEVAL ######

test_case = LLMTestCase(
    input=INCIDENT,
    actual_output=actual_output,
    expected_output=EXPECTED_OUTPUT,
    context=[POLICY],
)


geval_metric = GEval(
    name="Incident Triage Business Rule Correctness",
    evaluation_steps=[
        (
            "Identify the number of affected users, service availability, "
            "incident type and duration from the input."
        ),
        (
            "Check whether the assigned priority matches the incident-triage "
            "policy."
        ),
        (
            "Check whether the assigned support team matches the incident "
            "type in the policy."
        ),
        (
            "Check whether the escalation decision follows the escalation "
            "rules in the policy."
        ),
        (
            "Check whether the explanation is consistent with the input, "
            "expected output and policy."
        ),
        (
            "Heavily penalize an incorrect priority, assigned team or "
            "escalation decision."
        ),
    ],
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
        SingleTurnParams.CONTEXT,
    ],
    threshold=0.8,
    model="gpt-4o-mini",
    async_mode=False,
)


geval_metric.measure(test_case)

geval_result = (
    "PASS"
    if geval_metric.score >= geval_metric.threshold
    else "FAIL"
)


print("\nG-Eval — Business Rule Correctness")
print("-" * 60)
print(f"Score: {geval_metric.score:.2f}")
print(f"Threshold: {geval_metric.threshold:.2f}")
print(f"Result: {geval_result}")
print(f"Reason: {geval_metric.reason}")

##### DAG METRIC #####
#DAG checks the response through an explicit sequence:

# Final decision: Was escalation handled correctly?
escalation_check = BinaryJudgementNode(
  criteria=(
    "Evaluate only the escalation decision in the actual output. "
    "Return True if the actual output explicitly states that escalation "
    "is required or must happen immediately. Return False if it says "
    "escalation is not required. Ignore the priority, assigned team, "
    "explanation and all other errors."
),
    evaluation_params=[
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
        SingleTurnParams.CONTEXT,
    ],
    label="Escalation decision",
)

escalation_check.add_verdict(
    verdict=True,
    score=10,
)

escalation_check.add_verdict(
    verdict=False,
    score=7,
)


# Second decision: Was the correct team assigned?
team_check = BinaryJudgementNode(
 criteria=(
    "Evaluate only the assigned team in the actual output. "
    "Return True if the actual output explicitly assigns the incident "
    "to Network Operations. Ignore the priority, escalation decision, "
    "explanation and all other errors."
),
    evaluation_params=[
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
        SingleTurnParams.CONTEXT,
    ],
    label="Team assignment",
)

team_check.add_verdict(
    verdict=True,
    then=escalation_check,
)

team_check.add_verdict(
    verdict=False,
    score=4,
)


# First and most important decision: Was priority correct?
priority_check = BinaryJudgementNode(
 criteria=(
    "Evaluate only the priority assigned in the actual output. "
    "Return True if the actual output explicitly assigns Priority P1. "
    "Ignore the assigned team, escalation decision, explanation and "
    "all other errors."
),
    evaluation_params=[
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
        SingleTurnParams.CONTEXT,
    ],
    label="Priority classification",
)

priority_check.add_verdict(
    verdict=True,
    then=team_check,
)

priority_check.add_verdict(
    verdict=False,
    score=0,
)


triage_dag = DeepAcyclicGraph(
    root_nodes=[priority_check]
)


dag_metric = DAGMetric(
    name="Incident Triage Decision Flow",
    dag=triage_dag,
    threshold=0.8,
    model="gpt-4o-mini",
    include_reason=True,
    async_mode=False,
    verbose_mode=True,
)


dag_metric.measure(test_case)

dag_result = (
    "PASS"
    if dag_metric.score >= dag_metric.threshold
    else "FAIL"
)


print("\nDAG Metric — Controlled Decision Flow")
print("-" * 60)
print(f"Score: {dag_metric.score:.2f}")
print(f"Threshold: {dag_metric.threshold:.2f}")
print(f"Result: {dag_result}")
print(f"Reason: {dag_metric.reason}")

## Customer Metric results
custom_metric = IncidentTriageMetric(
    threshold=1.0
)

custom_metric.measure(test_case)

custom_result = (
    "PASS"
    if custom_metric.is_successful()
    else "FAIL"
)


print("\nCustom Metric — Deterministic Python Rules")
print("-" * 60)
print(f"Score: {custom_metric.score:.2f}")
print(f"Threshold: {custom_metric.threshold:.2f}")
print(f"Result: {custom_result}")
print(f"Reason: {custom_metric.reason}")

## 
# Preserve the positive-test results before reusing the metrics
positive_results = {
    "geval": {
        "score": geval_metric.score,
        "result": geval_result,
        "reason": geval_metric.reason,
    },
    "dag": {
        "score": dag_metric.score,
        "result": dag_result,
        "reason": dag_metric.reason,
    },
    "custom": {
        "score": custom_metric.score,
        "result": custom_result,
        "reason": custom_metric.reason,
    },
}


flawed_output = """
Priority: P1
Assigned team: Application Support
Escalation required: No
Reason: Although the VPN is unavailable, the incident has only been open
for 40 minutes, so it does not require escalation yet.
""".strip()


flawed_test_case = LLMTestCase(
    input=INCIDENT,
    actual_output=flawed_output,
    expected_output=EXPECTED_OUTPUT,
    context=[POLICY],
)


print("\nNegative Test — Partially Correct Triage Decision")
print("=" * 60)
print(flawed_output)


# Reuse G-Eval for the flawed response
geval_metric.measure(flawed_test_case)

negative_geval_result = (
    "PASS"
    if geval_metric.score >= geval_metric.threshold
    else "FAIL"
)

print("\nG-Eval Result")
print("-" * 60)
print(f"Score: {geval_metric.score:.2f}")
print(f"Threshold: {geval_metric.threshold:.2f}")
print(f"Result: {negative_geval_result}")
print(f"Reason: {geval_metric.reason}")


# Reuse the DAG for the flawed response
dag_metric.measure(flawed_test_case)

negative_dag_result = (
    "PASS"
    if dag_metric.score >= dag_metric.threshold
    else "FAIL"
)

print("\nDAG Metric Result")
print("-" * 60)
print(f"Score: {dag_metric.score:.2f}")
print(f"Threshold: {dag_metric.threshold:.2f}")
print(f"Result: {negative_dag_result}")
print(f"Reason: {dag_metric.reason}")


# Run a new custom metric instance
negative_custom_metric = IncidentTriageMetric(
    threshold=1.0
)

negative_custom_metric.measure(flawed_test_case)

negative_custom_result = (
    "PASS"
    if negative_custom_metric.is_successful()
    else "FAIL"
)

print("\nCustom Metric Result")
print("-" * 60)
print(f"Score: {negative_custom_metric.score:.2f}")
print(f"Threshold: {negative_custom_metric.threshold:.2f}")
print(f"Result: {negative_custom_result}")
print(f"Reason: {negative_custom_metric.reason}")


## Capture results 
all_results = [
    {
        "test_id": "CUSTOM01",
        "scenario": "Correct incident-triage response",
        "input": INCIDENT,
        "expected_output": EXPECTED_OUTPUT,
        "actual_output": actual_output,
        "metrics": {
            "geval": {
                "score": positive_results["geval"]["score"],
                "threshold": 0.8,
                "result": positive_results["geval"]["result"],
                "reason": positive_results["geval"]["reason"],
            },
            "dag": {
                "score": positive_results["dag"]["score"],
                "threshold": 0.8,
                "result": positive_results["dag"]["result"],
                "reason": positive_results["dag"]["reason"],
            },
            "custom": {
                "score": positive_results["custom"]["score"],
                "threshold": 1.0,
                "result": positive_results["custom"]["result"],
                "reason": positive_results["custom"]["reason"],
            },
        },
    },
    {
        "test_id": "CUSTOM02",
        "scenario": "Correct priority but incorrect team and escalation",
        "input": INCIDENT,
        "expected_output": EXPECTED_OUTPUT,
        "actual_output": flawed_output,
        "metrics": {
            "geval": {
                "score": geval_metric.score,
                "threshold": geval_metric.threshold,
                "result": negative_geval_result,
                "reason": geval_metric.reason,
            },
            "dag": {
                "score": dag_metric.score,
                "threshold": dag_metric.threshold,
                "result": negative_dag_result,
                "reason": dag_metric.reason,
            },
            "custom": {
                "score": negative_custom_metric.score,
                "threshold": negative_custom_metric.threshold,
                "result": negative_custom_result,
                "reason": negative_custom_metric.reason,
            },
        },
    },
]


results_path = (
    Path(__file__).parent
    / "custom_evaluation_results.json"
)

with open(results_path, "w") as file:
    json.dump(all_results, file, indent=2)


metric_results = [
    metric
    for test_result in all_results
    for metric in test_result["metrics"].values()
]

passed = sum(
    1 for metric in metric_results
    if metric["result"] == "PASS"
)

failed = len(metric_results) - passed


print("\nCustom Evaluation Suite Summary")
print("=" * 60)
print(f"Test scenarios: {len(all_results)}")
print(f"Metric evaluations: {len(metric_results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Results saved to: {results_path}")