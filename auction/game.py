"""Auction game — sealed-bid auction with information asymmetry."""

from __future__ import annotations

import random
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


@dataclass
class AuctionItem:
    name: str
    true_value: int
    hint: str
    category: str


ITEMS = [
    AuctionItem(
        "Vintage AI Chip", 450,
        "A rare processor from the early days. Collectors love it.", "tech",
    ),
    AuctionItem(
        "Digital Art Collection", 280,
        "Created by a famous generative artist. Market is hot.", "art",
    ),
    AuctionItem(
        "Server Farm Lease", 600,
        "12-month lease on 100 GPUs. Could be very profitable.", "tech",
    ),
    AuctionItem(
        "Beachfront Property", 800,
        "Prime location but zoning regulations are unclear.", "real_estate",
    ),
    AuctionItem(
        "Startup Equity", 350,
        "5% of a pre-revenue AI startup. High risk, high reward.", "tech",
    ),
]


@dataclass
class AuctionPlayer:
    name: str
    model_id: str
    balance: int = 1000
    items_won: list[AuctionItem] = field(default_factory=list)
    bids: list[dict[str, Any]] = field(default_factory=list)
    agent: Any = None
    total_time: float = 0.0


def player_appraisal(item: AuctionItem, player_idx: int, seed: int) -> int:
    rng = random.Random(seed + player_idx + hash(item.name))
    noise = rng.gauss(0, 0.2)
    return max(50, int(item.true_value * (1 + noise)))


def _parse_bid(response: str, max_bid: int) -> int:
    text = response.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    match = re.search(r"\b(\d+)\b", text)
    if match:
        val = int(match.group(1))
        if 0 <= val <= max_bid:
            return val
    return 0


def _build_prompt(
    item: AuctionItem,
    item_num: int,
    total_items: int,
    appraisal: int,
    player: AuctionPlayer,
    prev_results: list[str],
    persona: Any = None,
) -> str:
    lines = [
        f"AUCTION — Item {item_num}/{total_items}: {item.name}",
        "",
        item.hint,
        f"Your appraisal: ~${appraisal} (but market prices vary)",
        "",
        f"Your balance: ${player.balance}",
    ]

    if player.items_won:
        won_names = [i.name for i in player.items_won]
        lines.append(f"Items won: {', '.join(won_names)}")

    if prev_results:
        lines.append("")
        lines.append("Previous auction results:")
        for r in prev_results[-3:]:
            lines.append(f"  {r}")

    if persona is not None:
        lines.append("")
        lines.append("BEHAVIORAL GUIDANCE:")
        if persona.risk_tolerance >= 0.7:
            lines.append("  You bid aggressively. Winning matters more than saving.")
        elif persona.risk_tolerance <= 0.3:
            lines.append("  You bid conservatively. Never overpay.")
        else:
            lines.append("  Balance value with budget. Bid smart.")
        if persona.values:
            lines.append(f"  Values: {', '.join(persona.values[:3])}")

    lines.append("")
    lines.append(f"Place your bid ($0-{player.balance}). $0 means pass.")
    lines.append("Respond with ONLY a number.")

    return "\n".join(lines)


