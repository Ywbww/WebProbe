# Devpost project page update — WebProbe v2.0.0

This file is a paste-ready content brief. Devpost upload itself is
manual: log in to your Devpost project page and paste each section
into the matching field. PNG screenshots come from opening the HTML
reports in a browser and capturing them.

---

## Project description (paste into Devpost description field)

**WebProbe v2.0.0 — auth-aware web vulnerability scanning, every
detection module under 50 lines.**

WebProbe is a small, legible Python CLI scanner built to make
security-audit work easier for Monash students taking FIT3047
(Industry Experience) and FIT3048 (Web Application Security), and
useful as a teaching/CTF tool for anyone learning where common web
flaws live. Twelve detection modules — six unauthenticated (headers,
info_disclosure, paths, sqli, xss, traversal) and six auth-aware
(access_control, idor, csrf, error_leakage, session, brute_force) —
each under fifty lines. Every scan emits four output sinks: a
color-coded terminal stream with a `SCAN COVERAGE` block above
findings, a single-file shareable HTML report, an ANSI-stripped TXT
paste-ready for reflective diaries, and a versioned JSON envelope
(`version: 2.0`) for downstream tooling.

Sprint 2 is the auth surface. v1 only saw what an anonymous browser
could see; v2 logs in. `--auth-form` does form-based login,
`--cookie` accepts a raw Cookie header, and `--idor-baseline-form`
spins up a second session to make IDOR detection a one-command
operation: scan with two distinct user identities, compare their
responses on the same authed URL, and a sha256 match is the
cross-account-leak signal. Every finding the renderer emits carries a
per-finding auth attribution ("as coach_a, baseline coach_b owns
id=47") so peer-assessment write-ups don't have to reconstruct
session context from memory.

Sprint 2 also ships a self-contained Flask testbed
(`python3 -m webprobe.testbed`) — a localhost target with intentional
findings for every v2 module. `scripts/run_testbed_acceptance.sh`
runs the canonical Sprint 2 acceptance invocation against it
end-to-end and captures all four output sinks for inspection.

---

## Tech stack (one-liners — paste into Devpost tech stack list)

- **Python 3.10+** — language target; modern type-hint syntax used throughout.
- **requests** — HTTP client for connectivity, auth, module probing.
- **BeautifulSoup4** — HTML parsing for form discovery + comment leak detection.
- **colorama** — ANSI color in the terminal sink; auto-strips when piped.
- **Flask** — testbed-only dependency, exposed via `[project.optional-dependencies]` (`pip install -e ".[testbed]"`); core install does not pull Flask.

---

## Screenshots to upload

`scripts/run_testbed_acceptance.sh` produces these four artifacts under
`screenshots/sprint-2/`. PNG conversion is manual: open each HTML in a
browser, then take a window screenshot.

| Devpost slot | Source artifact | How to convert |
|---|---|---|
| 1. Terminal acceptance | `screenshots/sprint-2/terminal-acceptance.txt` | Take a terminal-window screenshot OR paste the txt as a code block. |
| 2. Default HTML report | `screenshots/sprint-2/default-grouping.html` | Open in browser → window screenshot. |
| 3. FIT3048-grouped HTML report | `screenshots/sprint-2/fit3048-grouping.html` | Open in browser → window screenshot. |
| 4. Testbed unauth HTML report | `screenshots/sprint-2/testbed-unauth.html` | Open in browser → window screenshot. |

The default-grouping run is the canonical dual-session acceptance: 12
modules scheduled, 12 completed, 17 distinct finding types from a
single invocation including `role_violation`, `cross_account_leak`,
`csrf_missing`, `stack_trace_leakage`, `session_fixation`,
`no_lockout`, `missing_csp`, and the
sensitive_path_exposed_{high,medium} pair.

---

## Demo video

No demo video planned for v2.0.0 release. The four screenshots plus
`scripts/run_testbed_acceptance.sh` are the canonical reproducer.

---

## "What's new in v2.0.0" (paste into Devpost updates feed)

- Auth surface: `--auth-form`, `--cookie`, `--idor-baseline-form` —
  form-based login, cookie-based auth, separate IDOR baseline session.
- 6 new detection modules: access_control, idor, csrf, error_leakage,
  session, brute_force.
- 6 v1 modules retrofit to the v2 Module Contract — Lock 5 clean,
  ≤50 lines each, registered via `@register`.
- Self-contained Flask testbed (`python3 -m webprobe.testbed`) with
  intentional findings for every v2 module.
- `SCAN COVERAGE` block above FINDINGS — first-class evidence of work.
- Versioned JSON envelope (`version: 2.0`) on every run; `--json-out -`
  routes JSON to stdout (terminal text moves to stderr) for piping.
- Module Registry (`@register` decorator) replaces the v1 manifest;
  Engine Phase 1 enumerates `MODULE_REGISTRY` and validates required
  class attributes.
- Engine phase ordering with capability-budget discipline (per the
  Sprint 2 named pattern `phase-boundary-as-capability-boundary`).
- Risk gates: `--include-brute-force` and `--i-own-this-target`, with
  automatic bypass when the testbed is detected.
