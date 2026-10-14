import sys
from pathlib import Path

from deepeval import evaluate
from deepeval.metrics import ContextualPrecisionMetric
from deepeval.test_case import LLMTestCase


previous_metric_path = Path(__file__).resolve().parents[1] / "05_contextual_relevancy"
sys.path.append(str(previous_metric_path))

from rag_agent import run_rag


if __name__ == "__main__":
    user_input = "What is the refund period for a damaged item?"

    expected_output = (
        "Customers can request a refund for damaged items within 14 days of delivery."
    )

    actual_output, retrieved_context = run_rag(user_input)

    poor_retrieval_order = [
        "Standard delivery policy: Standard parcels usually arrive within 3 to 5 business days.",
        "Damaged parcel policy: Customers should take clear photos of the damaged item.",
        "Refund policy: Customers can request a refund for damaged items within 14 days of delivery.",
    ]

    passing_test_case = LLMTestCase(
        input=user_input,
        actual_output=actual_output,
        expected_output=expected_output,
        retrieval_context=retrieved_context,
    )

    failing_test_case = LLMTestCase(
        input=user_input,
        actual_output="Customers can request a refund for damaged items within 14 days of delivery.",
        expected_output=expected_output,
        retrieval_context=poor_retrieval_order,
    )

    metric = ContextualPrecisionMetric(
        threshold=0.7,
        model="gpt-4o-mini",
        include_reason=True,
    )

    evaluate(
        test_cases=[passing_test_case, failing_test_case],
        metrics=[metric],
    )

    print("\nInput:")
    print(user_input)

    print("\nExpected Output:")
    print(expected_output)

    print("\nActual RAG Output:")
    print(actual_output)

    print("\nRetrieved Context from RAG:")
    for context in retrieved_context:
        print(f"- {context}")

    print("\nPoor Retrieval Order Used for Failed Scenario:")
    for context in poor_retrieval_order:
        print(f"- {context}")