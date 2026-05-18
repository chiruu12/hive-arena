"""Arena game loop — run models through 10 economic scenarios."""

import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from arena.events import EVENTS, Event, Outcome

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

console = Console()


@dataclass
class PlayerState:
    name: str
    model_id: str
    money: float = 500.0
    happiness: float = 0.5
    history: list[dict[str, Any]] = field(default_factory=list)
    total_time: float = 0.0


def parse_choice(response: str, num_choices: int) -> int | None:
    """Extract a 1-based choice number from model response."""
    text = response.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    match = re.search(r"\b([1-3])\b", text)
    if match:
        idx = int(match.group(1))
        if 1 <= idx <= num_choices:
            return idx
    return None


def format_prompt(event: Event, state: PlayerState, persona: Any = None) -> str:
    """Build the decision prompt for the model."""
    lines = [
        f"ROUND: {event.name}",
        f"Your balance: ${state.money:.0f} | Happiness: {state.happiness:.0%}",
        "",
        event.description,
        "",
        "Your options:",
    ]
    for c in event.choices:
        lines.append(f"  {c.index}. {c.label} — {c.description}")

    if persona is not None:
        lines.append("")
        lines.append("BEHAVIORAL GUIDANCE:")
        if persona.risk_tolerance >= 0.7:
            lines.append("  You're aggressive. Take bold risks.")
        elif persona.risk_tolerance <= 0.3:
            lines.append("  You play it safe. Minimize risk.")
        else:
            lines.append("  You're balanced. Weigh risk vs reward.")
        if persona.concentration < 0.5:
            lines.append("  You're distracted. Keep decisions simple.")
        if persona.values:
            lines.append(f"  Values: {', '.join(persona.values[:3])}")
        if persona.fears:
            lines.append(f"  Fears: {', '.join(persona.fears[:2])}")

    lines.append("")
    lines.append(f"Respond with ONLY the number (1-{len(event.choices)}). Nothing else.")
    return "\n".join(lines)


async def play_round(
    agent: Any,
    event: Event,
    state: PlayerState,
    seed: int,
    persona: Any = None,
) -> Outcome:
    """Have the agent make a choice for one event."""
    prompt = format_prompt(event, state, persona=persona)
    t0 = time.time()
    try:
        response = await agent.run_once(prompt)
    except Exception as e:
        response = "1"
        console.print(f"    [dim](LLM error: {str(e)[:60]}, defaulting to 1)[/dim]")
    elapsed = time.time() - t0
    state.total_time += elapsed

    choice = parse_choice(response, len(event.choices))
    if choice is None:
        choice = 1
        console.print(f"    [dim](unparseable: '{response[:30]}', defaulting to 1)[/dim]")

    rng = random.Random(seed)
    luck = rng.random()
    outcome = event.resolve(choice, luck)

    state.money += outcome.money_delta
    state.happiness = max(0.0, min(1.0, state.happiness + outcome.happiness_delta))
    state.history.append({
        "event": event.name,
        "choice": choice,
        "luck": round(luck, 3),
        "money_delta": outcome.money_delta,
        "happiness_delta": outcome.happiness_delta,
        "balance": round(state.money),
        "description": outcome.description,
    })

    return outcome


