# WebProbe v2 — Sprint 2 Product Requirements

Authenticated-scanning expansion of the v1 black-box scanner. This PRD
extends `docs/sprint-2/scope.md` into formalized user stories, acceptance
criteria, and locked invariants that `/spec` and `/checklist` will
consume.

The PRD's 7 epics align to the `--help` flag taxonomy plus a cross-cutting
contract epic, on the principle that every epic must be an independently
closeable unit:

```
Epic 1  Authentication & Session Setup
Epic 2  Discovery
Epic 3  Output
Epic 4  Filtering
Epic 5  Risk Gates
Epic 6  Module Contract           (cross-cutting framework)
Epic 7  New Detection Modules     (six parallel stories)
```

## Problem Statement

WebProbe v1 ships a working unauthenticated scanner that caught real
exposures (`/cpanel`, `/.htaccess`, `/.htpasswd`, missing csrfToken
Secure flag, missing HSTS) in <team>'s FIT3047 deployment. v2's job
is to extend the same "caught a real thing in my own project"
discipline to the application layer: post-login pages, role-based
access control, IDOR, CSRF on state-changing POSTs, session handling,
and brute-force defenses.

The scanner must produce *either* a finding from a post-login page *or*
a clean SCAN COVERAGE block proving the auth pipeline exercised the
post-login surface. Silence is acceptable when it's *provable* silence;
silence is not acceptable when it's ambiguous "scanner ran but auth
may not have worked." Distinguishing those two states is the central
v2 design problem.

## User Stories

### Epic 1 — Authentication & Session Setup

#### Story 1.1 — Form-login auto-discovery via `--auth-form`

> As Trump auditing FIT3047 with one Coach account, I want to log in by
> passing `--auth-form <url>` plus credentials, so I don't have to
> manually identify form fields or hand-craft the POST body.

Acceptance criteria:
- [ ] `webprobe <target> --auth-form <login-url> --auth-user <user>` GETs
  the login URL, finds the `<form>` containing `<input type="password">`,
  identifies fields per the heuristic below, POSTs with all
  `<input type="hidden">` preserved (CakePHP `_csrfToken`, Django
  `csrfmiddlewaretoken`, Rails `authenticity_token`, Laravel `_token`),
  and validates login.
- [ ] Field heuristic priority: `input[type=email|text]` immediately
  preceding the password input, then named `email` / `username` /
  `login` / `user` (priority order).
- [ ] Login validation rule: redirect away from `--auth-form` URL =
  success; same URL with form re-rendered = failure.
- [ ] Login success prints `[*] Logging in as <user>... [+] Login confirmed`.
- [ ] Login failure prints `[-] Login failed for <user>: form re-rendered
  at <url>` and exits with non-zero status before any module fires.
- [ ] Multiple `<form>` elements at login URL: pick the one containing
  `<input type="password">`. None match → fail loud "no password field
  found in any form at <url>".
- [ ] POST destination: `<form action>` if non-empty, fallback to
  `--auth-form` URL.
- [ ] `--auth-form` URL returns 401/403 (already gated): fail loud
  "login URL requires existing authentication; pass --cookie instead".

**Multi-step login (1.1.E1 lock):** Auto-discovery is single-page only.
When discovery sees an email-page → submit → password-page sequence
(no `<input type="password">` on first page, form action redirects to
new page that has one), webprobe fails loud:

```
ERROR: Multi-step login flow detected at <url>.
webprobe's --auth-form is single-page only.
Use --cookie '<session-string>' from a manual login instead.
```

Documented in `--help` and README. SSO redirect chains, MFA challenges,
and same-origin tracking are explicit Sprint 4+ scope.

**Override flags (1.1.E2 lock):** `--auth-user-field` and
`--auth-pass-field` are deferred until the auto-discovery field-name
heuristic is validated against ≥3 real testbeds. If a non-idiomatic form
is observed during `/build`, document the case in process notes and
re-evaluate in Sprint 3 `/scope`.

#### Story 1.2 — Cookie-based session via `--cookie`

> As Trump scanning a CTF target where I have a session cookie from
> manual interaction, I want to pass `--cookie 'sessionid=abc123'` and
> have all auth-required modules use that session, so I don't
> re-authenticate against rate-limiting external systems.

Acceptance criteria:
- [ ] `webprobe <target> --cookie 'name=value; name2=value2'` parses the
  cookie string (RFC 6265 Cookie header form), attaches it to a
  `requests.Session`, treats as primary.
- [ ] No login validation step (caller's responsibility); auth-setup
  phase prints `[*] Cookie session attached`.
- [ ] Cookie attached to every `auth_required` module's request and to
  `follow`-with-`--scan-both` modules' authed pass.
- [ ] `--cookie` and `--auth-form` mutually exclusive: passing both →
  fail loud "pick one primary auth method".

#### Story 1.3 — Multi-session contract

> As Trump testing IDOR, I want a second session (Coach B baseline)
> via `--idor-baseline` or `--idor-baseline-form`, so the `idor` module
> can do cross-account differential probing.

Acceptance criteria:
- [ ] `--idor-baseline <cookie-string>` adds a second cookie session.
- [ ] `--idor-baseline-form <url>` + `--idor-baseline-user` +
  `--idor-baseline-pass` does a second form-login (same heuristic as 1.1).
- [ ] `session_factory()` returns `list[Session]` with `len == 2` when
  any baseline flag is set, `len == 1` otherwise.
- [ ] `--idor-baseline` and `--idor-baseline-form` mutually exclusive.
- [ ] Primary and baseline can mix shapes: `(cookie, cookie)`,
  `(cookie, form)`, `(form, cookie)`, `(form, form)` all valid.
- [ ] Baseline login failure: scan exits before any module fires (parity
  with primary login failure).
- [ ] COVERAGE block consolidated line: `Login probe: [+] Both logins
  confirmed at HH:MM:SS` (single line, not per-session lines).

**Same-user silent IDOR false-negative (1.3.E1 lock):** After both logins
complete, the engine compares named-session cookies between
`sessions[0]` and `sessions[1]`. Cookie names checked: `PHPSESSID`,
`laravel_session`, `_session_id`, `connect.sid`, `JSESSIONID`,
`ci_session`, `sessionid`. If any same-named cookie has identical value
across both sessions → emit INFO finding:

```
[INFO] Primary and baseline sessions share session-cookie value.
       This usually means both --auth-form and --idor-baseline-form
       resolved to the same user account. IDOR cross-account checks
       may produce false negatives. Verify account separation manually.
```

Do not abort. The `/me`-shape endpoint probe is a Sprint 3 candidate
for higher-confidence detection.

#### Story 1.4 — Throwaway sub-session for `session` module

> As Trump verifying logout correctness, I want the `session` module to
> run its destructive post-logout cookie-replay test against a disposable
> third session, so my primary Coach A session stays intact for any
> module that fires after `session`.

Acceptance criteria:
- [ ] `session` module obtains an ephemeral session via fresh form-login
  (mechanism = `/spec`'s call: `session_factory(ephemeral=True)`,
  separate `ephemeral_login()` helper, or vanilla second `login_form()`
  invocation).
- [ ] Module flow: ephemeral login → GET protected URL `<X>` → POST
  logout endpoint → GET `<X>` again → flag HIGH if second GET still
  returns authed-shape content.
- [ ] Primary `sessions[0]` and baseline `sessions[1]` untouched.
- [ ] COVERAGE adds: `Logout test: [+] Cookie rejected after logout` or
  `[-] Post-logout cookie still accepted (HIGH)`.
- [ ] Cost: +1 login HTTP request (acceptance image's `URLs probed`
  unchanged — sub-session login isn't a *URL probed*, it's an auth-setup
  request; total HTTP request count grows by ~3 for setup+logout+verify).

**`--cookie` mode (1.4.E1 lock):** When `session` module is enabled
(default) AND auth method is `--cookie` AND no `--auth-form` provided,
session module skips its detection logic and emits:

```
[INFO] session module skipped: post-logout cookie-replay test
       requires --auth-form to create an ephemeral sub-session
       (--cookie cannot create disposable secondary sessions
       without re-authentication). Pass --auth-form to enable, or
       accept that logout-correctness is not tested in this scan.
```

Auto-excluding `session` from the default module set is rejected (silent
decision); running on the primary cookie session is rejected (destroys
primary mid-scan, violates throwaway design).

#### Story 1.5 — Password resolution chain

> As Trump invoking webprobe across manual runs, CI, and scripted
> contexts, I want password resolution to follow a consistent priority
> chain (explicit flag → env var → `getpass`), so argv never carries
> plaintext passwords in the intended workflow.

Acceptance criteria:
- [ ] Resolution priority: `--auth-pass <value>` → `WEBPROBE_AUTH_PASS`
  env var → `getpass.getpass()` interactive prompt at scan start.
- [ ] Same chain for `--idor-baseline-pass` →
  `WEBPROBE_IDOR_BASELINE_PASS` env → `getpass`.
- [ ] No flag and no env var set: scan prints `[Password for
  coach_a@test.com]:` and blocks for input.
- [ ] Non-interactive terminal AND no flag/env: fail loud "password
  resolution failed: no flag set, no env var, no TTY available; use
  --auth-pass or set WEBPROBE_AUTH_PASS".
- [ ] Plaintext password never appears in `--help` output, `--version`,
  `[*]`-line auth-setup output, or any report (HTML/TXT/JSON).

#### Story 1.6 — Per-finding `auth_context` value generation

> As Trump reading a Sprint 2 report, I want every finding to carry an
> `auth_context` string identifying which session probed for it, so I
> can trace findings back to who saw what.

Acceptance criteria:
- [ ] During the **unauth phase**, the engine emits findings with
  `auth_context = None` (v1 modules untouched, paths.py unchanged).
- [ ] During the **auth phase**, every `report_finding(...)` callback
  automatically receives an `auth_context` string injected by the
  engine — modules don't construct the string.
- [ ] User identifier resolution: `--auth-user` value, or first 8 chars
  of cookie hash if `--cookie`, or `"primary"` / `"baseline"` as
  fallback.
- [ ] For IDOR's cross-account findings: `auth_context` from primary
  session's user identifier; module additionally sets `baseline_context`
  with resource-ownership context (`baseline coach_b owns id=47`).
- [ ] Modules never reach for session metadata — engine wraps the
  callback (Story 6.4).

**Role detection (1.6.E1 lock):** Optional `--auth-role <label>` flag,
**decorative-only**:

- With `--auth-role Coach`: `[*] Logging in as coach_a (Coach)...`
- Without `--auth-role`: `[*] Logging in as coach_a...`

PRD invariant: **`--auth-role` is rendered into reports but never read
by detection logic. Modules MUST NOT branch on `auth_role` values.**
Future role-based detection is Sprint 4+ scope and will use a separate
mechanism (JWT claim parsing, `/me`-endpoint queries, framework-specific
role attributes).

This protects against drift: a developer in Sprint 3 might be tempted
to write `if auth_role == 'admin': escalate severity` — the PRD
constraint blocks that.

---

### Epic 2 — Discovery

#### Story 2.1 — Sitemap-based URL discovery via `--use-sitemap`

> As Trump auditing FIT3047, I want `--use-sitemap` to discover URLs
> from `<target>/sitemap.xml`, so I get the app's published URL surface
> without running a recursive crawler.

Acceptance criteria:
- [ ] `webprobe <target> --use-sitemap` fetches `<target>/sitemap.xml`
  **unauth_always** (no session cookies attached, regardless of
  `--auth-form` / `--cookie`).
- [ ] Successful fetch (200, valid XML): all `<loc>` URLs extracted and
  added to `Target.urls` with `source = sitemap`.
- [ ] Sitemap-index format: fetch each child sitemap once, aggregate.
  **Recursion cap: 1 level** (no deeper sitemap-of-sitemap chains).
- [ ] Off-host URLs (scheme/host differs from `<target>`): silently
  filtered (sitemap may list cross-domain assets, scanner only probes
  same-origin).
- [ ] Sitemap not present (404 / 410): silent skip, no error, no INFO
  finding.
- [ ] Sitemap auth-gated (401, or 3xx → URL matching `/login` /
  `/signin` / `/auth` / `/users/login` / `/sessions/new`): **fail loud**:
  ```
  ERROR: sitemap.xml at <url> appears auth-gated (401 / 302 →
  /users/login).
  Options:
    --use-sitemap-authed   fetch sitemap inside the authenticated session
    --no-use-sitemap       skip sitemap; use --url-list or rely on
                           dynamic discovery
  Aborting discovery phase.
  ```
- [ ] Malformed XML: fail loud "sitemap.xml at <url> returned invalid
  XML; use --no-use-sitemap to skip" (silent partial success on
  malformed sitemap is the "did discovery run?" trap).
