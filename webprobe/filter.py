"""Module filtering + risk gates + testbed detection.

PRD ref: prd.md > Epic 4, Epic 5.
Spec ref: spec.md > Filtering & Risk Gates (Epic 4+5),
Phase 0.5 Inter-Flag Validation, Engine Phase Ordering
(Phases 2 / 3.5 / 3.6 / 3.7).

Item 14a: validate_module_flags + parse_module_list + Levenshtein +
filter_modules_by_user_flags.
Item 14b (this commit): detect_testbed (+ _matches_testbed_url_pattern),
filter_modules_by_risk_gates, render_risk_gate_banner,
validate_i_own_this_target.
"""
from __future__ import annotations

import json as _json
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

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

    Phase 0.5 is the no-HTTP, shape-coherence gate. Invariants checked
    here are flag-shape only:
      * mutex: ``--include-modules`` ⊕ ``--exclude-modules``
      * each name in include/exclude resolves to a registered module;
        Levenshtein-like suggestion when it doesn't, with case-sensitive
        hint when only case differs.

    Gated-module-in-include validation (the rule that ``--include-modules
    access_control`` requires ``--i-own-this-target``) is testbed-aware,
    so it lives in Phase 3.6 (``filter_modules_by_risk_gates``) — by
    then ``detect_testbed`` has run and we know whether to bypass.
    Build deviation #6 (Sprint 2): originally placed at Phase 0.5 in
    Item 14a, surfaced at Checkpoint C as a spec violation against the
    Q4 truth table (Phase 0.5 must not require HTTP knowledge).

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

    # Gated-module-in-include validation moved to Phase 3.6 — see
    # filter_modules_by_risk_gates() for the testbed-aware version.


def validate_i_own_this_target(args) -> None:
    """Phase 0.5 hostname-binding validator (Story 5.5).

    Edge case lock (spec): reject URL path/query in assertion shape so a
    copy-pasted ``https://host/admin`` doesn't silently get truncated to
    its hostname. Hostname comparison is case-insensitive. Port is
    port-agnostic when omitted from the flag, but must match when given.

    No-op when ``args.i_own_this_target`` is None. Raises
    ``ConfigurationError`` on violation.
    """
    asserted = getattr(args, "i_own_this_target", None)
    if asserted is None:
        return

    # Reject URL path/query/fragment before semantic validation.
    if "://" in asserted:
        parsed = urlparse(asserted)
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ConfigurationError(
                f"--i-own-this-target value '{asserted}' contains URL "
                f"path/query. Assertion must be hostname or hostname:port "
                f"only. Try '--i-own-this-target={parsed.hostname}'."
            )
        asserted_parsed = parsed
    else:
        if "/" in asserted or "?" in asserted:
            raise ConfigurationError(
                f"--i-own-this-target value '{asserted}' contains URL "
                f"path/query. Assertion must be hostname or hostname:port "
                f"only."
            )
        asserted_parsed = urlparse(f"//{asserted}")

    target_url = getattr(args, "target_url", None)
    if not target_url:
        raise ConfigurationError(
            "--i-own-this-target requires a target URL to validate against."
        )
    target_parsed = urlparse(target_url)
    if target_parsed.hostname is None or asserted_parsed.hostname is None:
        raise ConfigurationError(
            "unable to parse hostname from target or --i-own-this-target."
        )

    if target_parsed.hostname.lower() != asserted_parsed.hostname.lower():
        raise ConfigurationError(
            f"--i-own-this-target asserts ownership of "
            f"'{asserted_parsed.hostname}' but scan target is "
            f"'{target_parsed.hostname}'. The assertion must match the "
            f"target hostname; this prevents wrapper scripts from auto-"
            f"asserting ownership across changing targets."
        )

    if (asserted_parsed.port is not None
            and target_parsed.port != asserted_parsed.port):
        raise ConfigurationError(
            f"--i-own-this-target port {asserted_parsed.port} does not "
            f"match target port {target_parsed.port}. Either omit the "
            f"port from the assertion (match any port on this hostname) "
            f"or specify the target's exact port."
        )


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


# --- Phase 3.5: testbed detection ---------------------------------------

def _matches_testbed_url_pattern(target_url: str) -> bool:
    """Deterministic netloc check (NOT fuzzy heuristic). Used as a fast
    pre-flight before the HTTP probe, and as the signal for the
    "testbed-shaped target without health endpoint" hint banner."""
    parsed = urlparse(target_url)
    return parsed.netloc in {"localhost:9999", "127.0.0.1:9999"}


