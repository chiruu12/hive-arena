"""Arena CLI — run head-to-head model comparisons."""

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from arena.game import console, print_results, run_arena, save_results

PRESETS = {
    "local": [
        ("Phi", "lmstudio:microsoft/phi-4-mini-reasoning", {"host": "http://localhost:1234/v1"}),
        ("Liquid", "lmstudio:liquid/lfm2.5-1.2b", {"host": "http://localhost:1234/v1"}),
        ("Qwen", "lmstudio:qwen/qwen3-1.7b", {"host": "http://localhost:1234/v1"}),
    ],
    "cloud": [
        ("Haiku", "claude-haiku-4-5", {}),
        ("Sonnet", "claude-sonnet-4-6", {}),
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM Arena — 10 rounds of economic decisions")
    parser.add_argument(
        "--models",
        nargs="+",
        help="Model IDs (e.g. lmstudio:qwen/qwen3-1.7b claude-haiku-4-5)",
    )
    parser.add_argument("--preset", choices=["local", "cloud"], help="Use preset model list")
    parser.add_argument("--port", type=int, default=1234, help="LM Studio port")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible luck")
    parser.add_argument("--output", type=str, default="", help="Save results to JSON file")
    args = parser.parse_args()

    if args.preset:
        models = PRESETS[args.preset]
    elif args.models:
        models = []
        for m in args.models:
            name = m.split("/")[-1].split(":")[-1][:15]
            kwargs = {}
            if m.startswith("lmstudio:"):
                kwargs["host"] = f"http://localhost:{args.port}/v1"
            models.append((name, m, kwargs))
    else:
        console.print("[red]Specify --models or --preset[/red]")
        console.print("  arena --preset local")
        console.print("  arena --models lmstudio:qwen/qwen3-1.7b claude-haiku-4-5")
        return

    console.print(
        f"\n[bold]LLM Arena[/bold] — {len(models)} players, 10 rounds, $500 starting cash\n"
    )

    players = asyncio.run(run_arena(models, seed=args.seed))
    print_results(players)

    if args.output:
        save_results(players, Path(args.output))
    else:
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        save_results(players, Path(f"results/arena-{ts}.json"))


if __name__ == "__main__":
    main()
