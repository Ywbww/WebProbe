"""WebProbe — CLI entrypoint."""
from __future__ import annotations

import argparse
import sys

from webprobe import engine

DESCRIPTION = (
    "WebProbe — a small, legible web vulnerability scanner. "
    "Built for cybersecurity students auditing their own apps. "
    "Designed for FIT3047 / FIT3048 use cases (CakePHP, peer assessment)."
)
EPILOG = (
    "For full HTTP traces, manual fuzzing, or an intercepting proxy, "
    "use Burp Suite — WebProbe doesn't replace it."
)
VALID_MODULES = {"sqli", "xss", "paths", "headers", "info-disclosure", "traversal"}


def _parse_only(value: str) -> set[str]:
    names = {n.strip() for n in value.split(",") if n.strip()}
    invalid = names - VALID_MODULES
    if invalid:
        raise argparse.ArgumentTypeError(
            f"invalid module name(s): {sorted(invalid)}. "
            f"Valid: {sorted(VALID_MODULES)}"
        )
    return names


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="webprobe", description=DESCRIPTION, epilog=EPILOG)
    p.add_argument("target_url", help="http://localhost:* or public https://...")
    p.add_argument("--only", type=_parse_only, default=None,
                   help="Comma-separated module names to run.")
    p.add_argument("--output", default=".", help="Output directory for reports.")
    p.add_argument("--cakephp", action="store_true", help="Activate CakePHP profile.")
    p.add_argument("--fit3048", action="store_true",
                   help="Group HTML report by FIT3048 category.")
    p.add_argument("--include-traversal", dest="include_traversal", action="store_true",
                   help="Opt in to directory-traversal module (noisy).")
    p.add_argument("--no-color", dest="no_color", action="store_true")
    p.add_argument("--force-color", dest="force_color", action="store_true")
    p.add_argument("-v", dest="verbose", action="store_true",
                   help="Verbose: print every path/payload attempted.")

    args = p.parse_args(argv)

    try:
        return engine.run(args)
    except KeyboardInterrupt:
        print("\n[-] Interrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