- [ ] v2 only checks `<target>/sitemap.xml`; non-root paths out of scope.
- [ ] Successful discovery prints `[*] Discovering URLs from
  sitemap.xml... [+] N paths found`.

**URL cap (2.1.E1 lock):** Default cap **N=500**. Beyond cap:

```
[INFO] sitemap.xml contained 1,247 URLs; capped at 500 for scan-time
       bounds. 342 URLs from /products/* and 405 URLs from /blog/*
       were truncated. Sprint 3 will add --sitemap-cap <N> for
       explicit override.
```

Math under `--scan-both`: cap of 500 × 2 passes = 1000 URLs worst
case, still tractable. No-cap × 50K-URL sitemap × 6 follow modules ×
2 (`--scan-both`) = 600K requests — webprobe lockup before user
ctrl-C.

#### Story 2.2 — Sitemap behind authentication via `--use-sitemap-authed`

> As Trump scanning an app where `sitemap.xml` is gated behind login,
> I want `--use-sitemap-authed` to fetch the sitemap inside the
> authenticated session, so I don't lose discovery data on apps with
> global auth middleware.

Acceptance criteria:
- [ ] `--use-sitemap-authed` requires `--use-sitemap` to also be set;
  passing alone → fail loud "specify --use-sitemap to enable sitemap
  discovery first".
- [ ] When set, sitemap.xml fetched with primary session attached
  (after `[+] Login confirmed` but before any module fires).
- [ ] All other Story 2.1 criteria apply.
- [ ] COVERAGE line under auth: `... X sitemap (auth-fetched), ...`.
- [ ] `--use-sitemap-authed` set without auth flag → fail loud
  "--use-sitemap-authed requires --auth-form or --cookie".
- [ ] `--use-sitemap-authed` set and login fails → scan exits per
  Story 1.1; sitemap never fetched.

#### Story 2.3 — Robots-based URL discovery via `--use-robots`

> As Trump scanning a CTF target, I want `--use-robots` to extract
> Disallow paths from `robots.txt` as candidate URLs, since
> intent-to-block is intent-to-investigate.

Acceptance criteria:
- [ ] Fetches `<target>/robots.txt` unauth_always.
- [ ] Successful fetch (200): all `Disallow:` paths across all
  `User-agent:` blocks extracted, **deduplicated as union** (no
  per-bot filtering).
- [ ] Each path added with `source = robots`.
- [ ] Wildcard handling:
  - `/admin/*` → probed as `/admin/`, original recorded
  - `*.bak` → not probed, original recorded
  - `/api/v*` → probed as `/api/v`, original recorded
- [ ] Single consolidated INFO finding emitted at end of discovery
  phase listing all trimmed/skipped wildcard patterns plus upgrade
  hint: "Use --url-list with explicit paths to probe these wildcard
  intents."
- [ ] `Allow:` directives ignored.
- [ ] Empty `Disallow:` skipped (RFC: means "allow everything").
- [ ] robots.txt 404: silent skip.
- [ ] robots.txt auth-gated: fail loud per Story 2.1's pattern, with
  `--no-use-robots` as skip flag.
- [ ] Successful run: `[*] Parsing robots.txt... [+] N Disallow paths
  found, M wildcard patterns recorded`.

**Robots `Sitemap:` directive (2.2.E1 lock):** When robots parser sees
`Sitemap: <url>` directive, emit INFO at end of discovery phase. Three
branches:

```
# When sitemap not fetched:
[INFO] robots.txt at <target>/robots.txt advertised sitemap: <url>
       Pass --use-sitemap to include sitemap URLs in discovery.

# When sitemap already fetched (canonical match):
[INFO] robots.txt advertised sitemap: <target>/sitemap.xml
       (already fetched via --use-sitemap).

# When sitemap advertises non-canonical URL:
[INFO] robots.txt advertised sitemap at <url>, but --use-sitemap
       fetched <target>/sitemap.xml. Pass --sitemap-url <url> to
       fetch the advertised location instead.
       (--sitemap-url deferred to Sprint 3.)
```

#### Story 2.4 — Explicit URL list via `--url-list <file>`

> As Trump scanning a target where I have specific URLs of interest
> (manual exploration, Burp history, FIT3048 spec docs), I want
> `--url-list <file>` to read URLs from a file, so I can bypass
> discovery and probe a curated list.

Acceptance criteria:
- [ ] Reads `<path>` line-by-line.
- [ ] Lines starting with `#`: skipped (comments).
- [ ] Blank lines: skipped.
- [ ] Relative URLs (`/admin/users`): resolved against `<target>` base.
- [ ] Absolute URLs same-host: kept verbatim.
- [ ] Absolute URLs different-host: skipped with `[!] Skipping
  out-of-scope URL: <url>` warning, scan continues.
- [ ] File not found: fail loud "url-list file not found: <path>".
- [ ] File empty (or all comments/blanks): INFO finding "url-list
  <path> contained no probe-able URLs" + continue.
- [ ] Each URL added with `source = url_list`.

#### Story 2.5 — Source-tagged URL pool

> As Trump reading the COVERAGE block, I want every probed URL
> attributed to its discovery source, so I can see at a glance which
> sources contributed how many URLs and which modules respected which
> sources.

Acceptance criteria:
- [ ] `Target.urls: List[Tuple[str, Source]]` where `Source ∈ {sitemap,
  robots, url_list, dynamic, curated}`.
- [ ] Engine populates pool from all enabled discovery sources before
  module dispatch; pool is read-only after discovery phase.
- [ ] Each module receives a filtered view: `[u for u, s in target.urls
  if s in self.source_filter]`.
- [ ] Per-module `source_filter` mappings:
  - `paths` → `{curated, robots, url_list}`
  - `sqli` → `{dynamic, url_list}`
  - `xss` → `{dynamic, url_list, curated}`
  - `headers`, `info-disclosure`, `csrf`, `access_control`, `idor`,
    `error_leakage` → ALL sources
- [ ] COVERAGE breakdown: `URLs probed: 47 (8 sitemap, 5 robots-disallow,
  0 url-list, 34 dynamic, 0 curated)` (zeros included).
- [ ] COVERAGE per-module rejection: `paths.py probed 7 of 47 URLs
  (curated+robots+url-list only)`.
- [ ] Modules MUST NOT mutate `Target.urls` — read-only access; spider
  scope deferred to Sprint 4+.

