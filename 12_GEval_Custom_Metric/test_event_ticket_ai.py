import os
import json
from pathlib import Path
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from dotenv import load_dotenv
from openai import OpenAI


# Load the API key from the repository-level .env file
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


POLICY_PATH = Path(__file__).parent / "event_ticket_policy.txt"
POLICY = POLICY_PATH.read_text()


TEST_CASES = [
    {
        "id": "TC01",
        "scenario": "VIP refund and eligible transfer",
        "input": (
            "I purchased a VIP ticket but can no longer attend. "
            "The concert is two weeks away. Can I get a refund "
            "or transfer the ticket to my friend?"
        ),
        "expected_output": (
            "The VIP ticket cannot be refunded because VIP tickets are "
            "non-refundable. However, it can be transferred because more "
            "than 24 hours remain. The customer must verify their booking "
            "reference and registered email address before the transfer."
        ),
    },
    {
        "id": "TC02",
        "scenario": "Eligible General Admission refund",
        "input": (
            "I have a General Admission ticket and the event is 10 days away. "
            "Can I cancel it and get my money back?"
        ),
        "expected_output": (
            "The ticket is eligible for a refund because the request is more "
            "than 7 calendar days before the event. Booking and processing fees "
            "are non-refundable. The eligible refund must be returned to the "
            "original payment method within 5–10 business days. The customer "
            "must verify their booking reference and registered email address."
        ),
    },
    {
        "id": "TC03",
        "scenario": "Transfer requested inside 24 hours",
        "input": (
            "My event starts in 12 hours. Can I transfer my ticket "
            "to another person?"
        ),
        "expected_output": (
            "The ticket cannot be transferred because fewer than 24 hours "
            "remain before the event. The assistant must not promise an "
            "exception outside the policy."
        ),
    },
]


def generate_event_assistant_response(question):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are an event-ticket customer-support assistant.

Answer the customer's question using only the policy provided below.
Do not invent exceptions, guarantees or information that is not in the policy.

POLICY:
{POLICY}

CUSTOMER QUESTION:
{question}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


all_results = []


for test_data in TEST_CASES:
    user_input = test_data["input"]
    expected_output = test_data["expected_output"]

    # Generate a new live response for this scenario
    actual_output = generate_event_assistant_response(user_input)

    test_case = LLMTestCase(
        input=user_input,
        actual_output=actual_output,
        expected_output=expected_output,
        context=[POLICY],
    )

    correctness_metric = GEval(
        name="Event Ticket Policy Correctness",
        evaluation_steps=[
            (
                "Identify the ticket type, requested action and time remaining "
                "before the event."
            ),
            (
                "Compare the refund or transfer decision in the actual output "
                "with the expected output and policy context."
            ),
            (
                "Check whether all requirements relevant to the customer's "
                "request are included, such as non-refundable fees, payment "
                "method, processing time or identity verification."
            ),
            (
                "Do not penalize the response for omitting policy information "
                "that is unrelated to the customer's question."
            ),
            (
                "Identify contradictions, unsupported promises or exceptions "
                "that are not present in the policy."
            ),
            (
                "Heavily penalize an incorrect refund or transfer decision. "
                "Moderately penalize missing mandatory process requirements."
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

    correctness_metric.measure(test_case)

    result = (
        "PASS"
        if correctness_metric.score >= correctness_metric.threshold
        else "FAIL"
    )

    print(f"\n{test_data['id']} — {test_data['scenario']}")
    print("-" * 60)
    print(f"Question: {user_input}")
    print(f"\nActual AI Output: {actual_output}")
    print(f"\nScore: {correctness_metric.score:.2f}")
    print(f"Threshold: {correctness_metric.threshold:.2f}")
    print(f"Result: {result}")
    print(f"Reason: {correctness_metric.reason}")

    all_results.append(
        {
            "test_id": test_data["id"],
            "scenario": test_data["scenario"],
            "input": user_input,
            "expected_output": expected_output,
            "actual_output": actual_output,
            "score": correctness_metric.score,
            "threshold": correctness_metric.threshold,
            "result": result,
            "reason": correctness_metric.reason,
        }
    )


results_path = Path(__file__).parent / "correctness_results.json"

with open(results_path, "w") as file:
    json.dump(all_results, file, indent=2)


passed = sum(1 for item in all_results if item["result"] == "PASS")
failed = len(all_results) - passed

print("\nTest Summary")
print("=" * 60)
print(f"Total: {len(all_results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"Results saved to: {results_path}")