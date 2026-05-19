"""Tests for tilt display in poker TUI."""

from __future__ import annotations

from io import StringIO

from hive.agents.suffering import StressorType, SufferingState
from rich.console import Console

from poker.display import chip_counts, journal_entry, table_talk, tilt_alert
from poker.engine import PokerEngine


def _capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    import poker.display as disp

    old = disp.console
    disp.console = Console(file=buf, force_terminal=True)
    try:
        fn(*args, **kwargs)
    finally:
        disp.console = old
    return buf.getvalue()


def test_chip_counts_no_suffering():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    output = _capture(chip_counts, engine.players, 1000, suffering_states=None)
    assert "A" in output
    assert "B" in output
    assert "CRISIS" not in output


def test_chip_counts_with_crisis():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    suffering = SufferingState(agent_id="A")
    suffering.add_stressor(
        StressorType.EXISTENTIAL_THREAT, "Bad", "Win", initial_severity=0.95
    )
    output = _capture(
        chip_counts, engine.players, 1000, suffering_states={"A": suffering}
    )
    assert "CRISIS" in output


def test_chip_counts_with_tilt():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    suffering = SufferingState(agent_id="A")
    suffering.add_stressor(
        StressorType.REPEATED_FAILURE, "Bad", "Win", initial_severity=0.65
    )
    output = _capture(
        chip_counts, engine.players, 1000, suffering_states={"A": suffering}
    )
    assert "TILT" in output


def test_chip_counts_stressed():
    engine = PokerEngine(player_names=["A", "B"], starting_chips=1000)
    suffering = SufferingState(agent_id="A")
    suffering.add_stressor(
        StressorType.FUTILITY, "Bad", "Win", initial_severity=0.35
    )
    output = _capture(
        chip_counts, engine.players, 1000, suffering_states={"A": suffering}
    )
    assert "stressed" in output


def test_tilt_alert_spike():
    output = _capture(tilt_alert, "Alice", 0.3, 0.8)
    assert "spiked" in output


def test_tilt_alert_no_spike():
    output = _capture(tilt_alert, "Alice", 0.3, 0.35)
    assert output == ""


def test_journal_entry_display():
    output = _capture(journal_entry, "Bob", "I feel terrible after that loss")
    assert "Bob" in output
    assert "terrible" in output


def test_table_talk_display():
    output = _capture(table_talk, "Alice", "You're going down!")
    assert "Alice" in output
    assert "going down" in output
