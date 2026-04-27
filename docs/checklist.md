<!-- Every item uses the five-field format: Title / Spec ref / What to build /
     Acceptance / Verify. Three checkpoint annotations break the build into
     verification beats — the agent stops, prints state, and waits for "go". -->

# WebProbe — Build Checklist

## Build Preferences

- **Build mode:** Autonomous with three named checkpoints.
- **Comprehension checks:** N/A (autonomous mode).
- **Git:** One commit per numbered item, conventional-commits style
  (`feat: <item-N> <title>` for module/feature items, `chore: <item-N>` for
  scaffolding, `docs: <item-N>` for README/checklist updates). Commit
  immediately after item acceptance passes — clean revert points if a
  checkpoint fails.
- **Verification:** Yes. Three explicit checkpoints (A after item 7, B
  after item 12, C after item 15). At each checkpoint the agent stops,
  prints what was built, optionally runs `wc -l`, and waits for explicit
  "go" before continuing.
- **Check-in cadence:** N/A (autonomous mode).

## Notes for the build agent

- **Detection modules sqli, xss, traversal cannot be semantically
  validated without a target containing those vulnerabilities.** Items 9,
  10, 11 verify only structure (50-line constraint, import, registration,
  banner inclusion). Semantic validation happens at item 17 (FIT3047 e2e
  run). If item 17 surfaces a defect, return to the affected module's
  item and patch — the checklist is a contract, not sacred.
- **Error-handling concerns are distributed.** Per-module try/except + 90s
  ceiling + partial-scan flag live in item 7 (engine). 3-consecutive-
  failure degradation lives inside each HTTP-issuing module (items 9, 10,
  11, 12). Partial-scan banner mirroring lives in item 13 (HTML output).
- **The 50-line constraint is verified per-item.** Each module item's
  Verify step runs `wc -l`. Item 12's checkpoint runs the full audit
  across all module files; if any > 50, extract `_<name>_helpers.py` per
  spec carryover before continuing.
- **HTML clipboard fragility.** In item 13, render `<a>` and `<button
  class="copy-btn">` as direct DOM siblings (no wrappers). Add an inline
  HTML comment: `<!-- DO NOT WRAP — clipboard JS depends on
  previousElementSibling -->`. Manually click Copy on a `file://` rendered
  report before marking the item complete.

## Checklist

- [x] **1. Repo skeleton + git init**
  Spec ref: `spec.md > File Structure` and `spec.md > Stack`
  What to build: Create the directory tree exactly per `spec.md > File
  Structure` (`webprobe/`, `webprobe/modules/`, `webprobe/output/`,
  `webprobe/data/paths/`). Empty `__init__.py` in every package directory.
  `webprobe/__init__.py` sets `__version__ = "1.0.0"`. Write
  `requirements.txt` with three lines (`requests>=2.31`,
  `beautifulsoup4>=4.12`, `colorama>=0.4.6`). Write `.gitignore`
  (`__pycache__`, `*.pyc`, `webprobe_*.html`, `webprobe_*.txt`). Write a
  one-line `README.md` stub (filled out in item 16). `git init` and make
  an initial commit.
  Acceptance: `pip install -r requirements.txt` succeeds in a fresh venv.
  `python3 -c "import webprobe; print(webprobe.__version__)"` prints
  `1.0.0`. Per `prd.md > Epic 5 > "install one command"`.
  Verify: Run the import command above. Confirm "1.0.0" prints. Run
  `git log --oneline` and confirm one commit exists.

- [x] **2. Data model — Finding, Form, Target**
  Spec ref: `spec.md > Data Model`
  What to build: `webprobe/findings.py`. Define `SEVERITY_ORDER =
  ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]`. `@dataclass class
  Finding` with all 10 fields per `prd.md > Data Model` (severity,
  category, name, url, parameter, payload, evidence, poc_url,
  remediation, fit3048_category) and a `__post_init__` that asserts
  `severity in SEVERITY_ORDER` and `1 <= fit3048_category <= 10`.
  `@dataclass class Form(action, method, fields)`. `@dataclass class
  Target(url, base_response, forms, query_params, profile)`.
  Acceptance: Per `prd.md > Data Model — Finding Object`. `__post_init__`
  asserts catch invalid severity and out-of-range fit3048_category at
  construction (typos blow up immediately, not at render time).
  Verify: Open a Python REPL. `from webprobe.findings import Finding,
  Form, Target, SEVERITY_ORDER`. Construct a valid Finding — succeeds.
  Construct one with `severity="WRONG"` — AssertionError. Construct one
  with `fit3048_category=11` — AssertionError.

