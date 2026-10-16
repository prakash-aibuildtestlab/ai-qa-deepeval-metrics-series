import asyncio
from pathlib import Path

from dotenv import load_dotenv

from rag_agent import run_rag
from deepeval_evaluator import evaluate_with_deepeval
from ragas_evaluator import evaluate_with_ragas


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

THRESHOLD = 0.70
MODEL = "gpt-4o-mini"

METRIC_NAMES = [
    "Answer Relevancy",
    "Faithfulness",
    "Context Relevance",
    "Context Precision",
    "Context Recall",
]


def create_shared_rag_record():
    user_input = (
        "Can I cancel my order after it has been shipped, "
        "and how will my refund be processed?"
    )

    expected_output = (
        "Once an order has been dispatched, it cannot be cancelled. "
        "The customer may refuse delivery or return the item. "
        "After the returned item is received and inspected, the refund is "
        "issued to the original payment method within 5 to 7 business days."
    )

    # The real RAG pipeline runs only once.
    actual_output, retrieval_context = run_rag(user_input)

    return {
        "user_input": user_input,
        "actual_output": actual_output,
        "expected_output": expected_output,
        "retrieval_context": retrieval_context,
    }


def print_shared_record(rag_record):
    print("\nShared RAG Evaluation Record")
    print("============================")

    print(f"\nUser Input:\n{rag_record['user_input']}")
    print(f"\nActual RAG Output:\n{rag_record['actual_output']}")
    print(f"\nExpected Output:\n{rag_record['expected_output']}")

    print("\nRetrieved Context:")

    for context in rag_record["retrieval_context"]:
        print(f"- {context}")


def print_comparison(deepeval_results, ragas_results):
    print("\nFramework Comparison")
    print("====================")

    header = (
        f"{'Metric':<22}"
        f"{'DeepEval':<12}"
        f"{'RAGAS':<12}"
        f"{'DeepEval Result':<18}"
        f"{'RAGAS Result':<15}"
    )

    print(header)
    print("-" * len(header))

    for metric_name in METRIC_NAMES:
        deepeval_result = deepeval_results[metric_name]
        ragas_result = ragas_results[metric_name]

        print(
            f"{metric_name:<22}"
            f"{deepeval_result['score']:<12.2f}"
            f"{ragas_result['score']:<12.2f}"
            f"{deepeval_result['status']:<18}"
            f"{ragas_result['status']:<15}"
        )


def main():
    # Step 1: Run the RAG pipeline once
    rag_record = create_shared_rag_record()

    # Step 2: Display the shared evidence
    print_shared_record(rag_record)

    # Step 3: Evaluate with DeepEval
    deepeval_results = evaluate_with_deepeval(
        rag_record=rag_record,
        threshold=THRESHOLD,
        model=MODEL,
    )

    # Step 4: Evaluate the exact same record with RAGAS
    ragas_results = asyncio.run(
        evaluate_with_ragas(
            rag_record=rag_record,
            threshold=THRESHOLD,
            model=MODEL,
        )
    )

    # Step 5: Compare both frameworks
    print_comparison(
        deepeval_results=deepeval_results,
        ragas_results=ragas_results,
    )


if __name__ == "__main__":
    main()