**Dynamic source semantics (2.5.E1 lock):** Pre-computed at scan-start.
"Dynamic" = URLs extracted from `Target.base_response` HTML (form
actions, `<a href>` links, `<script src>` from the target's homepage)
for same-origin URLs. Pool size is fixed before module dispatch;
COVERAGE's `URLs probed: N` is a planning-time metric.

URLs found via redirects mid-scan are **not** added to the pool, but
the discovering module emits INFO:

```
[INFO] redirect target /dashboard not in URL pool;
       consider --url-list for full coverage in next scan.
```

Miss-this-scan-hint-for-next-scan pattern.

**Cross-source duplicates (2.4.E1 lock):** Dedupe by URL, keep
highest-priority source. Priority order locked verbatim:

```
url_list > robots > curated > sitemap > dynamic
```

Rationale: signal density per URL (human-curated > intent-declared >
heuristic-dictionary > bulk-published > incidental).

---

### Epic 3 — Output

#### Story 3.1 — SCAN COVERAGE block (terminal + TXT)

> As Trump reading the Sprint 2 report, I want a SCAN COVERAGE block
> that proves the scanner authenticated, exercised the right pages with
> the right sessions, and reports what was tested even when no findings
> surface, so I can distinguish "halfway-secure FIT3047 produces
> silence" from "auth pipeline failed silently."

Acceptance criteria:
- [ ] Block renders **above** the FINDINGS block, with header
  `═══════════════ SCAN COVERAGE ═══════════════`.
- [ ] Lines, in order:
  - `Mode:` — taxonomy enum, exactly four values:
    `Unauthenticated`, `Authenticated, single-session`,
    `Authenticated, dual-session`, plus any Sprint 1 carryover values.
    No `Cookie-attached` or other provenance variants — Mode is
    classification of scan shape, not auth-mechanism trace.
  - `Sessions:` — count + named identifiers, e.g.,
    `2 (coach_a, coach_b)`. With `--auth-role`:
    `2 (coach_a (Coach), coach_b (Coach))`.
  - `URLs probed:` — total + breakdown:
    `47 (8 sitemap, 5 robots-disallow, 0 url-list, 34 dynamic, 0
    curated)`. Zeros included.
  - `Modules fired:` — `N/total (no errors)` or `N/total (M errors —
    see MODULES WITH ERRORS)`.
  - `Login probe:` (auth phase only) — `[+] Both logins confirmed at
    HH:MM:SS` (dual) or `[+] Login confirmed at HH:MM:SS` (single).
  - `Session check:` (auth phase only) — `[+] / 200 with both sessions`
    (per session-check probe URL, see lock below).
  - `Logout test:` (only if `session` module ran) — `[+] Cookie rejected
    after logout` or `[-] Post-logout cookie still accepted (HIGH)`.
  - `Per-module source filter:` — one line per module that filtered
    (modules with `source_filter = ALL` skip this line).
  - `Wildcard intents:` (only if robots saw wildcards) — `5 patterns
    recorded (see INFO finding)`.
  - `Duration:` — `14.3s`.
- [ ] Marker convention preserved: `[*]` progress, `[+]` success/benign,
  `[-]` finding/failure, `[!]` warning/error. `[SEVERITY]` reserved for
  findings.
- [ ] Color: WHITE/GREY informational, GREEN-leaning `[+]`, RED-leaning
  `[-]`. No bright colors in COVERAGE.
- [ ] TXT report inherits identical layout, ANSI-stripped.
- [ ] Unauthenticated scan still renders SCAN COVERAGE — `Mode:
  Unauthenticated`, no auth-phase lines, source breakdown still present.
- [ ] Empty source case: `URLs probed: 80 (0 sitemap, 0 robots, 0
  url-list, 0 dynamic, 80 curated)`.

**Session-check probe URL (3.1.E1 lock):** Target homepage with sha256
comparison + INFO fallback when identical:

```
unauth GET <target>/ → sha256_a
session GET <target>/ with attached cookie → sha256_b
if sha256_a != sha256_b:
    print "[+] / 200 with both sessions"
else:
    print "[!] Session attachment unverified — homepage byte-identical
          with and without session"
    emit INFO finding "session_check_ambiguous"
    scan continues
```

Sprint 3 candidate: upgrade probe to "first sitemap URL if available,
else homepage" once Story 2.1 ships in production.

#### Story 3.2 — FINDINGS block (terminal + TXT) with auth_context rendering

> As Trump reading findings, I want each finding's auth attribution
> rendered inline (which session probed for it, who owned the IDOR
> resource), so I can trace findings to specific session/role context.

Acceptance criteria:
- [ ] FINDINGS block header: `═══════════════ FINDINGS ═══════════════`
  followed by count line `[HIGH × N] [MEDIUM × M] [LOW × X] [INFO × Y]`.
  Zeros rendered (`[CRITICAL × 0]` not omitted).
- [ ] Each finding renders as v1 multi-line block, with new `Probed:`
  line inserted between `Evidence:` and `Fix:`:
  ```
  [HIGH] Coach can reach /admin/messages
       URL:      .../admin/messages
       Evidence: HTTP 200 with admin-shaped HTML
                 (contains "All Messages" header)
       Probed:   as coach_a (Coach role)
       Fix:      Add admin role check in MessagesController::index()
       FIT3048:  Category 2
  ```
- [ ] `Probed:` line: only renders when `auth_context != None`. v1
  unauth findings preserve byte-for-byte v1 shape.
- [ ] IDOR cross-account findings: both `auth_context` and
  `baseline_context` populate the `Probed:`/`Baseline:` lines per
  Story 3.3 lock.
- [ ] Inline tease at moment-of-detection (Sprint 1 carryover).
- [ ] Default grouping: severity tier (CRITICAL → HIGH → MEDIUM → LOW →
  INFO), then category within severity.

#### Story 3.3 — HTML report v2

> As Trump archiving Sprint 2 audit reports for the FIT3048 reflective
> diary, I want the HTML report to render auth-context badges, IDOR
> cross-account differentials, and an OPERATIONAL_RISK chip when gated
> modules fired, so the report is screenshot-ready evidence and
> visually distinct from v1.

Acceptance criteria:
- [ ] Filename: `webprobe_<host>_<port>_<YYYYMMDD>-<HHMMSS>.html` (Sprint
  1 pattern preserved, port retained).
- [ ] Self-contained HTML — inline CSS/JS, no external assets.
- [ ] Top section: SCAN COVERAGE rendered as styled section.
- [ ] Second section: FINDINGS, grouped by severity (default) or FIT3048
  category (`--fit3048`).
- [ ] Per-finding rendering:
  - **Auth-context badge** next to finding name when `auth_context`
    set: `[as coach_a (Coach)]`. Color: WHITE/GREY informational, not
    severity-toned.
  - **IDOR dual-session text augmentation** (3.3.E1 lock) — locked
    rendering:
    ```
    [HIGH] IDOR — Coach A can read Coach B's patient records
        URL:           https://target/clients/47
        Evidence:      coach_a's GET returns same body as coach_b's
                       GET (sha256 match)
        Probed:        as coach_a (Coach role)
        Baseline:      coach_b owns id=47
        Sessions:      coach_a sha256=abc123e4 vs coach_b
                       sha256=abc123e4 (match)
        Fix:           Add ownership check in
                       PatientsController::view()
        FIT3048:       Category 2
    ```
    Constraints: sha256 truncated to 8 chars for terminal readability;
    `Sessions:` line renders ONLY when `category == 'idor' AND
    baseline_context is not None`; "match" / "differ" suffix.
  - **OPERATIONAL_RISK chip** (3.3.E2 lock) — single combined chip with
    gate flags listed:
    ```
    ⚠ OPERATIONAL_RISK: brute_force, access_control, idor, csrf
      gated by --include-brute-force --i-own-this-target
    ```
    Second line is non-negotiable — gate flag enumeration IS the audit
    trail. Auditor's first question after "this scan ran risky stuff"
    is "was it authorized" and gate-flag presence answers inline.
- [ ] Sprint 1 features preserved: copy-to-clipboard buttons (Clipboard
  API + text-selection fallback, no `execCommand`), 1200ms flash, "DO
  NOT WRAP" guard around `<a>` + `<button>` pairs.
- [ ] Manual browser test: `file://` in both Firefox and Chrome (`/build`
  Checkpoint C carryover).

#### Story 3.4 — JSON output v2 (versioned envelope)

> As Sprint 3's template system consuming Sprint 2 output, I want a
> versioned JSON envelope with stable schema and dedup applied at the
> engine layer, so I can dispatch on `.version` and trust field shapes.

Acceptance criteria:
- [ ] Top-level envelope:
  ```json
  {
    "version": "2.0",
    "tool": "webprobe",
    "scan": {
      "target": "...",
      "started_at": "2026-05-01T14:30:00+10:00",
      "completed_at": "2026-05-01T14:30:14+10:00",
      "duration_seconds": 14.3,
      "exit_code": 0,
      "modules": {"scheduled": 10, "completed": 10, "errored": 0},
      "risk_gates_asserted": [
        "i-own-this-target=<deployment-url>",
        "include-brute-force"
      ]
    },
    "scan_coverage": { ... },
    "findings": [ ... ]
  }
  ```
- [ ] **Semver rules** (locked):
  - **MAJOR** bump: field deletion, type change, semantic change.
  - **MINOR** bump: field addition (consumers MUST ignore unknown
    fields without error).
  - **PATCH** bump: enum value addition (e.g., new severity tier).
  - Sprint 3 templates check `.version | split(".") | .[0]` and fail
    loud on unknown major.
- [ ] **Field stability**: every field declared MUST appear on every
  finding. Optional fields (`auth_context`, `baseline_context`,
  `payload`, `poc_url`) present as `null` when absent — never omitted.
- [ ] **`--scan-both` deduplication**: identity =
  `(category, target_url, evidence_hash)`. Same finding emitted in both
  passes → one entry with `seen_in: ["unauth", "authed"]`. Different
  findings (e.g., headers genuinely differ between passes) → separate
  entries with single-element `seen_in`.
- [ ] **`risk_gates_asserted`** records user-typed argv form
  (case preserved). Audit-trail intent: the asserted hostname is
  verbatim what the user typed. Normalization would discard evidence.
- [ ] Output destination: default `webprobe_<host>_<port>_<ts>.json`
  next to HTML/TXT.
- [ ] `--json-out <path>`: explicit override.
- [ ] `--json-out -`: write to stdout, suppress JSON file write and
  `JSON:` line in run-end summary. HTML/TXT still written to defaults.
- [ ] Each finding JSON shape — locked v2.0 fields:
  ```json
  {
    "severity": "HIGH",
    "category": "idor",
    "name": "...",
    "url": "...",
    "payload": null,
    "evidence": "...",
    "evidence_hash": "abc123def4567890",
    "poc_url": null,
    "remediation": "...",
    "fit3048_category": 2,
    "auth_context": "as coach_a (Coach)",
    "baseline_context": "baseline coach_b owns id=47",
    "seen_in": ["authed"]
  }
  ```

**`evidence_hash` (3.4.E1 lock):** Public JSON field. Hash function
locked verbatim:

```python
evidence_hash = sha256(
    f"{category}:{target_url}:{evidence}".encode()
).hexdigest()[:16]
```

16 chars canonical (8-char truncation in terminal `Sessions:` line is
display-only). Hash function changes (algorithm, input, length) require
schema MAJOR bump.

#### Story 3.5 — Run-end summary block

> As Trump finishing a scan, I want the run-end summary to clearly
> enumerate the report files created, so I have one-line evidence of
> all outputs without inspecting the directory.

Acceptance criteria:
- [ ] Summary block renders after FINDINGS (terminal + TXT):
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
- [ ] Module counts: `scheduled` = post-filter; `completed` = ran
  without uncaught exception; `errored` = raised exception caught by
  engine.
- [ ] Finding counts: zero entries per severity print (`0 CRIT` not
  omitted) — Sprint 1 evidence-of-work pattern.
- [ ] `--json-out -` mode: `JSON:` line replaced with `JSON: <stdout>`.
- [ ] Single sink failure: line replaced with `HTML: [render failed —
  see MODULES WITH ERRORS]`, scan still produces TXT and JSON.
- [ ] Clean target (zero findings): summary still prints — evidence-of-
  work for "provable silence" half of win condition.
- [ ] `--scan-both` mode: `Modules: 10 scheduled, 10 completed (5 of 10
  ran twice via --scan-both)` for clarity.

---

### Epic 4 — Filtering

#### Story 4.1 — Module include/exclude

> As Trump scoping a scan to a specific subset of modules (quick smoke
> test, CI exclusion of slow modules), I want comma-delimited
> include/exclude flags so I can shape module dispatch without invasive
> flag combinations.

Acceptance criteria:
- [ ] `--include-modules <list>` — only listed modules scheduled.
- [ ] `--exclude-modules <list>` — listed modules skipped.
- [ ] Default: all modules scheduled subject to risk-gate defaults
  (Epic 5).
- [ ] **Mutually exclusive**: passing both → fail loud "use either
  --include-modules or --exclude-modules, not both".
- [ ] Module name validation: unknown name → fail loud with name
  suggestion if Levenshtein distance ≤ 2:
  ```
  ERROR: unknown module 'xrr'.
  Did you mean 'xss'?
  Available modules: headers, info-disclosure, paths, sqli, xss,
                     access_control, idor, csrf, error_leakage,
                     session, brute_force
  ```
- [ ] Empty list (`--include-modules ""` or `,,,`) → fail loud "module
  list cannot be empty".
- [ ] Whitespace tolerance: `"headers, sqli, xss"` parses identically
  to `headers,sqli,xss`.
- [ ] **Risk-gate interaction**: `--include-modules brute_force`
  without `--include-brute-force --i-own-this-target=<host>` → fail
  loud per Epic 5 invariants.
- [ ] Same rule for `access_control` / `idor` / `csrf`:
  `--include-modules <gated-module>` without `--i-own-this-target=<host>`
  → fail loud.
- [ ] `--exclude-modules <gated-module>` without flags: silent (no-op);
  module already excluded by default.
- [ ] COVERAGE `Modules fired: N/total` reflects post-filter counts.
- [ ] Run-end summary `Modules: N scheduled, ...` counts post-filter.

#### Story 4.2 — FIT3048 grouping via `--fit3048`

> As Trump preparing a FIT3048 reflective diary entry, I want
> `--fit3048` to render the HTML report grouped by FIT3048's 10-category
> rubric so I can paste category-by-category screenshots that map
> directly to the rubric columns.

Acceptance criteria:
- [ ] `--fit3048` reorganizes HTML FINDINGS by `fit3048_category` (1-10)
  instead of severity tier.
- [ ] **Two-level grouping**: outer = FIT3048 category, inner =
  severity tier. PRD rationale (prevents inversion in build):
  > outer=category is required by the FIT3048 reflective diary
  > copy-paste workflow; outer=severity would force users to
  > assemble per-category screenshots from multiple severity
  > sections, defeating the entire purpose of --fit3048.
- [ ] Each FIT3048 category renders even when empty — visible
  "Category 7: 0 findings" entries preserved as evidence-of-coverage.
- [ ] Every Sprint 2 finding **must** carry non-null
  `fit3048_category`. `Finding.__post_init__` invariant.
- [ ] Terminal/TXT: `--fit3048` does NOT change grouping (severity
  remains default). Flag affects HTML only.
- [ ] JSON: `--fit3048` does NOT change envelope shape. Findings array
  is order-preserving; consumers regroup via `.findings | group_by(
  .fit3048_category)`.
- [ ] When `--fit3048` set, run-end summary gains per-category count
  breakdown: `FIT3048: [Cat1: 3] [Cat2: 4] ... [Cat10: 1]`.

**FIT3048 module-level mappings (4.2.E1 lock):** Per-finding mapping;
ownership is Epic 6 (Finding dataclass). Module-level defaults:

| Module | Category | Notes |
|---|---|---|
| `access_control` | 2 | Broken Access Control |
| `idor` | 2 | Broken Access Control |
| `csrf` | 2 | Broken Access Control — forced action across auth boundary |
| `error_leakage` | multi | `username_enumeration_login` → 7, `stack_trace_leakage` → 1 |
| `session` | 7 | Identification & Authentication Failures |
| `brute_force` | 7 | Identification & Authentication Failures |
| `headers` (v1) | multi | Cat 4 + Cat 5 mappings per Sprint 1 PRD |

Each module file declares a `FIT3048_CATEGORY_MAP` dict (Epic 6, Story
6.1) mapping internal finding-type names to category numbers; engine
resolves at emit time and validates `1..10` at `__post_init__`.

**Two distinct empty-category messages (4.2.E3 lock):** Distinguishable
by reason:

```
# Empty because no findings:
[Cat 3] Cryptographic Failures
(no findings)

# Empty because module(s) excluded by filter:
[Cat 3] Cryptographic Failures
(no findings — modules covering this category were excluded by
 --include-modules / --exclude-modules)
```

Engine tracks scheduled-but-disabled-by-filter modules; for each
category, checks if any scheduled module's `FIT3048_CATEGORY_MAP`
includes that category and was filtered out. If yes → "modules
excluded"; if no → "no findings". The "modules excluded" message
renders ONLY if a module that **would** have produced findings in
this category was filtered out.

**Out of scope:** `--severity-min` is **not** in Sprint 2. Severity
filtering is a consumer-side concern (Sprint 3 template system handles
it; `jq '.findings[] | select(.severity == "HIGH")'` solves it
ad-hoc). Deferred to Sprint 3.

---

### Epic 5 — Risk Gates

#### Story 5.1 — `brute_force` requires double-flag gate

> As Trump using webprobe against a real target, I want `brute_force`
> to require *two* explicit flags so the friction matches the
> operational risk — failed-login probing is visible as an attack
> pattern in access logs, possible fail2ban / WAF lockouts.

Acceptance criteria:
- [ ] `brute_force` is **default OFF** for non-testbed targets.
- [ ] To enable on non-testbed targets: both `--include-brute-force`
  AND `--i-own-this-target=<hostname>` required.
- [ ] Only `--include-brute-force` (no `--i-own-this-target`):
  ```
  ERROR: --include-brute-force requires --i-own-this-target=<hostname>.

  brute_force sends ≥5 deliberate failed-login requests to the target.
  This pattern is visible in access logs as an attack and may trigger
  fail2ban / WAF lockouts. Pass --i-own-this-target=<hostname> to
  assert authorization for testing this target.
  ```
- [ ] Only `--i-own-this-target=<hostname>` (no `--include-brute-force`):
  silent; gate flag alone is benign.
- [ ] **Testbed exception**: when target host detected as testbed (Story
  5.4), `brute_force` runs without either flag.

#### Story 5.2 — `access_control`, `idor`, AND `csrf` require single-flag gate

> As Trump scanning a real target, I want `access_control`, `idor`, and
> `csrf` to require `--i-own-this-target=<hostname>` (single gate),
> since their operational consequence is audit-log anomalies and target
> state mutation (visible but not destructive), distinct from
> `brute_force`'s lockout-risk shape.

Acceptance criteria:
- [ ] `access_control`, `idor`, AND `csrf` are **default OFF** for
  non-testbed targets without `--i-own-this-target=<hostname>`.
- [ ] Passing `--i-own-this-target=<hostname>` alone enables all three
  modules (no per-module `--include-*` flags exist — single gate
  covers all three).
- [ ] When `--i-own-this-target=<hostname>` is set but auth missing:
  `access_control`, `idor` silently no-op (`auth_required` modules
  cannot fire without auth phase). `csrf` has no auth gate beyond
  `--i-own-this-target` itself but also requires auth phase to be
  established (it tests authed POST endpoints). Story 5.3 banner notes
  the secondary gap.
- [ ] **Testbed exception**: same as Story 5.1.

**csrf-gate rationale (7.3.E1 lock):** `csrf` module's state-mutating
risk is structurally equivalent to `brute_force`'s lockout risk — both
create real-world side effects on real targets. Single-gate (not
double) because csrf doesn't trigger external lockouts (fail2ban, WAF
rate limits) — only state mutation in the target's database.

