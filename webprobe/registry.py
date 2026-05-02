"""Module registry: decorator-based, single source of truth for module names.

PRD ref: Epic 4 > Story 4.1 (module-name validation). Architectural
derivation surfaced during /spec walk (4+5A): formalize v1's MODULES manifest
as a decorator-based registry that auto-extends to Sprint 3+ additions.

TYPE_CHECKING guard avoids the circular import that would otherwise occur
at module load time (registry imports BaseModule, BaseModule's subclasses
import registry to apply @register). The forward reference is for static
analysis only; at runtime, register(cls) works because the caller has
already imported BaseModule via subclassing.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .modules.base import BaseModule

MODULE_REGISTRY: dict[str, type["BaseModule"]] = {}


def register(cls: type["BaseModule"]) -> type["BaseModule"]:
    """Decorator: register a module class by its `name` class attribute.

    Idempotent — re-registration replaces the prior entry. (Useful for
    /build hot-reload during test development.)
    """
    MODULE_REGISTRY[cls.name] = cls
    return cls


def all_module_names() -> frozenset[str]:
    """Source of truth for filter.VALID_NAMES, --help text, and any other
    consumer that needs to enumerate modules.

    Returns a frozenset so callers cannot mutate the registry indirectly.
    """
    return frozenset(MODULE_REGISTRY.keys())
