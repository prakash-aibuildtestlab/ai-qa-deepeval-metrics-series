# 06 - Contextual Precision

Contextual Precision checks whether the most relevant retrieved context appears earlier in the retrieval results.

This is important in RAG testing because the LLM usually relies more on the top-ranked chunks.

## What we are testing

Question:

What is the refund period for a damaged item?

Expected output:

Customers can request a refund for damaged items within 14 days of delivery.

## Passing scenario

The RAG retriever returns the refund policy first.

Retrieved context:

1. Refund policy: Customers can request a refund for damaged items within 14 days of delivery.

Result: PASS

Why?

The most useful context is ranked at the top.

## Failing scenario

The correct refund policy is retrieved, but it appears after irrelevant context.

Retrieved context:

1. Standard delivery policy: Standard parcels usually arrive within 3 to 5 business days.
2. Damaged parcel policy: Customers should take clear photos of the damaged item.
3. Refund policy: Customers can request a refund for damaged items within 14 days of delivery.

Result: FAIL

Why?

The correct context exists, but it is ranked too low.

## Key learning

Contextual Relevancy asks:

Did we retrieve useful context?

Contextual Precision asks:

Did we rank the most useful context early enough?

A RAG system can retrieve the right document and still fail if the ranking is poor.

## Real RAG note

In this example, the passing case uses the RAG retriever from the previous example.

The failing case uses a controlled poor retrieval order to show how the metric detects ranking problems.