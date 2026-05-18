"""Tests for HiveGame protocol and data classes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from base import GameResult, HiveGame, PlayerResult


def test_hivegame_is_abstract():
    with pytest.raises(TypeError):
        HiveGame()


def test_player_result_fields():
    pr = PlayerResult(
        name="Alice", model_id="mock", final_score=1500.0,
        metrics={"hands_won": 5}, journal=["I won!"],
    )
    assert pr.name == "Alice"
    assert pr.final_score == 1500.0
    assert pr.metrics["hands_won"] == 5
    assert pr.journal == ["I won!"]


def test_player_result_defaults():
    pr = PlayerResult(name="Bob", model_id="mock", final_score=0.0)
    assert pr.metrics == {}
    assert pr.journal == []


def test_game_result_fields():
    gr = GameResult(
        game_name="Poker", winners=["Alice"],
        players=[PlayerResult("Alice", "m", 100.0)],
        rounds_played=20, metadata={"seed": 42},
    )
    assert gr.game_name == "Poker"
    assert gr.winners == ["Alice"]
    assert len(gr.players) == 1
    assert gr.rounds_played == 20
    assert gr.metadata["seed"] == 42


def test_game_result_defaults():
    gr = GameResult(
        game_name="Test", winners=[], players=[], rounds_played=0,
    )
    assert gr.metadata == {}


def test_poker_game_properties():
    from poker.game import PokerGame

    game = PokerGame()
    assert game.name == "Texas Hold'em Poker"
    assert game.min_players == 2
    assert game.max_players == 8


def test_arena_game_properties():
    from arena.wrapper import ArenaGame

    game = ArenaGame()
    assert game.name == "Economic Arena"
    assert game.min_players == 1
    assert game.max_players == 10


def test_poker_game_is_hivegame():
    from poker.game import PokerGame

    assert isinstance(PokerGame(), HiveGame)


def test_arena_game_is_hivegame():
    from arena.wrapper import ArenaGame

    assert isinstance(ArenaGame(), HiveGame)
