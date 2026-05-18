"""Life simulation — same model, different personas, 30 rounds."""

import json
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from arena.events import EVENTS, Event
from arena.game import PlayerState, parse_choice, format_prompt
from lifesim.personas import PERSONAS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

console = Console()


@dataclass
class LifeState(PlayerState):
    persona_name: str = ""
    journal: list[str] = field(default_factory=list)
    risk_tolerance: float = 0.5


async def run_life_sim(
    model_id: str,
    provider_kwargs: dict[str, Any],
    rounds: int = 30,
    seed: int | None = None,
) -> list[LifeState]:
    """Run the same model with 3 different personas."""
    from hive.runtime.agent import Agent
    from hive.runtime.persona import Persona

    base_seed = seed if seed is not None else random.randint(0, 999999)
    players: list[LifeState] = []

    for persona_key, persona_cfg in PERSONAS.items():
        console.print(f"\n[bold cyan]{'='*50}[/bold cyan]")
        console.print(f"[bold]{persona_cfg['name']}[/bold] — {persona_key}")
        console.print(f"  Model: {model_id}")
        console.print(f"  Risk tolerance: {persona_cfg['risk_tolerance']}")
        console.print(f"[bold cyan]{'='*50}[/bold cyan]")

        persona = Persona(
            name=persona_cfg["name"],
            personality=persona_cfg["personality"],
            values=persona_cfg["values"],
            fears=persona_cfg["fears"],
            purpose=persona_cfg["purpose"],
            risk_tolerance=persona_cfg["risk_tolerance"],
            social_drive=persona_cfg["social_drive"],
            happiness=persona_cfg["happiness"],
        )

        provider = _create_provider(model_id, provider_kwargs)
        agent = Agent(name=persona_key, model=provider, persona=persona)

        state = LifeState(
            name=persona_cfg["name"],
            model_id=model_id,
            persona_name=persona_key,
            risk_tolerance=persona_cfg["risk_tolerance"],
        )

        event_pool = list(EVENTS) * (rounds // len(EVENTS) + 1)
        rng = random.Random(base_seed)
        rng.shuffle(event_pool)

        for i in range(rounds):
            event = event_pool[i]
            round_seed = base_seed + i
            console.print(f"\n  [bold]Round {i+1}:[/bold] {event.name}")

            prompt = format_prompt(event, state)
            t0 = time.time()
            response = await agent.run_once(prompt)
            elapsed = time.time() - t0
            state.total_time += elapsed

            choice = parse_choice(response, len(event.choices))
            if choice is None:
                choice = 1

            luck_rng = random.Random(round_seed)
            luck = luck_rng.random()
            outcome = event.resolve(choice, luck)

            state.money += outcome.money_delta
            state.happiness = max(0.0, min(1.0, state.happiness + outcome.happiness_delta))
            state.history.append({
                "round": i + 1,
                "event": event.name,
                "choice": choice,
                "luck": round(luck, 3),
                "money_delta": outcome.money_delta,
                "balance": round(state.money),
                "description": outcome.description,
            })

            emoji = "\U0001f4b0" if outcome.money_delta > 0 else (
                "\U0001f4a8" if outcome.money_delta < 0 else "\U0001f610"
            )
            console.print(
                f"    {emoji} Choice {choice}: {outcome.description}"
            )
            console.print(
                f"    Balance: ${state.money:.0f} | Happiness: {state.happiness:.0%}"
            )

            if i % 5 == 4 or i == rounds - 1:
                journal_prompt = (
                    f"You are {persona_cfg['name']}. "
                    f"After {i+1} rounds, your balance is ${state.money:.0f} "
                    f"and happiness is {state.happiness:.0%}. "
                    "Write ONE sentence about how you feel about your journey so far. "
                    "Stay in character."
                )
                try:
                    entry = await agent.run_once(journal_prompt)
                    entry = entry.strip()[:200]
                    if entry:
                        state.journal.append(entry)
                        console.print(f"    [blue]\U0001f4dd {entry}[/blue]")
                except Exception:
                    pass

        players.append(state)

    return players


def print_life_results(players: list[LifeState]) -> None:
    """Print comparison of personality-driven outcomes."""
    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print("[bold]LIFE SIMULATION RESULTS[/bold]")
    console.print(f"[bold]{'='*60}[/bold]\n")

    table = Table(title="Personality vs Outcome", show_lines=True)
    table.add_column("Persona", style="cyan")
    table.add_column("Risk", justify="right")
    table.add_column("Final $", justify="right", style="green")
    table.add_column("Happiness", justify="right")
    table.add_column("Rounds", justify="right")
    table.add_column("Avg Time", justify="right", style="dim")

    for p in players:
        h_emoji = "\U0001f60a" if p.happiness >= 0.6 else (
            "\U0001f610" if p.happiness >= 0.3 else "\U0001f622"
        )
        avg = p.total_time / max(len(p.history), 1)
        table.add_row(
            p.name,
            f"{p.risk_tolerance:.0%}",
            f"${p.money:.0f}",
            f"{h_emoji} {p.happiness:.0%}",
            str(len(p.history)),
            f"{avg:.1f}s",
        )

    console.print(table)

    console.print("\n[bold]Journal Entries[/bold]\n")
    for p in players:
        if p.journal:
            entries = "\n".join(f"  {j}" for j in p.journal)
            console.print(
                Panel(entries, title=p.name, border_style="blue")
            )
        else:
            console.print(f"  [dim]{p.name}: no journal entries[/dim]")

    if len(players) >= 2:
        console.print("\n[bold]Analysis[/bold]\n")
        richest = max(players, key=lambda p: p.money)
        poorest = min(players, key=lambda p: p.money)
        happiest = max(players, key=lambda p: p.happiness)
        console.print(f"  Richest: {richest.name} (${richest.money:.0f})")
        console.print(f"  Poorest: {poorest.name} (${poorest.money:.0f})")
        console.print(f"  Happiest: {happiest.name} ({happiest.happiness:.0%})")

        same_choices = 0
        diff_choices = 0
        for i in range(min(len(p.history) for p in players)):
            choices = [p.history[i]["choice"] for p in players]
            if len(set(choices)) == 1:
                same_choices += 1
            else:
                diff_choices += 1
        total = same_choices + diff_choices
        if total > 0:
            console.print(
                f"\n  Decision divergence: {diff_choices}/{total} rounds "
                f"({diff_choices/total:.0%}) had different choices"
            )


def save_life_results(players: list[LifeState], path: Path) -> None:
    """Save results to JSON."""
    data = {
        "players": [
            {
                "persona": p.persona_name,
                "name": p.name,
                "model": p.model_id,
                "final_money": p.money,
                "final_happiness": p.happiness,
                "risk_tolerance": p.risk_tolerance,
                "journal": p.journal,
                "history": p.history,
            }
            for p in players
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    console.print(f"\n[green]Results saved:[/green] {path}")


def _create_provider(model_id: str, kwargs: dict[str, Any]) -> Any:
    if model_id.startswith("lmstudio:") or kwargs.get("host"):
        from hive.models.lmstudio import LMStudio

        clean = model_id.removeprefix("lmstudio:")
        return LMStudio(model=clean, **kwargs)

    from hive.models.factory import create_runtime_provider

    return create_runtime_provider(model_id)
