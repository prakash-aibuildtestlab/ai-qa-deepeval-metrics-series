import pytest

from evaluation_helpers import load_baseline, load_cases


@pytest.fixture(scope="session")
def evaluation_cases():
    """Provide the complete evaluation dataset."""
    return load_cases()


@pytest.fixture(scope="session")
def approved_baseline():
    """Provide the approved regression baseline."""
    return load_baseline()