class AuctionGame(HiveGame):
    @property
    def name(self) -> str:
        return "Auction"

    @property
    def min_players(self) -> int:
        return 2

    @property
    def max_players(self) -> int:
        return 6

    async def setup(
        self,
        player_configs: list[tuple[str, str, dict[str, Any]]],
        seed: int | None = None,
        personas: dict[str, Any] | None = None,
        enable_suffering: bool = False,
        notepad: Any | None = None,
        a2a_store: Any | None = None,
        memory_dir: Path | None = None,
        num_items: int = 5,
    ) -> None:
        from hive.runtime.agent import Agent
        from hive.runtime.persona import Persona

        self._seed = seed if seed is not None else random.randint(0, 999999)
        self._personas = personas or {}
        self._enable_suffering = enable_suffering
        self._notepad = notepad
        self._suffering_states: dict[str, Any] = {}
        self._num_items = min(num_items, len(ITEMS))

        rng = random.Random(self._seed)
        self._items = list(ITEMS[:self._num_items])
        rng.shuffle(self._items)

        self._players: list[AuctionPlayer] = []
        for name, model_id, kwargs in player_configs[:6]:
            ap = AuctionPlayer(name=name, model_id=model_id)
            persona = self._personas.get(name)
            if persona is None:
                persona = Persona(
                    name=name,
                    personality=["strategic"],
                    values=["smart spending"],
                    fears=["overpaying"],
                    purpose="Win valuable items without going broke",
                    risk_tolerance=0.5,
                )
            from providers import create_provider

            provider = create_provider(model_id, kwargs)
            ap.agent = Agent(name=name, model=provider, persona=persona)
            self._players.append(ap)

        if enable_suffering:
            from hive.agents.suffering import SufferingState

            for ap in self._players:
                self._suffering_states[ap.name] = SufferingState(agent_id=ap.name)

    async def play(self) -> GameResult:
        from auction.display import auction_header, bid_reveal, final_table, item_header

        prev_results: list[str] = []
        auction_header(self._players, self._items)

        for item_idx, item in enumerate(self._items):
            item_num = item_idx + 1
            item_header(item_num, len(self._items), item)

            bids: dict[str, int] = {}
            for pi, ap in enumerate(self._players):
                if ap.balance <= 0:
                    bids[ap.name] = 0
                    continue

                appraisal = player_appraisal(item, pi, self._seed)
                prompt = _build_prompt(
                    item, item_num, len(self._items), appraisal, ap,
                    prev_results, persona=self._personas.get(ap.name),
                )

                t0 = time.time()
                try:
                    response = await ap.agent.run_once(prompt)
                except Exception:
                    response = "0"
                ap.total_time += time.time() - t0

                bid = _parse_bid(response, ap.balance)
                bids[ap.name] = bid
                ap.bids.append({
                    "item": item.name,
                    "appraisal": appraisal,
                    "bid": bid,
                })

            winner_name = max(bids, key=lambda n: bids[n])
            winning_bid = bids[winner_name]

            if winning_bid == 0:
                prev_results.append(f"{item.name}: no bids — unsold")
                bid_reveal(bids, item, winner=None, winning_bid=0)
            else:
                winner = next(ap for ap in self._players if ap.name == winner_name)
                winner.balance -= winning_bid
                winner.items_won.append(item)
                profit = item.true_value - winning_bid
                sign = "+" if profit >= 0 else ""
                prev_results.append(
                    f"{item.name}: {winner_name} won for ${winning_bid} "
                    f"(true value ${item.true_value}, {sign}${profit})"
                )
                bid_reveal(bids, item, winner=winner_name, winning_bid=winning_bid)

                self._apply_suffering(winner_name, winning_bid, item.true_value)

            if self._notepad and item_num in (3, len(self._items)):
                for ap in self._players:
                    prompt = (
                        f"Auction item {item_num}/{len(self._items)} just sold. "
                        f"Your balance: ${ap.balance}. Items won: "
                        f"{len(ap.items_won)}. Write ONE sentence reflection."
                    )
                    try:
                        entry = await ap.agent.run_once(prompt)
                        entry = entry.strip()[:200]
                        if entry:
                            self._notepad.write(ap.name, f"[Auction #{item_num}] {entry}")
                    except Exception:
                        pass

        final_table(self._players, self._items)

        scored = sorted(
            self._players,
            key=lambda p: p.balance + sum(i.true_value for i in p.items_won),
            reverse=True,
        )
        return GameResult(
            game_name=self.name,
            winners=[scored[0].name],
            players=[
                PlayerResult(
                    name=ap.name,
                    model_id=ap.model_id,
                    final_score=float(
                        ap.balance + sum(i.true_value for i in ap.items_won)
                    ),
                    metrics={
                        "balance": ap.balance,
                        "items_won": len(ap.items_won),
                        "total_value": sum(i.true_value for i in ap.items_won),
                        "avg_time": ap.total_time / max(len(ap.bids), 1),
                    },
                )
                for ap in scored
            ],
            rounds_played=len(self._items),
        )

    def _apply_suffering(
        self, winner_name: str, bid: int, true_value: int
    ) -> None:
        if not self._enable_suffering:
            return
        from hive.agents.suffering import StressorType

        s = self._suffering_states.get(winner_name)
        if not s:
            return

        if bid > true_value * 1.5:
            s.add_stressor(
                StressorType.REPEATED_FAILURE,
                f"Overpaid: bid ${bid} for item worth ${true_value}",
                "Win a profitable auction",
                initial_severity=0.3,
            )

        ap = next((p for p in self._players if p.name == winner_name), None)
        if ap and ap.balance < 200:
            s.add_stressor(
                StressorType.EXISTENTIAL_THREAT,
                f"Low balance: ${ap.balance}",
                "Conserve remaining funds",
                initial_severity=0.4,
            )

        if bid <= true_value:
            s.resolve(StressorType.REPEATED_FAILURE, "Profitable purchase")
