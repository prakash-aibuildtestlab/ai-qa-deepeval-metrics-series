from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from rag_agent import generate_answer, run_rag


THRESHOLD = 0.70
JUDGE_MODEL = "gpt-4o-mini"

user_input = (
    "Can I cancel my order after it has been shipped, "
    "and how will my refund be processed?"
)

expected_output = (
    "The order cannot be cancelled after dispatch. "
    "The customer may refuse delivery or return the item after receiving it. "
    "After the returned item is received and inspected, the refund is issued "
    "to the original payment method within 5 to 7 business days."
)


def run_diagnosis(number, failure, component, metric, test_case):
    print("\n" + "=" * 70)
    print(f"SCENARIO {number}: {failure}")
    print(f"COMPONENT UNDER TEST: {component}")
    print(f"METRIC: {metric.__class__.__name__}")
    print("=" * 70)

    metric.measure(test_case)

    status = "PASS" if metric.score >= THRESHOLD else "FAIL"

    print(f"\nScore: {metric.score:.2f}")
    print(f"Threshold: {THRESHOLD:.2f}")
    print(f"Result: {status}")
    print(f"Reason: {metric.reason}")


if __name__ == "__main__":
    # Run the real RAG pipeline first
    baseline_output, baseline_context = run_rag(user_input)

    print("\nREAL RAG BASELINE")
    print("-----------------")

    print("\nQuestion:")
    print(user_input)

    print("\nRetrieved Context:")
    for context in baseline_context:
        print(f"- {context}")

    print("\nRAG Answer:")
    print(baseline_output)

    # ---------------------------------------------------------
    # Scenario 1: Retrieval returned completely unrelated context
    # ---------------------------------------------------------
    irrelevant_context = [
        "Customers can change their password from the profile settings page.",
        "Two-factor authentication can be enabled from security settings.",
    ]

    irrelevant_output = generate_answer(
        user_input,
        irrelevant_context,
    )

    relevancy_case = LLMTestCase(
        input=user_input,
        actual_output=irrelevant_output,
        retrieval_context=irrelevant_context,
    )

    relevancy_metric = ContextualRelevancyMetric(
        threshold=THRESHOLD,
        model=JUDGE_MODEL,
        include_reason=True,
        async_mode=False,
    )

    run_diagnosis(
        number=1,
        failure="The retriever returned unrelated documents",
        component="Retriever",
        metric=relevancy_metric,
        test_case=relevancy_case,
    )

    # ---------------------------------------------------------
    # Scenario 2: Correct documents were ranked too low
    # ---------------------------------------------------------
    badly_ranked_context = [
        "Customers can change their password from the profile settings page.",
        "Standard parcels normally arrive within 3 to 5 business days.",
        baseline_context[0],
        baseline_context[1],
    ]

    precision_case = LLMTestCase(
        input=user_input,
        actual_output=baseline_output,
        expected_output=expected_output,
        retrieval_context=badly_ranked_context,
    )

    precision_metric = ContextualPrecisionMetric(
        threshold=THRESHOLD,
        model=JUDGE_MODEL,
        include_reason=True,
        async_mode=False,
    )

    run_diagnosis(
        number=2,
        failure="Relevant documents were ranked below irrelevant documents",
        component="Retriever ranking",
        metric=precision_metric,
        test_case=precision_case,
    )

    # ---------------------------------------------------------
    # Scenario 3: Retrieval missed required refund information
    # ---------------------------------------------------------
    incomplete_context = [
        (
            "Order cancellation policy: Once an order has been dispatched, "
            "it cannot be cancelled. The customer may refuse delivery or "
            "return the item after receiving it."
        )
    ]

    incomplete_output = generate_answer(
        user_input,
        incomplete_context,
    )

    recall_case = LLMTestCase(
        input=user_input,
        actual_output=incomplete_output,
        expected_output=expected_output,
        retrieval_context=incomplete_context,
    )

    recall_metric = ContextualRecallMetric(
        threshold=THRESHOLD,
        model=JUDGE_MODEL,
        include_reason=True,
        async_mode=False,
    )

    run_diagnosis(
        number=3,
        failure="Retrieval missed required refund-processing information",
        component="Retriever coverage",
        metric=recall_metric,
        test_case=recall_case,
    )

    # ---------------------------------------------------------
    # Scenario 4: Answer contradicted the retrieved context
    # ---------------------------------------------------------
    hallucinated_output = (
        "The order can be cancelled after shipment. "
        "The refund will be provided as store credit within 24 hours."
    )

    faithfulness_case = LLMTestCase(
        input=user_input,
        actual_output=hallucinated_output,
        retrieval_context=baseline_context,
    )

    faithfulness_metric = FaithfulnessMetric(
        threshold=THRESHOLD,
        model=JUDGE_MODEL,
        include_reason=True,
        async_mode=False,
    )

    run_diagnosis(
        number=4,
        failure="The generated answer contradicted the retrieved documents",
        component="LLM generator",
        metric=faithfulness_metric,
        test_case=faithfulness_case,
    )