#### Story 5.3 — Banner output when gates are missing

> As Trump running webprobe against a real target without risk-gate
> flags, I want a banner reminding me which modules are disabled and
> how to enable them, so I'm never surprised by a silent capability
> gap.

Acceptance criteria:
- [ ] Banner renders **after** module-set resolution and **before**
  auth-setup phase:
  ```
  Risk-gated modules disabled (default OFF for non-testbed targets):
    brute_force      Pass --include-brute-force
                     --i-own-this-target=<hostname> to enable.
    access_control   Pass --i-own-this-target=<hostname> to enable.
    idor             Pass --i-own-this-target=<hostname> to enable.
    csrf             Pass --i-own-this-target=<hostname> to enable.
  ```
- [ ] Banner only includes modules that would have run if gated.
  Excluded-via-`--exclude-modules` modules don't appear.
- [ ] When `--i-own-this-target=<hostname>` set but auth missing:
  ```
  Risk-gated modules disabled:
    access_control   --i-own-this-target set ✓; pass --auth-form
                     or --cookie to enable.
    idor             --i-own-this-target set ✓; pass --auth-form
                     or --cookie + --idor-baseline-form to enable.
    csrf             --i-own-this-target set ✓; pass --auth-form
                     or --cookie to enable.
  ```
- [ ] Banner colored WHITE/GREY (informational, not warning).
- [ ] Suppressed when target is testbed.
- [ ] Suppressed when ALL risk-gated modules are explicitly excluded.
- [ ] Does NOT render in HTML/TXT/JSON reports — terminal-only.

