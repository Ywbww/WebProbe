"""Terminal renderer (v1 + v2 coexistence).

v1 functions (`render_findings_block`, `render_summary`) preserved for the
legacy `engine.run()` path called from `probe.py`. v2 functions
(`render_banner`, `render_scan_coverage`, `render_findings`,
`render_run_summary`) consume `ScanCoverage` / `ScanMetadata` / new Finding
fields per Sprint 2 spec (Stories 3.1, 3.2, 3.5).

Lock 6 (Sprint 2): renderer functions return strings or accept an explicit
output stream. No bare `print()` for new v2 paths.
"""
from __future__ import annotations

import sys
import textwrap
from typing import Optional, TextIO

from webprobe.findings import SEVERITY_ORDER

from .colors import RESET, SEVERITY_ANSI, should_color


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _tag(severity: str, colored: bool) -> str:
    if colored:
        return f"{SEVERITY_ANSI[severity]}[{severity}]{RESET}"
    return f"[{severity}]"


# ---------------------------------------------------------------------------
# v2 — Banner (Story spec.md "Banner + --help skeleton")
# ---------------------------------------------------------------------------

def _auth_mode_line(args) -> Optional[str]:
    """Return the Auth: line for the banner, or None to omit it."""
    if getattr(args, "auth_form", None):
        # Sessions list — coach_a / coach_b inferred from idor_baseline_user
        sessions: list[str] = []
        primary = getattr(args, "auth_user", None)
        if primary:
            sessions.append(_session_label(primary))
        baseline = getattr(args, "idor_baseline_user", None)
        if baseline:
            sessions.append(_session_label(baseline))
        if not sessions:
            sessions.append("primary")
        return f"form-login ({len(sessions)} sessions: {', '.join(sessions)})"
    if getattr(args, "cookie", None):
        return "cookie-session"
    return None


def _session_label(identity: str) -> str:
    """Strip @host and trailing -test to give compact session label."""
    head = identity.split("@", 1)[0]
    return head


def _profile_line(args) -> Optional[str]:
    if getattr(args, "fit3048", False):
        return "--fit3048"
    if getattr(args, "cakephp", False):
        return "--cakephp"
    return None


def render_banner(args, target) -> str:
    """v2 banner (skeleton-locked).

    Lines:
        WebProbe v2.0
        Target:        <target.url>
        Auth:          <... only if Phase 5 enabled>
        Modules:       [<comma-list>]
        Profile:       <only if profile set>
        ─────────────────────────────────────────────
    """
    target_url = getattr(target, "url", getattr(args, "target_url", ""))
    module_list = getattr(args, "modules_scheduled_names", None)
    if module_list is None:
        module_list = []
    if isinstance(module_list, (list, tuple)):
        modules_str = ", ".join(module_list)
    else:
        modules_str = str(module_list)

    lines = [
        "WebProbe v2.0",
        f"Target:        {target_url}",
    ]
    auth_line = _auth_mode_line(args)
    if auth_line is not None:
        lines.append(f"Auth:          {auth_line}")
    else:
        lines.append("Auth:          Unauthenticated")

    lines.append(f"Modules:       [{modules_str}]")

    profile_line = _profile_line(args)
    if profile_line is not None:
        lines.append(f"Profile:       {profile_line}")

    lines.append("─" * 45)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# v2 — SCAN COVERAGE block (Story 3.1)
# ---------------------------------------------------------------------------

def _coverage_header() -> str:
    return "═" * 15 + " SCAN COVERAGE " + "═" * 15


