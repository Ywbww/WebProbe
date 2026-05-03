# WebProbe v2 — Sprint 2

Authenticated-scanning expansion of the v1 black-box scanner. Same legibility
discipline (every detection module under 50 lines), same output philosophy
(severity-tagged findings + click-verifiable POC URLs), now with the post-login
surface visible.

## Idea

Take WebProbe from a "single-page, unauthenticated scanner" to an
**auth-aware web vulnerability scanner usable for FIT3047 / FIT3048 work,
hardened against <team>'s deployment as the canonical test target.**

The Sprint 1 win — running WebProbe against <team>'s CakePHP project and
catching `/cpanel`, `/.htaccess`, `/.htpasswd`, the missing csrfToken Secure
flag, and missing HSTS — proved that the deployment-layer / unauthenticated
surface is now a solved problem. Sprint 2's job is to extend the same
"caught a real thing in my own project" discipline to the application layer:
post-login pages, role-based access control, IDOR, CSRF on state-changing
POSTs, session handling.

The architectural commitments from v1 carry forward unchanged:

- One detection module per vulnerability class, each under 50 lines of Python.
- Three output sinks (terminal / HTML / TXT) consume the same finding list.
- Localhost and public HTTPS targets both work without flag changes.
- Run summary always prints, even on a clean target — evidence-of-work.
- Hand-written Python; no YAML templating, no plugin DSL.

What's new in v2 architecturally — kept deliberately small:

- **Multi-session-aware `session_factory()` returning `list[Session]`.**
  Default length 1 (single-session = v1 mental model unchanged for 5/6
  modules). Length 2 when `--idor-baseline` (cookie) or `--idor-baseline-form`
  (form-login) is provided. IDOR module is the only consumer of the
  multi-session shape; every other module reads `sessions[0]` and is
  identical to v1.
- **Self-contained testbed (`webprobe/testbed/`).** Tiny Flask app with
  deliberately-broken endpoints, runnable via `python3 -m webprobe.testbed`.
  Acts as the development feedback loop for the auth-detection modules
  (whose true-positive rate against a hardened target is near zero) and as
  a "did my install work" sanity check for cohort users.
- **Scan Coverage block.** First-class output section (above FINDINGS) that
  proves the scanner exercised the right pages with the right session(s).
  Makes the "provable silence" half of the win condition pinnable —
  finding-or-no-finding, the post-login surface is no longer a blind spot.

## Who It's For

**Primary user: the author**, in the same two contexts as v1, now with a
third:

1. **Authenticated audits of the FIT3047 CakePHP project (<iteration 2>).**
   The marquee Sprint 2 use case. Run as a Coach role against
   `https://<deployment-url>/`, with a second Coach
   account passed via `--idor-baseline-form` for cross-account differential
   IDOR detection. Catch role-based access-control issues, IDOR, CSRF gaps,
   session-handling problems before a tutor/marker (or another team's
   pen-test exercise) finds them.
2. **CTF reconnaissance on HackTheBox / TryHackMe targets** — same as v1.
   Auth modules become useful when a CTF box hands you a low-priv credential
   and you want to enumerate horizontal/vertical privilege escalation paths
   automatically.
3. **(Sprint 2 direction, not commitment) cohort-installable tooling.**
   `pip install` shape via `pyproject.toml` + `console_scripts`, README
   quality sufficient that a Coach-role student on a different FIT3047
   team could clone, install, and scan their own login page in under 10
   minutes. Sprint 2 ships the *shape* that makes cohort adoption possible;
   actual cohort adoption is a Sprint 3 outcome (and possibly Sprint 4+).

**Secondary use:** sharing reports with FIT3047 teammates is unchanged from
v1, plus a new flow — the SCAN COVERAGE block is itself shareable evidence
("here's what I tested and how, here's what I found") for FIT3048 reflective
diary entries and team standups.

**Not for** (unchanged from v1, with one addition):

