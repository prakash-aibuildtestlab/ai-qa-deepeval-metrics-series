# DeepEval Prompt Alignment Metric

This project demonstrates how to evaluate whether an AI response follows
the instructions defined in its prompt using DeepEval's
`PromptAlignmentMetric`.

## Scenario

A smart-home support assistant responds to a customer whose thermostat
screen is blank.

The assistant must follow five instructions:

1. Use an exact opening phrase.
2. Provide exactly three numbered troubleshooting lines.
3. Write one sentence in each numbered line.
4. Avoid unsafe internal electrical repair instructions.
5. Use an exact closing phrase.

## What Prompt Alignment Evaluates

Prompt Alignment asks:

> Did the AI follow the instructions defined in the prompt?

The score is calculated as:

```text
Prompt Alignment =
Instructions Followed / Total Instructions