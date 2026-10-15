from deepeval import evaluate
from deepeval.metrics import ContextualRecallMetric
from deepeval.test_case import LLMTestCase

from rag_agent import generate_answer, run_rag


user_input = (
    "I missed my parcel delivery. What do I need to collect it, "
    "and how long will it be held?"
)

expected_output = (
    "The customer must bring valid photo identification and the "
    "collection notification or tracking number. The parcel will "
    "be held at the nominated post office for 10 business days."
)


# ---------------------------------------------------------
# PASS: Use the retrieval context returned by the real RAG
# ---------------------------------------------------------

complete_output, complete_context = run_rag(user_input)

passing_test_case = LLMTestCase(
    name="Complete retrieval context",
    input=user_input,
    actual_output=complete_output,
    expected_output=expected_output,
    retrieval_context=complete_context,
)


# ---------------------------------------------------------
# FAIL: Simulate a retriever that missed the holding period
# ---------------------------------------------------------

incomplete_context = [
    (
        "Parcel collection requirements: To collect a missed parcel "
        "from the post office, the customer must bring valid photo "
        "identification and the collection notification or tracking number."
    )
]

incomplete_output = generate_answer(
    user_input,
    incomplete_context,
)

failing_test_case = LLMTestCase(
    name="Incomplete retrieval context",
    input=user_input,
    actual_output=incomplete_output,
    expected_output=expected_output,
    retrieval_context=incomplete_context,
)


metric = ContextualRecallMetric(
    threshold=0.7,
    model="gpt-4o-mini",
    include_reason=True,
    async_mode=False,
)


evaluate(
    test_cases=[
        passing_test_case,
        failing_test_case,
    ],
    metrics=[metric],
)


print("\nQuestion:")
print(user_input)

print("\nExpected Output:")
print(expected_output)

print("\nComplete Context Returned by RAG:")
for item in complete_context:
    print(f"- {item}")

print("\nIncomplete Context Used for Failed Scenario:")
for item in incomplete_context:
    print(f"- {item}")

print("\nComplete RAG Output:")
print(complete_output)

print("\nIncomplete RAG Output:")
print(incomplete_output)