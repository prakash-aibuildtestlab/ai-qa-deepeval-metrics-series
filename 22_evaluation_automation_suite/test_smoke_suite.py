import pytest

from evaluation_helpers import evaluate_case, get_cases_by_marker


SMOKE_CASES = get_cases_by_marker("smoke")


@pytest.mark.smoke
@pytest.mark.deterministic
@pytest.mark.parametrize(
    "case",
    SMOKE_CASES,
    ids=[case["test_id"] for case in SMOKE_CASES],
)
def test_approved_smoke_behaviour(case):
    """
    Verify essential chatbot behaviour using fast,
    deterministic checks.
    """
    result = evaluate_case(case)

    assert result["passed"], (
        f'{result["test_id"]} failed:\n'
        + "\n".join(result["failed_checks"])
    )