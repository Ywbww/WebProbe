"""v2 entry point: `python3 -m webprobe ...`.

Constructs the v2 Engine and runs the full phase pipeline. Item 9 wires
the minimum argparse surface required by the first vertical slice plus
the auth-pipeline + module-filter flags read by Phase 5 / Phase 0.5
helpers. Future items (10/14a/etc.) extend this argparse with discovery,
risk-gate, and JSON-out flags.

The Sprint 1 entry point (`webprobe/probe.py` / `webprobe.probe:main`)
is left untouched — it remains the v1 invocation path until Item 23
final wiring. Users who run `python3 webprobe/probe.py <target>` (the
README's documented Sprint 1 install flow) get the v1 stack; users who
run `python3 -m webprobe <target> --include-modules access_control ...`
get the v2 Engine.
"""
from __future__ import annotations

import argparse
import sys

from webprobe.engine import Engine


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="webprobe",
        description="WebProbe v2 — small, legible web vulnerability scanner.",
    )
    p.add_argument("target_url", help="http://localhost:* or public https://...")

    # --- Auth flags (Epic 1 / Phase 5) ---
    p.add_argument("--auth-form", dest="auth_form", default=None,
                   help="Login page URL for form-based auth.")
    p.add_argument("--auth-user", dest="auth_user", default=None,
                   help="Primary credential username.")
    p.add_argument("--auth-pass", dest="auth_pass", default=None,
                   help="Primary credential password (or set "
                        "WEBPROBE_AUTH_PASS env var, or be prompted).")
    p.add_argument("--auth-role", dest="auth_role", default=None,
                   help="Optional role label for finding auth_context "
                        "attribution (e.g. 'admin', 'coach').")
    p.add_argument("--cookie", dest="cookie", default=None,
                   help="RFC 6265 Cookie header form for cookie-based auth.")
    p.add_argument("--idor-baseline", dest="idor_baseline", default=None,
                   help="Cookie string for IDOR baseline session.")
    p.add_argument("--idor-baseline-form", dest="idor_baseline_form",
                   default=None,
                   help="Login URL for form-based IDOR baseline session.")
    p.add_argument("--idor-baseline-user", dest="idor_baseline_user",
                   default=None,
                   help="Username for IDOR baseline form-based login.")
    p.add_argument("--idor-baseline-pass", dest="idor_baseline_pass",
                   default=None,
                   help="Password for IDOR baseline form-based login "
                        "(or env WEBPROBE_IDOR_BASELINE_PASS).")
    p.add_argument("--auth-baseline", dest="auth_baseline", default=None,
                   help="(reserved — Item 6b/14a)")
    p.add_argument("--auth-baseline-form", dest="auth_baseline_form",
                   default=None,
                   help="(reserved — Item 6b/14a)")

    # --- Module-filter flags (Epic 4 / Phase 2) ---
    p.add_argument("--include-modules", dest="include_modules", default=None,
                   help="Comma-separated module names to include "
                        "(mutually exclusive with --exclude-modules).")
    p.add_argument("--exclude-modules", dest="exclude_modules", default=None,
                   help="Comma-separated module names to exclude.")

    # --- Risk-gate / scope flags (Epic 5) ---
    p.add_argument("--i-own-this-target", dest="i_own_this_target",
                   default=None,
                   help="Hostname assertion required by gated modules.")
    p.add_argument("--include-brute-force", dest="include_brute_force",
                   action="store_true",
                   help="Opt in to brute_force module (gated).")

    # --- Discovery flags (Epic 2 / Phase 4) ---
    p.add_argument("--use-sitemap", dest="use_sitemap", action="store_true")
    p.add_argument("--use-sitemap-authed", dest="use_sitemap_authed",
                   action="store_true")
    p.add_argument("--use-robots", dest="use_robots", action="store_true")
    p.add_argument("--url-list", dest="url_list", default=None,
                   help="Path to a newline-separated list of URLs to probe.")

    # --- Output flags (Epic 3) ---
    p.add_argument("--json-out", dest="json_out", default=None,
                   help="Path or '-' for JSON envelope output. (Item 13)")
    p.add_argument("--fit3048", dest="fit3048", action="store_true",
                   help="Group HTML report by FIT3048 category. (Item 13)")
    p.add_argument("--profile", dest="profile", default=None,
                   help="Profile preset (e.g. 'cakephp'). (reserved)")

    # Sprint 1 carryover for the legacy --no-color toggle (consumed
    # indirectly by colorama init in Engine.__init__):
    p.add_argument("--no-color", dest="no_color", action="store_true")
    p.add_argument("--force-color", dest="force_color", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        engine = Engine(args)
        return engine.run_pipeline()
    except KeyboardInterrupt:
        print("\n[-] Interrupted by user.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
