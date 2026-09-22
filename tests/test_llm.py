import os
import re
from pathlib import Path

import pytest

from src.llm import LLM, LLMResponse, load_llm_response_from_file, save_llm_response_to_file


@pytest.fixture
def llm():
    return LLM()


@pytest.fixture
def llm_response():
    return LLMResponse(
        content="This is a test response.",
        metadata={"source": "test"},
        path="test_response.txt",
    )


def test_load_llm_response_from_file(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file(tmp_path: Path, llm_response: LLMResponse):
    # Save the LLMResponse to a temporary file
    file_path = tmp_path / "test_response.txt"
    save_llm_response_to_file(llm_response, file_path)

    # Assert that the file was created and contains the correct content
    assert file_path.exists()
    assert file_path.read_text() == llm_response.content


def test_save_llm_response_to_file_with_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test_response.txt"
    file_path.write_text("This is a test response.")

    # Load the LLMResponse from the file
    loaded_response = load_llm_response_from_file(file_path)

    # Assert that the loaded response is the same as the original response
    assert loaded_response.content == llm_response.content
    assert loaded_response.metadata == llm_response.metadata
    assert loaded_response.path == llm_response.path


def test_save_llm_response_to_file_with_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path_and_content_and_metadata_and_path(tmp_path: Path, llm_response: LLMResponse):
    # Create a temporary file
    file_path = tmp_path / "test