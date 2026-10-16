from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)


def evaluate_with_deepeval(
    rag_record,
    threshold=0.70,
    model="gpt-4o-mini",
):
    test_case = LLMTestCase(
        input=rag_record["user_input"],
        actual_output=rag_record["actual_output"],
        expected_output=rag_record["expected_output"],
        retrieval_context=rag_record["retrieval_context"],
    )

    metrics = [
        (
            "Answer Relevancy",
            AnswerRelevancyMetric(
                threshold=threshold,
                model=model,
                include_reason=True,
                async_mode=False,
            ),
        ),
        (
            "Faithfulness",
            FaithfulnessMetric(
                threshold=threshold,
                model=model,
                include_reason=True,
                async_mode=False,
            ),
        ),
        (
            "Context Relevance",
            ContextualRelevancyMetric(
                threshold=threshold,
                model=model,
                include_reason=True,
                async_mode=False,
            ),
        ),
        (
            "Context Precision",
            ContextualPrecisionMetric(
                threshold=threshold,
                model=model,
                include_reason=True,
                async_mode=False,
            ),
        ),
        (
            "Context Recall",
            ContextualRecallMetric(
                threshold=threshold,
                model=model,
                include_reason=True,
                async_mode=False,
            ),
        ),
    ]

    results = {}

    print("\nDeepEval Results")
    print("================")

    for metric_name, metric in metrics:
        metric.measure(test_case)

        score = float(metric.score)
        status = "PASS" if score >= threshold else "FAIL"

        results[metric_name] = {
            "score": score,
            "status": status,
            "reason": metric.reason,
        }

        print(f"\n{metric_name}")
        print("-" * len(metric_name))
        print(f"Score: {score:.2f}")
        print(f"Result: {status}")
        print(f"Reason: {metric.reason}")

    return results