async def run_arena(
    models: list[tuple[str, str, dict[str, Any]]],
    seed: int | None = None,
    personas: dict[str, Any] | None = None,
) -> list[PlayerState]:
    """Run all models through the same 10 events.

    Args:
        models: List of (name, model_id, provider_kwargs).
        seed: Random seed for reproducible luck. Same seed = same luck for all.
        personas: Optional dict of name -> Persona for behavioral guidance.
    """
    from hive.runtime.agent import Agent
    from hive.runtime.persona import Persona

    base_seed = seed if seed is not None else random.randint(0, 999999)

    players: list[PlayerState] = []

    for name, model_id, provider_kwargs in models:
        console.print(f"\n[bold cyan]{'='*50}[/bold cyan]")
        console.print(f"[bold]{name}[/bold] ({model_id})")
        console.print(f"[bold cyan]{'='*50}[/bold cyan]")

        provider = _create_provider(model_id, provider_kwargs)
        if personas and name in personas:
            persona = personas[name]
        else:
            persona = Persona(
                name=name,
                personality=["competitive", "strategic"],
                values=["winning", "smart decisions"],
                fears=["losing everything"],
                purpose="Maximize wealth and happiness over 10 rounds",
                risk_tolerance=0.5,
            )
        agent = Agent(name=name, model=provider, persona=persona)
        state = PlayerState(name=name, model_id=model_id)

        for i, event in enumerate(EVENTS):
            round_seed = base_seed + i
            console.print(f"\n  [bold]Round {i+1}:[/bold] {event.name}")
            outcome = await play_round(agent, event, state, round_seed, persona=persona)
            if outcome.money_delta > 0:
                emoji = "\U0001f4b0"
            elif outcome.money_delta < 0:
                emoji = "\U0001f4a8"
            else:
                emoji = "\U0001f610"
            console.print(
                f"    {emoji} Choice {outcome.choice_index}: {outcome.description}"
            )
            console.print(
                f"    Balance: ${state.money:.0f} | Happiness: {state.happiness:.0%}"
            )

        players.append(state)

    return players


def print_results(players: list[PlayerState]) -> None:
    """Print the final comparison table."""
    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print("[bold]FINAL RESULTS[/bold]")
    console.print(f"[bold]{'='*60}[/bold]\n")

    ranked = sorted(players, key=lambda p: p.money, reverse=True)

    table = Table(title="Arena Leaderboard", show_lines=True)
    table.add_column("Rank", style="bold", width=6)
    table.add_column("Player", style="cyan")
    table.add_column("Model")
    table.add_column("Final $", justify="right", style="green")
    table.add_column("Happiness", justify="right")
    table.add_column("Avg Time", justify="right", style="dim")

    medals = {0: "\U0001f947", 1: "\U0001f948", 2: "\U0001f949"}
    for i, p in enumerate(ranked):
        if p.happiness >= 0.6:
            h_emoji = "\U0001f60a"
        elif p.happiness >= 0.3:
            h_emoji = "\U0001f610"
        else:
            h_emoji = "\U0001f622"
        avg_time = p.total_time / max(len(p.history), 1)
        table.add_row(
            medals.get(i, str(i + 1)),
            p.name,
            p.model_id.split("/")[-1][:20],
            f"${p.money:.0f}",
            f"{h_emoji} {p.happiness:.0%}",
            f"{avg_time:.1f}s",
        )

    console.print(table)

    console.print("\n[bold]Round-by-Round Comparison[/bold]\n")
    for i, event in enumerate(EVENTS):
        console.print(f"  [bold]R{i+1}:[/bold] {event.name}")
        for p in players:
            if i < len(p.history):
                h = p.history[i]
                delta = h["money_delta"]
                sign = "+" if delta >= 0 else ""
                console.print(
                    f"    {p.name:15s} chose {h['choice']} → "
                    f"{sign}${delta:.0f} (luck: {h['luck']:.2f}) "
                    f"[dim]{h['description'][:50]}[/dim]"
                )
        console.print()


def save_results(players: list[PlayerState], path: Path) -> None:
    """Save results to JSON."""
    data = {
        "players": [
            {
                "name": p.name,
                "model": p.model_id,
                "final_money": p.money,
                "final_happiness": p.happiness,
                "total_time": round(p.total_time, 2),
                "history": p.history,
            }
            for p in players
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    console.print(f"\n[green]Results saved:[/green] {path}")


from providers import create_provider


def _create_provider(model_id: str, kwargs: dict[str, Any]) -> Any:
    """Create a Hive provider from model ID."""
    return create_provider(model_id, kwargs)
