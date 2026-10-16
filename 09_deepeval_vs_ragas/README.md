# DeepEval vs RAGAS: Same RAG, Different Evaluation

This example compares DeepEval and RAGAS by evaluating the exact same output from a real RAG pipeline.

The RAG pipeline runs only once. Its question, generated answer, expected answer and retrieved documents are stored in one shared evaluation record.

That identical record is then passed to both frameworks.

## Why use one shared RAG record?

Running the RAG pipeline separately for each framework could produce different answers or retrieve different documents.

That would make the comparison unreliable.

The comparison flow is:

```text
User Question
      ↓
Real RAG Pipeline
      ↓
One Shared Evaluation Record
      ↓
 ┌───────────────┬───────────────┐
 │   DeepEval    │     RAGAS     │
 │   Evaluator   │   Evaluator   │
 └───────────────┴───────────────┘
      ↓                 ↓
        Compare Results

09_deepeval_vs_ragas/
├── rag_agent.py
├── deepeval_evaluator.py
├── ragas_evaluator.py
├── compare_deepeval_ragas.py
├── test_ragas_metrics.py
└── README.md

Business scenario
User question
Can I cancel my order after it has been shipped, and how will my refund be processed?

Retrieved context
1. Once an order has been dispatched, it cannot be cancelled. The customer may refuse delivery or return the item after receiving it.
2. After the returned item is received and inspected, the refund is issued to the original payment method within 5 to 7 business days.
RAG-generated answer
Once an order has been dispatched, it cannot be cancelled. You may refuse delivery or return the item after receiving it. After the returned item is received and inspected, the refund will be issued to the original payment method within 5 to 7 business days.

Metrics compared
Evaluation goal	DeepEval	RAGAS
Did the answer address the question?	Answer Relevancy	Answer Relevancy
Was the answer supported by the context?	Faithfulness	Faithfulness
Were the retrieved documents relevant?	Contextual Relevancy	Context Relevance
Were relevant documents ranked correctly?	Contextual Precision	Context Precision
Did retrieval contain all required information?	Contextual Recall	Context Recall


Comparison results
Threshold: 0.70
Metric	DeepEval	RAGAS	Comparison
Answer Relevancy	1.00 PASS	0.72 PASS	Same outcome, different score
Faithfulness	1.00 PASS	1.00 PASS	Complete agreement
Context Relevance	0.67 FAIL	1.00 PASS	Framework disagreement
Context Precision	1.00 PASS	1.00 PASS	Complete agreement
Context Recall	1.00 PASS	1.00 PASS	Complete agreement


Important finding
Both frameworks evaluated the exact same RAG evidence, but they did not produce identical scores.
The largest difference occurred in Context Relevance:
DeepEval: 0.67 — FAIL
RAGAS:    1.00 — PASS

The retrieved context contained both the cancellation and refund policies.
However, DeepEval’s LLM judge interpreted the contextual coverage differently, while RAGAS considered the complete context relevant.
Answer Relevancy also differed:
DeepEval: 1.00 — PASS
RAGAS:    0.72 — PASS

Both frameworks passed the response, but the numerical scores were significantly different.
Why can the scores differ?
The frameworks may use different:
- Evaluation prompts
- Scoring formulas
- Claim-decomposition methods
- Embedding calculations
- LLM-judge instructions
- Definitions of relevance
Similar metric names do not guarantee identical evaluation behaviour.