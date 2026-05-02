"""Module filtering + risk gates + testbed detection.

PRD ref: prd.md > Epic 4, Epic 5.
Spec ref: spec.md > Filtering & Risk Gates (Epic 4+5),
Phase 0.5 Inter-Flag Validation, Engine Phase Ordering
(Phases 2 / 3.5 / 3.6 / 3.7).

Item 14a (this commit): validate_module_flags + parse_module_list +
Levenshtein + filter_modules_by_user_flags. Item 14b lands testbed
detection, risk-gate filtering + banner, and validate_i_own_this_target.
"""
from __future__ import annotations

from typing import Iterable, Optional

from webprobe.auth import ConfigurationError
from webprobe.registry import all_module_names

# PRD-locked gated module sets (spec.md > Risk gate filter logic).
# brute_force needs DOUBLE gate: --include-brute-force + --i-own-this-target.
# access_control / idor / csrf need SINGLE gate: --i-own-this-target.
_GATED_DOUBLE: frozenset[str] = frozenset({"brute_force"})
_GATED_SINGLE: frozenset[str] = frozenset({"access_control", "idor", "csrf"})


# --- Module-name parsing -------------------------------------------------

def parse_module_list(value: str) -> list[str]:
    """Whitespace-tolerant comma-split. Empty tokens dropped.

    Example: ``"headers, info-disclosure ,  paths"`` →
    ``["headers", "info-disclosure", "paths"]``.
    """
    if not value:
        return []
    return [tok.strip() for tok in value.split(",") if tok.strip()]


# --- Levenshtein-like suggestion ----------------------------------------

def _levenshtein(a: str, b: str, max_distance: int = 3) -> int:
    """Min edit distance, capped at ``max_distance + 1``.

    Pure Python; no external deps. Wagner-Fischer with row-only DP.
    Early-exits if every cell in a row exceeds ``max_distance``.
    """
    if a == b:
        return 0
    if abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    if len(a) < len(b):
        a, b = b, a
    # b is now the shorter string.
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur[j] = min(
                prev[j] + 1,        # deletion
                cur[j - 1] + 1,     # insertion
                prev[j - 1] + cost, # substitution
            )
        if min(cur) > max_distance:
            return max_distance + 1
        prev = cur
    return prev[-1]


def _suggest_module_name(name: str, valid_names: frozenset[str]) -> tuple[Optional[str], bool]:
    """Return ``(closest_match, is_case_only_difference)``.

    First check case-insensitive match: if the lowercased input matches a
    registered name modulo case, return that with ``case_only=True``.
    Otherwise find the registered name with smallest edit distance ≤ 3
    against the lowercased input.
    """
    if not valid_names:
        return None, False
    name_lower = name.lower()
    # Case-only mismatch detection: input != registered exactly, but
    # lower(input) == lower(registered) for some registered name.
    for reg in valid_names:
        if reg.lower() == name_lower and reg != name:
            return reg, True
    # Edit-distance fallback.
    best: Optional[str] = None
    best_dist = 4
    for reg in valid_names:
        d = _levenshtein(name_lower, reg.lower(), max_distance=3)
        if d < best_dist:
            best = reg
            best_dist = d
    if best_dist <= 3:
        return best, False
    return None, False


# --- Phase 0.5 validators ------------------------------------------------

