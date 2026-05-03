<!-- Every item uses the five-field format: Title / Spec ref / What to build /
     Acceptance / Verify, plus an Estimated time field added during /checklist
     Phase 1 Q5. Five named checkpoints (A through E) anchored at architectural
     phase boundaries (NOT item numbers) per Phase 1 Q2. The checklist is a
     contract with /build, not a sacred text — if reality diverges, stop,
     propose revert to last clean state, revise the checklist, resume. -->

# WebProbe v2.0 — Sprint 2 Build Checklist

## Build Preferences

- **Build mode:** Autonomous with five named checkpoints (A through E),
  anchored to architectural phase boundaries — renumbering-robust per Phase 1
  Q2 (item splits don't move checkpoint anchors).
- **Comprehension checks:** N/A (autonomous mode).
- **Verification:** Yes, at each checkpoint. Checkpoint B carries a dual role
  (integration acceptance + hour-budget P1 cut decision gate).
- **Check-in cadence:** N/A (autonomous mode).
- **Git commits:** One commit per atomic-acceptance unit per Phase 1 Q3 (β),
  NOT one commit per item-number. Conventional Commits prefix taxonomy:
    - `feat:` — v2 net-new functionality (auth.py, discovery.py, new
      detection modules, etc.)
    - `refactor:` — v1 module retrofit to Module Contract (behavior unchanged,
      contract shape changed)
    - `chore:` — build/CI/tooling/dependency updates
    - `docs:` — documentation updates (README, checklist amendments,
      process-notes section appends)
- **Atomic commit boundary** (Phase 1 Q3 lock — atomic-acceptance unit, NOT
  file count):
    1. Every commit must leave the repo importable: `python -c "import
       webprobe"` succeeds immediately after the commit.
    2. Every commit must complete a single verification step end-to-end —
       no intermediate state where a verification step is half-done.
    3. If a file CAN be committed alone without breaking imports AND its
       acceptance can be verified independently, it gets its own commit.
       Otherwise, multi-file commits are correct.
- **MUST SPLIT rule** (Phase 1 Q5 lock): items annotated `MUST SPLIT` exceed
  the ≤30 min atomic cap and MUST be split into Na/Nb/... sub-items at
  /build time. Each split sub-item gets its own commit per (β); checkpoint
  boundaries hold at architectural completeness.

## Cumulative Time Tally

| Phase | Items | Estimated time |
|---|---|---|
| Foundation (Module Contract dataclasses) | 1-3 | 60 min |
| Framework prep (BaseModule + Engine + auth + testbed + first vertical slice) | 4-9 | 195 min (3.25 hr) |
| Framework epics (discovery + output + filter+gates) | 10-14 | 225 min (3.75 hr) |
| 5 new v2 detection modules | 15-19 | 175 min (2.9 hr) |
| v1 retrofit ×6 in 3 pairs | 20-22 | 90 min (1.5 hr) |
| v2.0.0 release + Devpost update | 23 | 60 min (1 hr) |
| **Subtotal (lower bound)** | 23 items | **820 min (13.7 hr)** |
| **+ MUST SPLIT context-switch overhead** (~8 splits × 20 min) | | **+160 min (2.7 hr)** |
| **+ 5 checkpoint verification overhead** (~15-25 min each) | | **+100 min (1.7 hr)** |
| **Lower-bound total** | | **~18.0 hr** |
| **Realistic real-world** (×1.3-1.5 estimation overhead per Phase 1 Q5) | | **~23-27 hr** |
| **/scope budget** (revised against ~70% Sprint 1 surface increase) | | **24-32 hr** |

P1 cut form (drop items 17/18/19 + their split overhead = 180 min saved):
realistic ~22.2 hr, aligns to original Sprint 1 1.5x estimate.

## Notes for the Build Agent

- **/scope amendment 1** at `docs/sprint-2/scope.md` tail supersedes the
  original rc.1 → final tag progression. Tag `v2.0.0` directly at Endpoint A
  (this checklist's final item). Iteration 2 audit produces v2.0.1 patches
  if needed; never blocks v2.0.0 release.
- **Renumbering-robust framing.** When /build splits item N into Na/Nb/Nc,
  checkpoints reference architectural completeness ("after Module Contract
  foundation locked"), NOT item numbers. The "Roughly: after item N" hints
  in checkpoint anchors are advisory, not binding. Bisect lands on the
  failing atomic commit; revert blast radius matches defect blast radius.
- **Testbed is the integration acceptance harness, not a smoke test** (Phase 1
  Q1 deepening lock). Item 8a + 8b spec the testbed as a complete
  acceptance fixture for ALL 12 modules (6 v1 + 6 v2). Each endpoint names
  its target module + expected finding type. Silent failure mode (module
  ran clean but couldn't fire because testbed lacked differentiating
  fixture) is the failure category to defend against.
- **Debug-print instrumentation at item 9** is engine-wrapper code (NOT
  module body code), so Lock 5 ("zero `print()` in module bodies") holds
  throughout items 9-12. Item 13 (json_render) explicitly removes the
  debug-print line — checklist item 13 verify includes
  `grep "TEMP" webprobe/engine.py` returns no match.
- **Helper file extraction is REACTIVE, not pre-allocated** (per spec.md
  Architecture Decision 15). Items 15, 17, 18 list `_<module>_helpers.py`
  expectations as "informational reference, not commitment" — extraction
  triggered only by 50-line cap violation after run() implementation.
- **Lock 5 grep verification** runs as part of items 20-22 retrofit
  acceptance:
  ```
  grep -rn "print(" webprobe/modules/ --include="*.py" \
      | grep -v _common.py | grep -v _.*_helpers.py
  ```
  Returns nothing. Grep AST upgrade deferred to /build if false-positive
  surfaces (e.g., comment containing `print(`); see Phase 1 Q5 deferral.
- **IDOR-conditional render single-source-of-truth verification** at item 12
  acceptance: `grep -rn "category == .idor." webprobe/output/ | wc -l`
  returns exactly 2 (terminal.py + html.py). Verified again at Checkpoint D.
- **Sprint 1 v1 retrofit acceptance reproduction at Checkpoint E uses
  3-tier fallback** (Phase 1 Q3 lock):
    - Tier 1 (preferred): same-target v1-vs-v2 comparison
      (`git checkout v1.0.0` → run, `git checkout HEAD` → run, diff).
      Target: testbed deliberate-flaw endpoints (item 8a/8b's complete
      fixture surface enables this) OR archived FIT3047 Iteration 1 dump
      if accessible.
    - Tier 2 (fallback): different-target v2 sanity check
      (juice-shop Docker, FIT3047 Iteration 2 if deployed).
    - Tier 3 (graceful degrade): testbed-only v2 acceptance — verify each
      v1 module fires its expected finding type on testbed deliberate-flaw
      endpoints. Always available; never blocks on external dependency.
    - /build agent uses highest available tier.
- **HTML clipboard fragility carryover** at item 12: `<a>` and
  `<button class="copy-btn">` rendered as direct DOM siblings (no
  wrappers); inline HTML comment `<!-- DO NOT WRAP — clipboard JS depends
  on previousElementSibling -->`. Manual click-Copy on a `file://` rendered
  report before marking item complete (Sprint 1 Checkpoint C carryover).
- **process-notes.md `## Sprint 2 — /build` section** is /build's
  autonomous-completion artifact, follows 3-part template (Phase 1 Q4 Flag 2):
    - **What got built** — 2-3 sentences, factual scope summary
      ("Sprint 2 added auth-aware scanning to v1. N new framework files +
      M new detection modules + 6 v1 retrofit migrations. K checkpoints
      A-E passed.").
    - **Notable decisions during build** — each item 1-3 sentences, decisions
      that resolved spec ambiguity / required deviation from spec /
      surfaced new pattern. Each links to the checkpoint that surfaced it
      ("at Checkpoint B: ...").
    - **Open at end of /build** — items left unfinished or known-imperfect,
      explicit handoff to /reflect (P1 cut triggered? helper refactor
      candidates? spec deviations to evaluate?).
  Without the template, the prerequisite passes vacuously ("build done")
  and starves /reflect.

## Checklist

- [x] **1. `findings.py` + `Source` enum + `Finding` kw_only=True dataclass**
  Spec ref: `spec.md > Module Contract > Finding dataclass v2` + `spec.md >
  findings.py scope lock`
  What to build: `webprobe/findings.py` with `Source` enum (5 values:
  SITEMAP, ROBOTS, URL_LIST, DYNAMIC, CURATED) + `ALL_SOURCES = frozenset(Source)`.
  `Finding` dataclass with `@dataclass(kw_only=True)`: required fields
  `severity`, `category`, `finding_type`, `name`, `url`, `evidence`,
  `remediation`. Optional user-content fields: `payload`, `poc_url`,
  `parameter`. Engine-injected fields with construction defaults:
  `auth_context=None`, `baseline_context=None`,
  `seen_in=field(default_factory=list)`, `fit3048_category=None`,
  `evidence_hash=None`. `__post_init__`: severity enum check
  (`SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]` — verify
  v1 source for tier consistency before locking values), finding_type
  non-empty assertion, fit3048_category range check (only if non-None),
  `evidence_hash` auto-compute via
  `sha256(f"{category}:{url}:{evidence}".encode()).hexdigest()[:16]` ONLY
  when None at construction. `Form` (v1 unchanged) and `Target` (v1 +
  `urls: tuple[tuple[str, Source], ...] = ()` field) preserved.
  Acceptance: Per `prd.md > Epic 6 > Story 6.2` — positional construction
  rejected (`Finding('HIGH', 'test', ...)` raises TypeError); evidence_hash
  auto-computes to exactly 16 hex chars; fit3048_category validation
  triggers only when non-None at __post_init__; file contains zero I/O,
  zero helpers acting on findings, zero processing logic — pure type
  definitions only. Estimated lines: 60-90 (informational; framework code
  has no hard cap, unlike detection modules' 50-line cap).
  Verify:
  ```
  python -c "from webprobe.findings import Finding; f = Finding(severity='HIGH', category='test', finding_type='x', name='n', url='https://t.com/p', evidence='e', remediation='r'); assert len(f.evidence_hash) == 16; assert f.fit3048_category is None; print('OK', f.evidence_hash)"
  python -c "from webprobe.findings import Finding; Finding('HIGH', 'test', 'x', 'n', 'u', 'e', 'r')" 2>&1 | grep -q TypeError && echo "positional rejected OK"
  grep -E "^(import|from)" webprobe/findings.py | grep -vE "(dataclasses|enum|hashlib|typing)" && echo "FAIL: extraneous import" || echo "import scope clean"
  ```
  Estimated time: 25 min

- [x] **2. `coverage.py` (ScanCoverage + sub-dataclasses + ScanMetadata)**
  Spec ref: `spec.md > Output > ScanCoverage + sub-dataclasses`
  What to build: `webprobe/coverage.py` with: `LoginProbeResult`,
  `SessionCheckResult`, `LogoutTestResult`, `PerModuleSourceFilter`,
  `WildcardIntents`, `ScanCoverage`, `ScanMetadata` dataclasses per spec
  field-by-field. `SessionCheckResult.sha256_unauth` / `sha256_authed` =
  16-char canonical (8-char terminal display is renderer concern, not
  storage).
  Acceptance: Per `spec.md > Architecture Decision 11` —
  `dataclasses.asdict(coverage_instance)` produces a dict whose key shape
  matches the JSON envelope target (verifies dataclass-shape == JSON-shape
  contract). Optional fields default to None / empty list (per Story 3.4
  field-stability rule).
  Verify:
  ```
  python -c "from webprobe.coverage import ScanCoverage; from dataclasses import asdict; c = ScanCoverage(mode='Unauthenticated', sessions=[], urls_probed={'total': 0, 'by_source': {}}, modules_fired={'scheduled': 0, 'completed': 0, 'errored': 0}, duration_seconds=0.0); d = asdict(c); assert 'login_probe' in d and d['login_probe'] is None; print('asdict OK')"
  ```
  Estimated time: 20 min

- [x] **3. `registry.py` (@register decorator + MODULE_REGISTRY)**
  Spec ref: `spec.md > Module Registry — webprobe/registry.py`
  What to build: `webprobe/registry.py` with: `MODULE_REGISTRY: dict[str,
  type["BaseModule"]] = {}`, `@register` decorator (idempotent —
  re-registration replaces, useful for /build hot-reload during test
  development), `all_module_names() -> frozenset[str]` function. TYPE_CHECKING
  guard for BaseModule type hint (avoids circular import at module load
  time; runtime `register(cls)` works because caller has already imported
  BaseModule via subclassing — forward reference is for static analysis,
  not runtime).
  Acceptance: Per `prd.md > Epic 4 > Story 4.1` — registry serves as single
  source of truth for module-name validation; `@register` is idempotent
  (registering same class name twice replaces, doesn't error);
  `all_module_names()` returns a frozenset (immutable — registry consumers
  can't mutate); registry empty until detection modules import.
  Verify:
  ```
  python -c "from webprobe.registry import register, all_module_names, MODULE_REGISTRY; assert all_module_names() == frozenset(); print('registry empty OK')"
  ```
  Sequencing note: Items 2 and 3 are mutually independent — coverage.py
  doesn't import registry, registry doesn't import coverage. Either order
  works for /build's preference. Default presented order (coverage first,
  registry second) groups "engine-consumed types" before "module-discovery
  types" as mild conceptual ordering — not enforced.
  Estimated time: 15 min

  **═══════════════ CHECKPOINT A — Module Contract foundation locked ═══════════════**
  Boundary: types stable, registry decorator working, no more touching
  dataclass shapes after this point.
  Roughly: after items 1-3 (renumbering-robust anchor: "after Module Contract
  dataclasses + registry").
  Verification: import every module's `@register` decorator firing without
  errors; every dataclass instantiable with `kw_only=True` forcing keyword
  args; `evidence_hash` `__post_init__` produces correct 16-char sha256;
  registry empty-but-importable.
  Heaviness: light (pure type-system check).

- [x] **4. `BaseModule` refactor with DATA_FILES auto-load + `_on_request_error`**
  Spec ref: `spec.md > Module Contract > BaseModule — extended class-level contract`
  What to build: `webprobe/modules/base.py` upgrade per spec —
  `BaseModule(ABC)` with required class attrs declared in body without
  defaults (`name`, `auth_strategy`, `FIT3048_CATEGORY_MAP` — Phase 1
  validation in Item 5 enforces presence). Optional class attrs with
  defaults: `source_filter = ALL_SOURCES`, `DATA_FILES = frozenset()`.
  `__init__(args=None)` stores `self.args = args`, builds `self._data:
  dict[str, list[str]] = {}` by reading each `DATA_FILES` entry from
  `webprobe.data.<name>` package via `importlib.resources.files()` with
  canonical parse (stripped, comment-`#`-skip, blank-skip). Abstract
  `run() -> None` with v2 INVARIANT docstring (engine accounting goes
  through wrapped callback only, NOT return value). `_on_request_error(url,
  exception)` default silent-skip with v2 INVARIANT docstring (no bare
  `except Exception`, no bare `except:`).
  Acceptance: Per `prd.md > Epic 6 > Story 6.1` + `spec.md > Lock 3` +
  `Lock 4` — class-attr declaration discipline, args injected uniformly,
  RequestException via hook (no bare except). Auto-load full integration
  test deferred to Item 10 (access_control with real admin_paths.txt +
  admin_signals.txt). Item 4 verifies class structure + parsing logic only —
  zero repo pollution from verify command.
  Verify:
  ```
  # Class structure
  python -c "
  from webprobe.modules.base import BaseModule
  import inspect
  assert hasattr(BaseModule, 'DATA_FILES'), 'DATA_FILES class attr missing'
  assert BaseModule.DATA_FILES == frozenset(), 'DATA_FILES default not empty'
  assert hasattr(BaseModule, '_on_request_error'), '_on_request_error missing'
  sig = inspect.signature(BaseModule.run)
  params = list(sig.parameters.keys())
  assert params == ['self', 'target', 'session_factory', 'report_finding'], params
  print('BaseModule structure OK')
  "

  # Canonical parse logic via tempfile (no repo pollution)
  python -c "
  import tempfile, pathlib
  with tempfile.TemporaryDirectory() as tmp:
      f = pathlib.Path(tmp) / 'sample.txt'
      f.write_text('# header\n\n  /admin/  \nadmin_path\n')
      parsed = [
          line.strip() for line in f.read_text().splitlines()
          if line.strip() and not line.strip().startswith('#')
      ]
      assert parsed == ['/admin/', 'admin_path'], parsed
  print('canonical parse logic OK')
  "
  ```
  Estimated time: 15-20 min

- [x] **5. `engine.py` Engine class skeleton + Phase 0 / 0.5 / 1 / 2 / 3** — MUST SPLIT (5a engine `__init__` + `_make_report_finding` wrapper, 5b Phase 0/0.5/1, 5c Phase 2/3)
  Spec ref: `spec.md > Engine Phase Ordering` + `spec.md > report_finding callback v2 — closure capture`
  What to build: `webprobe/engine.py` Engine class. `__init__(args)` sets
  `_terminal_stream = sys.stderr if args.json_out == "-" else sys.stdout`,
  `colorama.init(wrap_stdout=False, strip=not stream.isatty())`,
  `_stdout_lock = threading.Lock()`, `_findings: list[Finding] = []`,
  `_errored_modules`, `_is_testbed = None`, `_sessions: list[Session] = []`,
  `_auth_phase_succeeded = False`. `_make_report_finding(module_cls,
  pass_label, primary_user_id, role_label)` closure-captured wrapper per
  spec (closes only over immutable values + designed-for-concurrency
  primitives). Phase 0 (argparse Namespace consumed already), Phase 0.5
  calls `auth.validate_auth_flags + discovery.validate_discovery_flags +
  filter.validate_module_flags + filter.validate_i_own_this_target`
  (functions stubbed at import time; concrete bodies land in items 6/10/14).
  Phase 1 module enumeration + class-attr validation per spec. Phase 2
  user-flag module filtering (skeleton — calls
  `filter.filter_modules_by_user_flags` stub). Phase 3 connectivity check
  (single GET → `self._target.base_response`, RequestException →
  `[-] Target unreachable` + `sys.exit(1)`).
  Acceptance: Per `prd.md > Epic 6 > Story 6.3` + `6.4` — closure capture
  pattern (NOT mutable engine state for context-dependent fields), wrapper
  acquires stdout lock + appends to `_findings`. Engine importable with no
  concrete validators wired (stub functions return None).
  Verify:
  ```
  python -c "from webprobe.engine import Engine; import argparse; e = Engine(argparse.Namespace(json_out=None)); assert e._stdout_lock is not None; print('engine init OK')"
  ```
  Estimated time: 45 min (MUST SPLIT into 5a/5b/5c per ≤30 min cap)

- [x] **6. `auth.py` (custom exceptions + setup functions + helpers)** — MUST SPLIT (6a exceptions + setup_form_login + 3 helpers, 6b setup_cookie_session + setup_baseline + ephemeral_login_form + resolve_password + detect_shared_session + validate_auth_flags)
  Spec ref: `spec.md > Authentication & Session Setup (Epic 1)`
  What to build: `webprobe/auth.py`. Custom exceptions: `LoginDiscoveryError`,
  `LoginValidationError`, `PasswordResolutionError`, `ConfigurationError`.
  `setup_form_login(target_url, login_url, user, password, *,
  verbose=True)` with composition of `_discover_login_form` +
  `_build_login_payload` + `_validate_login_response` (3 pure private
  helpers, NO `requests.Session` instantiation in helpers — testable
  without integration fixtures). `setup_cookie_session(cookie_string)`
  parses RFC 6265 form. `setup_baseline(args, target_url)` owns inter-flag
  invariants (`--idor-baseline` / `--idor-baseline-form` mutex,
  required-with checks → ConfigurationError). `ephemeral_login_form()`
  wraps `setup_form_login(verbose=False)`. `resolve_password(flag, env_name,
  prompt)` with chain → flag → env → `getpass.getpass(stream=sys.stderr)`,
  raises `PasswordResolutionError` on non-TTY + missing flag/env.
  `detect_shared_session(sessions)` checks `_SHARED_SESSION_COOKIE_NAMES`
  frozenset cookie equality, returns Optional[Finding]. `validate_auth_flags(args)`
  (called from Engine Phase 0.5 — Item 5 stub gets concrete body here).
  Acceptance: Per `prd.md > Epic 1 > Stories 1.1/1.2/1.3/1.4/1.5` +
  `spec.md > Phase 5 abort/continue table` — abort-barriers raise the
  right exception types, INFO finding from `detect_shared_session` doesn't
  abort.
  Verify: Unit-test the 3 private helpers in `_build_login_payload` against
  fixture HTML (CakePHP-shaped form with `_csrfToken` hidden field,
  Django-shaped with `csrfmiddlewaretoken`, Rails-shaped with
  `authenticity_token`) — assert hidden fields preserved verbatim.
  ```
  python -c "from webprobe.auth import resolve_password, PasswordResolutionError; import os; os.environ['TEST_PW'] = 'x'; assert resolve_password(None, 'TEST_PW', 'p') == 'x'; print('resolve OK')"
  ```
  Estimated time: 45 min (MUST SPLIT into 6a/6b)

- [x] **7. Engine Phase 5 wiring (auth setup) + Phase 3.5 / 3.6 / 3.7 testbed/risk-gate skeleton**
  Spec ref: `spec.md > Engine Phase Ordering > Phase 5 sub-phase
  abort/continue table` + Phase 3.5/3.6/3.7
  What to build: Engine `_phase_5a/5b/5c/5d/5e/5f` methods per spec. 5a
  calls `auth.resolve_password`, 5b `auth.setup_form_login` or
  `setup_cookie_session` for primary, 5c `auth.setup_baseline` for
  baseline, 5d `auth.detect_shared_session` (continue + INFO if shared),
  5e session-check probe (sha256 unauth vs primary, INFO if ambiguous,
  continue), 5f authed sitemap (deferred body — stub, real body lands
  with discovery.py at item 10). Phase 3.5 calls `filter.detect_testbed`,
  caches `self._is_testbed`. Phase 3.6 calls
  `filter.filter_modules_by_risk_gates`, stores `(kept, dropped)`. Phase
  3.7 calls `filter.render_risk_gate_banner` if dropped non-empty + not
  testbed + not all-excluded.
  Acceptance: Per spec.md Phase 5 abort/continue table — 5a/5b/5c/5f
  abort+sys.exit(1) on their named exceptions, 5d/5e continue + INFO.
  Engine catches `ConfigurationError` at top level, sys.exit(2). Testbed
  bypass returns `(modules, [])` from Phase 3.6.
  Verify:
  ```
  python -c "from webprobe.engine import Engine; from argparse import Namespace; ns = Namespace(json_out=None, auth_form=None, cookie=None, idor_baseline=None, idor_baseline_form=None); print('phase 5 skipped path importable OK')"
  ```
  Full auth flow validation deferred to Item 9 (first vertical slice fires
  through Phase 5 against testbed).
  Estimated time: 30 min

- [x] **8a. Testbed harness — stateless endpoints**
  Spec ref: `spec.md > Testbed (webprobe/testbed/)` + Phase 1 Q1 deepening
  amendment
  What to build: `webprobe/testbed/__main__.py` Flask app skeleton.
  Stateless endpoints (no session interaction):
    - `GET /__webprobe_testbed__/health` — 200 + JSON
      `{"webprobe_testbed": true, "testbed_version": "2.0.0"}` (Story 5.4
      detection — REQUIRED)
    - `GET /` — root response: missing security headers (no CSP, no HSTS,
      no X-Frame-Options) + body containing 2 `<form>` elements (POST
      `/csrf-broken` with `_csrfToken` hidden field per Gap 1; GET `""`
      empty action per Gap 9 for CakePHP edge case) + `<a href="?id=1">`
      seed for sqli/xss DYNAMIC source extraction. Set-Cookie:
      `PHPSESSID=...` without Secure, without HttpOnly, without SameSite
      (feeds v1 headers cookie audits)
    - `GET /server-info` — body contains internal IP + commented credential
      ("# DB password: testbed-leak-do-not-use", "Server: nginx/1.18,
      internal IP 10.0.0.5") for info_disclosure module
    - `GET /.htaccess` — 200 with Apache config text (paths
      `sensitive_path_exposed_high`)
    - `GET /cpanel` — 200 with cPanel-shape HTML (paths
      `sensitive_path_exposed_medium`)
    - `GET /reflect-xss?q=` — reflects q value unfiltered (xss
      `reflected_xss`)
    - `GET /vulnerable?q=` — concatenates q into SQL string with error
      message on quote injection (sqli `sqli_error_string`)
    - `GET /search?q=` — when q contains `'` or `"`, returns 500 + Python
      stack trace (`Traceback (most recent call last):` ... pattern matched
      by stack_trace_patterns.txt) for error_leakage
      `stack_trace_leakage`
    - `GET /file?name=` — when name contains `..`, returns synthetic
      `/etc/passwd` content (root:x:0:0:...) for traversal
      `path_traversal_unix`
  `webprobe/testbed/__init__.py` empty. `pyproject.toml` adds
  `[project.optional-dependencies] testbed = ["Flask>=3.0"]`.
  Acceptance: Per Phase 1 Q1 lock — testbed is complete acceptance fixture
  for ALL 12 modules. Stateless endpoints serve: filter.detect_testbed,
  headers (root response cookies + missing security headers),
  info_disclosure (root + /server-info), paths (.htaccess, cpanel,
  server-info), discovery (root forms + ?id= seed + empty-action edge),
  xss (/reflect-xss), sqli (/vulnerable), error_leakage stack trace
  (/search), traversal (/file).
  Verify: In one terminal: `pip install -e ".[testbed]"; python3 -m
  webprobe.testbed &`. In another:
  ```
  curl -s http://localhost:9999/__webprobe_testbed__/health | python -c "import sys, json; b = json.load(sys.stdin); assert b['webprobe_testbed'] is True; print('testbed health OK')"
  curl -s http://localhost:9999/ | grep -q "_csrfToken" && echo "csrf form OK"
  curl -s "http://localhost:9999/search?q='" | grep -q "Traceback" && echo "stack trace OK"
  curl -s "http://localhost:9999/file?name=../../../etc/passwd" | grep -q "root:x:0:0" && echo "traversal OK"
  ```
  Kill testbed: `kill %1`.
  Estimated time: 15 min

- [x] **8b. Testbed harness — stateful endpoints + custom session interface (Gap 5)**
  Spec ref: `spec.md > Testbed` + Phase 1 Q1 deepening Gap 5 lock
  What to build: Continued additions to `webprobe/testbed/__main__.py`.
  **Custom SessionInterface** for fixation fixture (Gap 5 (i) lock):
  ```python
  import secrets
  from flask.sessions import SessionInterface, SessionMixin

  _TESTBED_SESSIONS: dict[str, dict] = {}

  class FixationVulnerableSession(dict, SessionMixin):
      def __init__(self, sid: str, initial: dict = None):
          super().__init__(initial or {})
          self.sid = sid
          self.modified = False

  class FixationVulnerableSessionInterface(SessionInterface):
      """Deliberately broken: does NOT regenerate session ID on login.
      Real-world equivalent: server-side session store where developer
      forgets to rotate session ID on auth state transition."""

      def open_session(self, app, request):
          sid = request.cookies.get("PHPSESSID")
          if sid is None or sid not in _TESTBED_SESSIONS:
              sid = secrets.token_urlsafe(16)
              _TESTBED_SESSIONS[sid] = {}
          return FixationVulnerableSession(sid, _TESTBED_SESSIONS[sid])

      def save_session(self, app, session, response):
          if session.modified:
              _TESTBED_SESSIONS[session.sid] = dict(session)
          # Always set cookie to current sid — does NOT rotate on login (deliberate flaw)
          response.set_cookie("PHPSESSID", session.sid, httponly=False)

  app.session_interface = FixationVulnerableSessionInterface()
  ```
  This single SessionInterface implementation closes 3 module fixtures:
  session.session_fixation + headers.cookie_no_httponly + auth.detect_shared_session
  cookie name compatibility (PHPSESSID is in the frozenset).
  **Stateful endpoints** (use the session interface):
    - `POST /login` — `KNOWN_USERS = {"admin", "alice", "bob"}`. user=="admin"
      + non-empty pw → session["role"]="admin", 302 to `/`. user in
      KNOWN_USERS - {"admin"} + non-empty pw → session["role"]="user", 302
      to `/`. user NOT in KNOWN_USERS → 401 with body "Unknown user"
      (Gap 2: enables user-enum diff). empty user OR empty pw → 401 with
      body "Missing credentials". NO lockout (brute_force `no_lockout`
      target).
    - `POST /login-locked` — per-source-IP attempt counter, 5 attempts
      allowed. 6th returns 429 with body "Account temporarily locked due
      to too many failed attempts." (matches lockout_signals.txt entry —
      brute_force correct-lockout case).
    - `POST /logout` — Gap 4: returns 200 `{"status": "logged out"}` but
      does NOT call `session.clear()` — cookie remains valid for
      subsequent authed requests (session.session_persists_post_logout
      target).
    - `POST /csrf-broken` — accepts POST without CSRF token validation
      (csrf `csrf_missing` target).
    - `GET /admin/` — when `session.get("role") == "admin"` → 200 with
      admin-signal HTML containing "All Users" (matches admin_signals.txt
      entry — access_control `role_violation` target). Otherwise → 403.
    - `GET /idor/<int:id>` — returns same body
      `{"id": <id>, "data": "resource-<id>-data"}` for ANY authenticated
      session (Gap-implicit per spec: cross-session sha256 match enables
      idor `cross_account_leak`).
  `if __name__ == "__main__": app.run(host="127.0.0.1", port=9999, debug=False)`.
  Acceptance: Per Phase 1 Q1 Gap 5 (i) lock — FixationVulnerableSessionInterface
  exposes real fixation mechanism (session ID stable across login
  transition). Stateful endpoints serve: access_control, csrf, idor,
  error_leakage user enum (KNOWN_USERS routing), session (post-logout
  + fixation + logout URL discovery), brute_force (both no-lockout and
  correct-lockout cases). Cookie name PHPSESSID matches
  _SHARED_SESSION_COOKIE_NAMES frozenset (cross-cutting (γ) lock).
  Verify (testbed must be running from item 8a):
  ```
  curl -s -c cookies.txt -X POST -d "user=admin&password=x" http://localhost:9999/login -i | grep -E "(302|PHPSESSID)" && echo "login admin OK"
  curl -s -c cookies-bad.txt -X POST -d "user=nonexistent_xyz@test.invalid&password=x" http://localhost:9999/login | grep -q "Unknown user" && echo "user enum diff OK"
  curl -s -b cookies.txt http://localhost:9999/admin/ | grep -q "All Users" && echo "admin role-gated OK"
  for i in $(seq 1 6); do curl -s -X POST -d "user=x&password=$i" http://localhost:9999/login-locked -o /dev/null -w "%{http_code} "; done; echo
  # Expected: 401 401 401 401 401 429
  ```
  Estimated time: 30 min

- [x] **9. First vertical slice — `access_control` end-to-end with debug-print instrumentation**
  Spec ref: `spec.md > Detection Modules > access_control.py` + `prd.md >
  Epic 7 > Story 7.1` + Phase 1 Q1 debug-print refinement
  What to build: `webprobe/modules/access_control.py` per spec — `@register`
  class with `name="access_control"`, `auth_strategy="auth_required"`,
  `source_filter=ALL_SOURCES`, `FIT3048_CATEGORY_MAP={"role_violation": 2,
  "ambiguous_200_summary": 2}`, `DATA_FILES=frozenset({"admin_paths.txt",
  "admin_signals.txt"})`. `webprobe/data/access_control/admin_paths.txt`
  with default contents (`/admin/`, `/admin/users`, `/backoffice/`,
  `/cpanel/`, `/manage/`, `/console/`).
  `webprobe/data/access_control/admin_signals.txt` multi-language defaults
  per spec.E1 (English: "All Users", "Admin Dashboard", "All Messages",
  etc. + Chinese "管理后台"). `run()` body using `_common.send(url,
  session=s)` for each candidate path; signal match → HIGH role_violation
  Finding; ambiguous 200s collected → end-of-run INFO ambiguous_200_summary.
  `webprobe/modules/__init__.py` imports access_control (triggers
  `@register`). **Q1 debug-print instrumentation**: insert in
  `Engine._make_report_finding` wrapper AFTER injection (auth_context /
  seen_in / fit3048_category set), BEFORE `self._findings.append(f)`:
  ```python
  # TEMP — Q1 debug-print verification artifact, removed at Item 13 when json_render lands
  print(json.dumps(asdict(f), indent=2), file=self._terminal_stream)
  ```
  Lock 5 preserved (debug-print is engine wrapper code, NOT module body
  code).
  Acceptance: Per `prd.md > Epic 7 > Story 7.1` + Q1 — running webprobe
  against testbed `/admin/` with `--auth-user admin` produces HIGH
  `role_violation` Finding with `auth_context="as admin"`,
  `seen_in=["authed"]`, `fit3048_category=2`, `evidence_hash` 16 chars,
  `baseline_context=None`, `payload=None`. Debug-print emits valid JSON
  parse-able by `python -m json.tool`.
  Verify (testbed running from item 8b):
  ```
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --include-modules access_control 2>&1 | tee item9-output.txt
  grep -q '"role_violation"' item9-output.txt && echo "role_violation finding OK"
  grep -q '"auth_context": "as admin"' item9-output.txt && echo "auth_context injected OK"
  grep -q '"fit3048_category": 2' item9-output.txt && echo "fit3048_category injected OK"
  grep -E '"evidence_hash": "[a-f0-9]{16}"' item9-output.txt && echo "evidence_hash 16-char OK"
  ```
  Estimated time: 30 min

  **═══════════════ CHECKPOINT B — First vertical slice end-to-end ═══════════════**
  Boundary: access_control fires through engine wrapper against testbed
  with auth_context / seen_in / fit3048_category injected correctly.
  Roughly: after item 9 (renumbering-robust anchor: "after first vertical
  slice fires end-to-end against testbed").
  **Heaviness: HEAVY — most important gate of Sprint 2.**
  **Dual role:**
  - **Role 1 — Integration acceptance.** Inspect debug-print JSON from
    Item 9 verify output. Validate Module Contract types correct (kw_only
    fields all present, optional fields nullable as expected); engine
    wrapper injection working (auth_context format, seen_in list shape,
    fit3048_category lookup); `evidence_hash` `__post_init__` correct
    (16-char sha256 over `category:url:evidence`).
  - **Role 2 — Hour budget review (P1 cut decision point).** Compute
    actual hours spent on items 1-9 vs proportional estimate (9/23 of
    revised 24-32 hr budget = ~9.4-12.5 hr expected; lower-bound
    proportion of 18.0 hr is ~7 hr).
    - If actual ≤ expected × 1.5 → continue full scope.
    - If actual > expected × 1.5 → trigger P1 cut: drop items 17/18/19
      (error_leakage / session / brute_force) from items 11-19. Sprint 2
      contracts from 23 items to 20 items, hour budget recovers. P1 cut
      decision needs empirical evidence (actual hour data), not
      Sprint-start guesswork; Checkpoint B is the first point with enough
      data to extrapolate AND the latest safe point to cut (items 17-19
      not yet started, no work wasted by cutting). After Checkpoint B,
      P1 cuts mean throwing away completed work — defeats cost-saving
      intent.

- [x] **10. `discovery.py` (Epic 2 — sitemap + robots + url_list + dynamic + curated + dedup + freeze)** — MUST SPLIT (10a sitemap + robots + Result dataclasses, 10b url_list + dynamic + curated + _dedup_by_priority + Engine Phase 4 wiring + Phase 5f authed-sitemap)
  Spec ref: `spec.md > Discovery (Epic 2)` + Engine Phase 4 + 5f
  What to build: `webprobe/discovery.py` per spec — `discover_sitemap`
  (returns `SitemapDiscoveryResult` with cap=500 + advertised-via-robots
  flag, raises `SitemapDiscoveryError` on malformed XML or auth-gated),
  `discover_robots` (custom parser ~25 lines, `RobotsDiscoveryResult` with
  `wildcard_intents` + `sitemap_url_advertised`), `discover_url_list_pairs`,
  `discover_dynamic_pairs` (same-origin from base_response HTML;
  `<form action="">` adds target.url per CakePHP edge case from Phase 1
  Q1 Gap 9), `discover_curated_pairs` (loads
  `webprobe/data/paths/curated.txt` + `CAKEPHP_PATHS` from profiles.py —
  v1→v2 architectural shift: paths.py NO LONGER loads curated.txt
  internally), `_dedup_by_priority` with `_SOURCE_PRIORITY` per Story
  2.4.E1 lock, `_canonicalize_url` (dedup-key only, no query
  normalization). `validate_discovery_flags` for Phase 0.5.
  `resolve_url_pool(args, target, sessions=None)` composes all enabled
  sources → dedup → freeze → tuple. Engine `_phase_4` wires it; `_phase_5f`
  re-dedups when authed sitemap arrives. Verify also: `webprobe/data/
  paths/curated.txt` already exists from v1 — confirm engine-load works
  against existing file. **DATA_FILES auto-load full integration test**
  (deferred from Item 4) lands here implicitly via curated.txt loading.
  Acceptance: Per `prd.md > Epic 2 > Stories 2.1-2.5` + spec.md Source
  priority lock — `url_list > robots > curated > sitemap > dynamic`,
  off-host filtered silently, sitemap cap=500 with INFO on overflow,
  malformed XML fails loud per Story 2.1.
  Verify:
  ```
  # Against testbed (no sitemap.xml, no robots.txt — both 404 silent skip):
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any 2>&1 | grep "URLs probed"
  # Expected: "URLs probed: N (0 sitemap, 0 robots, 0 url-list, X dynamic, Y curated)"

  # Source priority dedup unit:
  python -c "from webprobe.discovery import _dedup_by_priority, _SOURCE_PRIORITY; from webprobe.findings import Source; pairs = [('/admin/', Source.SITEMAP), ('/admin/', Source.ROBOTS)]; assert _dedup_by_priority(pairs)[0][1] == Source.ROBOTS; print('dedup priority OK')"

  # Empty-action form edge case:
  curl -s http://localhost:9999/ | grep -q 'action=""' && echo "empty action form present in testbed OK"
  # Confirm dynamic source extraction adds target.url for empty-action form (verified in Item 14 banner output)
  ```
  Estimated time: 45 min (MUST SPLIT into 10a/10b)

- [x] **11. `terminal.py` output (banner + COVERAGE block + FINDINGS + summary + inline tease)** — MUST SPLIT (11a banner + COVERAGE block + inline tease, 11b FINDINGS + summary)
  Spec ref: `spec.md > Output (Epic 3) > ScanCoverage` + `prd.md > Epic 3
  > Stories 3.1/3.2/3.5`
  What to build: `webprobe/output/terminal.py` upgrade per spec.
  `render_banner(args, target)` per skeleton lock (auth-mode line
  conditional, profile line conditional). `render_scan_coverage(coverage)`
  per Story 3.1 line order (Mode / Sessions / URLs probed / Modules fired
  / Login probe / Session check / Logout test / Per-module source filter
  / Wildcard intents / Duration). `render_findings(findings, args)` per
  Story 3.2 with severity grouping default + `Probed:` line conditional
  on `auth_context != None`. `render_summary(metadata, sink_paths)` per
  Story 3.5. `render_inline_tease(f, args, stream)` for engine wrapper.
  Marker convention (`[*]/[+]/[-]/[!]/[SEVERITY]`) preserved from v1.
  `_terminal_stream` parameter passed through (Lock 6: NEVER bare `print()`
  in renderer code).
  Acceptance: Per `prd.md > Epic 3 > Stories 3.1/3.2/3.5` — Mode enum
  exactly 4 values, COVERAGE always renders even on Unauthenticated (no
  auth-phase lines, source breakdown still present), FINDINGS count line
  includes zeros (`[CRITICAL × 0]` not omitted).
  Verify:
  ```
  python -c "
  from webprobe.coverage import ScanCoverage
  from webprobe.output.terminal import render_scan_coverage
  c = ScanCoverage(mode='Unauthenticated', sessions=[],
                   urls_probed={'total': 5, 'by_source': {'sitemap': 0, 'robots': 0, 'url_list': 0, 'dynamic': 5, 'curated': 0}},
                   modules_fired={'scheduled': 5, 'completed': 5, 'errored': 0},
                   duration_seconds=2.1)
  out = render_scan_coverage(c)
  assert 'Mode: Unauthenticated' in out
  assert 'URLs probed: 5 (0 sitemap, 0 robots, 0 url-list, 5 dynamic, 0 curated)' in out
  assert 'Login probe:' not in out  # auth-phase line absent
  print(out)
  print('terminal COVERAGE block OK')
  "
  ```
  Estimated time: 45 min (MUST SPLIT into 11a/11b)

- [x] **12. `html.py` output (auth-context badge + IDOR conditional + OPERATIONAL_RISK chip + FIT3048 grouping)** — MUST SPLIT (12a structure + auth-badge + IDOR conditional, 12b OPERATIONAL_RISK chip + FIT3048 two-level grouping + Sprint 1 clipboard preservation)
  Spec ref: `spec.md > Output > HTML report v2 structure` + `prd.md > Epic
  3 > Story 3.3`
  What to build: `webprobe/output/html.py` upgrade per spec. `<article>` +
  `<header>` + `<dl>` semantic per finding. `OPERATIONAL_RISK` chip in
  `<header class="report-header">` ABOVE SCAN COVERAGE
  (screenshot-readable). Auth-context badge (only when `auth_context !=
  None`, color WHITE/GREY informational). IDOR-conditional render for
  `Baseline:` + `Sessions:` rows (single Python expression `if
  finding.category == "idor" and finding.baseline_context is not None`,
  lives in EXACTLY 2 places: terminal.py and html.py — grep verifies).
  FIT3048 two-level grouping when `--fit3048`: outer FIT3048 category,
  inner severity, both empty-category messages (no findings vs filtered-out).
  Sprint 1 clipboard fragility preserved: `<a>` + `<button>` direct DOM
  siblings, `<!-- DO NOT WRAP — clipboard JS depends on
  previousElementSibling -->` comment.
  Acceptance: Per `prd.md > Epic 3 > Story 3.3` + spec.md HTML rendering
  — manual `file://` test in Firefox AND Chrome, OPERATIONAL_RISK chip
  visible above COVERAGE, auth-badge renders only when populated, IDOR
  Sessions row only when category=='idor' AND baseline_context!=None,
  copy button works on a finding URL.
  Verify:
  ```
  # Generate fixture report from a 5-finding hand-built list:
  python -c "
  from webprobe.findings import Finding
  from webprobe.coverage import ScanCoverage, ScanMetadata
  from webprobe.output.html import render_html
  findings = [
      Finding(severity='HIGH', category='idor', finding_type='cross_account_leak',
              name='IDOR — Coach A can read Coach B', url='https://t.com/p/47',
              evidence='sha256 match', remediation='ownership check',
              auth_context='as coach_a', baseline_context='baseline coach_b owns id=47',
              fit3048_category=2, seen_in=['authed']),
      Finding(severity='HIGH', category='access_control', finding_type='role_violation',
              name='admin reachable', url='https://t.com/admin/', evidence='200',
              remediation='role check', auth_context='as coach_a',
              fit3048_category=2, seen_in=['authed']),
      Finding(severity='MEDIUM', category='headers', finding_type='missing_csp',
              name='no CSP', url='https://t.com/', evidence='no header',
              remediation='add CSP', fit3048_category=4, seen_in=['unauth']),
  ]
  # ... build coverage + metadata, render, write to /tmp/test.html
  "
  open /tmp/test.html  # manual click-Copy verification

  # Grep verification — IDOR conditional in EXACTLY 2 locations:
  test "$(grep -rn "category == .idor." webprobe/output/ | wc -l)" -eq 2 && echo "IDOR conditional single-source-of-truth OK"
  ```
  Estimated time: 60 min (MUST SPLIT into 12a/12b)

- [x] **13. `txt.py` + `json_render.py` + remove debug-print from Item 9**
  Spec ref: `spec.md > Output > JSON envelope — Story 3.4` + Phase 1 Q1
  debug-print removal
  What to build: `webprobe/output/txt.py` ANSI-stripped variant of
  terminal.py output (re-uses render functions with
  `colorama.init(strip=True)` shim or post-process ANSI strip).
  `webprobe/output/json_render.py` per spec — versioned envelope with
  `version: "2.0"`, `tool`, `scan` (asdict ScanMetadata), `scan_coverage`
  (asdict ScanCoverage), `findings` (per-finding `_finding_to_dict` with
  optional-fields-always-present rule, null when absent never omitted).
  `ensure_ascii=False` for unicode (Mandarin/Japanese lockout signals).
  Engine Phase 7 dedup: `(category, url, evidence_hash)` identity tuple
  (dedup tuple precision vs minimalism deferred per Phase 1 Q5 Q4 — /build
  may simplify to `(category, evidence_hash)`; /reflect evaluates),
  mutates `self._findings` in place, merges `seen_in: ["unauth", "authed"]`
  for matched pairs. **REMOVE the debug-print line added in Item 9** from
  `Engine._make_report_finding`. `webprobe/output/__init__.py` exports all
  4 `render_*` functions per spec uniform signature.
  Acceptance: Per `prd.md > Epic 3 > Story 3.4` — semver MINOR rules
  (consumers ignore unknown fields), every optional field present as
  `null` when absent (never omitted), `--scan-both` dedup correct.
  Removal of debug-print preserves Lock 5 (zero `print()` in module bodies
  still holds — debug-print was in engine wrapper).
  Verify:
  ```
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --json-out - 2>/dev/null | python -m json.tool > /dev/null && echo "JSON parse OK"

  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --json-out - 2>/dev/null | python -c "import sys, json; e = json.load(sys.stdin); assert e['version'] == '2.0'; assert 'scan_coverage' in e; for f in e['findings']: assert 'auth_context' in f and 'baseline_context' in f; print('envelope shape OK')"

  # Confirm debug-print removal — Lock 5 preserved:
  grep -n "TEMP" webprobe/engine.py && echo "FAIL: debug-print not removed" || echo "debug-print removed OK"
  ```
  Estimated time: 30 min

- [x] **14. `filter.py` (module filtering + risk gates + testbed detection + i-own-this-target validation + banner)** — MUST SPLIT (14a validate_module_flags + parse_module_list + Levenshtein, 14b detect_testbed + filter_modules_by_risk_gates + render_risk_gate_banner + validate_i_own_this_target)
  Spec ref: `spec.md > Filtering & Risk Gates (Epic 4+5)` + `prd.md >
  Epic 4 + Epic 5`
  What to build: `webprobe/filter.py` per spec. `validate_module_flags`
  (mutex `--include-modules` / `--exclude-modules`, Levenshtein-like
  suggestion case-insensitive with case-sensitive note hint, lists ALL
  missing gate flags at once per spec extends-actionable-error pattern).
  `parse_module_list` (whitespace-tolerant). `filter_modules_by_user_flags`.
  `detect_testbed` per Story 5.4.E1 (probe `/__webprobe_testbed__/health`,
  validate 200 + Content-Type application/json + body
  `webprobe_testbed: true`, single attempt no retry).
  `_matches_testbed_url_pattern` (deterministic netloc check
  `localhost:9999`/`127.0.0.1:9999`). `filter_modules_by_risk_gates` per
  `_GATED_DOUBLE = {"brute_force"}` and `_GATED_SINGLE = {"access_control",
  "idor", "csrf"}` with testbed bypass returning `(modules, [])`.
  `render_risk_gate_banner` with box-drawing frame (`═` × 60), suppressed
  on testbed or when all gated excluded. `validate_i_own_this_target` per
  Story 5.5 + spec edge case lock (rejects URL path/query in assertion
  shape, hostname comparison case-insensitive, port-agnostic when omitted
  from flag).
  Acceptance: Per `prd.md > Epic 4 + 5` + spec.md testbed/validation truth
  table — testbed bypass replaces risk gates NOT hostname validation
  (orthogonal mechanisms), `--i-own-this-target` rejects `https://host/path`
  shape, multi-error gate-validation lists all missing at once.
  Verify:
  ```
  # Path/query rejection in assertion:
  webprobe https://example.com --i-own-this-target=https://example.com/admin 2>&1 | grep -q "contains URL path/query" && echo "path rejection OK"

  # Testbed bypass — banner suppressed:
  webprobe http://localhost:9999 2>&1 | grep -v "Risk-gated modules disabled" >/dev/null && echo "testbed banner suppressed OK"

  # Levenshtein suggestion:
  webprobe http://localhost:9999 --include-modules xrr 2>&1 | grep -q "Did you mean 'xss'" && echo "Levenshtein suggestion OK"
  ```
  Estimated time: 45 min (MUST SPLIT into 14a/14b)

  **═══════════════ CHECKPOINT C — Framework epics complete ═══════════════**
  Boundary: discovery + output + filter+gates all working; full pipeline
  runs against testbed with finding emission + terminal COVERAGE block +
  HTML report + JSON envelope; risk-gate banner emits correctly when
  `--i-own-this-target` absent.
  Roughly: after item 14 (renumbering-robust anchor: "after framework
  epics complete").
  Verification: end-to-end against testbed produces all 4 output formats
  (terminal output, HTML at `webprobe_localhost_9999_<ts>.html`, TXT at
  `webprobe_localhost_9999_<ts>.txt`, JSON at `webprobe_localhost_9999_<ts>.json`);
  `--json-out -` routes to stderr correctly (scan progress on stderr,
  JSON clean on stdout); banner appears on terminal but not in HTML/TXT/
  JSON reports.
  Heaviness: medium.

- [x] **15. `idor` module**
  Spec ref: `spec.md > idor.py` + `prd.md > Epic 7 > Story 7.2`
  What to build: `webprobe/modules/idor.py` per spec. `@register` class,
  `name="idor"`, `auth_strategy="auth_required"`, `source_filter=ALL_SOURCES`,
  `FIT3048_CATEGORY_MAP={"cross_account_leak": 2, "idor_baseline_missing":
  2, "uuid_not_supported": 2}`. `run()` checks `len(sessions) < 2` → INFO
  `idor_baseline_missing` + return. UUID-shaped paths in candidates →
  INFO `uuid_not_supported` (per Story 7.2.E2 honest banner). For each
  candidate matching `_id_bearing` patterns (`/<resource>/<id>`,
  `/<resource>/view/<id>`, `?id=N`, `?<resource>_id=N`): `send` from both
  sessions, `compare_responses` true + both 200 → HIGH `cross_account_leak`
  with `baseline_context=f"baseline owns id={baseline_id}"`. Module-set
  `baseline_context` (engine never auto-injects). Helpers (`_id_bearing`,
  `_uuid_in`, `_extract_resource_id`, `_fix_hint_idor`) extracted to
  `_idor_helpers.py` IF AND ONLY IF module body exceeds 50 lines after
  run() implementation. Module body single-pass write first; helper
  extraction reactive on cap violation. Estimated likely-extraction
  (informational reference, not commitment): idor likely fits cap.
  Acceptance: Per `prd.md > Epic 7 > Story 7.2` + spec.md ID enumeration
  scope lock — probe-only-discovered (no synthesis of ID range),
  integer-ID only (UUID detection deferred + honest INFO banner).
  Verify (testbed running):
  ```
  # Need dual-session form-login. Use testbed users admin + alice:
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --idor-baseline-form http://localhost:9999/login --idor-baseline-user alice --idor-baseline-pass any --include-modules idor --url-list <(echo "/idor/1") 2>&1 | grep -q "cross_account_leak" && echo "IDOR finding OK"
  wc -l webprobe/modules/idor.py | awk '{print $1}' | xargs -I{} test {} -le 50 && echo "≤50 lines OK"
  ```
  Estimated time: 30 min

- [x] **16. `csrf` module**
  Spec ref: `spec.md > csrf.py` + `prd.md > Epic 7 > Story 7.3`
  What to build: `webprobe/modules/csrf.py` per spec. `@register`,
  `name="csrf"`, `auth_strategy="auth_required"`, `FIT3048_CATEGORY_MAP=
  {"csrf_missing": 2, "csrf_indeterminate": 2}`. **Risk-gated per Story
  5.2** (Epic 5 validation in Item 14 already enforces; module body
  assumes auth phase succeeded). `run()` iterates `target.forms` filtered
  to `method=="POST"` + on-host action; constructs payload with ALL
  `<input type="hidden">` stripped + other fields filled with placeholders
  (`webprobe-csrf-test`, `webprobe@test.invalid`, `1`); POST with primary
  session, `allow_redirects=False`; 403/419 → no finding (Laravel CSRF
  mismatch=419), 200/302/204 → HIGH `csrf_missing`, other 4xx → INFO
  `csrf_indeterminate`. Skip GET-only forms, off-host action URLs. Rails
  `_method` override caveat documented per Story 7.3.E2 lock.
  Acceptance: Per `prd.md > Epic 7 > Story 7.3` — `wc -l webprobe/modules/
  csrf.py` ≤ 50, hidden-field stripping verified against testbed root
  form's `_csrfToken` hidden input.
  Verify (testbed running):
  ```
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --i-own-this-target=localhost --include-modules csrf 2>&1 | grep -q "csrf_missing" && echo "csrf_missing finding OK"
  wc -l webprobe/modules/csrf.py | awk '{print $1}' | xargs -I{} test {} -le 50 && echo "≤50 lines OK"
  ```
  Estimated time: 25 min

- [x] **17. `error_leakage` module — P1 CUT TARGET** — MUST SPLIT (17a user enumeration probe, 17b stack-trace own probe set + pattern matching)
  Spec ref: `spec.md > error_leakage.py` + `prd.md > Epic 7 > Story 7.4`
  What to build: `webprobe/modules/error_leakage.py` per spec. `@register`,
  `FIT3048_CATEGORY_MAP={"username_enumeration_login": 7, "stack_trace_leakage":
  1}`, `DATA_FILES={"stack_trace_patterns.txt"}`. **Phase 1 — user
  enumeration**: 2 POSTs to `--auth-form` URL (probe A: real user + wrong
  pw, probe B: nonexistent user + wrong pw); diff status/redirect URL/body
  sha256/error message → HIGH `username_enumeration_login`. **Phase 2 —
  stack trace own probe set** per Story 7.4.E1: `GET /`, `GET <auth-form-url>`,
  `GET /admin/__webprobe_404_trigger__`, `GET /?id='%20OR%201=1`,
  `GET /search?q='` (testbed has /search per Item 8a Gap 3 fix); pattern
  match against `stack_trace_patterns.txt` (PHP / Python / Ruby / Java /
  generic) → MEDIUM `stack_trace_leakage` with first 200 chars of matched
  trace as evidence. `webprobe/data/error_leakage/stack_trace_patterns.txt`
  per spec defaults. Helpers (`_probe_user_enumeration`, `_build_probe_set`,
  `_match_stack_trace`) extracted to `_error_leakage_helpers.py` IF AND
  ONLY IF module body exceeds 50 lines after run() implementation. Module
  body single-pass write first; helper extraction reactive on cap
  violation. Estimated likely-extraction (informational reference, not
  commitment): error_leakage likely needs helpers (multi-phase probe +
  pattern matching).
  Acceptance: Per `prd.md > Epic 7 > Story 7.4` — module fires
  `username_enumeration_login` against testbed `/login` (KNOWN_USERS
  routing per Item 8b Gap 2 enables differential response) AND
  `stack_trace_leakage` against testbed `/search?q='` (returns 500 +
  Python stack trace per Item 8a Gap 3).
  Verify (testbed running):
  ```
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass wrong --i-own-this-target=localhost --include-modules error_leakage 2>&1 | tee item17-output.txt
  grep -q "username_enumeration_login" item17-output.txt && echo "user enum finding OK"
  grep -q "stack_trace_leakage" item17-output.txt && echo "stack trace finding OK"
  ```
  Estimated time: 45 min (MUST SPLIT into 17a/17b)

- [x] **18. `session` module — P1 CUT TARGET** — MUST SPLIT (18a post-logout cookie replay, 18b session fixation + logout URL discovery)
  Spec ref: `spec.md > session.py` + `prd.md > Epic 7 > Story 7.5`
  What to build: `webprobe/modules/session.py` per spec. `@register`,
  `FIT3048_CATEGORY_MAP` with 4 keys (`session_persists_post_logout`,
  `session_fixation`, `session_skipped_cookie_mode`, `logout_endpoint_not_found`).
  **Skip with INFO** when `args.auth_form` is None (cookie-mode →
  ephemeral sub-session impossible, per Story 1.4.E1 lock). **Phase 1 —
  post-logout cookie replay**: `auth.ephemeral_login_form()` → GET protected
  URL X → POST logout → GET X → if similar-shape (sha256 match OR both
  200 with overlap signals) → HIGH `session_persists_post_logout`. **Phase 2
  — session fixation**: pre-login GET login URL anonymously, capture
  Set-Cookie, login with that cookie attached, post-login compare session
  cookie value → MEDIUM `session_fixation` if same. Logout URL discovery
  via heuristic patterns (`/logout`, `/signout`, `/users/logout`,
  `/sessions/destroy`); none found → INFO `logout_endpoint_not_found`.
  Helpers (`_test_post_logout`, `_test_session_fixation`, `_find_logout_url`)
  extracted to `_session_helpers.py` IF AND ONLY IF module body exceeds 50
  lines after run() implementation. Estimated likely-extraction (informational
  reference, not commitment): session likely needs helpers (logout
  discovery + fixation logic).
  Acceptance: Per `prd.md > Epic 7 > Story 7.5` — throwaway sub-session
  preserves primary `sessions[0]` and baseline `sessions[1]` integrity.
  Item 8b's FixationVulnerableSessionInterface enables both findings to
  fire (Gap 4 + Gap 5).
  Verify (testbed running):
  ```
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --i-own-this-target=localhost --include-modules session 2>&1 | tee item18-output.txt
  grep -q "session_persists_post_logout" item18-output.txt && echo "post-logout replay finding OK"
  grep -q "session_fixation" item18-output.txt && echo "fixation finding OK"
  ```
  Estimated time: 45 min (MUST SPLIT into 18a/18b)

- [x] **19. `brute_force` module — P1 CUT TARGET**
  Spec ref: `spec.md > brute_force.py` + `prd.md > Epic 7 > Story 7.6`
  What to build: `webprobe/modules/brute_force.py` per spec. `@register`,
  `FIT3048_CATEGORY_MAP={"no_lockout": 7, "weak_lockout": 7}`,
  `DATA_FILES={"lockout_signals.txt"}`. **Risk-gated per Story 5.1**
  (testbed-default; non-testbed requires `--include-brute-force` AND
  `--i-own-this-target=<host>`; Epic 5 validation in Item 14 already
  enforces). 6 POST attempts with `--auth-user` + `wrong_password_<i>`,
  1-second sleep between attempts. Detection: all 6 identical → MEDIUM
  `no_lockout`; response 6 contains lockout signal from
  `lockout_signals.txt` → no finding (correct); 1-5 vary but no clear
  lockout signal → INFO `weak_lockout`. `webprobe/data/brute_force/
  lockout_signals.txt` multi-language defaults per spec (English +
  Chinese + Japanese).
  Acceptance: Per `prd.md > Epic 7 > Story 7.6` — module fires `no_lockout`
  against testbed `/login` (no lockout) and emits no finding (correct
  behavior) against testbed `/login-locked` (5-attempt lockout). 6-attempt
  cycle = 6 × 1s sleep = 6s acceptable.
  Verify (testbed running):
  ```
  # Against /login (no lockout) → expect no_lockout finding:
  time webprobe http://localhost:9999 --auth-form http://localhost:9999/login --auth-user admin --auth-pass any --include-modules brute_force 2>&1 | grep -q "no_lockout" && echo "no_lockout finding OK"

  # Against /login-locked (5-attempt lockout) → expect no finding:
  webprobe http://localhost:9999 --auth-form http://localhost:9999/login-locked --auth-user admin --auth-pass any --include-modules brute_force 2>&1 | grep -q "no_lockout" && echo "FAIL: lockout signal not detected" || echo "correct lockout detected (no finding) OK"

  wc -l webprobe/modules/brute_force.py | awk '{print $1}' | xargs -I{} test {} -le 50 && echo "≤50 lines OK"
  ```
  Estimated time: 30 min

  **═══════════════ CHECKPOINT D — All 6 new v2 detection modules complete ═══════════════**
  Boundary: full v2 detection capability (access_control + idor + csrf +
  error_leakage + session + brute_force, OR access_control + idor + csrf
  if P1 cut triggered at Checkpoint B).
  Roughly: after item 19 (renumbering-robust anchor: "after all 6 new v2
  detection modules complete") OR after item 16 if P1 cut.
  Verification: each module fires expected finding type against testbed;
  cross-module ambiguous_200 / INFO findings emit correctly; IDOR-conditional
  render appears in EXACTLY 2 locations
  (`grep -rn "category == .idor." webprobe/output/ | wc -l` returns 2).
  Heaviness: medium.

- [x] **20. v1 retrofit pair — `headers` + `info_disclosure`**
  Spec ref: `spec.md > v1 module retrofit checklist` (9 steps × 6 modules)
  What to build: Apply 9-step retrofit to both modules:
    1. Add `auth_strategy = "follow"`
    2. Add `FIT3048_CATEGORY_MAP` with v1 internal type slugs (`missing_csp`,
       `missing_hsts`, `missing_x_frame_options`, `cookie_no_secure`,
       `cookie_no_httponly`, `cookie_no_samesite` for headers; `email_in_html`,
       `internal_ip_in_html`, `comment_with_credential`, `meta_generator`
       for info_disclosure)
    3. Replace `Finding(..., fit3048_category=N, ...)` with
       `Finding(..., finding_type="<slug>", ...)`
    4. Drop `return module_findings` from end of `run()`
    5. `source_filter = ALL_SOURCES` (default — no override needed)
    6. `_common.send` callers unchanged (these don't use `inject_param`)
    7. Add `@register` decorator at class definition
    8. Verify `wc -l ≤ 50`
    9. **Audit + REMOVE all `print()` calls in module body** (Lock 5
       enforcement)
  Acceptance: Per `prd.md > Epic 7 (E)` + `spec.md > Lock 5` — retrofit
  preserves v1 detection behavior (same findings produced for same inputs),
  zero `print()` in module body, ≤ 50 lines. Tier 3 v1 acceptance
  reproduction always available via testbed deliberate-flaw root response
  (Item 8a missing security headers + cookies without Secure/HttpOnly/
  SameSite from Item 8b PHPSESSID cookie).
  Verify:
  ```
  # Tier 3 acceptance: testbed root produces expected v1 findings:
  webprobe http://localhost:9999 --include-modules headers,info-disclosure 2>&1 | tee item20-output.txt
  grep -q "missing_csp" item20-output.txt && echo "headers retrofit OK"
  grep -q "cookie_no_httponly" item20-output.txt && echo "cookie audit OK (PHPSESSID with httponly=False)"

  wc -l webprobe/modules/headers.py webprobe/modules/info_disclosure.py
  # Both must be ≤ 50

  grep -n "print(" webprobe/modules/headers.py webprobe/modules/info_disclosure.py
  # Must return nothing
  ```
  Estimated time: 30 min

- [x] **21. v1 retrofit pair — `paths` (with curated.txt move) + `traversal`**
  Spec ref: `spec.md > v1 module retrofit checklist` + `spec.md > Curated
  discovery — v1→v2 architectural shift`
  What to build: **paths.py specifically** (heavy retrofit due to v1→v2
  curated-paths shift):
    - Drop `load_default_paths()` call
    - Drop `path_list=` kwarg in `__init__`
    - Iterate `target.urls` filtered to `source_filter = frozenset({Source.CURATED,
      Source.ROBOTS, Source.URL_LIST})` instead of internal path list
    - Declare `auth_strategy = "unauth_always"`
    - Slugs: `sensitive_path_exposed_high`, `sensitive_path_exposed_medium`,
      `sensitive_path_exposed_low` (3 severity tiers from one algorithm)
    - Helper file `_paths_helpers.py` likely shrinks
  **traversal.py** (mechanical retrofit):
    - Declare `auth_strategy = "follow"`
    - `source_filter = ALL_SOURCES` (default)
    - Slugs: `path_traversal_unix`, `path_traversal_windows`
    - Replace `from ._common import send` callers with `inject_param`
  Both apply 9-step retrofit + Lock 5 audit. Pairing balances heavy
  (paths) + light (traversal) within the item.
  Acceptance: Per spec.md curated-paths-shift + Epic 7 (E) — paths.py
  becomes contract-uniform (no internal path-loading logic), curated.txt
  now loaded by engine Phase 4 (Item 10), URL pool dedup applies.
  Verify:
  ```
  grep -n "load_default_paths\|path_list" webprobe/modules/paths.py
  # Must return nothing

  wc -l webprobe/modules/paths.py webprobe/modules/traversal.py
  # Both ≤ 50

  # Tier 3 acceptance: testbed sensitive paths fire:
  webprobe http://localhost:9999 --include-modules paths 2>&1 | tee item21-output.txt
  grep -q "sensitive_path_exposed" item21-output.txt && echo "paths retrofit OK (catches /.htaccess /cpanel from testbed)"

  # Tier 3 acceptance: testbed traversal fires:
  webprobe http://localhost:9999 --include-modules traversal 2>&1 | grep -q "path_traversal" && echo "traversal retrofit OK"

  grep -n "print(" webprobe/modules/paths.py webprobe/modules/traversal.py
  # Must return nothing
  ```
  Estimated time: 30 min

- [ ] **22. v1 retrofit pair — `sqli` + `xss`**
  Spec ref: `spec.md > v1 module retrofit checklist`
  What to build: **sqli.py:**
    - Declare `auth_strategy = "follow"`
    - `source_filter = frozenset({Source.DYNAMIC, Source.URL_LIST})`
    - Slugs: `sqli_error_string`, `sqli_boolean_diff`
    - Replace `from ._common import send` callers with `inject_param`
  **xss.py:**
    - Declare `auth_strategy = "follow"`
    - `source_filter = frozenset({Source.DYNAMIC, Source.URL_LIST, Source.CURATED})`
    - Slugs: `reflected_xss`, `stored_xss_candidate`
    - Replace `send` callers with `inject_param`
  Both apply 9-step retrofit + Lock 5 audit. **Final Lock 5 sweep across
  ALL 12 modules** at this item's verify step.
  Acceptance: Per Epic 7 (E) — same findings as Sprint 1 against testbed
  `/reflect-xss` (xss `reflected_xss`) + testbed `/vulnerable?q='`
  (sqli `sqli_error_string`). `wc -l ≤ 50` for both.
  Verify (testbed running):
  ```
  # Tier 3 acceptance: testbed SQLi/XSS endpoints fire:
  webprobe http://localhost:9999 --url-list <(echo "/vulnerable?q=test") --include-modules sqli 2>&1 | grep -q "sqli_error_string" && echo "sqli retrofit OK"

  webprobe http://localhost:9999 --url-list <(echo "/reflect-xss?q=test") --include-modules xss 2>&1 | grep -q "reflected_xss" && echo "xss retrofit OK"

  wc -l webprobe/modules/sqli.py webprobe/modules/xss.py

  # FINAL Lock 5 sweep across ALL 12 modules:
  grep -rn "print(" webprobe/modules/ --include="*.py" | grep -v _common.py | grep -v _.*_helpers.py
  # Must return nothing — Lock 5 verified across all 12 modules
  ```
  Estimated time: 30 min

  **═══════════════ CHECKPOINT E — v1 retrofit + integration complete ═══════════════**
  Boundary: 6 v1 modules retrofit to Module Contract; integration test
  passes end-to-end on testbed; v1 module emit pattern matches Sprint 1
  acceptance image (within Tier 3 constraints — testbed deliberate-flaw
  endpoints serve as v1 acceptance fixtures); Sprint 2 acceptance image
  (47 reqs / dual-session / IDOR / SCAN COVERAGE) reproduces against
  testbed.
  Roughly: after item 22 (renumbering-robust anchor: "after v1 retrofit +
  integration complete").
  **Heaviness: HEAVY (final acceptance gate before release).**
  Verification:
    - Lock 5 grep clean across ALL module bodies
    - v1 module emit pattern produces same finding type slugs as Sprint 1
    - Sprint 2 acceptance image reproduces against testbed (run command
      from item 23 prerequisites, inspect output for: 47-ish requirements
      counted, dual-session evidence, IDOR finding present with
      baseline_context populated, SCAN COVERAGE block correct, --fit3048
      grouping mode produces 7-category HTML)

- [ ] **23. v2.0.0 release + Devpost update** *(locked from Phase 1 Q4)*
  Spec ref: `scope.md > Endpoint A` + `scope.md > Amendment 1` (semver
  progression supersession) + Phase 1 Q4 final-item structure
  **Prerequisites** (must pass before final item starts):
    1. testbed-acceptance run produces output matching /spec acceptance criteria:
       - 47-ish requirements counted in SCAN COVERAGE block
       - dual-session evidence (auth_context badge "primary" + "baseline"
         OR "as admin" + "as alice" depending on auth-user values)
       - IDOR finding present with baseline_context populated
       - SCAN COVERAGE block renders correctly across terminal + HTML +
         JSON
       - `--fit3048` grouping mode produces 7-category HTML structure
    2. zero `print()` in module bodies:
       `grep -rn "print(" webprobe/modules/ --include="*.py" | grep -v
       _common.py | grep -v _.*_helpers.py` returns nothing
    3. all 5 checkpoints A-E passed
    4. process-notes.md updated with `## Sprint 2 — /build` section per
       3-part template:
       - **What got built** (factual scope summary)
       - **Notable decisions during build** (with checkpoint refs)
       - **Open at end of /build** (input pile for /reflect)
  **Final item actions:**
    1. Run testbed-acceptance: `scripts/run_testbed_acceptance.sh >
       acceptance-output.txt` (script created as part of this item; runs
       the canonical Sprint 2 invocation against running testbed,
       captures all 4 output sinks)
    2. Inspect `acceptance-output.txt` against /spec acceptance criteria
    3. Generate 4 screenshots (terminal acceptance image + 3 HTML reports:
       default grouping / `--fit3048` grouping / testbed run); save to
       `screenshots/sprint-2/`
    4. Update README:
       - Add "Last verified against: webprobe testbed v2.0.0" line
       - Update version badge to v2.0.0
       - Update changelog with v2 narrative (auth surface, 6 new modules,
         testbed harness, SCAN COVERAGE block, JSON envelope)
    5. Tag `v2.0.0` (NOT `v2.0.0-rc.1`, per scope.md Amendment 1)
    6. Push tag + commits
    7. Update Devpost project page:
       - Replace screenshots gallery with the 4 new screenshots
       - Update description with v2 narrative
       - Update tech stack list (note: Flask testbed-only via
         `[project.optional-dependencies]`)
  Acceptance: scripts/run_testbed_acceptance.sh produces output matching
  prerequisites #1; v2.0.0 tag pushed; Devpost page updated with new
  screenshots + description; README "Last verified against" line
  reflects v2.0.0.
  Verify:
  ```
  # Tag verification:
  git tag --list | grep -q "^v2.0.0$" && echo "v2.0.0 tag present OK"
  git log v2.0.0 --oneline | head -3

  # README verification:
  grep -q "Last verified against: webprobe testbed v2.0.0" README.md && echo "README updated OK"
  grep -q "v2.0.0" README.md && echo "version badge updated OK"

  # Screenshots verification:
  test -f screenshots/sprint-2/terminal-acceptance.png && echo "terminal screenshot present OK"
  test -d screenshots/sprint-2 && ls screenshots/sprint-2 | wc -l | xargs -I{} test {} -ge 4 && echo "≥4 screenshots present OK"
  ```
  Estimated time: 60 min

---

## P1 cut decision logic (referenced from Checkpoint B Role 2)

If actual hours spent on items 1-9 > expected × 1.5 at Checkpoint B:

  **Drop:** items 17 (error_leakage), 18 (session), 19 (brute_force) and
  their MUST SPLIT sub-items.
  **Keep:** items 15 (idor), 16 (csrf) — these complete the Sprint 2
  marquee detection capability (auth-aware probes against state-aware
  vulnerabilities) without the supporting v1-style detections.
  **Sprint 2 contracts** from 23 items to 20 items.
  **Hour budget recovers** to Sprint 1's 1.5x rather than 2x (~22.2 hr
  realistic vs 26.7 hr no-cut).
  **Documentation:** Item 23's process-notes "Open at end of /build"
  section explicitly notes P1 cut triggered + which items deferred to
  Sprint 3.
  **Spec/scope unchanged:** P1-cut Sprint 2 still ships v2.0.0 (per
  Amendment 1); the 3 deferred modules become Sprint 3 items 1-3.

If actual ≤ expected × 1.5 → continue full 23-item scope.

P1 cut decision happens AT Checkpoint B (item 9 acceptance), NOT later
— after Checkpoint B, P1 cuts mean throwing away completed work, defeating
the cost-saving intent.
