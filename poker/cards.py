"""Card deck, hand evaluation, and poker mechanics."""

from dataclasses import dataclass
from enum import IntEnum


class Suit(IntEnum):
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


SUIT_SYMBOLS = {Suit.CLUBS: "♣", Suit.DIAMONDS: "♦", Suit.HEARTS: "♥", Suit.SPADES: "♠"}

RANK_NAMES = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8",
    9: "9", 10: "10", 11: "J", 12: "Q", 13: "K", 14: "A",
}


@dataclass(frozen=True)
class Card:
    rank: int
    suit: Suit

    def __str__(self) -> str:
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    def __repr__(self) -> str:
        return str(self)


class HandRank(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


HAND_NAMES = {
    HandRank.HIGH_CARD: "High Card",
    HandRank.PAIR: "Pair",
    HandRank.TWO_PAIR: "Two Pair",
    HandRank.THREE_OF_A_KIND: "Three of a Kind",
    HandRank.STRAIGHT: "Straight",
    HandRank.FLUSH: "Flush",
    HandRank.FULL_HOUSE: "Full House",
    HandRank.FOUR_OF_A_KIND: "Four of a Kind",
    HandRank.STRAIGHT_FLUSH: "Straight Flush",
    HandRank.ROYAL_FLUSH: "Royal Flush",
}


@dataclass
class HandResult:
    rank: HandRank
    tiebreaker: tuple[int, ...]
    best_cards: list[Card]

    @property
    def name(self) -> str:
        return HAND_NAMES[self.rank]

    def __gt__(self, other: "HandResult") -> bool:
        if self.rank != other.rank:
            return self.rank > other.rank
        return self.tiebreaker > other.tiebreaker

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandResult):
            return NotImplemented
        return self.rank == other.rank and self.tiebreaker == other.tiebreaker


def make_deck() -> list[Card]:
    return [Card(rank=r, suit=s) for s in Suit for r in range(2, 15)]


def evaluate_hand(cards: list[Card]) -> HandResult:
    """Evaluate the best 5-card hand from any number of cards."""
    if len(cards) < 5:
        ranks = sorted([c.rank for c in cards], reverse=True)
        return HandResult(HandRank.HIGH_CARD, tuple(ranks), list(cards))

    from itertools import combinations

    best: HandResult | None = None
    for combo in combinations(cards, 5):
        result = _evaluate_five(list(combo))
        if best is None or result > best:
            best = result
    assert best is not None
    return best


def _evaluate_five(cards: list[Card]) -> HandResult:
    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    rank_counts: dict[int, int] = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1

    is_flush = len(set(suits)) == 1
    sorted_unique = sorted(set(ranks), reverse=True)
    is_straight = (
        len(sorted_unique) == 5
        and sorted_unique[0] - sorted_unique[4] == 4
    )
    if sorted_unique == [14, 5, 4, 3, 2]:
        is_straight = True
        ranks = [5, 4, 3, 2, 1]

    groups = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    if is_straight and is_flush:
        if ranks[0] == 14 and ranks[1] == 13:
            return HandResult(HandRank.ROYAL_FLUSH, tuple(ranks), cards)
        return HandResult(HandRank.STRAIGHT_FLUSH, tuple(ranks), cards)
    if groups[0][1] == 4:
        tb = (groups[0][0], groups[1][0])
        return HandResult(HandRank.FOUR_OF_A_KIND, tb, cards)
    if groups[0][1] == 3 and groups[1][1] == 2:
        tb = (groups[0][0], groups[1][0])
        return HandResult(HandRank.FULL_HOUSE, tb, cards)
    if is_flush:
        return HandResult(HandRank.FLUSH, tuple(ranks), cards)
    if is_straight:
        return HandResult(HandRank.STRAIGHT, tuple(ranks), cards)
    if groups[0][1] == 3:
        kickers = sorted([g[0] for g in groups[1:]], reverse=True)
        return HandResult(HandRank.THREE_OF_A_KIND, (groups[0][0], *kickers), cards)
    if groups[0][1] == 2 and groups[1][1] == 2:
        pairs = sorted([groups[0][0], groups[1][0]], reverse=True)
        kicker = groups[2][0]
        return HandResult(HandRank.TWO_PAIR, (*pairs, kicker), cards)
    if groups[0][1] == 2:
        kickers = sorted([g[0] for g in groups[1:]], reverse=True)
        return HandResult(HandRank.PAIR, (groups[0][0], *kickers), cards)

    return HandResult(HandRank.HIGH_CARD, tuple(ranks), cards)


def describe_hand(result: HandResult) -> str:
    """Human-readable hand description like 'Pair of Aces'."""
    tb = result.tiebreaker
    r = result.rank
    _r = lambda v: RANK_NAMES.get(v, str(v))  # noqa: E731

    if r == HandRank.ROYAL_FLUSH:
        return "Royal Flush"
    if r == HandRank.STRAIGHT_FLUSH:
        return f"Straight Flush, {_r(tb[0])}-high"
    if r == HandRank.FOUR_OF_A_KIND:
        return f"Four {_r(tb[0])}s"
    if r == HandRank.FULL_HOUSE:
        return f"Full House, {_r(tb[0])}s full of {_r(tb[1])}s"
    if r == HandRank.FLUSH:
        return f"Flush, {_r(tb[0])}-high"
    if r == HandRank.STRAIGHT:
        return f"Straight, {_r(tb[0])}-high"
    if r == HandRank.THREE_OF_A_KIND:
        return f"Three {_r(tb[0])}s"
    if r == HandRank.TWO_PAIR:
        return f"Two Pair, {_r(tb[0])}s and {_r(tb[1])}s"
    if r == HandRank.PAIR:
        return f"Pair of {_r(tb[0])}s"
    return f"{_r(tb[0])}-high"
