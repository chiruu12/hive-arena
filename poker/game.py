"""Texas Hold'em poker game for LLMs."""

import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from poker.cards import Card, HandResult, evaluate_hand, make_deck

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

console = Console()

STARTING_CHIPS = 1000
SMALL_BLIND = 10
BIG_BLIND = 20


@dataclass
class Player:
    name: str
    model_id: str
    provider_kwargs: dict[str, Any] = field(default_factory=dict)
    chips: int = STARTING_CHIPS
    hole_cards: list[Card] = field(default_factory=list)
    current_bet: int = 0
    folded: bool = False
    all_in: bool = False
    hands_won: int = 0
    hands_played: int = 0
    total_time: float = 0.0
    bluffs: int = 0
    folds: int = 0
    raises: int = 0
    agent: Any = None


@dataclass
class HandState:
    pot: int = 0
    community: list[Card] = field(default_factory=list)
    current_bet: int = 0
    hand_num: int = 0


def _create_provider(model_id: str, kwargs: dict[str, Any]) -> Any:
    if model_id.startswith("lmstudio:") or kwargs.get("host"):
        from hive.models.lmstudio import LMStudio

        clean = model_id.removeprefix("lmstudio:")
        return LMStudio(model=clean, **kwargs)
    from hive.models.factory import create_runtime_provider

    return create_runtime_provider(model_id)


def _create_agent(player: Player) -> Any:
    from hive.runtime.agent import Agent
    from hive.runtime.persona import Persona

    provider = _create_provider(player.model_id, player.provider_kwargs)
    persona = Persona(
        name=player.name,
        personality=["poker player", "strategic", "reads opponents"],
        values=["winning", "calculated risk"],
        fears=["losing all chips"],
        purpose="Win the poker tournament",
        risk_tolerance=0.5,
    )
    return Agent(name=player.name, model=provider, persona=persona)


def _format_cards(cards: list[Card]) -> str:
    return " ".join(str(c) for c in cards)


def _build_prompt(
    player: Player,
    hand: HandState,
    phase: str,
    action_history: list[str],
) -> str:
    lines = [
        f"TEXAS HOLD'EM — {phase}",
        f"Hand #{hand.hand_num}",
        "",
        f"Your cards: {_format_cards(player.hole_cards)}",
    ]
    if hand.community:
        lines.append(f"Community: {_format_cards(hand.community)}")

        all_cards = player.hole_cards + hand.community
        result = evaluate_hand(all_cards)
        lines.append(f"Your current hand: {result.name}")

    lines.append("")
    lines.append(f"Your chips: {player.chips}")
    lines.append(f"Pot: {hand.pot}")
    lines.append(f"Current bet: {hand.current_bet}")
    lines.append(f"You've put in: {player.current_bet}")
    cost_to_call = hand.current_bet - player.current_bet

    lines.append("")
    if action_history:
        lines.append("Actions this round:")
        for a in action_history[-5:]:
            lines.append(f"  {a}")
        lines.append("")

    lines.append("Your options:")
    lines.append("  1. Fold — surrender your cards")
    if cost_to_call > 0:
        lines.append(f"  2. Call — match the bet (costs {cost_to_call} chips)")
    else:
        lines.append("  2. Check — stay in for free")
    raise_amount = max(BIG_BLIND, hand.current_bet * 2)
    if raise_amount <= player.chips:
        lines.append(f"  3. Raise to {raise_amount} — show strength")
    else:
        lines.append(f"  3. All-in ({player.chips} chips)")

    lines.append("")
    lines.append("Respond with ONLY the number (1, 2, or 3). Nothing else.")
    return "\n".join(lines)


def _parse_action(response: str) -> int:
    text = response.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    match = re.search(r"\b([1-3])\b", text)
    if match:
        return int(match.group(1))
    return 2


