"""WebProbe v2 engine — orchestrates module dispatch and output.

PRD ref: prd.md > Epic 6 > Stories 6.3, 6.4.
Spec ref: spec.md > Engine Phase Ordering + report_finding callback v2.

Phase ordering (Engine.run_pipeline):
    Phase 0    argparse + colors.init() (consumed via __init__)
    Phase 0.5  Inter-flag validation (auth + discovery + filter)
    Phase 1    Module enumeration + class-attr validation
    Phase 2    User-flag module filtering
    Phase 3    Connectivity check (single GET → base_response)
    Phase 3.5+ Wired progressively in subsequent items.

Sprint 1's module-level `run(args)` function is preserved at the bottom of
this file so `webprobe/probe.py` keeps working until Item 23 rewires the
CLI to the v2 Engine class.
"""
from __future__ import annotations

import sys
import threading
import time
from datetime import datetime
from typing import List, Optional, Tuple

import colorama
import requests
from requests import Session

from webprobe import auth as _auth
from webprobe import discovery as _discovery
from webprobe import filter as _filter
from webprobe.findings import Finding, Target
from webprobe.registry import MODULE_REGISTRY

VERSION = "2.0.0-dev"


class Engine:
    """v2 Engine. Phase methods are one-line coordinators that delegate to
    helpers. Logic lives in helpers; phase methods read as prose.

    Construction is Phase 0 (argparse already consumed by probe.py). Subsequent
    phases run via `run_pipeline()`.
    """

    def __init__(self, args) -> None:
        self.args = args
        self._terminal_stream = (
            sys.stderr if getattr(args, "json_out", None) == "-" else sys.stdout
        )
        # colorama: don't auto-wrap stdout (we route through
        # self._terminal_stream explicitly); strip ANSI when not a TTY.
        # Note: spec says `wrap_stdout=False` but the actual colorama API
        # uses `wrap=False` (and rejects mixing wrap=False with any other
        # explicit arg, so we configure strip via deinit/init pattern).
        if self._terminal_stream.isatty():
            colorama.init(wrap=False)
        else:
            colorama.init(strip=True, convert=False)
        self._stdout_lock = threading.Lock()
        self._findings: list[Finding] = []
        self._errored_modules: list[tuple[str, Exception]] = []
        self._is_testbed: Optional[bool] = None
        self._sessions: list[Session] = []
        self._auth_phase_succeeded: bool = False
        self._target: Optional[Target] = None
        # Auth attribution captured once per scan; closures read these:
        self._primary_user_id: Optional[str] = getattr(args, "auth_user", None)
        # Module enumeration cache (filled in Phase 1):
        self._scheduled_modules: list[type] = []

    # --- Phase 0.5: inter-flag validation -------------------------------
    def _phase_0_5(self) -> None:
        """All cross-flag invariants caught here, before any HTTP. Validators
        raise ConfigurationError; engine catches at top level and exits with
        code 2 (argparse-style)."""
        _auth.validate_auth_flags(self.args)
        _discovery.validate_discovery_flags(self.args)
        _filter.validate_module_flags(self.args)
        _filter.validate_i_own_this_target(self.args)

    # --- Phase 1: module enumeration + class-attr validation ------------
    def _phase_1(self) -> None:
        """Enumerate registered modules; validate required class attrs.

        Triggers `import webprobe.modules` to fire @register side effects,
        then iterates MODULE_REGISTRY. Each class must declare `name`,
        `auth_strategy`, `FIT3048_CATEGORY_MAP`. Missing attrs raise
        ConfigurationError (caught at run_pipeline's top-level handler).
        """
        # Trigger module imports so @register fires. Sprint 1's v1 modules
        # don't yet use @register (retrofit lands at Items 20-22), so an
        # empty MODULE_REGISTRY is fine here — v2 modules register starting
        # at Item 9.
        import webprobe.modules  # noqa: F401  (side-effect import)

        scheduled: list[type] = []
        for module_cls in MODULE_REGISTRY.values():
            for required in ("name", "auth_strategy", "FIT3048_CATEGORY_MAP"):
                if not _has_concrete_attr(module_cls, required):
                    raise _auth.ConfigurationError(
                        f"Module {module_cls.__name__} missing required class "
                        f"attribute '{required}'. See spec > BaseModule contract."
                    )
            scheduled.append(module_cls)
        self._scheduled_modules = scheduled

    # --- Phase 2: user-flag module filtering ----------------------------
    def _phase_2(self) -> None:
        """Apply --include-modules / --exclude-modules. Risk gates NOT applied
        yet; testbed unknown. Concrete body lives in `filter.py` (Item 14a)."""
        self._scheduled_modules = list(
            _filter.filter_modules_by_user_flags(self._scheduled_modules, self.args)
        )

    # --- Phase 3: connectivity check ------------------------------------
    def _phase_3(self) -> None:
        """Single GET against args.target_url; store as base_response on a
        bare Target. Discovery (Phase 4, Item 10) replaces forms+urls."""
        try:
            resp = requests.get(
                self.args.target_url,
                timeout=10,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            print(f"[-] Target unreachable: {exc}", file=self._terminal_stream)
            sys.exit(1)
        self._target = Target(
            url=self.args.target_url,
            base_response=resp,
            forms=[],
            query_params={},
            profile=None,
            urls=(),
        )

    # --- Pipeline entry --------------------------------------------------
    def run_pipeline(self) -> int:
        """Execute Phases 0.5 → 1 → 2 → 3. Subsequent phases (3.5/3.6/3.7/4/5/6/7)
        are wired in items 7/10/14. Calling beyond Phase 3 currently no-ops.
        """
        try:
            self._phase_0_5()
        except _auth.ConfigurationError as exc:
            print(f"ERROR: {exc}", file=self._terminal_stream)
            sys.exit(2)
        self._phase_1()
        self._phase_2()
        self._phase_3()
        return 0

    # --- report_finding wrapper -----------------------------------------
    def _make_report_finding(
        self,
        module_cls: type,
        pass_label: str,
        primary_user_id: Optional[str],
        role_label: Optional[str],
    ):
        """Build wrapped report_finding for one (module, pass) dispatch.

        Closes ONLY over immutable values + concurrency-designed primitives:
          - module_cls (class object — immutable identity)
          - pass_label (str)
          - primary_user_id (str, set once per scan)
          - role_label (Optional[str], set once via --auth-role)
          - self._stdout_lock (lock object designed for concurrent access)
          - self._findings.append (list.append is GIL-atomic in CPython)
          - self._terminal_stream (set once during Phase 0)

        Sprint 3+ note: self._findings.append safety relies on CPython GIL
        atomicity. If we move to multiprocessing or non-CPython interpreters,
        replace with a thread-safe queue or process-safe IPC.

        The closure must NOT close over mutable engine state for context-
        dependent fields (auth_context shape) — those are captured here as
        outer-call parameters.
        """
        lock = self._stdout_lock
        findings = self._findings
        stream = self._terminal_stream
        auth_strategy = getattr(module_cls, "auth_strategy", None)
        category_map = getattr(module_cls, "FIT3048_CATEGORY_MAP", {})

        def wrapped(f: Finding) -> None:
            # Inject context-dependent attribution fields:
            if auth_strategy == "unauth_always" or pass_label == "unauth":
                f.auth_context = None
            else:
                f.auth_context = (
                    f"as {primary_user_id}"
                    + (f" ({role_label})" if role_label else "")
                )
            # Append pass label to seen_in (engine-private mutation):
            if pass_label not in f.seen_in:
                f.seen_in.append(pass_label)
            # FIT3048 category lookup if module didn't pre-set:
            if f.fit3048_category is None:
                try:
                    f.fit3048_category = category_map[f.finding_type]
                except KeyError:
                    raise RuntimeError(
                        f"{module_cls.__name__}.FIT3048_CATEGORY_MAP missing key "
                        f"'{f.finding_type}'. Add the mapping to the module class."
                    )
            # Render + store with lock. Inline-tease render lands in Item 11;
            # for now we just acquire-and-append so storage is thread-safe.
            with lock:
                # TODO Item 11: terminal.render_inline_tease(f, self.args, stream=stream)
                _ = stream  # placeholder reference; render wired in Item 11
                findings.append(f)

        return wrapped


def _has_concrete_attr(cls: type, attr: str) -> bool:
    """Return True iff `attr` exists with a value somewhere in cls's MRO.

    Pure-annotation declarations (e.g. `name: str` with no `=` value) do
    NOT count: they live in __annotations__, not in any __dict__. This is
    what Phase 1 wants — concrete subclasses must assign the attribute.
    """
    for klass in cls.__mro__:
        if attr in klass.__dict__:
            return True
    return False


# --- Sprint 1 v1 backwards-compat -----------------------------------------
# probe.py imports `engine` and calls `engine.run(args)`. The v1 implementation
# is preserved verbatim below until Item 23 rewires probe.py to the v2 Engine
# class. v1 dependencies are imported lazily inside run() so the Sprint 1
# output stack isn't loaded at module-import time.

_DEFAULT_MODULE_SLUGS = {"sqli", "xss", "paths", "headers", "info-disclosure", "traversal"}
_SCAN_CEILING_SECONDS = 90
_CONNECT_TIMEOUT = 5


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
        resp = sess.get(url, timeout=_CONNECT_TIMEOUT, allow_redirects=True)
    except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
        print("[-] Target unreachable. Check URL and try again.")
        print(f"    ({type(e).__name__}: {e})")
        sys.exit(1)
    elapsed = time.time() - t0
    print(f"[+] Target responding (HTTP {resp.status_code}, {elapsed:.1f}s)")
    return resp


def build_active_modules(args):
    from webprobe.modules import MODULES
    selected = set(getattr(args, "only", None) or _DEFAULT_MODULE_SLUGS)
    if not getattr(args, "include_traversal", False):
        selected.discard("traversal")
    instances = []
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
    """v1 entry point preserved for probe.py until Item 23 rewires to v2 Engine."""
    from webprobe.session import make_session_factory
    from webprobe.target import discover_target
    from webprobe.output import colors, filename_for_target, terminal
    from webprobe.output.html import render_html
    from webprobe.output.txt import render_txt

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
    degraded_any = False

    def report_finding(f: Finding) -> None:
        with stdout_lock:
            terminal.render_inline_tease(f, args)

    session_factory = make_session_factory(args)

    for module in active_modules:
        if (time.time() - started) >= _SCAN_CEILING_SECONDS:
            with stdout_lock:
                print(f"[!] Scan ceiling reached ({_SCAN_CEILING_SECONDS}s) — emitting findings collected so far.")
            ceiling_hit = True
            errored_modules.append((module.name, TimeoutError(f"ceiling {_SCAN_CEILING_SECONDS}s")))
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

    txt_path = html_path.with_suffix(".txt")
    txt_path.write_text(
        render_txt(findings, errored_modules, args, target, duration),
        encoding="utf-8",
    )

    print()
    print(terminal.render_summary(findings, errored_modules, args, duration))

    return 0
