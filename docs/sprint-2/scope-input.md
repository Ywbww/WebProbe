# Sprint 2 — Scope Input

## Context for /scope
WebProbe v1 is complete (18 checklist items, 6 modules, public 
at github.com/Ywbww/WebProbe). Sprint 2 ambition: take it from 
"single-page passive+light-active scanner" to "the canonical 
FIT3047/FIT3048 cohort security tool."

## Reference document
<team> Security Test Cases doc (<iteration 1>, 26 security TCs).
This is ONE team's format. Each FIT3047 team has different 
document structures, column names, even languages. The doc is 
under uploaded files; key shape: columns are 
[TC ID, Category, Test Step, Expected, Actual, Status].

## v1 coverage gap (26 TC analysis)
- v1 covers ~6/26 (23%) — sqli, xss, HTTPS check, indirect cookie 
  flag check
- 17/26 require new capabilities, mostly in two clusters:
  - Authenticated probing (IDOR, access control, session, brute 
    force) — 11 TCs
  - Active CSRF/CAPTCHA/error-leakage testing — 6 TCs
- 3/26 NOT automatable (DB password storage, business-rule 
  validation) — out of scope

## Sprint 2 candidate features (30 items, 6 groups)

### 2.1 Authenticated scanning infrastructure
1. --cookie flag (pass session cookie)
2. --auth-form flag (form login → use resulting session)
3. Adapt BaseModule contract to flow auth state to all modules

### 2.2 Authenticated detection modules
4. access_control module (unauth access to protected pages)
5. idor module (horizontal privilege)
6. csrf module (POST without token → expect 403)
7. brute_force module (5 wrong passwords → expect lockout)
8. error_leakage module (user enumeration via response diff)
9. session fixation / cookie replay / post-logout access

### 2.3 General security detection expansion
10. os_command_injection module
11. HTTP methods abuse (OPTIONS / TRACE / PUT)
12. Default credentials dictionary test
13. CORS misconfiguration (Allow-Origin: * + Credentials: true)
14. HTTP→HTTPS redirect check
15. SRI missing (external <script> without integrity=)
16. Open redirect detection
17. HTML comment sensitive info detection

### 2.4 Output system overhaul
18. JSON output sink
19. Template system: --template <docx/xlsx/md/csv>
20. Natural-language matching (test step text → finding type)
21. Column mapping learning (.webprobe-template-map.json)
22. Diff mode (scan1.json vs scan2.json — pre-fix/post-fix)

### 2.5 Install / polish
23. pyproject.toml + console_scripts (pip install → webprobe cmd)
24. README revision
25. pytest suite

### 2.6 Multi-URL scanning (A+B chosen, NOT full spider)
26. --url-list <file> (explicit URL list)
27. --use-sitemap (parse sitemap.xml)
28. --use-robots (parse robots.txt Disallow paths — these are 
    often the sensitive paths attackers want)
29. Multi-URL findings consolidated into single report

EXPLICITLY REJECTED: full HTML-link-following spider/crawler.
Rationale: rabbit hole (15+ corner cases), breaks "fast scanner" 
positioning, replaceable by Burp Suite Spider, would dominate 
the entire sprint.

## Time budget reality check
- Sprint 1 was ~6 hrs build (planning was another ~3 hrs)
- Sprint 2 above is realistically 14-18 hrs build = 3x Sprint 1
- I'd rather Claude Code push back on scope than build half-baked 
  versions of all 30. Expecting /scope to recommend splitting 
  into Sprint 2 (P0 essentials) + Sprint 3 (P1 polish).

## Likely natural split (my guess; defer to /scope conversation)
Sprint 2 (~10 hrs): items 1-9 (auth + auth-after detections), 
  23 (pyproject), 18 (JSON), 26-29 (multi-URL)
Sprint 3 (~8 hrs): items 10-17 (general detection expansion), 
  19-22 (template system), 24-25 (README + tests)

## Two design decisions already locked
1. Multi-URL = A+B only (no spider)
2. Template system MUST be in this project's roadmap (not v1.0 
   forever) because each team's report format is different — 
   without templates, the tool isn't truly cohort-usable

## Two things that explicitly DON'T need /scope discussion
- Architecture: BaseModule contract, output sinks, threading 
  model, file structure — all settled in v1 spec
- Workflow: spec-driven, autonomous build mode, A/B/C 
  checkpoints — same protocol as Sprint 1
