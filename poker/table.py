"""Poker table — connects the PokerEngine to LLM players."""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from poker import display
from poker.cards import describe_hand, evaluate_hand
from poker.engine import (
    Action,
    ActionType,
    Phase,
    PlayerState,
    PokerEngine,
)
from poker.equity import EquityResult, calculate_equity


@dataclass
class LLMPlayer:
    name: str
    model_id: str
    provider_kwargs: dict[str, Any] = field(default_factory=dict)
    persona: Any = None
    agent: Any = None
    total_time: float = 0.0


@dataclass
class TableConfig:
    starting_chips: int = 1000
    small_blind: int = 10
    big_blind: int = 20
    num_hands: int = 20
    seed: int | None = None
    show_equity: bool = True
    equity_simulations: int = 500


POSITION_LABELS_3 = ["Dealer", "SB", "BB"]
POSITION_LABELS_4P = ["Dealer", "SB", "BB", "UTG", "UTG+1", "CO", "HJ", "LJ"]


def _create_provider(model_id: str, kwargs: dict[str, Any]) -> Any:
    if model_id.startswith("lmstudio:") or kwargs.get("host"):
        from hive.models.lmstudio import LMStudio

        clean = model_id.removeprefix("lmstudio:")
        return LMStudio(model=clean, **kwargs)
    from hive.models.factory import create_runtime_provider

    return create_runtime_provider(model_id)


def _create_agent(player: LLMPlayer) -> Any:
    from hive.runtime.agent import Agent
    from hive.runtime.persona import Persona

    provider = _create_provider(player.model_id, player.provider_kwargs)
    if player.persona is not None:
        persona = player.persona
    else:
        persona = Persona(
            name=player.name,
            personality=["poker player", "strategic", "reads opponents"],
            values=["winning", "calculated risk"],
            fears=["losing all chips"],
            purpose="Win the poker tournament through smart play",
            risk_tolerance=0.5,
        )
    return Agent(name=player.name, model=provider, persona=persona)


def _parse_response(response: str, num_options: int) -> int | None:
    text = response.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    match = re.search(r"\b([1-6])\b", text)
    if match:
        val = int(match.group(1))
        if 1 <= val <= num_options:
            return val
    return None


def _position_labels(
    players: list[PlayerState], dealer_idx: int
) -> dict[str, str]:
    alive = [p for p in players if not p.folded]
    n = len(alive)
    labels: dict[str, str] = {}
    try:
        dealer_pos = next(i for i, p in enumerate(alive) if p.name == players[dealer_idx].name)
    except StopIteration:
        return {p.name: "" for p in alive}

    for i in range(n):
        pos = (i - dealer_pos) % n
        if n == 2:
            label = ["Dealer/SB", "BB"][pos]
        elif n == 3:
            label = POSITION_LABELS_3[pos]
        else:
            label = POSITION_LABELS_4P[pos] if pos < len(POSITION_LABELS_4P) else f"Seat{pos}"
        labels[alive[i].name] = label

    return labels


def _opponent_style(p: PlayerState) -> str:
    if p.hands_played < 3:
        return "unknown"
    fold_rate = p.total_folds / max(p.hands_played, 1)
    raise_rate = p.total_raises / max(p.hands_played, 1)
    if raise_rate > 0.3:
        return "aggressive" if fold_rate < 0.3 else "tricky"
    if fold_rate > 0.4:
        return "tight"
    return "passive"


def _persona_context(persona: Any) -> list[str]:
    """Build behavioral guidance lines from a Persona's live params."""
    lines = ["", "BEHAVIORAL GUIDANCE:"]
    if persona.risk_tolerance >= 0.7:
        lines.append("  You're aggressive. Lean toward raises and all-ins.")
    elif persona.risk_tolerance <= 0.3:
        lines.append("  You play tight. Only premium hands.")
    else:
        lines.append("  You're balanced. Mix aggression with caution.")
    if persona.concentration < 0.5:
        lines.append("  You're feeling scattered. Keep your strategy simple.")
    if persona.values:
        lines.append(f"  Values: {', '.join(persona.values[:3])}")
    if persona.fears:
        lines.append(f"  Fears: {', '.join(persona.fears[:2])}")
    if persona.suffering:
        frag = persona.suffering.prompt_fragment()
        if frag:
            lines.append("")
            lines.append(frag)
    return lines


