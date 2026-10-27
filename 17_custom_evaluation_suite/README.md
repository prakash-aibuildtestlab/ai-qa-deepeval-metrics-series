Metric	         What it will test
G-Eval	         Overall semantic and business-rule correctness
DAG Metric	     A fixed step-by-step decision flow
Custom Metric	  Our own deterministic Python validation

# Custom Evaluation Suite

This project compares three approaches for evaluating the same AI-generated IT incident-triage response:

1. G-Eval
2. DAG Metric
3. Custom deterministic metric

## Scenario

An AI assistant reviews an IT incident and decides:

- Incident priority
- Assigned support team
- Whether escalation is required
- Policy-based reasoning

The test incident describes a complete VPN outage affecting approximately 150 remote employees.

## Expected Decision

```text
Priority: P1
Assigned team: Network Operations
Escalation required: Yes
```

## Why Three Evaluation Approaches?

### G-Eval

G-Eval performs a flexible semantic evaluation using business rules defined through evaluation steps.

It is useful when:

- Meaning matters more than exact wording
- Several related requirements must be evaluated together
- Human-like judgement is required

### DAG Metric

The DAG Metric evaluates the response through an explicit decision path:

```text
Correct priority?
    ↓
Correct team?
    ↓
Correct escalation?
    ↓
Final score
```

The terminal scores are controlled by the evaluator:

| Failure point | Score |
|---|---:|
| Incorrect priority | 0.00 |
| Incorrect team | 0.40 |
| Incorrect escalation | 0.70 |
| All decisions correct | 1.00 |

The scoring path is controlled, but the individual judgement nodes still use an LLM judge.

### Custom Metric

The custom metric inherits from DeepEval's `BaseMetric` and applies deterministic Python and regular-expression checks.

Scoring:

| Check | Weight |
|---|---:|
| Correct P1 priority | 0.50 |
| Correct Network Operations team | 0.25 |
| Correct escalation decision | 0.25 |

The passing threshold is `1.00`, so all three checks must pass.

## Results

| Test | G-Eval | DAG | Custom |
|---|---:|---:|---:|
| Correct response | 1.00 PASS | 1.00 PASS | 1.00 PASS |
| Incorrect team and escalation | 0.26 FAIL | 0.40 FAIL | 0.50 FAIL |

G-Eval scores can vary slightly between executions because an LLM judge produces the score.

## Important DAG Finding

The first version of the priority node used broad criteria. During the negative test, it incorrectly returned `False` even though the response explicitly assigned `P1`.

The node considered the incorrect escalation decision while evaluating priority.

The criteria were improved to isolate one decision:

```python
criteria=(
    "Evaluate only the priority assigned in the actual output. "
    "Return True if the actual output explicitly assigns Priority P1. "
    "Ignore the assigned team, escalation decision, explanation and "
    "all other errors."
)
```

After narrowing the criteria, the DAG followed the intended path:

```text
Priority P1 → True
Application Support → False
Terminal score → 0.40
```

## Key Comparison

| Approach | Evaluation style | Main advantage | Main limitation |
|---|---|---|---|
| G-Eval | LLM semantic judgement | Flexible and easy to configure | Score may vary |
| DAG | LLM decisions with controlled branches | Explicit decision flow and score mapping | Judgement nodes may still misinterpret broad criteria |
| Custom Metric | Python rules | Fast, repeatable and deterministic | Can be brittle when wording changes |

## Main Lesson

No single evaluation approach is best for every requirement.

- Use G-Eval for semantic quality and business-rule interpretation.
- Use a DAG for conditional rules and controlled scoring paths.
- Use custom Python metrics for exact, repeatable checks.
- Combine approaches when an AI system has both semantic and deterministic requirements.

## Run the Suite

Activate the repository virtual environment:

```bash
source ../.venv/bin/activate
```

Run:

```bash
python test_custom_evaluation_suite.py
```

## Project Files

```text
17_custom_evaluation_suite/
├── README.md
├── custom_evaluation_results.json
├── incident_triage_policy.txt
└── test_custom_evaluation_suite.py
```