- [x] **3. BaseModule ABC + module manifest**
  Spec ref: `spec.md > BaseModule Contract` and `spec.md > Module
  Registration`
  What to build: `webprobe/modules/base.py` with `class BaseModule(ABC)`:
  class attributes `name: str` and `category: str`; `@abstractmethod def
  run(self, target, session_factory, report_finding) -> list[Finding]`
  with the docstring from spec (callback drives real-time output, return
  list drives per-module accounting, both populated by design).
  `webprobe/modules/__init__.py` exports `MODULES: list[type[BaseModule]]
  = []` (empty manifest; populated as modules are registered).
  Acceptance: Instantiating `BaseModule()` raises `TypeError`. Subclasses
  must implement `run()`. `MODULES` is importable and iterable.
  Verify: `python3 -c "from webprobe.modules import MODULES; print(MODULES)"`
  prints `[]`. `python3 -c "from webprobe.modules.base import BaseModule;
  BaseModule()"` raises `TypeError: Can't instantiate abstract class`.

- [x] **4. Thread-local session factory**
  Spec ref: `spec.md > Concurrency Model > Thread-Local Session Factory`
  What to build: `webprobe/session.py`. `make_session_factory(args) ->
  Callable[[], requests.Session]` returns a closure. Inside the closure:
  use `threading.local()` to store one `requests.Session` per thread,
  lazy-initialized on first call. Future-extension hook: a comment
  marking where Sprint 2's `--cookie` flag will set `s.cookies` after
  `requests.Session()` is instantiated.
  Acceptance: Per spec — same thread → same Session instance; different
  thread → different Session instance. Avoids the documented
  thread-safety footgun of sharing `requests.Session` across a
  ThreadPoolExecutor.
  Verify: REPL: build a factory, call it twice on the main thread →
  same object. Spawn a `threading.Thread` that calls the factory and
  appends to a list → list[0] is a different Session object.

- [x] **5. Output palette + terminal renderers**
  Spec ref: `spec.md > Output Sinks > output/colors.py` and `spec.md >
  Output Sinks > output/terminal.py`
  What to build:
  - `webprobe/output/colors.py` — `SEVERITY_ANSI` dict (colorama
    `Fore`/`Style`); `SEVERITY_HEX` dict (white-bg palette per spec);
    `HTML_BG = "#FFFFFF"`; `HTML_TEXT = "#2C3E50"`; `RESET =
    Style.RESET_ALL`; `init()` calls `colorama.init(autoreset=False)`;
    `should_color(args) -> bool` resolves `--no-color`/`--force-color`/
    `sys.stdout.isatty()`.
  - `webprobe/output/terminal.py` — three render functions per spec:
    - `render_inline_tease(finding, args) -> None`: prints
      `[<SEVERITY>] <one-line summary>` to stdout with appropriate ANSI.
    - `render_findings_block(findings, errored_modules, args) -> str`:
      builds the `══════════════════ FINDINGS ══════════════════` block.
      Sort: SEVERITY_ORDER index ascending (CRITICAL → INFO), tie-break
      category alphabetical. Per-finding rows: severity-tagged title +
      indented `URL:` `POC:` (omit for passive) `Evidence:` `Fix:`
      `FIT3048:` (only with `--fit3048`). After findings, a `MODULES
      WITH ERRORS` sub-block listing each errored module with exception
      type and a default tip.
    - `render_summary(findings, errored_modules, args, duration) -> str`:
      always-printed summary with `Target:`, `Modules:`, `Findings:`,
      `Report:`, `Duration:`. Clean scan: `Findings: 0 — no issues
      detected`. Partial scan: append `⚠ Partial scan — results may be
      incomplete`.
  Acceptance: Per `prd.md > Epic 3 > color palette` (terminal half), per
  `prd.md > Epic 3 > "=== FINDINGS === block"` and `"summary line"`.
  Marker convention reserved per `spec.md > output/terminal.py` table
  ([*]/[+]/[-]/[!]/[.]/[SEVERITY]).
  Verify: REPL: construct one Finding (HIGH/xss). Call each of the three
  render functions and inspect output. Tease line is one line and
  colored. Findings block sorts correctly. Summary's clean-scan path
  prints when findings list is empty.

