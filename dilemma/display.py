"""Rich display for Prisoner's Dilemma."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

console = Console()


def round_result(
    round_num: int,
    name1: str, choice1: str, pay1: int,
    name2: str, choice2: str, pay2: int,
) -> None:
    c1_style = "[green]COOPERATE[/green]" if choice1 == "cooperate" else "[red]BETRAY[/red]"
    c2_style = "[green]COOPERATE[/green]" if choice2 == "cooperate" else "[red]BETRAY[/red]"
    console.print(
        f"  R{round_num:2d}:  {name1}: {c1_style} (+{pay1})  |  "
        f"{name2}: {c2_style} (+{pay2})"
    )


def summary_table(p1, p2) -> None:
    console.print(f"\n[bold]{'='*50}[/bold]")
    console.print("[bold]PRISONER'S DILEMMA RESULTS[/bold]")
    console.print(f"[bold]{'='*50}[/bold]\n")

    table = Table(show_lines=True)
    table.add_column("Player", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Cooperated", justify="right")
    table.add_column("Betrayed", justify="right")
    table.add_column("Coop Rate", justify="right")

    for p in [p1, p2]:
        coop = p.history.count("cooperate")
        betray = p.history.count("betray")
        rate = coop / len(p.history) if p.history else 0
        table.add_row(
            p.name, str(p.score), str(coop), str(betray), f"{rate:.0%}"
        )

    console.print(table)
