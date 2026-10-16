import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# Load the shared .env file from the repository root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


POLICY_DOCUMENTS = [
    Document(
        page_content=(
            "Order cancellation policy: Once an order has been dispatched, "
            "it cannot be cancelled. The customer may refuse delivery or "
            "return the item after receiving it."
        )
    ),
    Document(
        page_content=(
            "Refund processing policy: After the returned item is received "
            "and inspected, the refund is issued to the original payment "
            "method within 5 to 7 business days."
        )
    ),
    Document(
        page_content=(
            "Delivery policy: Standard parcels normally arrive within "
            "3 to 5 business days after dispatch."
        )
    ),
    Document(
        page_content=(
            "Account security policy: Customers can change their password "
            "from the profile settings page."
        )
    ),
]


def build_vector_store():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    return InMemoryVectorStore.from_documents(
        documents=POLICY_DOCUMENTS,
        embedding=embeddings,
    )


def retrieve_context(user_input, vector_store, number_of_documents=2):
    documents = vector_store.similarity_search(
        user_input,
        k=number_of_documents,
    )

    return [document.page_content for document in documents]


def generate_answer(user_input, retrieval_context):
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    context_text = "\n\n".join(retrieval_context)

    prompt = f"""
You are a customer-support assistant.

Answer the customer's question using only the retrieved context.

If the context does not contain enough information, say that the information
is not available in the retrieved context.

Customer question:
{user_input}

Retrieved context:
{context_text}
"""

    response = model.invoke(prompt)

    return response.content


def run_rag(user_input):
    vector_store = build_vector_store()

    retrieval_context = retrieve_context(
        user_input,
        vector_store,
    )

    actual_output = generate_answer(
        user_input,
        retrieval_context,
    )

    return actual_output, retrieval_context


if __name__ == "__main__":
    question = (
        "Can I cancel my order after it has been shipped, "
        "and how will my refund be processed?"
    )

    answer, context = run_rag(question)

    print("\nQuestion:")
    print(question)

    print("\nRetrieved Context:")
    for item in context:
        print(f"- {item}")

    print("\nRAG Answer:")
    print(answer)