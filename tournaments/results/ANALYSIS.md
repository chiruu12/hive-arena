# Million Dollar Poker Tournament — Results Analysis

## Setup
- **6 LLMs** playing Texas Hold'em against each other
- **$1,000,000** starting chips per player
- **25 hands** per tournament, 5K/10K blinds, 1K ante
- **Same persona** for all — model is the only variable
- **5 runs** total (2 with old code + Phi, 3 with new code + GPT-OSS)
- Built on [Hive Agent SDK](https://github.com/chiruu12/Hive)

## The Players

| Name | Model | Type | Size | Avg Speed |
|------|-------|------|------|-----------|
| Liquid | liquid/lfm2.5-1.2b | LOCAL | 1.2B | ~5s |
| Qwen | qwen/qwen3-1.7b | LOCAL | 1.7B | ~131s |
| GPT-OSS | gpt-oss-120b | CLOUD | 120B | ~16s |
| MiniMax | minimax-m2p7 | CLOUD | ~300B | ~34s |
| Haiku | claude-haiku-4-5 | CLOUD | ~600B | ~6s |
| Kimi | kimi-k2p6 | CLOUD | ~1T | ~55s |

## Overall Standings (5 runs)

| Rank | Player | Wins | Avg Place | Hands Won | Style | Notes |
|------|--------|------|-----------|-----------|-------|-------|
| 1 | **Liquid** | **2** | **1.6** | 19 | Aggressive (53R, 9F) | Fastest + winningest |
| 2 | Qwen | 1 | 2.2 | 21 | Aggressive (53R, 9F) | Most hands won overall |
| 3 | MiniMax | 1 | 4.4 | 17 | Mixed (55R, 35F) | Raises a lot but folds a lot too |
| 4 | Kimi | 1 | 5.0 | 9 | Passive (31R, 27F) | Won Run 4 decisively |
| 5 | GPT-OSS | 0 | 3.3 | 2 | Tight-passive (11R, 17F) | 120B params, 0 wins |
| 6 | Haiku | 0 | 4.4 | 9 | Tight (35R, 28F) | Smartest model, worst results |

## Run-by-Run Results

### Run 1 — Qwen Sweeps (old code, with Phi)
**Winner: Qwen (1.7B LOCAL)** — $6,000,000

Qwen dominated with 14 wins in 16 hands. Phi died on hand 1 without making a single raise. Kimi gone by hand 3. Qwen just kept raising and winning.

### Run 2 — MiniMax Takes Control (old code, with Phi)  
**Winner: MiniMax (CLOUD)** — $5,971,000

MiniMax played aggressive (12 raises) but selective (4 folds). Phi took 7 minutes per decision and still lost everything on hand 2 with 0 raises. Haiku folded 83% of hands.

### Run 3 — Liquid's Perfect Game (new code, with GPT-OSS)
**Winner: Liquid (1.2B LOCAL)** — $5,985,000

Liquid won with 0 folds and 19 raises — pure aggression. GPT-OSS (120B) folded 5 times and raised 0 times. The biggest model at the table played the most passively and got eliminated.

### Run 4 — Kimi's Revenge (new code)
**Winner: Kimi (~1T CLOUD)** — $5,952,000

The biggest model finally won. Kimi played 25 raises (most of any winner) with 8 folds. Haiku put up a fight with 6 hand wins and 16 raises but got eliminated. Qwen died early with only 1 win.

### Run 5 — Liquid Does It Again (new code)
**Winner: Liquid (1.2B LOCAL)** — $5,964,000

Liquid won its second tournament. 6 wins, 15 raises, 2.5s average decision time. The tiny local model outplayed every cloud model again.

## Key Findings

### 1. Parameter count doesn't determine poker ability
The 1.2B model (Liquid) won 2 out of 5 tournaments, beating models up to 800x its size. GPT-OSS (120B) never won a single tournament despite being 100x larger than Liquid.

### 2. Speed correlates with aggression, aggression correlates with winning
Liquid (5s avg) and Qwen are the most aggressive players (53 raises each across all runs). The two winningest players are also the fastest decision-makers who raise the most.

### 3. Bigger models fold too much
Haiku (28 folds), Kimi (27 folds), and GPT-OSS (17 folds in only 3 runs) fold far more than the small models. They "understand" poker better — they know when they have weak hands — but in this tournament structure, folding bleeds chips to blinds/antes.

### 4. Haiku is the best player who never wins
Haiku folds when it should (weak hands), raises when it should (strong hands), and plays the fastest among cloud models (6s). But its conservative strategy doesn't work in a 25-hand tournament with escalating blind pressure. In a 200-hand deep-stack tournament, Haiku would likely dominate.

### 5. The dumbest strategy works
Liquid's strategy is essentially "raise everything, never fold." This is terrible poker — but against opponents who fold too much, it prints money. The small model doesn't understand hand strength well enough to be scared, and that fearlessness is an advantage.

### 6. Every model has won at least once (except GPT-OSS and Haiku)
Liquid (2), Qwen (1), MiniMax (1), Kimi (1). The results are genuinely random — different winner every time. This proves the poker engine and card shuffler are working correctly.

## Noteworthy Moments

- **Phi's 7-minute decisions**: In Run 2, Phi averaged 421 seconds per decision (7 minutes). It used all that thinking time to... call and lose. 0 wins, 0 raises.
- **Liquid's 0-fold game**: In Run 3, Liquid played every single hand without folding once. 19 raises, 0 folds. Pure chaos.
- **GPT-OSS's paradox**: A 120B parameter model that folds 5 times and raises 0 times in its debut tournament. The model is smart enough to know it has bad cards, too smart to bluff.
- **Kimi's 25-raise rampage**: In Run 4, Kimi went on a raising spree with 25 raises — the most aggressive single-run performance by any model.
- **Haiku's consistent mediocrity**: Average placement of 4.4 across 5 runs. Never won, never finished last (except Run 5). The model equivalent of a mid-table Premier League team.

## Model Placements Across All Runs

```
         Run1  Run2  Run3  Run4  Run5
Liquid    2nd   2nd   1st   2nd   1st   ← Most consistent
Qwen      1st   3rd   2nd   3rd   2nd
GPT-OSS   —     —     3rd   4th   3rd
Haiku     4th   5th   4th   5th   4th   ← Always 4th-5th
MiniMax   5th   1st   5th   6th   5th
Kimi      6th   6th   6th   1st   6th   ← Feast or famine
Phi       3rd   4th   —     —     —     ← Removed (too slow)
```
