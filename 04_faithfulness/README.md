# 04 - Faithfulness

Faithfulness checks whether the AI answer is supported by the provided context.

This is very important in RAG testing because an answer can sound correct, but still be unsupported by the retrieved documents.

## What we are testing

Question:

What is the refund period for a damaged item?

Retrieval context:

- Customers can request a refund for damaged items within 14 days of delivery.
- Refund requests must include the order number and photos of the damaged item.

## Test scenarios

### Passing scenario

The AI answers:

The refund period for a damaged item is 14 days after delivery.

This passes because the answer is supported by the retrieval context.

### Failing scenario

The answer says:

Customers can request a refund for damaged items within 30 days of delivery.

This fails because the retrieval context says 14 days, not 30 days.

## Why this matters

In RAG applications, the AI should not invent facts.

Faithfulness helps us check whether the final answer is grounded in the retrieved context.