"""Poker CLI — run an LLM poker tournament."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from poker.display import console
from poker.table import TableConfig, run_tournament

PRESETS = {
    "local": [
        ("Liquid", "lmstudio:liquid/lfm2.5-1.2b", {}),
        ("Qwen", "lmstudio:qwen/qwen3-1.7b", {}),
        ("Phi", "lmstudio:microsoft/phi-4-mini-reasoning", {}),
    ],
    "cloud": [
        ("Haiku", "claude-haiku-4-5", {}),
        ("MiniMax", "accounts/fireworks/models/minimax-m2p7", {}),
    ],
    "all": [
        ("Liquid", "lmstudio:liquid/lfm2.5-1.2b", {}),
        ("Qwen", "lmstudio:qwen/qwen3-1.7b", {}),
        ("Phi", "lmstudio:microsoft/phi-4-mini-reasoning", {}),
        ("Haiku", "claude-haiku-4-5", {}),
        ("MiniMax", "accounts/fireworks/models/minimax-m2p7", {}),
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Poker Tournament")
    parser.add_argument("--models", nargs="+", help="Model IDs")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Preset player list")
    parser.add_argument("--port", type=int, default=1234, help="LM Studio port")
    parser.add_argument("--hands", type=int, default=20, help="Number of hands")
    parser.add_argument("--chips", type=int, default=1000, help="Starting chips")
    parser.add_argument("--blinds", type=str, default="10/20", help="Blinds (e.g. 10/20)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--no-equity", action="store_true", help="Hide equity from models")
    parser.add_argument("--output", type=str, default="", help="Output JSON path")
    args = parser.parse_args()

    if args.preset:
        players = []
        for name, model, kwargs in PRESETS[args.preset]:
            if model.startswith("lmstudio:"):
                kwargs = {"host": f"http://localhost:{args.port}/v1"}
            players.append((name, model, kwargs))
    elif args.models:
        players = []
        for m in args.models:
            name = m.split("/")[-1].split(":")[-1].replace(".", "")[:12]
            kwargs = {}
            if m.startswith("lmstudio:"):
                kwargs["host"] = f"http://localhost:{args.port}/v1"
            players.append((name, m, kwargs))
    else:
        console.print("[red]Specify --models or --preset[/red]")
        console.print("  python -m poker.cli --preset local --hands 5")
        console.print("  python -m poker.cli --models lmstudio:qwen/qwen3-1.7b claude-haiku-4-5")
        return

    sb, bb = (int(x) for x in args.blinds.split("/"))

    config = TableConfig(
        starting_chips=args.chips,
        small_blind=sb,
        big_blind=bb,
        num_hands=args.hands,
        seed=args.seed,
        show_equity=not args.no_equity,
    )

    engine, times = asyncio.run(run_tournament(players, config))

    output_data = {
        "tournament": {
            "hands": engine.hand_num,
            "seed": args.seed,
            "config": {
                "starting_chips": args.chips,
                "blinds": args.blinds,
            },
            "players": [
                {
                    "name": p.name,
                    "model": m,
                    "final_chips": p.chips,
                    "profit_loss": p.chips - args.chips,
                    "hands_won": p.hands_won,
                    "hands_played": p.hands_played,
                    "folds": p.total_folds,
                    "raises": p.total_raises,
                    "calls": p.total_calls,
                    "checks": p.total_checks,
                    "avg_time": round(times.get(p.name, 0) / max(p.hands_played, 1), 2),
                }
                for p, m in zip(
                    engine.players,
                    [mid for _, mid, _ in players],
                )
            ],
        }
    }

    if args.output:
        path = Path(args.output)
    else:
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        path = Path(f"results/poker-{ts}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output_data, indent=2))
    console.print(f"\n[green]Results saved:[/green] {path}")


if __name__ == "__main__":
    main()
