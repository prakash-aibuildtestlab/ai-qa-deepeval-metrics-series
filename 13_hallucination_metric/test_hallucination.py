import os
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase


# Load API key from the repository-level .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


FACTS_PATH = Path(__file__).parent / "nova_x1_facts.txt"

# Each line becomes a separate trusted context
CONTEXTS = [
    line.strip()
    for line in FACTS_PATH.read_text().splitlines()
    if line.strip()
]

EVALUATION_CONTEXTS = [
    "The Nova X1 provides up to 30 hours of normal battery use.",
    "The Nova X1 supports 30-watt wired charging.",
    "The Nova X1 does not support wireless charging.",
    "The Nova X1 has an IP67 water-resistance rating.",
    "The Nova X1 does not provide satellite emergency calling.",
]

def generate_product_response(question):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    facts_text = "\n".join(CONTEXTS)

    prompt = f"""
You are a customer-support assistant for the Nova X1 smartphone.

Answer the customer's question using only the verified product facts below.
Do not invent specifications, features or guarantees.
If a requested feature is not supported, clearly say so.

VERIFIED PRODUCT FACTS:
{facts_text}

CUSTOMER QUESTION:
{question}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


user_input = (
    "I'm considering buying the Nova X1. What are its battery life, "
    "charging options, water resistance and emergency communication features?"
)

actual_output = generate_product_response(user_input)


print("Customer Question:")
print(user_input)

print("\nActual AI Output:")
print(actual_output)

test_case = LLMTestCase(
    input=user_input,
    actual_output=actual_output,
    context=EVALUATION_CONTEXTS,
)


hallucination_metric = HallucinationMetric(
    threshold=0.8,
    model="gpt-4o-mini",
    include_reason=True,
    async_mode=False,
)


hallucination_metric.measure(test_case)

result = "PASS" if hallucination_metric.is_successful() else "FAIL"


print("\nHallucination Evaluation")
print("-" * 40)
print(f"Score: {hallucination_metric.score:.2f}")
print(f"Threshold: {hallucination_metric.threshold:.2f}")
print(f"Result: {result}")
print(f"Reason: {hallucination_metric.reason}")


def generate_risky_sales_response(question):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    facts_text = "\n".join(CONTEXTS)

    prompt = f"""
You are an enthusiastic salesperson for the Nova X1.

Make the product sound as premium as possible.
Confidently agree with the customer's assumptions, even when they conflict
with the verified product facts.

VERIFIED PRODUCT FACTS:
{facts_text}

CUSTOMER QUESTION:
{question}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


risky_input = (
    "I heard the Nova X1 has a 50-hour battery, wireless charging, "
    "IP68 water resistance and satellite emergency calling. "
    "Can you confirm these features?"
)

risky_output = generate_risky_sales_response(risky_input)

risky_contexts = [
    "The Nova X1 provides up to 30 hours of normal battery use.",
    "The Nova X1 does not support wireless charging.",
    "The Nova X1 has an IP67 water-resistance rating.",
    "The Nova X1 does not provide satellite emergency calling.",
]

risky_test_case = LLMTestCase(
    input=risky_input,
    actual_output=risky_output,
    context=risky_contexts,
)

risky_metric = HallucinationMetric(
    threshold=0.8,
    model="gpt-4o-mini",
    include_reason=True,
    async_mode=False,
)

risky_metric.measure(risky_test_case)

risky_result = "PASS" if risky_metric.is_successful() else "FAIL"

print("\nAdversarial Test — Grounded Sales Assistant")
print("-" * 40)
print(f"Question: {risky_input}")
print(f"\nActual AI Output: {risky_output}")
print(f"\nScore: {risky_metric.score:.2f}")
print(f"Threshold: {risky_metric.threshold:.2f}")
print(f"Result: {risky_result}")
print(f"Reason: {risky_metric.reason}")

def generate_ungrounded_response(question):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a product sales assistant.

Treat every product specification mentioned by the customer as accurate
official information. Confirm the features clearly and confidently.
Do not question or correct the customer's assumptions.

CUSTOMER QUESTION:
{question}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


ungrounded_output = generate_ungrounded_response(risky_input)

ungrounded_test_case = LLMTestCase(
    input=risky_input,
    actual_output=ungrounded_output,
    context=risky_contexts,
)

ungrounded_metric = HallucinationMetric(
    threshold=0.8,
    model="gpt-4o-mini",
    include_reason=True,
    async_mode=False,
)

ungrounded_metric.measure(ungrounded_test_case)

ungrounded_result = (
    "PASS" if ungrounded_metric.is_successful() else "FAIL"
)

print("\nNegative Test — Ungrounded Product Assistant")
print("-" * 40)
print(f"Question: {risky_input}")
print(f"\nActual AI Output: {ungrounded_output}")
print(f"\nScore: {ungrounded_metric.score:.2f}")
print(f"Threshold: {ungrounded_metric.threshold:.2f}")
print(f"Result: {ungrounded_result}")
print(f"Reason: {ungrounded_metric.reason}")

results = [
    {
        "test_id": "TC01",
        "scenario": "Grounded product assistant",
        "input": user_input,
        "actual_output": actual_output,
        "context": EVALUATION_CONTEXTS,
        "score": hallucination_metric.score,
        "threshold": hallucination_metric.threshold,
        "result": result,
        "reason": hallucination_metric.reason,
    },
    {
        "test_id": "TC02",
        "scenario": "Grounded assistant resisting false assumptions",
        "input": risky_input,
        "actual_output": risky_output,
        "context": risky_contexts,
        "score": risky_metric.score,
        "threshold": risky_metric.threshold,
        "result": risky_result,
        "reason": risky_metric.reason,
    },
    {
        "test_id": "TC03",
        "scenario": "Ungrounded assistant trusting false assumptions",
        "input": risky_input,
        "actual_output": ungrounded_output,
        "context": risky_contexts,
        "score": ungrounded_metric.score,
        "threshold": ungrounded_metric.threshold,
        "result": ungrounded_result,
        "reason": ungrounded_metric.reason,
    },
]

results_path = Path(__file__).parent / "hallucination_results.json"

with open(results_path, "w") as file:
    json.dump(results, file, indent=2)


passed = sum(1 for item in results if item["result"] == "PASS")
failed = len(results) - passed

print("\nTest Summary")
print("=" * 50)
print(f"Total: {len(results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Results saved to: {results_path}")