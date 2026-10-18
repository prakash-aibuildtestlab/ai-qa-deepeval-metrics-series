import os
import json
from pathlib import Path
from deepeval.metrics import GEval
#from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.test_case import LLMTestCase, SingleTurnParams
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


POLICY = """
Standard hotel bookings may be cancelled without charge more than
48 hours before check-in.

Cancellations made within 48 hours of check-in incur a fee equal
to the first night's accommodation.
"""


def generate_llm_response(user_input):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing from the root .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a hotel customer-support assistant.

Answer the customer's question using only the policy below.

Policy:
{POLICY}

Customer question:
{user_input}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


user_input = "Can I cancel my hotel booking 24 hours before check-in?"

expected_output = (
    "Yes, the booking can be cancelled 24 hours before check-in, "
    "but a fee equal to the first night's accommodation will apply."
)

actual_output = generate_llm_response(user_input)

print("Question:")
print(user_input)

print("\nActual LLM Output:")
print(actual_output)


test_case = LLMTestCase(
    input=user_input,
    actual_output=actual_output,
    expected_output=expected_output,
)


def run_judge(run_number):
   
    metric = GEval(
    name="Policy Correctness",
    criteria=(
        "Evaluate the answer using these requirements: "
        "1. It must clearly state that the booking can be cancelled. "
        "2. It must state that cancelling 24 hours before check-in results "
        "in a fee equal to the first night's accommodation. "
        "Do not require the answer to repeat the complete 48-hour policy "
        "if it correctly answers the specific 24-hour scenario."
    ),
        # evaluation_params=[
        #     LLMTestCaseParams.INPUT,
        #     LLMTestCaseParams.ACTUAL_OUTPUT,
        #     LLMTestCaseParams.EXPECTED_OUTPUT,
        # ],
evaluation_params=[
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
],


        threshold=0.7,
        model="gpt-4o-mini",
        async_mode=False,
    )

    metric.measure(test_case)

    result = "PASS" if metric.score >= metric.threshold else "FAIL"

    print(f"\nJudge Run {run_number}")
    print("-" * 30)
    print(f"Score: {metric.score:.2f}")
    print(f"Threshold: {metric.threshold:.2f}")
    print(f"Result: {result}")
    print(f"Reason: {metric.reason}")

    return {
        "run": run_number,
        "score": metric.score,
        "threshold": metric.threshold,
        "result": result,
        "reason": metric.reason,
    }


run_1 = run_judge(1)
run_2 = run_judge(2)

score_difference = abs(run_1["score"] - run_2["score"])
verdict_consistent = run_1["result"] == run_2["result"]

comparison = {
    "input": user_input,
    "actual_output": actual_output,
    "expected_output": expected_output,
    "judge_model": "gpt-4o-mini",
    "runs": [run_1, run_2],
    "comparison": {
        "score_difference": round(score_difference, 2),
        "verdict_consistent": verdict_consistent,
    },
}

results_path = Path(__file__).parent / "comparison_results.json"

with open(results_path, "w") as file:
    json.dump(comparison, file, indent=2)

print("\nComparison")
print("-" * 30)
print(f"Score difference: {score_difference:.2f}")
print(f"Same verdict: {verdict_consistent}")
print(f"Results saved to: {results_path}")