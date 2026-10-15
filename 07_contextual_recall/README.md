# Contextual Recall

Contextual Recall evaluates whether a RAG retriever returned all the
information required to produce the expected answer.

## Test Scenario

A customer asks:

> I missed my parcel delivery. What do I need to collect it, and how long will it be held?

The expected answer requires:

- Valid photo identification
- Collection notification or tracking number
- A holding period of 10 business days

## Passing Scenario

The real RAG retriever returns both:

- Parcel collection requirements
- Parcel holding period

Result: PASS

## Failing Scenario

The controlled incomplete retrieval returns only the collection requirements.

It misses the 10-business-day holding period.

Result: FAIL — Contextual Recall score 0.50

## Run

From the repository root:

```bash
source .venv/bin/activate
cd 07_contextual_recall
python test_contextual_recall.py