async def play_betting_round(
    players: list[Player],
    hand: HandState,
    phase: str,
    action_history: list[str],
) -> None:
    """One betting round — each active player acts in order."""
    active = [p for p in players if not p.folded and not p.all_in and p.chips > 0]
    if len(active) <= 1:
        return

    acted: set[str] = set()
    last_raiser: str | None = None

    i = 0
    max_iterations = len(active) * 3
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        p = active[i % len(active)]

        if p.folded or p.all_in:
            i += 1
            continue

        if p.name in acted and p.name != last_raiser and last_raiser not in acted:
            pass
        elif p.name in acted and last_raiser is None:
            break

        prompt = _build_prompt(p, hand, phase, action_history)

        t0 = time.time()
        try:
            response = await p.agent.run_once(prompt)
        except Exception as e:
            console.print(f"    [dim]{p.name} error: {e}, defaulting to check/call[/dim]")
            response = "2"
        elapsed = time.time() - t0
        p.total_time += elapsed

        action = _parse_action(response)
        cost_to_call = hand.current_bet - p.current_bet

        if action == 1:
            p.folded = True
            p.folds += 1
            action_history.append(f"{p.name} folds")
            console.print(f"    {p.name}: [red]FOLD[/red]")
        elif action == 3:
            raise_to = max(BIG_BLIND, hand.current_bet * 2)
            if raise_to >= p.chips:
                amount = p.chips
                p.current_bet += amount
                p.chips = 0
                p.all_in = True
                hand.pot += amount
                hand.current_bet = max(hand.current_bet, p.current_bet)
                action_history.append(f"{p.name} ALL-IN ({amount})")
                console.print(f"    {p.name}: [bold red]ALL-IN {amount}[/bold red]")
            else:
                cost = raise_to - p.current_bet
                p.chips -= cost
                hand.pot += cost
                p.current_bet = raise_to
                hand.current_bet = raise_to
                action_history.append(f"{p.name} raises to {raise_to}")
                console.print(f"    {p.name}: [yellow]RAISE to {raise_to}[/yellow]")
            p.raises += 1
            last_raiser = p.name
            acted = {p.name}
        else:
            if cost_to_call > 0:
                pay = min(cost_to_call, p.chips)
                p.chips -= pay
                p.current_bet += pay
                hand.pot += pay
                if p.chips == 0:
                    p.all_in = True
                action_history.append(f"{p.name} calls {pay}")
                console.print(f"    {p.name}: [green]CALL {pay}[/green]")
            else:
                action_history.append(f"{p.name} checks")
                console.print(f"    {p.name}: [dim]check[/dim]")

        acted.add(p.name)
        i += 1

        still_active = [p for p in active if not p.folded and not p.all_in]
        if len(still_active) <= 1:
            break
        all_matched = all(
            p.current_bet == hand.current_bet or p.all_in or p.folded
            for p in active
        )
        if all_matched and len(acted) >= len(still_active):
            break


async def play_hand(
    players: list[Player],
    hand_num: int,
    deck_seed: int,
) -> str | None:
    """Play one hand of Texas Hold'em. Returns winner name."""
    rng = random.Random(deck_seed)
    deck = make_deck()
    rng.shuffle(deck)

    hand = HandState(hand_num=hand_num)
    action_history: list[str] = []

    for p in players:
        p.hole_cards = []
        p.current_bet = 0
        p.folded = p.chips <= 0
        p.all_in = False
        if not p.folded:
            p.hands_played += 1

    active = [p for p in players if not p.folded]
    if len(active) < 2:
        return None

    card_idx = 0
    for p in active:
        p.hole_cards = [deck[card_idx], deck[card_idx + 1]]
        card_idx += 2

    sb_player = active[0]
    bb_player = active[1 % len(active)]
    sb = min(SMALL_BLIND, sb_player.chips)
    bb = min(BIG_BLIND, bb_player.chips)
    sb_player.chips -= sb
    sb_player.current_bet = sb
    bb_player.chips -= bb
    bb_player.current_bet = bb
    hand.pot = sb + bb
    hand.current_bet = bb

    console.print(f"\n  [bold]Hand #{hand_num}[/bold] — Pot: {hand.pot}")
    for p in active:
        console.print(f"    {p.name}: {_format_cards(p.hole_cards)} ({p.chips} chips)")

    await play_betting_round(active, hand, "Pre-Flop", action_history)

    still_in = [p for p in active if not p.folded]
    if len(still_in) <= 1:
        winner = still_in[0] if still_in else active[0]
        winner.chips += hand.pot
        winner.hands_won += 1
        console.print(f"    [green]{winner.name} wins {hand.pot} (everyone folded)[/green]")
        return winner.name

    hand.community = [deck[card_idx], deck[card_idx + 1], deck[card_idx + 2]]
    card_idx += 3
    console.print(f"  [cyan]Flop:[/cyan] {_format_cards(hand.community)}")
    for p in active:
        p.current_bet = 0
    hand.current_bet = 0
    await play_betting_round(active, hand, "Flop", action_history)

    still_in = [p for p in active if not p.folded]
    if len(still_in) <= 1:
        winner = still_in[0]
        winner.chips += hand.pot
        winner.hands_won += 1
        console.print(f"    [green]{winner.name} wins {hand.pot}[/green]")
        return winner.name

    hand.community.append(deck[card_idx])
    card_idx += 1
    console.print(f"  [cyan]Turn:[/cyan] {_format_cards(hand.community)}")
    for p in active:
        p.current_bet = 0
    hand.current_bet = 0
    await play_betting_round(active, hand, "Turn", action_history)

    still_in = [p for p in active if not p.folded]
    if len(still_in) <= 1:
        winner = still_in[0]
        winner.chips += hand.pot
        winner.hands_won += 1
        console.print(f"    [green]{winner.name} wins {hand.pot}[/green]")
        return winner.name

    hand.community.append(deck[card_idx])
    console.print(f"  [cyan]River:[/cyan] {_format_cards(hand.community)}")
    for p in active:
        p.current_bet = 0
    hand.current_bet = 0
    await play_betting_round(active, hand, "River", action_history)

    console.print(f"\n  [bold]Showdown![/bold] Pot: {hand.pot}")
    still_in = [p for p in active if not p.folded]
    best_player: Player | None = None
    best_hand: HandResult | None = None

    for p in still_in:
        all_cards = p.hole_cards + hand.community
        result = evaluate_hand(all_cards)
        console.print(
            f"    {p.name}: {_format_cards(p.hole_cards)} → [bold]{result.name}[/bold]"
        )
        if best_hand is None or result > best_hand:
            best_hand = result
            best_player = p

    if best_player:
        best_player.chips += hand.pot
        best_player.hands_won += 1
        console.print(
            f"    [green bold]{best_player.name} wins {hand.pot} "
            f"with {best_hand.name}![/green bold]"
        )
        return best_player.name
    return None


