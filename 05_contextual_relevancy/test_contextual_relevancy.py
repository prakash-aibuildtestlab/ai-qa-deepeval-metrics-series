from deepeval import evaluate
from deepeval.metrics import ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase

from rag_agent import run_rag


if __name__ == "__main__":
    user_input = "What is the refund period for a damaged item?"

    actual_output, retrieved_context = run_rag(user_input)

    irrelevant_context = [
        "Customers can change their account password from the profile settings page.",
        "Two-factor authentication can be enabled from security settings.",
    ]

    passing_test_case = LLMTestCase(
        input=user_input,
        actual_output=actual_output,
        retrieval_context=retrieved_context,
    )

    failing_test_case = LLMTestCase(
        input=user_input,
        actual_output="The refund period is 14 days after delivery.",
        retrieval_context=irrelevant_context,
    )

    metric = ContextualRelevancyMetric(
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

    print("\nRetrieved Context from RAG:")
    for context in retrieved_context:
        print(f"- {context}")

    print("\nActual RAG Output:")
    print(actual_output)

    print("\nIrrelevant Context Used for Failed Scenario:")
    for context in irrelevant_context:
        print(f"- {context}")