# WebProbe

A Python CLI web vulnerability scanner that finds real, actionable issues
in web apps you own — and stays small enough that you can read every line
of detection logic.

## Idea

A black-box web vulnerability scanner with **Wapiti's scope, DalFox's
output philosophy, and an architectural commitment to legibility**: every
detection module readable in fewer than 50 lines of Python. One
`python3 webprobe/probe.py <url>` command produces severity-tagged findings
in the terminal, an HTML report, and a TXT report — each finding actionable
enough to verify in a browser via a click-ready POC URL.

The project exists to make the *detection logic itself* the learning
artifact: not a wrapped library or a YAML-template runner, but hand-written
Python the author can read, defend, and extend.

## Who It's For

**Primary user: the author** (cybersecurity student) in two contexts:

1. **Pre-demo audits of the FIT3047 CakePHP project.** Running WebProbe
   against the deployed app *and* the localhost dev environment to catch
   issues — exposed paths, missing security headers, reflected XSS,
   SQL-injectable parameters — before a tutor or marker finds them.
2. **CTF reconnaissance on HackTheBox / TryHackMe targets.** A trusted,
   auditable scanner that won't silently mislead. Every finding can be
   manually verified via the included POC URL.

**Secondary use:** sharing reports with FIT3047 teammates to surface
security gaps in shared codebases. Reports must be screenshot-friendly and
paste-ready for lab writeups and the unit's reflective diary.

**Not for:** professional pentesting, automated CI scanning of third-party
sites, or anything requiring the breadth of a commercial scanner.

## Inspiration & References

Three reference projects, each contributing one design lever:

