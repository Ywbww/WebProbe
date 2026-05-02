"""WebProbe v2 engine — orchestrates module dispatch and output.

PRD ref: prd.md > Epic 6 > Stories 6.3, 6.4.
Spec ref: spec.md > Engine Phase Ordering + report_finding callback v2.

Phase ordering (Engine.run_pipeline):
    Phase 0    argparse + colors.init() (consumed via __init__)
    Phase 0.5  Inter-flag validation (auth + discovery + filter)
    Phase 1    Module enumeration + class-attr validation
    Phase 2    User-flag module filtering
    Phase 3    Connectivity check (single GET → base_response)
    Phase 3.5  Testbed detection (filter.detect_testbed)
    Phase 3.6  Risk-gate filtering (filter.filter_modules_by_risk_gates)
    Phase 3.7  Risk-gate banner emission
    Phase 5a   Resolve primary credential password
    Phase 5b   Build primary Session (form-login OR cookie)
    Phase 5c   Build baseline Session (optional)
    Phase 5d   Shared-session detection (INFO if equal)
    Phase 5e   Session-check probe (sha256 unauth vs primary; INFO if equal)
    Phase 5f   Authed sitemap (stub — body lands at Item 10)
    Phase 4/6/7 Wired progressively in subsequent items.

Sprint 1's module-level `run(args)` function is preserved at the bottom of
this file so `webprobe/probe.py` keeps working until Item 23 rewires the
CLI to the v2 Engine class.
"""
from __future__ import annotations

