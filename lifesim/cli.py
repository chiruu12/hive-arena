"""Life Sim CLI — same model, different personalities."""

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from lifesim.sim import console, print_life_results, run_life_sim, save_life_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Life Sim — one model, 3 personalities, who thrives?"
    )
    parser.add_argument(
        "--model",
        default="lmstudio:qwen/qwen3-1.7b",
        help="Model to test (default: lmstudio:qwen/qwen3-1.7b)",
    )
    parser.add_argument("--port", type=int, default=1234, help="LM Studio port")
    parser.add_argument("--rounds", type=int, default=30, help="Rounds per persona")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--output", type=str, default="", help="Save results to JSON")
    args = parser.parse_args()

    kwargs = {}
    if args.model.startswith("lmstudio:"):
        kwargs["host"] = f"http://localhost:{args.port}/v1"

    console.print(
        f"\n[bold]Life Simulation[/bold] — 1 model, 3 personas, {args.rounds} rounds each\n"
        f"  Model: {args.model}\n"
    )

    players = asyncio.run(
        run_life_sim(args.model, kwargs, rounds=args.rounds, seed=args.seed)
    )
    print_life_results(players)

    if args.output:
        save_life_results(players, Path(args.output))
    else:
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        save_life_results(players, Path(f"results/lifesim-{ts}.json"))


if __name__ == "__main__":
    main()
