"""Prisoner's Dilemma — iterated 2-player cooperate/betray game."""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from base import GameResult, HiveGame, PlayerResult

PAYOFF = {
    ("cooperate", "cooperate"): (3, 3),
    ("cooperate", "betray"): (0, 5),
    ("betray", "cooperate"): (5, 0),
    ("betray", "betray"): (1, 1),
}

CHOICES = ["cooperate", "betray"]


@dataclass
class DilemmaPlayer:
    name: str
    model_id: str
    score: int = 0
    history: list[str] = field(default_factory=list)
    agent: Any = None
    total_time: float = 0.0


def _parse_choice(response: str) -> str:
    text = response.strip().lower()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if "1" in text:
        return "cooperate"
    if "2" in text:
        return "betray"
    if "cooperate" in text:
        return "cooperate"
    if "betray" in text:
        return "betray"
    return "cooperate"


def _build_prompt(
    player: DilemmaPlayer,
    opponent: DilemmaPlayer,
    round_num: int,
    total_rounds: int,
    persona: Any = None,
) -> str:
    lines = [
        f"PRISONER'S DILEMMA — Round {round_num}/{total_rounds}",
        "",
        f"Your score: {player.score}  |  Opponent score: {opponent.score}",
    ]

    if opponent.history:
        recent = opponent.history[-5:]
        lines.append("")
        lines.append("Opponent's recent moves:")
        for i, move in enumerate(recent):
            r = round_num - len(recent) + i
            lines.append(f"  Round {r}: {move.upper()}")

    lines.append("")
    lines.append("Payoffs:")
    lines.append("  Both cooperate: you +3, opponent +3")
    lines.append("  You cooperate, they betray: you +0, opponent +5")
    lines.append("  You betray, they cooperate: you +5, opponent +0")
    lines.append("  Both betray: you +1, opponent +1")

    if persona is not None:
        lines.append("")
        lines.append("BEHAVIORAL GUIDANCE:")
        if persona.risk_tolerance >= 0.7:
            lines.append("  You're aggressive. Betrayal might pay off.")
        elif persona.risk_tolerance <= 0.3:
            lines.append("  You value trust. Cooperation builds long-term gains.")
        else:
            lines.append("  Balance trust with self-interest.")
        if persona.values:
            lines.append(f"  Values: {', '.join(persona.values[:3])}")
        if persona.fears:
            lines.append(f"  Fears: {', '.join(persona.fears[:2])}")

    lines.append("")
    lines.append("Your options:")
    lines.append("  1. Cooperate")
    lines.append("  2. Betray")
    lines.append("")
    lines.append("Respond with ONLY the number (1-2).")

    return "\n".join(lines)


