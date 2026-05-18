"""PokerGame — HiveGame wrapper around run_tournament."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from base import GameResult, HiveGame, PlayerResult
from poker.table import TableConfig, _opponent_style, run_tournament


class PokerGame(HiveGame):
    """Texas Hold'em poker tournament as a HiveGame."""

    @property
    def name(self) -> str:
        return "Texas Hold'em Poker"

    @property
    def min_players(self) -> int:
        return 2

    @property
    def max_players(self) -> int:
        return 8

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
        self._player_configs = player_configs
        self._config = TableConfig(seed=seed)
        self._personas = personas
        self._enable_suffering = enable_suffering
        self._notepad = notepad
        self._a2a_store = a2a_store
        self._memory_dir = memory_dir

    async def play(self) -> GameResult:
        engine, times = await run_tournament(
            self._player_configs,
            self._config,
            personas=self._personas,
            enable_suffering=self._enable_suffering,
            notepad=self._notepad,
            a2a_store=self._a2a_store,
            memory_dir=self._memory_dir,
        )

        players = []
        ranked = sorted(engine.players, key=lambda p: p.chips, reverse=True)
        for p in ranked:
            players.append(PlayerResult(
                name=p.name,
                model_id=next(
                    (mid for n, mid, _ in self._player_configs if n == p.name),
                    "unknown",
                ),
                final_score=float(p.chips),
                metrics={
                    "hands_played": p.hands_played,
                    "hands_won": p.hands_won,
                    "total_folds": p.total_folds,
                    "total_raises": p.total_raises,
                    "style": _opponent_style(p),
                    "avg_time": times.get(p.name, 0) / max(p.hands_played, 1),
                },
            ))

        winners = [ranked[0].name] if ranked else []
        return GameResult(
            game_name=self.name,
            winners=winners,
            players=players,
            rounds_played=engine.hand_num,
            metadata={"starting_chips": self._config.starting_chips},
        )
