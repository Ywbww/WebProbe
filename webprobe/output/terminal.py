from webprobe.findings import SEVERITY_ORDER

from .colors import RESET, SEVERITY_ANSI, should_color


def _tag(severity: str, colored: bool) -> str:
    if colored:
        return f"{SEVERITY_ANSI[severity]}[{severity}]{RESET}"
    return f"[{severity}]"


def render_inline_tease(finding, args) -> None:
    print(f"{_tag(finding.severity, should_color(args))} {finding.name} — {finding.url}")


def render_findings_block(findings, errored_modules, args) -> str:
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
