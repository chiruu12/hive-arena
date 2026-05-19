"""CLI for Prisoner's Dilemma."""

import argparse
import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from dilemma.display import console
from dilemma.game import PrisonersDilemma


def main() -> None:
    parser = argparse.ArgumentParser(description="Prisoner's Dilemma — LLM Edition")
    parser.add_argument("--models", nargs=2, required=True, help="Two model IDs")
    parser.add_argument("--rounds", type=int, default=20, help="Number of rounds")
    parser.add_argument("--port", type=int, default=1234, help="LM Studio port")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--dramatic", action="store_true")
    parser.add_argument("--suffering", action="store_true")
    args = parser.parse_args()

    players = []
    for m in args.models:
        name = m.split("/")[-1].split(":")[-1].replace(".", "")[:12]
        kwargs = {}
        if m.startswith("lmstudio:"):
            kwargs["host"] = f"http://localhost:{args.port}/v1"
        players.append((name, m, kwargs))

    personas = None
    if args.dramatic:
        from hive.agents.profile import AgentProfile
        from hive.runtime.persona import Persona

        profiles_dir = Path(__file__).resolve().parent.parent.parent / "profiles"
        dramatic = ["gambler", "philosopher"]
        personas = {}
        for i, (name, _, _) in enumerate(players):
            pname = dramatic[i] if i < len(dramatic) else "coder"
            path = profiles_dir / f"{pname}.yaml"
            if path.exists():
                profile = AgentProfile.from_yaml(path)
                p = Persona.from_profile(profile)
                p.name = name
                personas[name] = p

    console.print(
        f"\n[bold]Prisoner's Dilemma[/bold] — "
        f"{players[0][0]} vs {players[1][0]}, {args.rounds} rounds\n"
    )

    game = PrisonersDilemma()

    async def _run():
        await game.setup(
            players,
            seed=args.seed,
            personas=personas,
            enable_suffering=args.suffering,
            num_rounds=args.rounds,
        )
        return await game.play()

    result = asyncio.run(_run())
    console.print(f"\n[bold green]Winner: {result.winners[0]}[/bold green]")


if __name__ == "__main__":
    main()