#### Story 5.4 — Testbed detection

> As a developer running webprobe against the bundled testbed, I want
> the testbed target to bypass risk-gate requirements so the
> testbed-as-acceptance-harness use case works without ceremony.

Acceptance criteria:
- [ ] **Detection rule (5.4.E1 lock):** Host+port + active fingerprint
  via dedicated endpoint:
  ```
  GET <target>/__webprobe_testbed__/health
  Expected response (ALL three must match):
    Status:       200
    Content-Type: application/json
    Body:         {"webprobe_testbed": true,
                   "testbed_version": "<version>"}
  ```
- [ ] Failure modes (ALL fall back to risk gates active):
  - Connection refused / timeout / DNS failure
  - 404 / 5xx / any non-200 status
  - Wrong Content-Type
  - Body fails JSON parse
  - JSON missing `webprobe_testbed: true`
- [ ] Banner on detection failure (when host+port matches `localhost:9999`
  or `127.0.0.1:9999` but probe fails):
  ```
  [!] Target host+port matches testbed convention (localhost:9999) but
      /__webprobe_testbed__/health probe failed. Risk gates remain active.
      If this IS the webprobe testbed, ensure the testbed harness is
      running the current version with the detection endpoint enabled.
  ```
- [ ] Detection probe constraints:
  - Pre-scan setup phase, before module dispatch.
  - Does NOT count toward URLs probed total in COVERAGE.
  - User-Agent: `webprobe/2.0 (testbed-detection)`.
  - Single probe attempt, no retry. Speed > resilience for setup phase.
- [ ] OPERATIONAL_RISK chip STILL renders on testbed bypass with
  testbed annotation:
  ```
  ⚠ OPERATIONAL_RISK: brute_force, access_control, idor, csrf
    fired against testbed (localhost:9999) — gates auto-bypassed
  ```
- [ ] Detection is target-driven, not flag-driven. Passing
  `--testbed-mode` is **not** a feature.

#### Story 5.5 — `--i-own-this-target` flag shape

> As Trump asserting authorization, I want the gate flag's shape to
> match its purpose — friction-as-binding (not friction-as-friction) —
> so the flag isn't trivially auto-enabled by a wrapper script.

Acceptance criteria:
- [ ] **Flag form (5.5.E1 lock):** Value-taking flag:
  ```
  --i-own-this-target=<hostname-or-hostname:port>
  ```
- [ ] Assertion validation:
  - Parse target URL, extract hostname (and port if explicit).
  - Hostname comparison: case-insensitive (DNS convention).
  - Port comparison: flag omits port = port-agnostic match; flag
    includes port = must match exactly.
  - Mismatch → fail loud:
    ```
    ERROR: --i-own-this-target asserts ownership of '<asserted>' but
    scan target is '<target-hostname>'. The assertion must match the
    target hostname; this prevents wrapper scripts from auto-asserting
    ownership across changing targets.
    ```
- [ ] Cannot be set via env var (only argv).
- [ ] Recorded in JSON envelope's `scan.risk_gates_asserted` (Story
  3.4) — user-typed argv form, case preserved (NOT normalized).
- [ ] Recorded in HTML OPERATIONAL_RISK chip per Story 3.3.

**Edge case lock:**

```
target = https://<deployment-url>/path
  + --i-own-this-target=<deployment-url>              → pass

target = <deployment-url>:8080
  + --i-own-this-target=<deployment-url>              → pass (port-agnostic)

target = <deployment-url>:8080
  + --i-own-this-target=<deployment-url>:8080         → pass (port-explicit)

target = <deployment-url>
  + --i-own-this-target=<deployment-url>                       → fail (no suffix matching)

target = <deployment-url>
  + --i-own-this-target=<deployment-url>:8080         → fail (port mismatch)
```

---

### Epic 6 — Module Contract (cross-cutting framework)

This epic must close (independently verifiable via a dummy module)
before Epic 7 stories can ship.

#### Story 6.1 — `BaseModule` class-level contract extensions

> As a module author writing a Sprint 2 detection module, I want to
> declare auth-handling and discovery-source preferences as class
> attributes (not flag-conditional logic in `run()`), so module bodies
> stay flag-naive and the engine resolves dispatch.

Acceptance criteria:
- [ ] **`BaseModule.auth_strategy`** class attribute,
  `Literal["unauth_always", "follow", "auth_required"]`. Required, no
  default — every Sprint 2 module class declares explicitly.
  - `unauth_always` — always anonymous (paths.py).
  - `follow` — unauth by default; runs again with auth attached during
    auth phase if `--scan-both` is set (headers, info-disclosure,
    sqli, xss).
  - `auth_required` — only fires when auth phase established
    (access_control, idor, csrf, error_leakage, session, brute_force).
- [ ] **`BaseModule.source_filter`** class attribute,
  `frozenset[Source]`. Default = `ALL`.
- [ ] **`session_factory()` return type** = `list[Session]`. Default
  len 1; len 2 when `--idor-baseline*` set.
- [ ] **`run()` signature unchanged** from Sprint 1: `run(self, target,
  session_factory, report_finding) -> None`.
- [ ] **`FIT3048_CATEGORY_MAP`** class attribute, `dict[str, int]`
  mapping internal finding-type names to FIT3048 categories (1-10).
  Required for any module emitting findings.
- [ ] Engine reads class attributes via `getattr(ModuleClass, ...)` —
  modules never instantiated just to query config.
- [ ] Validation at engine startup: every registered module class must
  declare `auth_strategy` and `FIT3048_CATEGORY_MAP`. Missing → fail
  loud. `source_filter` defaults to `ALL` if not declared.

#### Story 6.2 — `Finding` dataclass v2 extensions

> As Trump consuming Sprint 2 reports (or Sprint 3 templates consuming
> JSON), I want every finding to carry stable fields for auth
> attribution, dedup identity, and FIT3048 mapping.

Acceptance criteria:
- [ ] v1 fields preserved unchanged: `severity`, `category`, `name`,
  `url`, `payload`, `evidence`, `poc_url`, `remediation`,
  `fit3048_category`.
- [ ] **`fit3048_category` lifted to per-finding** (was per-module-class
  in Sprint 1's exercised path; Sprint 2 fully exercises with
  multi-category modules per 4.2.E1). Required field, must be in
  `1..10`. `Finding.__post_init__` invariant raises on out-of-range.
- [ ] **New: `auth_context: Optional[str]`**. Engine-populated
  (Story 6.4); modules never construct.
- [ ] **New: `baseline_context: Optional[str]`**. Module-constructed
  (only IDOR sets it).
- [ ] **New: `evidence_hash: str`**. Computed by `Finding.__post_init__`:
  ```python
  evidence_hash = sha256(
      f"{category}:{url}:{evidence}".encode()
  ).hexdigest()[:16]
  ```
  Hash function change requires schema MAJOR bump.
