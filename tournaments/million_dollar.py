"""Million Dollar Tournament — 6 LLMs, $1M chips, 25 hands."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hive.runtime.persona import Persona

from poker.display import console
from poker.table import TableConfig, run_tournament

SHARED_PERSONA = Persona(
    name="Poker Player",
    personality=["strategic", "competitive", "focused"],
    values=["winning", "smart decisions", "reading opponents"],
    fears=["losing chips", "being outplayed"],
    purpose="Win the poker tournament through smart play",
    risk_tolerance=0.5,
    social_drive=0.4,
    concentration=0.8,
)

PLAYERS = [
    {
        "name": "Liquid",
        "model": "lmstudio:liquid/lfm2.5-1.2b",
        "kwargs": {"host": "http://localhost:1234/v1"},
    },
    {
        "name": "Qwen",
        "model": "lmstudio:qwen/qwen3-1.7b",
        "kwargs": {"host": "http://localhost:1234/v1"},
    },
    {
        "name": "Phi",
        "model": "lmstudio:microsoft/phi-4-mini-reasoning",
        "kwargs": {"host": "http://localhost:1234/v1"},
    },
    {
        "name": "Haiku",
        "model": "claude-haiku-4-5",
        "kwargs": {},
    },
    {
        "name": "MiniMax",
        "model": "fireworks:accounts/fireworks/models/minimax-m2p7",
        "kwargs": {},
    },
    {
        "name": "Kimi",
        "model": "fireworks:accounts/fireworks/models/kimi-k2p6",
        "kwargs": {},
    },
]

STARTING_CHIPS = 1_000_000
NUM_HANDS = 25
SMALL_BLIND = 5_000
BIG_BLIND = 10_000


def main() -> None:
    console.print("\n[bold red]" + "=" * 60 + "[/bold red]")
    console.print("[bold red]  MILLION DOLLAR POKER TOURNAMENT[/bold red]")
    console.print("[bold red]  6 LLMs • $1,000,000 chips • 25 hands[/bold red]")
    console.print("[bold red]" + "=" * 60 + "[/bold red]\n")

    console.print("[bold]Players (same persona, model is the only variable):[/bold]")
    for p in PLAYERS:
        model_short = p["model"].split("/")[-1][:25]
        local = "LOCAL" if p["model"].startswith("lmstudio:") else "CLOUD"
        console.print(f"  [cyan]{p['name']:12s}[/cyan] [{local}] ({model_short})")
    console.print()

    player_configs = [
        (p["name"], p["model"], p["kwargs"]) for p in PLAYERS
    ]
    personas = {}
    for p in PLAYERS:
        persona = Persona(
            name=p["name"],
            personality=SHARED_PERSONA.personality.copy(),
            values=SHARED_PERSONA.values.copy(),
            fears=SHARED_PERSONA.fears.copy(),
            purpose=SHARED_PERSONA.purpose,
            risk_tolerance=SHARED_PERSONA.risk_tolerance,
            social_drive=SHARED_PERSONA.social_drive,
            concentration=SHARED_PERSONA.concentration,
        )
        personas[p["name"]] = persona

    config = TableConfig(
        starting_chips=STARTING_CHIPS,
        small_blind=SMALL_BLIND,
        big_blind=BIG_BLIND,
        num_hands=NUM_HANDS,
        seed=42,
        show_equity=True,
        equity_simulations=500,
    )

    engine, times = asyncio.run(
        run_tournament(
            player_configs, config,
            personas=personas,
            enable_suffering=True,
        )
    )

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    console.print(f"\n[bold]{'=' * 60}[/bold]")
    console.print("[bold]TOURNAMENT HIGHLIGHTS[/bold]")
    console.print(f"[bold]{'=' * 60}[/bold]\n")

    ranked = sorted(engine.players, key=lambda p: p.chips, reverse=True)
    results = {
        "tournament": "Million Dollar Poker — 6 LLMs",
        "date": ts,
        "config": {
            "starting_chips": STARTING_CHIPS,
            "num_hands": NUM_HANDS,
            "blinds": f"{SMALL_BLIND}/{BIG_BLIND}",
            "seed": 42,
            "enable_suffering": True,
            "same_persona": True,
        },
        "players": [],
        "highlights": [],
    }

    for i, p in enumerate(ranked):
        model = next(
            (pl["model"] for pl in PLAYERS if pl["name"] == p.name), "?"
        )
        model_short = model.split("/")[-1][:25]
        local = "LOCAL" if model.startswith("lmstudio:") else "CLOUD"
        pl = p.chips - STARTING_CHIPS
        avg_t = times.get(p.name, 0) / max(p.hands_played, 1)

        medals = {0: "\U0001f947", 1: "\U0001f948", 2: "\U0001f949"}
        medal = medals.get(i, f"#{i+1}")

        if p.chips > 0:
            pl_str = f"+${pl:,}" if pl >= 0 else f"-${abs(pl):,}"
            status = f"${p.chips:,} ({pl_str})"
        else:
            status = "\U0001f480 ELIMINATED"

        console.print(f"  {medal} [bold]{p.name}[/bold] [{local}] ({model_short})")
        console.print(f"     Chips: {status}")
        console.print(
            f"     Stats: {p.hands_won}W / {p.total_folds}F / "
            f"{p.total_raises}R | {avg_t:.1f}s avg"
        )

        results["players"].append({
            "rank": i + 1,
            "name": p.name,
            "model": model,
            "type": local,
            "final_chips": p.chips,
            "profit_loss": pl,
            "hands_won": p.hands_won,
            "hands_played": p.hands_played,
            "folds": p.total_folds,
            "raises": p.total_raises,
            "calls": p.total_calls,
            "checks": p.total_checks,
            "avg_decision_time": round(avg_t, 2),
            "eliminated": p.chips <= 0,
        })

        if p.chips > STARTING_CHIPS * 2:
            results["highlights"].append(
                f"{p.name} doubled up! Final: ${p.chips:,}"
            )
        if p.chips <= 0:
            results["highlights"].append(f"{p.name} ({model_short}) eliminated")

    for h in results["highlights"]:
        console.print(f"  {h}")

    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"million-dollar-{ts}.json"
    out_path.write_text(json.dumps(results, indent=2))
    console.print(f"\n[green]Results saved:[/green] {out_path}")


if __name__ == "__main__":
    main()
