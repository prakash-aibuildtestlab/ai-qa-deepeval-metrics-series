# Multi-Turn Conversation Evaluation Suite

This module demonstrates how to evaluate a multi-turn customer-support chatbot using DeepEval conversational metrics.

The example uses a fictional parcel-delivery support chatbot that must:

- Verify customer information
- Explain a delayed parcel’s status
- Offer valid resolution options
- Remember the selected resolution and delivery address
- Provide the correct next step and case reference
- Refuse requests outside its parcel-support role

## Metrics Covered

| Metric | Question answered |
|---|---|
| Knowledge Retention | Did the chatbot remember facts from earlier turns? |
| Turn Relevancy | Was every assistant response relevant to the conversation? |
| Conversation Completeness | Did the chatbot address all valid customer intentions? |
| Role Adherence | Did the chatbot remain within its assigned role? |

## Test Scenario

The customer provides the following information:

- Order number: `ORD-2048`
- Registered email: `alex.morgan@example.com`
- Expected delivery date: `20 October 2026`
- Selected resolution: Replacement
- New delivery address: `55 Bourke Street, Melbourne VIC 3000`

The parcel is delayed by six business days.

The chatbot must confirm the replacement, remember the new address, explain that the support team will process the request and provide case reference `CASE-7781`.

## Positive Conversation Results

The live chatbot conversation was evaluated with four metrics.

| Metric | Score | Threshold | Result |
|---|---:|---:|---|
| Knowledge Retention | 1.00 | 0.80 | PASS |
| Turn Relevancy | 1.00 | 0.80 | PASS |
| Conversation Completeness | 1.00 | 0.80 | PASS |
| Role Adherence | 1.00 | 0.80 | PASS |

### Knowledge Retention

The chatbot correctly remembered:

- Order number
- Expected delivery date
- Replacement choice
- New delivery address
- Case reference

### Turn Relevancy

Every assistant response remained relevant to the customer’s parcel-delivery questions.

### Conversation Completeness

The chatbot addressed all valid customer intentions:

- Verified the order
- Explained the parcel status
- Presented replacement and refund options
- Confirmed the replacement
- Remembered the new address
- Explained the next step
- Provided the case reference

### Role Adherence

When asked to write a wedding speech, the chatbot explicitly refused the unrelated request and remained within its parcel-support role.

Example:

```text
I'm here to assist with parcel-delivery support only, so I can't help
with writing a wedding speech. If you have any questions regarding
your parcel or delivery, feel free to ask.
```

## Controlled Negative Tests

Each negative test introduces one deliberate chatbot defect and evaluates it using only the relevant metric.

| Negative scenario | Metric | Score | Expected result |
|---|---|---:|---|
| Chatbot changes the replacement address | Knowledge Retention | 0.50 | FAIL |
| Chatbot answers a parcel question with wedding content | Turn Relevancy | 0.50 | FAIL |
| Chatbot ignores the replacement request and case reference | Conversation Completeness | 0.00 | FAIL |
| Chatbot writes the requested wedding speech | Role Adherence | 0.00 | FAIL |

The negative results are expected. They demonstrate that each metric detects the defect it was designed to identify.

## What Each Metric Detected

### Knowledge Retention Metric

This metric checks whether facts established earlier in the conversation are remembered correctly.

The negative response changed:

```text
55 Bourke Street, Melbourne VIC 3000
```

to:

```text
18 Collins Street, Melbourne VIC 3000
```

The metric scored the conversation `0.50`.

### Turn Relevancy Metric

This metric checks whether each assistant message is relevant to the current user message and conversation context.

The negative assistant response provided wedding-speech content when the customer asked about parcel resolution options.

The metric scored the conversation `0.50`.

### Conversation Completeness Metric

This metric checks whether the chatbot addressed all valid user intentions across the complete conversation.

The negative response failed to:

- Confirm the replacement
- Confirm the delivery address
- Explain the next step
- Provide the case reference

The metric scored the conversation `0.00`.

### Role Adherence Metric

This metric checks whether the chatbot remains within its assigned identity, scope and behavioural rules.

The negative response complied with the wedding-speech request even though the chatbot was restricted to parcel support.

The metric scored the conversation `0.00`.

## Important Evaluation-Design Lessons

### 1. Keep conflicting objectives in separate test cases

An earlier version included the wedding-speech challenge inside the main customer journey.

This created a conflict:

- Role Adherence expected the chatbot to refuse it.
- Conversation Completeness treated it as an unfulfilled user intention.
- Turn Relevancy treated the refusal as unrelated to the wedding request.

The role challenge was therefore moved into a dedicated Role Adherence test.

### 2. Make facts explicit

The Knowledge Retention judge initially inferred an incorrect relationship between the order number and expected delivery date.

The customer message was updated to state the expected delivery date explicitly.

This gave the evaluator clear evidence and removed the false failure.

### 3. Redirecting is not always the same as refusing

The first role-safe response only redirected the user:

```text
I'm here to assist with parcel-delivery support.
```

The evaluator scored it `0.50` because the policy required an explicit refusal.

After the chatbot clearly stated that it could not write the speech, the result improved to `1.00`.

### 4. Evaluate one controlled defect at a time

Each controlled negative scenario is measured using only its corresponding metric.

This makes failures easier to diagnose and prevents one deliberate defect from creating unrelated metric failures.

### 5. Read the reason, not only the score

LLM-based evaluators can misunderstand:

- Which speaker produced a message
- Whether a refusal is relevant
- Whether a customer intention is valid
- Which facts were established earlier

Metric results should be reviewed as evidence, not treated as unquestionable truth.

## Project Files

```text
20_conversation_evaluation_suite/
├── README.md
├── HOW_TO_RUN.txt
├── requirements.txt
├── parcel_support_policy.txt
├── conversation_evaluation_results.json
└── test_conversation_evaluation_suite.py
```

## Installation

Create and activate a Python virtual environment from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the module dependencies:

```bash
python -m pip install -r 20_conversation_evaluation_suite/requirements.txt
```

## OpenAI API Key

Create a `.env` file in the repository root:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

Do not commit the real `.env` file or API key to GitHub.

## Run the Suite

From the repository root:

```bash
cd 20_conversation_evaluation_suite
python -m py_compile test_conversation_evaluation_suite.py
python test_conversation_evaluation_suite.py
```

## Validate the Results File

```bash
python -m json.tool conversation_evaluation_results.json > /dev/null \
  && echo "Results JSON is valid"
```

## Expected Test Summary

```text
Positive scenarios: 4
Positive scenarios passed: 4

Controlled negative scenarios: 4
Expected failures detected: 4

Unexpected results: 0
```

## Metric Selection Guide

| Testing requirement | Recommended metric |
|---|---|
| Remember customer facts across turns | Knowledge Retention |
| Keep every answer relevant | Turn Relevancy |
| Complete the customer’s valid goal | Conversation Completeness |
| Stay within the chatbot’s assigned scope | Role Adherence |

## Key Takeaway

A successful multi-turn chatbot must do more than generate a good final answer.

It must:

1. Remember information from earlier turns.
2. Keep every response relevant.
3. Complete all valid customer intentions.
4. Remain within its assigned role.

Testing these behaviours separately makes conversation failures easier to identify, explain and fix.