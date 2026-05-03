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

Item 23 (v2.0.0) retired Sprint 1's module-level `run(args)` and
`build_active_modules` helper plus `webprobe/probe.py`; the Engine class
below is the sole entry path, invoked from `webprobe/__main__.py`.
"""
from __future__ import annotations

import hashlib
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import colorama
import requests
from requests import Session

from webprobe import auth as _auth
from webprobe import discovery as _discovery
from webprobe import filter as _filter
from webprobe.coverage import ScanCoverage, ScanMetadata, WildcardIntents
from webprobe.findings import Finding, Source, Target
from webprobe.registry import MODULE_REGISTRY
from webprobe.session import make_session_factory

VERSION = "2.0.0"


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
        self._baseline_user_id: Optional[str] = getattr(args, "idor_baseline_user", None)
        # Module enumeration cache (filled in Phase 1):
        self._scheduled_modules: list[type] = []
        # Risk-gate result (filled in Phase 3.6):
        self._dropped_by_risk_gate: list[tuple[type, str]] = []
        # Phase 7 timing: started_at captured here, completed_at at end.
        self._started_at = datetime.now().astimezone()
        self._started_perf = time.time()

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
        """Single GET against args.target_url; build Target with forms +
        query_params extracted from the response body via
        target.discover_target. Phase 4 (Item 10) layers in target.urls."""
        try:
            resp = requests.get(
                self.args.target_url,
                timeout=10,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            print(f"[-] Target unreachable: {exc}", file=self._terminal_stream)
            sys.exit(1)
        from webprobe.target import discover_target
        self._target = discover_target(self.args.target_url, resp, profile=None)

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
        when running against testbed (gates bypassed), or when every
        gated module was ALSO explicitly excluded via --exclude-modules
        (so the drop was user-anticipated and bannering would be noise).
        """
        if not self._dropped_by_risk_gate:
            return
        if self._is_testbed:
            return
        # all_excluded: every risk-gate-dropped module is also in the
        # user's --exclude-modules set. (Spec wording: "ALL risk-gated
        # modules are explicitly excluded via --exclude-modules.")
        excluded_raw = getattr(self.args, "exclude_modules", None)
        excluded_set: set[str] = set()
        if excluded_raw:
            from webprobe.filter import parse_module_list
            excluded_set = set(parse_module_list(excluded_raw))
        dropped_names = {
            getattr(cls, "name", "") for cls, _r in self._dropped_by_risk_gate
        }
        all_excluded = bool(dropped_names) and dropped_names.issubset(excluded_set)
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

    # --- Phase 7: dedup + ScanCoverage/ScanMetadata + sink writes -------
    def _phase_7(self) -> None:
        """Story 3.4 + 3.5 — final integration.

        Steps:
          1. Wildcard-intents INFO finding (Story 2.3) — appended BEFORE
             dedup so it participates in the identity-tuple collapse.
          2. Dedup `self._findings` in place. Identity tuple
             `(category, url, evidence_hash)`. Matched pairs across
             unauth/authed passes merge into one finding with both labels
             on `seen_in`.
          3. Build ScanCoverage from engine state (mode, sessions,
             urls_probed by-source, modules_fired, duration).
          4. Build ScanMetadata (target, started_at, completed_at,
             duration, exit_code, errored_modules, risk_gates_asserted).
          5. Populate `args.fit3048_excluded_categories` so the FIT3048
             HTML grouping renderer can distinguish "no findings (clean)"
             from "no findings (excluded by --include/--exclude)".
          6. Populate `args.risk_gates_asserted` for the OPERATIONAL_RISK
             chip (cross-checked by HTML renderer).
          7. Write four output sinks: terminal stream + HTML + TXT + JSON.
             `--json-out -` routes JSON to stdout; terminal/coverage/
             findings/summary already route to `self._terminal_stream`
             which is stderr in that mode.
        """
        # 1. Wildcard-intents INFO finding (BEFORE dedup so it's in the
        #    identity-tuple pool — though uniqueness should make collapse
        #    a no-op for INFO singletons).
        self._maybe_emit_wildcard_intents_finding()

        # 2. Dedup in place.
        self._findings = _dedup_findings(self._findings)

        # 3. Build ScanCoverage.
        completed_dt = datetime.now().astimezone()
        elapsed = time.time() - self._started_perf
        coverage = self._build_scan_coverage(elapsed)

        # 4. Build ScanMetadata.
        metadata = self._build_scan_metadata(completed_dt, elapsed)

        # 5. fit3048_excluded_categories.
        self.args.fit3048_excluded_categories = self._compute_excluded_categories()

        # 6. risk_gates_asserted (used by HTML chip + ScanMetadata).
        self.args.risk_gates_asserted = self._compute_risk_gates_asserted()

        # 7. Render and write four sinks.
        self._write_output_sinks(coverage, metadata)

    def _maybe_emit_wildcard_intents_finding(self) -> None:
        """Story 2.3 consolidated INFO finding for robots.txt wildcards.

        Reads `args._discovery_robots_result.wildcard_intents` (populated
        by Phase 4's `discover_robots`) and emits ONE INFO finding per
        scan if any wildcard patterns were observed. Sets
        `coverage.wildcard_intents` cross-reference field via stash on
        self._wildcard_intents (read by `_build_scan_coverage`).
        """
        self._wildcard_intents: Optional[WildcardIntents] = None
        robots_result = getattr(self.args, "_discovery_robots_result", None)
        if robots_result is None:
            return
        patterns = tuple(getattr(robots_result, "wildcard_intents", ()) or ())
        if not patterns:
            return
        target_url = self.args.target_url
        from urllib.parse import urljoin
        info = Finding(
            severity="INFO",
            category="discovery",
            finding_type="wildcard_intents_observed",
            name="robots.txt wildcard intents detected",
            url=urljoin(target_url, "/robots.txt"),
            evidence=", ".join(patterns),
            remediation=(
                "Review robots.txt wildcard semantics — wildcard "
                "Disallow patterns are advisory hints, not access "
                "controls. Verify the underlying paths enforce auth."
            ),
            fit3048_category=1,
        )
        self._findings.append(info)
        self._wildcard_intents = WildcardIntents(
            pattern_count=len(patterns),
            info_finding_id=info.evidence_hash or "",
        )

    def _build_scan_coverage(self, elapsed: float) -> ScanCoverage:
        """Construct the Story 3.4 ScanCoverage block from engine state."""
        # Mode resolution (4 enum values per Mode invariant lock).
        # Item 14b aligns runtime to the spec-locked vocabulary:
        #   "Unauthenticated" / "Cookie-session" /
        #   "Authenticated, single-session" / "Authenticated, dual-session"
        from webprobe.coverage import MODE_VALUES
        auth_form = getattr(self.args, "auth_form", None)
        cookie = getattr(self.args, "cookie", None)
        has_baseline = bool(
            getattr(self.args, "idor_baseline", None)
            or getattr(self.args, "idor_baseline_form", None)
        )
        n_sessions = len(self._sessions)
        if auth_form is None and cookie is None:
            mode = "Unauthenticated"
        elif cookie is not None and not has_baseline:
            mode = "Cookie-session"
        elif n_sessions >= 2 or has_baseline:
            mode = "Authenticated, dual-session"
        else:
            mode = "Authenticated, single-session"
        assert mode in MODE_VALUES, f"mode {mode!r} not in MODE_VALUES"

        # Sessions list: identifiers of primary + baseline (when present).
        sessions: list[str] = []
        if self._primary_user_id:
            sessions.append(self._primary_user_id)
        elif self._sessions:
            sessions.append("primary")
        if self._baseline_user_id:
            sessions.append(self._baseline_user_id)

        # urls_probed.by_source breakdown from frozen pool.
        by_source: dict[str, int] = {
            "sitemap": 0, "robots": 0, "url_list": 0,
            "dynamic": 0, "curated": 0,
        }
        urls = (self._target.urls if self._target is not None else ())
        for _u, src in urls:
            key = src.value if isinstance(src, Source) else str(src)
            by_source[key] = by_source.get(key, 0) + 1
        urls_probed = {"total": len(urls), "by_source": by_source}

        # Modules fired: scheduled (post-Phase-2/3.6 filter) ; errored
        # comes from self._errored_modules; completed = scheduled - errored.
        scheduled = len(self._scheduled_modules)
        errored = len(self._errored_modules)
        completed = max(scheduled - errored, 0)
        modules_fired = {
            "scheduled": scheduled,
            "completed": completed,
            "errored": errored,
        }

        return ScanCoverage(
            mode=mode,
            sessions=sessions,
            urls_probed=urls_probed,
            modules_fired=modules_fired,
            duration_seconds=elapsed,
            wildcard_intents=getattr(self, "_wildcard_intents", None),
        )

    def _build_scan_metadata(self, completed_dt: datetime, elapsed: float) -> ScanMetadata:
        """Construct the Story 3.4 ScanMetadata block from engine state."""
        risk_gates = self._compute_risk_gates_asserted_argv()
        errored_names = [name for name, _exc in self._errored_modules]
        return ScanMetadata(
            target=self.args.target_url,
            started_at=self._started_at.isoformat(),
            completed_at=completed_dt.isoformat(),
            duration_seconds=elapsed,
            exit_code=0,
            errored_modules=errored_names,
            risk_gates_asserted=risk_gates,
        )

    def _compute_risk_gates_asserted_argv(self) -> list[str]:
        """User-typed argv form of risk-gate assertions (case preserved)."""
        flags: list[str] = []
        if getattr(self.args, "include_brute_force", False):
            flags.append("--include-brute-force")
        if getattr(self.args, "include_traversal", False):
            flags.append("--include-traversal")
        iott = getattr(self.args, "i_own_this_target", None)
        if iott:
            flags.append(f"--i-own-this-target={iott}")
        return flags

    def _compute_risk_gates_asserted(self) -> dict[str, bool]:
        """Boolean view of risk-gate assertions (consumed by HTML chip)."""
        return {
            "i_own_this_target": bool(getattr(self.args, "i_own_this_target", None)),
            "include_brute_force": bool(getattr(self.args, "include_brute_force", False)),
            "include_traversal": bool(getattr(self.args, "include_traversal", False)),
        }

    def _compute_excluded_categories(self) -> set[int]:
        """Set of FIT3048 categories with zero scheduled modules.

        After Phase 2 filtering, walk every REGISTERED module's
        FIT3048_CATEGORY_MAP, collect every category any registered module
        covers, then subtract the union of categories covered by
        currently-scheduled modules. The remainder is "excluded by user
        flags" — the renderer uses this to label empty FIT3048 categories.
        """
        registered_cats: set[int] = set()
        for cls in MODULE_REGISTRY.values():
            registered_cats.update((getattr(cls, "FIT3048_CATEGORY_MAP", {}) or {}).values())
        scheduled_cats: set[int] = set()
        for cls in self._scheduled_modules:
            scheduled_cats.update((getattr(cls, "FIT3048_CATEGORY_MAP", {}) or {}).values())
        return registered_cats - scheduled_cats

    def _write_output_sinks(self, coverage: ScanCoverage, metadata: ScanMetadata) -> None:
        """Render four sinks (terminal stream + HTML/TXT/JSON files).

        Per Lock 6, terminal output uses `print(..., file=self._terminal_stream)`.
        `--json-out -` mode wires `_terminal_stream` to stderr in __init__,
        so banner/coverage/findings/summary land on stderr automatically.
        """
        from webprobe.output import filename_for_target
        from webprobe.output.html import render_html
        from webprobe.output.json_render import render_json
        from webprobe.output.terminal import (
            render_banner, render_findings, render_run_summary,
            render_scan_coverage,
        )
        from webprobe.output.txt import render_txt

        # JSON sink first — file path or "-" (stdout). Terminal output
        # follows so the user sees a clean JSON document on stdout when
        # piping, and progress text on stderr.
        json_out = getattr(self.args, "json_out", None)
        json_str = render_json(self._findings, coverage, metadata, self.args)
        sink_paths: dict[str, str] = {}

        # Decide HTML/TXT output paths up front so the run-end summary
        # can list them.
        output_dir = getattr(self.args, "output", ".") or "."
        html_path = filename_for_target(
            self.args.target_url, self._started_at, output_dir, "html"
        )
        txt_path = html_path.with_suffix(".txt")
        json_path = None
        if json_out and json_out != "-":
            from pathlib import Path as _Path
            json_path = _Path(json_out)
        elif json_out is None:
            json_path = html_path.with_suffix(".json")

        sink_paths["html"] = str(html_path)
        sink_paths["txt"] = str(txt_path)
        if json_out == "-":
            sink_paths["json"] = "<stdout>"
        elif json_path is not None:
            sink_paths["json"] = str(json_path)

        # Attach runtime-only attributes for render_run_summary's getattr
        # reads. asdict() only serializes declared dataclass fields, so
        # the JSON envelope's `scan` block stays clean (Lock 6 sibling).
        metadata.findings = self._findings  # type: ignore[attr-defined]
        metadata.modules_scheduled = coverage.modules_fired.get("scheduled", 0)  # type: ignore[attr-defined]
        metadata.modules_completed = coverage.modules_fired.get("completed", 0)  # type: ignore[attr-defined]

        # Render banner once (used by both terminal and TXT sinks).
        banner = render_banner(self.args, self._target)

        # Terminal stream output.
        print(banner.rstrip("\n"), file=self._terminal_stream)
        print(render_scan_coverage(coverage).rstrip("\n"), file=self._terminal_stream)
        print(render_findings(self._findings, self.args).rstrip("\n"),
              file=self._terminal_stream)
        print(render_run_summary(metadata, sink_paths).rstrip("\n"),
              file=self._terminal_stream)

        # HTML sink.
        try:
            html_path.write_text(
                render_html(self._findings, coverage, metadata, self.args),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[!] HTML render failed: {exc}", file=self._terminal_stream)

        # TXT sink.
        try:
            txt_path.write_text(
                render_txt(banner, coverage, self._findings, metadata,
                           self.args, sink_paths),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[!] TXT render failed: {exc}", file=self._terminal_stream)

        # JSON sink (last so any earlier failures show up before the
        # machine-readable artifact lands).
        if json_out == "-":
            sys.stdout.write(json_str)
            if not json_str.endswith("\n"):
                sys.stdout.write("\n")
        elif json_path is not None:
            try:
                json_path.write_text(json_str, encoding="utf-8")
            except Exception as exc:
                print(f"[!] JSON render failed: {exc}", file=self._terminal_stream)

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
        try:
            self._phase_3_6()
        except _auth.ConfigurationError as exc:
            # Gated-module-in-include hard error (Story 4.1 / 5.1 / 5.2).
            # Testbed-aware — moved here from Phase 0.5 per build deviation #6.
            print(f"ERROR: {exc}", file=self._terminal_stream)
            sys.exit(2)
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
            # Live "[SEVERITY] <name> — <url>" feedback during Phase 6.
            # Item 13 replaced the Item-9 debug-print with this render call.
            # Lock 5 preserved (this is engine wrapper code, NOT module
            # body code). list.append is GIL-atomic in CPython; the lock
            # serializes the inline-tease emission so concurrent module
            # threads don't interleave bytes on the same stream.
            with lock:
                from webprobe.output.terminal import render_inline_tease
                render_inline_tease(f, self.args, stream=stream)
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


def _dedup_findings(findings: list[Finding]) -> list[Finding]:
    """Phase 7 dedup. Identity tuple `(category, url, evidence_hash)`.

    Order-preserving (first occurrence wins on identity collisions).
    Matched pairs across passes merge their `seen_in` lists into one
    finding (e.g. ["unauth"] + ["authed"] -> ["unauth", "authed"]).
    Mutates pass-attribution by extending `seen_in` on the survivor;
    other fields take the first-seen value (auth_context from the first
    pass, etc. — module-body fields are identity-stable by construction).
    """
    by_id: dict[tuple[str, str, str], Finding] = {}
    order: list[tuple[str, str, str]] = []
    for f in findings:
        key = (f.category, f.url, f.evidence_hash or "")
        if key not in by_id:
            by_id[key] = f
            order.append(key)
            continue
        survivor = by_id[key]
        for label in (f.seen_in or []):
            if label not in survivor.seen_in:
                survivor.seen_in.append(label)
    return [by_id[k] for k in order]


def _hash_body(text: Optional[str]) -> str:
    """Phase 5e helper: sha256 of (normalized) body, truncated to 16 hex.

    Normalization is conservative — strip leading/trailing whitespace only.
    Aggressive normalization (cookies, CSRF tokens, timestamps) is deferred
    to Sprint 3+ if false-positive rates demand it.
    """
    return hashlib.sha256((text or "").strip().encode("utf-8", "replace")).hexdigest()[:16]


# Sprint 1's module-level `run(args)` plus `build_active_modules` helper were
# retired at Item 23 (v2.0.0 release). The v2 Engine class above is now the
# sole entry path; `python3 -m webprobe ...` invokes `webprobe/__main__.py`
# which constructs and runs the Engine directly.
