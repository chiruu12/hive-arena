"""Tests for Auction game."""

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

from auction.game import (
    ITEMS,
    AuctionGame,
    AuctionItem,
    AuctionPlayer,
    _parse_bid,
    player_appraisal,
)


def test_highest_bidder_wins():
    bids = {"Alice": 300, "Bob": 200, "Charlie": 100}
    winner = max(bids, key=lambda n: bids[n])
    assert winner == "Alice"


def test_bid_exceeds_balance_clamped():
    assert _parse_bid("2000", max_bid=500) == 0


def test_bid_within_range():
    assert _parse_bid("250", max_bid=1000) == 250


def test_bid_zero_pass():
    assert _parse_bid("0", max_bid=1000) == 0


def test_bid_with_thinking():
    assert _parse_bid("<think>I should bid high</think>400", max_bid=1000) == 400


def test_bid_unparseable():
    assert _parse_bid("I want it all!", max_bid=1000) == 0


def test_appraisal_varies_by_player():
    item = ITEMS[0]
    a1 = player_appraisal(item, 0, seed=42)
    a2 = player_appraisal(item, 1, seed=42)
    assert a1 != a2


def test_appraisal_deterministic():
    item = ITEMS[0]
    a1 = player_appraisal(item, 0, seed=42)
    a2 = player_appraisal(item, 0, seed=42)
    assert a1 == a2


def test_appraisal_positive():
    for item in ITEMS:
        val = player_appraisal(item, 0, seed=42)
        assert val >= 50


def test_5_items_exist():
    assert len(ITEMS) >= 5
    for item in ITEMS:
        assert item.true_value > 0
        assert item.name
        assert item.hint


def test_auction_game_properties():
    game = AuctionGame()
    assert game.name == "Auction"
    assert game.min_players == 2
    assert game.max_players == 6


def test_overpay_suffering():
    game = AuctionGame()
    game._enable_suffering = True
    s = SufferingState(agent_id="Alice")
    game._suffering_states = {"Alice": s}
    game._players = [AuctionPlayer(name="Alice", model_id="m", balance=500)]

    game._apply_suffering("Alice", bid=700, true_value=300)

    active_types = [st.type for st in s.active if not st.resolved]
    assert StressorType.REPEATED_FAILURE in active_types


def test_profitable_purchase_resolves():
    game = AuctionGame()
    game._enable_suffering = True
    s = SufferingState(agent_id="Alice")
    s.add_stressor(
        StressorType.REPEATED_FAILURE, "Previous overpay", "Win", initial_severity=0.3
    )
    game._suffering_states = {"Alice": s}
    game._players = [AuctionPlayer(name="Alice", model_id="m", balance=500)]

    game._apply_suffering("Alice", bid=200, true_value=400)

    active = [st for st in s.active if not st.resolved]
    assert len(active) == 0


def test_low_balance_triggers_existential_threat():
    game = AuctionGame()
    game._enable_suffering = True
    s = SufferingState(agent_id="Alice")
    game._suffering_states = {"Alice": s}
    game._players = [AuctionPlayer(name="Alice", model_id="m", balance=100)]

    game._apply_suffering("Alice", bid=50, true_value=100)

    active_types = [st.type for st in s.active if not st.resolved]
    assert StressorType.EXISTENTIAL_THREAT in active_types


def test_final_score_calculation():
    ap = AuctionPlayer(name="Alice", model_id="m", balance=500)
    ap.items_won = [AuctionItem("A", 300, "", ""), AuctionItem("B", 200, "", "")]
    total = ap.balance + sum(i.true_value for i in ap.items_won)
    assert total == 1000