- [ ] **New: `seen_in: list[str]`**. Engine-managed (Story 6.4); values
  in `{"unauth", "authed"}`. Default per-pass; dedup merges to
  `["unauth", "authed"]` when same finding in both passes.
- [ ] `Finding.__post_init__` invariants:
  - `severity ∈ {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}`
  - `fit3048_category ∈ range(1, 11)`
  - `auth_context` is `None` or `str`
  - `baseline_context` is `None` or `str`
  - `seen_in` is non-empty list of `str`, values in
    `{"unauth", "authed"}`
  - `evidence_hash` matches `^[a-f0-9]{16}$` (auto-computed if not
    passed)
- [ ] All optional fields ALWAYS present in JSON serialization, `null`
  when absent (Q4 field-stability rule).

#### Story 6.3 — Engine pre-resolution semantics

> As an engine running Sprint 2 modules, I want to read each module
> class's declarations once at scan-start, build per-module config, and
> inject it via `__init__` so `run()` body has no flag-conditional
> branches.

Acceptance criteria:
- [ ] Pre-resolution phase order:
  1. Module enumeration; validate Story 6.1's required class attributes.
  2. Filter resolution (`--include-modules` / `--exclude-modules` per
     Epic 4, risk-gate filters per Epic 5).
  3. URL pool resolution (Epic 2); freeze pool.
  4. Session resolution (auth phase produces `sessions: list[Session]`).
  5. Per-module config injection: filtered URL view, session-list-or-
     empty, module-specific config (Sprint 1 `--cakephp` merging,
     Sprint 2 auth-related additions).
  6. Module instantiation: `ModuleClass(**resolved_config)`.
- [ ] Per-pass dispatch (`unauth` vs `authed`) for `follow` modules
  under `--scan-both`:
  - First pass: `run()` with `session_factory()` returning
    `[unauth_session]`. `seen_in = ["unauth"]`.
  - Second pass: `run()` with `session_factory()` returning
    `[primary_session, ...]`. `seen_in = ["authed"]`.
- [ ] Module body MUST NOT introspect engine state.
- [ ] Engine wraps `report_finding` in stdout lock (Sprint 1 carryover).
- [ ] `--scan-both` ordering: back-to-back per module
  (`headers-unauth → headers-auth → info-disclosure-unauth →
  info-disclosure-auth → ...`) for debuggability.
- [ ] Module fire ordering with auth (Q2 lock):
  ```
  [unauth phase]  headers → info-disclosure → paths → sqli → xss
  [auth setup]    login (--auth-form) or cookie attach (--cookie)
  [auth phase]    access_control → csrf → idor → error_leakage →
                  session → brute_force
  ```

#### Story 6.4 — `report_finding` callback v2 (auto-injection rules)

> As a module author emitting findings, I want auth_context to be
> populated automatically by the engine based on which pass and session
> I'm running under, so I don't construct attribution strings inside
> `run()`.

Acceptance criteria:
- [ ] **Engine wraps `report_finding`** per scheduled module + per pass:
  - **`auth_context`**:
    - `unauth_always`: always `None`.
    - `follow` unauth pass: `None`.
    - `follow` `--scan-both` authed pass: `"as <user-id> (<role>)"`
      from primary session.
    - `auth_required`: `"as <user-id> (<role>)"` from primary session.
  - **`seen_in`**: per-pass — `["unauth"]` or `["authed"]`. Dedup
    merges per Q4(iii).
  - **`evidence_hash`**: `Finding.__post_init__` auto-computes.
  - **`fit3048_category`**: looked up from `ModuleClass.FIT3048_CATEGORY_MAP`
    by finding-type key at emit time.
- [ ] **`baseline_context`**: module-constructed only (engine never
  auto-injects).
- [ ] User-id resolution:
  - `--auth-form` mode: `"as <auth-user-value>"` (or `+ (<role>)` if
    `--auth-role` set).
  - `--cookie` mode: `"as primary"` (or `+ (<role>)` if `--auth-role`
    set). No identity available from cookie alone.
- [ ] Inline tease still fires per Sprint 1 callback (`[HIGH] ...`
  printed at moment-of-detection).
- [ ] Stdout lock preserved (modules stay thread-naive).
- [ ] Missing key in `FIT3048_CATEGORY_MAP` at emit time → fail loud
  with module class name + finding-type key + map contents
  (developer error, not runtime condition).
- [ ] Engine MUST NOT mutate: `name`, `url`, `payload`, `evidence`,
  `poc_url`, `remediation`, `severity`, `category`. Engine only
  injects per-finding *attribution* fields and computed-identity
  fields.

#### Story 6.5 — Module size discipline + auth-aware HTTP helper

> As Trump preserving Sprint 1's legibility commitment in Sprint 2, I
> want every detection module ≤50 lines on first build attempt, with
> helper extraction as the structural-relief pattern.

Acceptance criteria:
- [ ] **50-line cap per detection module file** (Sprint 1 carryover).
  Sprint 1 actuals: headers=49, info_disclosure=49, paths=46, sqli=47,
  xss=43, traversal=50.
- [ ] **Helper extraction**: `webprobe/modules/_<name>_helpers.py` if
  module crosses 50 lines.
- [ ] `/build` Checkpoint B carryover: `wc -l webprobe/modules/*.py`
  audit must pass.
- [ ] Helper line counts not capped (helpers exist to absorb
  complexity).
- [ ] Engine's `__init__.py` and other framework files not subject to
  50-line cap.

**Auth-aware HTTP helper (6.5.E1 lock):** Pre-extract via extending
`_common.py` (single capability axis: all HTTP requests may or may not
carry a session). Locked signature:

```python
# webprobe/modules/_common.py

def send(url, *, session=None, **kwargs):
    """
    Send HTTP request, optionally with attached session.

    Sprint 1 callers (sqli/xss/traversal): session=None (default),
    anonymous.
    Sprint 2 callers (access_control/idor/csrf/error_leakage/brute_force):
        session=<requests.Session> from session_factory().
    """
    if session is None:
        return requests.get(url, **kwargs)
    return session.get(url, **kwargs)


def compare_responses(resp_a, resp_b):
    """sha256 body match — IDOR's core check, hoisted for reuse."""
    return (sha256(resp_a.content).hexdigest()
            == sha256(resp_b.content).hexdigest())
```

Constraints:
- Keyword-only `session` parameter (`*` prevents positional misuse).
- Sprint 1 callers' source files unchanged — `send(url)` still works.
- `_common.py` exempt from 50-line cap per "helpers absorb complexity".

**Future-helper rule:** if `/build` discovers a third auth-aware
concern that doesn't fit `send` or `compare_responses` (e.g.,
session-cookie introspection), extend `_common.py` with the new
helper rather than splitting into a second file. Capability-axis-
single-helper discipline.

---

### Epic 7 — New Detection Modules (six parallel stories)

Each module: ≤50 lines, declares `(auth_strategy, source_filter,
FIT3048_CATEGORY_MAP)` per Epic 6, uses `_common.send()` (and
`compare_responses()` for IDOR), emits via the engine-wrapped
`report_finding`.

#### Story 7.1 — `access_control` module

> As Trump auditing FIT3047 with a Coach role, I want `access_control`
> to probe admin-shape paths with my Coach session and flag any that
> return authed-shape content, so I catch missing role checks.

Acceptance criteria:
- [ ] Class declarations: `auth_strategy = "auth_required"`,
  `source_filter = ALL`,
  `FIT3048_CATEGORY_MAP = {"role_violation": 2}`.
- [ ] Probes a curated list of admin-shape paths from
  `webprobe/data/access_control/admin_paths.txt` (mirrors Sprint 1
  paths/curated.txt discipline). Default contents include `/admin/`,
  `/admin/users`, `/admin/dashboard`, `/admin/messages`,
  `/backoffice/`, `/controlpanel/`, `/cpanel/`, `/manage/`,
  `/console/`.
- [ ] Also probes URLs from `Target.urls` matching admin-shape regex
  `/(admin|backoffice|controlpanel|manage|console)/`.
- [ ] Probes with `sessions[0]` (primary).
- [ ] Detection rule: HTTP 200 + admin-shape signal → flag HIGH
  `role_violation`.
