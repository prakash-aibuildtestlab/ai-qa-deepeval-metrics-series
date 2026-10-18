# LLM-as-a-Judge Basics

This example demonstrates how an LLM can evaluate another LLM’s response—and why the judge itself must also be tested.

## What are we testing?

A hotel-support LLM answers this question:

> Can I cancel my hotel booking 24 hours before check-in?

The policy states that cancellations made within 48 hours incur a fee equal to the first night’s accommodation.

The application response is generated dynamically using OpenAI. The same response is then evaluated twice using DeepEval’s `GEval` metric.

## Evaluation flow

1. Send the policy and question to the application LLM.
2. Capture its response.
3. Create a DeepEval test case.
4. Evaluate the identical response twice.
5. Compare the scores, verdicts and reasons.
6. Save the comparison as JSON.

## Why use the same response twice?

If we generated a different response for every evaluation, we would not know whether a score difference came from:

- The application LLM
- The evaluation model

Using the same response isolates the behaviour of the LLM judge.

## Result observed

The calibrated evaluation produced:

| Run | Score | Threshold | Result |
|---|---:|---:|---|
| Judge Run 1 | 0.61 | 0.70 | FAIL |
| Judge Run 2 | 0.71 | 0.70 | PASS |

The same response received two different verdicts.

One judge reason also incorrectly claimed that the actual output explicitly confirmed cancellation and that the expected output did not. The opposite was true.

## Key lesson

An LLM judge can provide semantic evaluation, numerical scores and detailed reasons. However, it remains an AI system and can produce inconsistent scores or incorrect reasoning.

Do not treat one LLM-generated score as absolute truth.

In a real evaluation framework:

- Define precise evaluation criteria.
- Use human-reviewed expected outputs.
- Inspect the judge’s reason.
- Repeat or aggregate borderline evaluations.
- Combine semantic metrics with deterministic checks.
- Send uncertain results for human review.
- Calibrate thresholds using labelled test cases.

## Files

- `test_llm_judge.py` – generates and evaluates the response
- `comparison_results.json` – latest evaluation result
- `comparison_results_before_calibration.json` – result before rubric calibration
- `comparison_results_after_calibration.json` – result after calibration

## Run the example

Activate the repository-level virtual environment:

```bash
source ../.venv/bin/activate