# RAG Metric Diagnosis with DeepEval

This example demonstrates how different DeepEval metrics diagnose different failures in a RAG pipeline.

## Question

Can I cancel my order after it has been shipped, and how will my refund be processed?

## RAG Pipeline

The example uses:

- OpenAI embeddings
- In-memory vector store
- Similarity search
- GPT-4o-mini for answer generation
- DeepEval for evaluation

## Metrics Tested

| Metric | What it tests | Failure introduced |
|---|---|---|
| Contextual Relevancy | Whether retrieved context is relevant to the question | Unrelated password documents |
| Contextual Precision | Whether relevant documents are ranked higher | Correct documents placed at lower ranks |
| Contextual Recall | Whether all required information was retrieved | Refund-processing information removed |
| Faithfulness | Whether the answer is supported by retrieved context | Answer contradicts the policies |

## Results

| Metric | Score | Threshold | Result |
|---|---:|---:|---|
| Contextual Relevancy | 0.00 | 0.70 | FAIL |
| Contextual Precision | 0.42 | 0.70 | FAIL |
| Contextual Recall | 0.67 | 0.70 | FAIL |
| Faithfulness | 0.50 | 0.70 | FAIL |

Scores may vary slightly because the evaluation is performed by an LLM judge.

## Diagnosis

```text
Relevancy failure  → Inspect retrieval relevance
Precision failure  → Inspect document ranking
Recall failure     → Inspect retrieval coverage
Faithfulness failure → Inspect prompt and LLM generation