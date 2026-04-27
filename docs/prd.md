# WebProbe — Product Requirements

## Project Context

**Project name:** WebProbe v1.0 — Web Security Scanner

**Two audiences for v1:**

1. **Primary: the author** — a cybersecurity student running WebProbe
   against (a) the FIT3047 / FIT3048 CakePHP wellness coaching app he
   owns, before unit demos and as evidence for the FIT3047 reflective
   diary and FIT3048 peer-assessment artifact, and (b) HackTheBox /
   TryHackMe CTF targets.
2. **Secondary: the broader student and junior-developer community.**
   WebProbe is open-sourced on GitHub from v1. The intended secondary
   user is anyone building real web apps who needs an actionable
   vulnerability scanner without learning Burp Suite or OWASP ZAP.

This is a meaningful expansion of the scope.md framing. Every UX
decision in v1 must clear *both* bars:

- **Output is self-explanatory.** The remediation hint and POC URL
  together must give a junior dev enough context to verify and fix
  without prior security knowledge.
- **Install is one command.** `pip install -r requirements.txt`. No
  Burp, no ZAP, no Docker, no Java runtime, no system-level deps.
- **Reports are self-contained.** A teammate or marker opens
  `report.html` in any browser — including restricted university lab
  environments with no CDN access — and reads findings without setup.
- **Architecture is extensible from day one.** New detection modules
  and framework profiles drop in as single files, so the open-source
  contribution promise is real even before contribution docs exist.

## Problem Statement

Cybersecurity students and junior developers building real web
applications need to verify their work is free of common vulnerabilities
before submission, demos, or deployment — but commercial scanners
(Burp Suite, OWASP ZAP) are too complex for casual pre-demo audits, and
existing open-source scanners (Wapiti, ZAP CLI) are either too large to
read end-to-end or produce findings that aren't actionable enough for
non-experts to verify and fix. The result: most students ship work
without security testing, then either get caught by markers or never
learn detection logic at the implementation level. WebProbe targets the
gap with a *legible* scanner — every detection module is hand-written,
under 50 lines, and ships findings with click-verifiable POC URLs and
one-line remediation hints.

## User Stories

### Epic 1 — Running a Scan

- **As a security-aware student**, I want to run a single command
  against my own web app and start getting findings, so I don't need to
  learn a Burp-style workflow before my pre-demo audit.
  - [ ] `python3 webprobe/probe.py http://localhost:8765` produces
        findings without any additional config or setup steps.
  - [ ] Install requires only Python 3 and `pip install -r
        requirements.txt`. No Burp, no ZAP, no Docker, no system deps.
  - [ ] Works against `http://localhost:*`, `http://127.0.0.1:*`, and
        public `https://...` targets without flag changes.

- **As a user**, I want to see what coverage I'm getting before the scan
  starts, so I know up front which detection categories are running.
  - [ ] Banner prints before any module runs, showing: tool name +
        version, target URL, list of active modules, active framework
        profile (or `none`), separator line.
  - [ ] If `--include-traversal` is *not* set, the banner explicitly
        advertises it as opt-in:
        `(traversal: opt-in via --include-traversal)`.
  - [ ] Banner is terse — under 6 lines, no flashy ASCII art.

- **As a user**, I want WebProbe to confirm the target is reachable
  before running modules, so a typo in the URL fails fast instead of
  producing a misleading clean-scan report.
  - [ ] Connectivity check is the first action after the banner:
        `[*] Checking target reachability...`.
  - [ ] On success: `[+] Target responding (HTTP <code>, <duration>s)`.
  - [ ] On failure (connection refused, DNS error, timeout):
        `[-] Target unreachable. Check URL and try again.` Exit
        immediately with non-zero status. No modules run.

### Epic 2 — Detecting Vulnerabilities

> **Detection input contract.** Every active module receives the
> user-supplied URL plus auto-discovered form fields and URL query
> parameters from that page. WebProbe loads the given URL once, parses
> HTML for `<form>` and `<input>` elements, and tests each injectable
> parameter. WebProbe does **not** follow links, spider, or test pages
> other than the one given. Multi-page coverage is achieved via multiple
> invocations.

