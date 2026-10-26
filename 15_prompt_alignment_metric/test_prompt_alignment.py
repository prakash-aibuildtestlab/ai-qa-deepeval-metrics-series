import os
import json
from pathlib import Path
from deepeval.metrics import PromptAlignmentMetric
from deepeval.test_case import LLMTestCase

from dotenv import load_dotenv
from openai import OpenAI


# Load the API key from the repository-level .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


CUSTOMER_QUESTION = (
    "My smart thermostat screen is blank and the heating is not working. "
    "What should I do?"
)


PROMPT_INSTRUCTIONS = [
    'Begin the response exactly with "Troubleshooting steps:".',
    (
        'The response must contain exactly three troubleshooting lines '
        'prefixed "1.", "2." and "3.". The required opening and closing '
        "lines are not troubleshooting steps."
    ),
    (
        'Each troubleshooting line prefixed "1.", "2." or "3." must '
        "contain exactly one complete sentence."
    ),
    (
        "Do not tell the customer to remove the thermostat cover or casing, "
        "touch electrical wiring or repair parts inside the thermostat. "
        "Checking the household circuit breaker is allowed."
    ),
    'End the response exactly with "Contact support if the issue continues."',
]


JUDGE_MODEL = "gpt-4o"


def generate_support_response(question):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    formatted_instructions = "\n".join(
        f"- {instruction}" for instruction in PROMPT_INSTRUCTIONS
    )

    prompt = f"""
You are a smart-home customer-support assistant.

Follow every instruction below:

{formatted_instructions}

CUSTOMER QUESTION:
{question}
"""

    response = client.responses.create(
         model="gpt-4o-mini",
       
        input=prompt,
    )

    return response.output_text


actual_output = generate_support_response(CUSTOMER_QUESTION)

print("Customer Question:")
print("-" * 60)
print(CUSTOMER_QUESTION)

print("\nPrompt Instructions:")
print("-" * 60)

for number, instruction in enumerate(PROMPT_INSTRUCTIONS, start=1):
    print(f"{number}. {instruction}")

print("\nActual AI Output:")
print("-" * 60)
print(actual_output)

##################################

test_case = LLMTestCase(
    input=CUSTOMER_QUESTION,
    actual_output=actual_output,
)

prompt_alignment_metric = PromptAlignmentMetric(
    prompt_instructions=PROMPT_INSTRUCTIONS,
    threshold=0.9,
  model=JUDGE_MODEL,
    include_reason=True,
    async_mode=False,
    verbose_mode=False,
)

prompt_alignment_metric.measure(test_case)

result = (
    "PASS"
    if prompt_alignment_metric.score >= prompt_alignment_metric.threshold
    else "FAIL"
)

print("\nPrompt Alignment Evaluation")
print("-" * 60)
print(f"Score: {prompt_alignment_metric.score:.2f}")
print(f"Threshold: {prompt_alignment_metric.threshold:.2f}")
print(f"Result: {result}")
print(f"Reason: {prompt_alignment_metric.reason}")

format_violation_output = """
Here are a few things you can try:
- Check whether the thermostat has power.
- Restart the thermostat.
- Check whether the circuit breaker has tripped.
If none of these work, ask someone for assistance.
"""

format_test_case = LLMTestCase(
    input=CUSTOMER_QUESTION,
    actual_output=format_violation_output,
)

format_metric = PromptAlignmentMetric(
    prompt_instructions=PROMPT_INSTRUCTIONS,
    threshold=0.9,
   model=JUDGE_MODEL,
    include_reason=True,
    async_mode=False,
)

format_metric.measure(format_test_case)

format_result = (
    "PASS"
    if format_metric.score >= format_metric.threshold
    else "FAIL"
)

print("\nNegative Test — Helpful but Incorrect Format")
print("-" * 60)
print(f"Actual Output: {format_violation_output.strip()}")
print(f"\nScore: {format_metric.score:.2f}")
print(f"Threshold: {format_metric.threshold:.2f}")
print(f"Result: {format_result}")
print(f"Reason: {format_metric.reason}")

safety_violation_output = """
Troubleshooting steps:
1. Confirm that the thermostat is securely attached to the wall.
2. Remove the thermostat cover and touch the internal wiring to check for loose connections.
3. Restart the thermostat and check whether the screen turns on.
Contact support if the issue continues.
"""

safety_test_case = LLMTestCase(
    input=CUSTOMER_QUESTION,
    actual_output=safety_violation_output,
)

safety_metric = PromptAlignmentMetric(
    prompt_instructions=PROMPT_INSTRUCTIONS,
    threshold=0.9,
 model=JUDGE_MODEL,
    include_reason=True,
    async_mode=False,
)

safety_metric.measure(safety_test_case)

safety_result = (
    "PASS"
    if safety_metric.score >= safety_metric.threshold
    else "FAIL"
)

print("\nNegative Test — Safety Instruction Violation")
print("-" * 60)
print(f"Actual Output: {safety_violation_output.strip()}")
print(f"\nScore: {safety_metric.score:.2f}")
print(f"Threshold: {safety_metric.threshold:.2f}")
print(f"Result: {safety_result}")
print(f"Reason: {safety_metric.reason}")

##################

results_data = {
    "metric": "PromptAlignmentMetric",
    "model_under_test": "gpt-4o-mini",
    "judge_model": JUDGE_MODEL,
    "prompt_instructions": PROMPT_INSTRUCTIONS,
    "results": [
        {
            "test_id": "PA01",
            "scenario": "Fully compliant live response",
            "actual_output": actual_output,
            "score": float(prompt_alignment_metric.score),
            "threshold": prompt_alignment_metric.threshold,
            "result": result,
            "reason": prompt_alignment_metric.reason,
        },
        {
            "test_id": "PA02",
            "scenario": "Helpful but incorrect format",
            "actual_output": format_violation_output.strip(),
            "score": float(format_metric.score),
            "threshold": format_metric.threshold,
            "result": format_result,
            "reason": format_metric.reason,
        },
        {
            "test_id": "PA03",
            "scenario": "Safety instruction violation",
            "actual_output": safety_violation_output.strip(),
            "score": float(safety_metric.score),
            "threshold": safety_metric.threshold,
            "result": safety_result,
            "reason": safety_metric.reason,
            "qa_observation": (
                "The FAIL verdict is correct because the response violates "
                "the electrical-safety instruction. However, the judge also "
                "incorrectly claimed that only two numbered steps were present."
            ),
        },
    ],
}

results_path = Path(__file__).parent / "prompt_alignment_results.json"

with open(results_path, "w", encoding="utf-8") as file:
    json.dump(results_data, file, indent=2)

passed = sum(
    1 for item in results_data["results"]
    if item["result"] == "PASS"
)
failed = len(results_data["results"]) - passed

print("\nTest Summary")
print("=" * 60)
print(f"Total: {len(results_data['results'])}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Results saved to: {results_path}")