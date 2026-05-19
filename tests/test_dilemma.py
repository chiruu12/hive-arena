"""Tests for Prisoner's Dilemma game."""

from __future__ import annotations

from hive.agents.suffering import StressorType, SufferingState

from dilemma.game import PAYOFF, PrisonersDilemma, _parse_choice


def test_payoff_both_cooperate():
    assert PAYOFF[("cooperate", "cooperate")] == (3, 3)


def test_payoff_one_betrays():
    assert PAYOFF[("cooperate", "betray")] == (0, 5)
    assert PAYOFF[("betray", "cooperate")] == (5, 0)


def test_payoff_both_betray():
    assert PAYOFF[("betray", "betray")] == (1, 1)


def test_parse_choice_number_1():
    assert _parse_choice("1") == "cooperate"


def test_parse_choice_number_2():
    assert _parse_choice("2") == "betray"


def test_parse_choice_word():
    assert _parse_choice("I'll cooperate this time") == "cooperate"
    assert _parse_choice("Time to betray!") == "betray"


def test_parse_choice_with_thinking():
    assert _parse_choice("<think>hmm...</think>2") == "betray"


def test_parse_choice_default():
    assert _parse_choice("nonsense") == "cooperate"


def test_dilemma_properties():
    game = PrisonersDilemma()
    assert game.name == "Prisoner's Dilemma"
    assert game.min_players == 2
    assert game.max_players == 2


def test_suffering_on_betrayal():
    game = PrisonersDilemma()
    game._suffering_states = {
        "A": SufferingState(agent_id="A"),
        "B": SufferingState(agent_id="B"),
    }
    game._enable_suffering = True
    game._mutual_betray_streak = 0

    game._apply_suffering("A", "B", "cooperate", "betray")

    a_types = [s.type for s in game._suffering_states["A"].active if not s.resolved]
    assert StressorType.IDENTITY_VIOLATION in a_types

    b_types = [s.type for s in game._suffering_states["B"].active if not s.resolved]
    assert StressorType.IDENTITY_VIOLATION not in b_types


def test_mutual_cooperation_resolves():
    game = PrisonersDilemma()
    s_a = SufferingState(agent_id="A")
    s_a.add_stressor(
        StressorType.IDENTITY_VIOLATION, "Was betrayed", "Coop", initial_severity=0.3
    )
    game._suffering_states = {"A": s_a, "B": SufferingState(agent_id="B")}
    game._enable_suffering = True
    game._mutual_betray_streak = 0

    game._apply_suffering("A", "B", "cooperate", "cooperate")

    active = [s for s in s_a.active if not s.resolved]
    assert len(active) == 0


def test_mutual_betrayal_futility():
    game = PrisonersDilemma()
    game._suffering_states = {
        "A": SufferingState(agent_id="A"),
        "B": SufferingState(agent_id="B"),
    }
    game._enable_suffering = True
    game._mutual_betray_streak = 2

    game._apply_suffering("A", "B", "betray", "betray")

    a_types = [s.type for s in game._suffering_states["A"].active if not s.resolved]
    assert StressorType.FUTILITY in a_types