- [x] **6. Headers module — first detection module, registered**
  Spec ref: `spec.md > Detection Modules > headers`
  What to build: `webprobe/modules/headers.py`. `HeadersModule(BaseModule)`
  with `name = "headers"`, `category = "headers"`. `run()` reads
  `target.base_response.headers` and `target.base_response.cookies` —
  zero new HTTP requests. Header missing-checks per spec severities: CSP
  → MEDIUM (cat 5), X-Frame-Options → MEDIUM (cat 5), HSTS only on
  https:// → HIGH (cat 5), X-Content-Type-Options → LOW (cat 5),
  Referrer-Policy → LOW (cat 5). Cookie checks per `Set-Cookie`: missing
  HttpOnly → MEDIUM (cat 4, `category="cookies"`), missing Secure on
  https:// → HIGH (cat 4, `category="cookies"`), missing SameSite → LOW
  (cat 4, `category="cookies"`). Each finding is reported via
  `report_finding(f)` AND included in the returned list. Register
  `HeadersModule` in `MODULES` manifest (first per spec ordering — fast,
  single-response parse).
  Acceptance: Per `prd.md > Epic 2 > "missing security headers and unsafe
  cookie flags"`. All severity assignments match spec exactly. `wc -l
  webprobe/modules/headers.py` ≤ 50 (the project's central legibility
  commitment).
  Verify: `wc -l webprobe/modules/headers.py` ≤ 50. Defer end-to-end
  test until item 7.

- [x] **7. Engine + CLI entrypoint (vertical slice)**
  Spec ref: `spec.md > Engine` (probe.py + engine.py + argument parsing
  + banner + connectivity check + target discovery + module dispatch)
  and `spec.md > Error Handling`
  What to build:
  - `webprobe/engine.py` — `run(args)` orchestrator. Build banner per
    spec: tool name + version + target URL + active module slugs +
    profile (or `none`) + traversal opt-in advertisement when
    `--include-traversal` is not set + separator. Banner < 6 lines.
    `check_connectivity` (single GET, `timeout=5`, `allow_redirects=True`):
    success → `[+] Target responding (HTTP <code>, <duration>s)`;
    failure (`ConnectionError` / `Timeout` / `RequestException`) → `[-]
    Target unreachable. Check URL and try again.` + `sys.exit(1)`.
    `discover_target(url, response, profile) -> Target` — parse forms via
    `BeautifulSoup(html.parser)`, extract query params via
    `urllib.parse.urlparse + parse_qs`. On parse exception: `[!] form
    discovery failed (<Exception>) — proceeding with no forms` and
    return `Target(forms=[], ...)`. `build_active_modules(args) ->
    list[BaseModule]`: parse `--only`, exclude `traversal` unless
    `--include-traversal`, instantiate each `MODULES` class (paths gets
    `path_list=load_default_paths()` — `--cakephp` merge deferred to
    item 15). Module dispatch loop: print `[*] Running: {module.name}...`,
    wrap each `module.run(...)` in `try/except`, on exception emit `[!]
    {module.name}: errored ({type}) — skipped` and append to
    `errored_modules`. Between modules: check elapsed time; if ≥ 90s
    print ceiling-reached line and break. `stdout_lock = threading.Lock()`;
    `report_finding(f)` is locked and calls `render_inline_tease`.
    `partial = bool(errored_modules) or degraded_flag or ceiling_hit`.
    After loop: print `render_findings_block` + `render_summary`. Write
    HTML / TXT reports — STUB at this item (real renders land in items
    13/14); summary's `Report:` field can show a placeholder filename
    until then.
  - `webprobe/probe.py` (~30 lines) — argparse: `target_url` positional;
    flags `--only`, `--output`, `--cakephp`, `--fit3048`,
    `--include-traversal`, `--no-color`, `--force-color`, `-v`.
    Description + epilog per `prd.md > CLI Surface (v1)` advertising the
    FIT3047/FIT3048 use case and ending with the "use Burp Suite for X"
    line. Validate `--only` against `{sqli, xss, paths, headers,
    info-disclosure, traversal}`; invalid → fail fast with valid list,
    `sys.exit(2)`. Catch `KeyboardInterrupt` → clean `[-]` line.
    `engine.run(args)`.
  Acceptance: Per `prd.md > Epic 1` (banner + connectivity + scan run).
  Per `prd.md > Epic 4 > "module crashes isolated"` (try/except + `[!]`
  line + `MODULES WITH ERRORS` + partial-scan flag). Per `prd.md >
  Performance > Hard scan ceiling`. `--only invalid_name` → exit 2.
  Banner < 6 lines.
  Verify: `python3 webprobe/probe.py http://example.com`. Confirm:
  banner prints with `[headers]` in active modules and `(traversal: opt-in
  via --include-traversal)`; `[*] Checking target reachability...` then
  `[+] Target responding (HTTP 200, <s>s)`; headers module emits ≥1
  inline tease line (example.com is missing several security headers);
  FINDINGS block + summary print. Failure mode: `python3
  webprobe/probe.py http://nonexistent.invalid` → `[-] Target
  unreachable...` and exit 1. Invalid only: `python3 webprobe/probe.py
  http://example.com --only nonsense` → fail fast with valid list and
  exit 2.

  → **CHECKPOINT A** — Stop after item 7. Print summary of what was
  built (file list, entrypoint command, current line counts on
  `webprobe/modules/headers.py`). Wait for explicit "go" before item 8.
  Verification I will perform: run `python3 webprobe/probe.py
  http://example.com`, confirm banner / connectivity / inline tease /
  FINDINGS block / summary all render correctly with right colors and
  marker conventions. Any visible bug here pauses Slice 2.

