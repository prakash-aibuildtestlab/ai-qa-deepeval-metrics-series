# 05 - Contextual Relevancy

Contextual Relevancy checks whether the retrieved context is relevant to the user's question.

This is important in RAG testing because the final answer depends on the quality of the retrieved documents.

## What we are testing

Question:

What is the refund period for a damaged item?

The RAG retriever should return context related to the refund policy for damaged items.

## Passing scenario

Retrieved context:

Refund policy: Customers can request a refund for damaged items within 14 days of delivery. Refund requests must include the order number and photos of the damaged item.

Result: PASS

Why?

The retrieved context directly answers the user's question.

## Failing scenario

Retrieved context:

Customers can change their account password from the profile settings page.

Two-factor authentication can be enabled from security settings.

Result: FAIL

Why?

The retrieved context is not related to refund period or damaged items.

## Key learning

Contextual Relevancy checks retrieval quality.

It does not test whether the final answer is faithful.

Faithfulness asks:

Is the answer supported by the context?

Contextual Relevancy asks:

Is the retrieved context relevant to the question?

## Real RAG note

In this example, we use a small RAG flow:

documents -> embeddings -> in-memory vector store -> retriever -> retrieved context -> DeepEval metric

In a real project, the same idea applies with PDFs, policy documents, websites, databases, or vector databases.