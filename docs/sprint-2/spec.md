# WebProbe v2.0 — Sprint 2 Technical Spec

Authenticated-scanning expansion of the v1 black-box scanner. This spec
translates `docs/sprint-2/prd.md`'s 7 epics × ~40 stories into
implementation contracts: class signatures, file boundaries, phase
ordering, and the cross-cutting invariants that survive `/checklist`
and `/build`.

PRD reference invariants (cross-sprint discipline):
- Every detection module ≤ 50 lines (Story 6.5).
- One detection module per vulnerability class.
- Three output sinks (terminal/HTML/TXT) plus JSON envelope (Story 3.4).
- Localhost and public HTTPS targets work without flag changes.
- Run summary always prints — evidence-of-work for "provable silence".
- Hand-written Python; no YAML templating, no plugin DSL.

## Stack

Carried from v1 unchanged:
- **Python 3.11+** — `dataclasses(kw_only=True)`, `typing.Literal`,
  `importlib.resources.files()`. Sprint 1 ran on 3.14 successfully.
- [`requests`](https://requests.readthedocs.io/en/latest/) — HTTP client.
- [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
  — HTML form parsing + dynamic-source URL extraction (new v2 use site).
- [`colorama`](https://pypi.org/project/colorama/) — Windows ANSI; auto-strip
  on non-TTY streams.

New in v2:
- [`Flask`](https://flask.palletsprojects.com/en/stable/) — testbed-only
  dependency. Single-file Flask app at `webprobe/testbed/`, runnable via
  `python3 -m webprobe.testbed`. Bundled but optional (declared in
  `[project.optional-dependencies]` group `testbed`); core scanner does
  not import Flask.
- **`pyproject.toml` + `[project.scripts]`** — replaces v1's
  `python3 webprobe/probe.py <target>` ugliness with `webprobe <target>`
  via [setuptools entry points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html).
  Console script: `webprobe = "webprobe.probe:main"`.

Stdlib additions (no new deps for these):
- [`getpass`](https://docs.python.org/3/library/getpass.html) — Story 1.5
  password resolution chain. `stream=sys.stderr` to keep prompts off
  stdout.
- [`xml.etree.ElementTree`](https://docs.python.org/3/library/xml.etree.elementtree.html)
  — sitemap.xml parsing (Story 2.1).
- [`difflib.get_close_matches`](https://docs.python.org/3/library/difflib.html#difflib.get_close_matches)
  — Levenshtein-like module-name suggestion (Story 4.1).
- [`importlib.resources.files`](https://docs.python.org/3/library/importlib.resources.html)
  — package-resource access for `webprobe/data/*/*.txt` files.
- [`hashlib.sha256`](https://docs.python.org/3/library/hashlib.html) —
  evidence_hash, IDOR body comparison, session-check fingerprinting.
- `threading.Lock`, `concurrent.futures.ThreadPoolExecutor` — paths.py
  concurrency (v1 carryover).

## Runtime & Deployment

- **Install:** `pip install -e .` from repo root. Sets up `webprobe`
  console script in user's PATH.
- **Invoke:** `webprobe <target> [flags]` from any directory.
- **Testbed:** `python3 -m webprobe.testbed` binds Flask app to
  `localhost:9999`. Acceptance harness for v2 detection modules.
- **No external services.** Outbound HTTP only to user-supplied target
  + the testbed when running locally. No telemetry, no update checks,
  no third-party APIs.

Runtime environment requirements:
- `pip install -e .` requires `pip ≥ 21.3` (pyproject.toml support).
- Flask 3.x (testbed only). Optional dependency group `testbed`.

## Architecture Overview

```
                    ┌──────────────┐
                    │  webprobe    │  CLI entry (probe.py:main)
                    │  argparse    │
                    └──────┬───────┘
                           │ args (argparse Namespace)
                           ▼
                    ┌──────────────┐
                    │   Engine     │  10-phase orchestrator (engine.py)
                    │  (instance)  │
                    └──────┬───────┘
                           │
        ┌──────────────────┼─────────────────┬───────────────┐
        ▼                  ▼                 ▼               ▼
  ┌──────────┐      ┌────────────┐    ┌──────────┐    ┌────────────┐
  │  filter  │      │ discovery  │    │   auth   │    │  modules/  │
  │  (Phase  │      │ (Phase 4)  │    │ (Phase 5)│    │  (Phase 6) │
  │  2,3.5,  │      │            │    │          │    │  dispatch  │
  │  3.6)    │      │            │    │          │    │            │
  └────┬─────┘      └─────┬──────┘    └────┬─────┘    └──────┬─────┘
       │                  │                │                  │
       │            ┌─────▼──────┐         │                  │
       │            │  Target    │         │                  │
       │            │  (forms +  │◄────────┴──────────────────┤
       │            │  query +   │                            │
       │            │  urls pool)│                            │
       │            └────────────┘                            │
       │                                                       │
       └─────────►  ScanCoverage  ◄────────────────────────────┘
                    (incremental fill, Phase 3.5 → 7)
                          │
                          ▼
                  ┌──────────────────┐
                  │  Phase 7 dedup   │  in-place mutation
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────┐
                  │  Phase 8 render  │  4 sinks: terminal, html, txt, json
                  └──────────────────┘
```

Data flow lifecycle of a finding:

1. **Module body** constructs `Finding(severity, category, finding_type,
   name, url, evidence, remediation, ...)` — ALL fields required at this
   point are user-content fields. Engine-injected fields (`auth_context`,
   `seen_in`, `fit3048_category`) default to `None`.
2. `Finding.__post_init__` validates ranges (severity enum,
   fit3048_category if set, finding_type non-empty) and **auto-computes
   `evidence_hash`** from `category:url:evidence` (self-contained, no
   engine context needed).
3. Module calls `report_finding(f)` — engine-wrapped callback per
   module-per-pass (Story 6.4).
4. **Engine wrapper** injects context-dependent fields:
   - `auth_context` from pass_label + primary user/role
   - `seen_in = [pass_label]`
   - `fit3048_category = ModuleClass.FIT3048_CATEGORY_MAP[f.finding_type]`
5. Wrapper acquires `_stdout_lock`, renders inline tease to
   `self._terminal_stream`, appends to `self._findings`.
6. **Phase 7 dedup** mutates `self._findings` in place: identity tuple
   `(category, url, evidence_hash)`; matched pairs collapse to single
   entry with `seen_in: ["unauth", "authed"]`.
7. **Phase 8 render** consumes deduped findings + ScanCoverage +
   ScanMetadata via four parallel renderers.

## File Structure

```
webprobe-project/
├── webprobe/
│   ├── __init__.py                       # __version__ = "2.0.0"
│   ├── probe.py                          # CLI entrypoint (argparse + main)
│   ├── engine.py                         # Engine class, 10-phase orchestration
│   ├── auth.py                           # NEW v2 — credential exchange
│   ├── discovery.py                      # NEW v2 — URL pool composition
│   ├── filter.py                         # NEW v2 — module filtering + risk gates + testbed
│   ├── registry.py                       # NEW v2 — @register decorator + MODULE_REGISTRY
│   ├── coverage.py                       # NEW v2 — ScanCoverage + sub-dataclasses + ScanMetadata
│   ├── target.py                         # v1 — discover_target (forms + query_params only)
│   ├── findings.py                       # v1+v2 — Finding, Form, Target, Source enum, ALL_SOURCES
│   ├── session.py                        # v1+v2 — thinner; eager session-list factory
│   ├── profiles.py                       # v1 — CAKEPHP_PATHS (consumed by discovery now)
│   │
│   ├── modules/
│   │   ├── __init__.py                   # imports each module file (triggers @register)
│   │   ├── base.py                       # BaseModule ABC + DATA_FILES auto-load + _on_request_error
│   │   ├── _common.py                    # send + inject_param + compare_responses + build_units + DEFAULT_TIMEOUT
│   │   │
│   │   ├── headers.py                    # v1 retrofit
│   │   ├── info_disclosure.py            # v1 retrofit
│   │   ├── paths.py                      # v1 retrofit, shrunk per (2K) — no curated.txt load
│   │   ├── _paths_helpers.py             # v1 carryover (likely shrinks)
│   │   ├── sqli.py                       # v1 retrofit (calls inject_param, was send)
│   │   ├── _sqli_helpers.py              # v1 carryover
│   │   ├── xss.py                        # v1 retrofit
│   │   ├── _xss_helpers.py               # v1 carryover
│   │   ├── traversal.py                  # v1 retrofit
│   │   ├── _traversal_helpers.py         # v1 carryover
│   │   │
│   │   ├── access_control.py             # NEW v2 — Story 7.1
│   │   ├── idor.py                       # NEW v2 — Story 7.2
│   │   ├── csrf.py                       # NEW v2 — Story 7.3
│   │   ├── error_leakage.py              # NEW v2 — Story 7.4
│   │   ├── session.py                    # NEW v2 — Story 7.5
│   │   └── brute_force.py                # NEW v2 — Story 7.6
│   │   # Helper files (_<name>_helpers.py) created REACTIVELY by /build
│   │   # only when module body crosses 50-line cap. NOT pre-allocated.
│   │
│   ├── output/
│   │   ├── __init__.py                   # exports render_terminal, render_html, render_txt, render_json
│   │   ├── colors.py                     # v1 — SEVERITY_ANSI, SEVERITY_HEX, init()
│   │   ├── terminal.py                   # v1+v2 — banner, COVERAGE block, FINDINGS, summary
│   │   ├── html.py                       # v1+v2 — extended for auth-badge / IDOR / OPERATIONAL_RISK chip
│   │   ├── txt.py                        # v1+v2 — ANSI-stripped terminal output
│   │   └── json_render.py                # NEW v2 — Story 3.4 versioned envelope
│   │
│   ├── testbed/                          # NEW v2 — Story 3.5 (item 3.5)
│   │   ├── __init__.py
│   │   └── __main__.py                   # Flask app, deliberately-broken endpoints
│   │
│   └── data/
│       ├── paths/curated.txt             # v1, now engine-loaded (Source.CURATED)
│       ├── access_control/
│       │   ├── admin_paths.txt           # NEW
│       │   └── admin_signals.txt         # NEW (multi-language)
│       ├── error_leakage/
│       │   └── stack_trace_patterns.txt  # NEW
│       └── brute_force/
│           └── lockout_signals.txt       # NEW (English + Chinese + Japanese)
│
├── docs/
│   ├── learner-profile.md
│   ├── scope.md                          # v1
│   ├── prd.md                            # v1
│   ├── spec.md                           # v1
│   ├── checklist.md                      # v1
│   └── sprint-2/
│       ├── scope-input.md
│       ├── scope.md
│       ├── prd.md
│       └── spec.md                       # ← this file
├── screenshots/
│   ├── webprobe_*.html                   # v1 audit artifacts
│   └── sprint-2/                         # v2 audit artifacts (Endpoint B output)
├── pyproject.toml                        # NEW v2 — replaces v1 requirements.txt
├── README.md                             # v1+v2 (updated for auth + testbed walkthrough)
├── process-notes.md                      # learning journal
└── .gitignore                            # __pycache__, *.pyc, webprobe_*.{html,txt,json}
```

## Engine Phase Ordering

Phases run sequentially in `Engine.run()`. Each phase is a one-line
coordinator method (`_phase_name(self)`) that delegates to specific
helpers. Phase methods read as prose; logic lives in helpers.

```
Phase 0    argparse + colors.init()
Phase 0.5  Inter-flag validation (auth + discovery + filter + risk-gate)
           — All cross-flag invariants caught here, before any HTTP
Phase 1    Module enumeration + class-attr validation
           — Validates auth_strategy, FIT3048_CATEGORY_MAP, DATA_FILES
             existence per registered class
Phase 2    User-flag module filtering (--include-modules / --exclude-modules)
           — Risk gates NOT applied yet; testbed unknown
Phase 3    Connectivity check (v1 carryover, single GET, base_response)
Phase 3.5  Testbed detection (filter.detect_testbed)
           — caches self._is_testbed
Phase 3.6  Risk-gate filtering (filter.filter_modules_by_risk_gates)
           — produces (kept, dropped); testbed bypass returns (modules, [])
Phase 3.7  Risk-gate banner emission to self._terminal_stream (Story 5.3)
           — only if dropped non-empty AND not all-excluded AND not testbed
Phase 4    URL pool resolution (discovery.resolve_url_pool)
           — url_list + robots + dynamic + curated; sitemap if not authed
Phase 5    AUTH SETUP (skipped if neither --auth-form nor --cookie)
           5a: resolve passwords (auth.resolve_password × 1-2)
           5b: build primary session
           5c: build baseline if any
           5d: detect_shared_session → INFO if shared
           5e: session-check probe (sha256 unauth vs primary)
           5f: authed sitemap discovery (if --use-sitemap-authed)
Phase 6    Per-module dispatch (Story 6.3 fire ordering, --scan-both per-pass)
Phase 7    Dedup findings (engine-private, mutates self._findings in place)
Phase 8    Render (4 sinks; ScanCoverage frozen-by-convention here)
Phase 9    Run-end summary block to terminal + TXT
```

### Phase 5 Sub-Phase Abort/Continue Table

PRD ref: `prd.md > Epic 1 > Stories 1.1, 1.3, 1.4, 1.5`.

| Sub-phase | Failure mode | Behavior |
|---|---|---|
| 5a | `PasswordResolutionError` | Abort, `sys.exit(1)` |
| 5b | `LoginDiscoveryError` / `LoginValidationError` | Abort, `sys.exit(1)` |
| 5c | `LoginDiscoveryError` / `LoginValidationError` | Abort, `sys.exit(1)` |
| 5d | Cookie equality detected | Continue, INFO finding |
| 5e | Session-check ambiguous | Continue, INFO finding |
| 5f | `SitemapDiscoveryError` (auth-fetched sitemap fails) | Abort, `sys.exit(1)` (parity with 5b/c — auth pipeline broken) |

5a/5b/5c/5f are abort-barriers (auth pipeline broken → no point dispatching).
5d/5e are observability checks (auth works, but webprobe noticed something
worth flagging) → emit INFO, continue.

### Phase 0.5 Inter-Flag Validation

PRD ref: `prd.md > Epic 4 > Story 4.1` (cross-flag gated-module-in-include),
plus extension of Epic 1 (1F) pattern (flag-combination invariants live in
consuming module, not argparse).

```python
# Invocations during Phase 0.5
auth.validate_auth_flags(args)             # mutex: --cookie / --auth-form
                                           # mutex: --idor-baseline / --idor-baseline-form
                                           # required-with: --auth-form needs --auth-user
discovery.validate_discovery_flags(args)   # --use-sitemap-authed needs --use-sitemap
                                           # --use-sitemap-authed needs --auth-form/--cookie
filter.validate_module_flags(args)         # mutex: --include-modules / --exclude-modules
                                           # name validation + Levenshtein suggestion
                                           # cross-flag: --include-modules <gated> needs gates
filter.validate_i_own_this_target(args.target_url, args.i_own_this_target)
                                           # hostname binding (Story 5.5)
                                           # rejects path/query in assertion
```

All validators raise `ConfigurationError`. Engine catches at top level
and exits with code 2 (argparse-style config error).

`filter.validate_module_flags` lists ALL missing gate flags at once
(extends actionable-error pattern):

```
ERROR: The following modules require risk-gate flags:
  access_control: requires --i-own-this-target=<hostname>
  brute_force: requires --include-brute-force AND --i-own-this-target=<hostname>
  csrf: requires --i-own-this-target=<hostname>
See risk gates in --help.
```

## Module Contract (Epic 6)

### `BaseModule` — extended class-level contract

PRD ref: `prd.md > Epic 6 > Story 6.1`.

`webprobe/modules/base.py`:

```python
from abc import ABC, abstractmethod
from importlib.resources import files
from typing import Callable, Literal, Optional

from requests import Session
from requests.exceptions import RequestException

from webprobe.findings import Finding, Source, ALL_SOURCES, Target


class BaseModule(ABC):
    """Every detection module subclasses this. ≤50 lines per concrete module."""

    # Required class attributes (Phase 1 validation enforces presence):
    name: str                                      # slug, e.g. "access_control"
    auth_strategy: Literal["unauth_always", "follow", "auth_required"]
    FIT3048_CATEGORY_MAP: dict[str, int]           # finding_type → 1..10

    # Optional class attributes (defaults below):
    source_filter: frozenset[Source] = ALL_SOURCES
    DATA_FILES: frozenset[str] = frozenset()       # filenames under webprobe/data/<name>/

    def __init__(self, args=None):
        """Args injected uniformly per Lock 4. Modules that don't need args
        ignore self.args; modules that do (session, brute_force) read from it.

        Subclass overrides MUST call super().__init__(args) first. Override
        pattern is post-process self._data, NOT replace base loading logic.
        """
        self.args = args
        self._data: dict[str, list[str]] = {}
        for filename in self.DATA_FILES:
            text = (files("webprobe.data") / self.name / filename).read_text(encoding="utf-8")
            # Canonical parsed form: stripped, comment-free, blank-free
            self._data[filename] = [
                line.strip() for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

    @abstractmethod
    def run(
        self,
        target: Target,
        session_factory: Callable[[], list[Session]],
        report_finding: Callable[[Finding], None],
    ) -> None:
        """Run this module against `target`.

        - `session_factory()` returns list[Session]. Length 1 in unauth phase
          and unauth_always modules. Length 1-2 in auth phase. IDOR is the
          sole consumer of len > 1; other modules use sessions[0].
        - `report_finding(f)` emits the inline tease at moment of detection.
          Engine wraps this callback per dispatch (per module, per pass) to
          inject auth_context, seen_in, fit3048_category and acquire stdout
          lock. Module body is thread-naive.

        v2 INVARIANT: `run()` returns None. Engine accounting goes through
        wrapped callback only (not return value). v1's `-> list[Finding]`
        return is dropped — see Open Issues for /prd loop-back note.
        """

    def _on_request_error(self, url: str, exception: RequestException) -> None:
        """Default RequestException handler: silent skip. Subclass may override.

        v2 INVARIANT: module body MUST handle RequestException via this hook,
        NOT bare `except Exception` (swallows programmer bugs) or bare
        `except:` (swallows KeyboardInterrupt).
        """
```

### `Finding` dataclass v2

PRD ref: `prd.md > Epic 6 > Story 6.2`.

`webprobe/findings.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Literal, Optional

from requests import Response

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


class Source(str, Enum):
    """URL discovery source taxonomy. str mixin for cheap JSON serialization."""
    SITEMAP = "sitemap"
    ROBOTS = "robots"
    URL_LIST = "url_list"
    DYNAMIC = "dynamic"
    CURATED = "curated"


ALL_SOURCES: frozenset[Source] = frozenset(Source)


@dataclass(kw_only=True)
class Finding:
    """v2 finding. kw_only=True forbids positional construction — readability
    discipline so module body always reads as
    Finding(severity="HIGH", category="csrf", finding_type=..., ...).
    """
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    category: str                                  # module-identity slug
    finding_type: str                              # FIT3048_CATEGORY_MAP key
    name: str                                      # human-readable title
    url: str
    evidence: str
    remediation: str

    # Optional user-content fields (module sets if relevant):
    payload: Optional[str] = None
    poc_url: Optional[str] = None
    parameter: Optional[str] = None                # v1 carryover

    # Engine-injected fields (None at construction; wrapper fills before render):
    auth_context: Optional[str] = None             # context-dependent
    baseline_context: Optional[str] = None         # IDOR-only, module-set
    seen_in: list[str] = field(default_factory=list)  # ["unauth"] or ["authed"] or both
    fit3048_category: Optional[int] = None         # context-dependent (lookup)
    evidence_hash: Optional[str] = None            # self-contained, auto-computed below

    def __post_init__(self):
        # Severity validation (always)
        assert self.severity in SEVERITY_ORDER, f"invalid severity: {self.severity}"

        # finding_type non-empty (always)
        assert self.finding_type, "finding_type must be non-empty"

        # fit3048_category range (only if set; engine wrapper guarantees non-None at storage)
        if self.fit3048_category is not None:
            if not 1 <= self.fit3048_category <= 10:
                raise ValueError(
                    f"fit3048_category must be 1..10, got {self.fit3048_category}. "
                    f"See FIT3048_CATEGORY_MAP in module class."
                )

        # evidence_hash auto-computed from constructor args (self-contained)
        if self.evidence_hash is None:
            self.evidence_hash = sha256(
                f"{self.category}:{self.url}:{self.evidence}".encode()
            ).hexdigest()[:16]


@dataclass
class Form:                                        # v1 unchanged
    action: str
    method: str
    fields: dict[str, str]


@dataclass
class Target:                                      # v1 + v2 urls field
    url: str
    base_response: Response
    forms: list[Form]
    query_params: dict[str, str]
    profile: Optional[str]
    urls: tuple[tuple[str, Source], ...] = ()      # frozen URL pool (Phase 4 freeze)
```

`Source` enum location lock: `webprobe/findings.py` is a pure
type-definition module. **Permitted contents:** dataclasses, enums,
type-level constants, validation invariants. **NOT permitted:** I/O,
processing logic, helpers acting on findings. Sprint 3+ adds Severity
enum / Mode enum here; never adds `dedup_findings()` here.

`Finding.fit3048_category` invariant: Optional during construction;
engine wrapper guarantees non-None before storage and rendering. JSON
serialization always emits with concrete value (per Story 6.2
clarification — flagged as PRD ambiguity, see Open Issues).

`Finding.evidence_hash`: self-contained computation in `__post_init__`.
Engine wrapper does NOT inject. Categorization rule: self-contained
fields auto-compute in `__post_init__`; context-dependent fields
(auth_context, seen_in, fit3048_category) are engine-wrapper-injected.

### Module Registry — `webprobe/registry.py`

PRD ref: `prd.md > Epic 4 > Story 4.1` (module-name validation).
Architectural derivation surfaced during /spec walk (4+5A): formalize
v1's MODULES manifest as decorator-based registry that auto-extends
to Sprint 3+ module additions.

```python
# webprobe/registry.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .modules.base import BaseModule

MODULE_REGISTRY: dict[str, type["BaseModule"]] = {}


def register(cls: type["BaseModule"]) -> type["BaseModule"]:
    """Decorator: register module class by its `name` class attribute.

    Idempotent — re-registration replaces. (Useful for /build hot-reload during
    test development.)
    """
    MODULE_REGISTRY[cls.name] = cls
    return cls


def all_module_names() -> frozenset[str]:
    """Source of truth for filter.VALID_NAMES, --help text, and any other
    consumer that needs to enumerate modules."""
    return frozenset(MODULE_REGISTRY.keys())
```

Each module file uses `@register` at class definition:

```python
# webprobe/modules/access_control.py
from ..registry import register
from .base import BaseModule

@register
class AccessControlModule(BaseModule):
    name = "access_control"
    auth_strategy = "auth_required"
    FIT3048_CATEGORY_MAP = {"role_violation": 2, "ambiguous_200_summary": 2}
    DATA_FILES = frozenset({"admin_paths.txt", "admin_signals.txt"})
    ...
```

`webprobe/modules/__init__.py` imports each module file (triggers `@register`
side effects). Adding a 7th detection module = creating
`webprobe/modules/<name>.py` + `@register` decorator + import in
`__init__.py`. No engine changes.

### Engine Pre-Resolution Semantics

PRD ref: `prd.md > Epic 6 > Story 6.3`.

Engine reads each registered class's declarations once at scan-start
(Phase 1 validation), filters per Phase 2/3.6, then dispatches per
Phase 6 with closure-captured callbacks.

```python
# engine.py Phase 6 dispatch loop
for module_cls in self._scheduled_modules:
    instance = module_cls(self.args)               # uniform args injection (Lock 4)

    if module_cls.auth_strategy == "unauth_always":
        self._dispatch_one(instance, "unauth", [self._unauth_session])

    elif module_cls.auth_strategy == "follow":
        # Always run unauth pass
        self._dispatch_one(instance, "unauth", [self._unauth_session])
        # Conditionally run authed pass under --scan-both
        if self.args.scan_both and self._auth_phase_succeeded:
            self._dispatch_one(instance, "authed", self._sessions)

    else:  # auth_required
        if self._auth_phase_succeeded:
            self._dispatch_one(instance, "authed", self._sessions)

def _dispatch_one(self, instance, pass_label, session_list):
    """One module, one pass. Builds wrapped callback and session_factory."""
    factory = lambda: session_list                 # identity-shape factory
    wrapped = self._make_report_finding(
        type(instance), pass_label,
        primary_user_id=self._primary_user_id,
        role_label=self.args.auth_role,
    )
    try:
        instance.run(self._target, factory, wrapped)
    except Exception as e:
        with self._stdout_lock:
            print(f"[!] {instance.name}: errored ({type(e).__name__}) — skipped",
                  file=self._terminal_stream)
        self._errored_modules.append((instance.name, e))
```

Module fire ordering (Story 6.3 lock):

```
[unauth phase]  headers → info_disclosure → paths → sqli → xss → traversal
[auth setup]    Phase 5
[auth phase]    access_control → csrf → idor → error_leakage → session → brute_force
```

`--scan-both` ordering: back-to-back per `follow` module (headers-unauth →
headers-authed → info_disclosure-unauth → info_disclosure-authed → ...)
for debuggability.

### `report_finding` callback v2 — closure capture

PRD ref: `prd.md > Epic 6 > Story 6.4`.

```python
def _make_report_finding(self, module_cls, pass_label, primary_user_id, role_label):
    """Build wrapped report_finding for one (module, pass) dispatch.

    Closes ONLY over immutable values:
      - module_cls (class object)
      - pass_label (str)
      - primary_user_id (str, set once per scan)
      - role_label (Optional[str], set once via --auth-role)

    Permitted closure over engine state:
      - self._stdout_lock (lock object designed for concurrent access)
      - self._findings.append (list append is GIL-atomic in CPython)
      - self._terminal_stream (set once during Phase 0)

    SPRINT 3+ NOTE: self._findings.append safety relies on CPython GIL atomicity
    for list.append. If Sprint 3+ moves to multiprocessing or non-CPython
    interpreters, replace self._findings with a thread-safe queue or process-safe
    IPC mechanism.
    """
    def wrapped(f: Finding) -> None:
        # Inject context-dependent fields:
        if module_cls.auth_strategy == "unauth_always" or pass_label == "unauth":
            f.auth_context = None
        else:
            f.auth_context = (
                f"as {primary_user_id}"
                + (f" ({role_label})" if role_label else "")
            )
        f.seen_in = [pass_label]
        if f.fit3048_category is None:
            try:
                f.fit3048_category = module_cls.FIT3048_CATEGORY_MAP[f.finding_type]
            except KeyError:
                raise RuntimeError(
                    f"{module_cls.__name__}.FIT3048_CATEGORY_MAP missing key "
                    f"'{f.finding_type}'. Add the mapping to the module class."
                )
        # Render + store with lock
        with self._stdout_lock:
            terminal.render_inline_tease(f, self.args, stream=self._terminal_stream)
        self._findings.append(f)
    return wrapped
```

**Engine MUST NOT mutate** Finding fields: `name`, `url`, `payload`,
`evidence`, `poc_url`, `remediation`, `severity`, `category`,
`finding_type`. Engine only injects per-finding *attribution* fields and
*computed-identity* fields (Story 6.4 invariant).

### `_common.py` final shape

PRD ref: `prd.md > Epic 6 > Story 6.5.E1`.

`webprobe/modules/_common.py`:

```python
from hashlib import sha256
import requests
from requests import Response

DEFAULT_TIMEOUT: float = 10.0  # seconds, v1 carryover; not user-configurable in v2

def send(url, *, session=None, **kwargs) -> Response:
    """Sprint 2 PRD-locked: anonymous-or-authed single GET.
    Used by: access_control, idor, csrf, error_leakage, session, brute_force.

    Keyword-only `session` parameter (`*` prevents positional misuse).
    Sprint 1 callers pass session=None (or omit) for anonymous behavior.
    """
    if session is None:
        return requests.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
    return session.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)


def inject_param(sess, url, method, param, payload, base):
    """v1 carryover (renamed from `send`). Per-param injection helper.
    Used by: sqli, xss, traversal."""
    d = {**base, param: payload}
    if method.upper() == "POST":
        return sess.post(url, data=d, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    return sess.get(url, params=d, timeout=DEFAULT_TIMEOUT, allow_redirects=True)


def compare_responses(resp_a: Response, resp_b: Response) -> bool:
    """sha256 body match. 3+ callers: idor (cross-account), session (logout test),
    error_leakage (user-enumeration baseline diff)."""
    return (sha256(resp_a.content).hexdigest() ==
            sha256(resp_b.content).hexdigest())


def build_units(target):
    """v1 carryover. Per-injectable surface enumerator.
    Used by: sqli, xss, traversal."""
    units: list[tuple[str, str, str, dict]] = [
        (target.url, "GET", k, {}) for k in target.query_params
    ]
    for fm in target.forms:
        for k in fm.fields:
            base = {f: v for f, v in fm.fields.items() if f != k}
            units.append((fm.action, fm.method, k, base))
    return units
```

**Capability-axis discipline:** if /build observes a 3rd caller for any
new helper concern (hidden-input stripping, logout URL discovery, login
attempt), promote to `_common.py`. Until 3+ callers, stays in
per-module `_<name>_helpers.py`.

### Module-Body Invariants (cross-cutting Locks)

- **Lock 1: Finding kw_only.** All Finding construction uses keyword
  arguments. `@dataclass(kw_only=True)` enforces. No positional args.
- **Lock 2: URL construction via `urllib.parse.urljoin`.** No string
  concatenation for URLs. Concatenation breaks on trailing-slash
  boundary cases.
- **Lock 3: `RequestException` via `_on_request_error`.** No bare
  `except Exception`, no bare `except:`. Module-specific behavior
  overrides `_on_request_error` if needed.
- **Lock 4: args uniform injection.** Engine always passes `args` to
  `module_cls(self.args)`. Modules ignore if not needed; read
  `self.args.*` if needed. No per-module asymmetry in dispatch code.
- **Lock 5: Zero `print()` in module bodies.** All user-visible output
  via `report_finding` callback. Engine wrapper handles routing,
  locking, ANSI. Build verification: `grep -rn "print(" webprobe/modules/`
  returns zero matches in module bodies (excluding `_common.py` if used
  for debugging, which it isn't in v2).

### 50-Line Cap

PRD ref: `prd.md > Epic 6 > Story 6.5`.

Per detection module file. Helper extraction to
`webprobe/modules/_<name>_helpers.py` if module crosses cap. Helpers
exempt from cap (helpers absorb complexity). Engine framework files
(`engine.py`, `auth.py`, `discovery.py`, `filter.py`, etc.) not subject
to cap.

`/build` Checkpoint B: `wc -l webprobe/modules/*.py` — every detection
module file must be ≤50 lines. Helper extraction reactive (don't
pre-create empty helper files; create only when /build observes
overflow).

## Authentication & Session Setup (Epic 1)

`webprobe/auth.py` — credential exchange. ~5 functions, ~30-50 lines
of code. Single file (subpackage premature for this volume).

### Custom Exceptions

```python
# webprobe/auth.py
class LoginDiscoveryError(Exception):
    """Form not found, multi-step login detected, etc.
    Message MUST be user-actionable (full sentence with remediation).
    Engine prints message verbatim to stderr before sys.exit(1)."""

class LoginValidationError(Exception):
    """POST succeeded but login didn't (form re-rendered)."""

class PasswordResolutionError(Exception):
    """No flag, no env var, no TTY available."""

class ConfigurationError(Exception):
    """Inter-flag invariant violated (mutex / required-with).
    Engine catches at top level, exits with code 2."""
```

### `setup_form_login()` — Story 1.1

```python
def setup_form_login(
    target_url: str,
    login_url: str,
    user: str,
    password: str,
    *,
    verbose: bool = True,
) -> requests.Session:
    """Story 1.1 form-login auto-discovery + POST + validation.

    Composition: _discover_login_form → _build_login_payload → _validate_login_response.

    `verbose=False` suppresses scan-stream "[*] Logging in as ..." line.
    Used by ephemeral_login_form() to keep ephemeral sessions truly ephemeral
    (no scan-stream footprint, only target-side auth log entry).
    """
    sess = requests.Session()
    resp = sess.get(login_url, allow_redirects=True)
    form, action_url = _discover_login_form(resp, login_url)
    payload = _build_login_payload(form, user, password)
    login_resp = sess.post(action_url, data=payload, allow_redirects=True)
    _validate_login_response(login_resp, login_url, user)
    if verbose:
        print(f"[*] Logging in as {user}... [+] Login confirmed")
    return sess
```

Three private helpers — all unit-testable without mocking
`requests.Session`:

```python
def _discover_login_form(response: Response, login_url: str) -> tuple[Form, str]:
    """Pure function: parse <form> with type=password input. Story 1.1.E1
    multi-step detection raises LoginDiscoveryError."""

def _build_login_payload(form: Form, user: str, password: str) -> dict[str, str]:
    """Pure function: apply Story 1.1 field heuristic. Preserve all
    <input type=hidden> verbatim (CakePHP _csrfToken, Django
    csrfmiddlewaretoken, Rails authenticity_token, Laravel _token)."""

def _validate_login_response(response: Response, login_url: str, user: str) -> None:
    """Pure function: redirect away from login_url = success;
    same URL = failure (form re-rendered)."""
```

**Constraint:** helpers MUST NOT instantiate or call `requests.Session`.
Network I/O lives in `setup_form_login`'s main body. Form-discovery
heuristic and field-naming logic become testable without integration
test fixtures.

### `setup_cookie_session()` — Story 1.2

```python
def setup_cookie_session(cookie_string: str) -> requests.Session:
    """Parse RFC 6265 Cookie header form, attach to Session."""
```

### `setup_baseline()` — Story 1.3

Inter-flag validation lives here, not argparse:

```python
def setup_baseline(args, target_url: str) -> Optional[requests.Session]:
    """Story 1.3 multi-session contract. Owns inter-flag invariants:
    --idor-baseline / --idor-baseline-form mutex; --idor-baseline-form
    requires --idor-baseline-user. Raises ConfigurationError on violation."""
    if args.idor_baseline and args.idor_baseline_form:
        raise ConfigurationError(
            "--idor-baseline and --idor-baseline-form are mutually exclusive. "
            "Pick cookie-based baseline (--idor-baseline) or form-based "
            "baseline (--idor-baseline-form), not both."
        )
    if args.idor_baseline_form and not args.idor_baseline_user:
        raise ConfigurationError(
            "--idor-baseline-form requires --idor-baseline-user."
        )
    if args.idor_baseline:
        return setup_cookie_session(args.idor_baseline)
    if args.idor_baseline_form:
        pw = resolve_password(
            args.idor_baseline_pass,
            "WEBPROBE_IDOR_BASELINE_PASS",
            f"[Password for {args.idor_baseline_user}]: ",
        )
        return setup_form_login(
            target_url, args.idor_baseline_form, args.idor_baseline_user, pw
        )
    return None
```

### `ephemeral_login_form()` — Story 1.4

Resolves /prd △ for throwaway sub-session mechanism:

```python
def ephemeral_login_form(
    target_url: str,
    login_url: str,
    user: str,
    password: str,
) -> requests.Session:
    """Build a one-shot disposable Session via fresh form-login.

    Used by Story 7.5's session module for post-logout cookie-replay test.
    Returned Session is independent of primary/baseline list — destruction
    by logout does not affect sessions[0] or sessions[1].

    Caller responsible for using-then-discarding; engine never stores
    ephemeral Sessions. session_factory's signature stays unchanged from
    v1 — no ephemeral=True parameter pollution.
    """
    return setup_form_login(target_url, login_url, user, password, verbose=False)
```

Side effect to document in README per Story 7.5: throwaway session is
+1 login event in target's auth log.

### `resolve_password()` — Story 1.5

```python
def resolve_password(
    flag_value: Optional[str],
    env_var_name: str,
    prompt_text: str,
) -> str:
    """Story 1.5 priority chain: flag → env → getpass.
    Raises PasswordResolutionError on non-interactive TTY + no flag + no env.
    """
    if flag_value is not None:
        return flag_value
    env = os.environ.get(env_var_name)
    if env is not None:
        return env
    if not sys.stdin.isatty():
        raise PasswordResolutionError(
            f"password resolution failed: no flag set, no {env_var_name} "
            "env var, no TTY available; use --auth-pass or set env var"
        )
    return getpass.getpass(prompt=prompt_text, stream=sys.stderr)
```

`stream=sys.stderr` per [getpass docs](https://docs.python.org/3/library/getpass.html)
— keeps prompt off stdout (critical for `--json-out -` mode).

`/checklist` verification beat: `webprobe target --auth-form ... --json-out -`
produces valid JSON to stdout (no prompt string contamination). Pipe
through `jq` and confirm parse success.

### `detect_shared_session()` — Story 1.3.E1

```python
_SHARED_SESSION_COOKIE_NAMES: frozenset[str] = frozenset({
    "PHPSESSID", "laravel_session", "_session_id",
    "connect.sid", "JSESSIONID", "ci_session", "sessionid",
})

def detect_shared_session(sessions: list[requests.Session]) -> Optional[Finding]:
    """Story 1.3.E1: cookie equality check between sessions[0] and sessions[1].
    Returns INFO Finding if any same-name cookie has identical value."""
```

Module-private constant (NOT user-configurable via CLI flag — detection
heuristic must be predictable; user-configurable list is Sprint 3+
candidate). Append to frozenset at /build if <team> testbed shape uses
unusual session cookie name (e.g., `CAKEPHP_SESSION`).

### `session.py` — eager-list factory

v1 thread-local pattern retired. v2 `webprobe/session.py`:

```python
from typing import Callable
import requests

def make_session_factory(sessions: list[requests.Session]) -> Callable[[], list[requests.Session]]:
    """Identity-shape factory. Returns same list every call. Engine constructs
    `sessions` during Phase 5; this wraps for module consumption."""
    def factory() -> list[requests.Session]:
        return sessions
    return factory
```

Rationale for retiring thread-local:
1. v2 paths.py is `unauth_always` — no auth state on Session — all 20
   workers sharing one Session has zero race surface.
2. 5/6 v2 detection modules are `auth_required` and dispatched serially
   per PRD lock — thread-locality irrelevant.
3. `threading.local()` doesn't survive fork; Sprint 3+ multiprocessing
   path (flagged in Module Contract closure-capture note) would
   invalidate it. Eager list survives serialization.

`/build` Checkpoint B paths.py runtime check: if v2 paths.py is >15%
slower than Sprint 1's 11.8s on FIT3047, apply explicit
`pool_maxsize=20` mount in unauth_session construction:

```python
from requests.adapters import HTTPAdapter
session.mount("http://", HTTPAdapter(pool_maxsize=20))
session.mount("https://", HTTPAdapter(pool_maxsize=20))
```

## Discovery (Epic 2)

`webprobe/discovery.py` — URL pool composition. Naming convention:

- `discover_<source>(...)` returns metadata-rich `Result` dataclass when
  source has side-channel info (sitemap, robots).
- `discover_<source>_pairs(...)` returns simple `list[tuple[str, Source]]`
  when source is a pure URL emitter (url_list, dynamic, curated).

```python
# webprobe/discovery.py — public API

def discover_sitemap(
    target: Target, authed_session: Optional[Session] = None
) -> SitemapDiscoveryResult: ...

def discover_robots(target: Target) -> RobotsDiscoveryResult: ...

def discover_url_list_pairs(target: Target, path: str) -> list[tuple[str, Source]]: ...

def discover_dynamic_pairs(target: Target) -> list[tuple[str, Source]]: ...

def discover_curated_pairs() -> list[tuple[str, Source]]: ...

def resolve_url_pool(
    args, target: Target, sessions: Optional[list[Session]] = None
) -> tuple[tuple[str, Source], ...]:
    """Compose all enabled sources, dedup by priority, freeze. Engine Phase 4."""

def validate_discovery_flags(args) -> None:
    """Phase 0.5 inter-flag validation. Raises ConfigurationError."""
```

### `Target.urls` data shape — resolves /prd △

```python
@dataclass
class Target:
    ...
    urls: tuple[tuple[str, Source], ...] = ()
```

Tuple, not list — Python's type system enforces "MUST NOT mutate".
Modules calling `target.urls.append(...)` get `AttributeError`. Default
value `()` (empty tuple literal), NOT `field(default_factory=tuple)` —
tuple is immutable, safe as dataclass default.

Engine Phase 4 builds `discovered: list[tuple[str, Source]]`, then
assigns `target.urls = tuple(discovered)` at end of phase. After that,
the pool is structurally immutable.

Sprint 3+ migration: `tuple → ProbeURL` dataclass is mechanical
(1-line type change + 8 unpacking sites updated to read `.url`/`.source`
attrs). Acceptable carryover.

### Source priority dedup

Story 2.4.E1 lock: `url_list > robots > curated > sitemap > dynamic`.

```python
_SOURCE_PRIORITY: dict[Source, int] = {
    Source.URL_LIST: 0,
    Source.ROBOTS:   1,
    Source.CURATED:  2,
    Source.SITEMAP:  3,
    Source.DYNAMIC:  4,
}

def _dedup_by_priority(pairs: list[tuple[str, Source]]) -> list[tuple[str, Source]]:
    """Keep highest-priority source per unique URL (lower number wins).
    URL canonicalization for dedup key only — stored URL is user-typed form."""
    best: dict[str, Source] = {}
    for url, source in pairs:
        key = _canonicalize_url(url)
        if key not in best or _SOURCE_PRIORITY[source] < _SOURCE_PRIORITY[best[key][1]]:
            best[key] = (url, source)
    return list(best.values())

def _canonicalize_url(url: str) -> str:
    """Dedup-key only. Returns canonical form: lowercase scheme/netloc,
    path '/' if empty. NO query-string normalization, NO query-param order
    normalization (?id=1 ≠ ?id=01 in v2; Sprint 3+ candidate)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path or "/", parts.query, ""))
```

Audit-trail discipline (parallel to Story 5.5's `--i-own-this-target`
case preservation): record what user/source actually said, not
normalized variant. Canonicalization is dedup-key-only.

### Sitemap discovery — Story 2.1

```python
@dataclass
class SitemapDiscoveryResult:
    urls: list[tuple[str, Source]]
    capped: bool                                   # True if N>500 hit
    cap_count: int                                 # actual count if capped
    advertised_via_robots: bool                    # for Story 2.2.E1 INFO logic

class SitemapDiscoveryError(Exception): pass


def discover_sitemap(target, authed_session=None) -> SitemapDiscoveryResult:
    sess = authed_session or requests.Session()
    sitemap_url = urljoin(target.url, "/sitemap.xml")
    resp = sess.get(sitemap_url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    # 404/410 → silent skip
    # 401 / 3xx → /users/login → fail loud per Story 2.1
    # 200 → parse
    root = ET.fromstring(resp.text)                # let ParseError propagate
    locs = _extract_sitemap_locs(root, sess, recursion_remaining=1)
    # off-host filter; cap N=500
    ...

def _extract_sitemap_locs(root, session, recursion_remaining: int) -> list[str]:
    """Handles <urlset> (direct) and <sitemapindex> (one-level recursion).
    XML namespace stripped via tag.split('}')[-1]."""
    local_name = root.tag.split('}')[-1]
    if local_name == "urlset":
        return [elem.text for elem in root.iter() if elem.tag.split('}')[-1] == "loc"]
    if local_name == "sitemapindex" and recursion_remaining > 0:
        urls = []
        for elem in root.iter():
            if elem.tag.split('}')[-1] == "loc":
                child = session.get(elem.text, timeout=DEFAULT_TIMEOUT)
                urls.extend(_extract_sitemap_locs(
                    ET.fromstring(child.text), session, recursion_remaining - 1
                ))
        return urls
    return []
```

`xml.etree.ElementTree.ParseError` propagates to `discover_sitemap`,
which wraps in `SitemapDiscoveryError` with PRD-locked message:

```
sitemap.xml at <url> returned invalid XML.
Use --no-use-sitemap to skip sitemap discovery.
```

`/reflect` note: if Sprint 3+ adds untrusted-XML processing
(user-uploaded sitemap files, third-party feed aggregation), migrate to
`defusedxml`. v2 stdlib is correct because target is user-opted-in, not
adversarial.

### Robots discovery — Story 2.3

```python
@dataclass
class RobotsDiscoveryResult:
    urls: list[tuple[str, Source]]
    wildcard_intents: list[str]                    # Story 2.3 consolidated INFO
    sitemap_url_advertised: Optional[str]          # Story 2.2.E1 three-branch INFO
```

Custom parser (~25 lines): ignores `User-agent:` line value entirely
(except as block boundary marker); Disallow lines from ALL User-agent
blocks union into single output. Wildcard handling per Story 2.3:
`/admin/*` → probed as `/admin/`; `*.bak` → not probed; `/api/v*` →
probed as `/api/v`. `Sitemap:` directive captures URL for cross-check.

### URL list discovery — Story 2.4

```python
def discover_url_list_pairs(target, path: str) -> list[tuple[str, Source]]:
    """File not found → fail loud (FileNotFoundError → handled at engine layer).
    File empty (or all comments/blanks) → INFO finding 'url-list contained no
    probe-able URLs', continue scan (intentional empty placeholder use case)."""
```

Edge case lock: file-not-found = user error (path typo, broken CI mount)
→ fail-loud immediately. File-exists-but-empty = user-intentional
(empty placeholder in CI pipelines, conditional file population) → INFO
+ continue.

### Dynamic source extraction — Story 2.5.E1

```python
def discover_dynamic_pairs(target: Target) -> list[tuple[str, Source]]:
    """Same-origin URLs from base_response HTML: <a href>, <form action>,
    <script src>. Pre-computed at scan-start; pool size fixed before module
    dispatch.

    Edge case (CakePHP-relevant): <form action=""> means "submit to current
    URL". MUST add target.url to dynamic source list, NOT skip empty action.
    """
```

### Curated discovery — v1→v2 architectural shift

```python
def discover_curated_pairs() -> list[tuple[str, Source]]:
    """Loads webprobe/data/paths/curated.txt + profile paths
    (CAKEPHP_PATHS, future Django/Rails). Tags ALL with Source.CURATED.

    v1→v2 SHIFT: paths.py NO LONGER loads curated.txt internally. Engine
    Phase 4 calls this; URL pool is single source of truth for which URLs
    get probed. paths.py reads filtered Target.urls like every other module.

    Architectural payoff:
    1. paths.py becomes contract-uniform (no special path-loading logic).
    2. paths.py file shrinks (~46 → ~30 lines; headroom for Sprint 3+ adds).
    3. COVERAGE accuracy: curated paths now in URL pool, counted in source
       breakdown.
    4. Cross-source dedup applies: /admin/ in both curated.txt AND robots.txt
       Disallow → priority ROBOTS keeps single entry.
    """
```

`webprobe/profiles.py` unchanged — `CAKEPHP_PATHS` list of strings,
consumed by `discover_curated_pairs()` instead of
`engine.build_active_modules()`.

### URL pool composition — Engine Phase 4

```python
def _resolve_url_pool(self):
    pairs: list[tuple[str, Source]] = []

    # Order doesn't affect output (dedup is order-independent), but matches
    # user mental model: explicit > intent-declared > heuristic > bulk > incidental
    if self.args.url_list:
        pairs.extend(discovery.discover_url_list_pairs(self._target, self.args.url_list))
    if self.args.use_robots:
        self._robots_result = discovery.discover_robots(self._target)
        pairs.extend(self._robots_result.urls)
    if self.args.use_sitemap and not self.args.use_sitemap_authed:
        self._sitemap_result = discovery.discover_sitemap(self._target)
        pairs.extend(self._sitemap_result.urls)
    pairs.extend(discovery.discover_dynamic_pairs(self._target))
    pairs.extend(discovery.discover_curated_pairs())  # always

    deduped = discovery._dedup_by_priority(pairs)
    self._target.urls = tuple(deduped)

# Phase 5f: authed sitemap, runs AFTER auth setup
def _phase_5f(self):
    if self.args.use_sitemap_authed and self._auth_phase_succeeded:
        self._sitemap_result = discovery.discover_sitemap(
            self._target, authed_session=self._sessions[0]
        )
        # Re-dedup after auth-fetched sitemap arrives
        all_pairs = list(self._target.urls) + self._sitemap_result.urls
        self._target.urls = tuple(discovery._dedup_by_priority(all_pairs))
```

INFO emissions for wildcard intents (Story 2.3) and sitemap-vs-robots-
advertised (Story 2.2.E1) happen at end of Phase 4 (or Phase 5f if
authed sitemap), before module dispatch.

## Output (Epic 3)

### `ScanCoverage` + sub-dataclasses

`webprobe/coverage.py`:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LoginProbeResult:
    confirmed: bool
    sessions: list[str]                            # ["coach_a", "coach_b"]
    timestamp: str                                 # "HH:MM:SS"


@dataclass
class SessionCheckResult:
    probe_url: str
    session_attached: bool                         # False → ambiguous, INFO emitted
    sha256_unauth: str                             # 16-char canonical (Story 3.4.E1)
    sha256_authed: str                             # 16-char canonical
    # Renderers truncate to 8 char for terminal/HTML Sessions: line display.
    # Dataclass field and JSON envelope always store 16-char canonical.


@dataclass
class LogoutTestResult:
    cookie_rejected_after_logout: bool
    finding_severity: Optional[str] = None         # "HIGH" if persisted; None if rejected


@dataclass
class PerModuleSourceFilter:
    module_name: str
    accepted_sources: list[str]                    # ["curated", "robots", "url_list"]
    accepted_count: int
    pool_total: int


@dataclass
class WildcardIntents:
    pattern_count: int
    info_finding_id: str                           # cross-ref to consolidated INFO


@dataclass
class ScanCoverage:
    """Story 3.4 JSON envelope target; Story 3.1 terminal/HTML target.
    Single source of truth.

    Mutable during scan (engine fills incrementally Phase 3.5 → Phase 7).
    Frozen by convention after Phase 7. Phase 8 (render) MUST NOT mutate.
    Engine asserts coverage.duration_seconds and modules_fired are populated
    before render starts.
    """
    mode: str                                      # exactly 4 enum values per Mode invariant
    sessions: list[str]
    urls_probed: dict                              # {"total": 47, "by_source": {...}}
    modules_fired: dict                            # {"scheduled": 10, "completed": 10, "errored": 0}
    duration_seconds: float
    login_probe: Optional[LoginProbeResult] = None
    session_check: Optional[SessionCheckResult] = None
    logout_test: Optional[LogoutTestResult] = None
    per_module_source_filter: list[PerModuleSourceFilter] = field(default_factory=list)
    wildcard_intents: Optional[WildcardIntents] = None


@dataclass
class ScanMetadata:
    """Story 3.4 JSON envelope's `scan` block."""
    target: str
    started_at: str                                # ISO8601 with TZ offset
    completed_at: str
    duration_seconds: float
    exit_code: int
    errored_modules: list[str]
    risk_gates_asserted: list[str]                 # user-typed argv form, case preserved
```

### Renderer signatures (uniform)

```python
# webprobe/output/__init__.py
from .terminal import render_terminal
from .txt import render_txt
from .html import render_html
from .json_render import render_json

__all__ = ["render_terminal", "render_txt", "render_html", "render_json"]


# Uniform signature across all four:
def render_<format>(
    coverage: ScanCoverage,
    metadata: ScanMetadata,
    findings: list[Finding],
    args,
) -> str: ...
```

Engine import: `from webprobe.output import render_terminal, render_html, render_json, render_txt`.

### `--json-out -` mode terminal-output routing — cross-cutting

Story 3.4: `--json-out -` writes JSON to stdout. ALL `[*]`/`[+]`/`[-]`/
`[HIGH]` inline-tease output during Phase 5/6 routes to **stderr**
(Unix convention: stdout = data, stderr = logs). User running
`webprobe target --json-out - | jq '.findings'` sees scan progress on
stderr, JSON clean on stdout.

```python
class Engine:
    def __init__(self, args):
        self.args = args
        if args.json_out == "-":
            self._terminal_stream = sys.stderr
        else:
            self._terminal_stream = sys.stdout

        colorama.init(
            wrap_stdout=False,                     # don't auto-wrap; we control stream
            strip=not self._terminal_stream.isatty(),
        )
```

Three pipe scenarios cleanly handled:
- `webprobe target` → stdout=TTY, stderr=TTY: colors on, stream=stdout
- `webprobe target > file.txt` → stdout=file, stderr=TTY: colors off
  (strip), stream=stdout
- `webprobe target --json-out - | jq` → stdout=pipe, stderr=TTY: colors
  on for stderr, stream=stderr, JSON clean on stdout

**Lock 6: NEVER bare `print()` in renderer code.** All terminal output
uses `print(line, file=self._terminal_stream)` or
`self._terminal_stream.write(line)`.

### HTML report v2 structure

PRD ref: `prd.md > Epic 3 > Story 3.3` (auth-context badge,
IDOR dual-session, OPERATIONAL_RISK chip).

Extends v1 `<div>` + class-name + inline-CSS pattern (preserves
"self-contained HTML, no external assets" invariant; works in 2027+
browsers via stable HTML semantics, not Web Components).

```html
<body>
  <header class="report-header">
    <h1>WebProbe v2.0 — Scan Report</h1>
    <!-- OPERATIONAL_RISK chip placement: TOP — screenshot-readable critical signal -->
    <div class="operational-risk-chip">
      <strong>⚠ OPERATIONAL_RISK:</strong> brute_force, access_control, idor, csrf<br>
      <span class="gate-trail">gated by --include-brute-force --i-own-this-target=<deployment-url></span>
    </div>
  </header>

  <section class="scan-coverage">
    <h2>Scan Coverage</h2>
    ...
  </section>

  <section class="findings">
    <h2>Findings</h2>
    <!-- Default grouping (severity tier outer, category inner) OR
         --fit3048 grouping (FIT3048 category outer, severity inner) -->
    <article class="finding finding-high" data-category="idor">
      <header class="finding-header">
        <span class="severity-badge severity-high">HIGH</span>
        <h3 class="finding-name">IDOR — Coach A can read Coach B's patient records</h3>
        <span class="auth-badge">[as coach_a (Coach)]</span>  <!-- only if auth_context != None -->
      </header>
      <dl class="finding-fields">
        <dt>URL</dt>
        <dd>
          <a href="https://target/clients/47">https://target/clients/47</a>
          <!-- DO NOT WRAP: clipboard JS depends on previousElementSibling — Sprint 1 carryover -->
          <button class="copy-btn">copy</button>
        </dd>
        <dt>Evidence</dt><dd>coach_a's GET returns same body as coach_b's GET (sha256 match)</dd>
        <dt>Probed</dt><dd>as coach_a (Coach role)</dd>
        <dt>Baseline</dt><dd>coach_b owns id=47</dd>          <!-- only if baseline_context != None -->
        <dt>Sessions</dt><dd>coach_a sha256=abc123e4 vs coach_b sha256=abc123e4 (match)</dd>
        <!-- Sessions row: only if category=='idor' AND baseline_context != None -->
        <dt>Fix</dt><dd>Add ownership check in PatientsController::view()</dd>
        <dt>FIT3048</dt><dd>Category 2</dd>
      </dl>
    </article>
  </section>
</body>
```

**Heading discipline:** every `<section class="fit3048-category">`
requires `<h2>` as first child; every `<section class="severity-group">`
requires `<h3>`. HTML5 sectioning element semantics mandate this; build
shouldn't omit headings even when section is empty visually.

**Conditional Baseline/Sessions row rendering — single expression in
two locations:**

```python
if finding.category == "idor" and finding.baseline_context is not None:
    # render Baseline: and Sessions: rows
```

Lives in exactly two places: `webprobe/output/terminal.py` and
`webprobe/output/html.py`. Build verifies via grep that no other
module branches on `category == 'idor'` for rendering — single
source of truth for IDOR-specific UI logic.

### FIT3048 two-level HTML grouping — Story 4.2

```html
<section class="fit3048-category" data-category="2">
  <h2>Category 2: Broken Access Control <span class="count">[3 findings]</span></h2>
  <section class="severity-group" data-severity="HIGH">
    <h3>HIGH</h3>
    <article class="finding">...</article>
  </section>
  <section class="severity-group" data-severity="MEDIUM">...</section>
</section>

<!-- Two distinct empty-category messages (Story 4.2.E3) -->
<section class="fit3048-category fit3048-empty" data-category="3">
  <h2>Category 3: Cryptographic Failures</h2>
  <p class="empty-reason">(no findings)</p>
</section>

<section class="fit3048-category fit3048-empty fit3048-filtered" data-category="3">
  <h2>Category 3: Cryptographic Failures</h2>
  <p class="empty-reason">(no findings — modules covering this category were excluded by --include-modules / --exclude-modules)</p>
</section>
```

### JSON envelope — Story 3.4

`webprobe/output/json_render.py`:

```python
from dataclasses import asdict
import json

def render_json(coverage, metadata, findings, args) -> str:
    """Story 3.4 versioned envelope. ensure_ascii=False for unicode (Mandarin
    lockout signals)."""
    envelope = {
        "version": "2.0",
        "tool": "webprobe",
        "scan": asdict(metadata),
        "scan_coverage": asdict(coverage),
        "findings": [_finding_to_dict(f) for f in findings],
    }
    return json.dumps(envelope, indent=2, ensure_ascii=False)


def _finding_to_dict(f: Finding) -> dict:
    """Serialize Finding with optional-fields-always-present rule (Q4 Story 3.4)."""
    return {
        "severity": f.severity,
        "category": f.category,
        "finding_type": f.finding_type,
        "name": f.name,
        "url": f.url,
        "payload": f.payload,                      # null when None, not omitted
        "evidence": f.evidence,
        "evidence_hash": f.evidence_hash,          # post-construction always non-None
        "poc_url": f.poc_url,
        "remediation": f.remediation,
        "fit3048_category": f.fit3048_category,    # post-wrapper always non-None
        "auth_context": f.auth_context,            # null for unauth_always
        "baseline_context": f.baseline_context,    # null except IDOR
        "seen_in": f.seen_in,                      # ["unauth"] | ["authed"] | both
    }
```

**Semver rules** (Story 3.4 lock):
- **MAJOR** bump: field deletion, type change, semantic change.
- **MINOR** bump: field addition (consumers MUST ignore unknown fields).
- **PATCH** bump: enum value addition.
- Sprint 3 templates check `.version | split(".") | .[0]` and fail loud
  on unknown major.

`evidence_hash` formula (Story 3.4.E1 lock):
```python
evidence_hash = sha256(f"{category}:{url}:{evidence}".encode()).hexdigest()[:16]
```
16 chars canonical (8-char truncation in terminal `Sessions:` line is
display-only). Function changes require schema MAJOR bump.

`--scan-both` deduplication: identity = `(category, url, evidence_hash)`.
Engine Phase 7 mutates `self._findings` in place.

### Run-end summary — Story 3.5

```
Target:    https://<deployment-url>/
Modules:   10 scheduled, 10 completed, 0 errored
Findings:  14 (0 CRIT, 3 HIGH, 6 MED, 4 LOW, 1 INFO)
Reports written:
  HTML: webprobe_<deployment-url>_443_20260501-1430.html
  TXT:  webprobe_<deployment-url>_443_20260501-1430.txt
  JSON: webprobe_<deployment-url>_443_20260501-1430.json
Duration:  14.3s
```

`--json-out -` mode: `JSON:` line replaced with `JSON: <stdout>`.
Single sink failure: line replaced with `HTML: [render failed — see
MODULES WITH ERRORS]`, scan still produces other sinks.
`--scan-both` mode: `Modules: 10 scheduled, 10 completed (5 of 10 ran
twice via --scan-both)`.

### Banner + `--help` skeleton

PRD ref: `prd.md > Q5(a)` — flag taxonomy categories pinned.

```python
parser = argparse.ArgumentParser(prog="webprobe")
auth_group = parser.add_argument_group("Authentication")
discovery_group = parser.add_argument_group("Discovery")
output_group = parser.add_argument_group("Output")
filtering_group = parser.add_argument_group("Filtering")
risk_group = parser.add_argument_group("Risk Gates")
```

**Group titles match PRD Q5(a) taxonomy verbatim. /build may tune
individual flag help-text wording but MUST NOT rename groups.**

Banner skeleton (auth-mode line conditional):
```
WebProbe v2.0
Target:    {target}
Auth:      {auth-mode}                 # only if Phase 5 enabled
Modules:   [{module-list}]
Profile:   --fit3048                   # only if --fit3048
─────────────────────────────────────────────
```

Banner body wording is /build-time; banner skeleton (which lines appear
conditionally) is /spec-locked.

## Filtering & Risk Gates (Epic 4+5)

`webprobe/filter.py` — pre-dispatch decision logic. Distinct from
`engine.py` Phase 6 dispatch.

### Public API

```python
def validate_module_flags(args) -> None: ...
def parse_module_list(value: str, valid_names: frozenset[str]) -> set[str]: ...
def filter_modules_by_user_flags(modules: list[type], args) -> list[type]: ...
def detect_testbed(target_url: str) -> bool: ...
def filter_modules_by_risk_gates(
    modules: list[type], args, is_testbed: bool
) -> tuple[list[type], list[type]]: ...
def render_risk_gate_banner(
    dropped: list[type], args, is_testbed: bool
) -> Optional[str]: ...
def validate_i_own_this_target(target_url: str, asserted: Optional[str]) -> None: ...
```

`VALID_NAMES` sourced from `registry.all_module_names()` at import time.

### Cross-flag gated-module-in-include validation — Story 4.1

Lists ALL missing gate flags at once (extends actionable-error pattern):

```python
def validate_module_flags(args) -> None:
    if args.include_modules and args.exclude_modules:
        raise ConfigurationError(
            "use either --include-modules or --exclude-modules, not both"
        )
    # ... name validation with case-insensitive Levenshtein-like suggestion ...

    if args.include_modules:
        included = parse_module_list(args.include_modules, VALID_NAMES)
        missing_gates: dict[str, list[str]] = {}

        if "brute_force" in included:
            needed = []
            if not args.include_brute_force:
                needed.append("--include-brute-force")
            if not args.i_own_this_target:
                needed.append("--i-own-this-target=<hostname>")
            if needed:
                missing_gates["brute_force"] = needed

        for gated in {"access_control", "idor", "csrf"} & included:
            if not args.i_own_this_target:
                missing_gates[gated] = ["--i-own-this-target=<hostname>"]

        if missing_gates:
            lines = ["The following modules require risk-gate flags:"]
            for mod, flags in sorted(missing_gates.items()):
                lines.append(f"  {mod}: requires {' AND '.join(flags)}")
            lines.append("See risk gates in --help.")
            raise ConfigurationError("\n".join(lines))
```

### Levenshtein-like suggestion — Story 4.1

```python
def _suggest_module_name(name: str, valid_names: frozenset[str]) -> Optional[str]:
    """Case-insensitive suggestion. Returns lowercase canonical name."""
    name_lower = name.lower()
    matches = difflib.get_close_matches(name_lower, valid_names, n=1, cutoff=0.7)
    return matches[0] if matches else None
```

Error message distinguishes typo from case-mismatch:

```
ERROR: unknown module 'XSS'.
Did you mean 'xss'? (Module names are case-sensitive.)
Available modules: headers, info-disclosure, paths, sqli, xss, ...
```

### Testbed detection — Story 5.4

```python
def detect_testbed(target_url: str) -> bool:
    """Story 5.4.E1: probe /__webprobe_testbed__/health, validate response shape.
    Returns True only on full match. Single attempt, no retry."""
    probe_url = urljoin(target_url, "/__webprobe_testbed__/health")
    headers = {"User-Agent": "webprobe/2.0 (testbed-detection)"}
    try:
        resp = requests.get(probe_url, headers=headers, timeout=DEFAULT_TIMEOUT)
    except RequestException:
        return False
    if resp.status_code != 200:
        return False
    if "application/json" not in resp.headers.get("Content-Type", ""):
        return False
    try:
        body = resp.json()
    except json.JSONDecodeError:
        return False
    return body.get("webprobe_testbed") is True


def _matches_testbed_url_pattern(target_url: str) -> bool:
    """Deterministic URL pattern check (urlparse netloc match). NOT fuzzy
    heuristic — _match_ prefix communicates exact pattern check."""
    parsed = urlparse(target_url)
    return parsed.netloc in {"localhost:9999", "127.0.0.1:9999"}
```

Engine Phase 3.5 caches result on `self._is_testbed`. If detection
fails AND `_matches_testbed_url_pattern(target_url)` is True, emit
INFO-style banner with actionable hint:

```
[!] Target host+port matches testbed convention (localhost:9999) but
    /__webprobe_testbed__/health probe failed.
    Risk gates remain active. If this IS the webprobe testbed, ensure
    the testbed harness is running with detection endpoint enabled.
```

### Risk gate filter logic — Stories 5.1, 5.2

```python
# PRD-locked gated module sets:
# - Story 5.1: brute_force needs DOUBLE gate
# - Story 5.2: access_control, idor need SINGLE gate
# - Story 7.3.E1: csrf needs SINGLE gate (state-mutating risk)
_GATED_DOUBLE: frozenset[str] = frozenset({"brute_force"})
_GATED_SINGLE: frozenset[str] = frozenset({"access_control", "idor", "csrf"})


def filter_modules_by_risk_gates(
    modules: list[type], args, is_testbed: bool
) -> tuple[list[type], list[type]]:
    if is_testbed:
        return modules, []                         # Story 5.4 bypass

    kept, dropped = [], []
    for cls in modules:
        if cls.name in _GATED_DOUBLE:
            if args.include_brute_force and args.i_own_this_target:
                kept.append(cls)
            else:
                dropped.append(cls)
        elif cls.name in _GATED_SINGLE:
            if args.i_own_this_target:
                kept.append(cls)
            else:
                dropped.append(cls)
        else:
            kept.append(cls)
    return kept, dropped
```

### Risk-gate banner — Story 5.3

Box-drawing frame for visual delimitation:

```
═══════════════════════════════════════════════════════════
Risk-gated modules disabled (default OFF for non-testbed targets):
  brute_force      Pass --include-brute-force --i-own-this-target=<host> to enable.
  access_control   Pass --i-own-this-target=<host> to enable.
  idor             Pass --i-own-this-target=<host> to enable.
  csrf             Pass --i-own-this-target=<host> to enable.
═══════════════════════════════════════════════════════════
```

Banner output begins and ends with box-drawing horizontal line
(`═` × 60). Visually distinguishes banner from scan output stream.
Renders to `self._terminal_stream` (NOT to HTML/TXT/JSON).

Banner suppressed when target is testbed, or when ALL risk-gated
modules are explicitly excluded via `--exclude-modules`.

### `--i-own-this-target` validation — Story 5.5

```python
def validate_i_own_this_target(target_url: str, asserted: Optional[str]) -> None:
    """Story 5.5 hostname binding. Raises ConfigurationError on mismatch.
    No-op when asserted is None.

    Edge case lock (rejects URL path/query in assertion):
    user might write --i-own-this-target=https://<deployment-url>/admin
    as a copy-paste mistake. Silent acceptance (parsing out hostname only)
    hides the input error. Explicit rejection prevents wrapper script from
    "working" with wrong assertion shape.
    """
    if asserted is None:
        return

    # Reject URL path/query before semantic validation
    if "://" in asserted:
        parsed = urlparse(asserted)
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ConfigurationError(
                f"--i-own-this-target value '{asserted}' contains URL path/query. "
                f"Assertion must be hostname or hostname:port only. "
                f"Try '--i-own-this-target={parsed.hostname}'."
            )
        asserted_parsed = parsed
    else:
        if "/" in asserted:
            raise ConfigurationError(
                f"--i-own-this-target value '{asserted}' contains '/'. "
                f"Assertion must be hostname or hostname:port only."
            )
        asserted_parsed = urlparse(f"//{asserted}")

    target_parsed = urlparse(target_url)
    if target_parsed.hostname is None or asserted_parsed.hostname is None:
        raise ConfigurationError("unable to parse hostname from target or assertion")

    if target_parsed.hostname.lower() != asserted_parsed.hostname.lower():
        raise ConfigurationError(
            f"--i-own-this-target asserts ownership of '{asserted}' but scan target "
            f"is '{target_parsed.hostname}'. The assertion must match the target "
            f"hostname; this prevents wrapper scripts from auto-asserting ownership "
            f"across changing targets."
        )

    if asserted_parsed.port is not None and target_parsed.port != asserted_parsed.port:
        raise ConfigurationError(
            f"--i-own-this-target port {asserted_parsed.port} does not match target "
            f"port {target_parsed.port}. Either omit the port from the assertion "
            f"(match any port on this hostname) or specify the target's exact port."
        )
```

### Testbed/validation truth table — invariant lock

```
User input              Target              Phase 0.5      Phase 3.5/3.6
--i-own-...=hostA       hostA               pass           gates active or testbed bypass
--i-own-...=hostA       hostB               FAIL           never reached
--i-own-...=lh:9999     localhost:9999      pass           testbed bypass
(not passed)            hostA               skip           gates drop modules
(not passed)            localhost:9999      skip           testbed bypass
```

**Testbed bypass replaces risk-gate filtering, NOT hostname validation.**
The two mechanisms are orthogonal — validation checks user-input
consistency, testbed detection checks target-environment safety. Build
shouldn't conflate them.

## Detection Modules (Epic 7)

Each module declares `(name, auth_strategy, source_filter,
FIT3048_CATEGORY_MAP, DATA_FILES)`, uses `_common.send` (and
`compare_responses` for IDOR/session/error_leakage), emits via
engine-wrapped `report_finding`. ≤50 lines.

### v1 module retrofit checklist

For each of headers, info_disclosure, paths, sqli, xss, traversal:

1. Add class attributes:
   - `auth_strategy = "unauth_always"` (paths)
   - `auth_strategy = "follow"` (headers, info_disclosure, sqli, xss, traversal)
   - `source_filter = frozenset({Source.CURATED, Source.ROBOTS, Source.URL_LIST})` (paths)
   - `source_filter = frozenset({Source.DYNAMIC, Source.URL_LIST})` (sqli)
   - `source_filter = frozenset({Source.DYNAMIC, Source.URL_LIST, Source.CURATED})` (xss)
   - `source_filter = ALL_SOURCES` (default — headers, info_disclosure, traversal)
2. Add `FIT3048_CATEGORY_MAP` with v1 internal type slugs as keys.
   Slugs locked at /spec from v1 implementation walk; not /build-tunable.
3. Replace `Finding(..., fit3048_category=N, ...)` with
   `Finding(..., finding_type="<slug>", ...)`. Engine wrapper fills
   fit3048_category.
4. Drop `return module_findings` from end of `run()` (Epic 6 (A) — `-> None`).
5. paths.py specifically: drop `load_default_paths()` call; drop
   `path_list=` kwarg in `__init__`; iterate `target.urls` filtered to
   source_filter instead.
6. sqli.py / xss.py / traversal.py: replace `from ._common import send`
   callers with `from ._common import inject_param` (Epic 6 rename).
7. Add `@register` decorator at class definition.
8. Verify ≤50 lines after retrofit. Helper extraction if needed.
9. **Audit existing v1 `print()` calls in module body — REMOVE ALL.**
   v2 module bodies MUST NOT call `print()` or write to stdout/stderr.
   All user-visible output via report_finding callback. Build-time
   verification: `grep -rn "print(" webprobe/modules/` returns zero
   matches in module bodies (excluding `_common.py`).

v1 internal type slugs to extract during /spec walk (locked):

- `headers.py`: `missing_csp`, `missing_hsts`, `missing_x_frame_options`,
  `cookie_no_secure`, `cookie_no_httponly`, `cookie_no_samesite`, ...
- `info_disclosure.py`: `email_in_html`, `internal_ip_in_html`,
  `comment_with_credential`, `meta_generator`, ...
- `paths.py`: `sensitive_path_exposed_high`, `sensitive_path_exposed_medium`,
  `sensitive_path_exposed_low` (3 severity tiers from one algorithm)
- `sqli.py`: `sqli_error_string`, `sqli_boolean_diff`
- `xss.py`: `reflected_xss`, `stored_xss_candidate`
- `traversal.py`: `path_traversal_unix`, `path_traversal_windows`

Process notes carry the v1→v2 slug mapping for /checklist verification.

### `access_control.py` — Story 7.1

```python
@register
class AccessControlModule(BaseModule):
    name = "access_control"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"role_violation": 2, "ambiguous_200_summary": 2}
    DATA_FILES = frozenset({"admin_paths.txt", "admin_signals.txt"})

    def __init__(self, args=None):
        super().__init__(args)
        self._signal_patterns_lower = [s.lower() for s in self._data["admin_signals.txt"]]

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        ambiguous = []
        for path in self._candidate_paths(target):
            url = urljoin(target.url, path)
            try:
                resp = send(url, session=s)
            except RequestException as e:
                self._on_request_error(url, e)
                continue
            if resp.status_code != 200:
                continue
            matched = _match_signal(resp.text, self._signal_patterns_lower)
            if matched:
                report_finding(Finding(
                    severity="HIGH", category="access_control",
                    finding_type="role_violation",
                    name=f"Admin-shape page reachable: {path}",
                    url=url,
                    evidence=f"HTTP 200, signal matched: '{matched}'",
                    remediation=_fix_hint(path),
                ))
            else:
                ambiguous.append(path)
        if ambiguous:
            report_finding(Finding(
                severity="INFO", category="access_control",
                finding_type="ambiguous_200_summary",
                name="probed admin-shape paths returned 200 without confirming signal",
                url=target.url,
                evidence=f"{len(ambiguous)} paths: {', '.join(ambiguous[:3])}",
                remediation="Review URLs manually — possible false negatives.",
            ))
```

`_candidate_paths`, `_match_signal`, `_fix_hint` extracted to
`_access_control_helpers.py` if module body crosses 50-line cap (likely).

### `idor.py` — Story 7.2

```python
@register
class IdorModule(BaseModule):
    name = "idor"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"cross_account_leak": 2, "idor_baseline_missing": 2,
                            "uuid_not_supported": 2}

    def run(self, target, session_factory, report_finding) -> None:
        sessions = session_factory()
        if len(sessions) < 2:
            report_finding(Finding(
                severity="INFO", category="idor",
                finding_type="idor_baseline_missing",
                name="idor-baseline-missing",
                url=target.url,
                evidence="IDOR detection requires --idor-baseline or "
                         "--idor-baseline-form for cross-account differential probing",
                remediation="Pass --idor-baseline-form <login-url>.",
            ))
            return

        s_a, s_b = sessions[0], sessions[1]
        candidates = [u for u, src in target.urls if _id_bearing(u)]

        if any(_uuid_in(u) for u in candidates):
            report_finding(Finding(
                severity="INFO", category="idor",
                finding_type="uuid_not_supported",
                name="UUID-based resource IDs detected; not enumerated in v2",
                url=target.url,
                evidence="UUID detection support is a Sprint 3+ candidate",
                remediation="Manual testing required for UUID-shaped resource IDs.",
            ))

        for url in candidates:
            try:
                resp_a = send(url, session=s_a)
                resp_b = send(url, session=s_b)
            except RequestException as e:
                self._on_request_error(url, e)
                continue
            if (resp_a.status_code == 200 and resp_b.status_code == 200
                    and compare_responses(resp_a, resp_b)):
                baseline_id = _extract_resource_id(url)
                report_finding(Finding(
                    severity="HIGH", category="idor",
                    finding_type="cross_account_leak",
                    name=f"IDOR — primary can read baseline's resource at {url}",
                    url=url,
                    evidence=f"sha256 body match between sessions",
                    baseline_context=f"baseline owns id={baseline_id}",
                    remediation=_fix_hint_idor(url),
                ))
```

`_id_bearing`, `_uuid_in`, `_extract_resource_id`, `_fix_hint_idor` in
`_idor_helpers.py` if needed. Patterns: `/<resource>/<numeric-id>`,
`/<resource>/view/<numeric-id>` (CakePHP), `?id=N`, `?<resource>_id=N`.

### `csrf.py` — Story 7.3

```python
@register
class CsrfModule(BaseModule):
    name = "csrf"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"csrf_missing": 2, "csrf_indeterminate": 2}

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        for form in target.forms:
            if form.method.upper() != "POST" or _off_host(form.action, target.url):
                continue
            payload = _strip_hidden_and_fill(form)
            try:
                resp = s.post(form.action, data=payload, allow_redirects=False,
                              timeout=DEFAULT_TIMEOUT)
            except RequestException as e:
                self._on_request_error(form.action, e)
                continue
            if resp.status_code in (403, 419):                # Laravel CSRF mismatch = 419
                continue                                       # correct protection
            if resp.status_code in (200, 302, 204):
                report_finding(Finding(
                    severity="HIGH", category="csrf",
                    finding_type="csrf_missing",
                    name=f"POST accepted without CSRF token: {form.action}",
                    url=form.action,
                    evidence=f"HTTP {resp.status_code} (expected 403 or 419)",
                    remediation="Add CSRF token validation to controller action.",
                ))
            else:
                report_finding(Finding(
                    severity="INFO", category="csrf",
                    finding_type="csrf_indeterminate",
                    name=f"POST returned unexpected status: HTTP {resp.status_code}",
                    url=form.action,
                    evidence=f"Cannot determine CSRF protection from this status",
                    remediation="Manual review.",
                ))
```

### `error_leakage.py` — Story 7.4

```python
@register
class ErrorLeakageModule(BaseModule):
    name = "error_leakage"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"username_enumeration_login": 7, "stack_trace_leakage": 1}
    DATA_FILES = frozenset({"stack_trace_patterns.txt"})

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        # Phase 1: user enumeration (Cat 7) — 2 POSTs
        if self.args.auth_form and self.args.auth_user:
            self._probe_user_enumeration(target, s, report_finding)
        # Phase 2: stack trace own probe set (Cat 1) per Story 7.4.E1
        for url in self._build_probe_set(target):
            try:
                resp = send(url, session=s)
            except RequestException as e:
                self._on_request_error(url, e)
                continue
            matched = _match_stack_trace(resp.text, self._data["stack_trace_patterns.txt"])
            if matched:
                report_finding(Finding(
                    severity="MEDIUM", category="error_leakage",
                    finding_type="stack_trace_leakage",
                    name=f"Stack trace exposed at {url}",
                    url=url,
                    evidence=matched[:200],
                    remediation="Disable debug error pages in production.",
                ))
```

`_probe_user_enumeration`, `_build_probe_set`, `_match_stack_trace` in
`_error_leakage_helpers.py` (likely needed — multi-phase probe set
construction + pattern matching).

### `session.py` — Story 7.5

```python
@register
class SessionModule(BaseModule):
    name = "session"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {
        "session_persists_post_logout": 7,
        "session_fixation": 7,
        "session_skipped_cookie_mode": 7,
        "logout_endpoint_not_found": 7,
    }

    def run(self, target, session_factory, report_finding) -> None:
        if not self.args.auth_form:
            report_finding(Finding(
                severity="INFO", category="session",
                finding_type="session_skipped_cookie_mode",
                name="session module skipped under --cookie mode",
                url=target.url,
                evidence="Post-logout cookie-replay test requires --auth-form to "
                         "create an ephemeral sub-session",
                remediation="Pass --auth-form to enable, or accept that "
                            "logout-correctness is not tested in this scan.",
            ))
            return

        from webprobe.auth import ephemeral_login_form
        ephemeral = ephemeral_login_form(
            target.url, self.args.auth_form, self.args.auth_user, self.args.auth_pass,
        )
        # Phase 1: post-logout cookie replay
        self._test_post_logout(target, ephemeral, report_finding)
        # Phase 2: session fixation (secondary check)
        self._test_session_fixation(target, report_finding)
```

`_test_post_logout`, `_test_session_fixation`, `_find_logout_url` in
`_session_helpers.py` (likely needed — multi-phase logic + heuristic
URL discovery).

### `brute_force.py` — Story 7.6

```python
@register
class BruteForceModule(BaseModule):
    name = "brute_force"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"no_lockout": 7, "weak_lockout": 7}
    DATA_FILES = frozenset({"lockout_signals.txt"})

    def run(self, target, session_factory, report_finding) -> None:
        responses = []
        for i in range(1, 7):
            try:
                resp = self._post_login_attempt(target, i)
            except RequestException as e:
                self._on_request_error(self.args.auth_form, e)
                return
            responses.append(resp)
            time.sleep(1.0)                          # Story 7.6: 1s between attempts

        if _all_identical(responses):
            report_finding(Finding(
                severity="MEDIUM", category="brute_force",
                finding_type="no_lockout",
                name="No lockout detected after 6 failed login attempts",
                url=self.args.auth_form,
                evidence="All 6 responses identical (status, redirect, body sha256)",
                remediation="Implement account lockout or rate limiting.",
            ))
        elif _matches_lockout_signal(responses[-1].text, self._data["lockout_signals.txt"]):
            return                                   # correct lockout
        else:
            report_finding(Finding(
                severity="INFO", category="brute_force",
                finding_type="weak_lockout",
                name="Responses vary across attempts but no clear lockout signal",
                url=self.args.auth_form,
                evidence="Possible weak rate limiting; manual review needed",
                remediation="Verify lockout policy; consider tightening threshold.",
            ))
```

## Data Files

```
webprobe/data/
├── paths/
│   └── curated.txt                     # v1 — engine-loaded (Source.CURATED)
├── access_control/
│   ├── admin_paths.txt                 # /admin/, /admin/users, /backoffice/, ...
│   └── admin_signals.txt               # All Users, Admin Dashboard, 管理后台, ...
├── error_leakage/
│   └── stack_trace_patterns.txt        # PHP/Python/Ruby/Java/generic regex patterns
└── brute_force/
    └── lockout_signals.txt             # account locked, 帐户已锁定, アカウントがロック..., ...
```

**Distinction (locked):** `DATA_FILES` = user-editable external files
(extension mechanism). Module-internal frozensets/dicts (e.g.,
`_GATED_DOUBLE` in `filter.py`, `_SHARED_SESSION_COOKIE_NAMES` in
`auth.py`) are code constants, NOT data files — they stay as Python
constants in the module file, spec-locked, not user-editable.

`/build` adds entries by editing the `.txt` files directly. Each file
opens with comment-block documenting purpose + when to add (`#`
prefix lines stripped by base `__init__` loader).

## Testbed (`webprobe/testbed/`)

PRD ref: `prd.md > scope.md > Sprint 2 Final Shape > item 3.5`.

Standalone Flask app, runnable via `python3 -m webprobe.testbed`
(binds to `localhost:9999`). Acceptance harness for v2 detection
modules.

```python
# webprobe/testbed/__main__.py — single-file Flask app, ~50-80 lines
from flask import Flask, request, jsonify, redirect, session, make_response

app = Flask(__name__)
app.secret_key = "webprobe-testbed-not-for-production"

# Story 5.4 detection endpoint (REQUIRED)
@app.route("/__webprobe_testbed__/health")
def health():
    return jsonify({"webprobe_testbed": True, "testbed_version": "2.0.0"})

# Deliberately-broken endpoints (one per detection module):
@app.route("/idor/<int:id>")
def idor(id):
    """No ownership check — IDOR module catches via cross-session match."""
    return jsonify({"id": id, "data": f"resource-{id}-data"})

@app.route("/admin/")
def admin_no_check():
    """No auth check — access_control module catches via admin signal."""
    return "<html><body><h1>Admin Dashboard</h1>All Users</body></html>"

@app.route("/csrf-broken", methods=["POST"])
def csrf_broken():
    """Accepts POST without CSRF token — csrf module catches via 200 response."""
    return jsonify({"status": "ok"})

@app.route("/login", methods=["POST"])
def login_no_lockout():
    """Accepts unlimited attempts — brute_force module catches via identical responses."""
    return "Invalid credentials", 401

@app.route("/login-locked", methods=["POST"])
def login_locked():
    """Locks after 5 attempts — brute_force module verifies lockout signal."""
    session["attempts"] = session.get("attempts", 0) + 1
    if session["attempts"] >= 5:
        return "Account locked. Too many attempts.", 429
    return "Invalid credentials", 401

@app.route("/reflect-xss")
def reflect_xss():
    """Reflects query unescaped — sanity check for v1 xss module."""
    q = request.args.get("q", "")
    return f"<html><body>You searched: {q}</body></html>"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9999, debug=False)
```

Acceptance: every Sprint 2 detection module fires at least one finding
when run against the testbed. Becomes a permanent acceptance harness
for all future detection modules.

## Concurrency Model

Inherited from v1 with two changes:

- `ThreadPoolExecutor(max_workers=20)` for `paths` module only (v1
  carryover). Auth-detection modules run serially.
- Thread-local Session pattern retired. v2 `session.py` returns eager
  list. paths.py workers share single `unauth_session` (requests.Session
  is documented thread-safe; v2 paths.py is `unauth_always` so no auth
  state on session = zero race surface).

Stdout lock owned by engine. Engine wraps `report_finding` callback in
`with self._stdout_lock:`. Modules call `report_finding(f)` from worker
threads safely without lock awareness.

## Error Handling

### Custom Exception Hierarchy

```
ConfigurationError              # auth.py — flag-combination invariant violations
                                # → engine catches at top level, sys.exit(2)

PasswordResolutionError         # auth.py — Phase 5a abort
LoginDiscoveryError             # auth.py — Phase 5b/5c abort
LoginValidationError            # auth.py — Phase 5b/5c abort
SitemapDiscoveryError           # discovery.py — Phase 4 / 5f abort
                                # → engine catches at top level, sys.exit(1)

RequestException (third-party)  # per-request failures
                                # → module's _on_request_error hook (default: silent skip)
```

### Connectivity Failure (HTTP-Layer)

v1 carryover. Phase 3 makes single GET; on `RequestException`, prints
`[-] Target unreachable. Check URL and try again.` + exception type, exits 1.

### Module Crash (Per-Module try/except)

Engine wraps each module's `run()` in try/except (Story 6.3). On
unhandled exception:
- Print `[!] {module.name}: errored ({type(e).__name__}) — skipped`
- Append `(module.name, exception)` to `self._errored_modules`
- Continue to next module

Run-end summary `Modules: N scheduled, M completed, K errored` reflects
this. `MODULES WITH ERRORS` block enumerated in render output.

### Hard Scan Ceiling

v1 carryover at 90s. Engine checks elapsed time before each module
dispatch. If exceeded, remaining modules added to `_errored_modules`
with `TimeoutError`, scan finalizes with current findings.

### Partial-Scan Trust Signal

v1 carryover. `args.partial = True` if any of:
- Any module errored
- Scan ceiling hit
- Any module set `self.degraded = True` (3-consecutive-failure heuristic)

Run-end summary prints `⚠ Partial scan` flag. Junior dev never mistakes
a partial scan for clean target.

## Dependencies & External Services

External code (declared in `pyproject.toml`):
- [`requests`](https://requests.readthedocs.io/en/latest/) — HTTP client.
- [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
  — HTML parsing.
- [`colorama`](https://pypi.org/project/colorama/) — Windows ANSI.
- [`Flask`](https://flask.palletsprojects.com/en/stable/) — testbed only
  (`[project.optional-dependencies]` group `testbed`).

Stdlib (no install needed):
- `xml.etree.ElementTree`, `urllib.parse`, `getpass`, `difflib.get_close_matches`,
  `importlib.resources.files`, `hashlib.sha256`, `threading.Lock`,
  `concurrent.futures.ThreadPoolExecutor`, `dataclasses`, `enum.Enum`,
  `typing.Literal`, `argparse`.

External services: **none.** Outbound HTTP only to user-supplied target
+ optional testbed when running locally.

Browser APIs (HTML report):
- [Clipboard API](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText)
- [Selection API](https://developer.mozilla.org/en-US/docs/Web/API/Selection)
- [Range API](https://developer.mozilla.org/en-US/docs/Web/API/Range)

`pyproject.toml` skeleton:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "webprobe"
version = "2.0.0"
description = "A small, legible web vulnerability scanner."
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "colorama>=0.4.6",
]

[project.optional-dependencies]
testbed = ["Flask>=3.0"]

[project.scripts]
webprobe = "webprobe.probe:main"

[tool.setuptools.package-data]
"webprobe.data" = ["**/*.txt"]
```

## Key Technical Decisions

1. **`run()` returns `None`, not `list[Finding]`.** Engine-wrapped
   callback enforces all v2 invariants (auth_context injection,
   evidence_hash auto-compute, dedup eligibility, stdout lock). Findings
   that bypass the wrapper (returned via list) violate every invariant.
   Single-channel discipline. v1 dual-channel was historical artifact;
   v2 retires it.

2. **`finding_type` separated from `category`.** v1's `category`
   ("sqli", "headers", "cookies") is module-identity slug. v2 adds
   `finding_type` ("missing_csp", "role_violation", "cross_account_leak")
   as the FIT3048_CATEGORY_MAP lookup key. Single-responsibility per
   dataclass field — category groups for JSON dedup; finding_type maps
   to FIT3048 categories.

3. **`Source` enum + `findings.py` as type-definition-only module.**
   findings.py owns shape (dataclasses, enums, validation invariants).
   Helpers acting on findings live elsewhere (engine for dedup; renderers
   for display; serializers for JSON). Cross-sprint scope discipline
   prevents "junk drawer" expansion.

4. **`Target.urls = tuple[tuple[str, Source], ...]` with engine-time
   freeze.** Python's type system enforces "MUST NOT mutate" — module
   `target.urls.append(...)` raises AttributeError. Zero overhead.
   Sprint 3+ migration to `ProbeURL` dataclass is mechanical.

5. **`webprobe/discovery.py` + target.py-stays-thin split.** target.py
   keeps form/query_params discovery (v1 contract preserved). discovery.py
   owns URL pool composition (5 source functions × dedup × freeze).
   Single-responsibility per file.

6. **Curated paths move from paths.py to engine URL pool — v1→v2
   architectural shift.** paths.py becomes contract-uniform; URL pool is
   single source of truth; cross-source dedup applies to curated entries;
   COVERAGE accuracy improves.

7. **Engine class + closure-captured callbacks (no mutable engine
   state for context-dependent injection).** Each per-module-per-pass
   dispatch builds fresh wrapped `report_finding` closing over immutable
   values + designed-for-concurrency primitives (lock, GIL-atomic list
   append). Avoids "current_X attribute" thread-safety pitfalls.

8. **`webprobe/auth.py` single file (not subpackage).** ~5 functions,
   ~30-50 lines. Subpackage premature; folding into session.py muddles
   factory-vs-credential-exchange concerns. Sprint 3+ SSO addition
   refactors to `auth/` subpackage when needed.

9. **`webprobe/registry.py` + `@register` decorator.** Module discovery
   pattern formalized for v2. Auto-extends to Sprint 3+ additions
   (decorator + import in `modules/__init__.py` is the only edit).

10. **`webprobe/filter.py` for pre-dispatch decision logic.**
    `engine.py` Phase 6 dispatches; `filter.py` decides which modules
    reach dispatch. ~80-120 lines; subpackage premature.

11. **`webprobe/coverage.py` + sub-dataclasses.** ScanCoverage +
    ScanMetadata as typed containers. dataclass shape == JSON shape
    (Story 3.4); `dataclasses.asdict()` produces envelope verbatim.
    Survives engine teardown; AttributeError on field-name typo at
    runtime; semver-clean field additions.

12. **`--json-out -` routes terminal output to stderr (Unix
    convention).** stdout reserved for JSON. `webprobe target
    --json-out - | jq '.findings'` works; user sees scan progress on
    stderr. NEVER bare `print()` in renderer code.

13. **Module body invariants (5 cross-cutting Locks).** kw_only Finding,
    urljoin (no string concat), `_on_request_error` (no bare except),
    args uniform injection, zero `print()`. Build-time grep verification
    for Lock 5.

14. **DATA_FILES uniform contract on BaseModule.** Base `__init__`
    produces canonical parsed form (stripped non-comment lines).
    Module-specific post-processing (regex compile, case folding) in
    module's own `__init__` after `super().__init__(args)` call.
    Loading is contract-uniform; usage is module-specific.

15. **Helper file extraction is REACTIVE, not pre-allocated.** `/build`
    creates `_<module>_helpers.py` only when module body crosses 50-line
    cap. Extends Sprint 1's reactive-helper discipline.

## PRD Loop-Backs / Spec Additions

Items where /spec resolved a PRD-level ambiguity, derived a PRD-implicit
shift, or added a constraint not anticipated by /prd. /reflect should
propagate these to a PRD amendment if Sprint 2 PRD is re-published:

1. **`run()` return type: PRD says "unchanged from Sprint 1: -> None"
   but v1 actual is `-> list[Finding]`.** /spec resolves to `-> None`
   (Epic 6 (A)). Drop v1 return statements (6 lines).

2. **`finding_type` field added to Finding.** PRD Story 6.4 implies it
   ("looked up from FIT3048_CATEGORY_MAP by finding-type key at emit
   time") but doesn't formally introduce it as a Finding field. /spec
   adds it; v1 modules retrofit per Epic 7 (E).

3. **`Finding.fit3048_category: Optional[int] = None` during
   construction.** PRD Story 6.2 says "Required field, must be in 1..10"
   — but Story 6.4 has engine wrapper inject the value. /spec resolves:
   Optional during construction; engine wrapper guarantees non-None
   before storage; `__post_init__` validates range only when non-None.
   Same pattern for `auth_context` and `seen_in`. `evidence_hash` is
   self-contained (auto-computed in `__post_init__`).

4. **Phase 0.5 inter-flag validation introduced.** Extends Epic 1 (1F)
   pattern. Engine never relies on argparse for cross-flag invariants;
   consuming modules own them. Catches everything before any HTTP.

5. **Phase 4.5 / 5f authed-sitemap-discovery surfaced.** PRD didn't
   anticipate ordering: `--use-sitemap-authed` requires auth setup
   complete. /spec splits sitemap discovery between Phase 4 (unauth
   default) and Phase 5f (authed if flag set).

6. **Phase 7 dedup phase boundary explicit.** PRD said dedup "at engine
   layer"; /spec pins to between Phase 6 dispatch and Phase 8 render.
   Inline tease prints findings TWICE for `--scan-both`; final report
   shows once with merged `seen_in`. Both correct because they occur at
   different phases.

7. **Curated paths v1→v2 architectural shift.** PRD didn't make
   explicit; /spec derived from `source_filter` contract + Story 6.3
   "module body MUST NOT introspect engine state". paths.py loses
   curated.txt loading; engine URL pool gains it.

8. **Module registry pattern formalization (`@register`).** Replaces
   v1's hardcoded MODULES manifest. PRD Story 4.1 module-name validation
   needs a single source of truth; registry provides it.

9. **Cross-flag gated-module-in-include validation lists ALL missing
   gates at once.** Extends Sprint 1 actionable-error pattern. User
   fixes once, retries once.

10. **Testbed-bypass-replaces-risk-gates-NOT-hostname-validation
    invariant.** Two mechanisms are orthogonal — validation checks
    user-input consistency, testbed detection checks target-environment
    safety.

11. **`--i-own-this-target` rejects URL path/query in assertion shape.**
    Input-shape validation before semantic validation.

12. **DATA_FILES uniform contract.** Base `__init__` loads canonical
    form; modules post-process. `super().__init__(args)` discipline.
    paths.py inherits empty default (no explicit declaration).

13. **Helper files reactive (not pre-allocated).** `/build` creates
    `_<module>_helpers.py` only on overflow. Sprint 1 reactive-helper
    discipline carried forward.

14. **Finding `kw_only=True` dataclass discipline.** Forbids positional
    construction. Module body always reads as
    `Finding(severity="HIGH", category="csrf", finding_type=..., ...)`.

15. **`urljoin` enforcement (no string concatenation for URLs).** Prevents
    trailing-slash boundary bugs.

16. **`RequestException` uniform handling via `_on_request_error` hook.**
    No bare `except Exception` (swallows programmer bugs); no bare
    `except:` (swallows KeyboardInterrupt).

17. **args uniform injection (no per-module asymmetry).** Engine always
    passes args; modules ignore if not needed.

18. **Zero `print()` in module bodies.** All user-visible output via
    `report_finding`. Engine wrapper handles routing, locking, ANSI.
    Build-time grep verification.

19. **`verbose=False` parameter on `setup_form_login` for ephemeral
    suppression.** PRD didn't anticipate ephemeral session printing
    "[+] Login confirmed" mid-scan would be confusing.

20. **Phase 5 abort/continue table.** PRD Stories 1.1/1.3 specify abort
    behavior; /spec pins exact sub-phase boundaries.

21. **argparse argument_groups verbatim taxonomy lock.** Group titles
    match PRD Q5(a) verbatim. /build can tune flag wording but MUST NOT
    rename groups.

## Open Issues — Spec → /build Handoff

Items deliberately unresolved at /spec level — implementation details
below the spec/build line. Each lands as a /checklist build-time
decision:

- **SQLi `DIFF_THRESHOLD` re-tuning.** Sprint 1 left at 0.30 with
  auditable-constant pattern. Sprint 2 doesn't change unless <iteration 2>
  audit surfaces a known SQLi missed by 0.30. /build Checkpoint A may
  revisit.
- **Banner exact wording, `--help` flag descriptions, `--version`
  output.** Format pinned (PRD Q5(a) taxonomy + skeleton); literal
  strings are /build.
- **paths.py pool sizing.** /build Checkpoint B paths.py runtime check;
  if v2 paths.py is >15% slower than Sprint 1's 11.8s on FIT3047, apply
  explicit `pool_maxsize=20` mount.
- **Verbose `[.]` line format.** v1 carryover; exact format strings
  /build.
- **Module-error one-line tips.** Default `Tip: re-run with -v for more
  detail.` is sufficient; targeted tips per exception type are
  nice-to-have.
- **`--scan-both` mode-line flavor in run-end summary.** PRD shows
  `Modules: 10 scheduled, 10 completed (5 of 10 ran twice via
  --scan-both)`; exact wording /build.
- **HTML CSS palette refinement.** Story 3.3 PRD locks color
  semantics (white background, severity colors); pixel-level CSS is
  /build.

## /checklist Carryover

Walk down this spec's section list and produce one checklist item per
granular subsection. The spec was written with /checklist addressability
in mind — every subsection is a candidate item.

- Decide build mode (step-by-step vs autonomous) up front; Sprint 1
  /reflect pattern (autonomous + named checkpoints) likely applies.
- Pre-build verification: `BaseModule` contract test (instantiate every
  module class, dispatch a no-op `Target`, assert no exceptions) is
  worth its own checklist item.
- 50-line constraint is a *checklist verification step* (Checkpoint B),
  not a build-time aspiration. Each module's checklist item should
  include `wc -l` check.
- Build-time grep verifications (Lock 5: zero `print()` in modules;
  IDOR-conditional render expression in exactly two locations) are
  /checklist items.
- Phase 0.5 / Phase 5 abort tables are /checklist verification beats.
- Testbed item (3.5): standalone Flask app must work end-to-end as
  acceptance harness before any v2 detection module can be properly
  validated.
- v1 module retrofit checklist (Epic 7 (E), 9 steps × 6 modules) =
  6 atomic /checklist items.
- v1→v2 architectural shift items (curated paths move, session.py
  rewrite, target.py contract preservation) are atomic /checklist
  items, not folded into module retrofits.