- [x] **8. info-disclosure module**
  Spec ref: `spec.md > Detection Modules > info-disclosure`
  What to build: `webprobe/modules/info_disclosure.py`.
  `InfoDisclosureModule(BaseModule)` with `name = "info-disclosure"`,
  `category = "info-disclosure"`. `run()` reads
  `target.base_response.headers` and `target.base_response.text` — zero
  new HTTP requests. Checks: `Server` header → LOW (cat 3);
  `X-Powered-By` → LOW (cat 3); HTML comments containing `TODO`/`FIXME`/
  URL-like substrings (`http://`, `https://`, `localhost`, internal IPs)
  → MEDIUM (cat 3); stack-trace fingerprints in body (`Traceback (most
  recent call last)`, `at java.lang.`, `Stack trace:`, `Warning: ` (PHP),
  `Notice: ` (PHP)) → MEDIUM (cat 3). Register in `MODULES` after
  `HeadersModule` per spec ordering.
  Acceptance: Per `prd.md > Epic 2 > "passive info-disclosure findings"`.
  Zero false-positive risk by design. `wc -l` ≤ 50.
  Verify: `wc -l webprobe/modules/info_disclosure.py` ≤ 50. Run
  `python3 webprobe/probe.py http://example.com` — banner shows
  `[headers, info-disclosure]`; info-disclosure findings render inline
  with `[LOW]` / `[MEDIUM]` markers.

- [x] **9. sqli module**
  Spec ref: `spec.md > Detection Modules > sqli`
  What to build: `webprobe/modules/sqli.py`. `SqliModule(BaseModule)` with
  `name = "sqli"`, `category = "sqli"`. The 7 v1 payloads exactly: `'`,
  `"`, `1'`, `1' OR '1'='1`, `1' AND '1'='2`, `1 AND 1=1`, `1 AND 1=2`.
  For each query param + each form field: send each payload via
  `session_factory()`-acquired Session (one Session — sequential module).
  Boolean-differential: compare the `OR '1'='1` vs `AND '1'='2` pair (and
  the `1=1` vs `1=2` pair) on the same parameter. Default differential
  threshold: response-length delta ≥ 30% OR status-code change → HIGH
  finding. Error-based: response body contains any of `SQLSTATE`,
  `mysql_fetch_array`, `MariaDB`, `ORA-`, `SQLite3::`, `PostgreSQL`,
  `unclosed quotation mark` → HIGH finding. Evidence string includes the
  differentiator inline (e.g., `'OR '1'='1' returned 47KB; 'AND '1'='2'
  returned 0KB`). 3-consecutive-failure tracker per spec error-handling.
  fit3048_category=5. Register in `MODULES` after passive modules.
  Acceptance: Per `prd.md > Epic 2 > "SQL injection"`. Differential
  threshold pinned (30% length delta or status change) and named in code
  via a constant so it's auditable. `wc -l` ≤ 50.
  Verify: `wc -l webprobe/modules/sqli.py` ≤ 50. `python3
  webprobe/probe.py http://example.com` — banner shows `[headers,
  info-disclosure, sqli]`; sqli runs (no findings on example.com because
  no forms/params; expected). Semantic validation deferred to item 17.