def _build_prompt(
    player: PlayerState,
    engine: PokerEngine,
    equity: EquityResult | None,
    valid_actions: list[Action],
    positions: dict[str, str],
    persona: Any = None,
) -> str:
    phase_name = {
        Phase.PRE_FLOP: "Pre-Flop",
        Phase.FLOP: "Flop",
        Phase.TURN: "Turn",
        Phase.RIVER: "River",
    }.get(engine.phase, str(engine.phase))

    lines = [
        f"TEXAS HOLD'EM — {phase_name} — Hand #{engine.hand_num}",
        "",
        f"Your cards: {' '.join(str(c) for c in player.hole_cards)}",
    ]

    if engine.community:
        lines.append(f"Community:  {' '.join(str(c) for c in engine.community)}")
        all_cards = player.hole_cards + engine.community
        hand = evaluate_hand(all_cards)
        lines.append(f"Your hand:  {describe_hand(hand)}")

    if equity:
        lines.append("")
        lines.append(f"Win probability: ~{equity.win_probability:.0%}")
        improvements = [
            f"{name}: {prob:.0%}"
            for name, prob in list(equity.hand_improvement.items())[:4]
        ]
        if improvements:
            lines.append(f"Hand chances: {', '.join(improvements)}")

    lines.append("")
    cost_to_call = engine.current_bet - player.bet_this_round
    lines.append(f"Pot: {engine.pot}  |  Your chips: {player.chips}  |  To call: {cost_to_call}")

    pos_parts = []
    for p in engine.players:
        if p.folded or p.chips <= 0:
            continue
        pos = positions.get(p.name, "")
        marker = " *YOU*" if p.name == player.name else ""
        pos_parts.append(f"[{pos}] {p.name} ({p.chips}){marker}")
    lines.append(f"Seats: {', '.join(pos_parts)}")

    shown = engine.showed_cards
    if shown:
        lines.append("")
        for name, cards in shown.items():
            if name != player.name:
                lines.append(
                    f"!! {name} SHOWED: {' '.join(str(c) for c in cards)}"
                )

    opponents = [p for p in engine.players if p.name != player.name and not p.folded]
    if opponents and any(p.hands_played >= 3 for p in opponents):
        lines.append("")
        for opp in opponents:
            if opp.hands_played >= 3:
                style = _opponent_style(opp)
                fold_pct = opp.total_folds / max(opp.hands_played, 1)
                raise_pct = opp.total_raises / max(opp.hands_played, 1)
                lines.append(
                    f"  {opp.name}: {style} "
                    f"(fold {fold_pct:.0%}, raise {raise_pct:.0%})"
                )

    if engine.action_log:
        lines.append("")
        lines.append("Actions this hand:")
        for ar in engine.action_log[-8:]:
            atype = ar.action.type.name.lower()
            if ar.action.type == ActionType.RAISE:
                lines.append(f"  {ar.player} raises to {ar.action.amount}")
            elif ar.action.type == ActionType.ALL_IN:
                lines.append(f"  {ar.player} ALL-IN ({ar.chips_spent})")
            else:
                if atype != "check":
                    lines.append(f"  {ar.player} {atype}s")
                else:
                    lines.append(f"  {ar.player} checks")

    lines.append("")
    lines.append("Your options:")
    option_num = 0
    action_map: list[Action] = []
    for a in valid_actions:
        if a.type == ActionType.SHOW_CARDS:
            continue
        option_num += 1
        action_map.append(a)
        if a.type == ActionType.FOLD:
            lines.append(f"  {option_num}. Fold")
        elif a.type == ActionType.CHECK:
            lines.append(f"  {option_num}. Check")
        elif a.type == ActionType.CALL:
            lines.append(f"  {option_num}. Call {a.amount}")
        elif a.type == ActionType.RAISE:
            lines.append(f"  {option_num}. Raise to {a.amount}")
        elif a.type == ActionType.ALL_IN:
            lines.append(f"  {option_num}. All-in ({player.chips + player.bet_this_round})")

    has_show = any(a.type == ActionType.SHOW_CARDS for a in valid_actions)
    if has_show and not player.showed_cards:
        option_num += 1
        action_map.append(Action(ActionType.SHOW_CARDS))
        lines.append(f"  {option_num}. Show your cards (reveal to intimidate, then choose action)")

    if persona is not None:
        lines.extend(_persona_context(persona))

    lines.append("")
    lines.append(f"Respond with ONLY the number (1-{option_num}).")

    return "\n".join(lines), action_map