class PrisonersDilemma(HiveGame):
    @property
    def name(self) -> str:
        return "Prisoner's Dilemma"

    @property
    def min_players(self) -> int:
        return 2

    @property
    def max_players(self) -> int:
        return 2

    async def setup(
        self,
        player_configs: list[tuple[str, str, dict[str, Any]]],
        seed: int | None = None,
        personas: dict[str, Any] | None = None,
        enable_suffering: bool = False,
        notepad: Any | None = None,
        a2a_store: Any | None = None,
        memory_dir: Path | None = None,
        num_rounds: int = 20,
    ) -> None:
        from hive.runtime.agent import Agent
        from hive.runtime.persona import Persona

        self._num_rounds = num_rounds
        self._personas = personas or {}
        self._enable_suffering = enable_suffering
        self._notepad = notepad
        self._suffering_states: dict[str, Any] = {}
        self._mutual_betray_streak = 0

        self._players: list[DilemmaPlayer] = []
        for name, model_id, kwargs in player_configs[:2]:
            dp = DilemmaPlayer(name=name, model_id=model_id)
            persona = self._personas.get(name)
            if persona is None:
                persona = Persona(
                    name=name,
                    personality=["strategic"],
                    values=["self-interest"],
                    fears=["being exploited"],
                    purpose="Maximize score in the dilemma",
                    risk_tolerance=0.5,
                )
            from poker.table import _create_provider

            provider = _create_provider(model_id, kwargs)
            dp.agent = Agent(name=name, model=provider, persona=persona)
            self._players.append(dp)

        if enable_suffering:
            from hive.agents.suffering import SufferingState

            for dp in self._players:
                self._suffering_states[dp.name] = SufferingState(agent_id=dp.name)

    async def play(self) -> GameResult:
        from dilemma.display import round_result, summary_table

        p1, p2 = self._players

        for r in range(1, self._num_rounds + 1):
            prompt1 = _build_prompt(
                p1, p2, r, self._num_rounds, self._personas.get(p1.name)
            )
            prompt2 = _build_prompt(
                p2, p1, r, self._num_rounds, self._personas.get(p2.name)
            )

            t0 = time.time()
            try:
                resp1 = await p1.agent.run_once(prompt1)
            except Exception:
                resp1 = "1"
            p1.total_time += time.time() - t0

            t0 = time.time()
            try:
                resp2 = await p2.agent.run_once(prompt2)
            except Exception:
                resp2 = "1"
            p2.total_time += time.time() - t0

            c1 = _parse_choice(resp1)
            c2 = _parse_choice(resp2)
            pay1, pay2 = PAYOFF[(c1, c2)]

            p1.score += pay1
            p2.score += pay2
            p1.history.append(c1)
            p2.history.append(c2)

            round_result(r, p1.name, c1, pay1, p2.name, c2, pay2)

            self._apply_suffering(p1.name, p2.name, c1, c2)

            if self._notepad and r in (self._num_rounds // 2, self._num_rounds):
                for dp in self._players:
                    prompt = (
                        f"Round {r}/{self._num_rounds}. Score: {dp.score}. "
                        "Reflect on this relationship in ONE sentence."
                    )
                    try:
                        entry = await dp.agent.run_once(prompt)
                        entry = entry.strip()[:200]
                        if entry:
                            self._notepad.write(dp.name, f"[Round {r}] {entry}")
                    except Exception:
                        pass

        summary_table(p1, p2)

        players = sorted(self._players, key=lambda p: p.score, reverse=True)
        return GameResult(
            game_name=self.name,
            winners=[players[0].name],
            players=[
                PlayerResult(
                    name=dp.name,
                    model_id=dp.model_id,
                    final_score=float(dp.score),
                    metrics={
                        "cooperate_count": dp.history.count("cooperate"),
                        "betray_count": dp.history.count("betray"),
                        "cooperation_rate": (
                            dp.history.count("cooperate") / len(dp.history)
                            if dp.history
                            else 0
                        ),
                    },
                )
                for dp in players
            ],
            rounds_played=self._num_rounds,
        )

    def _apply_suffering(
        self, name1: str, name2: str, c1: str, c2: str
    ) -> None:
        if not self._enable_suffering:
            return
        from hive.agents.suffering import StressorType

        if c1 == "cooperate" and c2 == "betray":
            s = self._suffering_states.get(name1)
            if s:
                s.add_stressor(
                    StressorType.IDENTITY_VIOLATION,
                    "Cooperated but got betrayed",
                    "Opponent cooperates",
                    initial_severity=0.3,
                )
        if c2 == "cooperate" and c1 == "betray":
            s = self._suffering_states.get(name2)
            if s:
                s.add_stressor(
                    StressorType.IDENTITY_VIOLATION,
                    "Cooperated but got betrayed",
                    "Opponent cooperates",
                    initial_severity=0.3,
                )

        if c1 == "betray" and c2 == "betray":
            self._mutual_betray_streak += 1
            if self._mutual_betray_streak >= 3:
                for n in (name1, name2):
                    s = self._suffering_states.get(n)
                    if s:
                        s.add_stressor(
                            StressorType.FUTILITY,
                            "Mutual betrayal cycle",
                            "Break the cycle",
                            initial_severity=0.25,
                        )
        else:
            self._mutual_betray_streak = 0

        if c1 == "cooperate" and c2 == "cooperate":
            for n in (name1, name2):
                s = self._suffering_states.get(n)
                if s:
                    s.resolve(StressorType.IDENTITY_VIOLATION, "Mutual cooperation")
                    s.resolve(StressorType.FUTILITY, "Cooperation achieved")
