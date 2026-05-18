"""Tests for suffering/tilt mechanic in poker."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hive.agents.suffering import StressorType, SufferingState
from hive.runtime.persona import Persona

from poker.cards import HandRank, HandResult
from poker.engine import HandSummary, PokerEngine, ShowdownResult, SidePot
from poker.table import TableConfig, _update_suffering

_DUMMY_HAND = HandResult(rank=HandRank.PAIR, tiebreaker=(10,), best_cards=[])


def _make_summary(winners: list[str], results: list[ShowdownResult] | None = None) -> HandSummary:
    """Create a minimal HandSummary for testing."""
    if results is None:
        results = [
            ShowdownResult(
                player_name=w, hand=_DUMMY_HAND,
                hole_cards=[], hand_description="pair", winnings=100,
            )
            for w in winners
        ]
    return HandSummary(
        hand_num=1,
        winners=winners,
        results=results,
        win_reason="showdown",
        community=[],
        pots=[SidePot(amount=200, eligible=winners)],
    )


def _make_engine(names: list[str], chips: dict[str, int] | None = None) -> PokerEngine:
    engine = PokerEngine(player_names=names, starting_chips=1000)
    if chips:
        for p in engine.players:
            if p.name in chips:
                p.chips = chips[p.name]
    return engine


def _make_config() -> TableConfig:
    return TableConfig(starting_chips=1000)


def test_suffering_created_per_player():
    states: dict[str, SufferingState] = {}
    names = ["Alice", "Bob", "Charlie"]
    for name in names:
        states[name] = SufferingState(agent_id=name)
    assert len(states) == 3
    assert all(isinstance(v, SufferingState) for v in states.values())


def test_win_resolves_repeated_failure():
    suffering = SufferingState(agent_id="Alice")
    suffering.add_stressor(StressorType.REPEATED_FAILURE, "Lost", "Win", initial_severity=0.3)
    assert len(suffering.active) == 1

    engine = _make_engine(["Alice", "Bob"])
    summary = _make_summary(winners=["Alice"])
    streak = {"Alice": 3, "Bob": 0}

    _update_suffering(
        "Alice", summary, engine, _make_config(),
        {"Alice": suffering}, None, streak,
    )

    active_types = [s.type for s in suffering.active if not s.resolved]
    assert StressorType.REPEATED_FAILURE not in active_types
    assert streak["Alice"] == 0


def test_big_loss_triggers_existential_threat():
    engine = _make_engine(["Alice", "Bob"], chips={"Alice": 200, "Bob": 800})
    suffering = SufferingState(agent_id="Alice")
    summary = _make_summary(winners=["Bob"])
    streak = {"Alice": 0, "Bob": 0}

    _update_suffering(
        "Alice", summary, engine, _make_config(),
        {"Alice": suffering}, None, streak,
    )

    active_types = [s.type for s in suffering.active if not s.resolved]
    assert StressorType.EXISTENTIAL_THREAT in active_types


def test_fold_rate_triggers_futility():
    engine = _make_engine(["Alice", "Bob"])
    player = next(p for p in engine.players if p.name == "Alice")
    player.hands_played = 10
    player.total_folds = 7

    suffering = SufferingState(agent_id="Alice")
    summary = _make_summary(winners=["Bob"])
    streak = {"Alice": 0, "Bob": 0}

    _update_suffering(
        "Alice", summary, engine, _make_config(),
        {"Alice": suffering}, None, streak,
    )

    active_types = [s.type for s in suffering.active if not s.resolved]
    assert StressorType.FUTILITY in active_types


def test_streak_triggers_invisibility():
    engine = _make_engine(["Alice", "Bob"])
    suffering = SufferingState(agent_id="Alice")
    summary = _make_summary(winners=["Bob"])
    streak = {"Alice": 4, "Bob": 0}

    _update_suffering(
        "Alice", summary, engine, _make_config(),
        {"Alice": suffering}, None, streak,
    )

    assert streak["Alice"] == 5
    active_types = [s.type for s in suffering.active if not s.resolved]
    assert StressorType.INVISIBILITY in active_types


def test_suffering_modifies_persona_risk():
    persona = Persona(name="Alice", risk_tolerance=0.3)
    suffering = SufferingState(agent_id="Alice")
    suffering.add_stressor(
        StressorType.EXISTENTIAL_THREAT, "Near elimination", "Win", initial_severity=0.8
    )
    suffering.add_stressor(
        StressorType.REPEATED_FAILURE, "Keeps losing", "Win", initial_severity=0.6
    )
    suffering.add_stressor(
        StressorType.FUTILITY, "Folding everything", "Play", initial_severity=0.6
    )

    engine = _make_engine(["Alice", "Bob"], chips={"Alice": 100, "Bob": 900})
    summary = _make_summary(winners=["Bob"])
    streak = {"Alice": 6, "Bob": 0}
    personas = {"Alice": persona}

    _update_suffering(
        "Alice", summary, engine, _make_config(),
        {"Alice": suffering}, personas, streak,
    )

    assert persona.risk_tolerance != 0.3


def test_suffering_disabled_by_default():
    suffering_states: dict[str, SufferingState] = {}
    assert len(suffering_states) == 0


def test_loser_gets_repeated_failure_bump():
    suffering = SufferingState(agent_id="Alice")
    suffering.add_stressor(
        StressorType.REPEATED_FAILURE, "Lost", "Win", initial_severity=0.2
    )
    initial_sev = suffering.active[0].severity

    engine = _make_engine(["Alice", "Bob"])
    summary = _make_summary(winners=["Bob"])
    streak = {"Alice": 0, "Bob": 0}

    _update_suffering(
        "Alice", summary, engine, _make_config(),
        {"Alice": suffering}, None, streak,
    )

    current_sev = next(
        s.severity for s in suffering.active
        if s.type == StressorType.REPEATED_FAILURE and not s.resolved
    )
    assert current_sev > initial_sev
