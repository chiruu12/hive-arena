"""Tests for journal entries during poker."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from poker.table import LLMPlayer, _write_journal


@pytest.fixture
def mock_notepad():
    notepad = MagicMock()
    notepad.write = MagicMock(return_value="written")
    return notepad


@pytest.fixture
def mock_llm_player():
    lp = LLMPlayer(name="Alice", model_id="mock")
    lp.agent = MagicMock()
    lp.agent.run_once = AsyncMock(return_value="I feel devastated by that loss.")
    return lp


async def test_journal_writes_entry(mock_llm_player, mock_notepad):
    await _write_journal(mock_llm_player, "Lost big pot", 5, mock_notepad)
    mock_notepad.write.assert_called_once()
    call_args = mock_notepad.write.call_args
    assert call_args[0][0] == "Alice"
    assert "Hand #5" in call_args[0][1]


async def test_journal_calls_agent(mock_llm_player, mock_notepad):
    await _write_journal(mock_llm_player, "Won big pot", 3, mock_notepad)
    mock_llm_player.agent.run_once.assert_called_once()
    prompt = mock_llm_player.agent.run_once.call_args[0][0]
    assert "Won big pot" in prompt
    assert "ONE sentence" in prompt


async def test_journal_truncates_long_entries(mock_notepad):
    lp = LLMPlayer(name="Bob", model_id="mock")
    lp.agent = MagicMock()
    lp.agent.run_once = AsyncMock(return_value="x" * 500)
    await _write_journal(lp, "Test", 1, mock_notepad)
    written = mock_notepad.write.call_args[0][1]
    assert len(written) <= 220


async def test_journal_skips_empty_response(mock_notepad):
    lp = LLMPlayer(name="Bob", model_id="mock")
    lp.agent = MagicMock()
    lp.agent.run_once = AsyncMock(return_value="   ")
    await _write_journal(lp, "Test", 1, mock_notepad)
    mock_notepad.write.assert_not_called()


async def test_journal_handles_agent_error(mock_notepad):
    lp = LLMPlayer(name="Bob", model_id="mock")
    lp.agent = MagicMock()
    lp.agent.run_once = AsyncMock(side_effect=RuntimeError("API down"))
    await _write_journal(lp, "Test", 1, mock_notepad)
    mock_notepad.write.assert_not_called()
