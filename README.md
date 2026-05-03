# WebProbe

**Version: 2.0.0** — auth-aware web vulnerability scanning.

A small, legible Python web vulnerability scanner — every detection
module under 50 lines.

## What It Is

WebProbe is a CLI web vulnerability scanner built to make security
testing easier for Monash students taking FIT3047 (Industry Experience)
and FIT3048 (Industry Experience 2), and useful as a teaching/CTF
tool for anyone learning where common web flaws live.

It produces:

- Color-coded terminal output with severity-tagged findings, plus a
  `SCAN COVERAGE` block above FINDINGS that records what was actually
  probed (mode, sessions, URLs by source, modules fired, duration).
- Single-file HTML reports (shareable, printable, screenshot-ready).
- Plain-text reports paste-ready for reflective diaries and peer
  assessment forms.
- A versioned JSON envelope (`version: 2.0`) for downstream tooling,
  with `--json-out -` routing JSON to stdout (terminal to stderr) for
  pipe-friendly use.

## Why It Exists

FIT3047 teams need to audit their own CakePHP projects before demos.
FIT3048 students need to assess each other's projects against a
multi-category rubric. Both involve the same underlying work: run a
scanner, read findings, write up evidence. WebProbe collapses that
into one command.

## Built-In Course Support

### `--cakephp` profile

Adds CakePHP-specific path checks (debug_kit, logs, tmp, config) to
the sensitive-path scan. Use this when auditing your FIT3047 team
project.

### `--fit3048` flag

Organizes the HTML report into the FIT3048 7-category rubric used in
peer assessment. Each finding shows its category mapping.

## Detection Modules (v2)

Twelve modules, each ≤ 50 lines.

**Sprint 1 (v1) — passive / unauthenticated:**

- **headers** — security headers + cookie flags (HSTS, CSP, XFO,
  HttpOnly, Secure, SameSite)
- **info_disclosure** — Server / X-Powered-By headers, HTML comment
  leaks, framework version disclosure
- **paths** — sensitive path exposure via curated 162-path list
  (`.env`, `.git/`, `phpinfo.php`, backup files)
- **sqli** — boolean-differential + error-based SQL injection
- **xss** — reflected XSS via payload reflection detection
- **traversal** — path traversal (opt-in via `--include-traversal`)

**Sprint 2 (v2) — auth-aware / state-aware:**

- **access_control** — role-boundary probes against logged-in surface
- **idor** — cross-account leak detection via dual-session diff
- **csrf** — anti-CSRF token presence + state-changing form audit
- **error_leakage** — stack traces, framework error pages, debug
  banners surfaced in normal responses
- **session** — session-fixation, post-logout cookie replay, session
  ambiguity probes
- **brute_force** — login throttling / lockout absence (gated via
  `--include-brute-force`)

## Install

    git clone https://github.com/Ywbww/WebProbe.git
    cd WebProbe
    pip install -e .

For the optional Flask testbed (used by `python3 -m webprobe.testbed`
and `scripts/run_testbed_acceptance.sh`):

    pip install -e ".[testbed]"

Requires Python 3.10+. Core dependencies: `requests`, `beautifulsoup4`,
`colorama`. Testbed-only: `Flask`.

## Quick start

Unauthenticated single-target scan:

    webprobe http://example.com

Authenticated single-session scan with form-login:

    webprobe http://example.com \
        --auth-form http://example.com/login \
        --auth-user alice@example.com

(Password resolution chain: `--auth-pass`, then `WEBPROBE_AUTH_PASS`
env var, then interactive prompt.)

Dual-session scan for IDOR (canonical Sprint 2 acceptance command):

    webprobe https://your-target.example.com/team-app/ \
        --auth-form https://your-target.example.com/team-app/users/login \
        --auth-user coach_a@test.com \
        --idor-baseline-form https://your-target.example.com/team-app/users/login \
        --idor-baseline-user coach_b@test.com \
        --use-sitemap --fit3048

The IDOR module compares the primary session's response to the baseline
session's response on the same authed URL — a sha256 match across two
distinct user identities is the cross-account-leak signal.

You can also invoke the package directly without installing:

    python3 -m webprobe http://example.com

## Testbed walkthrough

The Sprint 2 testbed is a self-contained Flask app that exposes
intentional vulnerabilities for every v2 module. Start it, then point
WebProbe at it:

    python3 -m webprobe.testbed &
    webprobe http://localhost:9999 \
        --auth-form http://localhost:9999/login \
        --auth-user admin --auth-pass any \
        --idor-baseline-form http://localhost:9999/login \
        --idor-baseline-user alice --idor-baseline-pass any \
        --url-list <(echo -e "/idor/1\n/vulnerable?q=test")

For a fully reproducible end-to-end run (testbed + dual-session + three
output sinks captured to disk), use the canonical reproducer script:

    scripts/run_testbed_acceptance.sh

It produces `screenshots/sprint-2/`:

- `terminal-acceptance.txt` — terminal stream
- `default-grouping.{html,txt,json}` — the four output sinks
- `fit3048-grouping.html` — HTML report grouped by FIT3048 category
- `testbed-unauth.{html,txt}` — testbed scanned without auth (for
  comparison)

