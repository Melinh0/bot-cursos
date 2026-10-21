import os
import pytest
from unittest.mock import Mock, patch
from src.llm.client import LLMClient
from src.llm.solver import QuizSolver


def test_llm_client_initialization():
    with patch("src.llm.client.OpenAI") as mock_openai:
        with patch.dict("os.environ", {"OLLAMA_API_KEYS": "key1,key2,key3"}):
            client = LLMClient()
            assert client.api_keys == ["key1", "key2", "key3"]


def test_key_rotation():
    with patch("src.llm.client.OpenAI") as mock_openai:
        with patch.dict("os.environ", {"OLLAMA_API_KEYS": "key1,key2,key3"}):
            client = LLMClient()
            initial_index = client.current_key_index
            client._rotate_key()
            assert client.current_key_index == (initial_index + 1) % len(client.api_keys)


def test_quiz_solver():
    with patch("src.llm.solver.LLMClient") as mock_client_class:
        mock_client = Mock()
        mock_client.chat_completion.return_value = "1"
        mock_client_class.return_value = mock_client

        solver = QuizSolver()
        result = solver.solve_quiz({
            "question": "What is 2+2?",
            "options": ["3", "4", "5", "6"]
        })
        assert result == 1


def test_activity_solver():
    with patch("src.llm.solver.LLMClient") as mock_client_class:
        mock_client = Mock()
        mock_client.chat_completion.return_value = "print('Hello World')"
        mock_client_class.return_value = mock_client

        solver = QuizSolver()
        result = solver.solve_activity({
            "prompt": "Write a hello world program"
        })
        assert result == "print('Hello World')"