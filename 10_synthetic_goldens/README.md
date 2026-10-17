# Synthetic Goldens with DeepEval

Manually creating a few AI test cases is manageable. Real AI systems, however, may require hundreds of test cases covering business rules, boundaries, negative scenarios, privacy and safety.

This example demonstrates how DeepEval’s `Synthesizer` can generate candidate goldens automatically from a business policy document.

## What is a synthetic golden?

A synthetic golden is an AI-generated test case created from source material such as:

- Business requirements
- Policy documents
- Knowledge-base articles
- Product documentation
- User stories and acceptance criteria

A generated golden can contain:

- `input` — a realistic user question
- `expected_output` — the expected correct behaviour
- `context` — the source information supporting the answer

## Project files

```text
10_synthetic_goldens/
├── hotel_booking_policy.txt
├── generate_goldens.py
├── synthetic_goldens.json
├── approved_goldens.json
└── README.md
```

### `hotel_booking_policy.txt`

The source business policy used by DeepEval to generate test cases.

### `generate_goldens.py`

Reads the policy document and uses DeepEval’s `Synthesizer` with `gpt-4o-mini` to generate candidate goldens.

### `synthetic_goldens.json`

Contains the raw AI-generated test cases. These cases have not yet been approved for regression testing.

### `approved_goldens.json`

Contains the reviewed, corrected and approved test cases.

## Workflow

```text
Business policy
      ↓
DeepEval Synthesizer
      ↓
Synthetic goldens
      ↓
Human QA review
      ↓
Approved dataset
      ↓
AI evaluation and regression testing
```

## Setup

Activate the shared virtual environment from this folder:

```bash
source ../.venv/bin/activate
```

Install the required packages:

```bash
python -m pip install deepeval chromadb python-dotenv
```

Add the OpenAI API key to the `.env` file stored in the project root:

```text
OPENAI_API_KEY=your_api_key_here
```

Never commit the `.env` file or API key to GitHub.

## Generate synthetic goldens

Run:

```bash
python generate_goldens.py
```

DeepEval will:

1. Load the policy document.
2. Split the document into chunks.
3. Use ChromaDB during context construction.
4. Select source context.
5. Generate user questions.
6. Generate expected answers.
7. Save the results to `synthetic_goldens.json`.

## Result

The example generated six candidate goldens from one policy context.

The generated cases included questions about:

- Late cancellations
- Cancellation fees
- Booking-date changes
- Refund processing
- Cancellation verification

However, several questions repeated the same cancellation behaviour, and one expected answer introduced information that was not explicitly supported by the policy.

## Human QA review

The generated cases were reviewed for:

- Factual correctness
- Source grounding
- Natural user wording
- Duplicate coverage
- Unsupported assumptions
- Positive and negative scenarios
- Boundary conditions
- Privacy and safety risks

The reviewed dataset contains six approved cases covering:

- Free standard cancellation
- Late-cancellation fees
- Non-refundable bookings
- Booking-date changes
- Refund processing
- Booking privacy and identity verification

Each approved case also includes:

- Test-case ID
- Source file
- Tags
- Risk level
- Review status

## Validate the approved dataset

Run:

```bash
python -m json.tool approved_goldens.json
```

If the formatted JSON is printed without an error, the file contains valid JSON syntax.

## Important lesson

Synthetic generation creates test cases quickly, but generated test cases should not automatically become regression tests.

```text
Generation creates scale.
Human review creates trust.
```

An AI QA engineer remains responsible for validating coverage, correctness, business risk and expected behaviour before approving the dataset.

## Current scope

This example generates and reviews test cases. It does not yet execute them against an AI application.

The approved goldens can later be connected to:

- An LLM
- A RAG chatbot
- An AI agent
- DeepEval metrics
- An automated regression suite
- A CI/CD quality gate