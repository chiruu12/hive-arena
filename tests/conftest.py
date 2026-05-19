"""Shared fixtures for hive-arena tests."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def tmp_hive_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_provider():
    """Mock BaseProvider that returns '2' for every generate call."""
    from hive.runtime.types import GenerateResult, Message

    provider = MagicMock()
    provider.model = "mock-model"
    provider.available = True

    result = GenerateResult(message=Message.assistant("2"), model="mock-model")
    provider.generate_with_metadata = AsyncMock(return_value=result)
    provider.generate = AsyncMock(return_value=Message.assistant("2"))
    return provider


@pytest.fixture
def mock_agent_factory(mock_provider):
    """Factory that creates an Agent with a mock provider."""

    def _create(name: str = "test-player", persona=None):
        from hive.runtime.agent import Agent

        kwargs = {"name": name, "model": mock_provider}
        if persona is not None:
            kwargs["persona"] = persona
        return Agent(**kwargs)

    return _create
