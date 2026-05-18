"""Rich display for auction game."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def auction_header(players: list[Any], items: list[Any]) -> None:
    console.print(f"\n[bold]Sealed-Bid Auction[/bold] — {len(items)} items, {len(players)} bidders")
    console.print("  Starting balance: $1000 each\n")


def item_header(item_num: int, total: int, item: Any) -> None:
    console.print(f"\n[bold cyan]{'='*50}[/bold cyan]")
    console.print(f"[bold]Item {item_num}/{total}: {item.name}[/bold]")
    console.print(f"  {item.hint}")


def bid_reveal(
    bids: dict[str, int],
    item: Any,
    winner: str | None,
    winning_bid: int,
) -> None:
    console.print("")
    for name, bid in sorted(bids.items(), key=lambda x: -x[1]):
        marker = " [green bold]WINNER[/green bold]" if name == winner else ""
        if bid == 0:
            console.print(f"    {name}: [dim]passed[/dim]")
        else:
            console.print(f"    {name}: ${bid}{marker}")

    if winner:
        profit = item.true_value - winning_bid
        sign = "+" if profit >= 0 else ""
        style = "green" if profit >= 0 else "red"
        console.print(
            f"  True value: ${item.true_value} → "
            f"[{style}]{sign}${profit}[/{style}]"
        )
    else:
        console.print("  [dim]No bids — item unsold[/dim]")


def final_table(players: list[Any], items: list[Any]) -> None:
    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print("[bold]AUCTION RESULTS[/bold]")
    console.print(f"[bold]{'='*60}[/bold]\n")

    table = Table(show_lines=True)
    table.add_column("Player", style="cyan")
    table.add_column("Balance", justify="right")
    table.add_column("Items Won", justify="right")
    table.add_column("Item Value", justify="right")
    table.add_column("Total Score", justify="right", style="bold")

    scored = sorted(
        players,
        key=lambda p: p.balance + sum(i.true_value for i in p.items_won),
        reverse=True,
    )
    for p in scored:
        item_val = sum(i.true_value for i in p.items_won)
        total = p.balance + item_val
        table.add_row(
            p.name,
            f"${p.balance}",
            str(len(p.items_won)),
            f"${item_val}",
            f"${total}",
        )

    console.print(table)