- Professional pentesting.
- Automated CI scanning of third-party sites.
- Anything requiring the breadth of a commercial scanner.
- **NEW:** running `brute_force` against shared environments without
  explicit ownership assertion. The `--include-brute-force` flag requires
  partnering `--i-own-this-target` — a typed sentence asserting the user
  owns / has authorized testing of the target. brute_force is testbed-
  default; opt-in for real targets is gated behind two flags by design.

## Inspiration & References

Sprint 1 references carry forward unchanged:

- **[Wapiti](https://github.com/wapiti-scanner/wapiti)** — scope and shape.
- **[DalFox](https://github.com/hahwul/dalfox)** — output philosophy
  (click-verifiable POC URLs, single-class deep over multi-class shallow).
- **[Nuclei](https://github.com/projectdiscovery/nuclei)** — terminal
  aesthetic and modular shape (one module per vuln class).

New v2 references — adopted for specific design levers, *not* wholesale:

- **[OWASP ZAP](https://www.zaproxy.org/)** — *form-login auto-discovery
  pattern.* ZAP's "manual auth setup" UI parses the login form, identifies
  username/password fields by `<input>` shape, preserves hidden fields
  (CSRF tokens). WebProbe v2 steals the auto-discovery heuristic for
  `--auth-form` (find `<form>`, identify `input[type=password]` as password,
  identify the preceding `input[type=email|text]` as username, preserve
  all `<input type=hidden>` so CakePHP's `_csrfToken` and Django/Rails/
  Laravel CSRF token fields survive the POST). What WebProbe doesn't take:
  ZAP's session-management framework, scripting, GUI complexity. Override
  flags (`--auth-user-field` / `--auth-pass-field`) ship if heuristic
  discovery hits a non-idiomatic form during build; otherwise they wait
  for Sprint 3.
- **[Burp Suite Authenticator extension](https://portswigger.net/bappstore)**
  — *the multi-session pattern.* Burp's professional-grade IDOR detection
  uses two authenticated sessions to compare what each role can see.
  WebProbe v2 takes the *idea* (cross-account differential as the only
  way to do IDOR detection without false-positive paths through generic
  error pages and 404 templates) without the GUI complexity. The
  list-always `session_factory()` shape is WebProbe-specific; Burp's
  contract is more elaborate.

### Aesthetic direction (unchanged from v1)

CTF tooling energy softened by Mandopop calm. Dark background, muted greys
for status lines, bright color reserved for real findings only.

Severity palette (terminal, unchanged from v1):
- `RED` — CRITICAL / HIGH
- `YELLOW` — MEDIUM
- `CYAN` — LOW
- `WHITE` — INFO
- `GREY` — clean / passed checks

HTML palette (white-background, unchanged from v1 PRD).

The SCAN COVERAGE block is rendered in WHITE/GREY (informational, not alarmist)
with `[+]` (green-leaning) for passed checks and `[-]` (red-leaning) for
failed checks — visual continuity with the v1 marker convention.

## Goals

**Primary learning goal.** Understand authenticated web vulnerability
detection at the implementation level. Sprint 1 covered the
unauthenticated-payload-and-differential class (XSS, SQLi). Sprint 2 covers
the *state-aware* detection class — how do you scan a system whose behavior
depends on *who is logged in*? The design questions are different:

- How do you preserve session state across modules without making every
  module responsible for cookie handling?
- How do you detect IDOR without false positives? (Answer that emerged from
  /scope: cross-account differential, not single-session response-shape
  diffing.)
- How do you produce evidence that the scanner *actually* authenticated and
  saw the post-login surface, distinct from "scanner ran and found nothing"?
- How do you build a useful detector for vulnerabilities whose default
  state in a modern framework is "absent"? (CakePHP/Django/Rails apps using
  the framework's CSRF/access-control defaults will produce zero findings —
  the testbed answers the "is the module broken or is the target secure?"
  question.)

**Win condition (Endpoint B).** Run WebProbe v2 against the deployed
<team> FIT3047 <iteration 2> build at
`https://<deployment-url>/` while logged in as a
Coach role (with a second Coach account passed via `--idor-baseline-form`
for IDOR), and produce *either*:

- A finding from a page that is only reachable post-login — at least one
  of: an access-control issue (Coach reaches `/admin/*`), an IDOR
  (Coach A reaches `/coach/patients/{id}` owned by Coach B), or a
  session-management issue (cookie reusable after logout, or no rotation
  on login). **OR**
- A clean SCAN COVERAGE block proving the auth pipeline exercised the
  post-login surface — explicit "Login confirmed" lines, dual-session
  validation, N URLs probed across both sessions, modules fired count,
  no module errors. Silence with positive evidence.

The win is "v2 saw the post-login world and made a clear statement about
it" — finding-or-no-finding, the post-login surface is no longer a blind
spot. This dual-shape is deliberate: a halfway-secure FIT3047 <iteration 2>
should produce silence, but the silence must be *provable* (the scanner
authenticated, exercised the right pages, and reports cleanly), not
*ambiguous* (the scanner failed to authenticate and silently ran 0 useful
checks against an unauthenticated guest surface).

**Secondary goals.**

- Preserve the v1 50-line module discipline. Every new detection module
  (`access_control`, `idor`, `csrf`, `error_leakage`, `session`,
  `brute_force`) under 50 lines on first build attempt; helper extraction
  to `_<name>_helpers.py` if not.
- Ship the testbed (`webprobe/testbed/`) as a permanent acceptance harness.
  Every future module gets validated against testbed-known-vulnerable
  endpoints before shipping.
- Make the "provable silence" half of the win condition first-class through
  the SCAN COVERAGE output block. Not a secondary log line; a structural
  output section above FINDINGS.
- Keep the cohort-canonical *direction* alive without over-committing the
  Sprint 2 *outcome*. `pyproject.toml` + console_scripts means
  `pip install webprobe`; README updated with the two-session auth example
  and the "first-run on your own team's app" walkthrough; Sprint 3 picks
  up active cohort distribution.

## What "Done" Looks Like

Sprint 2 has **two endpoints** — separated to decouple engineering completion
from the externally-gated win validation.

### Endpoint A — Engineering complete

All P0 items shipped, all checkpoints passed, testbed validates each
detection module fires on a known-vulnerable target. Concretely:

- `pip install -e .` succeeds; `webprobe --help` runs from any directory.
- `python3 -m webprobe.testbed` starts the testbed on `localhost:9999`.
  Running `webprobe http://localhost:9999 --auth-form
  http://localhost:9999/login --auth-user any --auth-pass any
  --idor-baseline-form http://localhost:9999/login --idor-baseline-user
  any2 --idor-baseline-pass any2` produces non-zero findings from each of:
  `access_control`, `idor`, `csrf`, `error_leakage`, `session`. (Plus
  `brute_force` against `/login-locked` when both `--include-brute-force`
  and `--i-own-this-target` are passed.)
- Manual `wc -l webprobe/modules/*.py` audit: every module ≤ 50 lines.
- Three demo HTML reports rendered (default grouping, `--fit3048` grouping,
  testbed run) and manually verified in Firefox + Chrome via `file://`.
- README updated with the v2 auth example, the testbed walkthrough, and
  the multi-session IDOR explanation.
- `/reflect` runs and the engineering-side diary entry is written.
- **Optional `v2.0.0-rc.1` GitHub tag** at A — marks "code complete,
  validation pending" for any cohort user who clones the repo between A
  and B. Optional because solo workflow doesn't strictly need it.

### Endpoint B — Win pinned (external gate, with max-gap fallback)

WebProbe v2 ran against <team>'s FIT3047 **<iteration 2>** deployment with
auth, produced either a finding or a provable-silence SCAN COVERAGE block.
Concretely:

- Real audit report file in `screenshots/sprint-2/webprobe_<deployment-url>_443_<timestamp>.html`.
- `v2.0.0` GitHub release tag with notes describing what's new since v1
  (auth infrastructure, 6 new detection modules, testbed, SCAN COVERAGE),
  referencing the canonical scan output from this run.
- README's "Last verified against" line updated to name <team>'s
  <iteration 2> build identifier (commit hash, deployment date, or
  iteration number).
- A short second reflective-diary entry for the win itself, separate from
  the engineering-side entry at Endpoint A.

**Max-gap fallback:** if Endpoint B has not triggered within ~2 weeks of
Endpoint A (waiting on <team> <iteration 2> deployment), run validation
against (i) the testbed (mandatory baseline — proves modules fire) and
(ii) any available secondary target — a personal throwaway dev deployment,
a juice-shop instance, or the FIT3047 <iteration 1> archive. Document Team
157 <iteration 2> readiness as the explicit constraint, tag `v2.0.0`,
declare the sprint provisionally won. Re-run against <iteration 2> when it
deploys and add an addendum scan to the report. The fallback exists to
prevent indefinite drift; the priority order remains real <iteration 2>
first, fallback only if blocked.

### The acceptance moment — concrete terminal output

The image of the Endpoint B success run, sufficient detail that this is
the literal acceptance test for the output-renderer items:

```
$ webprobe https://<deployment-url>/ \
    --auth-form https://<deployment-url>/users/login \
    --auth-user coach_a@test.com \
    --idor-baseline-form https://<deployment-url>/users/login \
    --idor-baseline-user coach_b@test.com \
    --use-sitemap --fit3048
[Password for coach_a@test.com]:
[Password for coach_b@test.com]:

WebProbe v2.0
Target:        https://<deployment-url>/
Auth:          form-login (2 sessions: coach_a, coach_b)
Modules:       [headers, info-disclosure, paths, sqli, xss,
               access_control, idor, csrf, error_leakage, session]
Profile:       --fit3048
─────────────────────────────────────────────

[*] Logging in as coach_a... [+] Login confirmed
[*] Logging in as coach_b... [+] Login confirmed
[*] Discovering URLs from sitemap.xml... [+] 8 paths found
[*] Running access_control with sessions: [coach_a]
[HIGH] Coach can reach /admin/messages
     URL:      .../admin/messages
     Evidence: HTTP 200 with admin-shaped HTML
               (contains "All Messages" header)
     Probed:   as coach_a (Coach role)
     Fix:      Add admin role check in MessagesController::index()
     FIT3048:  Category 2

[*] Running idor with sessions: [coach_a, coach_b]
[HIGH] IDOR — Coach A can read Coach B's patient records
     URL:      .../coach/patients/47
     Evidence: coach_a's GET returns same body as
               coach_b's GET (sha256 match)
     Probed:   as coach_a, baseline coach_b owns id=47
     Fix:      Add ownership check in PatientsController::view()
     FIT3048:  Category 2

═══════════════ SCAN COVERAGE ═══════════════
Mode:           Authenticated, dual-session
Sessions:       2 (coach_a, coach_b)
URLs probed:    47 (8 sitemap, 39 dynamic)
Modules fired:  10/10 (no errors)
Login probe:    [+] Both logins confirmed at 02:31:14
Session check:  [+] /coach/dashboard 200 with both sessions
Logout test:    [-] Post-logout cookie still accepted (HIGH)
Duration:       14.3s

═══════════════ FINDINGS ═══════════════
[HIGH × 3] [MEDIUM × 6] [LOW × 4] [INFO × 1]
...

Target:    https://<deployment-url>/
Modules:   10 scheduled, 10 completed, 0 errored
Findings:  14 (0 CRIT, 3 HIGH, 6 MED, 4 LOW, 1 INFO)
Report:    webprobe_<deployment-url>_443_<ts>.html
Duration:  14.3s
```

Five things this acceptance image pins (carry to /prd and /spec):

1. **Per-finding auth attribution.** "Probed: as coach_a, baseline coach_b
   owns id=47" — `Finding` dataclass needs an `auth_context` field.
2. **SCAN COVERAGE as a structural section.** Above FINDINGS, not embedded
   in summary. Either a new output module (`output/coverage.py`) or
   extension to `terminal.py` and `html.py` — `/spec` decides.
3. **`idor-baseline-missing` INFO finding** sits beside HIGH findings in
   the same FINDINGS block when `--idor-baseline*` is not provided. The
   "no false confidence" pattern from v1 carried into v2's IDOR contract.
4. **Heavy command line.** 5+ flags for the win-shape invocation. README
   needs a "common invocation patterns" section showing this exact line
   verbatim, with copy-paste-friendly placeholders.
5. **Two-tier finding architecture.** Coverage-level facts ("we tested
   logout") vs finding-level alerts ("logout was broken"). The "Logout
   test: [-] Post-logout cookie still accepted (HIGH)" line in COVERAGE
   is the *evidence-of-test* line; the corresponding HIGH finding for
   the broken logout sits in FINDINGS. `/spec` decides whether session
   findings duplicate or only render in COVERAGE with a back-reference.

## What's Explicitly Cut

Sprint 2 ambition entered as 30 candidate items across 6 groups (see
`scope-input.md`). Cut to 14 items (10 P0 + 4 P1 + 1 stretch) on the
basis of the win-condition anchor: every kept item directly serves the
authenticated-scanning win or its packaging, every cut item serves a
different goal that belongs in Sprint 3.

### Sprint 2 Final Shape

**P0 — must-have (~10-12 hrs):**
1. `--cookie` flag (single primary cookie session)
2. `--auth-form` with auto-discovery of username/password fields
3. `BaseModule` adapted to multi-session (`session_factory()` returns
   `list[Session]`, default len 1)
4. `access_control` module (Coach hits `/admin/*`, observe status)
5. `idor` module (cross-account differential, INFO when baseline absent)
6. `csrf` module (POST without token → expect 403)
8. `error_leakage` module (user-enumeration via login-response diff)
3.5. **`webprobe/testbed/`** — Flask app with deliberately-broken endpoints
3.6. **SCAN COVERAGE output block** — first-class output section
23. `pyproject.toml` + `console_scripts` (`pip install` → `webprobe` cmd)

**P1 — keep if room (~3-4 hrs):**
7. `brute_force` module (testbed-default; double-flag opt-in for real
   targets via `--include-brute-force` + `--i-own-this-target`)
9. `session` module (post-logout cookie replay + session fixation)
18. JSON output sink
26. `--url-list <file>` (explicit URL list)
27. `--use-sitemap` (parse sitemap.xml)
28. `--use-robots` (parse robots.txt Disallow paths)

**Stretch — only if Sprint 2 finishes early (~30 min):**
- `--export-md` mini: fixed markdown table (TC ID blank, Test Step =
  finding name, Expected = fix, Actual / Status filled). NO natural-
  language matching, NO column-mapping learning. Bridge artifact toward
  Sprint 3's full template system without shipping the engineering.

**Total realistic:** 14 items, ~13-16 hrs build (was 12-14 in the first
cut; +1.5 hrs for testbed, +0.5 hrs for SCAN COVERAGE, +30 min for
`--auth-form` field auto-discovery).

### Cut to Sprint 3 (with reasons)

Items 10-17 — **general security detection expansion** (`os_command_injection`,
HTTP methods abuse, default credentials, CORS, HTTP→HTTPS redirect, SRI
missing, open redirect, HTML-comment sensitive info). Cut: valuable, but
none auth-related. Sprint 2's win is the auth surface; mixing in unauth
detection expansion dilutes both threads. All of these are natural Sprint 3
items individually under 50 lines, with no architectural prerequisites.

Items 19-22 — **full template system** (NL matching, column mapping,
.webprobe-template-map.json learning, diff mode). Cut: largest engineering
work in the scope-input.md list, not on the auth-win critical path, and
the `--export-md` stretch in Sprint 2 already ships a mini-shape that
Sprint 3 can grow from. Defending the template system as Sprint 3 work
keeps the "every team has a different report format → tool needs templates
to be cohort-canonical" thread alive without pre-committing the
engineering during Sprint 2.

Item 24 — **README revision** beyond what's needed for v2 features. Cut:
v2 README updates are scoped to "the new auth example, the testbed
walkthrough, and the multi-session IDOR explanation." Anything beyond
that (full tutorial rewrite, contribution docs, demo GIF, branding
polish) is Sprint 3 cohort-distribution work.

Item 25 — **pytest suite.** Cut from Sprint 2: the testbed (item 3.5)
serves as the manual integration-test harness for v2; pytest-driven
automation against the testbed is Sprint 3 work. Could be promoted from
P1 if Sprint 2 has unexpected slack, but not in the baseline plan.

### Sprint 1 cuts that *are now in scope* — and why the operational risk is contained

- **Authenticated probing.** Cut from v1 /scope on operational-risk grounds
  ("aggressive login probing can lock real users out of shared
  environments"). In Sprint 2: the deployment is Trump's own team's
  (<team>), the `brute_force` module is testbed-default with a
  double-flag opt-in for real targets, and the IDOR/access-control/CSRF
  modules don't carry lockout risk in the first place (they probe
  authorization, not authentication credentials). The original
  operational-risk concern is preserved in shape, not relaxed.

### Permanently rejected

- **Full HTML-link-following spider/crawler.** From scope-input.md, kept
  rejected. Replaceable by Burp Suite Spider, would dominate the entire
  sprint, breaks "fast scanner" positioning. Multi-URL discovery in
  Sprint 2 is `--url-list` + `--use-sitemap` + `--use-robots` (items 26-28);
  no recursive HTML link following.

The cut discipline encoded here, same as v1: every removal carries a named
reason (time, win-condition relevance, operational risk, generalization).

## Loose Implementation Notes

Non-binding early thinking. Final decisions live in `/sprint-2/spec.md`.

### Multi-session contract — the unified shape

Single `BaseModule` contract, `session_factory()` always returns
`list[Session]`. Default length 1 (single-session = v1's mental model
unchanged for 5/6 modules). Length 2 when `--idor-baseline` (cookie) or
`--idor-baseline-form` (form-login) is provided.

Module body shape (5/6 modules, identical to v1 mental model):

```python
class AccessControlModule(BaseModule):
    def run(self, target, session_factory, report_finding):
        s = session_factory()[0]   # <-- one line, identical to v1
        # ... single-session detection logic, ≤ 50 lines total
```

IDOR module (the only multi-session consumer):

```python
class IdorModule(BaseModule):
    def run(self, target, session_factory, report_finding):
        sessions = session_factory()
        if len(sessions) < 2:
            report_finding(Finding(
                severity="INFO",
                name="idor-baseline-missing",
                evidence="IDOR detection requires --idor-baseline or "
                         "--idor-baseline-form for cross-account "
                         "differential probing; running status-code "
                         "heuristic on sessions[0] only",
            ))
            # falls back to status-code heuristic on sessions[0]
            return
        s_a, s_b = sessions[0], sessions[1]
        # cross-account differential: probe each candidate URL as both
        # sessions, flag if A's GET returns same body as B's GET on
        # B-owned resources (sha256 match) — ≤ 50 lines total
```

Why list-always rather than `Optional[Session]` or `Union[Session, list]`:
modules don't need to branch on the contract shape. `sessions[0]` is one
line and works in both single- and multi-session mode. The 50-line budget
is preserved for every module; IDOR's extra branching is its own
complexity, not exported to others.

### Auth flag matrix (4 flags, mapped to a 2×2 cookie/form × primary/baseline grid)

```
--cookie SESSION                   # primary, cookie-based
--idor-baseline COOKIE             # baseline, cookie-based
--auth-form URL                    # primary, form-based
--auth-user EMAIL                  # username for --auth-form
--auth-pass PASS                   # password (or env, or getpass prompt)
--idor-baseline-form URL           # baseline, form-based
--idor-baseline-user EMAIL         # username for --idor-baseline-form
--idor-baseline-pass PASS          # password (or env, or getpass prompt)
```

- `--cookie` and `--auth-form` are mutually exclusive (pick a primary).
- `--idor-baseline` and `--idor-baseline-form` are mutually exclusive
  (pick a baseline shape).
- Password resolution order: explicit `--*-pass` flag → env var
  (`WEBPROBE_AUTH_PASS`, `WEBPROBE_IDOR_BASELINE_PASS`) → `getpass.getpass()`
  interactive prompt. Argv never carries plaintext passwords in the
  intended workflow.
- Engine validates flag combinations and exits with a clear error message
  on conflicts.

### `--auth-form` field auto-discovery

Heuristic (reuses v1's form-discovery module):

1. GET `--auth-form` URL.
2. Find `<form>` elements. If multiple, pick the one containing
   `<input type="password">`.
3. Identify password field as `input[type="password"]` (first one wins).
4. Identify username field as the `input[type="email"|"text"]` immediately
   preceding the password field, OR the only non-password text input in
   the same form, OR fall back to fields named `email`, `username`,
   `login`, `user` in that priority order.
5. POST the form's `action` (or fall back to `--auth-form` URL if action
   empty) with `<username-field-name>=<--auth-user>` and
   `<password-field-name>=<--auth-pass>`, plus all `<input type="hidden">`
   preserved (handles CakePHP `_csrfToken`, Django `csrfmiddlewaretoken`,
   Rails `authenticity_token`, Laravel `_token` automatically).
6. Validate login: redirect away from the login URL = success. Same URL
   with the form re-rendered = failure. Fail loud with explicit error
   message and `--auth-user-field` / `--auth-pass-field` override hint.

Override flags (`--auth-user-field NAME`, `--auth-pass-field NAME`) ship
in Sprint 2 only if the auto-discovery heuristic hits a non-idiomatic form
during build. Otherwise deferred to Sprint 3 with a documented "if your
form doesn't work, file an issue / use --cookie" workaround.

### Testbed (`webprobe/testbed/`)

Standalone Flask app, runnable via `python3 -m webprobe.testbed` (binds
to `localhost:9999`). Endpoints:

- `GET /idor/{id}` — returns user data, no ownership check
- `GET /admin/` — returns admin content, no auth check
- `POST /csrf-broken` — accepts POST without CSRF token
- `POST /login` — accepts unlimited attempts (no lockout)
- `POST /login-locked` — locks account after 5 attempts (validates
  the "should detect lockout" finding from `brute_force`)
- `GET /reflect-xss?q=` — reflects query param unescaped (sanity check
  for v1 `xss` module against a known-vulnerable target)

Acceptance: every Sprint 2 detection module fires at least one finding
when run against the testbed. Becomes a permanent acceptance harness for
all future detection modules.

### SCAN COVERAGE block — output structure

New structural output section, rendered above FINDINGS. Lines:

- `Mode:` — auth shape (Unauthenticated / Authenticated, single-session /
  Authenticated, dual-session)
- `Sessions:` — count + named identifiers (e.g. `2 (coach_a, coach_b)`)
- `URLs probed:` — count + breakdown by source (sitemap / robots / url-list /
  dynamic)
- `Modules fired:` — `N/total (no errors)` or `N/total (M errors — see
  MODULES WITH ERRORS)`
- `Login probe:` — `[+] Login confirmed at HH:MM:SS` per session, or
  `[-] Login failed for <user>` (in which case the scan should have
  already exited)
- `Session check:` — `[+] <validation-url> 200 with <session-name>`
  per session, validates session is actually carrying auth state
- `Logout test:` — only present when `session` module ran. `[+] Cookie
  rejected after logout` or `[-] Post-logout cookie still accepted (HIGH)`
- `Duration:` — total scan time

Two-tier finding architecture: the COVERAGE block carries facts-about-the-scan
(we tested logout, here's the result), the FINDINGS block carries
findings-as-alerts (broken logout is HIGH). `/spec` decides whether
session/auth findings duplicate into FINDINGS or only render in COVERAGE
with a back-reference.

### `Finding` dataclass extensions for v2

New optional fields (v1 fields all preserved):

```python
{
    # ... v1 fields unchanged ...
    "auth_context": "as coach_a (Coach role)",          # NEW: per-finding auth attribution
    "baseline_context": "baseline coach_b owns id=47",  # NEW: only set on cross-account findings
}
```

`auth_context` is `None` for unauthenticated/passive findings (v1 modules
keep producing v1-shape findings). `baseline_context` is `None` except on
IDOR module's cross-account findings.

### Concurrency

Inherited from v1 — `ThreadPoolExecutor(max_workers=20)` for `paths`
module only. Auth-detection modules run serially; the per-request work
is small (auth-detection modules issue 1-10 requests typically), and
threading per-module would complicate session sharing across modules
without measurable speedup on a 47-URL scan.

### Open questions for /sprint-2/prd

- **CLI surface for combined unauth-and-auth scans.** When `--auth-form` is
  set, do unauth modules (headers, info-disclosure, paths, sqli, xss)
  still run as unauthenticated GETs? Run twice (unauth + auth)? Run only
  authenticated? Default likely: run once with auth attached if available,
  flag for user override later.
- **Module-fire ordering with auth.** Login should land first (so failure
  exits before any module runs). Then which auth module first? Probably
  `access_control` (cheapest, fastest, highest find-rate on misconfigured
  apps) → `csrf` → `idor` → `error_leakage` → `session` → `brute_force`
  (last because lockout side effects).
- **`--use-sitemap` + `--use-robots` interaction with auth.** The sitemap
  is fetched unauthenticated; the URLs in it are then probed
  authenticated. `robots.txt` Disallow paths should be probed as
  authenticated (the interesting case is "is this disallowed path actually
  protected?").
- **JSON output schema.** Mirror the `Finding` dataclass field-for-field
  with a top-level `scan_coverage` block, or wrap in a more general
  envelope (`{"version": "2.0", "scan": {...}, "findings": [...]}`)?
  Versioning matters because Sprint 3's template system will consume JSON.
- **Banner / `--help` text shape** — same as v1, defer to /build with
  documented defaults at /spec.

## Amendment 1 — Semver progression (added during /checklist Phase 1 Q4)

**Original /scope:** `v2.0.0-rc.1` at Endpoint A, `v2.0.0` at Endpoint B
(assumed Endpoint B was the validation gate).

**/checklist Q4 selected (p) shape:** /build phase ends deterministically
at engineering completion, decoupled from <iteration 2> deployment. Under
(p), testbed-acceptance pass IS the stability gate; there is no separate
"release candidate" stage to gate.

**Amended progression:**

- `v2.0.0` at Endpoint A (testbed-validated, engineering complete)
- `v2.0.1` patch path for any post-release <iteration 2> audit findings
- `v2.0.1-validated-fallback` if max-gap fallback fires (per Endpoint B
  playbook — testbed + secondary target like juice-shop or FIT3047
  <iteration 1> archive when <iteration 2> unavailable within ~2 weeks of
  Endpoint A)

Original /scope rc.1 → final language is superseded by this amendment.
/reflect should validate the amendment cleanly survived /build phase.

**Why amend rather than drift:** /scope wasn't wrong — the rc.1 → final
two-tag progression was internally consistent under the (q) shape /scope
assumed. /checklist Q4 explicitly chose (p) (decoupled engineering
completion from external validation), which broke rc.1's referent
(release-candidate-pending-validation). Documenting the amendment at
scope.md tail, parallel to /spec's 21 loop-backs at spec.md tail,
prevents future-Trump from reading silent contradictions between
/scope (rc.1 progression) and git history (v2.0.0 direct).
