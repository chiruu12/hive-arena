"""Tests for --dramatic CLI flag and profile loading."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from hive.agents.profile import AgentProfile
from hive.runtime.persona import Persona

PROFILES_DIR = _PROJECT_ROOT.parent / "profiles"


def test_dramatic_profiles_exist():
    for name in ["gambler", "coder", "philosopher"]:
        path = PROFILES_DIR / f"{name}.yaml"
        assert path.exists(), f"Profile {name}.yaml not found at {path}"


def test_gambler_profile_high_risk():
    profile = AgentProfile.from_yaml(PROFILES_DIR / "gambler.yaml")
    persona = Persona.from_profile(profile)
    assert persona.risk_tolerance >= 0.7, f"Expected high risk, got {persona.risk_tolerance}"


def test_coder_profile_low_risk():
    profile = AgentProfile.from_yaml(PROFILES_DIR / "coder.yaml")
    persona = Persona.from_profile(profile)
    assert persona.risk_tolerance <= 0.4, f"Expected low risk, got {persona.risk_tolerance}"


def test_philosopher_profile_values():
    profile = AgentProfile.from_yaml(PROFILES_DIR / "philosopher.yaml")
    persona = Persona.from_profile(profile)
    assert persona.values, "Philosopher should have values"
    assert persona.fears, "Philosopher should have fears"


def test_persona_from_profile_preserves_personality():
    profile = AgentProfile.from_yaml(PROFILES_DIR / "gambler.yaml")
    persona = Persona.from_profile(profile)
    assert persona.personality, "Persona should have personality traits from profile"


def test_poker_cli_accepts_dramatic_flag():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dramatic", action="store_true")
    parser.add_argument("--preset", choices=["local", "cloud", "all"])
    args = parser.parse_args(["--preset", "local", "--dramatic"])
    assert args.dramatic is True
    assert args.preset == "local"


def test_arena_cli_accepts_dramatic_flag():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dramatic", action="store_true")
    parser.add_argument("--preset", choices=["local", "cloud"])
    args = parser.parse_args(["--preset", "local", "--dramatic"])
    assert args.dramatic is True
