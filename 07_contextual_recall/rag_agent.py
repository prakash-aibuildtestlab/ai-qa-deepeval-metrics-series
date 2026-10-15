import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# Load the shared .env file from the repository root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


DOCUMENTS = [
    Document(
        page_content=(
            "Parcel collection requirements: To collect a missed parcel "
            "from the post office, the customer must bring valid photo "
            "identification and the collection notification or tracking number."
        )
    ),
    Document(
        page_content=(
            "Parcel holding period: Missed parcels are held at the nominated "
            "post office for 10 business days. After this period, the parcel "
            "may be returned to the sender."
        )
    ),
    Document(
        page_content=(
            "Redelivery policy: Eligible parcels may be scheduled for "
            "redelivery through the customer portal."
        )
    ),
    Document(
        page_content=(
            "Address update policy: Customers can update their delivery "
            "preferences before the parcel reaches the delivery facility."
        )
    ),
]


def build_vector_store():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vector_store = InMemoryVectorStore(embeddings)

    vector_store.add_documents(DOCUMENTS)

    return vector_store


def retrieve_context(user_input, vector_store):
    documents = vector_store.similarity_search(
        user_input,
        k=2,
    )

    return [document.page_content for document in documents]


def generate_answer(user_input, retrieval_context):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    context_text = "\n\n".join(retrieval_context)

    prompt = f"""
You are a parcel-support assistant.

Answer the customer's question using only the retrieved context.

If the retrieved context does not contain enough information,
say that the information is unavailable.

Customer question:
{user_input}

Retrieved context:
{context_text}
"""

    response = llm.invoke(prompt)

    return response.content


def run_rag(user_input):
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY is missing from the repository .env file."
        )

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
        "I missed my parcel delivery. What do I need to collect it, "
        "and how long will it be held?"
    )

    answer, context = run_rag(question)

    print("\nQuestion:")
    print(question)

    print("\nRetrieved Context:")
    for item in context:
        print(f"- {item}")

    print("\nRAG Answer:")
    print(answer)