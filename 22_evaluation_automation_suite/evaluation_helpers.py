import json
import re
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
CASES_FILE = MODULE_DIR / "evaluation_cases.json"
BASELINE_FILE = MODULE_DIR / "approved_baseline.json"


def load_json(file_path: Path) -> dict[str, Any]:
    """Load and return a JSON document."""
    with file_path.open(encoding="utf-8") as file:
        return json.load(file)


def load_cases() -> list[dict[str, Any]]:
    """Load all evaluation test cases."""
    document = load_json(CASES_FILE)
    return document["test_cases"]


def load_baseline() -> dict[str, Any]:
    """Load the approved regression baseline."""
    return load_json(BASELINE_FILE)


def get_cases_by_marker(marker: str) -> list[dict[str, Any]]:
    """Return test cases assigned to a pytest suite marker."""
    return [
        case
        for case in load_cases()
        if marker in case.get("markers", [])
    ]


def normalize_text(value: str) -> str:
    """Normalize text for deterministic comparisons."""
    return " ".join(value.lower().split())


def check_required_phrases(
    output: str,
    required_phrases: list[str],
) -> list[str]:
    """Return required phrases that are missing from the output."""
    normalized_output = normalize_text(output)

    return [
        phrase
        for phrase in required_phrases
        if normalize_text(phrase) not in normalized_output
    ]


def check_forbidden_phrases(
    output: str,
    forbidden_phrases: list[str],
) -> list[str]:
    """Return forbidden phrases found in the output."""
    normalized_output = normalize_text(output)

    return [
        phrase
        for phrase in forbidden_phrases
        if normalize_text(phrase) in normalized_output
    ]


def check_numbered_options(output: str) -> list[str]:
    """
    Validate the controlled response format used by AUTO-008.

    Expected structure:

    Available options:
    1. ...
    2. ...
    Please choose one option.
    """
    failures: list[str] = []

    lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]

    numbered_lines = [
        line
        for line in lines
        if re.match(r"^\d+\.\s+\S", line)
    ]

    if len(numbered_lines) != 2:
        failures.append(
            "Expected exactly two numbered options."
        )
        return failures

    if not numbered_lines[0].startswith("1."):
        failures.append("The first option must start with '1.'.")

    if not numbered_lines[1].startswith("2."):
        failures.append("The second option must start with '2.'.")

    if not any(
        normalize_text(line) == "please choose one option."
        for line in lines
    ):
        failures.append(
            "Expected the closing instruction: "
            "'Please choose one option.'"
        )

    return failures


def evaluate_case(
    case: dict[str, Any],
    actual_output: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate one response using deterministic rules.

    When no actual output is supplied, the approved output stored in the
    dataset is evaluated.
    """
    output = (
        actual_output
        if actual_output is not None
        else case["approved_output"]
    )

    missing_required = check_required_phrases(
        output,
        case.get("required_phrases", []),
    )

    forbidden_found = check_forbidden_phrases(
        output,
        case.get("forbidden_phrases", []),
    )

    failed_checks: list[str] = []

    for phrase in missing_required:
        failed_checks.append(
            f"Missing required phrase: {phrase}"
        )

    for phrase in forbidden_found:
        failed_checks.append(
            f"Forbidden phrase found: {phrase}"
        )

    check_type = case.get("check_type", "contains")

    if check_type == "numbered_options":
        failed_checks.extend(
            check_numbered_options(output)
        )
    elif check_type != "contains":
        failed_checks.append(
            f"Unsupported check type: {check_type}"
        )

    result = "PASS" if not failed_checks else "FAIL"

    return {
        "test_id": case["test_id"],
        "name": case["name"],
        "severity": case["severity"],
        "markers": case["markers"],
        "check_type": check_type,
        "result": result,
        "passed": result == "PASS",
        "failed_checks": failed_checks,
        "actual_output": output,
    }


def evaluate_cases(
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate a collection of test cases."""
    return [
        evaluate_case(case)
        for case in cases
    ]