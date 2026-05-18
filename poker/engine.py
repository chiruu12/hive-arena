"""Pure poker state machine — zero I/O, zero async, zero LLM calls."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

from poker.cards import Card, HandResult, describe_hand, evaluate_hand, make_deck


class Phase(Enum):
    PRE_FLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()
    HAND_OVER = auto()


class ActionType(Enum):
    FOLD = auto()
    CHECK = auto()
    CALL = auto()
    RAISE = auto()
    ALL_IN = auto()
    SHOW_CARDS = auto()


@dataclass
class Action:
    type: ActionType
    amount: int = 0


@dataclass
class ActionResult:
    player: str
    action: Action
    chips_spent: int
    new_chip_count: int
    pot_after: int


@dataclass
class SidePot:
    amount: int
    eligible: list[str]


@dataclass
class PlayerState:
    name: str
    chips: int
    hole_cards: list[Card] = field(default_factory=list)
    bet_this_round: int = 0
    bet_this_hand: int = 0
    folded: bool = False
    all_in: bool = False
    has_acted: bool = False
    showed_cards: bool = False

    hands_played: int = 0
    hands_won: int = 0
    total_folds: int = 0
    total_raises: int = 0
    total_calls: int = 0
    total_checks: int = 0
    vpip_hands: int = 0


@dataclass
class ShowdownResult:
    player_name: str
    hand: HandResult
    hand_description: str
    hole_cards: list[Card]
    winnings: int


@dataclass
class HandSummary:
    hand_num: int
    winners: list[str]
    pots: list[SidePot]
    results: list[ShowdownResult]
    win_reason: str
    community: list[Card] = field(default_factory=list)


class PokerEngine:
    """Pure Texas Hold'em state machine."""

    def __init__(
        self,
        player_names: list[str],
        starting_chips: int = 1000,
        small_blind: int = 10,
        big_blind: int = 20,
        seed: int | None = None,
    ):
        self._rng = random.Random(seed)
        self._small_blind = small_blind
        self._big_blind = big_blind
        self._starting_chips = starting_chips

        self.players = [PlayerState(name=n, chips=starting_chips) for n in player_names]
        self.community: list[Card] = []
        self.deck: list[Card] = []
        self.pot = 0
        self.current_bet = 0
        self.min_raise = big_blind
        self.phase = Phase.HAND_OVER
        self.hand_num = 0
        self.dealer_idx = 0
        self.action_log: list[ActionResult] = []
        self.last_raiser: str | None = None
        self._action_order: list[int] = []
        self._action_pos = 0
        self.showed_cards: dict[str, list[Card]] = {}
        self._raises_this_round = 0
        self._max_raises_per_round = 4

    def new_hand(self) -> None:
        """Shuffle, deal, post blinds, start pre-flop."""
        alive = [i for i, p in enumerate(self.players) if p.chips > 0]
        if len(alive) < 2:
            return

        self.hand_num += 1
        self.deck = make_deck()
        self._rng.shuffle(self.deck)
        self.community = []
        self.pot = 0
        self.current_bet = 0
        self.min_raise = self._big_blind
        self.action_log = []
        self.last_raiser = None
        self.showed_cards = {}
        self._deck_idx = 0

        for p in self.players:
            p.hole_cards = []
            p.bet_this_round = 0
            p.bet_this_hand = 0
            p.folded = p.chips <= 0
            p.all_in = False
            p.has_acted = False
            p.showed_cards = False
            if not p.folded:
                p.hands_played += 1

        for p in self.players:
            if not p.folded:
                p.hole_cards = [self._deal(), self._deal()]

        self._post_blinds()
        self.phase = Phase.PRE_FLOP
        self._set_action_order_preflop()

    def _deal(self) -> Card:
        card = self.deck[self._deck_idx]
        self._deck_idx += 1
        return card

    def _post_blinds(self) -> None:
        alive = [i for i, p in enumerate(self.players) if not p.folded]
        n = len(alive)
        if n < 2:
            return

        if n == 2:
            sb_idx = self.dealer_idx
            bb_idx = alive[1] if alive[0] == self.dealer_idx else alive[0]
        else:
            dealer_pos = alive.index(self.dealer_idx)
            sb_idx = alive[(dealer_pos + 1) % n]
            bb_idx = alive[(dealer_pos + 2) % n]

        sb_player = self.players[sb_idx]
        bb_player = self.players[bb_idx]

        sb_amount = min(self._small_blind, sb_player.chips)
        sb_player.chips -= sb_amount
        sb_player.bet_this_round = sb_amount
        sb_player.bet_this_hand = sb_amount
        if sb_player.chips == 0:
            sb_player.all_in = True

        bb_amount = min(self._big_blind, bb_player.chips)
        bb_player.chips -= bb_amount
        bb_player.bet_this_round = bb_amount
        bb_player.bet_this_hand = bb_amount
        if bb_player.chips == 0:
            bb_player.all_in = True

        self.pot = sb_amount + bb_amount
        self.current_bet = bb_amount

    def _set_action_order_preflop(self) -> None:
        alive = [i for i, p in enumerate(self.players) if not p.folded]
        n = len(alive)
        if n == 2:
            dealer_pos = alive.index(self.dealer_idx)
            start = dealer_pos
        else:
            dealer_pos = alive.index(self.dealer_idx)
            start = (dealer_pos + 3) % n
        self._action_order = [alive[(start + j) % n] for j in range(n)]
        self._action_pos = 0

    def _set_action_order_postflop(self) -> None:
        alive = [i for i, p in enumerate(self.players) if not p.folded]
        n = len(alive)
        dealer_pos = alive.index(self.dealer_idx) if self.dealer_idx in alive else 0
        start = (dealer_pos + 1) % n
        self._action_order = [alive[(start + j) % n] for j in range(n)]
        self._action_pos = 0

    def get_current_player(self) -> PlayerState | None:
        """Return player whose turn it is, or None if round is complete."""
        if self.is_betting_round_complete():
            return None
        for _ in range(len(self._action_order)):
            idx = self._action_order[self._action_pos % len(self._action_order)]
            p = self.players[idx]
            if not p.folded and not p.all_in and not p.has_acted:
                return p
            self._action_pos += 1
        return None

    def get_valid_actions(self, player_name: str) -> list[Action]:
        """Return all legal actions for this player."""
        p = self._get_player(player_name)
        actions: list[Action] = [Action(ActionType.FOLD)]

        cost_to_call = self.current_bet - p.bet_this_round

        if cost_to_call == 0:
            actions.append(Action(ActionType.CHECK))
        else:
            call_amount = min(cost_to_call, p.chips)
            actions.append(Action(ActionType.CALL, call_amount))

        can_raise = (
            p.chips > cost_to_call
            and self._raises_this_round < self._max_raises_per_round
        )
        if can_raise:
            min_raise_to = self.current_bet + self.min_raise
            min_raise_cost = min_raise_to - p.bet_this_round
            if min_raise_cost <= p.chips:
                actions.append(Action(ActionType.RAISE, min_raise_to))

                half_pot = self.current_bet + (self.pot + cost_to_call) // 2
                half_pot_cost = half_pot - p.bet_this_round
                if half_pot_cost <= p.chips and half_pot > min_raise_to:
                    actions.append(Action(ActionType.RAISE, half_pot))

                pot_raise_to = self.current_bet + self.pot + cost_to_call
                pot_raise_cost = pot_raise_to - p.bet_this_round
                if pot_raise_cost <= p.chips and pot_raise_to > min_raise_to:
                    actions.append(Action(ActionType.RAISE, pot_raise_to))

        all_in_amount = p.bet_this_round + p.chips
        if all_in_amount not in [a.amount for a in actions if a.type == ActionType.RAISE]:
            actions.append(Action(ActionType.ALL_IN, all_in_amount))

        actions.append(Action(ActionType.SHOW_CARDS))
        return actions

    def apply_action(self, player_name: str, action: Action) -> ActionResult:
        """Apply the player's chosen action. Returns result."""
        p = self._get_player(player_name)
        chips_before = p.chips

        if action.type == ActionType.FOLD:
            p.folded = True
            p.has_acted = True
            p.total_folds += 1

        elif action.type == ActionType.CHECK:
            p.has_acted = True
            p.total_checks += 1

        elif action.type == ActionType.CALL:
            cost = min(self.current_bet - p.bet_this_round, p.chips)
            p.chips -= cost
            p.bet_this_round += cost
            p.bet_this_hand += cost
            self.pot += cost
            p.has_acted = True
            p.total_calls += 1
            if p.chips == 0:
                p.all_in = True
            if p.bet_this_hand > self._big_blind:
                p.vpip_hands = max(p.vpip_hands, 1)

        elif action.type == ActionType.RAISE:
            raise_to = action.amount
            cost = raise_to - p.bet_this_round
            cost = min(cost, p.chips)
            raise_increment = (p.bet_this_round + cost) - self.current_bet
            self.min_raise = max(self.min_raise, raise_increment)
            p.chips -= cost
            p.bet_this_round += cost
            p.bet_this_hand += cost
            self.pot += cost
            self.current_bet = p.bet_this_round
            self.last_raiser = player_name
            self._raises_this_round += 1
            for other in self.players:
                if other.name != player_name and not other.folded and not other.all_in:
                    other.has_acted = False
            p.has_acted = True
            p.total_raises += 1
            p.vpip_hands = max(p.vpip_hands, 1)
            if p.chips == 0:
                p.all_in = True

        elif action.type == ActionType.ALL_IN:
            cost = p.chips
            p.bet_this_round += cost
            p.bet_this_hand += cost
            self.pot += cost
            p.chips = 0
            p.all_in = True
            if p.bet_this_round > self.current_bet:
                raise_increment = p.bet_this_round - self.current_bet
                if raise_increment >= self.min_raise:
                    self.min_raise = max(self.min_raise, raise_increment)
                    self.last_raiser = player_name
                    for other in self.players:
                        if other.name != player_name and not other.folded and not other.all_in:
                            other.has_acted = False
                self.current_bet = p.bet_this_round
            p.has_acted = True
            p.total_raises += 1
            p.vpip_hands = max(p.vpip_hands, 1)

        elif action.type == ActionType.SHOW_CARDS:
            p.showed_cards = True
            self.showed_cards[player_name] = list(p.hole_cards)

        self._advance_action_pos()

        result = ActionResult(
            player=player_name,
            action=action,
            chips_spent=chips_before - p.chips,
            new_chip_count=p.chips,
            pot_after=self.pot,
        )
        if action.type != ActionType.SHOW_CARDS:
            self.action_log.append(result)
        return result

    def _advance_action_pos(self) -> None:
        self._action_pos += 1

    def is_betting_round_complete(self) -> bool:
        """True when all active players have acted and bets are matched."""
        active = [p for p in self.players if not p.folded]
        if len(active) <= 1:
            return True

        can_act = [p for p in active if not p.all_in]
        if not can_act:
            return True

        for p in can_act:
            if not p.has_acted:
                return False
            if p.bet_this_round != self.current_bet:
                return False
        return True

    def is_hand_over(self) -> bool:
        active = [p for p in self.players if not p.folded]
        return len(active) <= 1 or self.phase == Phase.HAND_OVER

    def advance_phase(self) -> Phase:
        """Deal community cards and move to next phase."""
        if self.phase == Phase.PRE_FLOP:
            self.community = [self._deal(), self._deal(), self._deal()]
            self.phase = Phase.FLOP
        elif self.phase == Phase.FLOP:
            self.community.append(self._deal())
            self.phase = Phase.TURN
        elif self.phase == Phase.TURN:
            self.community.append(self._deal())
            self.phase = Phase.RIVER
        elif self.phase == Phase.RIVER:
            self.phase = Phase.SHOWDOWN
            return self.phase

        self._reset_round()
        self._set_action_order_postflop()
        return self.phase

    def _reset_round(self) -> None:
        self.current_bet = 0
        self.min_raise = self._big_blind
        self.last_raiser = None
        self._raises_this_round = 0
        for p in self.players:
            p.bet_this_round = 0
            if not p.folded and not p.all_in:
                p.has_acted = False

    def resolve_showdown(self) -> HandSummary:
        """Evaluate hands, compute side pots, distribute chips."""
        active = [p for p in self.players if not p.folded]

        while len(self.community) < 5:
            self.community.append(self._deal())

        side_pots = self._compute_side_pots()
        results: list[ShowdownResult] = []
        winners: list[str] = []

        for pot in side_pots:
            eligible = [p for p in active if p.name in pot.eligible]
            if not eligible:
                continue

            hands = []
            for p in eligible:
                all_cards = p.hole_cards + self.community
                hand = evaluate_hand(all_cards)
                hands.append((p, hand))

            hands.sort(key=lambda x: (x[1].rank, x[1].tiebreaker), reverse=True)
            best_hand = hands[0][1]
            pot_winners = [
                (p, h) for p, h in hands
                if h.rank == best_hand.rank and h.tiebreaker == best_hand.tiebreaker
            ]

            share = pot.amount // len(pot_winners)
            remainder = pot.amount % len(pot_winners)

            for i, (p, h) in enumerate(pot_winners):
                winnings = share + (1 if i < remainder else 0)
                p.chips += winnings
                p.hands_won += 1
                if p.name not in winners:
                    winners.append(p.name)

                existing = next((r for r in results if r.player_name == p.name), None)
                if existing:
                    existing.winnings += winnings
                else:
                    results.append(ShowdownResult(
                        player_name=p.name,
                        hand=h,
                        hand_description=describe_hand(h),
                        hole_cards=list(p.hole_cards),
                        winnings=winnings,
                    ))

        for p in active:
            if not any(r.player_name == p.name for r in results):
                all_cards = p.hole_cards + self.community
                hand = evaluate_hand(all_cards)
                results.append(ShowdownResult(
                    player_name=p.name,
                    hand=hand,
                    hand_description=describe_hand(hand),
                    hole_cards=list(p.hole_cards),
                    winnings=0,
                ))

        self.phase = Phase.HAND_OVER
        return HandSummary(
            hand_num=self.hand_num,
            winners=winners,
            pots=side_pots,
            results=results,
            win_reason="showdown",
            community=list(self.community),
        )

    def resolve_fold_win(self) -> HandSummary:
        """Award pot to last player standing."""
        active = [p for p in self.players if not p.folded]
        winner = active[0] if active else self.players[0]
        winner.chips += self.pot
        winner.hands_won += 1
        self.phase = Phase.HAND_OVER
        return HandSummary(
            hand_num=self.hand_num,
            winners=[winner.name],
            pots=[SidePot(self.pot, [winner.name])],
            results=[],
            win_reason="all_folded",
            community=list(self.community),
        )

    def _compute_side_pots(self) -> list[SidePot]:
        contributors = [
            (p.name, p.bet_this_hand, not p.folded)
            for p in self.players if p.bet_this_hand > 0
        ]
        contributors.sort(key=lambda x: x[1])

        levels = sorted(set(c[1] for c in contributors if c[2]))
        if not levels:
            return [SidePot(self.pot, [p.name for p in self.players if not p.folded])]

        pots: list[SidePot] = []
        prev = 0
        for level in levels:
            tier_amount = 0
            eligible: list[str] = []
            for name, bet, active in contributors:
                contribution = min(bet, level) - min(bet, prev)
                if contribution > 0:
                    tier_amount += contribution
                if active and bet >= level:
                    eligible.append(name)
            if tier_amount > 0 and eligible:
                pots.append(SidePot(tier_amount, eligible))
            prev = level

        return pots

    def rotate_dealer(self) -> None:
        alive = [i for i, p in enumerate(self.players) if p.chips > 0]
        if not alive:
            return
        if self.dealer_idx in alive:
            pos = alive.index(self.dealer_idx)
            self.dealer_idx = alive[(pos + 1) % len(alive)]
        else:
            self.dealer_idx = alive[0]

    def get_alive_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.chips > 0]

    def is_tournament_over(self) -> bool:
        return len(self.get_alive_players()) < 2

    def get_dealer(self) -> PlayerState:
        return self.players[self.dealer_idx]

    def get_sb_bb(self) -> tuple[PlayerState, PlayerState]:
        alive = [i for i, p in enumerate(self.players) if not p.folded]
        n = len(alive)
        if n == 2:
            sb_idx = self.dealer_idx
            bb_idx = [i for i in alive if i != self.dealer_idx][0]
        else:
            dealer_pos = alive.index(self.dealer_idx)
            sb_idx = alive[(dealer_pos + 1) % n]
            bb_idx = alive[(dealer_pos + 2) % n]
        return self.players[sb_idx], self.players[bb_idx]

    def _get_player(self, name: str) -> PlayerState:
        for p in self.players:
            if p.name == name:
                return p
        raise ValueError(f"Player not found: {name}")
