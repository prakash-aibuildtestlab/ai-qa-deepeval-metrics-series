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


async def evaluate_with_ragas(
    rag_record,
    threshold=0.70,
    model="gpt-4o-mini",
):
    llm_client = AsyncOpenAI()
    embedding_client = AsyncOpenAI()

    evaluator_llm = llm_factory(
        model,
        client=llm_client,
    )

    evaluator_embeddings = embedding_factory(
        "openai",
        model="text-embedding-3-small",
        client=embedding_client,
        interface="modern",
    )

    results = {}

    print("\nRAGAS Results")
    print("=============")

    try:
        # 1. Answer Relevancy
        metric = AnswerRelevancy(
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )

        result = await metric.ascore(
            user_input=rag_record["user_input"],
            response=rag_record["actual_output"],
        )

        save_result(
            results,
            "Answer Relevancy",
            result,
            threshold,
        )

        # 2. Faithfulness
        metric = Faithfulness(llm=evaluator_llm)

        result = await metric.ascore(
            user_input=rag_record["user_input"],
            response=rag_record["actual_output"],
            retrieved_contexts=rag_record["retrieval_context"],
        )

        save_result(
            results,
            "Faithfulness",
            result,
            threshold,
        )

        # 3. Context Relevance
        metric = ContextRelevance(llm=evaluator_llm)

        result = await metric.ascore(
            user_input=rag_record["user_input"],
            retrieved_contexts=rag_record["retrieval_context"],
        )

        save_result(
            results,
            "Context Relevance",
            result,
            threshold,
        )

        # 4. Context Precision
        metric = ContextPrecisionWithReference(llm=evaluator_llm)

        result = await metric.ascore(
            user_input=rag_record["user_input"],
            reference=rag_record["expected_output"],
            retrieved_contexts=rag_record["retrieval_context"],
        )

        save_result(
            results,
            "Context Precision",
            result,
            threshold,
        )

        # 5. Context Recall
        metric = ContextRecall(llm=evaluator_llm)

        result = await metric.ascore(
            user_input=rag_record["user_input"],
            reference=rag_record["expected_output"],
            retrieved_contexts=rag_record["retrieval_context"],
        )

        save_result(
            results,
            "Context Recall",
            result,
            threshold,
        )

    finally:
        await llm_client.close()
        await embedding_client.close()

    return results


def save_result(results, metric_name, result, threshold):
    score = float(result.value)
    status = "PASS" if score >= threshold else "FAIL"
    reason = getattr(result, "reason", None)

    results[metric_name] = {
        "score": score,
        "status": status,
        "reason": reason,
    }

    print(f"\n{metric_name}")
    print("-" * len(metric_name))
    print(f"Score: {score:.2f}")
    print(f"Result: {status}")

    if reason:
        print(f"Reason: {reason}")