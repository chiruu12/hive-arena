"""Tests for Persona wiring into poker and arena."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


from hive.runtime.persona import Persona

from poker.engine import PokerEngine
from poker.table import LLMPlayer, _build_prompt, _persona_context

# --- LLMPlayer ---


def test_llmplayer_accepts_persona():
    p = Persona(name="Test", risk_tolerance=0.85, values=["greed"], fears=["poverty"])
    lp = LLMPlayer(name="Test", model_id="mock", persona=p)
    assert lp.persona is p
    assert lp.persona.risk_tolerance == 0.85


def test_llmplayer_persona_defaults_none():
    lp = LLMPlayer(name="Test", model_id="mock")
    assert lp.persona is None


# --- _persona_context ---


def test_persona_context_aggressive():
    p = Persona(name="Gambler", risk_tolerance=0.85, values=["glory"], fears=["boredom"])
    lines = _persona_context(p)
    text = "\n".join(lines)
    assert "aggressive" in text.lower()
    assert "glory" in text


def test_persona_context_tight():
    p = Persona(name="Cautious", risk_tolerance=0.2, values=["safety"], fears=["loss"])
    lines = _persona_context(p)
    text = "\n".join(lines)
    assert "tight" in text.lower()
    assert "safety" in text


def test_persona_context_balanced():
    p = Persona(name="Balanced", risk_tolerance=0.5, values=["balance"], fears=["chaos"])
    lines = _persona_context(p)
    text = "\n".join(lines)
    assert "balanced" in text.lower()


def test_persona_context_low_concentration():
    p = Persona(name="Distracted", risk_tolerance=0.5, concentration=0.3)
    lines = _persona_context(p)
    text = "\n".join(lines)
    assert "scattered" in text.lower() or "distracted" in text.lower()


def test_persona_context_with_suffering():
    from hive.agents.suffering import StressorType, SufferingState

    p = Persona(name="Tilted", risk_tolerance=0.5)
    suffering = SufferingState(agent_id="Tilted")
    suffering.add_stressor(
        StressorType.REPEATED_FAILURE, "Lost many hands", "Win a hand", initial_severity=0.6
    )
    p.suffering = suffering
    lines = _persona_context(p)
    text = "\n".join(lines)
    assert len(text) > 50


# --- _build_prompt with persona ---


def _make_engine(names: list[str]) -> PokerEngine:
    return PokerEngine(player_names=names, starting_chips=1000, small_blind=10, big_blind=20)


def test_build_prompt_includes_persona():
    engine = _make_engine(["Alice", "Bob"])
    engine.new_hand()
    player = engine.players[0]
    valid = engine.get_valid_actions(player.name)
    positions = {p.name: "Seat" for p in engine.players}
    persona = Persona(name="Alice", risk_tolerance=0.85, values=["dominance"], fears=["weakness"])

    prompt, _ = _build_prompt(player, engine, None, valid, positions, persona=persona)
    assert "BEHAVIORAL GUIDANCE" in prompt
    assert "aggressive" in prompt.lower()
    assert "dominance" in prompt


def test_build_prompt_no_persona():
    engine = _make_engine(["Alice", "Bob"])
    engine.new_hand()
    player = engine.players[0]
    valid = engine.get_valid_actions(player.name)
    positions = {p.name: "Seat" for p in engine.players}

    prompt, _ = _build_prompt(player, engine, None, valid, positions, persona=None)
    assert "BEHAVIORAL GUIDANCE" not in prompt


# --- Arena format_prompt with persona ---


def test_arena_format_prompt_with_persona():
    from arena.events import EVENTS
    from arena.game import PlayerState as ArenaPlayerState
    from arena.game import format_prompt

    state = ArenaPlayerState(name="Test", model_id="mock")
    persona = Persona(name="Test", risk_tolerance=0.1, values=["caution"], fears=["ruin"])

    prompt = format_prompt(EVENTS[0], state, persona=persona)
    assert "BEHAVIORAL GUIDANCE" in prompt
    assert "safe" in prompt.lower()
    assert "caution" in prompt


def test_arena_format_prompt_without_persona():
    from arena.events import EVENTS
    from arena.game import PlayerState as ArenaPlayerState
    from arena.game import format_prompt

    state = ArenaPlayerState(name="Test", model_id="mock")

    prompt = format_prompt(EVENTS[0], state, persona=None)
    assert "BEHAVIORAL GUIDANCE" not in prompt
