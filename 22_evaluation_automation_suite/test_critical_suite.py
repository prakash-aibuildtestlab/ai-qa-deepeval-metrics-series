import pytest

from evaluation_helpers import evaluate_case, get_cases_by_marker


CRITICAL_CASES = get_cases_by_marker("critical")


@pytest.mark.critical
@pytest.mark.deterministic
@pytest.mark.parametrize(
    "case",
    CRITICAL_CASES,
    ids=[case["test_id"] for case in CRITICAL_CASES],
)
def test_approved_critical_behaviour(case):
    """
    Verify release-blocking business rules using
    deterministic checks.
    """
    result = evaluate_case(case)

    assert result["passed"], (
        f'{result["test_id"]} failed:\n'
        + "\n".join(result["failed_checks"])
    )