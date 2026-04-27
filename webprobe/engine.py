"""WebProbe engine — orchestrates module dispatch and output."""
from __future__ import annotations

import sys
import time
import threading
from datetime import datetime
from typing import List, Optional, Tuple

import requests

from webprobe.findings import Finding
from webprobe.modules import MODULES
from webprobe.modules.base import BaseModule
from webprobe.session import make_session_factory
from webprobe.target import discover_target
from webprobe.output import colors, filename_for_target, terminal
from webprobe.output.html import render_html
from webprobe.output.txt import render_txt

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
        if cls.name == "paths":
            from webprobe.modules.paths import load_default_paths
            from webprobe.profiles import CAKEPHP_PATHS
            extra = CAKEPHP_PATHS if getattr(args, "cakephp", False) else []
            instances.append(cls(path_list=load_default_paths() + extra))
        else:
            instances.append(cls())
    return instances


def run(args) -> int:
    colors.init()
    started = time.time()
    started_dt = datetime.now().astimezone()

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
    degraded_any = False  # convention: a module signals degradation by setting self.degraded = True

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
        if getattr(module, "degraded", False):
            degraded_any = True

    duration = time.time() - started
    args.partial = bool(errored_modules) or ceiling_hit or degraded_any

    print()
    print(terminal.render_findings_block(findings, errored_modules, args))

    output_dir = getattr(args, "output", ".") or "."
    html_path = filename_for_target(args.target_url, started_dt, output_dir, "html")
    html_path.write_text(
        render_html(findings, errored_modules, args, target, duration),
        encoding="utf-8",
    )
    args.report_filename = html_path.name

    # txt shares basename with html; collision suffix is inherited
    txt_path = html_path.with_suffix(".txt")
    txt_path.write_text(
        render_txt(findings, errored_modules, args, target, duration),
        encoding="utf-8",
    )

    print()
    print(terminal.render_summary(findings, errored_modules, args, duration))

    return 0