## Flag reference

    target_url               Required. http://localhost:* or public https://...
    --auth-form URL          Login page URL for form-based auth.
    --auth-user USER         Primary credential username.
    --auth-pass PASS         Primary password (or WEBPROBE_AUTH_PASS env).
    --auth-role LABEL        Role label for auth_context attribution.
    --cookie HEADER          RFC-6265 Cookie header for cookie-based auth.
    --idor-baseline COOKIE   Cookie string for IDOR baseline session.
    --idor-baseline-form URL Login URL for form-based IDOR baseline.
    --idor-baseline-user U   Username for IDOR baseline.
    --idor-baseline-pass P   Password for IDOR baseline.
    --logout-url URL         Explicit logout URL for the session module.
    --include-modules LIST   Comma-separated module names to include.
    --exclude-modules LIST   Comma-separated module names to exclude.
    --i-own-this-target HOST Hostname assertion required by gated modules.
    --include-brute-force    Opt in to brute_force module (gated).
    --include-traversal      Opt in to directory-traversal module.
    --use-sitemap            Discover URLs from /sitemap.xml.
    --use-sitemap-authed     Re-fetch /sitemap.xml with the authed session.
    --use-robots             Discover URLs from /robots.txt.
    --url-list FILE          Newline-separated URLs to probe.
    --fit3048                Group HTML report by FIT3048 category.
    --json-out PATH|-        JSON envelope output. '-' = stdout.
    --no-color / --force-color  ANSI control.

## Output

Each scan produces four sinks:

1. **Terminal stream** — banner, `SCAN COVERAGE` block, inline
   severity-tagged teases as findings emerge, then a `=== FINDINGS ===`
   block and a run summary.
2. **`webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.html`** — self-contained
   HTML report. Open with any browser, including university lab
   machines without internet.
3. **`webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.txt`** — ANSI-stripped
   plain text. Paste-ready into reflective diaries or peer-assessment
   forms.
4. **`webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.json`** — versioned
   JSON envelope (`version: 2.0`) with `scan`, `coverage`, and
   `findings` blocks. Override the path with `--json-out PATH`, or use
   `--json-out -` to route JSON to stdout (terminal text moves to
   stderr) for pipe-friendly composition.

## What's new in v2.0.0

- **Authentication & session setup** — form-login (`--auth-form`),
  cookie-based (`--cookie`), and a separate baseline session for IDOR
  (`--idor-baseline-form` / `--idor-baseline`). Two-session scans pin
  per-finding auth attribution ("as coach_a, baseline coach_b owns
  id=47") on every finding the renderer surfaces.
- **6 new detection modules** — `access_control`, `idor`, `csrf`,
  `error_leakage`, `session`, `brute_force`. The 6 v1 modules
  (`headers`, `info_disclosure`, `paths`, `sqli`, `xss`, `traversal`)
  were retrofitted to the v2 Module Contract (each ≤ 50 lines, Lock 5
  clean, registered via `@register`).
- **Self-contained Flask testbed** — `python3 -m webprobe.testbed`
  spins up a localhost target with intentional findings for every
  module, including a fixation-vulnerable session interface that
  serves three modules simultaneously (session_fixation +
  cookie_no_httponly + PHPSESSID detection).
- **`SCAN COVERAGE` block** — first-class evidence-of-work above
  FINDINGS. Records mode (Unauthenticated / Cookie-session /
  Authenticated single-session / Authenticated dual-session),
  sessions, URLs by source, modules fired/errored, and duration.
- **JSON output sink** — versioned envelope `version: 2.0`. Available
  on every run by default; `--json-out -` routes to stdout for piping.
- **Module Registry** — `@register` decorator replaces the v1 manifest;
  Engine Phase 1 enumerates `MODULE_REGISTRY` and validates required
  class attributes (`name`, `auth_strategy`, `FIT3048_CATEGORY_MAP`).
- **Engine phase ordering** — the pipeline is split into named phases
  (0.5 inter-flag validation → 1 enumeration → 2 user-flag filtering
  → 3.x connectivity/testbed/risk-gate → 4 URL pool → 5a-f auth setup
  → 6 module dispatch → 7 dedup + sinks). Each phase is a one-line
  coordinator; logic lives in helpers, surfacing the
  `phase-boundary-as-capability-boundary` invariant.
- **Risk gates** — `--include-brute-force` and `--i-own-this-target`
  for opt-in destructive probing, with automatic bypass when the
  testbed is detected.

## What WebProbe Does NOT Do

- Active fuzzing or deep payload exploration — use Burp Suite for that.
- Spidering or multi-page crawling beyond the URL pool resolved by
  `--url-list` / `--use-sitemap` / `--use-robots` / dynamic discovery.
- Anything destructive — all probes are GET/POST with read-only
  intent, except the brute-force module (gated and testbed-only by
  default).

## Architecture

Twelve detection modules under `webprobe/modules/`, each ≤ 50 lines.
Four output sinks under `webprobe/output/` (terminal, HTML, TXT, JSON).
Engine in `webprobe/engine.py` orchestrates the named phase pipeline;
each phase method is a one-line coordinator that delegates to helpers
in `webprobe/auth.py`, `webprobe/discovery.py`, `webprobe/filter.py`,
`webprobe/coverage.py`, etc. Modules conform to a `BaseModule`
contract; adding one is a single file decorated with `@register`.

The 50-line constraint per detection module is the project's central
legibility commitment — every module is hand-readable end-to-end in
under a minute.

## Screenshots

See `screenshots/sprint-2/` for the canonical Sprint 2 acceptance run
captures (terminal stream + 3 HTML reports + JSON envelope).

---

Last verified against: webprobe testbed v2.0.0