async def run_tournament(
    player_configs: list[tuple[str, str, dict[str, Any]]],
    config: TableConfig,
    personas: dict[str, Any] | None = None,
) -> tuple[PokerEngine, dict[str, float]]:
    """Run a full poker tournament. Returns engine state and timing."""
    engine = PokerEngine(
        player_names=[name for name, _, _ in player_configs],
        starting_chips=config.starting_chips,
        small_blind=config.small_blind,
        big_blind=config.big_blind,
        seed=config.seed,
    )

    llm_players: dict[str, LLMPlayer] = {}
    models_map: dict[str, str] = {}
    for name, model_id, kwargs in player_configs:
        lp = LLMPlayer(name=name, model_id=model_id, provider_kwargs=kwargs)
        if personas and name in personas:
            lp.persona = personas[name]
        lp.agent = _create_agent(lp)
        llm_players[name] = lp
        models_map[name] = model_id

    display.tournament_header(
        [(name, mid) for name, mid, _ in player_configs],
        config.num_hands,
        config.starting_chips,
        (config.small_blind, config.big_blind),
    )

    for hand_i in range(config.num_hands):
        if engine.is_tournament_over():
            break

        engine.new_hand()
        sb, bb = engine.get_sb_bb()
        dealer = engine.get_dealer()
        display.hand_header(
            engine.hand_num, dealer.name, sb.name, bb.name,
            (config.small_blind, config.big_blind),
        )
        display.deal_cards([p for p in engine.players if not p.folded])

        phases = [Phase.PRE_FLOP, Phase.FLOP, Phase.TURN, Phase.RIVER]
        for phase_idx, expected_phase in enumerate(phases):
            if engine.phase != expected_phase:
                break

            if phase_idx > 0:
                display.community_cards(engine.phase, engine.community)

            active_non_allin = [
                p for p in engine.players if not p.folded and not p.all_in
            ]
            if len(active_non_allin) <= 1:
                if not engine.is_hand_over():
                    engine.advance_phase()
                continue

            max_actions = len(engine.players) * 6
            action_count = 0
            while not engine.is_betting_round_complete() and action_count < max_actions:
                action_count += 1
                current = engine.get_current_player()
                if current is None:
                    break

                if engine.is_hand_over():
                    break

                positions = _position_labels(engine.players, engine.dealer_idx)
                valid = engine.get_valid_actions(current.name)

                eq = None
                if config.show_equity and current.hole_cards:
                    opponents_in = sum(
                        1 for p in engine.players
                        if not p.folded and p.name != current.name
                    )
                    eq = calculate_equity(
                        current.hole_cards,
                        engine.community,
                        opponents_in,
                        num_simulations=config.equity_simulations,
                    )

                lp = llm_players[current.name]
                prompt, action_map = _build_prompt(
                    current, engine, eq, valid, positions,
                    persona=lp.persona,
                )

                t0 = time.time()
                try:
                    response = await lp.agent.run_once(prompt)
                except Exception:
                    response = "2"
                elapsed = time.time() - t0
                lp.total_time += elapsed

                choice = _parse_response(response, len(action_map))
                if choice is not None:
                    action = action_map[choice - 1]
                else:
                    action = next(
                        (a for a in action_map if a.type in (ActionType.CHECK, ActionType.CALL)),
                        action_map[0],
                    )

                if action.type == ActionType.SHOW_CARDS:
                    result = engine.apply_action(current.name, action)
                    display.show_cards_reveal(current.name, current.hole_cards)
                    continue

                result = engine.apply_action(current.name, action)
                display.player_action(result)

            if engine.is_hand_over():
                summary = engine.resolve_fold_win()
                display.fold_win(summary)
                break

            if expected_phase != Phase.RIVER:
                engine.advance_phase()
            else:
                summary = engine.resolve_showdown()
                display.showdown(summary)

        else:
            if engine.phase == Phase.SHOWDOWN or engine.phase == Phase.RIVER:
                if engine.phase != Phase.HAND_OVER:
                    summary = engine.resolve_showdown()
                    display.showdown(summary)

        display.chip_counts(engine.players, config.starting_chips)

        for p in engine.players:
            if p.chips <= 0 and p.hands_played > 0:
                display.player_eliminated(p.name)

        engine.rotate_dealer()

    times = {name: lp.total_time for name, lp in llm_players.items()}
    display.tournament_results(engine.players, config.starting_chips, models_map, times)

    return engine, times
