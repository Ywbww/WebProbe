"""Module filtering + risk gates + testbed detection.

PRD ref: prd.md > Epic 4, Epic 5.
Spec ref: spec.md > Phase 0.5 Inter-Flag Validation, Engine Phase Ordering
(Phases 2 / 3.5 / 3.6 / 3.7).

This module is intentionally a stub at Item 5b. Concrete bodies for
`validate_module_flags`, `parse_module_list`, Levenshtein suggestion,
`detect_testbed`, `filter_modules_by_risk_gates`, `render_risk_gate_banner`,
and `validate_i_own_this_target` land in Item 14 (split into 14a/14b).
"""
from __future__ import annotations

from typing import Iterable


def validate_module_flags(args) -> None:
    """Phase 0.5 inter-flag validator.

    Item 14a will implement:
      - mutex: --include-modules / --exclude-modules
      - name validation + Levenshtein suggestion
      - cross-flag: --include-modules <gated> needs gates
    """
    return None


def validate_i_own_this_target(args) -> None:
    """Phase 0.5 hostname-binding validator (Story 5.5).

    Item 14b will implement:
      - rejects path/query in --i-own-this-target assertion
      - hostname == args.target_url's hostname
    """
    return None


def filter_modules_by_user_flags(modules: Iterable[type], args) -> list[type]:
    """Phase 2 user-flag module filtering.

    Item 14a will implement --include-modules / --exclude-modules. Stub
    returns modules unchanged so Phase 2 is a no-op until then.
    """
    return list(modules)


def detect_testbed(args, target) -> bool:
    """Phase 3.5 testbed detection.

    Item 14b will implement testbed signal detection (X-Testbed header,
    localhost/127.0.0.1 patterns, etc.). Stub returns False.
    """
    return False


def filter_modules_by_risk_gates(
    modules: Iterable[type], args, is_testbed: bool
) -> tuple[list[type], list[tuple[type, str]]]:
    """Phase 3.6 risk-gate filtering.

    Returns (kept, dropped). Item 14b will implement testbed bypass +
    per-module gate flag matching. Stub returns (modules, []) — no drops.
    """
    return list(modules), []


def render_risk_gate_banner(
    dropped: list[tuple[type, str]],
    args,
    is_testbed: bool,
    all_excluded: bool,
) -> str:
    """Phase 3.7 risk-gate banner emission (Story 5.3).

    Item 14b will implement banner formatting. Stub returns empty string.
    """
    return ""
