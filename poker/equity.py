"""Monte Carlo hand equity calculator for Texas Hold'em."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from poker.cards import (
    Card,
    HandRank,
    HandResult,
    describe_hand,
    evaluate_hand,
    make_deck,
)


@dataclass
class EquityResult:
    current_hand: str
    current_rank: HandRank
    win_probability: float
    tie_probability: float
    hand_improvement: dict[str, float] = field(default_factory=dict)


def calculate_equity(
    hole_cards: list[Card],
    community_cards: list[Card],
    num_opponents: int,
    num_simulations: int = 1000,
    seed: int | None = None,
) -> EquityResult:
    """Estimate win probability via Monte Carlo simulation."""
    rng = random.Random(seed)
    known = set(hole_cards) | set(community_cards)
    remaining = [c for c in make_deck() if c not in known]
    cards_to_deal = 5 - len(community_cards)

    current_hand = evaluate_hand(hole_cards + community_cards)

    if num_opponents == 0:
        return EquityResult(
            current_hand=describe_hand(current_hand),
            current_rank=current_hand.rank,
            win_probability=1.0,
            tie_probability=0.0,
        )

    wins = 0
    ties = 0
    rank_counts: dict[str, int] = {}

    for _ in range(num_simulations):
        deck = list(remaining)
        rng.shuffle(deck)

        idx = 0
        sim_community = list(community_cards) + deck[idx : idx + cards_to_deal]
        idx += cards_to_deal

        hero_hand = evaluate_hand(hole_cards + sim_community)
        rank_name = hero_hand.name
        rank_counts[rank_name] = rank_counts.get(rank_name, 0) + 1

        hero_wins = True
        hero_ties = True
        for _ in range(num_opponents):
            opp_cards = deck[idx : idx + 2]
            idx += 2
            opp_hand = evaluate_hand(list(opp_cards) + sim_community)
            if opp_hand > hero_hand:
                hero_wins = False
                hero_ties = False
                break
            if not (hero_hand > opp_hand):
                hero_wins = False
            else:
                hero_ties = False

        if hero_wins:
            wins += 1
        elif hero_ties:
            ties += 1

    improvement: dict[str, float] = {}
    for name, count in sorted(rank_counts.items(), key=lambda x: -x[1]):
        prob = count / num_simulations
        if prob >= 0.005:
            improvement[name] = round(prob, 3)

    return EquityResult(
        current_hand=describe_hand(current_hand),
        current_rank=current_hand.rank,
        win_probability=round(wins / num_simulations, 3),
        tie_probability=round(ties / num_simulations, 3),
        hand_improvement=improvement,
    )