- [x] **10. xss module**
  Spec ref: `spec.md > Detection Modules > xss`
  What to build: `webprobe/modules/xss.py`. `XssModule(BaseModule)` with
  `name = "xss"`, `category = "xss"`. The 6 v1 payloads exactly per spec.
  For each query param + each form field: inject payload, fetch response.
  Detection: `payload in response.text` AND the HTML-escaped form
  (`html.escape(payload)`) does NOT match (i.e., payload appears
  unescaped). On match → HIGH finding. POC URL: `target.url` with the
  matching payload URL-encoded into the parameter, DalFox-style
  click-ready. 3-consecutive-failure tracker. fit3048_category=5.
  Register in `MODULES` after sqli.
  Acceptance: Per `prd.md > Epic 2 > "reflected XSS detection"`. POC URL
  is a click-ready URL. Escaped variants do not produce false positives.
  `wc -l` ≤ 50.
  Verify: `wc -l webprobe/modules/xss.py` ≤ 50. `python3
  webprobe/probe.py http://example.com` — banner shows `[headers,
  info-disclosure, sqli, xss]`. Semantic validation deferred to item 17.

- [x] **11. traversal module + --include-traversal gating**
  Spec ref: `spec.md > Detection Modules > traversal`
  What to build: `webprobe/modules/traversal.py`.
  `TraversalModule(BaseModule)` with `name = "traversal"`, `category =
  "traversal"`. The 5 v1 payloads exactly per spec. Surface: query
  params + form fields + URL path segments (path-segment surface unique
  to this module). On `root:x:0:0:` in body → CRITICAL (Unix
  /etc/passwd). On `[fonts]` or `[extensions]` → CRITICAL (Windows
  win.ini). 3-consecutive-failure tracker. fit3048_category=3. Register
  in `MODULES` last per spec ordering. Engine
  `build_active_modules`: exclude `TraversalModule` if not
  `args.include_traversal`. Banner advertises `(traversal: opt-in via
  --include-traversal)` only when the flag is not set.
  Acceptance: Per `prd.md > Epic 2 > "directory-traversal detection —
  opt-in"`. Module excluded by default. `--cakephp` does NOT activate it.
  `wc -l` ≤ 50.
  Verify: `wc -l webprobe/modules/traversal.py` ≤ 50. Run `python3
  webprobe/probe.py http://example.com` — banner does NOT list
  `traversal` and DOES advertise opt-in. Run `python3 webprobe/probe.py
  http://example.com --include-traversal` — banner DOES list traversal;
  module runs (no findings expected on example.com). Run with
  `--cakephp` only — traversal still NOT in active modules.