def render_scan_coverage(coverage) -> str:
    """v2 SCAN COVERAGE block per Story 3.1.

    Line order: Mode / Sessions / URLs probed / Modules fired / Login probe /
    Session check / Logout test / Per-module source filter / Wildcard intents /
    Duration. Auth-phase lines render only when relevant.
    """
    lines: list[str] = [_coverage_header()]

    # Mode
    lines.append(f"Mode: {coverage.mode}")

    # Sessions
    sessions = list(getattr(coverage, "sessions", []) or [])
    if sessions:
        lines.append(f"Sessions: {len(sessions)} ({', '.join(sessions)})")
    else:
        lines.append("Sessions: 0")

    # URLs probed: total + by_source breakdown
    urls = coverage.urls_probed or {}
    total = urls.get("total", 0)
    by_source = urls.get("by_source", {}) or {}
    src_line = (
        f"{by_source.get('sitemap', 0)} sitemap, "
        f"{by_source.get('robots', 0)} robots, "
        f"{by_source.get('url_list', 0)} url-list, "
        f"{by_source.get('dynamic', 0)} dynamic, "
        f"{by_source.get('curated', 0)} curated"
    )
    lines.append(f"URLs probed: {total} ({src_line})")

    # Modules fired
    mods = coverage.modules_fired or {}
    scheduled = mods.get("scheduled", 0)
    completed = mods.get("completed", 0)
    errored = mods.get("errored", 0)
    if errored:
        mod_line = f"{completed}/{scheduled} ({errored} errors — see MODULES WITH ERRORS)"
    else:
        mod_line = f"{completed}/{scheduled} (no errors)"
    lines.append(f"Modules fired: {mod_line}")

    # Login probe (auth phase only)
    login_probe = getattr(coverage, "login_probe", None)
    if login_probe is not None:
        if login_probe.confirmed:
            n = len(login_probe.sessions or [])
            if n >= 2:
                lines.append(f"Login probe: [+] Both logins confirmed at {login_probe.timestamp}")
            else:
                lines.append(f"Login probe: [+] Login confirmed at {login_probe.timestamp}")
        else:
            lines.append(f"Login probe: [-] Login not confirmed at {login_probe.timestamp}")

    # Session check (auth phase only)
    session_check = getattr(coverage, "session_check", None)
    if session_check is not None:
        if session_check.session_attached:
            lines.append(
                f"Session check: [+] {session_check.probe_url} 200 with attached session"
            )
        else:
            lines.append(
                f"Session check: [!] Session attachment unverified — "
                f"{session_check.probe_url} byte-identical with and without session"
            )

    # Logout test (only if session module ran)
    logout = getattr(coverage, "logout_test", None)
    if logout is not None:
        if logout.cookie_rejected_after_logout:
            lines.append("Logout test: [+] Cookie rejected after logout")
        else:
            sev = logout.finding_severity or "HIGH"
            lines.append(f"Logout test: [-] Post-logout cookie still accepted ({sev})")

    # Per-module source filter
    psf = list(getattr(coverage, "per_module_source_filter", []) or [])
    for entry in psf:
        srcs = ", ".join(entry.accepted_sources or [])
        lines.append(
            f"Source filter: {entry.module_name} accepted "
            f"{entry.accepted_count}/{entry.pool_total} ({srcs})"
        )

    # Wildcard intents
    wi = getattr(coverage, "wildcard_intents", None)
    if wi is not None:
        ref = wi.info_finding_id or "INFO"
        lines.append(f"Wildcard intents: {wi.pattern_count} patterns (see INFO finding-id {ref})")

    # Duration
    lines.append(f"Duration: {coverage.duration_seconds:.1f}s")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# v2 — Inline tease (carries optional stream for --json-out - routing)
# ---------------------------------------------------------------------------

