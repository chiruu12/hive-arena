"""Rich console display for poker games."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from poker.cards import Card
from poker.engine import (
    ActionResult,
    ActionType,
    HandSummary,
    Phase,
    PlayerState,
)

console = Console()

PHASE_NAMES = {
    Phase.PRE_FLOP: "Pre-Flop",
    Phase.FLOP: "Flop",
    Phase.TURN: "Turn",
    Phase.RIVER: "River",
    Phase.SHOWDOWN: "Showdown",
}


def _cards(cards: list[Card]) -> str:
    return " ".join(str(c) for c in cards)


def tournament_header(
    players: list[tuple[str, str]],
    num_hands: int,
    starting_chips: int,
    blinds: tuple[int, int],
) -> None:
    lines = ["[bold]LLM Poker Tournament[/bold]\n"]
    for name, model in players:
        short = model.split("/")[-1][:20]
        lines.append(f"  {name} ({short})")
    lines.append(f"\n{num_hands} hands, {starting_chips} chips, blinds {blinds[0]}/{blinds[1]}")
    console.print(Panel("\n".join(lines), border_style="green"))


def hand_header(
    hand_num: int,
    dealer: str,
    sb: str,
    bb: str,
    blinds: tuple[int, int],
) -> None:
    console.print(
        f"\n[bold cyan]{'='*55}[/bold cyan]"
        f"\n[bold]Hand #{hand_num}[/bold]  "
        f"Dealer: {dealer}  SB: {sb} ({blinds[0]})  BB: {bb} ({blinds[1]})"
    )


def deal_cards(players: list[PlayerState]) -> None:
    for p in players:
        if not p.folded and p.hole_cards:
            console.print(f"  {p.name:12s} [{_cards(p.hole_cards)}]  ({p.chips} chips)")


def community_cards(phase: Phase, cards: list[Card]) -> None:
    name = PHASE_NAMES.get(phase, str(phase))
    console.print(f"\n  [cyan]{name}:[/cyan] [{_cards(cards)}]")


def player_action(result: ActionResult) -> None:
    a = result.action
    name = result.player

    if a.type == ActionType.FOLD:
        console.print(f"    {name}: [red]FOLD[/red]")
    elif a.type == ActionType.CHECK:
        console.print(f"    {name}: [dim]check[/dim]")
    elif a.type == ActionType.CALL:
        console.print(f"    {name}: [green]CALL {result.chips_spent}[/green]")
    elif a.type == ActionType.RAISE:
        console.print(f"    {name}: [yellow]RAISE to {a.amount}[/yellow]")
    elif a.type == ActionType.ALL_IN:
        console.print(f"    {name}: [bold red]ALL-IN {result.chips_spent}[/bold red]")
    elif a.type == ActionType.SHOW_CARDS:
        console.print(f"    {name}: [magenta]SHOWS CARDS[/magenta]")


def show_cards_reveal(name: str, cards: list[Card]) -> None:
    console.print(f"    [magenta]{name} reveals: [{_cards(cards)}][/magenta]")


def showdown(summary: HandSummary) -> None:
    console.print(f"\n  [bold]Showdown![/bold] Community: [{_cards(summary.community)}]")

    if len(summary.pots) > 1:
        for i, pot in enumerate(summary.pots):
            label = "Main pot" if i == 0 else f"Side pot {i}"
            console.print(f"    [dim]{label}: {pot.amount:,} ({', '.join(pot.eligible)})[/dim]")

    ranked = sorted(summary.results, key=lambda r: (r.hand.rank, r.hand.tiebreaker), reverse=True)
    for r in ranked:
        if r.contested_win:
            marker = " [green bold]WINNER[/green bold]"
            winnings = f" [green](+{r.winnings:,})[/green]"
        elif r.winnings > 0:
            marker = ""
            winnings = f" [dim](+{r.winnings:,} refund)[/dim]"
        else:
            marker = ""
            winnings = ""
        console.print(
            f"    {r.player_name}: [{_cards(r.hole_cards)}] "
            f"-> [bold]{r.hand_description}[/bold]{marker}{winnings}"
        )


def fold_win(summary: HandSummary) -> None:
    if summary.winners:
        console.print(
            f"    [green]{summary.winners[0]} wins {summary.pots[0].amount} "
            f"(everyone folded)[/green]"
        )


def chip_counts(
    players: list[PlayerState],
    starting: int,
    suffering_states: dict[str, Any] | None = None,
) -> None:
    parts = []
    for p in players:
        tilt = ""
        if suffering_states and p.name in suffering_states:
            s = suffering_states[p.name]
            load = s.cumulative_load
            if s.in_crisis:
                tilt = " [bold red]\U0001f480 CRISIS[/bold red]"
            elif load >= 0.6:
                tilt = " [red]\U0001f525 TILT[/red]"
            elif load >= 0.3:
                tilt = " [yellow]stressed[/yellow]"

        if p.chips <= 0:
            parts.append(f"[dim]{p.name}:OUT[/dim]")
        elif p.chips > starting:
            parts.append(f"[green]{p.name}:{p.chips}[/green]{tilt}")
        elif p.chips < starting // 3:
            parts.append(f"[red]{p.name}:{p.chips}[/red]{tilt}")
        else:
            parts.append(f"{p.name}:{p.chips}{tilt}")
    console.print(f"  Chips: {'  '.join(parts)}")


def player_eliminated(name: str) -> None:
    console.print(f"\n  [bold red]{name} is eliminated![/bold red]")


def waiting_for(name: str) -> None:
    console.print(f"    [dim]waiting for {name}...[/dim]", end="\r")


def tournament_results(
    players: list[PlayerState],
    starting: int,
    models: dict[str, str],
    times: dict[str, float],
) -> None:
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
    table.add_column("Won", justify="right")
    table.add_column("Folds", justify="right")
    table.add_column("Raises", justify="right")
    table.add_column("Avg Time", justify="right", style="dim")

    medals = {0: "\U0001f947", 1: "\U0001f948", 2: "\U0001f949"}
    for i, p in enumerate(ranked):
        pl = p.chips - starting
        pl_str = f"+{pl}" if pl >= 0 else str(pl)
        pl_style = "green" if pl >= 0 else "red"
        model = models.get(p.name, "?").split("/")[-1][:20]
        avg_t = times.get(p.name, 0) / max(p.hands_played, 1)
        table.add_row(
            medals.get(i, str(i + 1)),
            p.name,
            model,
            str(p.chips),
            f"[{pl_style}]{pl_str}[/{pl_style}]",
            str(p.hands_won),
            str(p.total_folds),
            str(p.total_raises),
            f"{avg_t:.1f}s",
        )

    console.print(table)


def scoreboard(
    players: list[PlayerState],
    starting: int,
    hand_num: int,
    total_hands: int,
    models: dict[str, str],
    times: dict[str, float],
    suffering_states: dict[str, Any] | None = None,
) -> None:
    """Print a live scoreboard after each hand."""
    ranked = sorted(players, key=lambda p: p.chips, reverse=True)

    table = Table(
        title=f"Scoreboard — Hand {hand_num}/{total_hands}",
        show_lines=False,
        border_style="dim",
        padding=(0, 1),
    )
    table.add_column("#", style="bold", width=3)
    table.add_column("Player", style="cyan", width=12)
    table.add_column("Chips", justify="right", width=12)
    table.add_column("P/L", justify="right", width=10)
    table.add_column("Bar", width=20)
    table.add_column("W/F/R", justify="center", width=8)
    table.add_column("Status", width=12)

    max_chips = max((p.chips for p in ranked), default=starting)
    bar_width = 16

    for i, p in enumerate(ranked):
        pl = p.chips - starting
        if p.chips <= 0:
            pl_str = f"[red]-${starting:,}[/red]"
            bar = "[dim]" + "░" * bar_width + "[/dim]"
            status = "[bold red]OUT[/bold red]"
        else:
            if pl >= 0:
                pl_str = f"[green]+${pl:,}[/green]"
            else:
                pl_str = f"[red]-${abs(pl):,}[/red]"
            filled = int((p.chips / max(max_chips, 1)) * bar_width)
            if p.chips > starting:
                bar = "[green]" + "█" * filled + "[/green]" + "░" * (bar_width - filled)
            elif p.chips < starting // 3:
                bar = "[red]" + "█" * filled + "[/red]" + "░" * (bar_width - filled)
            else:
                bar = "█" * filled + "░" * (bar_width - filled)

            status = ""
            if suffering_states and p.name in suffering_states:
                s = suffering_states[p.name]
                load = s.cumulative_load
                if s.in_crisis:
                    status = "[bold red]💀 CRISIS[/bold red]"
                elif load >= 0.6:
                    status = "[red]🔥 TILT[/red]"
                elif load >= 0.3:
                    status = "[yellow]😰[/yellow]"

        wfr = f"{p.hands_won}/{p.total_folds}/{p.total_raises}"

        table.add_row(
            str(i + 1),
            p.name,
            f"${p.chips:,}" if p.chips > 0 else "—",
            pl_str,
            bar,
            wfr,
            status,
        )

    console.print(table)


def tilt_alert(name: str, old_risk: float, new_risk: float) -> None:
    if new_risk > old_risk + 0.15:
        console.print(
            f"    [bold yellow]!! {name}'s risk tolerance spiked: "
            f"{old_risk:.0%} → {new_risk:.0%}[/bold yellow]"
        )


def journal_entry(name: str, text: str) -> None:
    console.print(f"    [blue]\U0001f4dd {name}: {text[:80]}[/blue]")


def table_talk(name: str, message: str) -> None:
    console.print(f"    [magenta]\U0001f4ac {name}:[/magenta] \"{message}\"")
