"""Registry for transforms and parsers."""

from typing import Callable
from dataclasses import dataclass, field
import ast


@dataclass
class _State:
    """Module-level state container for transforms and configuration."""
    transforms: dict[str, Callable[[str, str], tuple[str, str]]] = field(
        default_factory=dict)
    parsers: dict[str, Callable[[str], ast.expr]] = field(
        default_factory=dict)
    debug_hook: Callable[[str, str], None] | None = None
    # Future: backend_map: dict[str, Any] = field(default_factory=dict)


# Module singleton
_STATE = _State()


def add_transform(key: str):
    """Curried decorator to add a template to the options dictionary."""
    def f(func: Callable[[str, str], tuple[str, str]]) -> None:
        _STATE.transforms[key] = func
    return f


def add_parser(key: str):
    """Curried decorator to register template parsers by return type."""
    def decorator(func: Callable[[str], ast.expr]) -> None:
        _STATE.parsers[key] = func
    return decorator
