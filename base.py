"""HiveGame protocol — abstract base for all arena games."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PlayerResult:
    """Per-player outcome from a game."""

    name: str
    model_id: str
    final_score: float
    metrics: dict[str, Any] = field(default_factory=dict)
    journal: list[str] = field(default_factory=list)


@dataclass
class GameResult:
    """Overall outcome from a game."""

    game_name: str
    winners: list[str]
    players: list[PlayerResult]
    rounds_played: int
    metadata: dict[str, Any] = field(default_factory=dict)


class HiveGame(ABC):
    """Abstract base class for all hive-arena games."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def min_players(self) -> int: ...

    @property
    @abstractmethod
    def max_players(self) -> int: ...

    @abstractmethod
    async def setup(
        self,
        player_configs: list[tuple[str, str, dict[str, Any]]],
        seed: int | None = None,
        personas: dict[str, Any] | None = None,
        enable_suffering: bool = False,
        notepad: Any | None = None,
        a2a_store: Any | None = None,
        memory_dir: Path | None = None,
    ) -> None: ...

    @abstractmethod
    async def play(self) -> GameResult: ...

    def integrate_suffering(
        self,
        player_name: str,
        event_type: str,
        outcome: str,
    ) -> None:
        """Hook for suffering integration. Override in subclasses."""
