from scripts.docs_check import collect_errors as collect_doc_errors
from scripts.examples_check import collect_errors as collect_example_errors
from scripts.onboarding_check import collect_errors as collect_onboarding_errors


def test_docs_check_passes() -> None:
    assert collect_doc_errors() == []


def test_examples_check_passes() -> None:
    assert collect_example_errors() == []


def test_onboarding_check_passes() -> None:
    assert collect_onboarding_errors() == []
