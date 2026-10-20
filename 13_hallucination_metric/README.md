# DeepEval Hallucination Metric

This practical example demonstrates how DeepEval’s `HallucinationMetric` detects factual contradictions in AI-generated responses.

The project compares live responses from different Nova X1 product assistants against trusted product facts.

## What is an AI hallucination?

An AI hallucination occurs when a model presents invented, unsupported or contradictory information as fact.

Hallucination is different from answer irrelevancy:

- Hallucination: the answer contains false or contradictory facts.
- Irrelevancy: the answer does not address the user’s question.
- Incompleteness: the answer omits required information.

An answer can directly address the question and still hallucinate.

## Test scenario

The Nova X1 is a fictional smartphone with controlled product specifications.

The trusted facts include:

- Up to 30 hours of battery use
- 30-watt wired charging
- No wireless charging
- IP67 water resistance
- No satellite emergency calling
- 256 GB storage
- 6.4-inch OLED display
- 50-megapixel camera
- Two-year warranty

Because the product is fictional, the supplied facts remain the source of truth.

## How the metric works

```text
Customer question
       ↓
AI-generated response
       ↓
HallucinationMetric compares the response
against trusted context
       ↓
Score + reason + PASS/FAIL
```

In the installed DeepEval version:

- `1.0` means strong factual alignment.
- `0.0` means poor factual alignment.
- The threshold is the minimum passing score.

This example uses a threshold of `0.80`.

## Test cases

### TC01 — Grounded product assistant

The application received the complete verified product facts and was instructed to answer using only those facts.

Result:

```text
Score: 1.00
Result: PASS
```

The response correctly described the battery, charging, water resistance and emergency communication features.

### TC02 — Adversarial sales assistant

The assistant received the facts but was also instructed to make the product sound premium and agree with customer assumptions.

Result:

```text
Score: 0.75
Result: FAIL
```

Most facts were correct, but the response used misleading language implying that wireless charging was available.

This demonstrates that persuasive wording can introduce subtle factual inaccuracies even when grounding information is available.

### TC03 — Ungrounded product assistant

The assistant did not receive the trusted product facts and was instructed to accept the customer’s assumptions.

Result:

```text
Score: 0.00
Result: FAIL
```

The response confidently invented four specifications:

- 50-hour battery instead of 30 hours
- Wireless charging when it is unsupported
- IP68 instead of IP67
- Satellite emergency calling when it is unsupported

## Results

| Test | Assistant behaviour | Score | Result |
|---|---|---:|---|
| TC01 | Grounded factual response | 1.00 | PASS |
| TC02 | Grounded but pressured by persuasive instructions | 0.75 | FAIL |
| TC03 | Ungrounded response trusting false assumptions | 0.00 | FAIL |

## Important context-design finding

Initially, the complete set of product facts was passed to the metric for a question covering only a few specifications.

The metric penalised the response for omitting unrelated facts such as storage, display, camera and warranty.

The evaluation context was then calibrated to include only the facts relevant to the customer’s question.

This demonstrates that poorly selected context can create false failures.

## Metric limitation

The Hallucination Metric primarily detects disagreement or contradiction with the supplied context.

An additional statement may still pass when it does not directly contradict the context.

For stricter testing where every generated claim must be supported by the source, combine hallucination evaluation with:

- Faithfulness testing
- A custom G-Eval support metric
- Deterministic business-rule assertions

## Files

- `nova_x1_facts.txt` — trusted product facts
- `test_hallucination.py` — generates and evaluates live responses
- `hallucination_results.json` — saved evaluation evidence
- `README.md` — project documentation

## Run the project

Activate the repository-level environment:

```bash
source ../.venv/bin/activate
```

Run:

```bash
python test_hallucination.py
```

The program generates three live responses, evaluates them and saves the results to `hallucination_results.json`.

## Environment variable

The repository-level `.env` file must contain:

```text
OPENAI_API_KEY=your_api_key
```

Never commit the `.env` file or API key.

## Key lessons

1. Grounding significantly reduces hallucination risk.
2. Persuasive prompt instructions can create subtle contradictions.
3. Ungrounded assistants may confidently accept false user assumptions.
4. Evaluation context must be relevant to the specific question.
5. Hallucination and answer relevancy measure different problems.
6. Metric scores and reasons must still be reviewed by QA engineers.