def detect_testbed(args, target) -> bool:
    """Story 5.4.E1: probe ``/__webprobe_testbed__/health``, validate the
    response shape. Returns True only on full match. Single attempt, no
    retry; any exception → False.

    The probe URL derives from ``target.url`` when available (engine
    Phase 3 has populated it) or falls back to ``args.target_url``.
    """
    target_url = getattr(args, "target_url", None)
    if target is not None and getattr(target, "url", None):
        target_url = target.url
    if not target_url:
        return False

    probe_url = urljoin(target_url, "/__webprobe_testbed__/health")
    headers = {"User-Agent": "webprobe/2.0 (testbed-detection)"}
    try:
        import requests
        resp = requests.get(probe_url, headers=headers, timeout=5)
    except Exception:
        return False
    if resp.status_code != 200:
        return False
    if "application/json" not in resp.headers.get("Content-Type", ""):
        return False
    try:
        body = resp.json()
    except (ValueError, _json.JSONDecodeError):
        return False
    return body.get("webprobe_testbed") is True


# --- Phase 3.6: risk-gate filtering -------------------------------------

def filter_modules_by_risk_gates(
    modules: Iterable[type], args, is_testbed: bool
) -> tuple[list[type], list[tuple[type, str]]]:
    """Story 5.1 / 5.2 / 5.4 — apply per-module risk-gate flags.

    Testbed bypass returns ``(modules, [])`` — gates skipped entirely.
    Otherwise:
      * If ``--include-modules`` explicitly names a gated module without
        the corresponding gate flag, raise ``ConfigurationError`` listing
        ALL missing gate flags at once (extends-actionable-error pattern,
        Story 4.1 / 5.1 / 5.2). Hard error — user explicitly asked for
        the module but didn't authorize the risk surface.
      * Otherwise drop gated modules whose flags aren't set, returning
        ``(kept, [(cls, reason), ...])`` for the banner.

    The hard-error branch was originally at Phase 0.5
    (validate_module_flags) but that's HTTP-blind and broke testbed
    bypass — see build deviation #6.
    """
    mods = list(modules)
    if is_testbed:
        return mods, []

    has_iott = bool(getattr(args, "i_own_this_target", None))
    has_brute = bool(getattr(args, "include_brute_force", False))

    # Cross-flag gated-module-in-include hard error (non-testbed only).
    include_raw = getattr(args, "include_modules", None)
    if include_raw:
        included = set(parse_module_list(include_raw))
        missing_gates: dict[str, list[str]] = {}

        if "brute_force" in included:
            needed: list[str] = []
            if not has_brute:
                needed.append("--include-brute-force")
            if not has_iott:
                needed.append("--i-own-this-target=<hostname>")
            if needed:
                missing_gates["brute_force"] = needed

        for gated in sorted(_GATED_SINGLE & included):
            if not has_iott:
                missing_gates[gated] = ["--i-own-this-target=<hostname>"]

        if missing_gates:
            lines = ["The following modules require risk-gate flags:"]
            for mod, flags in sorted(missing_gates.items()):
                lines.append(f"  {mod}: requires {' AND '.join(flags)}")
            lines.append("See risk gates in --help.")
            raise ConfigurationError("\n".join(lines))

    kept: list[type] = []
    dropped: list[tuple[type, str]] = []
    for cls in mods:
        name = getattr(cls, "name", None)
        if name in _GATED_DOUBLE:
            if has_brute and has_iott:
                kept.append(cls)
            else:
                dropped.append((
                    cls,
                    "requires --include-brute-force AND --i-own-this-target",
                ))
        elif name in _GATED_SINGLE:
            if has_iott:
                kept.append(cls)
            else:
                dropped.append((cls, "requires --i-own-this-target"))
        else:
            kept.append(cls)
    return kept, dropped


# --- Phase 3.7: risk-gate banner ----------------------------------------

def render_risk_gate_banner(
    dropped: list[tuple[type, str]],
    args,
    is_testbed: bool,
    all_excluded: bool,
) -> str:
    """Story 5.3 — box-drawn banner listing risk-gated modules dropped.

    Suppressed when ``is_testbed`` (gates were bypassed) or when every
    gated module was already excluded by ``--exclude-modules`` (so
    dropping wasn't user-visible). Returns ``""`` in either case.

    Renders to the engine's terminal stream only (NOT to HTML/TXT/JSON
    sinks — Story 5.3 explicitly scopes the banner to the live console).
    """
    if is_testbed:
        return ""
    if all_excluded:
        return ""
    if not dropped:
        return ""

    bar = "═" * 60
    lines = [
        bar,
        "Risk-gated modules disabled (default OFF for non-testbed targets):",
    ]
    for cls, reason in dropped:
        name = getattr(cls, "name", getattr(cls, "__name__", "?"))
        lines.append(f"  {name:<16} {reason}")
    lines.append(bar)
    return "\n".join(lines)
