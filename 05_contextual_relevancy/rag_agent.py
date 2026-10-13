import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


POLICY_DOCS = [
    (
        "Express delivery policy: Express parcels are usually delivered within "
        "1 to 2 business days."
    ),
    (
        "Standard delivery policy: Standard parcels are usually delivered within "
        "3 to 5 business days."
    ),
    (
        "International delivery policy: International parcels may take 7 to 14 "
        "business days depending on customs clearance."
    ),
    (
        "Damaged parcel policy: Customers should retain the parcel, packaging, "
        "and contents and take clear photographs of the damage. Damage should be "
        "reported to support as soon as possible for assessment."
    ),
    (
        "Refund policy: Customers can request a refund for damaged items within "
        "14 days of delivery. Refund requests must include the order number and "
        "photos of the damaged item."
    ),
    (
        "Parcel privacy policy: Support must not reveal another customer's name, "
        "address, contact details, or parcel contents."
    ),
]


def build_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = InMemoryVectorStore(embedding=embeddings)
    vector_store.add_texts(texts=POLICY_DOCS)
    return vector_store


def retrieve_context(user_input, vector_store):
    documents = vector_store.similarity_search(user_input, k=1)
    return [document.page_content for document in documents]


def generate_answer(user_input, retrieval_context):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your root .env file.")

    client = OpenAI(api_key=api_key)

    context_text = "\n".join(retrieval_context)

    prompt = f"""
You are a customer support assistant.

Answer the user question using only the context below.
If the context does not contain the answer, say that the available information is insufficient.

Context:
{context_text}

User question:
{user_input}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    return response.output_text


def run_rag(user_input):
    vector_store = build_vector_store()
    retrieval_context = retrieve_context(user_input, vector_store)
    actual_output = generate_answer(user_input, retrieval_context)

    return actual_output, retrieval_context