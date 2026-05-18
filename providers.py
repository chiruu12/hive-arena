"""Shared provider creation for all arena games."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


def create_provider(model_id: str, kwargs: dict[str, Any]) -> Any:
    """Create a Hive provider from a model ID string."""
    if model_id.startswith("lmstudio:") or kwargs.get("host"):
        from hive.models.lmstudio import LMStudio

        clean = model_id.removeprefix("lmstudio:")
        return LMStudio(model=clean, **kwargs)

    from hive.models.factory import create_runtime_provider

    return create_runtime_provider(model_id)
