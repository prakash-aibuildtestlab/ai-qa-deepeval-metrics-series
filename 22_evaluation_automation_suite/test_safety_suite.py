import pytest

from evaluation_helpers import evaluate_case, get_cases_by_marker


SAFETY_CASES = get_cases_by_marker("safety")


@pytest.mark.safety
@pytest.mark.deterministic
@pytest.mark.parametrize(
    "case",
    SAFETY_CASES,
    ids=[case["test_id"] for case in SAFETY_CASES],
)
def test_approved_safety_behaviour(case):
    """
    Verify privacy, role-boundary and unsupported-action
    safety requirements.
    """
    result = evaluate_case(case)

    assert result["passed"], (
        f'{result["test_id"]} failed:\n'
        + "\n".join(result["failed_checks"])
    )