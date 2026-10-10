# Goldens and Datasets in AI QA Testing

In traditional QA, a test case usually has steps and an expected result.

In AI QA, we often use goldens.

A golden is a test case for an AI system. It defines the input, expected behaviour, and evaluation criteria.

## Why goldens are important

LLM outputs are not always fixed.

The same question can be answered in different words and still be correct.

So instead of only checking exact text, we use goldens to define what good behaviour looks like.

## Example golden

```json
{
  "input": "Where is my parcel ORD-1042?",
  "expected_output": "The response should provide the parcel status and ETA.",
  "expected_tools": ["get_order_status"],
  "tags": ["parcel_tracking", "agent", "happy_path"]
}
