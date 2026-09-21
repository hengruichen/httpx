import os
import sys
from pathlib import Path

import pytest

from llm_evals.registry import registry
from llm_evals.tasks.system import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_WITH_SYSTEM,
    SYSTEM_PROMPT_WITH_USER,
    SYSTEM_PROMPT_WITH_USER_AND_SYSTEM,
)


@pytest.mark.parametrize(
    "system_prompt",
    [
        SYSTEM_PROMPT_WITH_SYSTEM,
        SYSTEM_PROMPT_WITH_USER_AND_SYSTEM,
        SYSTEM_PROMPT_WITH_USER,
        SYSTEM_PROMPT,
    ],
)
def test_system_prompt(system_prompt):
    # Test that the system prompt is a string
    assert isinstance(system_prompt, str)

    # Test that the system prompt is not empty
    assert len(system_prompt) > 0

    # Test that the system prompt contains the expected placeholders
    assert "{{user}}" in system_prompt
    assert "{{assistant}}" in system_prompt

    # Test that the system prompt contains the expected system message
    if "{{system}}" in system_prompt:
        assert "You are a helpful assistant." in system_prompt

    # Test that the system prompt contains the expected user message
    if "{{user}}" in system_prompt:
        assert "You are a helpful assistant." in system_prompt

    # Test that the system prompt contains the expected assistant message
    if "{{assistant}}" in system_prompt:
        assert "You are a helpful assistant." in system_prompt

    # Test that the system prompt contains the expected system message
    if "{{system}}" in system_prompt:
        assert "{{system}}" in system_prompt

    # Test that the system prompt contains the expected user message
    if "{{user}}" in system_prompt:
        assert "{{user}}" in system_prompt

    # Test that the system prompt contains the expected assistant message
    if "{{assistant}}" in system_prompt:
        assert "{{assistant}}" in system_prompt

    # Test that the system prompt contains the expected system message
    if "{{system}}" in system_prompt:
        assert "{{system}}" in system_prompt

    # Test that the system prompt contains the expected user message
    if "{{user}}" in system_prompt:
        assert "{{user}}" in system_prompt

    # Test that the system prompt contains the expected assistant message
    if "{{assistant}}" in system_prompt:
        assert "{{assistant}}" in system_prompt

    # Test that the system prompt contains the expected system message
    if "{{system}}" in system_prompt:
        assert "{{system}}" in system_prompt

    # Test that the system prompt contains the expected user message
    if "{{user}}" in system_prompt:
        assert "{{user}}" in system_prompt

    # Test that the system prompt contains the expected assistant message
    if "{{assistant}}" in system_prompt:
        assert "{{assistant}}" in system_prompt

    # Test that the system prompt contains the expected system message
    if "{{system}}" in system_prompt:
        assert "{{system}}" in