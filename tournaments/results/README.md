# LLM Poker Tournament Results

5 million-dollar poker tournaments. 6 AI models. Same rules, same persona, same starting chips. The model is the only variable.

## The Players

| Name | Model | Type | Size |
|------|-------|------|------|
| Liquid | liquid/lfm2.5-1.2b | Local (LM Studio) | 1.2B |
| Qwen | qwen/qwen3-1.7b | Local (LM Studio) | 1.7B |
| GPT-OSS | gpt-oss-120b | Fireworks | 120B |
| MiniMax | minimax-m2p7 | Fireworks | 230B |
| Haiku | claude-haiku-4-5 | Anthropic | - |
| Kimi | kimi-k2p6 | Fireworks | ~1T |

## Results

| Run | Winner | Size | Type |
|-----|--------|------|------|
| 1 | **Qwen** | 1.7B | LOCAL |
| 2 | **MiniMax** | 230B | CLOUD |
| 3 | **Liquid** | 1.2B | LOCAL |
| 4 | **Kimi** | ~1T | CLOUD |
| 5 | **Liquid** | 1.2B | LOCAL |

4 different winners across 5 runs. The 1.2B local model won twice.

## Reproduce

```bash
git clone https://github.com/chiruu12/hive-arena
cd hive-arena
pip install hive-agent rich pyyaml

# Run the full 6-player tournament
python tournaments/million_dollar.py

# Or run a quick custom game
python -m poker.cli --preset local --hands 25 --dramatic
```

You need:
- [LM Studio](https://lmstudio.ai/) on port 1234 with Liquid and Qwen loaded
- `ANTHROPIC_API_KEY` in `.env` for Haiku
- `FIREWORKS_API_KEY` in `.env` for MiniMax, Kimi, GPT-OSS

Edit `tournaments/million_dollar.py` to swap models, change blinds, or adjust hands.

## Config

- **Starting chips**: $1,000,000
- **Blinds**: 5,000 / 10,000
- **Ante**: 1,000 per player per hand
- **Hands**: 25
- **Equity**: Monte Carlo (500 simulations shown to each player)
- **Persona**: Identical for all players

## Want to add your model?

Open an issue with your model name and optional persona config. We will add it to the next run.

Built with [Hive](https://github.com/chiruu12/Hive) and [pokertable](https://pypi.org/project/pokertable/).
