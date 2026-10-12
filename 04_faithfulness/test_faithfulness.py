import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from deepeval import evaluate
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase


load_dotenv(Path(__file__).parent / ".env")


def get_llm_response(user_input, retrieval_context):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file.")

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a customer support assistant.

Answer the user's question using only the context below.

Context:
{retrieval_context}

User question:
{user_input}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


if __name__ == "__main__":
    user_input = "What is the refund period for a damaged item?"

    retrieval_context = [
        "Customers can request a refund for damaged items within 14 days of delivery.",
        "Refund requests must include the order number and photos of the damaged item.",
    ]

    faithful_output = get_llm_response(user_input, retrieval_context)

    hallucinated_output = (
        "Customers can request a refund for damaged items within 30 days of delivery."
    )

    test_case_pass = LLMTestCase(
        input=user_input,
        actual_output=faithful_output,
        retrieval_context=retrieval_context,
    )

    test_case_fail = LLMTestCase(
        input=user_input,
        actual_output=hallucinated_output,
        retrieval_context=retrieval_context,
    )

    metric = FaithfulnessMetric(
        threshold=0.7,
        model="gpt-4o-mini",
        include_reason=True,
    )

    evaluate(
        test_cases=[test_case_pass, test_case_fail],
        metrics=[metric],
    )

    print("\nInput:")
    print(user_input)

    print("\nRetrieval Context:")
    for context in retrieval_context:
        print(f"- {context}")

    print("\nFaithful LLM Output:")
    print(faithful_output)

    print("\nHallucinated Output:")
    print(hallucinated_output)