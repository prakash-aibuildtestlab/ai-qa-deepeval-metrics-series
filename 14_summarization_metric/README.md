# DeepEval Summarization Metric

This project demonstrates how to evaluate AI-generated summaries using
DeepEval's `SummarizationMetric`.

## Scenario

An AI assistant summarizes a fictional airline disruption report for
Flight SB218 from Melbourne to Singapore.

## What the Metric Evaluates

The Summarization Metric evaluates two dimensions:

1. **Alignment** — Does the summary agree with the original document?
2. **Coverage** — Does the summary include the required information?

The final score is:

```text
Summarization Score = min(Alignment Score, Coverage Score)