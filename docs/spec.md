# WebProbe — Technical Spec

## Stack

- **Python 3.10+** (PEP 604 union types, modern dataclasses, `match` available
  if useful). Universal on any current dev machine.
- **`requests` 2.31+** — HTTP client. Connection pooling per `Session`,
  `data=` form encoding for SQLi/XSS POSTs, per-request `timeout=` kwarg.
  ([requests docs](https://requests.readthedocs.io/en/latest/))
- **`beautifulsoup4` 4.12+** — HTML parsing for `<form>` and `<input>`
  discovery. Default parser `html.parser` (stdlib) — keeps the dependency
  graph minimal; `lxml` is *not* required.
  ([bs4 docs](https://www.crummy.com/software/BeautifulSoup/bs4/doc/))
- **`colorama` 0.4.6+** — cross-platform ANSI on Windows lab terminals.
  `colorama.init(autoreset=False)` so the runner controls reset.
  ([colorama on PyPI](https://pypi.org/project/colorama/))
- **stdlib only** for everything else: `argparse`, `dataclasses`,
  `urllib.parse`, `concurrent.futures.ThreadPoolExecutor`, `threading.local`,
  `threading.Lock`, `pathlib`, `datetime`, `html` (for `html.escape`),
  `pkgutil` / `importlib.resources` (for path-list loading).

`requirements.txt`:

```
requests>=2.31
beautifulsoup4>=4.12
colorama>=0.4.6
```

Three lines. Trivially auditable. Aligned with the legibility commitment in
`scope.md > Architectural constraints` and the install-must-be-trivial bar
in `prd.md > Project Context`.

## Runtime & Deployment

- **CLI tool, runs locally** on the author's machine.
- Targets: `http://localhost:*`, `http://127.0.0.1:*`, public `https://...`.
  No flag changes between localhost and public targets.
- **No server, no Docker, no Java, no system deps** beyond Python 3.10+.
  Install + run is `git clone <repo> && pip install -r requirements.txt &&
  python3 webprobe/probe.py <target>`.
- Reports written to `cwd` by default; `--output <dir>` overrides.
- Demo deliverable: terminal screenshot + `report.html` + `report.txt`,
  pasted into the FIT3047 reflective diary and the FIT3048 peer-assessment
  artifact. No deployed URL needed.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  probe.py (CLI entrypoint, ~30 lines)                        │
│    │                                                         │
│    ▼  argparse → engine.run(args)                            │
└────┼─────────────────────────────────────────────────────────┘
     ▼
┌──────────────────────────────────────────────────────────────┐
│  engine.py (orchestration)                                   │
│    │                                                         │
│    ├─ print_banner()                                         │
│    ├─ check_connectivity()  ── 1 GET, timeout=5              │
│    │     │   fail → "[-] Target unreachable" → exit(1)       │
│    │     ▼   success → base_response                         │
│    ├─ discover_target(url, base_response) → Target           │
│    │     parse failure → "[!] form discovery failed",        │
│    │                     proceed with Target.forms=[]        │
│    ├─ build_active_modules(args)                             │
│    │     resolves --only / --include-traversal / --cakephp   │
│    │     into ordered list of module instances with          │
│    │     pre-resolved config                                 │
│    └─ for module in active_modules:                          │
│          try:                                                │
│              findings += module.run(target,                  │
│                                     session_factory,         │
│                                     report_finding)          │
│          except Exception as e:                              │
│              "[!] {name}: errored ({type}) — skipped"        │
│              errored_modules.append(...)                     │
│                                                              │
│        ▼ stdout-locked: report_finding emits inline tease    │
└──────────────────────────────────────────────────────────────┘
     ▼
┌──────────────────────────────────────────────────────────────┐
│  output sinks (consume the same finding list)                │
│    │                                                         │
│    ├─ terminal.py → === FINDINGS === block + summary         │
│    ├─ html.py     → webprobe_<host>_<port>_<ts>.html         │
│    └─ txt.py      → webprobe_<host>_<port>_<ts>.txt          │
└──────────────────────────────────────────────────────────────┘
```

Single-process, single-pass pipeline. Only the `paths` module is internally
threaded (via `ThreadPoolExecutor(max_workers=20)`); everything else stays
sequential on the main thread. The engine itself is thread-naive — it
hands modules a `session_factory` callable and a stdout-locked
`report_finding` callable, and modules decide internally whether to call
them sequentially or from worker threads.

## Engine

### probe.py — CLI Entrypoint

~30 lines. Imports `argparse` and `engine`. Builds the `ArgumentParser`,
parses, dispatches to `engine.run(args)`. Catches `KeyboardInterrupt` and
exits with a clean `[-]` line. No detection logic, no rendering — pure
dispatch.

### Argument Parsing

CLI surface pinned by `prd.md > CLI Surface (v1)`:

```
python3 webprobe/probe.py <target_url> [flags]

Positional:
  target_url                Required. http://localhost:*, http://127.0.0.1:*,
                            or public https://... — no flag differentiates them.

Flags:
  --only sqli,xss           Comma-separated subset of {sqli, xss, paths,
                            headers, info-disclosure, traversal}.
                            Invalid name → fail fast with valid list, exit 2.
  --output ./reports/       Output directory. Default: cwd.
                            Filenames are auto-generated; never user-controlled.
  --cakephp                 Activate CakePHP framework profile.
  --fit3048                 Group HTML report by FIT3048 category (1–10) →
                            severity nested. Inline tease unaffected.
  --include-traversal       Opt in to the directory-traversal module.
  --no-color                Force ANSI off.
  --force-color             Force ANSI on.
  -v                        Verbose: print every path and payload attempted,
                            prefixed with `[.]`. No -vv.
```

`argparse` description + epilog should advertise the FIT3047 / FIT3048 use
case and end with: *"For full HTTP traces, manual fuzzing, or an
intercepting proxy, use Burp Suite — WebProbe doesn't replace it."*

### Banner

PRD ref: `prd.md > Epic 1 > "see what coverage I'm getting"`.

Printed to stdout before any module runs. Terse — under 6 lines, no ASCII
art. Includes: tool name + version, target URL, list of active module
slugs, active framework profile (or `none`), and an explicit mention of
traversal as opt-in if `--include-traversal` was *not* set:
`(traversal: opt-in via --include-traversal)`. Separator line after.

Exact text is a `/build` concern, not pinned here.

### Connectivity Check

PRD ref: `prd.md > Epic 1 > "confirm the target is reachable"`.

```
print "[*] Checking target reachability..."
try:
    base_response = session.get(target_url, timeout=5,
                                allow_redirects=True)
    print f"[+] Target responding (HTTP {base_response.status_code}, "
          f"{elapsed:.1f}s)"
except (ConnectionError, Timeout, RequestException) as e:
    print "[-] Target unreachable. Check URL and try again."
    sys.exit(1)
```

The connectivity GET *is* the form-discovery / `Target.base_response`
GET. One HTTP roundtrip. Connectivity is an HTTP-layer concern; form
discovery is an application-layer concern; the two failure modes are
separated cleanly — see [Error Handling](#error-handling).

### Target Discovery

`webprobe/target.py`. Single function:

```python
def discover_target(url: str, response: requests.Response,
                    profile: Optional[str]) -> Target:
    """
    Build a Target from the response of the connectivity GET.
    Parse forms via BeautifulSoup, extract URL query params via urllib.parse.
    Returns a Target with forms=[] on parse failure (logged via [!]).
    """
```

- Forms: `BeautifulSoup(response.text, "html.parser").find_all("form")` →
  for each, build `Form(action=resolved_absolute_url, method=method.upper(),
  fields={input_name: default_value, ...})`. Inputs of type `submit`,
  `button`, `image` are excluded — they're not injectable parameters.
- Query params: `urllib.parse.urlparse(url).query` → `parse_qs` →
  flatten to `dict[str, str]`.
- On `BeautifulSoup` exception (encoding error, malformed body): log
  `[!] form discovery failed ({ExceptionType}) — proceeding with no forms`,
  return `Target(forms=[], query_params=parsed_or_empty, ...)`. Scan
  continues. Modules that need forms (`sqli`, `xss`) will return zero
  findings against an empty form list — that's correct, not an error.

### Module Dispatch

`engine.run` builds `active_modules` then loops:

```python
findings: list[Finding] = []
errored_modules: list[tuple[str, Exception]] = []
stdout_lock = threading.Lock()

def report_finding(f: Finding) -> None:
    with stdout_lock:
        terminal.render_inline_tease(f, args)

session_factory = make_thread_local_session_factory(args)

for module in active_modules:
    print(f"[*] Running: {module.name}...")
    try:
        findings.extend(
            module.run(target, session_factory, report_finding)
        )
    except Exception as e:
        with stdout_lock:
            print(f"[!] {module.name}: errored "
                  f"({type(e).__name__}) — skipped")
        errored_modules.append((module.name, e))
```

The lock is held for the duration of *one* tease line, not the whole
module run. Threaded modules acquire it briefly per finding; sequential
modules incur essentially zero contention.

After the loop: hand `(findings, errored_modules, args, target)` to each
output sink in turn (terminal → html → txt → summary).

## BaseModule Contract

PRD ref: `prd.md > Epic 5 > "adding a new detection module to be a
single-file drop-in"`.

`webprobe/modules/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Callable
from requests import Session

from webprobe.findings import Finding, Target

class BaseModule(ABC):
    """Every detection module subclasses this. ≤50 lines per concrete module."""

    name: str       # class attribute, e.g. "sqli". Used in CLI --only and tease lines.
    category: str   # short slug. Often equals `name`; differs only for headers,
                    # which produces both "headers" and "cookies" categories
                    # at the per-Finding level (severity differs by source).

    @abstractmethod
    def run(
        self,
        target: Target,
        session_factory: Callable[[], Session],
        report_finding: Callable[[Finding], None],
    ) -> list[Finding]:
        """
        Run this module against `target`.

        - `session_factory()` returns a thread-local requests.Session. Sequential
          modules call once and reuse; threaded modules call inside each worker.
        - `report_finding(f)` emits the inline [SEVERITY] tease line at the
          moment of detection. Engine wraps this in a stdout lock — modules
          can call from worker threads safely.
        - Returns the same findings the module reported via the callback,
          in module-internal order. The engine uses the return value for
          per-module accounting; the callback drives real-time output.

        Both channels are populated. Redundant by design — they serve
        different consumers.
        """
```

### Module Registration

`webprobe/modules/__init__.py` exports a manifest:

```python
MODULES: list[type[BaseModule]] = [
    HeadersModule,         # fast, single-response parse
    InfoDisclosureModule,  # passive, zero-FP, parses same response
    PathsModule,           # threaded, ~150 requests, ~3s on a healthy target
    SqliModule,            # per-param, sequential
    XssModule,             # per-param, sequential
    TraversalModule,       # opt-in only; included in manifest, gated by engine
]
```

Order is execution order. Cheap-and-deterministic first; per-param-and-slow
last; opt-in module last of all. Rationale: if the 90s scan ceiling fires
mid-run, the user has already received the high-value-low-cost findings.

Adding a 7th module = creating `webprobe/modules/<name>.py` and appending
its class to this list. No engine changes. This is the contribution
affordance.

### Instantiation Pattern (engine pre-resolves config)

PRD ref: `prd.md > Open Questions > "how each module declares its config"`.

Decided model: **engine pre-filters flags into per-module `__init__`
config**. Modules never see flag state; they get clean parameters.

```python
def build_active_modules(args) -> list[BaseModule]:
    selected = parse_only_flag(args.only) or DEFAULT_MODULE_SLUGS
    if not args.include_traversal:
        selected.discard("traversal")

    instances = []
    for cls in MODULES:
        if cls.name not in selected:
            continue
        if cls is PathsModule:
            instances.append(PathsModule(
                path_list=load_default_paths()
                          + (CAKEPHP_PATHS if args.cakephp else [])
            ))
        else:
            instances.append(cls())  # no per-module config in v1
    return instances
```

This keeps `run()` bodies free of `if not args.aggressive: skip_payload`
ceremony. Every per-module knob lives in `__init__`. Sprint 2's
`--aggressive` flag will set `SqliModule(include_time_based=True)` —
same pattern, no engine plumbing change.

## Data Model

`webprobe/findings.py`:

### Finding

PRD ref: `prd.md > Data Model — Finding Object`.

```python
SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

@dataclass
class Finding:
    severity: str             # one of SEVERITY_ORDER
    category: str             # "sqli" | "xss" | "paths" | "headers" |
                              # "cookies" | "info-disclosure" | "traversal"
    name: str                 # human-readable, e.g. "Reflected XSS"
    url: str                  # where it was found
    parameter: Optional[str]  # form field / query param (None for passive)
    payload: Optional[str]    # injected string (None for passive)
    evidence: str             # one-line "why we believe this"
    poc_url: Optional[str]    # click-to-verify (None for passive)
    remediation: str          # one-line fix hint
    fit3048_category: int     # 1–10

    def __post_init__(self):
        assert self.severity in SEVERITY_ORDER, \
            f"invalid severity: {self.severity}"
        assert 1 <= self.fit3048_category <= 10, \
            f"fit3048_category out of range: {self.fit3048_category}"
```

**Severity is on Finding, not on BaseModule.** The `paths` module produces
`HIGH` for `.env`, `MEDIUM` for `phpinfo.php`, `LOW` for `*.bak` — one
algorithm, multiple severity outputs. Module-level severity would force
splitting one module into three, which is wrong.

**`fit3048_category` is on Finding, not on BaseModule.** The `headers`
module produces Category 5 (CSP missing → input validation defense) AND
Category 4 (cookie HttpOnly missing → session management) in the same
pass. Mapping is per-condition.

### Form

```python
@dataclass
class Form:
    action: str             # absolute URL (resolved against target.url)
    method: str             # "GET" | "POST"
    fields: dict[str, str]  # field_name → default_value (excluding submit/button)
```

### Target

```python
@dataclass
class Target:
    url: str                          # user-supplied URL
    base_response: requests.Response  # connectivity-check GET, shared
    forms: list[Form]                 # discovered <form> elements
    query_params: dict[str, str]      # parsed from url
    profile: Optional[str]            # "cakephp" or None
```

`base_response` is the canonical shared response. The `headers` and
`info-disclosure` modules both read it without re-fetching. SQLi and XSS
modules use the URL + `query_params` + `forms` and issue their own
requests via the session factory.

## Detection Modules

Every concrete module file is **≤50 lines of Python**, non-negotiable.
This is the project's central legibility commitment from `scope.md`.

### sqli — webprobe/modules/sqli.py

PRD ref: `prd.md > Epic 2 > "SQL injection on form fields and URL params"`.

- **Payloads (v1, exact list):**
  `'`, `"`, `1'`, `1' OR '1'='1`, `1' AND '1'='2`, `1 AND 1=1`, `1 AND 1=2`.
  Time-based `1' AND SLEEP(1)--` is **not in v1** — gated to Sprint 2's
  `--aggressive` flag via `SqliModule(include_time_based=True)`.
- **Detection signals:**
  - **Boolean-differential.** Send the `OR '1'='1` and `AND '1'='2` (and
    integer-form `1=1` / `1=2`) pairs against the same parameter. If
    responses differ *materially* (threshold left to /build — likely a
    response-length delta > N% or a status-code change), flag `HIGH`.
  - **Error-based.** Inspect response body for SQL error fingerprints:
    `SQLSTATE`, `mysql_fetch_array`, `MariaDB`, `ORA-`, `SQLite3::`,
    `PostgreSQL`, `unclosed quotation mark`. Any match → `HIGH`.
- **Targets:** every `Target.query_params` entry, plus every field of
  every `Target.form` (POST or GET-action form, both supported).
- **Per-param payload sequence is sequential.** Differential detection
  needs ordered request/response pairs to attribute the differential
  correctly.
- **Evidence string format:** include the differentiator inline, e.g.
  `Evidence: 'OR '1'='1' returned 47KB; 'AND '1'='2' returned 0KB`.
- **Severity:** always `HIGH` in v1.
- **`fit3048_category`:** `5` (Input Validation and Error Handling).
- **Threshold for "materially differs":** **deferred to /build.** Spec
  says "configurable threshold," not "exactly N%." Implementation will
  pin a default that v1 manual-tests against the FIT3047 login form.

### xss — webprobe/modules/xss.py

PRD ref: `prd.md > Epic 2 > "reflected XSS detection"`.

- **Payloads (v1, exact list):**
  - `<script>alert(1)</script>`
  - `"><svg/onload=alert(1)>`
  - `'><img src=x onerror=alert(1)>`
  - `javascript:alert(1)`
  - `<body onload=alert(1)>`
  - `'"><script>alert(1)</script>`
- **Detection:** payload appears in the response body **unescaped**.
  Implementation reads the response body as text and checks
  `payload in response.text` *after* eliminating HTML-escaped variants
  (`&lt;script&gt;` should not count). Match → `HIGH`.
- **POC URL construction (DalFox-style):** `target.url` with the
  matching payload URL-encoded into the parameter. Click-ready in any
  browser.
- **Targets:** same surface as sqli — every query param + every form
  field.
- **Severity:** always `HIGH`.
- **`fit3048_category`:** `5`.

### paths — webprobe/modules/paths.py

PRD ref: `prd.md > Epic 2 > "exposed sensitive paths"`.

- **Default path list:** loaded from
  `webprobe/data/paths/curated.txt`, ~150 paths newline-delimited.
  Includes (per PRD): `/.env`, `/.git/HEAD`, `/.git/config`,
  `/phpinfo.php`, `/info.php`, `/server-status`, `/backup.sql`,
  `/db.sql`, plus `*.bak` and `*.old` variants.
- **`--cakephp` adds:** `/webroot/debug_kit/`, `/debug-kit/`, `/logs/`,
  `/tmp/`, `/config/app.php`, `/config/app_local.php`. Engine merges
  these into `path_list` at instantiation; module sees one resolved list.
- **HTTP behavior:** GET each path against
  `urljoin(target.url, "/")` (host root, ignoring path component of
  user-supplied URL).
  - `200`, `301`, `302`, `403` → flagged.
  - `404` → not flagged.
  - Other 5xx counts as a degraded-target signal (see [Error Handling]).
- **Threading:** `ThreadPoolExecutor(max_workers=20)`. Each worker calls
  `session_factory()` to get its own thread-local `Session`. Every
  worker calls `report_finding(f)` directly when it finds a hit; the
  engine's stdout lock serializes the tease lines. Per-thread Session
  keeps connection-pooling effective without sharing state.
- **Severity assignment (PRD-pinned):**
  - `HIGH`: `/.env`, `/.git/*`, `/config/app_local.php`, `/backup.sql`,
    `/db.sql`.
  - `MEDIUM`: `/phpinfo.php`, `/info.php`, `/debug-kit/`, `/webroot/debug_kit/`.
  - `LOW`: `*.bak`, `*.old`.
  - Default for other 200/403 hits: `MEDIUM`.
- **`fit3048_category`:** `3` (Sensitive Information Exposure).

### headers — webprobe/modules/headers.py

PRD ref: `prd.md > Epic 2 > "missing security headers and unsafe cookie flags"`.

- **No HTTP request.** Reads `target.base_response.headers` and
  `target.base_response.cookies` directly.
- **Header checks (missing → finding):**
  - `Content-Security-Policy` → `MEDIUM`, category `5`.
  - `X-Frame-Options` → `MEDIUM`, category `5`.
  - `Strict-Transport-Security` (only if URL is `https://`) → `HIGH`,
    category `5`.
  - `X-Content-Type-Options` → `LOW`, category `5`.
  - `Referrer-Policy` → `LOW`, category `5`.
- **Cookie checks** (per `Set-Cookie` returned):
  - Missing `HttpOnly` → `MEDIUM`, category `4`.
  - Missing `Secure` (only if URL is `https://`) → `HIGH`, category `4`.
  - Missing `SameSite=Strict|Lax` → `LOW`, category `4`.
  - `Finding.category` is `"cookies"` (not `"headers"`) for cookie findings,
    distinct from the `BaseModule.name` of `"headers"`. This is the only
    case where a module emits findings under a different category slug
    than its name.

### info-disclosure — webprobe/modules/info_disclosure.py

PRD ref: `prd.md > Epic 2 > "passive info-disclosure findings"`.

- **No HTTP request.** Reads `target.base_response.headers` and
  `target.base_response.text`.
- **Checks:**
  - `Server` header banner → `LOW`, category `3`.
  - `X-Powered-By` header → `LOW`, category `3`.
  - HTML comments (`<!-- ... -->`) containing `TODO`, `FIXME`, or
    URL-like substrings (`http://`, `https://`, `localhost`, internal
    IPs) → `MEDIUM`, category `3`.
  - Stack-trace fingerprints in body: `Traceback (most recent call last)`,
    `at java.lang.`, `Stack trace:`, `Warning: ` (PHP),
    `Notice: ` (PHP) → `MEDIUM`, category `3`.
- **Zero false-positive risk by design.** Only reports what's
  objectively present in the response.

### traversal — webprobe/modules/traversal.py

PRD ref: `prd.md > Epic 2 > "directory-traversal detection — opt-in"`.

- **OFF by default.** Only included in `active_modules` when
  `--include-traversal` is set. **Not** activated by `--cakephp` profile.
- **Payloads (v1, exact list):**
  - `../../../etc/passwd`
  - `..%2f..%2f..%2fetc%2fpasswd`
  - `....//....//....//etc/passwd`
  - `..\\..\\..\\windows\\win.ini`
  - `/etc/passwd`
- **Surface:** every query param, every form field, AND every URL path
  segment of `target.url` (the path-segment surface is unique to this
  module — sqli/xss don't test path segments).
- **Detection signatures (in response body):**
  - `root:x:0:0:` → `CRITICAL` (Unix `/etc/passwd`).
  - `[fonts]` or `[extensions]` → `CRITICAL` (Windows `win.ini`).
- **`fit3048_category`:** `3`.
- **Operational risk note:** when this module is active, the HTML
  report's header bar gets an `OPERATIONAL_RISK` annotation
  (handled in `output/html.py`, not here).

## Framework Profiles

`webprobe/profiles.py`:

```python
CAKEPHP_PATHS = [
    "/webroot/debug_kit/",
    "/debug-kit/",
    "/logs/",
    "/tmp/",
    "/config/app.php",
    "/config/app_local.php",
]

# Slot for Sprint 2: --django, --laravel, --rails are config additions,
# not engine changes. Each profile = a CAKEPHP_PATHS-equivalent list +
# (optional) module subset filter + (optional) additional payloads.
```

PRD ref: `prd.md > Epic 5 > "framework profile to be a config addition"`.
v1 ships only `--cakephp`. The slot's contribution affordance is the v1
deliverable; the additional profiles ship in Sprint 2.

## Output Sinks

All three sinks consume the same `(findings, errored_modules, args,
target)` tuple. Formatting is a presentation concern, not coupled to
detection.

### output/colors.py — Single Source of Truth for the Palette

```python
# Terminal palette — used by terminal.py
SEVERITY_ANSI = {
    "CRITICAL": Fore.RED + Style.BRIGHT,
    "HIGH":     Fore.RED,
    "MEDIUM":   Fore.YELLOW,
    "LOW":      Fore.CYAN,
    "INFO":     Fore.WHITE + Style.DIM,
}
RESET = Style.RESET_ALL

# HTML palette — used by html.py. Tuned for white background per PRD.
SEVERITY_HEX = {
    "CRITICAL": "#C0392B",
    "HIGH":     "#E74C3C",
    "MEDIUM":   "#F39C12",
    "LOW":      "#3498DB",
    "INFO":     "#7F8C8D",
}
HTML_BG       = "#FFFFFF"
HTML_TEXT     = "#2C3E50"

def init():
    """Call colorama.init(autoreset=False) once at startup."""

def should_color(args) -> bool:
    """Resolve --no-color / --force-color / sys.stdout.isatty()."""
```

PRD ref: `prd.md > Epic 3 > color palette` — both the terminal and HTML
palettes are pinned with rationale (yellow unreadable on white,
terminal-cyan prints poorly).

### output/terminal.py — Terminal Rendering

PRD ref: `prd.md > Epic 3 > "inline severity-tagged teases"` and
`"=== FINDINGS === block"` and `"summary line"`.

Three render functions:

- `render_inline_tease(finding, args) -> None` — prints
  `[<SEVERITY>] <one-line summary>\n` to stdout. Called by the engine's
  `report_finding` callback.
- `render_findings_block(findings, errored_modules, args) -> str` — builds
  the full `══════════════════ FINDINGS ══════════════════` block.
  Findings are sorted by `SEVERITY_ORDER` index (CRITICAL → INFO), ties
  broken by category alphabetical for determinism. Each finding renders:
  ```
  [<SEVERITY>] <name>
    URL:        <url>
    POC:        <poc_url>          # omitted for passive findings
    Evidence:   <evidence>
    Fix:        <remediation>
    FIT3048:    Category <n>       # only when --fit3048 is set
  ```
  After the findings: a `MODULES WITH ERRORS` sub-block listing each
  errored module with exception type and a one-line tip.
- `render_summary(findings, errored_modules, args, duration) -> str` —
  builds the always-printed summary line:
  ```
  Target:    <url>
  Modules:   <scheduled> scheduled, <completed> completed, <errored> errored
  Findings:  <total> (<n> CRITICAL, <n> HIGH, <n> MEDIUM, <n> LOW, <n> INFO)
  Report:    <html-filename>
  Duration:  <s>s
  ```
  On clean scan: `Findings:  0 — no issues detected`.
  On any errored module OR degraded-target signal:
  add `⚠ Partial scan — results may be incomplete`.

**Marker convention (reserved, mutually exclusive with severity tags):**

| Marker | Meaning |
|---|---|
| `[*]` | Module/action progress |
| `[+]` | Benign success / status note inside a module's narration |
| `[-]` | Run-level failure |
| `[!]` | Warning or module error |
| `[.]` | Verbose-only payload/path attempt (only with `-v`) |
| `[CRITICAL]` / `[HIGH]` / `[MEDIUM]` / `[LOW]` / `[INFO]` | Findings only |

### output/html.py — Self-Contained HTML Report

PRD ref: `prd.md > Epic 3 > "self-contained HTML report"` and Epic 5's
restricted-environment constraint.

- **One file, no external assets.** Inline `<style>` only. Inline
  `<script>` only for the clipboard button.
- **Filename:** `webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.html`. Slashes
  in URL path stripped — only host+port preserved. Same-second collision
  → append `_2`, `_3`, etc. Built in `output/__init__.py` as a shared
  helper consumed by both html.py and txt.py to guarantee filename pair
  matches.
- **Timestamp timezone:** local time, with timezone abbreviation in the
  header-bar timestamp string (e.g. `2026-04-27 14:30:00 AEST`). Filename
  uses local time too. Rationale: matches user mental model ("when I ran
  this scan"). UTC adds cognitive friction for the FIT3047 reflective-diary
  use case.
- **Top of page:** header bar with target URL, timestamp, severity counts
  (`3 HIGH | 1 MEDIUM | 0 LOW`). When `--include-traversal` was set, a
  small `OPERATIONAL_RISK` chip with hover/title text:
  *"this scan included path-traversal payloads, which generate noisy
  logs on the target."*
- **Default body grouping:** severity sections worst → best, each with a
  colored header bar using `SEVERITY_HEX`.
- **`--fit3048` body grouping:** two-level. FIT3048 Category (1 → 10) →
  severity-within-category nested. Severity section headers still appear
  inside each category section.
- **Findings always expanded.** No collapse/expand toggle. Evidence + fix
  visible without clicking.
- **Per-finding render:** name, URL (clickable `<a>`), POC URL (clickable
  `<a>` + `<button class="copy-btn">Copy</button>` adjacent), evidence,
  fix, FIT3048 category number.
- **Partial-scan banner** at the top of the report when any module
  errored or the degradation warning fired. Mirrors the terminal
  summary's `⚠ Partial scan` line.
- **HTML escaping:** every dynamic string flows through `html.escape()`
  before insertion. URLs in `<a href="...">` use `html.escape(url, quote=True)`.

#### Clipboard Fallback (Inline JS)

Per research finding #2 (`navigator.clipboard.writeText` is Baseline as
of March 2025 but requires secure context — `file://` is **not** secure
in Firefox/Safari, inconsistent in Chrome). The HTML report's dominant
use case is "double-click report.html from disk."

**Strategy: Clipboard API primary, text-selection fallback. No
`document.execCommand` rung.**

```javascript
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const a = btn.previousElementSibling;
      const url = a.href;     // browser-parsed, immune to Python escaping bugs
      try {
        await navigator.clipboard.writeText(url);
        flash(btn, 'Copied');
      } catch {
        const range = document.createRange();
        range.selectNodeContents(a);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        flash(btn, 'Selected — Ctrl+C');
      }
    });
  });
});
function flash(btn, msg) {
  const orig = btn.textContent;
  btn.textContent = msg;
  setTimeout(() => { btn.textContent = orig; }, 1200);
}
```

- **URL flows from `a.href` (DOM property), not a `data-url` attribute or
  inline string.** XSS findings produce POC URLs containing `<`, `>`,
  `'`, `"` — reading from `a.href` sidesteps every Python-side
  escaping bug. The Python renderer only has to escape for
  `<a href="...">`; the JS layer never touches a raw payload.
- **Fallback selects the URL text in-place; user presses Ctrl+C.** Honest
  UX. No deprecated APIs.
- **Flash duration: 1200ms.** Long enough to register and screenshot;
  short enough to not feel viscous on rapid copies.
- **No CSP meta tag.** Single-file artifact opened from disk; CSP is
  inert on `file://`. Inline script visible to any "view source" reader.

References:
- [MDN Clipboard.writeText](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText)
- [MDN Selection API](https://developer.mozilla.org/en-US/docs/Web/API/Selection)
- [caniuse Clipboard API](https://caniuse.com/mdn-api_clipboard_writetext)

### output/txt.py — Plaintext Report

PRD ref: `prd.md > Epic 3 > "report.txt paste-ready"`.

```python
def render_txt(findings, errored_modules, args, target, duration) -> str:
    """
    Returns the ANSI-stripped form of the terminal FINDINGS block + summary.
    Always written alongside the HTML report (same base filename, .txt extension).
    """
    block = render_findings_block(findings, errored_modules,
                                   args_force_no_color(args))
    summary = render_summary(findings, errored_modules,
                              args_force_no_color(args), duration)
    return block + "\n\n" + summary
```

ANSI is stripped by passing a copy of `args` with `no_color=True` into
the same renderers terminal.py uses. One source of truth for layout —
TXT is just terminal output without color.

## Concurrency Model

PRD ref: `prd.md > Performance & Operational Requirements > Concurrency
model`.

### Thread-Local Session Factory

`webprobe/session.py`:

```python
import threading
import requests

_local = threading.local()

def make_session_factory(args) -> Callable[[], requests.Session]:
    def factory() -> requests.Session:
        s = getattr(_local, "session", None)
        if s is None:
            s = requests.Session()
            # Future: --cookie sets s.cookies here
            _local.session = s
        return s
    return factory
```

Each thread gets its own `requests.Session`. Connection pooling stays
per-thread — fine for the paths module's 20-worker pool over a curated
~150-path list (each worker handles ~7-8 requests, pool stays warm).
Avoids the documented thread-safety footgun where a shared Session
across a ThreadPoolExecutor can throw socket errors under load.

### Stdout Lock

A single `threading.Lock()` in the engine wraps every print path that
modules can trigger:

- `report_finding(f)` — locked.
- `[!] {module.name}: errored ...` — locked.
- Verbose `[.]` lines emitted from threaded modules — locked.

Sequential modules incur essentially zero contention; threaded modules
serialize on the critical section (a single `print()` call). Negligible
overhead.

### Per-Module Concurrency

| Module | Concurrency | Rationale |
|---|---|---|
| headers | sequential | 0 HTTP requests (parses base_response) |
| info-disclosure | sequential | 0 HTTP requests (parses base_response) |
| paths | `ThreadPoolExecutor(max_workers=20)` | ~150 requests; serial = unacceptable |
| sqli | sequential per param | Differential detection needs ordered pairs |
| xss | sequential per param | Payload ordering matters for evidence quality |
| traversal | sequential per param | Same as sqli/xss; payload count small |

## Error Handling

### Connectivity Failure (HTTP-Layer)

```python
try:
    base_response = session.get(url, timeout=5, allow_redirects=True)
except (requests.ConnectionError, requests.Timeout,
        requests.RequestException) as e:
    print("[-] Target unreachable. Check URL and try again.")
    sys.exit(1)
```

Exits immediately with non-zero status. No modules run. No reports
written.

### Form Discovery Failure (Application-Layer)

```python
try:
    forms = parse_forms(base_response)
except Exception as e:
    print(f"[!] form discovery failed ({type(e).__name__}) — "
          f"proceeding with no forms")
    forms = []
```

Scan continues. Modules that need forms (sqli, xss) return zero findings
against an empty form list. This is correct — there's nothing to test.

### Module Crash (Per-Module try/except)

PRD ref: `prd.md > Epic 4 > "module crashes isolated and surfaced"`.

Engine wraps every `module.run(...)` call in a try/except. On exception:

- Inline `[!] {name}: errored ({ExceptionType}) — skipped` printed
  immediately.
- `(name, exception)` appended to `errored_modules` for the
  `MODULES WITH ERRORS` sub-block in the FINDINGS render.
- The errored module count surfaces in the summary's `Modules:` line.
- Partial-scan flag fires.

Exception categorization (which exceptions get a more helpful one-line
tip in `MODULES WITH ERRORS`) is a /build concern. Default tip:
`Tip: re-run with -v for more detail.` Specific categorizations
(e.g. binary content → `Tip: target may have returned binary content`)
are nice-to-have, not blocking.

### Degradation (3 Consecutive HTTP Failures)

PRD ref: `prd.md > Epic 4 > "scanning a flaky target"`.

A module-level helper tracks consecutive failures (timeout, 5xx,
connection reset). After 3 in a row within a single module, print:

```
[!] Target appears degraded — 3 consecutive failures.
    Completing remaining modules with reduced confidence.
```

Remaining modules still run. Partial-scan flag fires.

### Hard Scan Ceiling (90s)

PRD ref: `prd.md > Performance & Operational Requirements > Hard scan
ceiling: 90 seconds`.

Engine starts a wall clock at the top of the run. Before each module
dispatch, check elapsed time. If ≥ 90s:

- Print `[!] Scan ceiling reached (90s) — emitting findings collected
  so far.`
- Skip remaining modules (counted as errored for accounting purposes).
- Render output sinks with whatever findings exist.
- Partial-scan flag fires.

Timeout is checked between modules, not mid-module — a module already
running gets to complete. Cooperative, not preemptive.

### Partial-Scan Trust Signal

PRD ref: `prd.md > Epic 4 > "never to mistake a partial scan for a clean
target"`.

`partial = bool(errored_modules) or degraded_flag or ceiling_hit`

Whenever `partial` is True:

- Terminal summary prints `⚠ Partial scan — results may be incomplete`.
- HTML report top banner mirrors the same warning, in the
  partial-scan banner described in [output/html.py](#outputhtmlpy--self-contained-html-report).
- TXT report includes the warning verbatim from the terminal summary.

Silent partial failure is unacceptable. This is the central trust
property of the run.

## File Structure

```
webprobe-project/
├── webprobe/
│   ├── __init__.py                  # __version__ = "1.0.0"
│   ├── probe.py                     # CLI entrypoint (~30 lines)
│   ├── engine.py                    # orchestration: banner, connectivity,
│   │                                #   discover, dispatch, lock
│   ├── target.py                    # discover_target(url, response, profile) → Target
│   ├── findings.py                  # Finding, Form, Target dataclasses
│   │                                #   + SEVERITY_ORDER + __post_init__ asserts
│   ├── session.py                   # threading.local() session factory
│   ├── profiles.py                  # CAKEPHP_PATHS + (Sprint 2 slot)
│   ├── modules/
│   │   ├── __init__.py              # MODULES manifest (ordered)
│   │   ├── base.py                  # BaseModule ABC
│   │   ├── sqli.py                  # ≤50 lines — boolean-diff + error-string
│   │   ├── xss.py                   # ≤50 lines — reflection probe
│   │   ├── paths.py                 # ≤50 lines — ThreadPoolExecutor(20)
│   │   ├── headers.py               # ≤50 lines — header + cookie parse
│   │   ├── info_disclosure.py       # ≤50 lines — passive parse, no HTTP
│   │   └── traversal.py             # ≤50 lines — opt-in payloads
│   ├── output/
│   │   ├── __init__.py              # filename_for_target() helper
│   │   ├── colors.py                # SEVERITY_ANSI, SEVERITY_HEX, init()
│   │   ├── terminal.py              # tease + FINDINGS block + summary
│   │   ├── html.py                  # one template; inline <style> + <script>
│   │   └── txt.py                   # ansi_strip(terminal_output)
│   └── data/
│       └── paths/
│           └── curated.txt          # ~150 sensitive paths, newline-delimited
├── docs/
│   ├── learner-profile.md
│   ├── scope.md
│   ├── prd.md
│   ├── spec.md                      # ← this file
│   └── (later: checklist.md)
├── process-notes.md                 # learning journal
├── requirements.txt                 # 3 lines: requests, beautifulsoup4, colorama
├── README.md                        # install + run + FIT3048 advertisement
└── .gitignore                       # __pycache__, *.pyc, webprobe_*.html, webprobe_*.txt
```

**Why `data/paths/<asset>.txt`, not `data/<asset>.txt`:** future-proofs
Sprint 2 detection-data assets (e.g. `data/xss/payloads_extended.txt` for
`--thorough`, `data/traversal/signatures.txt` for additional OS targets).
Adding a sibling directory is a smaller structural change than reshelving
existing files.

**Why `data/` lives inside `webprobe/`, not at project root:** runtime
asset of the package, loaded via `importlib.resources.files("webprobe") /
"data" / "paths" / "curated.txt"`. Keeping it inside the package
guarantees the resource API works whether WebProbe is installed via
`pip install -e .` or run from a clone. Project root stays reserved for
repo-meta artifacts (README, requirements.txt, docs/, .gitignore).

## Key Technical Decisions

1. **Severity and `fit3048_category` live on `Finding`, not `BaseModule`.**
   The `paths` module produces multi-severity output from one algorithm;
   the `headers` module produces multi-category output from one parse.
   Per-finding fields are mandatory.

2. **`session_factory` callable, not `session` instance.** Modules call
   the factory to get a thread-local Session. Sequential modules call
   once; threaded modules call inside each worker. Threading concerns
   stay inside the factory, never leak into module bodies.

3. **`run()` is 3-arg with a `report_finding` callback.** PRD requires
   inline tease at the moment of detection, which incompatible with
   "return list at end." Callback over generator: module body reads as
   straight-line imperative code. Engine wraps callback in stdout lock
   so threaded modules stay thread-naive.

4. **Engine pre-resolves flags into per-module `__init__` config.**
   `--cakephp` becomes a merged `path_list` injected into `PathsModule`;
   `--include-traversal` controls whether `TraversalModule` is in
   `active_modules` at all. Module bodies never see flag state. Sprint 2
   flags follow the same pattern with no engine plumbing change.

5. **One GET, three consumers.** Connectivity check, form discovery, and
   `headers` / `info-disclosure` modules all consume the same response.
   Connectivity = HTTP-layer concern (failure → exit 1); form discovery
   = application-layer concern (failure → continue with `forms=[]`).

6. **Clipboard API primary, text-selection fallback. No `execCommand`.**
   `execCommand` is deprecated; v1 reports archived today should still
   work in 2027 browsers. URL flows from the DOM `a.href` property, not
   from a Python-escaped string — XSS findings can produce arbitrarily
   adversarial POC URLs and the JS layer must be immune.

7. **`webprobe/data/paths/curated.txt` external, not inline.** Inline ~150
   paths blows the 50-line module budget. Data-as-code separation also
   makes "add a path" a non-touching-detection-logic PR.

## Dependencies & External Services

External code:
- [`requests`](https://requests.readthedocs.io/en/latest/) — HTTP client.
- [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
  — HTML form parsing.
- [`colorama`](https://pypi.org/project/colorama/) — Windows ANSI.

External services: **none.** WebProbe makes outbound HTTP requests to
the user-supplied target only. No telemetry, no update checks, no
external API calls.

Browser APIs (used in the HTML report):
- [Clipboard API](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText)
- [Selection API](https://developer.mozilla.org/en-US/docs/Web/API/Selection)
- [Range API](https://developer.mozilla.org/en-US/docs/Web/API/Range)

## Open Issues — Spec → /build Handoff

These are deliberately *not* solved in /spec. They're implementation
details below the spec/build line — pinning them here would either
ossify wrong defaults or pad the spec with false precision. Each lands
in the /checklist as a build-time decision.

- **SQLi boolean-differential threshold.** Spec says "configurable
  threshold." /build pins a default (likely a response-length delta
  percentage or status-code change) and verifies it manually against
  the FIT3047 login form.
- **Module-error one-line tips** (the friendly hint after the
  `MODULES WITH ERRORS` exception type). Default `Tip: re-run with -v
  for more detail.` is sufficient for v1; targeted tips per exception
  type are nice-to-have.
- **Banner exact text.** Format pinned (target URL, active modules,
  profile, traversal-opt-in advertisement, separator); literal strings
  are /build.
- **`--help` description and epilog.** Format pinned (FIT3048 use case,
  open-source pointer, "use Burp for X" line); exact wording is /build.
- **Verbose `[.]` line format.** Pinned as "every path attempted, every
  payload tried." Exact format strings are /build.

## Open Questions Inherited From PRD (now resolved)

PRD ref: `prd.md > Open Questions`. All resolved by this spec:

- **`BaseModule` exact signature** — resolved. Type-hinted, severity is
  per-Finding, `fit3048_category` is per-Finding, `run()` is 3-arg with
  callback.
- **Concurrency confirmation** — resolved. `ThreadPoolExecutor(20)` for
  paths only; thread-local Sessions via `threading.local()` factory;
  stdout lock owned by engine.
- **HTML inline JS for copy-to-clipboard** — resolved. Clipboard API
  primary, text-selection fallback. `execCommand` rejected.
- **`--help` text shape** — captured at the format level
  ([Argument Parsing](#argument-parsing)); literal text is /build.
- **HTML report timestamp timezone** — resolved. Local time with
  timezone abbreviation in the header; local time in the filename.
