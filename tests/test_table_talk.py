"""Tests for table talk and A2A messaging during poker."""

from __future__ import annotations

from poker.engine import PokerEngine
from poker.table import _build_prompt


def test_table_talk_in_prompt():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    engine.new_hand()
    player = engine.players[0]
    valid = engine.get_valid_actions(player.name)
    positions = {p.name: "Seat" for p in engine.players}

    talk = [("B", "I'm coming for you!"), ("A", "Bring it on.")]
    prompt, _ = _build_prompt(
        player, engine, None, valid, positions, table_talk=talk
    )
    assert "Recent table talk" in prompt
    assert "coming for you" in prompt


def test_no_talk_in_prompt_when_none():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    engine.new_hand()
    player = engine.players[0]
    valid = engine.get_valid_actions(player.name)
    positions = {p.name: "Seat" for p in engine.players}

    prompt, _ = _build_prompt(
        player, engine, None, valid, positions, table_talk=None
    )
    assert "Recent table talk" not in prompt


def test_memory_context_in_prompt():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    engine.new_hand()
    player = engine.players[0]
    valid = engine.get_valid_actions(player.name)
    positions = {p.name: "Seat" for p in engine.players}

    memories = ["opponent B: aggressive, fold_rate=20%, raise_rate=40%"]
    prompt, _ = _build_prompt(
        player, engine, None, valid, positions, memory_context=memories
    )
    assert "memories of opponents" in prompt
    assert "aggressive" in prompt


def test_no_memory_in_prompt_when_none():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    engine.new_hand()
    player = engine.players[0]
    valid = engine.get_valid_actions(player.name)
    positions = {p.name: "Seat" for p in engine.players}

    prompt, _ = _build_prompt(
        player, engine, None, valid, positions, memory_context=None
    )
    assert "memories of opponents" not in prompt
