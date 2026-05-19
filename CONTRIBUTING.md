# Contributing to Hive Arena

## Branching Rules

**Never push directly to `main`.** Always create a feature branch and open a PR.

```bash
git checkout -b feat/my-feature
git checkout -b fix/bug-name
git checkout -b docs/update
```

## Setup

Requires **Python 3.11+** (see `requires-python` in pyproject.toml).

```bash
git clone https://github.com/chiruu12/hive-arena.git
cd hive-arena
pip install -e ".[dev]"
```

## Project Structure

```
arena/       # Head-to-head 10-round economic game
lifesim/     # Same model, 3 personas, personality injection test
poker/       # LLM poker tournament (uses poker-engine)
results/     # Output JSON (gitignored)
```

## Pull Request Guidelines

- One logical change per PR
- Test manually before submitting
- Clear description of what changed