- **As a CakePHP developer auditing my login form**, I want WebProbe to
  detect SQL injection on form fields and URL params via
  boolean-differential testing and error-string matching.
  - [ ] Module name: `sqli`. Tests every discovered form field and URL
        query param.
  - [ ] Sends 7 curated payloads per parameter in v1: `'`, `"`, `1'`,
        `1' OR '1'='1`, `1' AND '1'='2`, `1 AND 1=1`, `1 AND 1=2`. The
        time-based payload `1' AND SLEEP(1)--` only fires under
        `--aggressive` (Sprint 2 flag — payload skipped in v1).
  - [ ] Boolean-differential: a `1' OR '1'='1` response that materially
        differs from a `1' AND '1'='2` response on the same parameter
        triggers a `HIGH` finding.
  - [ ] Error-based: SQL error strings in the response (`SQLSTATE`,
        `mysql_fetch_array()`, `MariaDB`, etc.) trigger a `HIGH`
        finding.
  - [ ] Findings carry the parameter name and the differentiating
        evidence inline
        (e.g. `Evidence: 'OR 1=1' returned 47 rows; 'AND 1=2' returned 0`).
  - [ ] Maps to FIT3048 Category 5 (Input Validation and Error
        Handling).

- **As a CakePHP developer**, I want reflected XSS detection on the same
  parameter surface as SQLi.
  - [ ] Module name: `xss`. Tests every discovered form field and URL
        query param.
  - [ ] Sends 6 curated payloads per parameter:
        `<script>alert(1)</script>`, `"><svg/onload=alert(1)>`,
        `'><img src=x onerror=alert(1)>`, `javascript:alert(1)`,
        `<body onload=alert(1)>`, `'"><script>alert(1)</script>`.
  - [ ] Reflection check: payload appears unescaped in the response
        body → `HIGH` finding.
  - [ ] POC URL is a click-ready URL with the working payload encoded
        into the parameter (DalFox-style).
  - [ ] Maps to FIT3048 Category 5 (Input Validation and Error
        Handling).

- **As a CakePHP developer**, I want WebProbe to find exposed sensitive
  paths, with `--cakephp` adding CakePHP-specific paths to the curated
  list.
  - [ ] Module name: `paths`. Always runs against the target's host
        root.
  - [ ] Default curated path list includes: `/.env`, `/.git/HEAD`,
        `/.git/config`, `/phpinfo.php`, `/info.php`, `/server-status`,
        `*.bak`, `*.old`, `/backup.sql`, `/db.sql`.
  - [ ] `--cakephp` profile adds: `/webroot/debug_kit/`, `/debug-kit/`,
        `/logs/`, `/tmp/`, `/config/app.php`, `/config/app_local.php`.
  - [ ] HTTP 200 / 301 / 302 / 403 → flagged. HTTP 404 → not flagged.
  - [ ] Severity: `HIGH` for `.env`, `.git/*`, `app_local.php`,
        `db.sql`. `MEDIUM` for `phpinfo.php`, `debug_kit`. `LOW` for
        `*.bak`, `*.old`.
  - [ ] Maps to FIT3048 Category 3 (Sensitive Information Exposure).

- **As a security-aware student**, I want missing security headers and
  unsafe cookie flags reported.
  - [ ] Module name: `headers`. Performs a single GET on the target and
        parses response headers.
  - [ ] Reports missing: `Content-Security-Policy`, `X-Frame-Options`,
        `Strict-Transport-Security`, `X-Content-Type-Options`,
        `Referrer-Policy`.
  - [ ] Reports `Set-Cookie` flags missing: `HttpOnly`, `Secure`,
        `SameSite=Strict|Lax`.
  - [ ] Severity assignments:
        - HSTS missing on HTTPS = `HIGH`.
        - CSP missing = `MEDIUM`.
        - X-Frame-Options missing = `MEDIUM`.
        - Cookie without `HttpOnly` = `MEDIUM`.
        - Cookie without `Secure` (on HTTPS) = `HIGH`.
        - Cookie without `SameSite` = `LOW`.
  - [ ] Header findings map to FIT3048 Category 5 (Input Validation and
        Error Handling). Cookie-flag findings map to FIT3048
        Category 4 (Session Management).

- **As a junior dev**, I want passive info-disclosure findings that flag
  without sending exploit traffic.
  - [ ] Module name: `info-disclosure`. Pure passive — no payloads.
  - [ ] Parses the same response collected by the headers module
        (no extra HTTP request needed).
  - [ ] Reports: `Server` banner, `X-Powered-By` framework version,
        HTML comments containing `TODO` / `FIXME` / dev or staging
        URLs, verbose stack traces in body.
  - [ ] Severity: `LOW` for server banner / framework version. `MEDIUM`
        for verbose stack trace. `MEDIUM` for HTML comment containing
        an internal URL.
  - [ ] Zero false-positive risk by design — only reports what is
        objectively present in the response.
  - [ ] Maps to FIT3048 Category 3 (Sensitive Information Exposure).

