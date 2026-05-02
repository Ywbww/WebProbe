"""Plaintext report (v1 + v2 coexistence).

v2 (`render_txt`) is the ANSI-stripped variant of the terminal stack —
banner + SCAN COVERAGE + FINDINGS + run-end summary, all assembled into
one plain-text document. Implementation strategy: re-use the v2 `render_*`
functions with `args.no_color = True` (so `should_color()` returns False
and `_tag()` emits plain bracket form) AND post-process strip any residual
ANSI escape codes via regex. Idempotent — strip on already-clean text is
a no-op.

v1 (`render_txt_v1`) preserved verbatim for the legacy `engine.run()` path
called from `probe.py` until Item 23 retires the v1 entry point.
"""
from __future__ import annotations

import copy
import re
from typing import Optional

from webprobe.output.terminal import (
    render_banner,
    render_findings,
    render_findings_block,
    render_run_summary,
    render_scan_coverage,
    render_summary,
)

# ANSI escape sequence stripper (CSI + simple ESC sequences). Idempotent
# on already-clean text; safe to apply unconditionally.
_ANSI_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def render_txt(
    banner: str,
    coverage,
    findings: list,
    metadata,
    args,
    sink_paths: Optional[dict] = None,
) -> str:
    """v2 plain-text report.

    Combines banner + SCAN COVERAGE + FINDINGS + run-end summary into one
    document. Uses an args-shadow with `no_color = True` so the underlying
    renderers emit plain `[SEVERITY]` tags; ANSI strip pass after assembly
    catches any color escapes that slipped through (defense-in-depth).

    `sink_paths` mirrors the run-end summary's "Reports written:" block
    so the .txt artifact records what was emitted alongside it. Pass None
    or {} to suppress the block (e.g. for test fixtures).
    """
    no_color_args = copy.copy(args)
    no_color_args.no_color = True
    no_color_args.force_color = False

    sections: list[str] = []
    if banner:
        sections.append(banner.rstrip("\n"))
    if coverage is not None:
        sections.append(render_scan_coverage(coverage).rstrip("\n"))
    sections.append(render_findings(findings, no_color_args).rstrip("\n"))
    if metadata is not None:
        sections.append(render_run_summary(metadata, sink_paths or {}).rstrip("\n"))

    document = "\n\n".join(sections) + "\n"
    return _strip_ansi(document)


# ---------------------------------------------------------------------------
# v1 — preserved for legacy engine.run() path
# ---------------------------------------------------------------------------

def render_txt_v1(findings, errored_modules, args, target, duration) -> str:
    """v1 ANSI-stripped FINDINGS block + summary, sharing layout with terminal."""
    no_color_args = copy.copy(args)
    no_color_args.no_color = True
    no_color_args.force_color = False
    block = render_findings_block(findings, errored_modules, no_color_args)
    summary = render_summary(findings, errored_modules, no_color_args, duration)
    return _strip_ansi(block + "\n\n" + summary + "\n")