- [x] **12. paths module + curated path list**
  Spec ref: `spec.md > Detection Modules > paths`, `spec.md > File
  Structure` (data layout), `spec.md > Concurrency Model > Per-Module
  Concurrency`
  What to build:
  - `webprobe/data/paths/curated.txt` — newline-delimited list of ~150
    sensitive paths. Must include (per prd): `/.env`, `/.git/HEAD`,
    `/.git/config`, `/phpinfo.php`, `/info.php`, `/server-status`,
    `/backup.sql`, `/db.sql`, `*.bak` and `*.old` variants (a curated
    set, not exhaustive). Pad to ~150 with common exposed-config/admin
    paths.
  - `webprobe/modules/paths.py`. `PathsModule(BaseModule)` with `name =
    "paths"`, `category = "paths"`. `__init__(self, path_list:
    list[str])` accepts pre-resolved list (engine injects). `run()` uses
    `ThreadPoolExecutor(max_workers=20)`. Each worker calls
    `session_factory()` for thread-local Session. GET each path against
    `urljoin(target.url, "/")` (host root, ignoring path component).
    Status `200`/`301`/`302`/`403` → flagged. `404` → not flagged. Other
    5xx → contributes to 3-consecutive-failure degradation tracker.
    Severity: HIGH for `.env`/`.git/*`/`config/app_local.php`/`backup.sql`/
    `db.sql`; MEDIUM for `phpinfo.php`/`info.php`/`debug-kit`; LOW for
    `*.bak`/`*.old`; default MEDIUM for other 200/403 hits.
    fit3048_category=3. Load default path list via
    `importlib.resources.files("webprobe") / "data" / "paths" /
    "curated.txt"`. Module-internal helper `load_default_paths()` exposed
    for engine use.
  - Engine update: `build_active_modules` instantiates `PathsModule` with
    `load_default_paths()` (CAKEPHP_PATHS merge deferred to item 15).
    Register PathsModule in `MODULES` per spec ordering (after passive,
    before sqli/xss/traversal).
  Acceptance: Per `prd.md > Epic 2 > "exposed sensitive paths"`. paths
  uses `ThreadPoolExecutor(20)`. Per-thread Session (no shared-Session
  footgun). `wc -l webprobe/modules/paths.py` ≤ 50.
  Verify: `wc -l webprobe/modules/paths.py` ≤ 50. Run `python3
  webprobe/probe.py http://example.com` — paths module runs, completes
  in <5s (parallel), zero findings expected on example.com. Test against
  a target that exposes `/server-status` if available.

  → **CHECKPOINT B** — Stop after item 12. Run `wc -l
  webprobe/modules/*.py` and print line counts. If ANY module file > 50
  lines, extract a `_<module>_helpers.py` sibling per spec carryover
  ("50-line constraint is a verification step, not aspiration") and
  re-run the audit before proceeding. Wait for explicit "go" before
  item 13.

