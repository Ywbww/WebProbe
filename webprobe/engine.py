"""WebProbe engine — orchestrates module dispatch and output."""
from __future__ import annotations

import sys
import time
import threading
from typing import List, Optional, Tuple

import requests

from webprobe.findings import Finding
from webprobe.modules import MODULES
from webprobe.modules.base import BaseModule
from webprobe.session import make_session_factory
from webprobe.target import discover_target
from webprobe.output import colors, terminal

VERSION = "1.0.0"
DEFAULT_MODULE_SLUGS = {"sqli", "xss", "paths", "headers", "info-disclosure", "traversal"}
SCAN_CEILING_SECONDS = 90
CONNECT_TIMEOUT = 5


def _print_banner(args, active_module_names: list[str]) -> None:
    profile = "cakephp" if getattr(args, "cakephp", False) else "none"
    lines = [
        f"WebProbe v{VERSION}",
        f"Target:  {args.target_url}",
        f"Modules: [{', '.join(active_module_names)}]",
        f"Profile: {profile}",
    ]
    if not getattr(args, "include_traversal", False):
        lines.append("(traversal: opt-in via --include-traversal)")
    lines.append("─" * 60)
    for line in lines:
        print(line)


def _check_connectivity(url: str) -> Optional[requests.Response]:
    print("[*] Checking target reachability...")
    sess = requests.Session()
    t0 = time.time()
    try:
        resp = sess.get(url, timeout=CONNECT_TIMEOUT, allow_redirects=True)
    except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
        print("[-] Target unreachable. Check URL and try again.")
        print(f"    ({type(e).__name__}: {e})")
        sys.exit(1)
    elapsed = time.time() - t0
    print(f"[+] Target responding (HTTP {resp.status_code}, {elapsed:.1f}s)")
    return resp


def build_active_modules(args) -> list[BaseModule]:
    selected = set(getattr(args, "only", None) or DEFAULT_MODULE_SLUGS)
    if not getattr(args, "include_traversal", False):
        selected.discard("traversal")
    instances: list[BaseModule] = []
    for cls in MODULES:
        if cls.name not in selected:
            continue
        instances.append(cls())
    return instances


def run(args) -> int:
    colors.init()
    started = time.time()

    active_modules = build_active_modules(args)
    args.modules_scheduled = len(active_modules)

    _print_banner(args, [m.name for m in active_modules])

    base_response = _check_connectivity(args.target_url)

    profile = "cakephp" if getattr(args, "cakephp", False) else None
    target = discover_target(args.target_url, base_response, profile)

    findings: List[Finding] = []
    errored_modules: List[Tuple[str, Exception]] = []
    stdout_lock = threading.Lock()
    ceiling_hit = False

    def report_finding(f: Finding) -> None:
        with stdout_lock:
            terminal.render_inline_tease(f, args)

    session_factory = make_session_factory(args)

    for module in active_modules:
        if (time.time() - started) >= SCAN_CEILING_SECONDS:
            with stdout_lock:
                print(f"[!] Scan ceiling reached ({SCAN_CEILING_SECONDS}s) — emitting findings collected so far.")
            ceiling_hit = True
            errored_modules.append((module.name, TimeoutError(f"ceiling {SCAN_CEILING_SECONDS}s")))
            continue
        with stdout_lock:
            print(f"[*] Running: {module.name}...")
        try:
            module_findings = module.run(target, session_factory, report_finding)
            findings.extend(module_findings)
        except Exception as e:
            with stdout_lock:
                print(f"[!] {module.name}: errored ({type(e).__name__}) — skipped")
            errored_modules.append((module.name, e))

    duration = time.time() - started
    args.partial = bool(errored_modules) or ceiling_hit
    args.report_filename = "webprobe_<host>_<port>_<ts>.html"

    print()
    print(terminal.render_findings_block(findings, errored_modules, args))
    print()
    print(terminal.render_summary(findings, errored_modules, args, duration))

    return 0
