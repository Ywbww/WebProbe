"""Self-contained HTML report renderer (v1 + v2 coexistence).

One file, no external assets. Inline <style> and <script> only. The Copy
button next to each <a> is a DIRECT DOM SIBLING of the link — the
clipboard JS reads `btn.previousElementSibling.href`. Do not wrap them.

v2 (`render_html`) consumes ScanCoverage / ScanMetadata / args per Story
3.3. v1 (`render_html_v1`) preserved for engine.run() path until Item 23
retires the legacy entry point.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional

from webprobe.findings import Finding, SEVERITY_ORDER

from .colors import HTML_BG, HTML_TEXT, SEVERITY_HEX

_CLIPBOARD_JS = """document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const a = btn.previousElementSibling;
      const url = a.href || a.textContent;
      try {
        await navigator.clipboard.writeText(url);
        flash(btn, 'Copied');
      } catch {
        const range = document.createRange();
        range.selectNodeContents(a);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        flash(btn, 'Selected — Ctrl+C');
      }
    });
  });
});
function flash(btn, msg) {
  const orig = btn.textContent;
  btn.textContent = msg;
  setTimeout(() => { btn.textContent = orig; }, 1200);
}"""


# FIT3048 category names (Story 4.2). Source of truth.
FIT3048_CATEGORIES: dict[int, str] = {
    1: "Server config & deployment hygiene",
    2: "Broken access control",
    3: "Input validation / Injection",
    4: "Security headers & cookies",
    5: "Crypto / SSL / Sessions",
    6: "Information disclosure",
    7: "Brute force / Lockout",
}


def _css() -> str:
    return f"""body {{
  background: {HTML_BG};
  color: {HTML_TEXT};
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  max-width: 960px;
  margin: 2rem auto;
  padding: 0 1rem;
  line-height: 1.5;
}}
h1 {{ margin: 0 0 0.5rem 0; font-size: 1.75rem; }}
h2 {{ font-size: 1.3rem; margin: 1.5rem 0 0.5rem; }}
h3 {{ font-size: 1.1rem; margin: 1rem 0 0.5rem; }}
header.report-header {{ border-bottom: 1px solid #e0e0e0; padding-bottom: 1rem; margin-bottom: 1.5rem; }}
header.report-header .meta {{ display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; color: #555; margin: 0.5rem 0; }}
.operational-risk-chip {{
  background: #C0392B;
  color: white;
  padding: 0.5rem 0.75rem;
  font-weight: bold;
  border: 2px solid #922B21;
  border-radius: 3px;
  margin: 0.75rem 0;
  font-size: 0.95rem;
  letter-spacing: 0.04em;
}}
.operational-risk-chip.muted {{
  background: #95A5A6;
  border-color: #7F8C8D;
}}
.operational-risk-chip.clean {{
  background: #27AE60;
  border-color: #1E8449;
}}
.operational-risk-chip .gate-trail {{ display: block; font-weight: normal; font-size: 0.85rem; margin-top: 0.25rem; }}
.partial-banner {{
  background: #FEF3CD;
  color: #856404;
  padding: 0.5rem 1rem;
  border-left: 4px solid #F39C12;
  margin-top: 0.75rem;
}}
.coverage {{ background: #FAFAFA; border: 1px solid #E0E0E0; padding: 1rem 1.25rem; border-radius: 4px; margin-bottom: 1.5rem; }}
.coverage dl {{ display: grid; grid-template-columns: 200px 1fr; gap: 0.25rem 1rem; margin: 0; }}
.coverage dt {{ font-weight: 600; color: #555; }}
.coverage dd {{ margin: 0; word-break: break-word; }}
.fit3048-category {{ margin-bottom: 2rem; border: 1px solid #ddd; padding: 0.75rem 1rem; border-radius: 4px; }}
.fit3048-category > h2 {{ margin: 0 0 0.5rem; }}
.fit3048-category .count {{ font-weight: normal; color: #666; font-size: 0.9rem; }}
.fit3048-empty {{ background: #F8F8F8; }}
.empty-reason {{ color: #777; font-style: italic; margin: 0; }}
.severity-group {{ margin-top: 1rem; }}
.severity-group > h3 {{
  color: white;
  padding: 0.4rem 0.75rem;
  margin: 0 0 0.5rem 0;
  border-radius: 3px;
}}
.severity-section {{ margin-bottom: 2rem; }}
.severity-section > h2 {{
  color: white;
  padding: 0.4rem 0.75rem;
  margin: 0 0 0.5rem 0;
  border-radius: 3px;
}}
article.finding {{
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid #eee;
}}
article.finding > header.finding-header {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }}
.severity-badge {{
  color: white;
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
  font-size: 0.8rem;
  font-weight: bold;
}}
.severity-badge.severity-critical {{ background: {SEVERITY_HEX['CRITICAL']}; }}
.severity-badge.severity-high     {{ background: {SEVERITY_HEX['HIGH']}; }}
.severity-badge.severity-medium   {{ background: {SEVERITY_HEX['MEDIUM']}; }}
.severity-badge.severity-low      {{ background: {SEVERITY_HEX['LOW']}; }}
.severity-badge.severity-info     {{ background: {SEVERITY_HEX['INFO']}; }}
.finding-name {{ font-size: 1.05rem; margin: 0; flex: 1 1 auto; }}
.auth-badge {{
  background: #ECF0F1;
  color: #2C3E50;
  border: 1px solid #BDC3C7;
  padding: 0.15rem 0.5rem;
  font-size: 0.85rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  border-radius: 3px;
}}
.finding-fields {{
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 0.25rem 1rem;
  margin: 0;
}}
.finding-fields dt {{ font-weight: 600; color: #555; }}
.finding-fields dd {{ margin: 0; word-break: break-word; }}
.copy-btn {{
  font-size: 12px;
  padding: 0.2rem 0.5rem;
  border: 1px solid #ccc;
  background: #f8f8f8;
  cursor: pointer;
  margin-left: 0.5rem;
  border-radius: 3px;
}}
.copy-btn:hover {{ background: #e8e8e8; }}
aside.errors {{
  margin-top: 2rem;
  padding: 0.75rem 1rem;
  border: 1px solid #e0e0e0;
  background: #fafafa;
}}
aside.errors h2 {{ margin-top: 0; font-size: 1.1rem; }}
a {{ color: #2980B9; }}"""


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _esc_url(value: str) -> str:
    return html.escape(value, quote=True)


def _severity_counts(findings: Iterable[Finding]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] += 1
    return counts


# ---------------------------------------------------------------------------
# v2 — OPERATIONAL_RISK chip, SCAN COVERAGE block, FINDINGS block
# ---------------------------------------------------------------------------

def _operational_risk_chip(findings: list[Finding], args) -> str:
    """Item 12a placeholder — minimal chip above SCAN COVERAGE.

    Item 12b upgrades this with severity-tally-driven coloring and a
    `gate-trail` flag enumeration. For now the chip class is fixed and
    text labels the section.
    """
    return (
        '    <div class="operational-risk-chip">'
        "<strong>OPERATIONAL_RISK</strong></div>"
    )


def _coverage_block(coverage) -> str:
    """SCAN COVERAGE styled section — sibling structure to terminal renderer."""
    rows: list[tuple[str, str]] = [("Mode", coverage.mode)]

    sessions = list(getattr(coverage, "sessions", []) or [])
    if sessions:
        rows.append(("Sessions", f"{len(sessions)} ({', '.join(sessions)})"))
    else:
        rows.append(("Sessions", "0"))

    urls = coverage.urls_probed or {}
    by_source = urls.get("by_source", {}) or {}
    src_line = (
        f"{by_source.get('sitemap', 0)} sitemap, "
        f"{by_source.get('robots', 0)} robots, "
        f"{by_source.get('url_list', 0)} url-list, "
        f"{by_source.get('dynamic', 0)} dynamic, "
        f"{by_source.get('curated', 0)} curated"
    )
    rows.append(("URLs probed", f"{urls.get('total', 0)} ({src_line})"))

    mods = coverage.modules_fired or {}
    if mods.get("errored", 0):
        mod_line = (
            f"{mods.get('completed', 0)}/{mods.get('scheduled', 0)} "
            f"({mods['errored']} errors — see MODULES WITH ERRORS)"
        )
    else:
        mod_line = f"{mods.get('completed', 0)}/{mods.get('scheduled', 0)} (no errors)"
    rows.append(("Modules fired", mod_line))

    login_probe = getattr(coverage, "login_probe", None)
    if login_probe is not None:
        if login_probe.confirmed:
            n = len(login_probe.sessions or [])
            label = "Both logins confirmed" if n >= 2 else "Login confirmed"
            rows.append(("Login probe", f"[+] {label} at {login_probe.timestamp}"))
        else:
            rows.append(("Login probe", f"[-] Login not confirmed at {login_probe.timestamp}"))

    sc = getattr(coverage, "session_check", None)
    if sc is not None:
        if sc.session_attached:
            rows.append(("Session check", f"[+] {sc.probe_url} 200 with attached session"))
        else:
            rows.append((
                "Session check",
                f"[!] Session attachment unverified — {sc.probe_url} byte-identical",
            ))

    logout = getattr(coverage, "logout_test", None)
    if logout is not None:
        if logout.cookie_rejected_after_logout:
            rows.append(("Logout test", "[+] Cookie rejected after logout"))
        else:
            sev = logout.finding_severity or "HIGH"
            rows.append(("Logout test", f"[-] Post-logout cookie still accepted ({sev})"))

    psf = list(getattr(coverage, "per_module_source_filter", []) or [])
    for entry in psf:
        srcs = ", ".join(entry.accepted_sources or [])
        rows.append((
            f"Source filter: {entry.module_name}",
            f"accepted {entry.accepted_count}/{entry.pool_total} ({srcs})",
        ))

    wi = getattr(coverage, "wildcard_intents", None)
    if wi is not None:
        ref = wi.info_finding_id or "INFO"
        rows.append(("Wildcard intents", f"{wi.pattern_count} patterns (see INFO finding-id {ref})"))

    rows.append(("Duration", f"{coverage.duration_seconds:.1f}s"))

    parts = ['  <section class="coverage">', "    <h2>Scan Coverage</h2>", "    <dl>"]
    for label, value in rows:
        parts.append(f"      <dt>{_esc(label)}</dt><dd>{_esc(value)}</dd>")
    parts.extend(["    </dl>", "  </section>"])
    return "\n".join(parts)


def _render_finding(f: Finding) -> str:
    sev_class = f"severity-{f.severity.lower()}"
    parts = [
        f'    <article class="finding finding-{f.severity.lower()}" data-category="{_esc(f.category)}">',
        '      <header class="finding-header">',
        f'        <span class="severity-badge {sev_class}">{_esc(f.severity)}</span>',
        f'        <h3 class="finding-name">{_esc(f.name)}</h3>',
    ]
    if f.auth_context is not None:
        parts.append(f'        <span class="auth-badge">[{_esc(f.auth_context)}]</span>')
    parts.append("      </header>")

    parts.append('      <dl class="finding-fields">')
    # URL with copy-btn — DO NOT WRAP comment immediately above
    parts.append("        <dt>URL</dt>")
    parts.append("        <dd>")
    parts.append(
        "          <!-- DO NOT WRAP — clipboard JS depends on previousElementSibling -->"
    )
    parts.append(
        f'          <a href="{_esc_url(f.url)}">{_esc(f.url)}</a>'
        f'<button class="copy-btn" type="button">Copy</button>'
    )
    parts.append("        </dd>")

    parts.append("        <dt>Evidence</dt>")
    parts.append(f"        <dd>{_esc(f.evidence)}</dd>")

    if f.auth_context is not None:
        parts.append("        <dt>Probed</dt>")
        parts.append(f'        <dd><span class="auth-badge">{_esc(f.auth_context)}</span></dd>')

    # IDOR-conditional render — single source of truth (HTML half).
    # The matching expression also lives in webprobe/output/terminal.py.
    # Phase 1 lock: grep verifies this string appears in EXACTLY 2 places
    # under webprobe/output/.
    if f.category == "idor" and f.baseline_context is not None:
        parts.append("        <dt>Baseline</dt>")
        parts.append(f"        <dd>{_esc(f.baseline_context)}</dd>")
        sessions_summary = _idor_sessions_html(f)
        if sessions_summary:
            parts.append("        <dt>Sessions</dt>")
            parts.append(f"        <dd>{_esc(sessions_summary)}</dd>")

    parts.append("        <dt>Fix</dt>")
    parts.append(f"        <dd>{_esc(f.remediation)}</dd>")
    if f.fit3048_category is not None:
        parts.append("        <dt>FIT3048</dt>")
        parts.append(f"        <dd>Category {_esc(f.fit3048_category)}</dd>")
    parts.append("      </dl>")
    parts.append("    </article>")
    return "\n".join(parts)


def _idor_sessions_html(f: Finding) -> str:
    seen = list(getattr(f, "seen_in", []) or [])
    short_hash = (f.evidence_hash or "")[:8]
    if seen:
        return f"{', '.join(seen)} (sha256={short_hash})"
    return f"sha256={short_hash}"


def _render_severity_section_v2(severity: str, findings: list[Finding],
                                heading_tag: str = "h2") -> str:
    bg = SEVERITY_HEX[severity]
    section_cls = "severity-section" if heading_tag == "h2" else "severity-group"
    parts = [
        f'  <section class="{section_cls}" data-severity="{severity}">',
        f'    <{heading_tag} style="background: {bg};">{severity} ({len(findings)})</{heading_tag}>',
    ]
    for f in findings:
        parts.append(_render_finding(f))
    parts.append("  </section>")
    return "\n".join(parts)


def _render_default_findings(findings: list[Finding]) -> str:
    by_sev: dict[str, list[Finding]] = {s: [] for s in SEVERITY_ORDER}
    for f in findings:
        by_sev[f.severity].append(f)

    sections: list[str] = []
    for sev in SEVERITY_ORDER:
        bucket = by_sev[sev]
        if not bucket:
            continue
        sections.append(_render_severity_section_v2(sev, bucket, heading_tag="h2"))
    if not sections:
        return '  <p class="no-findings">(no findings)</p>'
    return "\n".join(sections)


def _render_fit3048_findings(findings: list[Finding], args) -> str:
    """Item 12a placeholder — FIT3048 two-level grouping lands in Item 12b.

    For now `--fit3048` falls through to default severity grouping so the
    document still renders coherently.
    """
    return _render_default_findings(findings)


# ---------------------------------------------------------------------------
# v2 — Top-level render_html
# ---------------------------------------------------------------------------

def render_html(findings: list[Finding], coverage, metadata, args) -> str:
    """v2 HTML report (Story 3.3).

    Returns a complete HTML document. Self-contained: inline CSS + JS, no
    external assets. Document order:
      <header class="report-header">
        h1 + meta + OPERATIONAL_RISK chip
      <section class="coverage"> (above FINDINGS — Story 3.1)
      <section class="findings">
        default: severity grouping
        --fit3048: two-level grouping (category outer, severity inner)
    """
    target_url = getattr(metadata, "target", "") or getattr(args, "target_url", "")
    from urllib.parse import urlparse
    host = urlparse(target_url).hostname or "report"

    started = getattr(metadata, "started_at", "") or ""
    completed = getattr(metadata, "completed_at", "") or ""
    duration = float(getattr(metadata, "duration_seconds", 0.0) or 0.0)

    op_risk_html = _operational_risk_chip(findings, args)
    coverage_html = _coverage_block(coverage)

    if getattr(args, "fit3048", False):
        findings_inner = _render_fit3048_findings(findings, args)
    else:
        findings_inner = _render_default_findings(findings)

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>WebProbe Report — {_esc(host)}</title>",
        "  <style>",
        _css(),
        "  </style>",
        "</head>",
        "<body>",
        '  <header class="report-header">',
        "    <h1>WebProbe v2.0 — Scan Report</h1>",
        '    <div class="meta">',
        f'      <span>Target: <a href="{_esc_url(target_url)}">{_esc(target_url)}</a></span>',
        f"      <span>Started: {_esc(started)}</span>",
        f"      <span>Completed: {_esc(completed)}</span>",
        f"      <span>Duration: {duration:.1f}s</span>",
        "    </div>",
        op_risk_html,
        "  </header>",
        coverage_html,
        '  <section class="findings">',
        "    <h2>Findings</h2>",
        findings_inner,
        "  </section>",
        "  <script>",
        _CLIPBOARD_JS,
        "  </script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# v1 — preserved for legacy engine.run() path
# ---------------------------------------------------------------------------

def _render_finding_v1(f: Finding, args) -> str:
    border_color = SEVERITY_HEX[f.severity]
    parts = [
        f'<article class="finding" style="border-left: 3px solid {border_color};">',
        f"  <h3>{_esc(f.name)}</h3>",
        "  <dl>",
        "    <dt>URL:</dt>",
        f'    <dd><a href="{_esc_url(f.url)}">{_esc(f.url)}</a></dd>',
    ]
    if f.poc_url is not None:
        parts.append("    <dt>POC:</dt>")
        parts.append("    <dd>")
        parts.append("      <!-- DO NOT WRAP -- clipboard JS depends on previousElementSibling -->")
        parts.append(
            f'      <a href="{_esc_url(f.poc_url)}">{_esc(f.poc_url)}</a>'
            f'<button class="copy-btn" type="button">Copy</button>'
        )
        parts.append("    </dd>")
    parts.extend([
        "    <dt>Evidence:</dt>",
        f"    <dd>{_esc(f.evidence)}</dd>",
        "    <dt>Fix:</dt>",
        f"    <dd>{_esc(f.remediation)}</dd>",
        "    <dt>FIT3048:</dt>",
        f"    <dd>Category {_esc(f.fit3048_category)}</dd>",
        "  </dl>",
        "</article>",
    ])
    return "\n".join(parts)


def _render_severity_section_v1(severity: str, findings: list[Finding],
                                args, heading_tag: str = "h2") -> str:
    bg = SEVERITY_HEX[severity]
    lines = [
        '<section class="severity-section">',
        f'  <{heading_tag} style="background: {bg};">{severity} ({len(findings)})</{heading_tag}>',
    ]
    for f in findings:
        lines.append(_render_finding_v1(f, args))
    lines.append("</section>")
    return "\n".join(lines)


def _render_default_body_v1(findings: list[Finding], args) -> str:
    by_sev: dict[str, list[Finding]] = {s: [] for s in SEVERITY_ORDER}
    for f in findings:
        by_sev[f.severity].append(f)

    sections: list[str] = []
    for sev in SEVERITY_ORDER:
        bucket = by_sev[sev]
        if not bucket:
            continue
        sections.append(_render_severity_section_v1(sev, bucket, args, heading_tag="h2"))
    if not sections:
        return '<p class="no-findings">(no findings)</p>'
    return "\n".join(sections)


def _render_fit3048_body_v1(findings: list[Finding], args) -> str:
    by_cat: dict[int, list[Finding]] = {}
    for f in findings:
        by_cat.setdefault(f.fit3048_category, []).append(f)

    sections: list[str] = []
    for cat in sorted(by_cat.keys()):
        cat_findings = by_cat[cat]
        by_sev: dict[str, list[Finding]] = {s: [] for s in SEVERITY_ORDER}
        for f in cat_findings:
            by_sev[f.severity].append(f)

        cat_lines = [
            f'<section class="category-section" data-cat="{cat}">',
            f"  <h2>FIT3048 Category {cat}</h2>",
        ]
        for sev in SEVERITY_ORDER:
            bucket = by_sev[sev]
            if not bucket:
                continue
            cat_lines.append(_render_severity_section_v1(sev, bucket, args, heading_tag="h3"))
        cat_lines.append("</section>")
        sections.append("\n".join(cat_lines))

    if not sections:
        return '<p class="no-findings">(no findings)</p>'
    return "\n".join(sections)


def _render_errors_v1(errored_modules: list[tuple[str, Exception]]) -> str:
    if not errored_modules:
        return ""
    items = []
    for name, exc in errored_modules:
        items.append(
            f"    <li>{_esc(name)}: {_esc(type(exc).__name__)} — Tip: re-run with -v for more detail.</li>"
        )
    return (
        '<aside class="errors">\n'
        "  <h2>Modules with errors</h2>\n"
        "  <ul>\n" + "\n".join(items) + "\n  </ul>\n"
        "</aside>"
    )


def render_html_v1(findings: list[Finding],
                   errored_modules: list[tuple[str, Exception]],
                   args, target, duration: float) -> str:
    """v1 HTML report — preserved verbatim for legacy engine.run() path.

    Identical structure to Sprint 1 output; v2 callers should use the
    `render_html(findings, coverage, metadata, args)` overload.
    """
    counts = _severity_counts(findings)
    counts_line = " | ".join(f"{counts[s]} {s}" for s in SEVERITY_ORDER)

    now = datetime.now().astimezone()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S %Z").strip()

    target_url = getattr(target, "url", getattr(args, "target_url", ""))
    from urllib.parse import urlparse
    host = urlparse(target_url).hostname or "report"

    op_risk_html = ""
    if getattr(args, "include_traversal", False):
        op_risk_html = (
            '    <div class="op-risk" '
            'title="this scan included path-traversal payloads, '
            'which generate noisy logs on the target.">OPERATIONAL_RISK</div>'
        )

    partial_banner_html = ""
    if getattr(args, "partial", False):
        partial_banner_html = (
            '    <div class="partial-banner">'
            "⚠ Partial scan — results may be incomplete</div>"
        )

    if getattr(args, "fit3048", False):
        body_inner = _render_fit3048_body_v1(findings, args)
    else:
        body_inner = _render_default_body_v1(findings, args)

    errors_html = _render_errors_v1(errored_modules)

    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>WebProbe Report — {_esc(host)}</title>",
        "  <style>",
        _css(),
        "  </style>",
        "</head>",
        "<body>",
        '  <header class="hud">',
        "    <h1>WebProbe Report</h1>",
        '    <div class="meta">',
        f'      <span>Target: <a href="{_esc_url(target_url)}">{_esc(target_url)}</a></span>',
        f"      <span>Scanned: {_esc(timestamp_str)}</span>",
        f"      <span>Duration: {duration:.1f}s</span>",
        "    </div>",
        f'    <div class="counts">{_esc(counts_line)}</div>',
    ]
    if op_risk_html:
        parts.append(op_risk_html)
    if partial_banner_html:
        parts.append(partial_banner_html)
    parts.extend([
        "  </header>",
        "  <main>",
        body_inner,
        "  </main>",
    ])
    if errors_html:
        parts.append(errors_html)
    parts.extend([
        "  <script>",
        _CLIPBOARD_JS,
        "  </script>",
        "</body>",
        "</html>",
    ])
    return "\n".join(parts) + "\n"
