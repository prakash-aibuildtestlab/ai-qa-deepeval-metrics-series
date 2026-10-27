# JSON Correctness Metric

This project demonstrates how to validate an AI-generated structured response using DeepEval's `JsonCorrectnessMetric` and a strict Pydantic schema.

## Scenario

A cybersecurity assistant reads an incident report and converts it into structured JSON for use by downstream systems such as:

- Incident management platforms
- Security dashboards
- APIs
- Databases
- Automated workflows

## What JSON Correctness Tests

The metric validates whether the output:

- Is syntactically valid JSON
- Contains all required fields
- Uses the correct data types
- Uses permitted values for restricted fields
- Contains no unexpected fields

## Expected Schema

```python
class IncidentSchema(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    incident_id: StrictStr
    affected_service: StrictStr
    severity: Literal["low", "medium", "high", "critical"]
    customer_impact: StrictStr
    records_exposed: StrictInt
    requires_escalation: StrictBool
    status: Literal["investigating", "contained", "resolved"]
```

`strict=True` prevents automatic type conversion, and `extra="forbid"` rejects unexpected fields.

## Test Scenarios

| Test ID | Scenario | Score | Result |
|---|---|---:|---|
| JSON01 | Valid and factually accurate JSON | 1.00 | PASS |
| JSON02 | Missing field, incorrect types and invalid values | 0.00 | FAIL |
| JSON03 | Valid schema but factually incorrect values | 1.00 | PASS |

## Key Finding

JSON Correctness validates the **structure**, not the **truthfulness of the values**.

The third test passes because its fields and data types satisfy the schema, even though the extracted incident information is incorrect.

Therefore, a production evaluation suite should combine:

- `JsonCorrectnessMetric` for JSON structure
- Deterministic assertions or G-Eval for value accuracy

## Run the Test

Activate the repository virtual environment:

```bash
source ../.venv/bin/activate
```

Run:

```bash
python test_json_correctness.py
```

## Project Files

```text
16_json_correctness_metric/
├── README.md
├── incident_report.txt
├── json_correctness_results.json
└── test_json_correctness.py
```

## Main Lesson

> Schema-valid JSON is not necessarily factually correct JSON.