# DeepEval vs RAGAS: RAG Metric Comparison

This example compares five RAG evaluation concepts previously tested with DeepEval against their native RAGAS equivalents.

The purpose is not to prove that one framework is better. It is to understand how different evaluation frameworks test similar RAG quality dimensions.

## Metrics covered

| Evaluation goal | DeepEval | RAGAS |
|---|---|---|
| Did the response address the question? | Answer Relevancy | Answer Relevancy |
| Was the response grounded in the context? | Faithfulness | Faithfulness |
| Were the retrieved documents relevant? | Contextual Relevancy | Context Relevance |
| Were relevant documents ranked higher? | Contextual Precision | Context Precision |
| Did retrieval include all required information? | Contextual Recall | Context Recall |

## Business scenario

**Question:**

> Can I cancel my order after it has been shipped, and how will my refund be processed?

The test data includes:

- A correct response
- A hallucinated response
- Relevant retrieved contexts
- Poorly ranked contexts
- Incomplete retrieved contexts

These controlled scenarios help us identify which part of the RAG pipeline is failing.

## Results

Threshold: `0.70`

| RAGAS metric | Score | Result |
|---|---:|---|
| Answer Relevancy | 0.73 | PASS |
| Faithfulness | 0.00 | FAIL |
| Context Relevance | 1.00 | PASS |
| Context Precision | 0.33 | FAIL |
| Context Recall | 0.67 | FAIL |

## What the results tell us

### Answer Relevancy — PASS

The response addressed both the cancellation and refund questions.

### Faithfulness — FAIL

The test response claimed that the order could be cancelled after shipment and that the refund would be issued as store credit within 24 hours.

Both claims contradicted the retrieved policies.

### Context Relevance — PASS

The cancellation and refund documents were directly related to the user’s question.

### Context Precision — FAIL

Irrelevant documents were placed before the useful cancellation and refund documents.

This shows that retrieving the correct documents is not enough. Their ranking also matters.

### Context Recall — FAIL

The retrieved context included the cancellation policy but omitted the refund-processing policy.

The expected answer contained approximately three required claims, while the retrieved context supported only two, producing a score of `0.67`.

## How to run

Activate the shared virtual environment from the repository root:

```bash
source .venv/bin/activate