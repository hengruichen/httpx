import pytest

from llm_fixer import LLMFixer


@pytest.mark.parametrize(
    "input_text,expected_text",
    [
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a test.",
            "This is a test.",
        ),
        (
            "This is a test. This is a test. This is a test. This is a