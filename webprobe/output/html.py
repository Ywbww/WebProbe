"""Self-contained HTML report renderer.

One file, no external assets. Inline <style> and <script> only. The Copy
button next to each POC URL is a DIRECT DOM SIBLING of the <a> — the
clipboard JS reads `btn.previousElementSibling.href`. Do not wrap them.
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Iterable

from webprobe.findings import Finding, SEVERITY_ORDER

from .colors import HTML_BG, HTML_TEXT, SEVERITY_HEX

_CLIPBOARD_JS = """document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const a = btn.previousElementSibling;
      const url = a.href;
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
header.hud {{ border-bottom: 1px solid #e0e0e0; padding-bottom: 1rem; margin-bottom: 1.5rem; }}
header.hud .meta {{ display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.9rem; color: #555; margin-bottom: 0.5rem; }}
header.hud .counts {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.95rem; }}
.partial-banner {{
  background: #FEF3CD;
  color: #856404;
  padding: 0.5rem 1rem;
  border-left: 4px solid #F39C12;
  margin-top: 0.75rem;
}}
.op-risk {{
  background: #C0392B;
  color: white;
  padding: 0.25rem 0.5rem;
  font-weight: bold;
  display: inline-block;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  cursor: help;
}}
.severity-section {{ margin-bottom: 2rem; }}
.severity-section > h2, .severity-section > h3 {{
  color: white;
  padding: 0.4rem 0.75rem;
  margin: 0 0 0.5rem 0;
  border-radius: 3px;
  font-size: 1.1rem;
}}
.category-section {{ margin-bottom: 2.5rem; }}
.category-section > h2 {{
  font-size: 1.3rem;
  border-bottom: 2px solid {HTML_TEXT};
  padding-bottom: 0.25rem;
  margin-bottom: 1rem;
}}
.finding {{
  padding: 0.75rem 1rem;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid #eee;
}}
.finding h3 {{ margin: 0 0 0.5rem 0; font-size: 1.05rem; }}
.finding dl {{
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 0.25rem 1rem;
  margin: 0;
}}
.finding dt {{ font-weight: 600; color: #555; }}
.finding dd {{ margin: 0; word-break: break-word; }}
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


def _render_finding(f: Finding, args) -> str:
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
        parts.append("      <!-- DO NOT WRAP — clipboard JS depends on previousElementSibling -->")
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


def _render_severity_section(severity: str, findings: list[Finding],
                             args, heading_tag: str = "h2") -> str:
    bg = SEVERITY_HEX[severity]
    lines = [
        '<section class="severity-section">',
        f'  <{heading_tag} style="background: {bg};">{severity} ({len(findings)})</{heading_tag}>',
    ]
    for f in findings:
        lines.append(_render_finding(f, args))
    lines.append("</section>")
    return "\n".join(lines)


def _render_default_body(findings: list[Finding], args) -> str:
    by_sev: dict[str, list[Finding]] = {s: [] for s in SEVERITY_ORDER}
    for f in findings:
        by_sev[f.severity].append(f)

    sections: list[str] = []
    for sev in SEVERITY_ORDER:
        bucket = by_sev[sev]
        if not bucket:
            continue
        sections.append(_render_severity_section(sev, bucket, args, heading_tag="h2"))
    if not sections:
        return '<p class="no-findings">(no findings)</p>'
    return "\n".join(sections)


def _render_fit3048_body(findings: list[Finding], args) -> str:
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
            cat_lines.append(_render_severity_section(sev, bucket, args, heading_tag="h3"))
        cat_lines.append("</section>")
        sections.append("\n".join(cat_lines))

    if not sections:
        return '<p class="no-findings">(no findings)</p>'
    return "\n".join(sections)


def _render_errors(errored_modules: list[tuple[str, Exception]]) -> str:
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


def render_html(findings: list[Finding],
                errored_modules: list[tuple[str, Exception]],
                args, target, duration: float) -> str:
    """Return a complete HTML document string for the report."""
    counts = _severity_counts(findings)
    counts_line = " | ".join(f"{counts[s]} {s}" for s in SEVERITY_ORDER)

    now = datetime.now().astimezone()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S %Z").strip()

    target_url = getattr(target, "url", getattr(args, "target_url", ""))
    # Host for the title — strip scheme/path.
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
        body_inner = _render_fit3048_body(findings, args)
    else:
        body_inner = _render_default_body(findings, args)

    errors_html = _render_errors(errored_modules)

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
