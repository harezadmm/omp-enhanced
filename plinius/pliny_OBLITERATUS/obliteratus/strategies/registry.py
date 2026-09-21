"""Strategy registry for looking up ablation strategies by name."""

from __future__ import annotations

from typing import Type

from obliteratus.strategies.base import AblationStrategy

STRATEGY_REGISTRY: dict[str, Type[AblationStrategy]] = {}


def register_strategy(cls: Type[AblationStrategy]) -> Type[AblationStrategy]:
    """Class decorator that registers a strategy under its `name` attribute."""
    STRATEGY_REGISTRY[cls.name] = cls
    return cls


def get_strategy(name: str) -> AblationStrategy:
    """Instantiate a registered strategy by name."""
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(sorted(STRATEGY_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown strategy {name!r}. Available: {available}")
    return STRATEGY_REGISTRY[name]()