- [ ] Skips 302→login (correctly protected), 404 (path doesn't exist),
  403 (correctly forbidden).
- [ ] Each finding: path, status code, signal-keyword that matched,
  fix hint with controller-action parsed from URL if CakePHP-shaped.

**Admin-shape signal heuristic (7.1.E1 lock):** Configurable via
`webprobe/data/access_control/admin_signals.txt`. Default ships:

```
All Users
Admin Dashboard
User Management
All Messages
Admin Panel
Backoffice
BakeAdmin
phpMyAdmin
Manage Users
管理后台
```

Module reads file at scan-start; missing file → fail loud at engine
validation.

**Severity for ambiguous 200 (7.1.E2 lock):** Skip emission entirely
for 200-without-confirmed-signal cases. Pair with single INFO finding
at end of `access_control` module:

```
[INFO] access_control: probed 12 admin-shape paths, 3 returned 200
       without confirming admin signal (skipped from findings to
       reduce noise; review URLs manually: /manage/profile,
       /admin/account, /backoffice/me).
```

Pattern: **no false alarm** — don't claim findings you can't confirm
(skip emission, document in COVERAGE).

#### Story 7.2 — `idor` module

> As Trump testing horizontal access controls between two Coach
> accounts, I want `idor` to probe candidate resource URLs with both
> sessions and flag any URL where Coach A's response body matches
> Coach B's response body (sha256 equality), so I catch missing
> ownership checks.

Acceptance criteria:
- [ ] Class declarations: `auth_strategy = "auth_required"`,
  `source_filter = ALL`,
  `FIT3048_CATEGORY_MAP = {"cross_account_leak": 2,
  "idor-baseline-missing": 2}`.
- [ ] Multi-session: `sessions = session_factory()`. If `len < 2` →
  emit INFO `idor-baseline-missing` (per scope.md) and return early.
- [ ] When `len == 2`: identifies candidate URLs from `Target.urls`
  matching ID-bearing patterns:
  - `/<resource>/<numeric-id>` (e.g., `/patients/47`)
  - `/<resource>/view/<numeric-id>` (CakePHP convention)
  - URL with `?id=N` or `?<resource>_id=N` query param
- [ ] For each candidate: `resp_a = send(url, session=sessions[0])`,
  `resp_b = send(url, session=sessions[1])`.
- [ ] Detection rule: `compare_responses(resp_a, resp_b) is True` AND
  both 200 → flag HIGH `cross_account_leak`.
- [ ] Skips when either response non-200; skips when bodies differ.
- [ ] Finding: `auth_context` engine-injected, `baseline_context`
  module-set as `f"baseline {baseline_user_id} owns {resource_path}"`.
- [ ] `Sessions:` line in render per Story 3.3 lock.
- [ ] Same-user detection happens at engine pre-resolution (Story
  6.3); idor receives validated multi-session input.

**ID enumeration scope (7.2.E1 lock):** Probe-only-discovered. Module
sees `/coach/patients/47` in `Target.urls` → probes only `/coach/
patients/47`. No synthesis of `/coach/patients/{1..N}`. If user wants
enumeration, `--url-list` provides explicit opt-in. Sprint 3 candidate:
`--idor-enumerate <count>` flag for bounded enumeration.

**UUID/hash IDs (7.2.E2 lock):** Sprint 2 detects integer-ID IDOR
only. Banner shown when idor module runs and `Target.urls` contains
UUID-shaped paths (regex `/[0-9a-f]{8}-[0-9a-f]{4}-/` matches any
URL):

```
[INFO] idor module detects integer-ID IDOR only. UUID-based or
       hash-based resource IDs are not enumerated in v2.0; manual
       testing required. UUID detection support is a Sprint 3+
       candidate.
```

Pattern: silent gap = false confidence. Honest banner > silent gap.

#### Story 7.3 — `csrf` module

> As Trump checking whether form POSTs are CSRF-protected, I want
> `csrf` to send POST requests to discovered forms with the CSRF token
> deliberately omitted and flag any that succeed instead of rejecting.

Acceptance criteria:
- [ ] Class declarations: `auth_strategy = "auth_required"`,
  `source_filter = ALL`, `FIT3048_CATEGORY_MAP = {"csrf_missing": 2}`.
- [ ] **Risk-gated** per Story 5.2 — requires
  `--i-own-this-target=<hostname>` (state-mutating risk).
- [ ] Reuses Sprint 1's form discovery (`Target.forms`).
- [ ] For each `method="POST"` form, constructs malformed POST: all
  `<input type="hidden">` stripped (CSRF tokens removed, ALL hidden
  fields removed); other fields populated with placeholders (text →
  `"webprobe-csrf-test"`, email → `"webprobe@test.invalid"`, number →
  `"1"`).
- [ ] POSTs to form's action URL with primary session attached.
- [ ] Detection rule:
  - 403 / 419 (Laravel CSRF mismatch) → no finding (correct
    protection).
  - 200 / 302 / 204 → flag HIGH `csrf_missing`.
  - 4xx other than 403/419 → INFO `csrf_indeterminate`.
- [ ] Skips GET-only forms; skips off-host action URLs.
- [ ] Each finding: form action URL, form method, fix hint.

**Rails `_method` override (7.3.E2 lock):** csrf strips ALL hidden
inputs (including `_method`, `_token`, etc.). Rails apps relying on
`_method` for DELETE/PUT semantics will not have those endpoints
tested in v2.0. Method-override-aware CSRF testing is Sprint 4+
candidate.

#### Story 7.4 — `error_leakage` module

> As Trump checking whether the login form leaks user existence and
> whether the app leaks stack traces, I want `error_leakage` to do a
> controlled login-response-diff probe and check for stack traces in
> error pages.

Acceptance criteria:
- [ ] Class declarations: `auth_strategy = "auth_required"`,
  `source_filter = ALL`,
  `FIT3048_CATEGORY_MAP = {"username_enumeration_login": 7,
  "stack_trace_leakage": 1}`.
- [ ] **User enumeration (Cat 7):**
  - Probe A: POST `--auth-form` URL with `<auth-user>` (real, valid)
    + `wrong_password_<random>`.
  - Probe B: POST same URL with
    `nonexistent_user_<random>@test.invalid` + `wrong_password_<random>`.
  - Compare responses: if status, redirect URL, body sha256, OR
    error-message differs → flag HIGH `username_enumeration_login`.
  - Identical → no finding.
  - Probe count: 2 extra POSTs.
- [ ] **Stack trace leakage (Cat 1) — own probe set (7.4.E1 lock):**
  `error_leakage` makes its own probe set:
  ```
  GET /
  GET /<auth-form-url>
  GET /admin/__webprobe_404_trigger__
  GET /?id='%20OR%201=1
  GET /search?q='   (only if /search in Target.urls)
  ```
  Active detection > passive observation. Sprint 1 didn't have a
  shared response cache; introducing one would break Story 6.3's
  frozen-pool architectural pattern.
- [ ] Stack-trace signatures from
  `webprobe/data/error_leakage/stack_trace_patterns.txt`:
  - PHP: `Stack trace:`, `#0 /var/www/`, `Fatal error:`, `Notice:`,
    `Warning: `
  - Python: `Traceback (most recent call last):`, `File "/`, `line N,
    in `
  - Ruby: `Error (`, `from /` followed by `.rb:N`
  - Java: `Exception in thread`, `at <package>.<class>(`,
    `Caused by:`
  - Generic: `at /var/www/`, `at /home/`, `at /opt/`
- [ ] Match → flag MEDIUM `stack_trace_leakage` with first 200 chars
  of matched trace as evidence.
- [ ] Cross-module observability is Sprint 3+ candidate (7.4.E2
  lock): "error_leakage performs best-effort stack-trace detection
  from its own active probes. Stack traces triggered by other
  modules' probes (e.g., sqli's malformed payloads) are not captured
  by error_leakage in v2.0."

#### Story 7.5 — `session` module

> As Trump checking that logout properly invalidates the session
> cookie, I want `session` to log in as a throwaway user, observe the
> cookie, log out, and replay the cookie against a protected URL, so
> I catch sessions that aren't server-invalidated on logout.

Acceptance criteria:
- [ ] Class declarations: `auth_strategy = "auth_required"`,
  `source_filter = ALL`,
  `FIT3048_CATEGORY_MAP = {"session_persists_post_logout": 7,
  "session_fixation": 7}`.
- [ ] **Throwaway sub-session pattern** per Story 1.4. Skips with
  INFO when primary auth is `--cookie`.
- [ ] **Post-logout cookie replay (Cat 7):**
  - GET protected URL `<X>` with ephemeral session → `auth_response_a`.
  - POST `<logout-url>` with ephemeral session → `logout_response`.
  - GET `<X>` again → `auth_response_b`.
  - If `auth_response_b` similar-shape to `auth_response_a` (sha256
    match OR both 200 with overlap signals) → flag HIGH
    `session_persists_post_logout`.
  - 302→login OR 401 → correct invalidation, no finding.
- [ ] **Session fixation (Cat 7) — secondary check:**
  - Pre-login: GET `--auth-form` URL anonymously, capture `Set-Cookie`.
  - Login with that pre-set cookie attached.
  - Post-login: compare session cookie value — same as pre-login →
    flag MEDIUM `session_fixation`. Rotated → correct, no finding.
- [ ] Logout URL discovery: heuristic patterns `/logout`, `/signout`,
  `/users/logout`, `/sessions/destroy`. `--logout-url` override
  deferred to Sprint 3.
- [ ] Protected URL `<X>`: same as Story 3.1's session-check probe
  URL.
- [ ] COVERAGE emits `Logout test:` line per Story 3.1.

**Logout URL discovery failure (7.5.E1 lock):** Silent skip with INFO
finding:

```
[INFO] session module: no logout endpoint found at heuristic paths.
       Tried: /logout, /signout, /users/logout, /sessions/destroy
       Pass --logout-url <url> to specify a logout endpoint, or
       --exclude-modules session to suppress this notice.
       Post-logout cookie test was not run.
```

Pattern: capability-gap honest-INFO from Stories 1.4 / 2.2.

#### Story 7.6 — `brute_force` module

> As Trump verifying my app's lockout policy, I want `brute_force` to
> send 5+ deliberately failed logins and detect whether the app
> implements lockout (or rate limiting), so I catch missing or weak
> failed-login defenses.

Acceptance criteria:
- [ ] Class declarations: `auth_strategy = "auth_required"`,
  `source_filter = ALL`,
  `FIT3048_CATEGORY_MAP = {"no_lockout": 7, "weak_lockout": 7}`.
- [ ] Risk-gate per Story 5.1: testbed-default; non-testbed targets
  require `--include-brute-force` AND `--i-own-this-target=<hostname>`.
