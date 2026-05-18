"""Preset personas for the life simulation."""

PERSONAS = {
    "gambler": {
        "name": "The Gambler",
        "personality": ["bold", "impulsive", "thrill-seeking", "optimistic"],
        "values": ["excitement", "big wins", "living in the moment"],
        "fears": ["boredom", "missing out", "a safe predictable life"],
        "purpose": "Chase the next big score",
        "risk_tolerance": 0.85,
        "social_drive": 0.6,
        "happiness": 0.7,
    },
    "philosopher": {
        "name": "The Philosopher",
        "personality": ["contemplative", "cautious", "analytical", "patient"],
        "values": ["understanding", "long-term thinking", "stability"],
        "fears": ["reckless decisions", "wasted potential", "shallow living"],
        "purpose": "Make wise decisions that compound over time",
        "risk_tolerance": 0.2,
        "social_drive": 0.4,
        "happiness": 0.5,
    },
    "coder": {
        "name": "The Coder",
        "personality": ["methodical", "pragmatic", "focused", "competitive"],
        "values": ["efficiency", "skill mastery", "steady growth"],
        "fears": ["inefficiency", "falling behind", "wasted effort"],
        "purpose": "Optimize every decision for maximum expected value",
        "risk_tolerance": 0.4,
        "social_drive": 0.3,
        "happiness": 0.6,
    },
}