def validate_module_flags(args) -> None:
    """Phase 0.5 inter-flag validator (Story 4.1).

    Invariants:
      * mutex: ``--include-modules`` ⊕ ``--exclude-modules``
      * each name in include/exclude resolves to a registered module;
        Levenshtein-like suggestion when it doesn't, with case-sensitive
        hint when only case differs.
      * gated-module-in-include needs corresponding gate flag(s).
        Multi-error: lists ALL missing gate flags at once (extends-
        actionable-error pattern).

    Raises ``ConfigurationError`` on violation.
    """
    include = getattr(args, "include_modules", None)
    exclude = getattr(args, "exclude_modules", None)

    if include and exclude:
        raise ConfigurationError(
            "--include-modules and --exclude-modules are mutually "
            "exclusive. Pass one or the other, not both."
        )

    # Trigger module imports so @register has fired before we read the
    # registry. Importing the package runs its __init__, which in turn
    # imports each v2 module (each decorated with @register).
    import webprobe.modules  # noqa: F401  (side-effect import)

    valid_names = all_module_names()

    # Validate each typed name; build suggestion error if unknown.
    for raw_value, flag_label in ((include, "--include-modules"),
                                  (exclude, "--exclude-modules")):
        if not raw_value:
            continue
        for name in parse_module_list(raw_value):
            if name in valid_names:
                continue
            suggestion, case_only = _suggest_module_name(name, valid_names)
            available = ", ".join(sorted(valid_names)) or "(none)"
            if suggestion and case_only:
                raise ConfigurationError(
                    f"unknown module '{name}' in {flag_label}. "
                    f"Did you mean '{suggestion}'? (case-sensitive)\n"
                    f"Available modules: {available}"
                )
            if suggestion:
                raise ConfigurationError(
                    f"unknown module '{name}' in {flag_label}. "
                    f"Did you mean '{suggestion}'?\n"
                    f"Available modules: {available}"
                )
            raise ConfigurationError(
                f"unknown module '{name}' in {flag_label}.\n"
                f"Available modules: {available}"
            )

    # Cross-flag gated-module-in-include validation.
    if include:
        included = set(parse_module_list(include))
        missing_gates: dict[str, list[str]] = {}

        if "brute_force" in included:
            needed: list[str] = []
            if not getattr(args, "include_brute_force", False):
                needed.append("--include-brute-force")
            if not getattr(args, "i_own_this_target", None):
                needed.append("--i-own-this-target=<hostname>")
            if needed:
                missing_gates["brute_force"] = needed

        for gated in sorted(_GATED_SINGLE & included):
            if not getattr(args, "i_own_this_target", None):
                missing_gates[gated] = ["--i-own-this-target=<hostname>"]

        if missing_gates:
            lines = ["The following modules require risk-gate flags:"]
            for mod, flags in sorted(missing_gates.items()):
                lines.append(f"  {mod}: requires {' AND '.join(flags)}")
            lines.append("See risk gates in --help.")
            raise ConfigurationError("\n".join(lines))


def validate_i_own_this_target(args) -> None:
    """Phase 0.5 hostname-binding validator (Story 5.5).

    Stub at Item 14a; Item 14b lands the full validator.
    """
    return None


# --- Phase 2: user-flag module filtering --------------------------------

def filter_modules_by_user_flags(modules: Iterable[type], args) -> list[type]:
    """Apply ``--include-modules`` / ``--exclude-modules`` (Story 4.1).

    Validation already happened at Phase 0.5; this is pure set logic over
    module ``name`` class attributes.
    """
    mods = list(modules)
    include = getattr(args, "include_modules", None)
    exclude = getattr(args, "exclude_modules", None)
    if include:
        wanted = set(parse_module_list(include))
        return [m for m in mods if getattr(m, "name", None) in wanted]
    if exclude:
        unwanted = set(parse_module_list(exclude))
        return [m for m in mods if getattr(m, "name", None) not in unwanted]
    return mods


# --- Phase 3.5/3.6/3.7 placeholders (filled at Item 14b) ----------------

def detect_testbed(args, target) -> bool:
    """Phase 3.5 testbed detection. Item 14b lands the full body."""
    return False


def filter_modules_by_risk_gates(
    modules: Iterable[type], args, is_testbed: bool
) -> tuple[list[type], list[tuple[type, str]]]:
    """Phase 3.6 risk-gate filter. Item 14b lands the full body."""
    return list(modules), []


def render_risk_gate_banner(
    dropped: list[tuple[type, str]],
    args,
    is_testbed: bool,
    all_excluded: bool,
) -> str:
    """Phase 3.7 banner. Item 14b lands the full body."""
    return ""