def render_findings(findings, args) -> str:
    """v2 FINDINGS block per Story 3.2.

    Severity grouping default (CRITICAL → HIGH → MEDIUM → LOW → INFO),
    then category within severity. Count line ALWAYS includes zeros
    (`[CRITICAL × 0]` not omitted). Per-finding multi-line block with
    Probed/Baseline/Sessions lines only when their source field is set.

    Lock (Phase 1): the IDOR-conditional render expression
    `category == "idor"` lives in EXACTLY 2 places under
    webprobe/output/ — this function and html.py.
    """
    header = "═" * 15 + " FINDINGS " + "═" * 15
    lines: list[str] = [header]

    # Count line — zeros included
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] += 1
    count_line = " ".join(f"[{s} × {counts[s]}]" for s in SEVERITY_ORDER)
    lines.append(count_line)
    lines.append("")

    if not findings:
        lines.append("(no findings)")
        return "\n".join(lines) + "\n"

    colored = should_color(args)
    sorted_findings = sorted(
        findings, key=lambda f: (SEVERITY_ORDER.index(f.severity), f.category)
    )

    for f in sorted_findings:
        lines.append(f"{_tag(f.severity, colored)} {f.name}")
        lines.append(f"     URL:        {f.url}")
        # Wrap evidence at ~70 cols
        ev = f.evidence or ""
        wrapped = textwrap.wrap(ev, width=70) or [""]
        lines.append(f"     Evidence:   {wrapped[0]}")
        for cont in wrapped[1:]:
            lines.append(f"                 {cont}")
        if f.auth_context is not None:
            lines.append(f"     Probed:     {f.auth_context}")
        if f.baseline_context is not None:
            lines.append(f"     Baseline:   {f.baseline_context}")
        # IDOR-conditional Sessions line — single source of truth (terminal half).
        # See html.py for the matching expression. Phase 1 lock: grep verifies
        # this string appears in EXACTLY 2 places under webprobe/output/.
        if f.category == "idor" and f.baseline_context is not None:
            sessions_summary = _idor_sessions_line(f)
            if sessions_summary:
                lines.append(f"     Sessions:   {sessions_summary}")
        lines.append(f"     Fix:        {f.remediation}")
        if f.fit3048_category is not None:
            lines.append(f"     FIT3048:    Category {f.fit3048_category}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _idor_sessions_line(f) -> str:
    """Render the Sessions: line for IDOR findings (8-char hash truncation).

    seen_in is a list of session-attribution labels; we surface them with
    the evidence_hash for the Sprint 2 lock display. Best-effort — when
    the module did not pre-format a sessions string, fall back to a
    summary derived from auth_context / baseline_context.
    """
    seen = list(getattr(f, "seen_in", []) or [])
    short_hash = (f.evidence_hash or "")[:8]
    if seen:
        return f"{', '.join(seen)} (sha256={short_hash})"
    return f"sha256={short_hash}"


def render_run_summary(metadata, sink_paths) -> str:
    """v2 run-end summary per Story 3.5.

    `metadata`: ScanMetadata. `sink_paths`: dict with keys 'html', 'txt',
    'json' — render only the keys present. `--json-out -` mode passes
    `{'json': '<stdout>'}`.
    """
    counts = {s: 0 for s in SEVERITY_ORDER}
    findings = getattr(metadata, "findings", None) or []
    for f in findings:
        counts[f.severity] += 1
    total = sum(counts.values())

    mods_scheduled = getattr(metadata, "modules_scheduled", None)
    mods_completed = getattr(metadata, "modules_completed", None)
    mods_errored = len(getattr(metadata, "errored_modules", []) or [])

    lines: list[str] = [f"Target:    {metadata.target}"]

    if mods_scheduled is not None:
        lines.append(
            f"Modules:   {mods_scheduled} scheduled, "
            f"{mods_completed if mods_completed is not None else mods_scheduled - mods_errored} completed, "
            f"{mods_errored} errored"
        )

    findings_line = (
        f"Findings:  {total} ({counts['CRITICAL']} CRIT, {counts['HIGH']} HIGH, "
        f"{counts['MEDIUM']} MED, {counts['LOW']} LOW, {counts['INFO']} INFO)"
    )
    lines.append(findings_line)

    if sink_paths:
        lines.append("Reports written:")
        for key in ("html", "txt", "json"):
            if key in sink_paths and sink_paths[key]:
                label = key.upper().ljust(4)
                lines.append(f"  {label}: {sink_paths[key]}")

    lines.append(f"Duration:  {metadata.duration_seconds:.1f}s")
    return "\n".join(lines) + "\n"


def render_inline_tease(finding, args, stream: Optional[TextIO] = None) -> None:
    """Live "[SEVERITY] <name> — <url>" feedback during Phase 6.

    Stream parameter for `--json-out -` routing (Lock 6): when JSON goes to
    stdout, terminal output goes to stderr. Defaults to stdout for v1 callers.
    """
    if stream is None:
        stream = sys.stdout
    line = f"{_tag(finding.severity, should_color(args))} {finding.name} — {finding.url}"
    print(line, file=stream)


# ---------------------------------------------------------------------------
# v1 — preserved for legacy engine.run() path
# ---------------------------------------------------------------------------

def render_findings_block(findings, errored_modules, args) -> str:
    """v1 FINDINGS block — kept verbatim for engine.run() compatibility."""
    header = "═" * 18 + " FINDINGS " + "═" * 18
    lines = [header, ""]

    if not findings and not errored_modules:
        lines.append("(no findings)")
        return "\n".join(lines)

    colored = should_color(args)
    sorted_findings = sorted(findings, key=lambda f: (SEVERITY_ORDER.index(f.severity), f.category))

    for f in sorted_findings:
        lines.append(f"{_tag(f.severity, colored)} {f.name}")
        lines.append(f"  URL:        {f.url}")
        if f.poc_url is not None:
            lines.append(f"  POC:        {f.poc_url}")
        lines.append(f"  Evidence:   {f.evidence}")
        lines.append(f"  Fix:        {f.remediation}")
        if getattr(args, "fit3048", False):
            lines.append(f"  FIT3048:    Category {f.fit3048_category}")
        lines.append("")

    if errored_modules:
        lines.append("MODULES WITH ERRORS")
        for name, exc in errored_modules:
            lines.append(f"  - {name}: {type(exc).__name__}")
            lines.append("    Tip: re-run with -v for more detail.")

    return "\n".join(lines).rstrip() + "\n"


def render_summary(findings, errored_modules, args, duration) -> str:
    """v1 run-end summary — kept verbatim for engine.run() compatibility.

    v2 callers should use `render_run_summary(metadata, sink_paths)` instead.
    """
    scheduled = getattr(args, "modules_scheduled", 0)
    errored = len(errored_modules)
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] += 1

    if findings:
        findings_line = (
            f"Findings:  {len(findings)} ({counts['CRITICAL']} CRITICAL, {counts['HIGH']} HIGH, "
            f"{counts['MEDIUM']} MEDIUM, {counts['LOW']} LOW, {counts['INFO']} INFO)"
        )
    else:
        findings_line = "Findings:  0 — no issues detected"

    lines = [
        f"Target:    {getattr(args, 'target_url', '')}",
        f"Modules:   {scheduled} scheduled, {scheduled - errored} completed, {errored} errored",
        findings_line,
        f"Report:    {getattr(args, 'report_filename', 'webprobe_*.html')}",
        f"Duration:  {duration:.1f}s",
    ]
    if errored_modules or getattr(args, "partial", False):
        lines.append("⚠ Partial scan — results may be incomplete")
    return "\n".join(lines) + "\n"