- **As a CakePHP developer with file upload/download features**, I want
  directory-traversal detection — opt-in to manage operational risk.
  - [ ] Module name: `traversal`. **OFF by default.** Only runs when
        `--include-traversal` is explicitly set.
  - [ ] **Not** enabled by `--cakephp` profile. No silent activation
        from any framework profile.
  - [ ] Sends 5 payloads per discovered parameter and against URL path
        segments: `../../../etc/passwd`, `..%2f..%2f..%2fetc%2fpasswd`,
        `....//....//....//etc/passwd`,
        `..\\..\\..\\windows\\win.ini`, `/etc/passwd`.
  - [ ] Detection: response body contains `root:x:0:0:` (Unix passwd
        signature) or `[fonts]` / `[extensions]` (Windows win.ini
        signature) → `CRITICAL` finding.
  - [ ] When `--include-traversal` was used, the HTML report header
        carries an `OPERATIONAL_RISK` note: "this scan included
        path-traversal payloads, which generate noisy logs on the
        target."
  - [ ] Maps to FIT3048 Category 3 (Sensitive Information Exposure).

### Epic 3 — Communicating Findings

- **As a user during the scan**, I want one-line severity-tagged teases
  as findings emerge, so I can react in real time.
  - [ ] Each finding prints inline at the moment of detection:
        `[<SEVERITY>] <one-line summary>`.
  - [ ] Marker convention is reserved and consistent:
        - `[*]` = module/action progress (e.g.,
          `[*] Running: Sensitive Paths...`).
        - `[+]` = benign success/status note inside a module's
          narration (e.g., `[+] Target responding (HTTP 200, 0.3s)`).
        - `[-]` = run-level failure (e.g., target unreachable).
        - `[!]` = warning or module error.
        - `[CRITICAL]` / `[HIGH]` / `[MEDIUM]` / `[LOW]` / `[INFO]` =
          finding tags. Reserved for findings only.
  - [ ] Inline tease lines stay on screen — they are NOT replaced by
        the full block later.

- **As a user at the end of the scan**, I want a `=== FINDINGS ===`
  block with full multi-line details I can read or screenshot.
  - [ ] After all modules complete, print a divider line followed by
        `══════════════════ FINDINGS ══════════════════`.
  - [ ] Each finding renders with: severity-tagged title, `URL:`,
        `POC:` (omitted for findings without a POC, e.g. passive),
        `Evidence:`, `Fix:`, and (when `--fit3048` is on) `FIT3048:`.
  - [ ] Order: severity descending
        (CRITICAL → HIGH → MEDIUM → LOW → INFO).
  - [ ] If any modules errored, a `MODULES WITH ERRORS` sub-block lists
        them with the exception type and a one-line tip.

- **As a user**, I want a summary line at the end that always prints —
  even on clean scans — as evidence the scan ran.
  - [ ] Summary always prints, with these fields:
        `Target:`, `Modules: <scheduled> scheduled, <completed>
        completed, <errored> errored`,
        `Findings: <total> (<n> CRITICAL, <n> HIGH, ...)`,
        `Report: <html-filename>`, `Duration: <s>`.
  - [ ] Clean scan: `Findings: 0 — no issues detected`.
  - [ ] Partial scan (any module errored OR target degraded mid-scan):
        the summary prints `⚠ Partial scan — results may be
        incomplete`. Silent partial failure is unacceptable.