- **[Wapiti](https://github.com/wapiti-scanner/wapiti)** — *scope and shape.*
  Python, black-box, multi-vuln, multi-format reports (HTML + TXT). The
  closest functional ancestor; WebProbe v1 = "Wapiti, but smaller and
  fully readable." What's *wrong* with Wapiti for this project: too large
  to read end-to-end, too black-box for the learning goal.
- **[DalFox](https://github.com/hahwul/dalfox)** — *output philosophy.*
  Click-ready POC URLs, evidence shown inline, single-vuln-class deep
  rather than ten-vuln-classes shallow. WebProbe steals the philosophy
  ("the user should be able to verify a finding in their browser without
  re-running the tool") even though the scope is wider.
- **[Nuclei](https://github.com/projectdiscovery/nuclei)** — *terminal
  output aesthetic and modular shape.* Severity-tagged findings, clean
  alignment, one detection per file. WebProbe takes the *shape* (one
  module per vuln class, swappable) without taking the *templating*
  (detection logic stays in hand-written Python, not YAML).

### Aesthetic direction

CTF tooling (HackTheBox / TryHackMe energy) softened by Mandopop calm —
*not* green-on-black 90s-hacker-movie. Dark background, muted greys for
status lines, **bright color reserved for real findings only**.

Severity palette:

- `RED` — CRITICAL / HIGH
- `YELLOW` — MEDIUM
- `CYAN` — LOW
- `WHITE` — INFO
- `GREY` — clean / passed checks

The emotional target is the *satisfying flag-drop moment* of a CTF, not
the relentless red of a corporate scan report.

## Goals

**Primary learning goal.** Understand web vulnerability detection at the
implementation level — specifically, how tools like Burp Suite decide that
a parameter is XSS- or SQLi-injectable. The boolean-differential SQLi
detection module is the project's flagship for this goal: send two
requests crafted to produce *different* responses if the parameter is
injectable, and decide based on the differential. Building this from
scratch is the point.

**Win condition.** Run WebProbe against the FIT3047 CakePHP project's
login page on localhost, have it catch a real issue (e.g. missing HSTS
header, exposed DebugKit panel, reflected XSS in a search parameter),
screenshot the output, and paste it into the FIT3047 reflective diary as
evidence of pre-demo security testing.

**Secondary goals.**

- Build a tool that's *small enough to read*. Every detection module
  under 50 lines is the architectural commitment — non-negotiable.
- Produce findings that are *actionable* — every finding ships with a
  click-verifiable POC URL and a one-line remediation hint.
- Support both **deployed targets** (`https://...`) and **localhost
  targets** (`http://localhost:8765`, `http://127.0.0.1:8080`) as
  first-class. No assumption that the target is public-facing.

## What "Done" Looks Like

After 3–4 hours of build time, running:

```
python3 webprobe/probe.py http://localhost:8765
```

…against the FIT3047 CakePHP login page produces:

1. **Color-coded terminal output**, one block per finding:

   ```
   [HIGH] Reflected XSS
     URL:        http://localhost:8765/search?q=<script>alert(1)</script>
     Evidence:   payload found unescaped in response body
     POC:        http://localhost:8765/search?q=<img+src=x+onerror=alert(1)>
     Fix:        Encode output with htmlspecialchars() in PHP
   ```

   …followed by a run summary: `Scan complete — 5 categories checked,
   N findings.` Even on a clean target, this summary prints — it's
   evidence-of-work for the reflective diary.

2. **`report.html`** — a single scrollable, dark-mode page. Findings
   grouped by severity (CRITICAL → INFO). Each finding row expands to
   show full evidence and the remediation hint. Designed to be
   screenshotted in one frame for a writeup.

3. **`report.txt`** — plaintext, paste-ready for FIT3047 lab writeups.

The "done" emotional moment: WebProbe catches the missing HSTS header
*and* flags `/debug-kit/` (or `/webroot/debug_kit/`) as exposed on the
FIT3047 dev server. The author screenshots the terminal output, pastes
it into the reflective diary under "pre-demo security check," and ships
the assignment.

## What's Explicitly Cut

Detection categories considered and removed from v1, with reasons:

- **Authentication issues / rate-limiting / default credentials.** *Cut.*
  Operational risk: aggressive login probing can lock real users out of
  shared environments, including the FIT3047 project. A correct
  implementation also runs to ~200 lines, breaking the <50-line rule.
- **CSRF token detection.** *Cut.* Doing this past a trivial "is there a
  token field?" check requires CakePHP-specific knowledge of correct
  CSRF behavior. Won't generalize to HTB / THM targets, where forms are
  framework-agnostic. Half-implemented CSRF is worse than absent.
- **CORS misconfiguration.** *Deferred to v2.* Medium implementation
  effort, low "find something" rate on student projects and CTF boxes.
- **Directory traversal.** *Deferred to v2 (not killed).* Path-traversal
  payloads can trip WAFs and dirty up logs on real targets. Want to
  understand the operational risk better — and design the payload set
  more carefully — before shipping. The deferral is a *judgment call*,
  not a time cut.

The cut discipline encoded here: every removal carries a *named reason*
(time, blast radius, generalization, operational risk), not "we ran out
of time."

## Loose Implementation Notes

Non-binding early thinking. Final decisions live in `/spec`.

### Detection modules (priority order)

1. **SQL injection** — boolean differential + error-based. *Flagship.*
   The detection module that justifies the project. Send two crafted
   requests that should produce different responses if the parameter is
   injectable; flag based on the differential. Also catch error strings
   (`SQLSTATE`, `mysql_fetch_array()`, MariaDB error patterns) as a
   secondary signal.
2. **Reflected XSS** — payload injection + reflection-context analysis.
   Inject a unique probe string with characteristic markers, check
   whether it appears in the response body unescaped, then run the real
   XSS payload. POC URL output in the DalFox style.
3. **Sensitive path exposure.** Loop a curated list of paths
   (`/.env`, `/.git/HEAD`, `/.git/config`, `/phpinfo.php`,
   `/debug-kit/`, `/webroot/debug_kit/`, `*.bak`, `*.old`). Flag on
   200 / 301 / 302 / 403 status codes (not 404). High guaranteed-find
   rate on real targets.
4. **Security headers + cookie flags.** Parse response headers; report
   missing `Content-Security-Policy`, `X-Frame-Options`,
   `Strict-Transport-Security`, `X-Content-Type-Options`,
   `Referrer-Policy`. Inspect `Set-Cookie` for `Secure`, `HttpOnly`,
   `SameSite`. Trivial implementation, always finds something.
5. **Information disclosure** (passive). Server banner in `Server` and
   `X-Powered-By`, framework versions, HTML comments containing
   `TODO` / `FIXME` / dev URLs, verbose error message detection
   (stack traces in response bodies). Pure passive — zero false-positive
   risk.

### Finding object shape

The data model for a single finding (will appear in `/spec` essentially
as-is):

```python
{
    "severity":    "HIGH",                          # CRITICAL | HIGH | MEDIUM | LOW | INFO
    "category":    "xss",                            # short slug per detection module
    "name":        "Reflected XSS",                  # human-readable name
    "url":         "http://...",                     # where the issue was found
    "payload":     "<script>alert(1)</script>",      # what was injected (null for passive checks)
    "evidence":    "payload found in response",      # one-line "why we believe this"
    "poc_url":     "http://...",                     # click-to-verify URL (null for passive)
    "remediation": "Encode output with htmlspecialchars()",  # one-line fix hint
}
```

### Architectural constraints (carry to /spec)

- Every detection module: **<50 lines of Python**, one file per category.
- Localhost (`http://localhost:*`, `http://127.0.0.1:*`) and public
  HTTPS targets must both work without flag changes.
- Three output sinks (terminal / HTML / TXT) consume the same finding
  list — formatting is a presentation concern, not coupled to detection.
- Run summary always prints (`5 categories checked, N findings`) even
  on clean targets — evidence-of-work for the reflective-diary use case.

### Open questions for /prd

- Concurrency model: serial requests, threaded (per ReconKit), or async
  (`aiohttp` / `httpx`)?
- CLI surface: which flags ship in v1 (`--only`, `--severity-min`,
  `--cookie`, `--output`)?
- Should the HTML report be self-contained (inline CSS/JS) or assume a
  sibling `style.css`? (Self-contained likely wins for screenshot and
  share-ability.)
- Failure modes: what does the run output look like if the target is
  unreachable, or if a single category errors mid-scan?
