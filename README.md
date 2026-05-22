# Hive Arena

Head-to-head LLM economic games and personality-driven life simulations.
Built on [Hive](https://github.com/chiruu12/Hive).

## Featured: Persona Poker Experiment

**Same model. Same cards. 6 different personalities. 100 poker tournaments.**

We gave the same 1.2B model (Liquid LFM-2.5, running locally via LM Studio) 6 classic poker personality prompts and ran 100 Texas Hold'em tournaments (25 hands each). The personality paragraph in the system prompt is the only variable.

### Results

| # | Persona | Style | Wins | Avg P/L | Eliminated | Avg Place |
|---|---------|-------|------|---------|------------|-----------|
| 1 | **Shark** | tight-aggressive | 45 | +$1,157 | 32% | 2.3 |
| 2 | **Maniac** | loose-aggressive | 24 | +$395 | 50% | 3.0 |
| 3 | **Gambler** | loose-passive | 21 | +$301 | 51% | 3.6 |
| 4 | **Tilter** | emotional | 10 | -$435 | 80% | 5.1 |
| 5 | **Grinder** | tight-passive | 0 | -$508 | 0% | 2.7 |
| 6 | **Rock** | ultra-tight | 0 | -$909 | 63% | 4.3 |

### Key Findings

- **Personality prompts create real behavioral differences.** A paragraph of text created a 45:0 win differential on the same model.
- **The Grinder Paradox:** 0 wins but 0 eliminations -- survived every tournament, always placed 2nd-3rd, but never accumulated enough to win.
- **Selective aggression beats blind aggression.** Shark (45 wins) vs Maniac (24 wins). Both aggressive, but Shark picks its spots.
- **Folding is more expensive than calling.** Rock (fold everything) was eliminated 63% of the time. Grinder (check/call everything) was eliminated 0%.
- **Passive play never wins.** Neither Grinder nor Rock won a single tournament in 100 runs.

### Reproduce It

```bash
cd experiments/poker
python batch_persona.py --runs 100 --hands 25 --model lmstudio:liquid/lfm2.5-1.2b
```

Persona profiles are in [`experiments/poker/profiles/`](experiments/poker/profiles/).

### Methodology

- Model: Liquid LFM-2.5 (1.2B params), local via LM Studio
- 100 tournaments, 25 hands each, random shuffles (no fixed seed)
- Blind schedule: 10/20 → 25/50 → 50/100, starting stack $1,000
- Each player receives: hole cards, community cards, pot size, chip counts, valid actions
- The ONLY difference between players is the personality paragraph in the system prompt
- Total runtime: ~12.7 hours on a 16GB Mac

---

## What's Inside

### Arena — 10-Round Economic Game

3 models. Same 10 scenarios. Same luck dice. Who makes the best decisions?

Each round presents a forced choice (invest/gamble/hire/save), luck determines the outcome magnitude, and the model's decisions compound across rounds.

```bash
# Run with local models (LM Studio)
python -m arena.cli --models lmstudio:qwen/qwen3-1.7b lmstudio:liquid/lfm2.5-1.2b

# Run with cloud models
python -m arena.cli --models claude-haiku-4-5 claude-sonnet-4-6

# Reproducible runs (same luck for all players)
python -m arena.cli --preset local --seed 42
```

### Life Sim — Personality Injection Test

1 model. 3 personalities. 30 rounds. Does the persona actually matter?

The Gambler (risk_tolerance=0.85), the Philosopher (risk_tolerance=0.2), and the Coder (risk_tolerance=0.4) face the same events with the same luck. The only variable is the Hive Persona prompt.

```bash
# Run with local model
python -m lifesim.cli --model lmstudio:qwen/qwen3-1.7b --rounds 30

# Run with cloud model
python -m lifesim.cli --model claude-haiku-4-5 --rounds 30

# Reproducible
python -m lifesim.cli --model lmstudio:qwen/qwen3-1.7b --seed 42
```

### Poker - LLM Texas Hold'em Tournament

Full poker engine with hand evaluation, equity calculator, and Rich TUI.

```bash
# Local models (LM Studio)
python -m poker.cli --preset local --hands 25

# With dramatic personas (gambler, philosopher, coder)
python -m poker.cli --preset local --dramatic

# Cloud models
python -m poker.cli --preset cloud --hands 25
```

See [tournaments/results/](tournaments/results/) for data from 5 complete runs.

## Setup

```bash
pip install hive-agent rich pyyaml
# Start LM Studio with a model loaded on port 1234
```

## How It Works

- Uses Hive's `Agent`, `Persona`, and `run_once()` for each decision
- Events are deterministic — luck is seeded so every player gets the same randomness
- Models just pick a number (1, 2, or 3) — no complex JSON parsing needed
- Journal entries every 5 rounds capture how the model "feels" about its journey
- Results saved to JSON for comparison

## The Events

| Round | Scenario | Choices |
|-------|----------|---------|
| 1 | Investment Opportunity | Pass / $100 / $300 |
| 2 | Job Offer | Stay / Switch / Freelance |
| 3 | Casino Night | Walk away / Small bet / All in |
| 4 | Skill Workshop | Skip / Basic ($50) / Premium ($200) |
| 5 | Friend Needs Money | Decline / Lend $100 / Give $50 |
| 6 | Health Scare | Ignore / Doctor ($200) / Home remedy |
| 7 | Rent Crisis | Negotiate / Move / Roommate |
| 8 | Unexpected Windfall | Save / Spend / Reinvest |
| 9 | Reputation Test | Stay quiet / Speak up / Deflect |
| 10 | Final Gambit | Lock in / Calculated risk / Moonshot |