- **As a user**, I want a self-contained HTML report I can open anywhere
  and share as a single file.
  - [ ] Default filename:
        `webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.html`. Slashes in
        the URL path are stripped — only host+port preserved. If two
        runs would produce the same filename within the same second,
        the second gets a `_2` suffix.
  - [ ] One file. Inline `<style>` only. No external CSS, no CDN
        dependencies. Inline `<script>` allowed only for the POC
        copy-to-clipboard button.
  - [ ] Top of page: header bar showing target + timestamp + finding
        counts by severity (e.g., `3 HIGH | 1 MEDIUM | 0 LOW`). No
        table of contents — counts at the top are sufficient
        navigation for a single scrollable page.
  - [ ] Default body grouping: severity sections worst → best, each
        with a colored header bar.
  - [ ] With `--fit3048`: two-level grouping — FIT3048 Category
        (1 → 10) → severity within each. Severity section headers
        still appear nested inside each category.
  - [ ] All findings are *always expanded* — no collapse/expand
        toggle. Evidence and fix visible without clicking.
  - [ ] POC URL renders as a clickable `<a>` plus a small
        copy-to-clipboard button.
  - [ ] When `--include-traversal` was used, the header bar carries
        an `OPERATIONAL_RISK` note describing the noisier scan
        profile.
  - [ ] Color palette tuned for white background (printable,
        screenshottable):
        - `CRITICAL: #C0392B` (deep red)
        - `HIGH: #E74C3C` (red)
        - `MEDIUM: #F39C12` (amber — yellow is unreadable on white)
        - `LOW: #3498DB` (blue — terminal cyan prints/photocopies
          poorly)
        - `INFO: #7F8C8D` (grey)
        - Background: white. Body text: `#2C3E50` (near-black, easier
          on eyes than pure black). Severity badges: white text on
          the colored chip.
  - [ ] Opens correctly in restricted university lab browsers (no CDN,
        no JS runtime requirements beyond inline button handlers).

- **As a user submitting a lab writeup or FIT3048 peer assessment**, I
  want a `report.txt` paste-ready into a text-only form.
  - [ ] TXT report is the ANSI-stripped form of the terminal
        `=== FINDINGS ===` + `=== SUMMARY ===` block.
  - [ ] Same default filename pattern as the HTML report, with `.txt`
        extension. Always written alongside the HTML.

- **As a user piping output to a file or running in CI**, I want color
  to behave correctly without manual flag-setting in the common case.
  - [ ] Default: auto-detect via `sys.stdout.isatty()`. If False, ANSI
        codes are stripped automatically.
  - [ ] `--no-color` forces colors off (overrides TTY detection).
  - [ ] `--force-color` forces colors on (for `less -R` piping).

- **As a verbose user debugging a scan**, I want optional finer-grained
  narration.
  - [ ] Default: module-level start/end + findings + errors only.
  - [ ] `-v`: also print every path attempted and every payload tried,
        prefixed with `[.]`.
  - [ ] No `-vv`. For full HTTP traces, the `--help` text directs the
        user to Burp Suite.

### Epic 4 — Trusting Partial Results

- **As a user**, I want module crashes isolated and surfaced visibly,
  so the scan continues and I see exactly what failed.
  - [ ] Every module runs inside `try/except`. Unhandled exceptions
        are caught, never allowed to abort the run.
  - [ ] On exception, an inline line prints immediately:
        `[!] <module>: errored (<ExceptionType>) — skipped`.
  - [ ] After all modules complete, errored modules appear in a
        `MODULES WITH ERRORS` section in the FINDINGS block with the
        exception type and a brief tip
        (e.g., `Tip: target may have returned binary content on one
        path`).
  - [ ] The errored module count is reflected in the summary's
        `Modules:` line.

- **As a user scanning a flaky target**, I want degradation flagged
  before the run ends in confusion.
  - [ ] After 3 consecutive HTTP-level failures (timeouts, 5xx,
        connection resets) within a single module, print:
        `[!] Target appears degraded — 3 consecutive failures.
        Completing remaining modules with reduced confidence.`
  - [ ] Remaining modules still run.
  - [ ] Summary's partial-scan flag fires.

- **As a user**, I want never to mistake a partial scan for a clean
  target.
  - [ ] Whenever any module errored OR the degradation warning fired,
        the summary's `⚠ Partial scan — results may be incomplete`
        line is mandatory.
  - [ ] The HTML report mirrors this — partial-scan banner at the top
        of the report when applicable.

### Epic 5 — Extending and Sharing

- **As a contributor**, I want adding a new detection module to be a
  single-file drop-in.
  - [ ] Every detection module conforms to the `BaseModule` contract
        (signature pinned in /spec): `name`, `category`, `severity`,
        and a `run(target, session) -> list[Finding]` method.
  - [ ] Adding a module = creating one file in
        `webprobe/modules/<name>.py` (and optionally registering it in
        a small modules manifest). No engine changes.
  - [ ] Each detection module file is **under 50 lines of Python.**
        Non-negotiable. This is the project's central legibility
        commitment.

