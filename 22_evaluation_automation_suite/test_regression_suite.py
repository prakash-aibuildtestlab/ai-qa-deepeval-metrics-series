import json
import os
from pathlib import Path

import pytest

from evaluation_helpers import (
    evaluate_case,
    get_cases_by_marker,
    load_baseline,
)


MODULE_DIR = Path(__file__).resolve().parent

REGRESSION_CASES = get_cases_by_marker("regression")
BASELINE = load_baseline()

BASELINE_RESULTS = {
    item["test_id"]: item["expected_verdict"]
    for item in BASELINE["results"]
}

DATASET_IDS = {
    case["test_id"]
    for case in REGRESSION_CASES
}

BASELINE_IDS = set(BASELINE_RESULTS)

missing_from_baseline = DATASET_IDS - BASELINE_IDS
unknown_baseline_cases = BASELINE_IDS - DATASET_IDS

if missing_from_baseline or unknown_baseline_cases:
    raise RuntimeError(
        "Dataset and baseline do not match. "
        f"Missing from baseline: {sorted(missing_from_baseline)}. "
        f"Unknown baseline cases: {sorted(unknown_baseline_cases)}."
    )


def load_output_overrides() -> dict[str, str]:
    """
    Load optional candidate outputs.

    By default, no overrides are used and the approved outputs are tested.
    Set EVALUATION_OUTPUTS_FILE to test candidate or controlled outputs.
    """
    output_file = os.getenv("EVALUATION_OUTPUTS_FILE")

    if not output_file:
        return {}

    output_path = Path(output_file)

    if not output_path.is_absolute():
        output_path = MODULE_DIR / output_path

    if not output_path.exists():
        raise FileNotFoundError(
            f"Evaluation outputs file not found: {output_path}"
        )

    with output_path.open(encoding="utf-8") as file:
        document = json.load(file)

    return {
        item["test_id"]: item["actual_output"]
        for item in document["outputs"]
    }


OUTPUT_OVERRIDES = load_output_overrides()


@pytest.mark.regression
@pytest.mark.deterministic
@pytest.mark.parametrize(
    "case",
    REGRESSION_CASES,
    ids=[case["test_id"] for case in REGRESSION_CASES],
)
def test_output_matches_approved_baseline(case):
    """
    Compare the current result with the approved baseline.

    A baseline PASS changing to FAIL is a regression.
    """
    test_id = case["test_id"]

    actual_output = OUTPUT_OVERRIDES.get(
        test_id,
        case["approved_output"],
    )

    result = evaluate_case(
        case,
        actual_output=actual_output,
    )

    expected_verdict = BASELINE_RESULTS[test_id]
    actual_verdict = result["result"]

    assert actual_verdict == expected_verdict, (
        f"Regression detected for {test_id}: "
        f"baseline={expected_verdict}, current={actual_verdict}.\n"
        + "\n".join(result["failed_checks"])
    )