import hashlib
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
from webprobe.session import make_session_factory

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
        # Risk-gate result (filled in Phase 3.6):
        self._dropped_by_risk_gate: list[tuple[type, str]] = []

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

    # --- Phase 3.5: testbed detection -----------------------------------
    def _phase_3_5(self) -> None:
        """Cache testbed signal so Phase 3.6 can apply the gate-bypass per
        Story 5.3. Concrete signal detection lives in `filter.detect_testbed`
        (Item 14b); stub returns False until then."""
        self._is_testbed = _filter.detect_testbed(self.args, self._target)

    # --- Phase 3.6: risk-gate filtering ---------------------------------
    def _phase_3_6(self) -> None:
        """Apply per-module risk-gate flags. Returns (kept, dropped); we
        keep both so Phase 3.7 can banner the dropped set."""
        kept, dropped = _filter.filter_modules_by_risk_gates(
            self._scheduled_modules, self.args, bool(self._is_testbed)
        )
        self._scheduled_modules = list(kept)
        self._dropped_by_risk_gate = list(dropped)

    # --- Phase 3.7: risk-gate banner ------------------------------------
    def _phase_3_7(self) -> None:
        """Banner emission per Story 5.3. Skipped when nothing was dropped,
        when running against testbed (gates bypassed), or when all modules
        were dropped (we leave that case to Phase 4+'s no-op-handling).
        """
        if not self._dropped_by_risk_gate:
            return
        if self._is_testbed:
            return
        all_excluded = not self._scheduled_modules
        if all_excluded:
            return
        banner = _filter.render_risk_gate_banner(
            self._dropped_by_risk_gate,
            self.args,
            bool(self._is_testbed),
            all_excluded=all_excluded,
        )
        if banner:
            print(banner, file=self._terminal_stream)

    # --- Phase 5a: resolve primary password -----------------------------
    def _phase_5a(self) -> None:
        """Resolve the primary auth password via the Story 1.5 chain.
        Cookie-mode skips (no password to resolve). Form-mode mutates
        `self.args.auth_pass` so Phase 5b reads a concrete value.

        On PasswordResolutionError: abort with sys.exit(1).
        """
        if not getattr(self.args, "auth_form", None):
            return
        try:
            pw = _auth.resolve_password(
                getattr(self.args, "auth_pass", None),
                "WEBPROBE_AUTH_PASS",
                f"[Password for {getattr(self.args, 'auth_user', '<user>')}]: ",
            )
        except _auth.PasswordResolutionError as exc:
            print(f"[-] {exc}", file=self._terminal_stream)
            sys.exit(1)
        self.args.auth_pass = pw

    # --- Phase 5b: primary Session --------------------------------------
    def _phase_5b(self) -> None:
        """Build the primary Session: form-login OR cookie. Append to
        self._sessions. On LoginDiscoveryError / LoginValidationError:
        abort with sys.exit(1).
        """
        cookie = getattr(self.args, "cookie", None)
        auth_form = getattr(self.args, "auth_form", None)
        if cookie:
            self._sessions.append(_auth.setup_cookie_session(cookie))
            return
        if auth_form:
            try:
                sess = _auth.setup_form_login(
                    self.args.target_url,
                    auth_form,
                    self.args.auth_user,
                    self.args.auth_pass,
                )
            except (_auth.LoginDiscoveryError, _auth.LoginValidationError) as exc:
                print(f"[-] {exc}", file=self._terminal_stream)
                sys.exit(1)
            self._sessions.append(sess)
            return
        # No auth flag: nothing to build at 5b. (Engine only enters Phase 5
        # at all when at least one auth flag is set; this branch is the
        # defensive fall-through.)
        return

    # --- Phase 5c: baseline Session -------------------------------------
    def _phase_5c(self) -> None:
        """Build optional baseline Session per Story 1.3. ConfigurationError
        from inter-flag invariants surfaces here at Phase 5c (not Phase 0.5)
        so failures get the auth-pipeline-broken exit code 2 distinct from
        runtime-auth exit code 1. LoginDiscoveryError / LoginValidationError
        from a baseline form-login still abort with sys.exit(1).
        """
        try:
            sess = _auth.setup_baseline(self.args, self.args.target_url)
        except _auth.ConfigurationError as exc:
            print(f"ERROR: {exc}", file=self._terminal_stream)
            sys.exit(2)
        except (_auth.LoginDiscoveryError, _auth.LoginValidationError) as exc:
            print(f"[-] {exc}", file=self._terminal_stream)
            sys.exit(1)
        if sess is not None:
            self._sessions.append(sess)

    # --- Phase 5d: shared-session detection -----------------------------
    def _phase_5d(self) -> None:
        """Continue + INFO finding per Story 1.3.E1 if primary and baseline
        sessions share a session cookie value."""
        f = _auth.detect_shared_session(self._sessions)
        if f is not None:
            # FIT3048 mapping is module-aware; for engine-emitted INFO
            # findings we attach a default category map entry.
            if f.fit3048_category is None:
                f.fit3048_category = 1  # operational/observability bucket
            self._findings.append(f)

    # --- Phase 5e: session-check probe ----------------------------------
    def _phase_5e(self) -> None:
        """GET target URL with primary session, then anonymously. Compare
        sha256 of normalized response bodies (truncated to 16 hex chars).
        Equal hashes -> INFO finding "session_ambiguous"; auth pipeline
        works but the target may not be honoring our cookies.
        """
        if not self._sessions:
            return
        primary = self._sessions[0]
        url = self.args.target_url
        try:
            authed_resp = primary.get(url, timeout=10, allow_redirects=True)
            anon_resp = requests.get(url, timeout=10, allow_redirects=True)
        except requests.RequestException:
            # Don't abort on probe failure — Phase 5e is observability,
            # not gate. Phase 4 will surface real connectivity issues.
            return
        authed_hash = _hash_body(authed_resp.text)
        anon_hash = _hash_body(anon_resp.text)
        if authed_hash == anon_hash:
            f = Finding(
                severity="INFO",
                category="auth",
                finding_type="session_ambiguous",
                name="Authenticated and anonymous responses are identical",
                url=url,
                evidence=(
                    f"GET {url} returned byte-identical bodies for "
                    f"authenticated and anonymous sessions (sha256 prefix "
                    f"{authed_hash}). The target may not be honoring the "
                    "supplied credentials, or the page is intentionally "
                    "public — auth-required modules may produce false "
                    "negatives."
                ),
                remediation=(
                    "Verify --auth-form / --cookie credentials by browsing "
                    "the target manually with the same auth shape, or pick "
                    "a target URL that gates content behind authentication."
                ),
                fit3048_category=1,
            )
            self._findings.append(f)

    # --- Phase 5f: authed sitemap ---------------------------------------
    def _phase_5f(self) -> None:
        """Authed sitemap (Story 2.1 + Phase 5 abort table).

        Triggered when --use-sitemap-authed is set AND auth pipeline has
        a primary session. Re-fetches /sitemap.xml with the authed session
        and merges new URLs into the existing pool (re-dedup applied).

        Per spec, SitemapDiscoveryError here aborts with sys.exit(1)
        — same fail-loud lock as Phase 4 unauth sitemap.
        """
        if not getattr(self.args, "use_sitemap_authed", False):
            return
        if not self._sessions:
            return
        if self._target is None:
            return
        robots_advertised = bool(
            getattr(self.args, "_discovery_robots_result", None)
            and self.args._discovery_robots_result.sitemap_url_advertised
        )
        try:
            new_pool, sitemap_result = _discovery.merge_authed_sitemap(
                self._target,
                self._target.urls,
                authed_session=self._sessions[0],
                advertised_via_robots=robots_advertised,
            )
        except _discovery.SitemapDiscoveryError as exc:
            print(f"[-] {exc}", file=self._terminal_stream)
            sys.exit(1)
        self._target.urls = new_pool
        self.args._discovery_sitemap_result = sitemap_result

    # --- Phase 4: URL pool resolution -----------------------------------
    def _phase_4(self) -> None:
        """URL pool resolution (Epic 2). Composes sitemap + robots +
        url-list + dynamic + curated, dedups by source priority
        (url_list > robots > curated > sitemap > dynamic per Story
        2.4.E1), and freezes the result as a tuple on target.urls.

        Auth-gated sitemap fetch (--use-sitemap-authed) is handled later
        in Phase 5f so the authed session is available; resolve_url_pool
        skips sitemap when use_sitemap_authed is set.

        SitemapDiscoveryError propagates to run_pipeline's existing
        Phase 4 abort handler (sys.exit(1)).
        """
        if self._target is None:
            return
        # sessions arg here is None at Phase 4 (auth runs at Phase 5);
        # passing it for forward-compat with Sprint 3+ unauth-aware
        # discovery flows.
        pool = _discovery.resolve_url_pool(self.args, self._target, sessions=None)
        self._target.urls = pool

    # --- Phase 6: per-module dispatch -----------------------------------
    def _phase_6(self) -> None:
        """Dispatch each scheduled module per its auth_strategy.

        Strategy → pass-label mapping:
          unauth_always   → one pass with anonymous session, label "unauth"
          auth_required   → one pass with primary session, label "authed"
                            (requires self._sessions; skipped silently if
                            no auth flag was set — module simply doesn't
                            run, which is the expected guard)
          follow          → one pass with primary if auth set, else
                            anonymous; label matches the case

        Each module's run() is wrapped in try/except per Module Crash
        semantics (spec.md > Module Crash). Unhandled exceptions append to
        self._errored_modules and the engine continues to the next module.
        """
        role_label = getattr(self.args, "auth_role", None)
        primary_user_id = self._primary_user_id
        for module_cls in self._scheduled_modules:
            strategy = getattr(module_cls, "auth_strategy", None)
            if strategy == "unauth_always":
                pass_label = "unauth"
                sessions_for_pass = [requests.Session()]
            elif strategy == "auth_required":
                if not self._sessions:
                    # No auth pipeline → auth-required modules cannot run.
                    # Engine doesn't error; absence-of-finding is the
                    # signal. (User-flag include of an auth-required
                    # module without auth flags is caught by Phase 0.5
                    # gated-module-in-include validation in Item 14a.)
                    continue
                pass_label = "authed"
                sessions_for_pass = self._sessions
            elif strategy == "follow":
                if self._sessions:
                    pass_label = "authed"
                    sessions_for_pass = self._sessions
                else:
                    pass_label = "unauth"
                    sessions_for_pass = [requests.Session()]
            else:
                # Unknown strategy — Phase 1 should have caught a missing
                # attr, but a typo'd value would leak through. Skip + log.
                self._errored_modules.append(
                    (module_cls.__name__, RuntimeError(
                        f"unknown auth_strategy {strategy!r}"
                    ))
                )
                continue

            try:
                module = module_cls(args=self.args)
            except Exception as exc:
                self._errored_modules.append((module_cls.__name__, exc))
                print(
                    f"[!] Module {module_cls.__name__} errored at construction: {exc}",
                    file=self._terminal_stream,
                )
                continue

            report_finding = self._make_report_finding(
                module_cls, pass_label, primary_user_id, role_label
            )
            session_factory = make_session_factory(sessions_for_pass)

            try:
                module.run(self._target, session_factory, report_finding)
            except Exception as exc:
                # Module Crash semantics — record + emit + continue.
                self._errored_modules.append(
                    (getattr(module_cls, "name", module_cls.__name__), exc)
                )
                print(
                    f"[!] Module {getattr(module_cls, 'name', module_cls.__name__)}"
                    f" errored: {exc}",
                    file=self._terminal_stream,
                )

    # --- Phase 7: dedup (stub) ------------------------------------------
    def _phase_7(self) -> None:
        """Dedup findings — concrete body lands at Item 13 with the JSON
        envelope. For Item 9 the only output is the debug-print emitted
        inside _make_report_finding, so Phase 7 is a no-op."""
        return

    # --- Pipeline entry --------------------------------------------------
    def run_pipeline(self) -> int:
        """Execute the v2 phase ordering. Phases not yet implemented are
        no-op'd via stubs in their owner modules.
        """
        try:
            self._phase_0_5()
        except _auth.ConfigurationError as exc:
            print(f"ERROR: {exc}", file=self._terminal_stream)
            sys.exit(2)
        try:
            self._phase_1()
        except _auth.ConfigurationError as exc:
            # Phase 1's class-attr validation also raises ConfigurationError.
            print(f"ERROR: {exc}", file=self._terminal_stream)
            sys.exit(2)
        self._phase_2()
        self._phase_3()
        self._phase_3_5()
        self._phase_3_6()
        self._phase_3_7()

        try:
            self._phase_4()
        except _discovery.SitemapDiscoveryError as exc:
            # Per spec Phase 5 abort table, SitemapDiscoveryError aborts.
            # The unauth-sitemap path raises here once Item 10 wires it;
            # the authed-sitemap path raises in Phase 5f.
            print(f"[-] {exc}", file=self._terminal_stream)
            sys.exit(1)

        if _any_auth_flag_set(self.args):
            try:
                self._phase_5a()
                self._phase_5b()
                self._phase_5c()
                self._phase_5d()
                self._phase_5e()
                self._phase_5f()
            except _auth.ConfigurationError as exc:
                # Defensive: setup_baseline raises ConfigurationError, which
                # _phase_5c already catches and exits(2). This outer guard
                # covers any future Phase 5 helper that surfaces the same
                # exception type.
                print(f"ERROR: {exc}", file=self._terminal_stream)
                sys.exit(2)
            except (_auth.LoginDiscoveryError,
                    _auth.LoginValidationError,
                    _auth.PasswordResolutionError) as exc:
                # Defensive: per-phase handlers already exit(1) on these,
                # but if any future helper raises without the local catch,
                # we still surface a uniform error+exit shape.
                print(f"[-] {exc}", file=self._terminal_stream)
                sys.exit(1)
            self._auth_phase_succeeded = True

        self._phase_6()
        self._phase_7()

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
            # TEMP — Q1 debug-print verification artifact, removed at
            # Item 13 when json_render lands. Lock 5 preserved (this is
            # engine wrapper code, NOT module body code). default=str
            # handles the Source enum if it ever appears on a Finding
            # field (defensive — current Finding shape doesn't carry one).
            import json as _json
            from dataclasses import asdict as _asdict
            print(_json.dumps(_asdict(f), indent=2, default=str), file=stream)

            # Render + store with lock. Inline-tease render lands in Item 11;
            # for now we just acquire-and-append so storage is thread-safe.
            with lock:
                # TODO Item 11: terminal.render_inline_tease(f, self.args, stream=stream)
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


def _any_auth_flag_set(args) -> bool:
    """Phase 5 entry guard. Skip Phase 5 entirely when no auth flag is set."""
    return any(
        getattr(args, name, None)
        for name in ("auth_form", "cookie", "idor_baseline", "idor_baseline_form")
    )


def _hash_body(text: Optional[str]) -> str:
    """Phase 5e helper: sha256 of (normalized) body, truncated to 16 hex.

    Normalization is conservative — strip leading/trailing whitespace only.
    Aggressive normalization (cookies, CSRF tokens, timestamps) is deferred
    to Sprint 3+ if false-positive rates demand it.
    """
    return hashlib.sha256((text or "").strip().encode("utf-8", "replace")).hexdigest()[:16]


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
