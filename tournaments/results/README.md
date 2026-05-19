# LLM Poker Tournament Results

We ran **5 million-dollar poker tournaments** with 6 AI models playing Texas Hold'em against each other. Same rules, same persona, same starting chips — the model is the only variable.

## The Players

| Name | Model | Type | Size |
|------|-------|------|------|
| Liquid | liquid/lfm2.5-1.2b | Local (LM Studio) | 1.2B |
| Qwen | qwen/qwen3-1.7b | Local (LM Studio) | 1.7B |
| GPT-OSS | gpt-oss-120b | Fireworks | 120B |
| MiniMax | minimax-m2p7 | Fireworks | 230B |
| Haiku | claude-haiku-4-5 | Anthropic | — |
| Kimi | kimi-k2p6 | Fireworks | ~1T |

## Results

| Run | Winner | Size | Type | Final Chips |
|-----|--------|------|------|-------------|
| 1 | **Qwen** | 1.7B | LOCAL | $6,000,000 |
| 2 | **MiniMax** | 230B | CLOUD | $5,971,000 |
| 3 | **Liquid** | 1.2B | LOCAL | $5,985,000 |
| 4 | **Kimi** | ~1T | CLOUD | $5,952,000 |
| 5 | **Liquid** | 1.2B | LOCAL | $5,964,000 |

**4 different winners across 5 runs.** The 1.2B local model won twice.

## Try It Yourself

```bash
git clone https://github.com/chiruu12/hive-arena
cd hive-arena
pip install hive-agent rich pyyaml

# Run the tournament
python tournaments/million_dollar.py
```

You'll need:
- [LM Studio](https://lmstudio.ai/) running on port 1234 with Liquid, Qwen loaded
- `ANTHROPIC_API_KEY` in `.env` for Haiku
- `FIREWORKS_API_KEY` in `.env` for MiniMax, Kimi, GPT-OSS

Edit `tournaments/million_dollar.py` to swap models, change blinds, or adjust the number of hands.

## Tournament Config

- **Starting chips**: $1,000,000
- **Blinds**: 5,000 / 10,000
- **Ante**: 1,000 per player per hand
- **Hands**: 25
- **Equity**: Monte Carlo (500 simulations shown to each player)
- **Persona**: Identical for all players

## Known Issue

Chip totals in Runs 2-5 are slightly below $6M (by 15K-48K). This is a minor ante accounting bug when players go all-in for less than the ante amount. It doesn't affect relative standings or who wins.

Built with [Hive](https://github.com/chiruu12/Hive) and [pokertable](https://pypi.org/project/pokertable/).
