"""ArenaGame — HiveGame wrapper around run_arena."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from arena.game import run_arena
from base import GameResult, HiveGame, PlayerResult


class ArenaGame(HiveGame):
    """10-round economic decision game as a HiveGame."""

    @property
    def name(self) -> str:
        return "Economic Arena"

    @property
    def min_players(self) -> int:
        return 1

    @property
    def max_players(self) -> int:
        return 10

    async def setup(
        self,
        player_configs: list[tuple[str, str, dict[str, Any]]],
        seed: int | None = None,
        personas: dict[str, Any] | None = None,
        enable_suffering: bool = False,
        notepad: Any | None = None,
        a2a_store: Any | None = None,
        memory_dir: Path | None = None,
    ) -> None:
        """Configure the arena game.

        Note: enable_suffering, notepad, a2a_store, and memory_dir are
        accepted for HiveGame interface compatibility but not yet
        wired into the arena game logic.
        """
        self._player_configs = player_configs
        self._seed = seed
        self._personas = personas

    async def play(self) -> GameResult:
        players = await run_arena(
            self._player_configs,
            seed=self._seed,
            personas=self._personas,
        )

        results = []
        ranked = sorted(players, key=lambda p: p.money, reverse=True)
        for p in ranked:
            results.append(PlayerResult(
                name=p.name,
                model_id=p.model_id,
                final_score=p.money,
                metrics={
                    "happiness": p.happiness,
                    "rounds": len(p.history),
                    "avg_time": p.total_time / max(len(p.history), 1),
                },
            ))

        winners = [ranked[0].name] if ranked else []
        return GameResult(
            game_name=self.name,
            winners=winners,
            players=results,
            rounds_played=len(players[0].history) if players else 0,
        )