- **As a contributor**, I want adding a new framework profile to be a
  config addition with no engine code change.
  - [ ] A framework profile = `{module_subset, additional_paths,
        additional_payloads}` config entry.
  - [ ] `--cakephp` is the v1 reference profile. `--django`,
        `--laravel`, `--rails` are Sprint 2 — but the slot must work
        in v1 (i.e., dropping a new profile config in is sufficient,
        no engine plumbing).

- **As a junior dev installing WebProbe for the first time**, I want
  install to be one command on top of Python 3.
  - [ ] `git clone <repo> && pip install -r requirements.txt &&
        python3 webprobe/probe.py <target>` is the install + run flow.
  - [ ] No Burp, no ZAP, no Docker, no Java runtime, no system-level
        deps.
  - [ ] Dependencies: `requests`, `beautifulsoup4`, and (likely)
        `colorama` for cross-platform ANSI. No more.

- **As a teammate or marker receiving `report.html`**, I want to open
  it in any browser without setup.
  - [ ] Single-file HTML, inline CSS, inline JS only for the
        copy-to-clipboard button, no external assets.
  - [ ] Renders correctly in restricted environments (university lab
        Windows browsers without internet access).

## What We're Building (v1, ~3–4 hours)

Headline summary of the Sprint 1 ship:

- **6 detection modules:** `sqli`, `xss`, `paths`, `headers`,
  `info-disclosure`, `traversal` (opt-in via `--include-traversal`).
- **1 framework profile:** `--cakephp`.
- **3 output sinks:** severity-grouped colored terminal output;
  self-contained HTML report (white-background palette);
  ANSI-stripped TXT report.
- **`--fit3048` flag:** two-level grouping in the HTML report mapped to
  the 10-category peer-assessment rubric. `fit3048_category` field on
  every finding regardless of flag.
- **CLI surface:** target URL (positional), `--only`, `--output`,
  `--cakephp`, `--fit3048`, `--include-traversal`, `--no-color`,
  `--force-color`, `-v`.
- **Plugin architecture:** `BaseModule` contract; modules are single
  files in `webprobe/modules/`; framework profiles are config entries.
- **Reliability:** connectivity check before scan, partial-scan trust
  signal in summary, per-request 5s timeout, hard 90s scan ceiling.

## CLI Surface (v1)

```
python3 webprobe/probe.py <target_url> [flags]

Flags:
  --only sqli,xss               Comma-separated list of modules to run.
                                Module names: sqli, xss, paths, headers,
                                info-disclosure, traversal.
                                Invalid name → fail fast with valid list.
  --output ./reports/           Directory for report files.
                                Default: current working directory.
                                Filenames are auto-generated; never
                                user-controlled (so .html and .txt
                                pair always matches).
  --cakephp                     Activate CakePHP framework profile —
                                adds CakePHP-specific paths to the
                                paths module.
  --fit3048                     Group HTML report by FIT3048 peer-
                                assessment category (10 categories,
                                category → severity nested grouping).
  --include-traversal           Opt in to the directory-traversal
                                module. Off by default. Generates
                                noisy logs on the target.
  --no-color                    Force ANSI colors off (overrides TTY
                                detection).
  --force-color                 Force ANSI colors on (for `less -R`
                                piping).
  -v                            Verbose: print every path and payload
                                attempted, prefixed with `[.]`.
                                No -vv. For full HTTP traces, use Burp.
```

## Data Model — Finding Object

Every finding emitted by every module conforms to this shape:

```python
{
    "severity":         "HIGH",
    # CRITICAL | HIGH | MEDIUM | LOW | INFO

    "category":         "xss",
    # short slug per detection module: sqli|xss|paths|headers|
    # info-disclosure|traversal

    "name":             "Reflected XSS",
    # human-readable name

    "url":              "http://localhost:8765/search",
    # where the issue was found

    "parameter":        "q",
    # form field or URL query param name (null for passive findings)

    "payload":          "<script>alert(1)</script>",
    # what was injected (null for passive checks)

    "evidence":         "payload reflected unescaped in response body",
    # one-line "why we believe this"

    "poc_url":          "http://localhost:8765/search?q=...",
    # click-to-verify URL (null for passive findings)

    "remediation":      "Encode output with htmlspecialchars()",
    # one-line fix hint

    "fit3048_category": 5,
    # 1-10 integer, the peer-assessment rubric category this finding
    # maps to. Always populated in v1 — every detection has a mapping.
}
```

