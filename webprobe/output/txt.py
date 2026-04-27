"""Plaintext report — ANSI-stripped form of terminal block + summary."""
from __future__ import annotations

import copy

from webprobe.output.terminal import render_findings_block, render_summary


def render_txt(findings, errored_modules, args, target, duration) -> str:
    """ANSI-stripped FINDINGS block + summary, sharing layout with terminal."""
    no_color_args = copy.copy(args)
    no_color_args.no_color = True
    no_color_args.force_color = False
    block = render_findings_block(findings, errored_modules, no_color_args)
    summary = render_summary(findings, errored_modules, no_color_args, duration)
    return block + "\n\n" + summary + "\n"
