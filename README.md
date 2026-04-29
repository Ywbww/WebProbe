# WebProbe

A small, legible Python web vulnerability scanner — every detection
module under 50 lines.

## What It Is

WebProbe is a CLI web vulnerability scanner built to make security
testing easier for Monash students taking FIT3047 (Industry Experience)
and FIT3048 (Industry Experience 2).

It produces:

- Color-coded terminal output with severity-tagged findings
- Single-file HTML reports (shareable, printable, screenshot-ready)
- Plain-text reports paste-ready for reflective diaries and peer
  assessment forms

## Why It Exists

FIT3047 teams need to audit their own CakePHP projects before demos.
FIT3048 students need to assess each other's projects against a
10-category rubric. Both involve the same underlying work: run a
scanner, read findings, write up evidence. WebProbe collapses that
into one command:

    python3 webprobe/probe.py http://your-project.com --cakephp --fit3048

## Built-In Course Support

### `--cakephp` profile

Adds CakePHP-specific path checks (debug_kit, logs, tmp, config) to
the sensitive-path scan. Use this when auditing your FIT3047 team
project.

### `--fit3048` flag

Organizes findings into the 10-category rubric used in FIT3048 peer
assessment. Each finding shows its category mapping, so the HTML
report maps directly onto your assessment form.

Categories currently produced by detection modules:

    Category 2 — Admin and User Privileges
    Category 3 — Sensitive Information Exposure
    Category 4 — Session Management
    Category 5 — Input Validation and Error Handling

(Categories 1, 6, 7, 8, 9, 10 require manual or authenticated
testing — WebProbe surfaces what passive + light-active probing
can detect.)

## Detection Modules (v1)

- **headers** — security headers + cookie flags (HSTS, CSP, XFO,
  HttpOnly, Secure, SameSite)
- **info-disclosure** — Server / X-Powered-By headers, HTML comment
  leaks, framework version disclosure
- **paths** — sensitive path exposure via curated 162-path list
  (`.env`, `.git/`, `phpinfo.php`, backup files)
- **sqli** — boolean-differential + error-based SQL injection
- **xss** — reflected XSS via payload reflection detection
- **traversal** — path traversal (opt-in via `--include-traversal`)

## Install

    git clone https://github.com/Ywbww/WebProbe.git
    cd WebProbe
    pip3 install -r requirements.txt

Requires Python 3.10+. Three dependencies: `requests`,
`beautifulsoup4`, `colorama`.

## Usage

Basic scan:

    python3 webprobe/probe.py http://localhost:8765

Audit your FIT3047 CakePHP project:

    python3 webprobe/probe.py http://localhost:8765 --cakephp

Generate a FIT3048-grouped report for peer assessment:

    python3 webprobe/probe.py http://localhost:8765 --cakephp --fit3048

Verbose output (every path and payload attempted):

    python3 webprobe/probe.py http://localhost:8765 -v

Run a subset of modules:

    python3 webprobe/probe.py http://example.com --only headers,sqli

Opt in to directory traversal (noisy on the target's logs):

    python3 webprobe/probe.py http://localhost:8765 --include-traversal

### Flag reference

    target_url               Required. http://localhost:* or public https://...
    --only MODULES           Comma-separated subset of {sqli, xss, paths,
                             headers, info-disclosure, traversal}.
    --output DIR             Output directory for reports. Default: cwd.
    --cakephp                Activate CakePHP framework profile.
    --fit3048                Group HTML report by FIT3048 category.
    --include-traversal      Opt in to directory-traversal module.
    --no-color               Force ANSI off.
    --force-color            Force ANSI on.
    -v                       Verbose: print every path/payload attempted.

## Output

Each scan produces three things:

1. Terminal output — inline severity-tagged teases as findings emerge,
   followed by a `=== FINDINGS ===` block and a summary line.
2. `webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.html` — self-contained
   HTML report (inline CSS + a tiny inline clipboard handler, no
   external assets). Open it with any browser, including university
   lab machines without internet.
3. `webprobe_<host>_<port>_<YYYYMMDD>_<HHMMSS>.txt` — ANSI-stripped
   plain text. Paste-ready into reflective diaries, peer-assessment
   forms, or any text-only field.

The `.html` and `.txt` siblings always share a base name.

## What WebProbe Does NOT Do

- Authenticated scanning (logged-in surface) — Sprint 2.
- Active fuzzing or deep payload exploration — use Burp Suite for that.
- Spidering or multi-page crawling — pass the URL you want tested;
  multi-page coverage is multiple invocations.
- Anything destructive — all probes are GET/POST with read-only intent.

## Architecture

Six detection modules under `webprobe/modules/`, each ≤ 50 lines.
Three output sinks under `webprobe/output/` (terminal, HTML, TXT).
Engine in `webprobe/engine.py` orchestrates: banner → connectivity
check → form/param discovery → module dispatch (with per-module
try/except + 90s scan ceiling) → render. Modules conform to a
`BaseModule` contract; adding one is a single file plus a manifest
entry.

The 50-line constraint per detection module is the project's central
legibility commitment — every module is hand-readable end-to-end in
under a minute.

## Screenshots

_(Filled in after running against a real target — see `docs/` for
examples from the FIT3047 audit run.)_