## Performance & Operational Requirements

- **Typical scan completes in under 30 seconds** for a developer-laptop
  scan against a localhost CakePHP target running 5 modules, ~300-path
  sensitive-paths sweep, and a single login page with 2 form fields.
- **Hard scan ceiling: 90 seconds.** After 90s, WebProbe prints a
  timeout warning and emits whatever findings were collected.
- **Per-request timeout: 5 seconds.**
- **Connectivity check timeout: 5 seconds.**
- **Concurrency model (open for /spec confirmation):**
  - `paths` module uses `ThreadPoolExecutor(max_workers=20)` to
    parallelize HTTP requests across the curated path list (300 paths
    × 1s sequential = unacceptable 5-minute wait).
  - `sqli`, `xss`, `traversal` modules stay sequential per parameter —
    payload count is small, ordering matters for evidence quality.
  - `headers` and `info-disclosure` use a single shared response (one
    GET, both modules parse it).

## What We'd Add With More Time (Sprint 2)

- **Authenticated scanning:** `--cookie <jar>`,
  `--auth-form <login-url>:<user-field>:<pass-field>:<creds>`.
- **More framework profiles:** `--django`, `--laravel`, `--rails`,
  `--express`.
- **`--severity-min <level>`** filter (suppress findings below the
  given severity in output and report).
- **`--aggressive`** flag enabling time-based blind SQLi
  (`SLEEP()`-style payloads) and other higher-risk probes.
- **Crawler / spider mode** with depth limit and scope rules.
- **`--urls <file>`** to test multiple endpoints in one invocation.
- **Contribution docs:** `CONTRIBUTING.md`, module-authoring guide,
  profile-authoring guide.
- **Additional detection modules:** CSRF token presence (beyond
  trivial check), CORS misconfiguration, open redirects.

## Non-Goals (v1)

- **Authenticated scanning is not in v1.** Operational risk:
  aggressive login probing can lock real users out of shared
  environments (FIT3047 dev server, HTB labs). Authentication support
  is Sprint 2 with explicit `--cookie` / `--auth-form` flags.
- **CSRF token validation is not in v1.** Doing this past a trivial
  "is there a token field?" check requires framework-specific
  knowledge; half-implemented CSRF is worse than absent.
- **CORS misconfiguration scanning is not in v1.** Medium
  implementation effort, low find-rate on student projects and CTF
  boxes.
- **No spidering, link-following, or multi-URL scanning.** v1 tests
  only the URL the user gave, plus auto-discovered forms and URL
  params on that page. Multi-page coverage = multiple invocations.
- **Not a Burp Suite replacement.** WebProbe does not provide an
  intercepting proxy, manual fuzzing, or full HTTP traces. Users
  needing those should use Burp; `--help` says so.
- **No CI/CD integration in v1.** No JSON output, no exit-code-encodes-
  severity, no JUnit XML. WebProbe is interactive or piped to a file.

## Open Questions

All seven /scope open questions resolved during /prd. A small handful
remain for /spec to nail down:

- **`BaseModule` exact signature.** Captured at the contract level
  (`name`, `category`, `severity`, `run(target, session) ->
  list[Finding]`). Finalize: type hints, default `severity` semantics
  (per-finding override?), and how each module declares its FIT3048
  mapping (per-module default vs per-finding override). **Needs
  answering before /spec lands its module-architecture section.**
- **Concurrency confirmation.** `ThreadPoolExecutor(20)` for `paths`
  is decided. Confirm `sqli` / `xss` / `traversal` stay sequential,
  and whether `requests.Session` is shared across threads or
  one-per-thread. **Needs answering before /spec finalizes the
  engine.**
- **HTML inline JS for copy-to-clipboard.** A handful of lines using
  `navigator.clipboard.writeText` is enough; finalize whether we ship
  a `document.execCommand('copy')` fallback for older browsers. **Can
  wait — defer to /spec.**
- **`--help` text shape.** Auto-generated by `argparse`, but the
  description and epilog should advertise the FIT3048 use case, the
  open-source contribution path, and a one-line "use Burp for X"
  pointer. **Can wait — /spec or /build.**
- **HTML report timestamp timezone.** Local time? UTC? Both? **Can
  wait — /spec or /build.**
