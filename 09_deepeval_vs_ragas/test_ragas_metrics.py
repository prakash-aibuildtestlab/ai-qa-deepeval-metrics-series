import asyncio
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory
from ragas.metrics.collections import (
    AnswerRelevancy,
    Faithfulness,
    ContextRelevance,
    ContextPrecisionWithReference,
    ContextRecall,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

THRESHOLD = 0.70


def print_result(metric_name, result):
    score = float(result.value)
    status = "PASS" if score >= THRESHOLD else "FAIL"

    print(f"\n{metric_name}")
    print("-" * len(metric_name))
    print(f"Score: {score:.2f}")
    print(f"Threshold: {THRESHOLD:.2f}")
    print(f"Result: {status}")

    reason = getattr(result, "reason", None)
    if reason:
        print(f"Reason: {reason}")


async def main():
    # RAGAS evaluator model
    llm_client = AsyncOpenAI()
    evaluator_llm = llm_factory(
        "gpt-4o-mini",
        client=llm_client,
    )

    # Answer Relevancy also requires embeddings
    embedding_client = AsyncOpenAI()
    evaluator_embeddings = embedding_factory(
        "openai",
        model="text-embedding-3-small",
        client=embedding_client,
        interface="modern",
    )

    question = (
        "Can I cancel my order after it has been shipped, "
        "and how will my refund be processed?"
    )

    expected_answer = (
        "Once an order has been dispatched, it cannot be cancelled. "
        "The customer may refuse delivery or return the item. "
        "After the return is received and inspected, the refund is issued "
        "to the original payment method within 5 to 7 business days."
    )

    correct_response = (
        "You cannot cancel an order after it has been shipped. "
        "You may refuse delivery or return it after receiving it. "
        "Once the return is received and inspected, the refund will be sent "
        "to the original payment method within 5 to 7 business days."
    )

    hallucinated_response = (
        "The order can be cancelled after shipment, and the refund will be "
        "issued as store credit within 24 hours."
    )

    relevant_contexts = [
        (
            "Order cancellation policy: Once an order has been dispatched, "
            "it cannot be cancelled. The customer may refuse delivery or "
            "return the item after receiving it."
        ),
        (
            "Refund processing policy: After the returned item is received "
            "and inspected, the refund is issued to the original payment "
            "method within 5 to 7 business days."
        ),
    ]

    poorly_ranked_contexts = [
        "Customers can change their password from the profile settings page.",
        "Standard parcels usually arrive within 3 to 5 business days.",
        relevant_contexts[0],
        relevant_contexts[1],
    ]

    incomplete_contexts = [
        relevant_contexts[0],
    ]

    # 1. Answer Relevancy
    answer_relevancy = AnswerRelevancy(
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )

    answer_relevancy_result = await answer_relevancy.ascore(
        user_input=question,
        response=correct_response,
    )

    print_result("1. Answer Relevancy", answer_relevancy_result)

    # 2. Faithfulness
    faithfulness = Faithfulness(llm=evaluator_llm)

    faithfulness_result = await faithfulness.ascore(
        user_input=question,
        response=hallucinated_response,
        retrieved_contexts=relevant_contexts,
    )

    print_result("2. Faithfulness", faithfulness_result)

    # 3. Context Relevance
    context_relevance = ContextRelevance(llm=evaluator_llm)

    context_relevance_result = await context_relevance.ascore(
        user_input=question,
        retrieved_contexts=relevant_contexts,
    )

    print_result("3. Context Relevance", context_relevance_result)

    # 4. Context Precision
    context_precision = ContextPrecisionWithReference(llm=evaluator_llm)

    context_precision_result = await context_precision.ascore(
        user_input=question,
        reference=expected_answer,
        retrieved_contexts=poorly_ranked_contexts,
    )

    print_result("4. Context Precision", context_precision_result)

    # 5. Context Recall
    context_recall = ContextRecall(llm=evaluator_llm)

    context_recall_result = await context_recall.ascore(
        user_input=question,
        reference=expected_answer,
        retrieved_contexts=incomplete_contexts,
    )

    print_result("5. Context Recall", context_recall_result)


if __name__ == "__main__":
    asyncio.run(main())