- [ ] **13. HTML output sink — filename helper + report rendering**
  Spec ref: `spec.md > Output Sinks > output/__init__.py`, `spec.md >
  Output Sinks > output/html.py`, `spec.md > Clipboard Fallback`
  What to build:
  - `webprobe/output/__init__.py` — `filename_for_target(target_url,
    timestamp, output_dir, ext) -> Path`. Strip slashes from URL path —
    preserve only host+port. Format: `webprobe_<host>_<port>_<YYYYMMDD>_
    <HHMMSS>.<ext>`. Local time. Same-second collision → append `_2`,
    `_3`, etc. Shared by both html.py and txt.py to guarantee the
    `.html`/`.txt` pair shares a base name even at second boundaries.
  - `webprobe/output/html.py` — `render_html(findings, errored_modules,
    args, target, duration) -> str`. Single file. Inline `<style>` only.
    Inline `<script>` ONLY for the clipboard fallback (no other JS).
    Header bar: target URL + timestamp with timezone abbreviation (e.g.,
    `2026-04-27 14:30:00 AEST`) + severity counts (`3 HIGH | 1 MEDIUM |
    0 LOW`). When `args.include_traversal`: small `OPERATIONAL_RISK` chip
    with hover/title text per spec. Default body: severity sections
    worst → best, colored bars from `SEVERITY_HEX`. With `args.fit3048`:
    two-level nested grouping — FIT3048 Category 1→10 → severity within
    each category. All findings always expanded (no collapse toggle).
    Per finding: name, URL (`<a>` clickable), POC URL (`<a>` + adjacent
    `<button class="copy-btn">Copy</button>` — **DIRECT DOM SIBLINGS, NO
    WRAPPERS**, with the inline HTML comment `<!-- DO NOT WRAP —
    clipboard JS depends on previousElementSibling -->`), evidence, fix,
    FIT3048 category number. All dynamic strings flow through
    `html.escape()`. URLs in `href` use `html.escape(url, quote=True)`.
    Inline JS per spec: Clipboard API primary; on failure, Selection +
    Range fallback (selects the `<a>` text in-place; flash "Selected —
    Ctrl+C"). Flash duration **1200ms**. White-bg palette per spec.
    Partial-scan banner at top when `partial=True`.
  - Engine update: write the HTML file via `filename_for_target(...,
    ext="html")` after the FINDINGS block prints. Update summary's
    `Report:` field to the actual filename.
  Acceptance: Per `prd.md > Epic 3 > "self-contained HTML report"`.
  Single file, no external assets. Per `--fit3048` two-level grouping.
  Per OPERATIONAL_RISK note. Renders correctly from `file://` in
  Firefox/Safari/Chrome.
  Verify: Run `python3 webprobe/probe.py http://example.com`. Open the
  generated `webprobe_*.html` in a browser. Confirm: header bar with
  target/timestamp/severity counts; severity sections render with correct
  hex on white; click the Copy button next to a POC URL — paste into a
  text editor and confirm URL is in clipboard. Re-run with `--fit3048`
  → confirm nested category → severity layout. Re-run with
  `--include-traversal` → confirm OPERATIONAL_RISK chip in header. Open
  the same file in Firefox via `file://` — if Clipboard API fails on
  insecure context, confirm the text-selection fallback fires (URL text
  highlights in-place, button reads "Selected — Ctrl+C").

- [x] **14. TXT output sink**
  Spec ref: `spec.md > Output Sinks > output/txt.py`
  What to build: `webprobe/output/txt.py`. `render_txt(findings,
  errored_modules, args, target, duration) -> str` returns the
  ANSI-stripped form of the terminal FINDINGS block + summary. Reuse
  `render_findings_block` and `render_summary` from terminal.py with a
  copy of `args` forced to `no_color=True` (one source of truth for
  layout — TXT is just terminal output without color). Engine update:
  write the `.txt` file via `filename_for_target(..., ext="txt")` —
  always alongside HTML, matching base filename.
  Acceptance: Per `prd.md > Epic 3 > "report.txt paste-ready"`. Same
  base filename as HTML. No ANSI escape sequences.
  Verify: Run `python3 webprobe/probe.py http://example.com`. Confirm a
  `webprobe_*.txt` file is created alongside the `.html` with matching
  base name. `cat webprobe_*.txt` shows the FINDINGS block + summary
  with no escape sequences (no `\x1b[`).

- [ ] **15. profiles.py + --cakephp wiring**
  Spec ref: `spec.md > Framework Profiles`
  What to build: `webprobe/profiles.py`. `CAKEPHP_PATHS = [
  "/webroot/debug_kit/", "/debug-kit/", "/logs/", "/tmp/",
  "/config/app.php", "/config/app_local.php" ]`. Comment slot for Sprint
  2 profiles (`--django`, `--laravel`, `--rails`) — config additions, no
  engine plumbing. Engine update: `build_active_modules` — when
  `args.cakephp`, instantiate `PathsModule(path_list=load_default_paths()
  + CAKEPHP_PATHS)`. Banner displays `Profile: cakephp` (or `none`).
  Acceptance: Per `prd.md > Epic 5 > "framework profile to be a config
  addition"`. `--cakephp` adds 6 paths to paths module's pre-resolved
  list. Banner shows the active profile.
  Verify: `python3 webprobe/probe.py http://example.com --cakephp` —
  banner shows `Profile: cakephp`. With `-v`: verbose `[.]` lines show
  `/webroot/debug_kit/` and `/config/app_local.php` among attempted
  paths. Without `--cakephp`: those paths NOT attempted.

  → **CHECKPOINT C** — Stop after item 15. Generate a fresh report from
  a real target (FIT3047 if running, else example.com). Open
  `webprobe_*.html` in a browser via `file://`. Confirm:
  - HTML renders with print-friendly white-background palette
  - Severity grouping (default, no `--fit3048`) works
  - Click "Copy" next to a POC URL → paste-confirm URL is in clipboard
  - **Test in both Firefox and Chrome via `file://`.** Firefox is the
    required validation case (`navigator.clipboard.writeText` silently
    fails in non-secure context, so this is where the text-selection
    fallback gets exercised). Chrome is recommended because its
    `file://` behavior for clipboard is documented as inconsistent — if
    the primary path works in Chrome that's a bonus signal, not a
    requirement. Safari is optional. Acceptance: in Firefox, click Copy
    → see "Selected — Ctrl+C", press Ctrl+C, paste into editor → URL
    pasted. In Chrome, either path is acceptable as long as the URL
    ends up in the clipboard.
  - Re-run with `--fit3048` → HTML reorganizes into nested category →
    severity layout
  - Re-run with `--include-traversal` → OPERATIONAL_RISK chip appears
  - The `.txt` companion file matches base filename and is ANSI-clean

  Wait for explicit "go" before item 16.

- [ ] **16. README with FIT3048 advertisement**
  Spec ref: `spec.md > Runtime & Deployment` and `prd.md > Epic 5 >
  "install one command"`
  What to build: Replace the stub `README.md`. Sections: project name +
  one-line tagline ("A small, legible Python web vulnerability scanner —
  every detection module under 50 lines."); install (3 lines: `git
  clone`, `pip install -r requirements.txt`, `python3 webprobe/probe.py
  <target>`); usage examples (basic, `--cakephp`, `--fit3048`, `-v`,
  `--include-traversal`); explanation of the 6 modules + 3 output sinks
  + the 50-line legibility commitment; FIT3048 use case advertised
  (peer-assessment integration); contribution path advertised (BaseModule
  one-file drop-in); a "use Burp Suite for X" pointer for cases WebProbe
  doesn't cover (intercepting proxy, manual fuzzing, full HTTP traces).
  Screenshot placeholder block for terminal output and HTML report —
  filled in after item 17 with the FIT3047 finding screenshot.
  Acceptance: Junior dev with no security knowledge reads the README and
  can install + run + interpret one finding without referring to other
  docs.
  Verify: Read the README out loud. Does it pass the
  no-prior-security-knowledge bar?

- [ ] **17. End-to-end run against FIT3047 — win condition**
  Spec ref: `prd.md > Project Context > Two audiences for v1` (the
  FIT3047 use case) and `learner-profile.md > Win condition`
  What to build: Start the FIT3047 CakePHP server locally. Run `python3
  webprobe/probe.py http://localhost:<port>/<login-or-report-page>
  --cakephp --fit3048`. Capture: terminal screenshot (full inline teases
  + FINDINGS block + summary); the `.html` and `.txt` report files.
  Identify ≥1 *real* vulnerability the learner did not previously know
  was in their CakePHP app. If zero real findings: re-run against the
  report page; if still zero, investigate detection logic — likely a
  too-strict differential threshold in sqli (lower from 30% to 15%) or a
  missed payload-encoding case in xss; iterate the affected module's
  item and re-run. Add the terminal screenshot to README.md's screenshot
  block.
  Acceptance: Per `learner-profile.md > Win condition`. WebProbe produces
  ≥1 finding the learner did not know about. Findings are *actionable* —
  POC URL (when present) clicks through to a verifiable demonstration;
  remediation hint is non-trivial.
  Verify: Look at the screenshot. Would you have caught this vuln
  without WebProbe? If yes — win condition not met; iterate. If no —
  save the screenshot for Devpost; this IS the wow moment.

- [ ] **18. GitHub repo + Devpost submission**
  Spec ref: `prd.md > Project Context > Two audiences for v1`
  (open-source community framing) and `prd.md > What We're Building`
  What to build:
  - GitHub: create a public repository (`webprobe` or similar). Add as
    `origin` remote. `git push -u origin main`. Confirm repo is
    accessible via the public URL.
  - Devpost: open the submission form. Project name: `WebProbe`.
    Tagline: "A small, legible Python web vulnerability scanner — every
    detection module under 50 lines." Description: draft from
    `scope.md` + `prd.md` — the problem (commercial scanners too complex
    for student audits, existing OSS scanners not legible/actionable),
    the solution (6 modules + 3 output sinks + plugin architecture),
    what was learned (boolean-differential SQLi detection from scratch,
    spec/build line discipline). Include the FIT3047 use case as a
    concrete user story. Built-with tags: Python, requests,
    beautifulsoup4, colorama. Image gallery: terminal screenshot from
    item 17 (the FIT3047 finding moment) + HTML report screenshot. Link
    the GitHub repo. No deployed link (CLI tool — N/A). No demo video
    (optional, skipped). Submit.
  Acceptance: Devpost submission is live with green "Submitted" badge.
  All required fields complete. Repo is public + linked. Description is
  comprehensible to a stranger.
  Verify: Open the Devpost submission page in an incognito window.
  Confirm the project page renders. Read the description out loud —
  would someone who has never used a vulnerability scanner understand
  what WebProbe does and why it matters?