- [ ] Probe sequence:
  - POST `--auth-form` URL with `<auth-user>` + `wrong_password_<i>`
    for `i in 1..5`. Record responses.
  - POST 6th attempt with same user + another wrong password.
  - Detection rule:
    - All 6 responses identical (status, redirect, body sha256) →
      flag MEDIUM `no_lockout`.
    - Response 6 differs from 1-5 (lockout signal present) → no
      finding (correct).
    - Responses 1-5 themselves differ (rate limiting earlier) →
      flag INFO `weak_lockout` noting threshold.
- [ ] **Per-attempt rate**: 1 second delay between attempts.
- [ ] **Side effect notice**: README documents that `--auth-user`
  account will be locked out by lockout policies being tested.
- [ ] Engine validates: brute_force may run only on testbed OR with
  both gate flags.

**Lockout signal heuristic (7.6.E1 lock):** Configurable via
`webprobe/data/brute_force/lockout_signals.txt`. Default ships
multi-language (English + Chinese + Japanese) for CTF testbed
compatibility:

```
account locked
too many attempts
too many login attempts
rate limit
account suspended
account temporarily disabled
please try again later
invalid credentials. account locked
帐户已锁定
试用次数过多
アカウントがロックされています
```

**Account selection (7.6.E2 lock):** Probe with `--auth-user` (real
account). `--i-own-this-target=<hostname>` is the consent signal.
README documents:

```
brute_force module side effect: the account specified in --auth-user
will be locked out by the lockout policy you're testing for. Use a
dedicated test account (not your daily login) when running brute_force
on real targets. On the bundled testbed, this is a non-issue —
testbed accounts are disposable.
```

---

## What We're Building

The Sprint 2 P0 + P1 + Stretch item list is locked in `docs/sprint-2/
scope.md` (14 items, ~13-16 hr build). This PRD's epics map onto that
list:

- **P0 (10 items):** Stories 1.1, 1.2, 1.3, 1.5, 6.1, 6.2, 6.3, 6.4,
  6.5, 7.1, 7.2, 7.3, 7.4, 5.4, plus `pyproject.toml` +
  `console_scripts` + testbed (item 3.5) + SCAN COVERAGE block (item
  3.6).
- **P1 (6 items):** Stories 7.5 (`session`), 7.6 (`brute_force`), 3.4
  JSON sink, 2.4 `--url-list`, 2.1 `--use-sitemap`, 2.3 `--use-robots`.
- **Stretch:** `--export-md` mini.

Two-endpoint structure (carried from scope.md):

- **Endpoint A — Engineering complete:** all P0 shipped, testbed
  validates each detection module fires, 50-line audit passes, three
  demo HTML reports rendered, README updated, `/reflect` runs and
  engineering-side diary entry written. Optional `v2.0.0-rc.1` GitHub
  tag.
- **Endpoint B — Win pinned (external gate, max-gap fallback):**
  WebProbe v2 ran against <team>'s FIT3047 <iteration 2> deployment
  with auth, produced *either* a finding from a post-login page *or*
  a clean SCAN COVERAGE block. `v2.0.0` GitHub release tag. README's
  "Last verified against" line updated.
- **Max-gap fallback:** if Endpoint B has not triggered within ~2 weeks
  of Endpoint A, validate against testbed (mandatory baseline) +
  secondary target (personal dev deployment, juice-shop, FIT3047
  <iteration 1> archive). Document <iteration 2> readiness as explicit
  constraint, declare provisionally won, re-run when <iteration 2>
  deploys.

## What We'd Add With More Time

Sprint 3 carryovers — **PRD-level promises that become Sprint 3 /scope
inputs automatically**:

- `--sitemap-cap <N>` flag for explicit sitemap URL cap override (Story
  2.1 lock).
- `--sitemap-url <url>` flag for non-canonical sitemap location (Story
  2.1 lock; empirical trigger via Story 2.3's robots-Sitemap-INFO).
- `--logout-url <url>` flag for explicit logout endpoint (Story 7.5
  lock).
- `--idor-enumerate <count>` flag for bounded ID enumeration around
  discovered IDOR candidates (Story 7.2 lock).
- `--auth-user-field NAME` / `--auth-pass-field NAME` override flags,
  pending validation against ≥3 real testbeds during Sprint 2 `/build`
  (Story 1.1 lock).
- UUID/hash-ID IDOR detection (Story 7.2 lock).
- Cross-module response observability framework (Story 7.4 lock).
- `/me`-shape endpoint identity probe for higher-confidence same-user
  IDOR detection (Story 1.3 lock).
- Full template system (NL matching, column mapping,
  `.webprobe-template-map.json` learning, diff mode) — bridge artifact
  is Sprint 2 `--export-md` stretch.
- `pytest` automation against testbed; testbed serves as manual
  integration-test harness for Sprint 2.
- `--severity-min <tier>` flag for severity threshold filtering — Sprint
  3 template-system concern.
- Session-check probe URL upgrade: "first sitemap URL if available,
  else homepage" (Story 3.1 lock).

Sprint 4+ candidates (deferred scope, not Sprint 3 promises):

- Multi-step login flows (SSO redirect chains, MFA challenges,
  email-then-password flows) — Story 1.1 lock.
- Rails `_method`-override-aware CSRF testing — Story 7.3 lock.
- Real role detection (JWT claim parsing, framework-specific role
  attributes) — Story 1.6 lock.
- Recursive HTML link-following spider/crawler — scope.md permanent
  rejection (Burp Suite Spider exists; would dominate sprint).

## Non-Goals

Sprint 2 explicitly does NOT do:

1. **Professional pentesting.** Scanner is a learning tool with
   `<50-line-per-module` legibility commitment. Commercial-scanner
   breadth is anti-goal.
2. **Automated CI scanning of third-party sites.** Risk-gate friction
   is intentional; CI workflows that auto-pass `--i-own-this-target`
   are out-of-scope.
3. **Brute-force against shared environments without explicit
   ownership assertion.** Double-flag gate is non-negotiable for
   non-testbed targets.
4. **Full template system.** Bridge `--export-md` stretch ships the
   shape; Sprint 3 builds the engineering.
5. **Spider / recursive HTML crawler.** Permanently rejected; Burp
   Suite Spider exists, would dominate the sprint.
6. **`--severity-min` filtering.** Consumer-side concern; Sprint 3
   templates handle it; `jq '.findings[] | select(.severity ==
   "HIGH")'` solves ad-hoc.
7. **UUID-based IDOR detection.** Sprint 2 covers integer-ID IDOR only.
   Banner discloses the gap.
8. **Multi-step login flows.** Sprint 4+; v2.0 fails loud and points
   at `--cookie`.
9. **Cross-module response observability.** `error_leakage` makes its
   own probes; Sprint 1's frozen-pool architectural pattern preserved.

## Open Questions

Items genuinely unresolved at end of `/prd`, requiring `/spec` or
`/build` resolution:

- **Throwaway sub-session mechanism (Story 1.4).** `session_factory(
  ephemeral=True)`, separate `ephemeral_login()` helper, or vanilla
  second `login_form()` invocation — `/spec`'s call.
- **`Target.urls` data shape (Story 2.5).** `List[Tuple[str, Source]]`
  or dataclass `List[ProbeURL]` with `url` + `source` fields —
  `/spec`'s call.
- **`scan_coverage` JSON internal shape (Story 3.4).** Field-by-field
  layout mirrors terminal layout but exact JSON keys (`urls_probed.
  by_source.{sitemap, robots, url_list, dynamic, curated}` vs
  alternative key shapes) — `/spec`'s call.
- **HTML rendering of FIT3048 grouping vs auth-context badges (Story
  3.3).** Definition list, table, or styled `<div>` blocks —
  `/spec`'s call.
- **Banner / `--help` text wording, `--version` output (Q5(a) lock).**
  Defer to `/build` with `/spec`-level documented defaults; `--help`
  flag taxonomy categories pinned (Authentication / Discovery /
  Output / Filtering / Risk Gates).
- **`--scan-both` deduplication implementation (Story 3.4).** Engine-
  level vs in `Finding.__post_init__` — `/spec`'s call. Identity tuple
  `(category, target_url, evidence_hash)` is locked.
- **SQLi `DIFF_THRESHOLD` re-tuning.** Sprint 1 left at 0.30 with
  `auditable_constant_in_helpers` pattern; Sprint 2 doesn't change
  unless <iteration 2> audit surfaces a known SQLi missed by 0.30.
  `/build` Checkpoint A may revisit.

## Locked PRD Invariants (cross-cutting)

These invariants must survive `/spec` and `/build`:

- **`--auth-role` is decorative.** Modules MUST NOT branch on its
  value (Story 1.6).
- **Mode enum has exactly four values.** No provenance variants
  (Story 3.1).
- **`evidence_hash` formula is fixed.** `sha256(f"{category}:{url}:
  {evidence}").hexdigest()[:16]`. Function changes = MAJOR bump
  (Story 3.4).
- **JSON optional fields always present, `null` when absent.** Field
  stability over message size (Story 3.4).
- **`url_list > robots > curated > sitemap > dynamic` priority.**
  Cross-source dedup ordering (Story 2.5).
- **50-line module cap.** Helper extraction over rule relaxation
  (Story 6.5).
- **`session_factory()` returns `list[Session]`.** Default len 1; len
  2 with `--idor-baseline*` (Story 1.3, 6.1).
- **Auth phase exits before any module fires on login failure.**
  Stories 1.1, 1.3.
- **csrf is `--i-own-this-target=<hostname>`-gated.** State-mutating
  side effects elevate to gated module class (Story 5.2; corrects
  initial Q5(b) framing).
- **Risk gates enforce *binding*, not just friction.**
  `--i-own-this-target=<hostname>` value validation defends against
  wrapper-script reuse across changing targets (Story 5.5).
