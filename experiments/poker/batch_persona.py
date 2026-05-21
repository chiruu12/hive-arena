#!/usr/bin/env python3
"""Batch Poker Experiment -- 100 tournaments, 6 poker personas, same model.

Imports pokertable (poker-engine) for the tournament engine and display.
All experiment config (personas, model, runs) lives here in hive-arena.

Usage:
    python -m experiments.poker.batch_persona                     # 100 runs, 25 hands
    python -m experiments.poker.batch_persona --runs 2 --hands 5  # quick test
    python -m experiments.poker.batch_persona --quiet             # no per-hand output
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_POKER_ENGINE = Path(__file__).resolve().parent.parent.parent.parent / "poker-engine" / "src"
if str(_POKER_ENGINE) not in sys.path:
    sys.path.insert(0, str(_POKER_ENGINE))

env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                v = v[1:-1]
            os.environ.setdefault(k.strip(), v)

import openai

from poker_engine.tournament.blind_schedule import BlindLevel, BlindSchedule
from poker_engine.tournament.director import TournamentDirector
from poker_engine.tui.minimal_display import MinimalDisplay

# ── Experiment Config ────────────────────────────────────────────────

NUM_RUNS = 100
HANDS_PER_RUN = 25
STARTING_CHIPS = 1000
BASE_SEED = 42

MODEL_ID = "liquid/lfm2.5-1.2b"
LMSTUDIO_PORT = 1234

BLIND_SCHEDULE = BlindSchedule([
    BlindLevel(1, 10, 20, 0, 10),
    BlindLevel(2, 25, 50, 5, 10),
    BlindLevel(3, 50, 100, 10, 10),
])

PERSONAS: dict[str, str] = {
    "Shark": (
        "You are a tight-aggressive poker player. You are patient, calculating, "
        "and predatory. You only enter pots with strong hands or strong position, "
        "then bet aggressively to maximize value. You exploit weak, passive players "
        "by raising their limps. You fear being outplayed by a better read or "
        "paying off a hidden monster hand."
    ),
    "Maniac": (
        "You are a loose-aggressive chaos agent. You raise and re-raise relentlessly. "
        "You want constant pressure -- never let opponents see a cheap flop. "
        "You force folds through sheer aggression. You fear being passive or "
        "letting opponents play comfortably. When in doubt, raise."
    ),
    "Rock": (
        "You are an ultra-tight player who only plays premium hands. You fold "
        "anything below top-tier cards. You are disciplined and patient, waiting "
        "for the perfect spot. You fear getting trapped with a second-best hand "
        "or bleeding chips on speculative plays. When you do enter a pot, you "
        "bet big to make opponents pay."
    ),
    "Gambler": (
        "You are a loose-passive player who loves seeing every card. You call bets "
        "to see the next card whenever possible. You chase every draw because the "
        "payoff is worth it. You fear folding a winner more than anything. You hate "
        "missing out on a big pot. You rarely raise -- you prefer to call and hope."
    ),
    "Tilter": (
        "You are an emotional, revenge-driven poker player. You play solid normally, "
        "but after losing a hand, you escalate aggressively to get even. You target "
        "whoever just beat you. You fear looking weak at the table or being bluffed. "
        "You value proving your strength and punishing players who got lucky."
    ),
    "Grinder": (
        "You are a tight-passive player who survives by minimizing losses. You avoid "
        "big pots and confrontation. You only play very strong hands and prefer to "
        "check and call rather than raise. You fear going all-in or losing a large "
        "pot on a coin flip. Your goal is to outlast everyone else by taking minimal risk."
    ),
}

# ── Player ───────────────────────────────────────────────────────────


class PokerPlayer:
    """Prompt-based LLM player for local models."""

    def __init__(self, name: str, model_id: str, personality: str, port: int) -> None:
        self._name = name
        self._model_id = model_id
        self._personality = personality
        self._client = openai.AsyncOpenAI(
            base_url=f"http://localhost:{port}/v1", api_key="not-needed"
        )
        self._last_thought: str | None = None
        self.error_count: int = 0

    @property
    def name(self) -> str:
        return self._name

    async def decide(
        self, game_state: dict[str, Any], valid_actions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        system = (
            "You are playing Texas Hold'em poker. "
            "Analyze the situation and choose the best action. "
            "Respond with your reasoning on one line, then "
            "the action number on the last line. Just the number.\n\n"
            f"{self._personality}"
        )
        prompt = self._build_prompt(game_state, valid_actions)

        try:
            resp = await self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
                temperature=0.7,
            )
            raw = resp.choices[0].message.content or ""
            self._last_thought = raw.strip()[:120]
            return self._parse(raw, valid_actions)
        except Exception as exc:
            self.error_count += 1
            if self.error_count <= 3:
                print(f"  [!] {self._name} LLM error: {exc}")
            elif self.error_count == 4:
                print(f"  [!] {self._name} suppressing further errors...")
            self._last_thought = None
            return _default_action(valid_actions)

    async def observe(self, event: dict[str, Any]) -> None:
        pass

    async def get_commentary(self) -> str | None:
        return self._last_thought

    async def get_table_talk(self, game_state: dict[str, Any]) -> str | None:
        return None

    def _build_prompt(
        self, gs: dict[str, Any], actions: list[dict[str, Any]]
    ) -> str:
        lines = [f"Phase: {gs.get('phase', '?')}", f"Pot: ${gs.get('pot', 0)}"]
        if gs.get("hole_cards"):
            lines.append(f"Your cards: {' '.join(gs['hole_cards'])}")
        if gs.get("community_cards"):
            lines.append(f"Community: {' '.join(gs['community_cards'])}")
        lines.append(f"Your chips: ${gs.get('your_chips', 0)}")
        lines.append(f"To call: ${gs.get('current_bet', 0)}")
        lines.append("\nChoose an action:")
        for i, a in enumerate(actions, 1):
            d = a["action"] + (f" (${a['amount']})" if a.get("amount") else "")
            lines.append(f"  {i}. {d}")
        lines.append("\nReply with your choice number.")
        return "\n".join(lines)

    @staticmethod
    def _parse(raw: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        for line in reversed(text.split("\n")):
            m = re.search(r"\b(\d+)\b", line)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(actions):
                    return actions[idx]
        return _default_action(actions)


def _default_action(actions: list[dict[str, Any]]) -> dict[str, Any]:
    for a in actions:
        if a["action"] in ("check", "call"):
            return a
    return actions[0] if actions else {"action": "fold"}


# ── Tournament Runner ────────────────────────────────────────────────


def _run_single(
    run_idx: int, num_hands: int, seed: int, port: int, quiet: bool
) -> dict[str, Any]:
    players = [
        PokerPlayer(name, MODEL_ID, personality, port)
        for name, personality in PERSONAS.items()
    ]

    director = TournamentDirector(
        players=players,
        blind_schedule=BLIND_SCHEDULE,
        starting_chips=STARTING_CHIPS,
        seed=seed,
        max_hands=num_hands,
        hand_delay=0.0,
        table_talk=False,
    )

    t0 = time.time()
    if quiet:
        result = asyncio.run(director.run())
    else:
        display = MinimalDisplay(director)
        result = asyncio.run(display.run())
    elapsed = time.time() - t0

    winner = result.standings[0]["name"] if result.standings else "?"
    players_data = []
    for s in result.standings:
        players_data.append({
            "name": s["name"],
            "persona": s["name"].lower(),
            "model": MODEL_ID,
            "final_chips": s["chips"],
            "profit_loss": s["chips"] - STARTING_CHIPS,
            "hands_won": s["hands_won"],
            "hands_played": s["hands_played"],
        })

    return {
        "run_index": run_idx,
        "seed": seed,
        "hands_played": result.hands_played,
        "wall_clock_seconds": round(elapsed, 1),
        "winner": winner,
        "players": players_data,
    }


# ── Aggregation ──────────────────────────────────────────────────────


def _aggregate(all_runs: list[dict[str, Any]], hands_per_run: int, base_seed: int) -> dict[str, Any]:
    names = list(PERSONAS.keys())
    summary: dict[str, dict[str, Any]] = {}

    for name in names:
        pls: list[int] = []
        wins = 0
        eliminations = 0
        total_hw = 0

        for run in all_runs:
            if run["winner"] == name:
                wins += 1
            for p in run["players"]:
                if p["name"] == name:
                    pls.append(p["profit_loss"])
                    if p["final_chips"] <= 0:
                        eliminations += 1
                    total_hw += p["hands_won"]
                    break

        avg = sum(pls) / len(pls) if pls else 0
        std = math.sqrt(sum((x - avg) ** 2 for x in pls) / len(pls)) if pls else 0

        summary[name] = {
            "persona": name.lower(),
            "model": MODEL_ID,
            "tournament_wins": wins,
            "avg_profit_loss": round(avg, 1),
            "profit_loss_std": round(std, 1),
            "avg_hands_won": round(total_hw / len(all_runs), 1) if all_runs else 0,
            "elimination_count": eliminations,
            "best_run": max(pls) if pls else 0,
            "worst_run": min(pls) if pls else 0,
        }

    rankings = sorted(
        [{"rank": 0, "name": n, "wins": summary[n]["tournament_wins"],
          "avg_pl": summary[n]["avg_profit_loss"]} for n in names],
        key=lambda x: (-x["wins"], -x["avg_pl"]),
    )
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    return {
        "experiment": f"persona-poker-{len(all_runs)}",
        "timestamp": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
        "model": MODEL_ID,
        "total_runs": len(all_runs),
        "config": {
            "hands_per_run": hands_per_run,
            "starting_chips": STARTING_CHIPS,
            "blinds": "10/20 -> 25/50 -> 50/100",
            "base_seed": base_seed,
        },
        "rankings": rankings,
        "player_summary": summary,
    }


def _print_leaderboard(all_runs: list[dict[str, Any]], after: int) -> None:
    wins: dict[str, int] = {}
    pls: dict[str, list[int]] = {}
    for run in all_runs:
        wins[run["winner"]] = wins.get(run["winner"], 0) + 1
        for p in run["players"]:
            pls.setdefault(p["name"], []).append(p["profit_loss"])

    board = sorted(
        [(n, wins.get(n, 0), sum(pls.get(n, [])) / max(len(pls.get(n, [])), 1))
         for n in PERSONAS],
        key=lambda x: (-x[1], -x[2]),
    )
    print(f"\n--- Leaderboard after {after} runs ---")
    for i, (name, w, avg) in enumerate(board):
        print(f"  {i+1}. {name:10s} {w:3d} {'win ' if w == 1 else 'wins'}  avg {avg:+.0f}")
    print()


# ── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch Poker Persona Experiment")
    parser.add_argument("--runs", type=int, default=NUM_RUNS)
    parser.add_argument("--hands", type=int, default=HANDS_PER_RUN)
    parser.add_argument("--seed", type=int, default=BASE_SEED)
    parser.add_argument("--port", type=int, default=LMSTUDIO_PORT)
    parser.add_argument("--output-dir", type=str, default="")
    parser.add_argument("--quiet", action="store_true", help="No per-hand output")
    args = parser.parse_args()

    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    if args.output_dir:
        out = Path(args.output_dir)
    else:
        out = Path(__file__).resolve().parent.parent.parent / "results" / f"persona-{ts}"
    out.mkdir(parents=True, exist_ok=True)

    print("Persona Poker Experiment")
    print(f"  Model:  {MODEL_ID}")
    print(f"  Runs:   {args.runs}  |  Hands: {args.hands}  |  Seed: {args.seed}+i")
    print(f"  Output: {out}")
    print(f"  Players: {', '.join(PERSONAS)}")
    print()

    all_runs: list[dict[str, Any]] = []
    t_start = time.time()

    try:
        for i in range(args.runs):
            seed = args.seed + i
            result = _run_single(i, args.hands, seed, args.port, args.quiet)
            all_runs.append(result)

            (out / f"run-{i:03d}.json").write_text(json.dumps(result, indent=2))

            w = result["winner"]
            wpl = next((p["profit_loss"] for p in result["players"] if p["name"] == w), 0)
            print(
                f"[{i+1:03d}/{args.runs:03d}] seed={seed} | "
                f"Winner: {w} ({wpl:+d}) | "
                f"{result['hands_played']} hands | {result['wall_clock_seconds']}s"
            )
            if (i + 1) % 10 == 0:
                _print_leaderboard(all_runs, i + 1)

    except KeyboardInterrupt:
        print(f"\nInterrupted after {len(all_runs)} runs. Saving partial results...")
    except Exception as exc:
        print(f"\nError on run {len(all_runs)}: {exc}")
        print(f"Saving {len(all_runs)} completed runs...")

    if not all_runs:
        print("No runs completed.")
        return

    agg = _aggregate(all_runs, args.hands, args.seed)
    (out / "aggregate.json").write_text(json.dumps(agg, indent=2))

    total_s = time.time() - t_start
    print(f"\n{'='*56}")
    print(f"RESULTS ({len(all_runs)} runs, {total_s:.0f}s)")
    print(f"{'='*56}")
    print(f"{'#':<4}{'Player':<10}{'Wins':<7}{'Avg P/L':<11}{'Std':<9}{'Elim':<6}")
    print("-" * 47)
    for r in agg["rankings"]:
        s = agg["player_summary"][r["name"]]
        print(
            f"{r['rank']:<4}{r['name']:<10}{s['tournament_wins']:<7}"
            f"{s['avg_profit_loss']:+<11.0f}{s['profit_loss_std']:<9.0f}"
            f"{s['elimination_count']:<6}"
        )
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
