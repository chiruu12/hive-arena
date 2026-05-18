"""Poker CLI — run an LLM poker tournament."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from poker.game import console, print_tournament_results, run_tournament


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Poker Tournament")
    parser.add_argument(
        "--models",
        nargs="+",
        help="Model IDs (e.g. lmstudio:qwen/qwen3-1.7b claude-haiku-4-5)",
    )
    parser.add_argument("--port", type=int, default=1234, help="LM Studio port")
    parser.add_argument("--hands", type=int, default=10, help="Number of hands to play")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--output", type=str, default="", help="Save results to JSON")
    args = parser.parse_args()

    if not args.models:
        console.print("[red]Specify --models[/red]")
        console.print(
            "  python -m poker.cli "
            "--models lmstudio:qwen/qwen3-1.7b lmstudio:liquid/lfm2.5-1.2b claude-haiku-4-5"
        )
        return

    players = []
    for m in args.models:
        name = m.split("/")[-1].split(":")[-1].replace(".", "")[:12]
        kwargs = {}
        if m.startswith("lmstudio:"):
            kwargs["host"] = f"http://localhost:{args.port}/v1"
        players.append((name, m, kwargs))

    results = asyncio.run(run_tournament(players, num_hands=args.hands, seed=args.seed))
    print_tournament_results(results)

    output_data = {
        "tournament": {
            "hands": args.hands,
            "seed": args.seed,
            "players": [
                {
                    "name": p.name,
                    "model": p.model_id,
                    "final_chips": p.chips,
                    "hands_won": p.hands_won,
                    "hands_played": p.hands_played,
                    "folds": p.folds,
                    "raises": p.raises,
                    "total_time": round(p.total_time, 2),
                }
                for p in results
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