async def run_tournament(
    player_configs: list[tuple[str, str, dict[str, Any]]],
    num_hands: int = 10,
    seed: int | None = None,
) -> list[Player]:
    """Run a full poker tournament."""
    base_seed = seed if seed is not None else random.randint(0, 999999)

    players = []
    for name, model_id, kwargs in player_configs:
        p = Player(name=name, model_id=model_id, provider_kwargs=kwargs)
        p.agent = _create_agent(p)
        players.append(p)

    console.print(
        Panel(
            f"[bold]LLM Poker Tournament[/bold]\n\n"
            + "\n".join(f"  {p.name} ({p.model_id.split('/')[-1][:20]})" for p in players)
            + f"\n\n{num_hands} hands, {STARTING_CHIPS} chips each",
            border_style="green",
        )
    )

    for hand_num in range(1, num_hands + 1):
        alive = [p for p in players if p.chips > 0]
        if len(alive) < 2:
            console.print("\n[bold red]Not enough players to continue![/bold red]")
            break

        players_rotated = alive[(hand_num - 1) % len(alive) :] + alive[: (hand_num - 1) % len(alive)]
        await play_hand(players_rotated, hand_num, base_seed + hand_num)

        parts = []
        for p in players:
            if p.chips > STARTING_CHIPS:
                parts.append(f"[green]{p.name}:{p.chips}[/green]")
            elif p.chips < 200:
                parts.append(f"[red]{p.name}:{p.chips}[/red]")
            else:
                parts.append(f"{p.name}:{p.chips}")
        console.print(f"  Chips: {'  '.join(parts)}")

    return players


def print_tournament_results(players: list[Player]) -> None:
    """Print the final tournament standings."""
    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print("[bold]TOURNAMENT RESULTS[/bold]")
    console.print(f"[bold]{'='*60}[/bold]\n")

    ranked = sorted(players, key=lambda p: p.chips, reverse=True)

    table = Table(title="Final Standings", show_lines=True)
    table.add_column("Rank", style="bold", width=6)
    table.add_column("Player", style="cyan")
    table.add_column("Model", max_width=20)
    table.add_column("Chips", justify="right")
    table.add_column("P/L", justify="right")
    table.add_column("Hands Won", justify="right")
    table.add_column("Folds", justify="right")
    table.add_column("Raises", justify="right")
    table.add_column("Avg Time", justify="right", style="dim")

    medals = {0: "\U0001f947", 1: "\U0001f948", 2: "\U0001f949"}
    for i, p in enumerate(ranked):
        pl = p.chips - STARTING_CHIPS
        pl_str = f"+{pl}" if pl >= 0 else str(pl)
        pl_style = "green" if pl >= 0 else "red"
        avg = p.total_time / max(p.hands_played, 1)
        table.add_row(
            medals.get(i, str(i + 1)),
            p.name,
            p.model_id.split("/")[-1][:20],
            str(p.chips),
            f"[{pl_style}]{pl_str}[/{pl_style}]",
            str(p.hands_won),
            str(p.folds),
            str(p.raises),
            f"{avg:.1f}s",
        )

    console.print(table)
