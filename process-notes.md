# Process Notes

## /onboard

**Technical experience summary:** Comfortable intermediate. Cybersecurity
student. Strong in Python, C, Java, PHP/CakePHP 5, SQL/MariaDB. Tools:
Git, GNS3, Wireshark, Claude Code. Has shipped a Python CLI recon tool
(ReconKit) using threading, urllib, sockets. Published research paper on
deepfake attacks against biometric systems — domain-deep in security.

**Learning goals:** Understand web vuln detection at the implementation
level (XSS / SQLi heuristics like Burp Suite's). Build WebProbe and run
it against their own CakePHP FIT3047 app. Win = catch a real vuln they
didn't already know about.

**Creative sensibility:** CTF aesthetic (HackTheBox / TryHackMe energy)
+ Mandopop softness. Translate to: terminal-forward output, satisfying
finding moments, calm and readable rather than aggressive hacker-green.
Light bandwidth for media due to uni workload.

**Prior SDD experience:** Yes — strong. Second project using this plugin.
Just shipped ReconKit through the full /scope → /prd → /spec → /checklist
→ /build chain. Articulated the value of specs unprompted ("defined every
function signature, data structure, and edge case before writing a single
line of code"). Calibration: skip basics, target craft and judgment in
/reflect; move briskly through interviews.

**Notable context:** Returning learner. Project name "WebProbe" already
locked in mentally — directory is `/Users/weiboye/webprobe-project`. The
target application (FIT3047 CakePHP project) is real, owned by the
learner, and provides a built-in evaluation environment. This is a
significant scoping advantage — should surface in `/scope`.

**Energy level:** Engaged, substantive, efficient. Gives compact but
information-dense answers. Doesn't need hand-holding; responds well to
brisk pacing. Match that.

## /scope

**Idea entry state.** Already structured. Trump arrived with a 9-category
detection list, a clear win condition (find a real vuln in FIT3047), and
strong opinions about output ("color-coded terminal + HTML + TXT"). Brain
dump was rich and self-organized — first pass already enumerated the
scope. Reflects /onboard calibration: returning learner who answers in
compact, information-dense blocks.

**How the idea evolved through conversation:**

- *Brain dump:* 9 detection categories + report formats + boolean-SQLi
  curiosity. Established WebProbe's product shape and learning goal.
- *Research / reaction (Wapiti, DalFox, Nuclei):* produced the sharpest
  synthesis of the conversation, articulated unprompted by Trump —
  "Wapiti's scope, DalFox's output philosophy, smaller and fully
  understandable. Every detection module should be readable in under 50
  lines." This **<50-line constraint** ended up being the most useful
  architectural decision of the entire /scope conversation — it doubles
  as a sizing tool *and* a learning-goal enforcer. Carry to /spec.
- *Cut:* 9 categories → 5. Trump made the call cleanly, with a typed
  reason per cut item.
- *Texture round:* produced a concrete severity color scheme
  (RED / YELLOW / CYAN / WHITE / GREY), a sample terminal-finding
  rendering, and a finding-object schema clean enough to lift verbatim
  into /spec.

**Pushback received and how Trump responded:**

- Pushed back on the 9-category scope → cut to 5 with reasons per cut.
- Pushed back on Wapiti as a model → Trump named what was *wrong* with
  Wapiti ("complexity, black-box feel"), which is exactly what produced
  the legibility commitment.
- Pushed back on Nuclei's templating approach → Trump rejected it
  ("becomes a rules-management problem rather than a coding problem").
  Important rejection because it's *why* WebProbe is hand-written Python,
  not a Nuclei template pack. Belongs in /spec rationale.
- Did not push back on the "scan complete, 0 findings" run summary
  suggestion — accepted as PRD-level concern.

**Two craft moments worth flagging in /reflect:**

- *Auth probing cut for operational risk, not just time.* Most learners
  cut auth because it's expensive. Trump cut it because aggressive login
  probing can lock real users out of shared environments. Mature security
  tooling instinct.
- *Directory traversal deferred, not killed*, with reasoning about WAF
  noise and log pollution on shared targets. Distinguished *defer* from
  *cut* explicitly. Both reasoning patterns are stronger than typical
  hackathon scoping discipline.

**References that resonated:**

- DalFox — output philosophy adopted wholesale ("POC URLs you can click
  and immediately verify").
- Wapiti — accepted as scope ancestor, rejected as legibility model.
- Nuclei — accepted modular shape, rejected templating.

**Deepening rounds.** **1 round (texture).** Trump took it deliberately
("let's nail the texture"), and the round produced material that's
unambiguously stronger than skipping it would have been: severity color
palette, sample finding format, finding-object schema, and a sharp
articulation of the "screenshot for reflective diary" usage that
implicitly constrains a lot of UX decisions. The schema in particular
will save real time in /spec — it can be lifted directly. Round paid off.

**Active shaping.**

- Drove the cut entirely — listed v1 categories in priority order with
  one-line cut reasons, unprompted.
- Drove the architectural commitment — the phrase "every detection module
  readable in under 50 lines" was Trump's, not the agent's. This phrase
  ended up framing the rest of the conversation.
- Drove the localhost-as-first-class requirement — explicit in brain
  dump, repeated through the cut. Lock in for /prd.
- Specified the finding schema in their own format with their own field
  naming. Schema was not prompted as a JSON object — Trump surfaced it
  that way themselves.
- Did not drive the references conversation — accepted the three proposed
  references and reacted to them. Appropriate for the research/reaction
  phase; this is where the agent leads.

**Carryover for /prd:**

- *Open:* concurrency model (ReconKit used threading; reuse here?).
- *Open:* HTML report self-contained vs. external CSS — leaning
  self-contained for screenshot / share-ability.
- *Open:* clean-scan summary format (must prove work was done, not just
  announce nothing was found).
- *Open:* failure modes for unreachable targets and mid-scan errors.
- *Open:* CLI surface (`--only`, `--severity-min`, `--cookie`,
  `--output`).

## /prd

**What was added or changed vs scope.md.** The biggest mid-conversation
shift: Trump expanded WebProbe's *ambition* unprompted. /scope framed
it as "tool for me + secondary share use." /prd reframes it as an
open-source community tool with FIT3048 peer-assessment integration as
a first-class feature. That expansion drove a chain of consequences —
self-contained HTML, install-must-be-trivial, BaseModule plugin
architecture, junior-dev-as-second-audience UX bar — that the agent
then surfaced as concrete acceptance criteria. The expansion was real
and well-scoped, not creep.

**Concrete additions on top of /scope:**

- 6 modules in v1, not 5. Path traversal moved from "deferred to v2" →
  "Sprint 1 module 6, opt-in via `--include-traversal`" (see pushback
  notes below).
- BaseModule plugin architecture committed to v1 (signature finalized
  in /spec).
- Framework profiles formalized as module-set + path-list config
  entries. `--cakephp` ships in v1; the *slot* is the contribution
  affordance, not the profile itself.
- FIT3048 peer-assessment 10-category rubric integrated as a
  first-class concern: every finding carries `fit3048_category`,
  `--fit3048` flag groups HTML report by category (two-level grouping,
  category → severity nested).
- Performance NFR pinned: 30s typical, 90s ceiling, 5s per-request,
  `ThreadPoolExecutor(max_workers=20)` only for `paths` module.
- HTML color palette redesigned for white background (different from
  /scope's terminal-tuned RED/YELLOW/CYAN/WHITE/GREY) with rationale
  (yellow unreadable on white, terminal-cyan prints poorly).
- TXT report = ANSI-stripped terminal `=== FINDINGS === / === SUMMARY
  ===` block. Always written alongside HTML.
- New flags: `--include-traversal`, `--fit3048`, `--no-color`,
  `--force-color`, `-v`. Two-level color override (auto via TTY
  detection, with explicit overrides) for the rare-but-real CI
  edge case.
- Filename rule pinned: `webprobe_<host>_<port>_<YYYYMMDD>_
  <HHMMSS>.{html,txt}`, port preserved (CTF/lab targets multiplex
  ports), `_2` suffix on same-second collision.
- Marker convention pinned and reserved: `[*]` progress, `[+]` benign
  status, `[-]` run failure, `[!]` warning/error, `[SEVERITY]`
  reserved for findings.

**Pushback received and how Trump handled it.**

- *Input contract (URL-only / auto-discover / spider).* Picked (b)
  cleanly with rationale per option ("(a) puts too much burden on
  the user; (c) is rabbit-hole risk"). Spider deferred to Sprint 2.
- *Sprint 1 vs Sprint 2 placement of `--cakephp` and `--fit3048`.*
  Agent suggested both might be Sprint 2; Trump kept both in Sprint 1
  with explicit cost analysis ("config and presentation work, not
  detection complexity"). Tied them to the win condition.
- *Path-traversal contradiction with /scope's deferral.* Agent flagged
  it as a contradiction. Trump's response was the strongest scoping
  moment of the conversation: he reversed the deferral with named
  rationale (real demand from FIT3047 wellness app's upload feature,
  detection logic genuinely simple, /scope's concern was operational
  not implementation), AND added a complete mitigation set (opt-in
  flag, exclusion from `--cakephp` profile, banner advertising it as
  off-by-default, HTML report `OPERATIONAL_RISK` header note). Did
  not retreat, did not double down, named what was different and
  addressed the original concern. Mature security-tool judgment.
- *Payload library size.* Pushed on minimal-vs-curated-vs-large.
  Trump's principled answer: "false negatives are worse than no scan
  because they give false confidence." Landed on curated 5–8 per
  attack class.

**Scope guard outcome.**

- *Sprint 1 (kept):* 6 modules + BaseModule plugin arch + 3 output
  sinks + `--cakephp` + `--fit3048` + opt-in traversal + minimal CLI.
- *Sprint 2 (deferred with rationale):* `--django` / `--laravel` /
  `--rails` profiles, authenticated scanning (`--cookie` /
  `--auth-form`), `--severity-min`, `--aggressive` (gates time-based
  SQLi), crawler / multi-URL, contribution docs, CSRF / CORS / open-
  redirect detection.
- The "Sprint 1 vs Sprint 2" framing came from Trump, not the agent.
  He used it before it was prompted. Already thinking in iterations.

**"What if" moments that surprised.**

- The mid-scan failure-modes question. Trump answered it with a
  *complete* error-handling model (try/except per module, inline
  `[!]` line, `MODULES WITH ERRORS` section, summary's `⚠ Partial
  scan` flag, 3-consecutive-failures degradation heuristic) without
  coaching. The "junior dev must never mistake a partial scan for
  a clean target" framing was Trump's, not the agent's.
- The connectivity-check requirement landed naturally — Trump
  immediately specified the success line (HTTP code + duration) and
  the failure line (exit immediately) without prompting.

**Deepening rounds: 1 round (deliberate, all 7 questions).** Trump's
response was decisive: "All 7 deserve real answers, not Open
Questions." The round produced the most concrete material of the
entire /prd: exact CLI syntax, performance NFR with hard ceilings,
complete payload libraries (with content), white-background HTML
color palette with hex values, filename collision rule, verbosity
levels, TTY-detection behavior. /spec will have dramatically less to
invent.

The path-traversal contradiction also surfaced *inside* this round —
which is a clean payoff for the curriculum: deepening rounds catch
ambiguities the mandatory beats wouldn't. Without round 1, path
traversal would have shipped quietly contradicting /scope.

**Active shaping.** This is among the most actively-shaped /prd
conversations a returning learner could produce. Trump drove almost
every architectural decision:

- Drove the open-source-tool framing (unprompted, mid-conversation).
- Drove the BaseModule architecture description, presented as code
  without being asked for code.
- Drove the FIT3048 10-category rubric integration (full category
  list, mapping rule, two-level grouping).
- Drove the inline-tease + end-block output model (model b) with a
  fully-rendered example block in their answer, not a sketch.
- Drove the partial-scan trust-signal framing — "silent partial
  failure is the worst outcome" was Trump's phrasing.
- Drove the curated-medium payload library decision, with the
  "false negatives are worse than no scan" rationale.
- Drove the path-traversal reversal *and* the complete mitigation
  set, after the agent caught the /scope contradiction.

The agent led: surfacing the path-traversal contradiction, framing
the input-contract options (a/b/c), framing the rendering-model
options (a/b/c), and offering the deepening-round choice.

**Carryover for /spec.**

- BaseModule signature finalization (type hints, severity defaults,
  FIT3048 mapping declaration mechanism) — must answer before /spec
  module-architecture section.
- Concurrency confirmation: ThreadPoolExecutor(20) for `paths` only,
  shared-vs-per-thread `requests.Session` decision.
- HTML copy-to-clipboard fallback strategy.
- `--help` text shape including FIT3048 advertisement and "use Burp
  for X" pointer.
- HTML timestamp timezone decision.

## /spec

**Spec-entry state.** Unusually well-prepared. PRD already pinned stack
(requests + bs4 + colorama), CLI surface, payload libraries, color
palettes, performance NFRs, marker convention, filename pattern, FIT3048
integration. /spec's job was confined to (a) confirming/refining 5
inherited open questions and (b) the architectural scaffolding the PRD
deliberately left for /spec — `BaseModule` signature, concurrency
mechanics, file structure, data flow, and the clipboard fallback that
research finding #2 surfaced.

**Decisions made in /spec (not inherited from PRD):**

- *`BaseModule` contract (3 sub-decisions resolved as a unit).*
  - Severity is on `Finding`, not on `BaseModule`. Module-level severity
    would force splitting `paths` into three modules — wrong, since one
    algorithm produces multi-severity output.
  - `fit3048_category` is on `Finding`, not on `BaseModule`. Same
    algebra: `headers` produces both Cat 5 (input validation) and Cat 4
    (session management) from one parse.
  - `session_factory` callable (not `Session` instance) is the module's
    third constructor argument. Threading concerns stay inside the
    factory; modules contain neither thread-locals nor a "shared
    Session" footgun.
- *`run()` is 3-arg with a `report_finding` callback*, not 2-arg
  returning a list. PRD requires inline tease *at moment of detection*.
  Callback chosen over generator — module body reads as straight-line
  imperative; engine wraps callback in stdout lock so threaded modules
  stay thread-naive. Both channels (callback for tease, return list for
  accounting) populated by design.
- *Engine pre-resolves flags into per-module `__init__` config.*
  Trump's call. Engine owns "which modules run with what config";
  modules own "what detection." `--cakephp` becomes a merged
  `path_list` injected into `PathsModule.__init__`. Module bodies never
  see flag state. Same pattern handles Sprint 2 `--aggressive`
  (`SqliModule(include_time_based=True)`) without engine plumbing.
- *One GET, three consumers.* Connectivity check IS the form-discovery
  IS the `Target.base_response` GET. Connectivity = HTTP-layer concern
  (failure → exit 1); form discovery = application-layer concern
  (failure → continue with `forms=[]`). Two distinct error paths, no
  false equivalence. Trump's principled separation — "is the target up?"
  vs "did we find forms?" mapped to two different exit paths.
- *File structure: `webprobe/data/paths/curated.txt`*, not project-root
  `data/`. Trump rejected the project-root suggestion: runtime asset of
  the package (loaded via `importlib.resources`), project root reserved
  for repo-meta. Also caught the future-proofing micro-fix: nest under
  `data/<module>/<asset>` so Sprint 2's `data/xss/payloads_extended.txt`
  has a natural home.
- *Clipboard fallback strategy.* Clipboard API primary, text-selection
  fallback (Selection + Range), **no `execCommand` rung.** Trump
  rejected `execCommand` not as deferral but as principle: deprecated
  API + the realistic risk of v1 reports archived today silently
  breaking in 2027 browsers when `execCommand` is removed. URL flows
  from `a.href` DOM property (not a `data-url` attribute or inline
  string) so the JS layer is immune to Python-side escaping bugs —
  critical because XSS findings produce the worst escape-edge payloads.
- *Flash duration: 1200ms.* Trump's reasoning was unusually crisp:
  1500ms feels viscous on rapid copies, 800ms doesn't survive the
  alt-tab-to-screenshot reflective-diary workflow, 1200ms is the sweet
  spot. Linear timeout, no fade — `textContent` swap is honest, fade
  adds CSS state surface for a 1-button feature.

**`Finding.__post_init__` range assertions** added per Trump's request —
typo (`fit3048_category=11`) blows up at construction rather than
producing a malformed report. Notable that he flagged this as a v1
move with an explicit "revisit if module count crosses ~15"
sunset condition (where a typed enum would earn its keep).

**What was confident vs uncertain.**

Trump was confident on essentially everything:
- Stack (rejected `urllib`, principled `requests` rationale unprompted).
- Severity / category / session model (independently arrived at the
  same three answers as the agent's proposal, with extra reasoning).
- Clipboard fallback (immediately ruled out `execCommand` on
  long-archive-lifetime grounds the agent had not yet articulated).
- Engine-pre-resolves-flags model (raised it as the next question
  himself, without prompting).

Trump was *not* uncertain — but deliberately deferred:
- SQLi boolean-differential threshold ("configurable, default at /build").
- Error-categorization specifics ("checklist task descriptions").
- Banner exact text + `--help` text + verbose line format
  ("string-level work, belongs in /build").

This deferral discipline is the same instinct that produced /scope's
"defer ≠ kill" framing for traversal. Mature spec-vs-build line.

**Pushback received and how Trump handled it.**

- *Project-root `data/` for "obvious contributability".* Rejected with
  three-clause reasoning (runtime asset, repo-meta separation, README
  pointer is a one-line fix). Counter-proposed
  `webprobe/data/paths/curated.txt` (deeper nest, future-proof).
- *Connectivity HEAD vs GET.* Agent surfaced "could form-discovery
  parse failure masquerade as connectivity failure?" as the failure
  case. Trump answered with a complete two-phase model — HTTP-layer
  failures during the request → exit(1); parse failures after the
  response arrives → log warning, continue with `forms=[]`. Decoupled
  the two failure modes by their *layer*, not by re-fetching.
- *(Implicit) keep `execCommand` as a fallback rung for legacy parity.*
  Rejected. The "deprecated API silently breaking in archived reports"
  scenario is the long-lived-correctness argument, not a mere
  preference. Trump made the argument without coaching.

**Deepening rounds: zero.** Trump declined explicit rounds — but the
mandatory beats themselves did the work of a deepening round. Each
beat surfaced a proposal with 2-3 deliberately-flagged sub-decisions;
Trump confirmed, refined, or counter-proposed on each. The
mandatory-beats-as-deepening-rounds shape is unique to this spec —
because the PRD pre-resolved most of the ambiguity that mandatory
beats usually surface.

This is consistent with /prd's payoff: deep PRD → leaner /spec
conversation. The agent had less to invent because Trump already had.

**Active shaping.** As actively shaped as a returning learner can be.
Trump drove:
- The `requests`-vs-`urllib` decision with workload-shape reasoning.
- The `__post_init__` assertion micro-improvement on the contract.
- The flag-handling model raised as an "adjacent question" before the
  agent prompted it.
- The `webprobe/data/paths/` rename catching a future-proofing concern.
- The connectivity-vs-discovery layer separation.
- The `execCommand` rejection on long-archive-lifetime grounds.
- The 1200ms flash duration with a multi-clause UX rationale.
- The explicit spec-vs-build line ("don't pin the threshold, just say
  configurable") — the kind of judgment normally invisible at /spec.

The agent led: surfacing the `requests.Session` thread-safety footgun
via research, surfacing the `file://` clipboard secure-context issue
via research, framing the `(a)/(b)/(c)` clipboard strategies, the
3-arg-vs-2-arg `run()` contract refinement, and the
mandatory-beats sequencing.

**Spec → /build line, made explicit.** Trump articulated the spec's
job as *"an LLM agent could implement this without making arbitrary
choices about architecture"* — not *"every literal constant is fixed."*
This framing produced clean deferrals to /checklist:
- SQLi threshold → /build pins a default.
- Module-error tips → default + targeted enhancements optional.
- Banner / `--help` / verbose format strings → /build.
- HTML report timestamp timezone → resolved (local + TZ suffix), but
  reachable for /build refinement.

**Carryover for /checklist.**
- Walk down the spec's section list and produce one checklist item per
  granular subsection (the spec was written with /checklist
  addressability in mind — every subsection is a candidate item).
- Decide build mode (step-by-step vs autonomous) up front; PRD's
  prior /reflect quiz can target this judgment.
- Pre-build verification: `BaseModule` contract test (instantiate every
  module class, dispatch a no-op `Target`, assert no exceptions) is
  worth its own checklist item.
- The 50-line constraint is a *checklist verification step*, not a
  build-time aspiration. Each module's checklist item should include
  a `wc -l` check.

## /checklist

**Checklist-entry state.** Spec was unusually checklist-addressable —
every subsection had been written with a /checklist item in mind.
Trump's spec carryover already named the sequencing primitives (vertical
slice, 50-line audit as verification step, BaseModule contract test as
its own item). This /checklist conversation was correspondingly leaner
than typical: two substantive questions (sequencing logic, build mode),
one targeted edit, no deepening rounds requested.

**Sequencing — picked (b) vertical slice with five-clause rationale.**
Trump rejected "skeleton-then-modules" (option a) on integration-risk
grounds: WebProbe's 6-module + cross-cutting-contract surface (callback
signature, session_factory, base_response sharing, stdout lock) is
substantially larger than ReconKit's 3-module surface, so the
"contract-mismatch surfaces as 6 simultaneous bugs at hour 4" failure
mode is real here even though it wasn't in ReconKit. Picked headers as
the first detection module (passive, declarative, exercises
one-GET-three-consumers) and paths last among detection modules
(tightest line budget, only concurrent module, importlib.resources
loading better understood with reference modules in view).

The five-slice + 21-item proposal Trump produced was already 90% of the
final checklist. Agent's job: consolidate where genuinely cohesive
(colors+terminal → item 5; engine+probe.py → item 7; curated.txt+paths
→ item 12), fold in error-handling distribution as inline beats inside
affected items, surface latent dependencies (engine STUB at item 7
needing cleanup at items 13/14), and add the Devpost item.

**Build mode — autonomous with three named checkpoints.** Trump locked
this in with a fourth supporting reason the agent hadn't articulated:
distributed error-handling only works under autonomous mode because
step-by-step would force the agent to re-discover the cross-cutting
structure on every error-handling beat. Counterargument (defending
build-time decisions in conversation) was correctly dismissed —
everything worth defending was already deferred to /build with reasoned
defaults at /spec.

The three checkpoints are explicit verification beats:
- A (after item 7): vertical slice runs against example.com — banner,
  connectivity, headers findings, FINDINGS block, summary all render.
- B (after item 12): `wc -l webprobe/modules/*.py` audit; >50 triggers
  `_<name>_helpers.py` extraction.
- C (after item 15): HTML report manual-test in **both Firefox and
  Chrome** via `file://` (Firefox = required fallback validation,
  Chrome = bonus signal); --fit3048 grouping; --include-traversal chip;
  TXT companion file.

**Item count and timing.** 18 items × ~15 min ≈ 4.5 hr. Above the
3–4 hr PRD bound, but Trump set this estimate himself and accepted it.
Each item is genuinely atomic; the largest two (item 7 engine+CLI,
item 13 HTML output) are cohesive work units that resist further
splitting without artificial seams.

**Confidence vs deferral.** Same instinct as /spec — Trump confident on
sequencing, mode, checkpoint structure; deliberately deferred to /build
on the SQLi differential threshold (30% pinned as default with
auditable constant), banner/help text strings, error-tip wording. Spec/
build line preserved.

**Pushback received and how Trump handled it.**
- *Deepening rounds offer.* Declined deliberately, with one-line
  rationales per offered target showing he understood each tradeoff.
  Articulated the principle directly: "the checklist's job is *an LLM
  agent could execute this without ambiguity about what counts as
  done* — not *every keystroke pre-determined*." Same false-precision
  resistance that landed at /spec for SQLi threshold. Mature
  checklist-vs-build line.
- *One correction accepted.* Checkpoint C originally said "test in
  Firefox via file://" — Trump replaced it with explicit Firefox +
  Chrome scoping plus the architectural reason: a build agent
  defaulting to Chrome (the Mac dev default) would never exercise the
  text-selection fallback the architecture was designed for. Caught
  the exact scenario the research surfaced. This kind of "make the
  test exercise the right code path, not just the obvious one" edit
  is the cybersecurity instinct showing through.

**Two risks observed and named, not eliminated.**
1. Items 9/10 (sqli, xss) cannot be semantically validated until item
   17 (FIT3047 e2e). Loop-back protocol named in build-agent notes:
   re-open affected item and patch.
2. Item 7's engine STUB for HTML/TXT writing must be cleanly replaced
   at items 13/14. Annotated as STUB in item 7's What-to-build.
Both risks have explicit recovery paths. Trump's framing: "observed,
named, and have explicit recovery paths — that's exactly what you want
pre-build, not eliminated."

**Active shaping.** This was the most actively-shaped /checklist
conversation a returning learner could produce. Trump drove:
- Sequencing logic with five-clause rationale before the agent's
  recommendation landed.
- Headers-first vs paths-last reasoning, both directions justified
  separately.
- Two non-negotiable checkpoints (50-line audit, file:// browser
  manual-test) baked into items.
- Two specific risk mitigations (paths.py 50-line extraction rule,
  HTML clipboard "DO NOT WRAP" inline comment) baked into items.
- Build-mode lock-in with the fourth supporting reason
  (error-handling distribution only works under autonomous).
- The Checkpoint C correction, with the architectural reason
  inline.
- Refusal of deepening rounds with per-target tradeoff articulation.

The agent led: surfacing the engine-STUB latent dependency at item 7,
proposing the consolidations (5+6, 8+9, 14+15), surfacing the
items-9/10-can't-be-validated-until-17 risk, the deepening-round
offer (declined).

**Carryover for /build.**
- Build agent should respect the three checkpoints literally — do not
  proceed past A/B/C without explicit "go."
- The 50-line audit at Checkpoint B is non-negotiable. If any module
  > 50 lines, extract `_<name>_helpers.py` before continuing — do not
  ask whether to relax the rule.
- Browser scoping for Checkpoint C: Firefox is the *required* test
  case (validates fallback). Chrome is a bonus signal, not a
  prerequisite.
- Items 9/10 will likely require iteration after item 17. Don't treat
  the first FIT3047 run as final acceptance — the loop is named.
- The `<a>` + `<button>` "DO NOT WRAP" inline HTML comment in item 13
  is critical: clipboard JS depends on `previousElementSibling`. If
  any wrapping seems convenient during HTML rendering, resist it.

## /build

**Build mode:** Autonomous with three named checkpoints (A after item 7,
B after item 12, C after item 15). 18 items planned, 18 complete. No
revisions to the checklist mid-build — the plan held end-to-end.

**Total items completed:** 18 of 18.

**Commits:** 19 commits on master, conventional-commits style. One
`chore:` (item 1 scaffolding), eleven `feat:` (items 2–6, 8–15), one
`docs:` (item 16 README), one `fix:` (item 7 follow-up: `python3
webprobe/probe.py` direct invocation needed a `sys.path` shim — the
spec/PRD's install line wouldn't have worked without it), and a small
docs commit marking checklist progress at Checkpoint A.

**Checkpoint observations:**

- *A (after item 7).* Vertical slice ran clean against `http://example.com`
  on first try — banner / connectivity / headers tease lines / FINDINGS
  block / summary all rendered with right markers. One mid-checkpoint
  fix: subagent had only made `python3 -m webprobe.probe` work, but the
  spec acceptance is `python3 webprobe/probe.py <target>`. Fixed in
  `d6db320` with a 3-line `sys.path.insert` shim. Worth flagging because
  the underlying issue (Python's import system + script-vs-module
  invocation) recurs in any package-shaped CLI without an entry point —
  the shim is the lowest-friction fix; a `pyproject.toml` console_scripts
  entry would be the proper Sprint 2 move.

- *B (after item 12).* 50-line audit across all 6 detection modules:
  headers=49, info_disclosure=49, paths=46, sqli=47, xss=43,
  traversal=50. Every module under the cap. Helper extraction (the
  `_<name>_helpers.py` carryover anticipated in /spec) was needed for
  sqli, xss, traversal, paths — that pattern landed cleanly. A bonus:
  during item 10 (xss), `_common.py` was extracted to host
  `build_units(target)` and `send(...)` because three modules
  (sqli/xss/traversal) shared the same per-param HTTP work. That
  refactor was the right call — three uses justify the abstraction —
  and validated retroactively when traversal landed at item 11 with no
  duplication. The "engine OR's `getattr(module, 'degraded', False)`
  into `args.partial`" convention also held across all four
  HTTP-issuing modules without churn.

- *C (after item 15).* Manual file:// browser test on the HTML report
  passed in both Firefox and Chrome. The text-selection fallback
  (Selection + Range API, no execCommand) fired correctly when
  navigator.clipboard.writeText silently failed in Firefox's
  insecure-context handling. Three demo HTML reports were generated
  (default severity grouping with OPERATIONAL_RISK chip + partial
  banner, fit3048 grouping, and the live example.com run) — structural
  assertions all passed: 3 DO NOT WRAP comments per report, 3
  `</a><button class="copy-btn"` direct-sibling matches, 1200ms flash
  timeout, zero `execCommand` occurrences, html.escape applied to all
  dynamic strings.

**Item 17 — win condition met without a △1 loop-back.** Trump ran the
scanner himself against my FIT3047 team's CakePHP project at
`https://your-project.local/users/login` (see
`screenshots/webprobe_your-project.local_443_20260428_014210.html`).

- 11 findings: 0 CRITICAL, 2 HIGH (csrfToken missing Secure; HSTS
  missing), 5 MEDIUM (CSP/X-Frame-Options missing; /cpanel,
  /.htaccess, /.htpasswd exposed), 4 LOW. 6 modules scheduled, 6
  completed, 0 errored, 11.8s.
- The /cpanel + /.htaccess + /.htpasswd findings are the unknown-unknown
  the win condition required — deployment-environment defaults from
  cPanel/Apache that Trump did not previously know were exposed. PRD
  win condition met.
- sqli/xss producing zero findings was diagnosed as adequate defense
  quality, not a calibration miss: my FIT3047 team's stack uses CakePHP 5
  ORM (parameterised queries by default) + `h()` auto-escaping +
  FormHelper CSRF tokens. Detector silence on a defended login form is
  the detector telling the truth. Trump explicitly declined to lower
  `DIFF_THRESHOLD` from 0.30 to 0.15 — that would manufacture false
  positives without specific knowledge of a missed defect, and the
  spec carryover loop-back protocol was scoped to known-vulnerability
  cases.
- The two HIGH findings (csrfToken Secure flag, HSTS) are genuinely
  actionable items being routed to my FIT3047 team's Iteration 2 backlog
  separate from this build. WebProbe produced security work, not just
  a screenshot.

**Item 18 scope reduction.** Devpost dropped per the README reframe at
item 16 (coursework helper, not hackathon project). GitHub push handled
out-of-band (private repo as canonical artifact). Item ticked with the
scope reduction noted in the checklist body so /reflect can pick it up.

**Cross-cutting build observations:**

- *50-line constraint as verification step, not aspiration.* It worked
  exactly as Trump framed it at /spec → /checklist. Every module
  landed at or under 50 lines on the first build attempt; helper
  extraction caught the two cases (sqli at 62-ish initially, paths at
  similar) that needed structural relief. No item required relaxing
  the rule.
- *Distributed error handling under autonomous mode.* The decision at
  /checklist that the per-module 3-consecutive-failure tracker
  belonged inside affected items rather than as a cross-cutting
  reliability sub-slice paid off — every module that landed it (sqli,
  xss, traversal, paths) got the tracker right on first try because
  the surrounding context was fresh. Confirms /checklist's
  `Active shaping` note about the fourth supporting reason for
  autonomous mode.
- *`<a>` + `<button>` "DO NOT WRAP" guard held.* The inline HTML
  comment was honored verbatim in item 13's render, the JS read
  `previousElementSibling` correctly, and the manual browser test
  exercised exactly the fragile path the constraint was designed to
  protect.
- *Spec-vs-build line preserved.* Three deferrals from /spec landed
  at /build with reasoned defaults: SQLi DIFF_THRESHOLD = 0.30 (named
  constant in `_sqli_helpers.py`, auditable for FIT3047 calibration);
  module-error tip = generic "re-run with -v"; verbose `[.]` line
  emission in paths.py = explicitly skipped at item 15 with the
  rationale recorded ("string-level deferral, can be re-opened").
- *Build duration vs estimate.* /checklist estimated 4.5 hours.
  Actual was longer — autonomous mode + subagent dispatch overhead
  + the manual browser test at Checkpoint C extended wall-clock,
  but every item landed in one pass without rebuild loops. The
  3-checkpoint structure was right-sized: enough granularity to
  catch problems early, not so much it stalled momentum.

**Carryover for /reflect:**

- My FIT3047 team's audit is a real artifact, not a demo. Two HIGH
  findings + three MEDIUM path exposures will inform Iteration 2
  remediation work.
- The `python3 webprobe/probe.py <target>` UX — fixed by sys.path
  shim — is functional but ugly; a `pyproject.toml` console_scripts
  entry is the right Sprint 2 polish.
- sqli's DIFF_THRESHOLD = 0.30 was never calibrated against a
  known-vulnerable target. If a future FIT3047 audit surfaces a
  known SQLi that WebProbe missed, the threshold is the first
  variable to revisit.
- The `_common.py` extraction (item 10) is the kind of refactor
  that Sprint 2 should formalise — when authenticated scanning
  lands, the `send()` helper will need a `cookies=` parameter,
  and having all three HTTP-issuing modules go through one
  function is the right place to add it.

## Sprint 2 — /scope

**Entry state.** Trump arrived with `docs/sprint-2/scope-input.md`:
30 candidate items in 6 groups, an explicit ask for pushback on
scope ("expecting /scope to recommend splitting"), two locked
architectural decisions (multi-URL = A+B not spider; template
system MUST be in roadmap), and two explicit "don't relitigate"
guardrails (architecture, workflow). The scope-input.md served
as the brain dump — the Phase-1 brain-dump beat was skipped
entirely. Research/reaction beat was also skipped (wrong phase
for a going-deeper sprint; Sprint 1's references still apply).

**Conversation shape.** Three sharpening questions in mandatory
beats, two deepening rounds requested (α and β), one inline-
answered (γ). Total: 4 substantive exchanges to land a 14-item
sprint with falsifiable win condition, two-endpoint structure,
and concrete acceptance image. Materially leaner than Sprint 1's
/scope conversation; consistent with returning-learner
calibration that landed at /onboard.

**Q1 — win condition.** Trump picked (A) authenticated-scanning
win unprompted with full falsifiable form ("Coach A reaches
Coach B's resource OR provable-silence SCAN COVERAGE block").
The dual shape (find-or-provably-clean) is the most important
single contribution of the entire conversation — it makes
Sprint 2 land even when FIT3047 Iteration 2 is genuinely
secure, by treating "scanner exercised the right pages with
the right session and reports cleanly" as positive evidence.
The "evolving alongside Iteration 2 of FIT3047" framing
(Sprint 2 strengthens the system it's meant to audit, not a
parallel hobby project) was Trump's, unprompted.

**Q2 — single-vs-multi-session auth contract.** Agent presented
3 options (a/b/c). Trump picked (c) — but the contract design he
returned was substantially better than the (c) option as
presented. The "list-always with `sessions[0]` default" pattern
unifies what (c) had as a parallel-contract split: 5/6 modules
remain identical to v1 (`s = session_factory()[0]` is one line,
no conditional), IDOR is the only multi-session consumer, and
the INFO finding when `--idor-baseline` is missing prevents
silent capability degradation. This is the "no false confidence"
discipline from Sprint 1's partial-scan signaling carried into
the IDOR contract. Agent's contribution was framing the fork
and noting the 80/20 module split; Trump's was the unified
shape that resolved (b) vs (c) as a presentation problem
rather than structural.

**Q3 — testbed + brute_force + execution-evidence (bundled).**
Agent surfaced three entangled concerns: (1) Sprint 2 modules
have near-zero true-positive rate against hardened targets,
breaking the "FIT3047 = win-condition validator AND module
validator" Sprint 1 luxury; (2) brute_force's lockout risk
hadn't been answered (re-raises Sprint 1 /scope's auth-probing
cut); (3) "provable silence" in the win condition is doing
unnamed engineering work. Trump returned three crisp answers:
(c) self-contained testbed (`webprobe/testbed/` Flask app with
deliberately-broken endpoints, doubles as cohort-install sanity
check), (i)+(ii) testbed-default + double-flag opt-in for
brute_force (`--include-brute-force` requires partner
`--i-own-this-target` — friction-as-feature, forcing the user
to type a sentence asserting ownership), and a new SCAN COVERAGE
output block as P0 (not P1) because it's half the win condition.

The double-flag pattern is Trump's strongest single design
moment in this conversation — `--include-traversal` from v1
was a single-flag opt-in, but brute_force's asymmetric
operational consequence (lockout vs log pollution) earned a
higher friction barrier. The `--i-own-this-target` flag exists
purely to force a typed assertion; nothing about its semantics
adds technical capability. The "testbed-default" guard means
brute_force on real targets is impossible without two
deliberate, non-overlapping opt-ins — a Sprint 1 mature-
security-tooling-instinct moment carried forward.

**Deepening rounds.**

- **Round α (acceptance moment).** Trump volunteered the full
  concrete terminal output with 5 things it pins (auth_context
  field, COVERAGE-as-section, `idor-baseline-missing` INFO
  beside HIGHs, heavy command-line shape, two-tier finding
  architecture). Agent's two questions in this round (Q-α-1
  flag shape, Q-α-2 form auto-discovery) were both pre-
  answered in his framing, which is the highest signal of
  good-conversation-as-spec-input. The acceptance image is
  the literal acceptance test for Sprint 2's output-renderer
  items — same role Sprint 1's `[HIGH] Reflected XSS` block
  played for items 5 and 13.

- **Round β (sprint endpoint shape).** Trump proposed the
  two-endpoint structure (A engineering-complete, B win-pinned,
  externally-gated). Agent confirmed and added the max-gap
  fallback (~2 weeks; if Iteration 2 hasn't deployed, validate
  against testbed + secondary target, declare provisionally-won,
  re-run when available). The two-endpoint shape resolves a
  real Sprint 2 risk (externally-gated win could float
  indefinitely) without coupling engineering doneness to
  Team 157 deployment timeline. v2.0.0 release tag fires at
  Endpoint B; optional v2.0.0-rc.1 at Endpoint A for cohort
  users who clone between the two.

- **Round γ (cohort-canonical thread, answered inline).**
  Trump correctly drew the line between "Sprint 2 ships the
  shape that makes cohort adoption possible" (in scope) and
  "another team actually adopts it" (Sprint 3+ outcome).
  The scope.md framing dropped "canonical cohort security
  tool" in favor of "auth-aware web scanner usable for
  FIT3047/FIT3048 work, hardened against Team 157's
  deployment as the canonical test target" — direction
  preserved, outcome scoped to single-team.

**Final cut: 14 items, ~13-16 hrs build.**

- P0 (10 items, ~10-12 hrs): 1, 2 (with auto-discovery),
  3 (multi-session contract), 3.5 (testbed — NEW), 3.6
  (SCAN COVERAGE — NEW), 4, 5, 6, 8, 23
- P1 (6 items, ~3-4 hrs): 7 (brute_force, double-flag gated),
  9, 18, 26, 27, 28
- Stretch (~30 min): `--export-md` mini

Net additions to scope-input.md baseline: +1.5 hrs (testbed),
+0.5 hrs (SCAN COVERAGE block), +30 min (`--auth-form` field
auto-discovery). All three are win-condition-load-bearing.

**Cuts to Sprint 3 (with reasons):**
- Items 10-17 (general detection expansion) — valuable, none
  auth-related, dilutes Sprint 2's focused thread
- Items 19-22 (full template system) — largest engineering
  effort, not on auth-win critical path, `--export-md` mini
  in stretch ships the shape Sprint 3 grows from
- Item 24 (full README revision) — Sprint 2 README updates
  scoped to v2 features only
- Item 25 (pytest suite) — testbed serves as manual
  integration-test harness for Sprint 2; pytest automation
  is Sprint 3 work

**Pushback received and how Trump handled it.**
- Single-vs-multi-session fork: agent presented (a)/(b)/(c)
  with tradeoffs; Trump picked (c) and improved on its
  contract design (list-always default len 1).
- Test-bed reality concern: agent framed as four options;
  Trump picked (c) self-contained testbed with five-clause
  rationale (rejected juice-shop on response-shape grounds,
  rejected FIT3047-dev on team-buy-in grounds, rejected
  no-testbed on TDD-signal grounds, picked self-contained
  on permanence + cohort-install-sanity-check grounds).
- brute_force operational risk: agent surfaced the Sprint 1
  /scope contradiction; Trump returned the double-flag
  pattern that explicitly preserves the original concern.
- Cohort-canonical framing: agent flagged the "canonical
  cohort tool" → "Team-157-only win" gap; Trump confirmed
  it was framing language, not commitment, and answered
  the round inline rather than burning a deepening round
  on it.

**Active shaping.** As actively-shaped as Sprint 1's /scope,
maybe more so. Trump drove:
- Win condition selection AND the dual-shape (find-or-
  provably-clean) refinement
- The unified list-always session_factory shape
- The double-flag `--include-brute-force` +
  `--i-own-this-target` pattern
- The two-endpoint structure with v2.0.0 release at B
- The concrete acceptance terminal output (5 things-it-
  pins came from his framing, not the agent's)
- The cohort-canonical scope correction (inline-answered γ)
- The Sprint 3 cut list with per-item reasoning

Agent led:
- Q1 framing (4 win-condition shapes for selection)
- Q2 framing (single-vs-multi session as a/b/c)
- Q3 bundling (testbed + brute_force + evidence as one
  entangled cluster)
- Round-α/β/γ offer with target descriptions
- Max-gap fallback addition to two-endpoint structure
- ZAP/Burp Authenticator references for v2 inspiration

**Calibration notes for /sprint-2/prd:**
- Trump enters /prd with the spec-vs-build line already
  internalized. Don't re-argue defaults that have a
  reasoned default + reopen-condition.
- Multi-session contract is locked at /scope; /prd should
  not relitigate the auth-flow shape, only refine the CLI
  surface and acceptance criteria.
- Five "things this acceptance image pins" from round α
  are direct /prd → /spec carryover. Don't lose them.
- Open questions explicitly carried to /prd: combined
  unauth-and-auth scan default behavior, module-fire
  ordering with auth, sitemap+robots interaction with
  auth, JSON schema versioning, banner/help text.
- Two-endpoint structure with max-gap fallback should
  appear in /prd's acceptance-criteria section, not just
  /scope's "Done" section.

**Risks observed and named, not eliminated.**
1. Endpoint B externally-gated by Team 157 Iteration 2
   deployment. Max-gap fallback (~2 weeks → testbed +
   secondary target validation, provisionally-won) is the
   recovery path. Not a /build concern; a Sprint-2-as-a-
   whole concern.
2. Auth-detection modules' near-zero true-positive rate
   against hardened targets. Testbed (item 3.5) is the
   recovery path — modules get validated against known-
   vulnerable endpoints before shipping.
3. Sprint 2 build estimate (13-16 hrs) is 2-2.5x Sprint 1.
   Two named recovery paths: P1 cuts (drop items 7, 9, 18,
   26-28 in priority order if hitting hour 12 with P0
   incomplete); stretch item is explicitly "skip if tight."
   Trump set this estimate himself with eyes open.

All three risks have explicit recovery paths, matching the
Sprint 1 /checklist pattern: observed, named, recoverable.

**Carryover for /sprint-2/prd:**
- Acceptance moment terminal output → lift verbatim into
  /prd as the canonical Sprint 2 acceptance test.
- Multi-session contract (list-always, default len 1, IDOR
  is sole consumer) → carry to /spec without modification.
- Double-flag brute_force gate → carry to /spec, may need a
  one-line opt-in confirmation prompt during scan setup.
- SCAN COVERAGE block as structural section → /spec decides
  whether new `output/coverage.py` module or extension to
  `terminal.py`/`html.py`.
- `Finding` dataclass extensions (`auth_context`,
  `baseline_context`) — both `Optional[str]`, both `None`
  for v1-shape findings, preserves backward compatibility.
- Two-endpoint structure with max-gap fallback → /prd's
  acceptance-criteria section.

## Sprint 2 — /prd

**Entry state.** /scope was unusually deep: multi-session contract,
double-flag brute_force, testbed, SCAN COVERAGE block as P0,
two-endpoint Done structure, literal acceptance terminal output, and
five "things-it-pins" already carried verbatim into the brief. Five
explicit open questions handed off from /scope (combined unauth+auth
scan default, module-fire ordering, sitemap/robots-with-auth, JSON
schema versioning, banner/help text). PRD's mandate: formalize user
stories, resolve the five opens, surface auth-specific edge cases.

**Conversation shape.** Five mandatory beats (the five scope-opens
restructured into Q1-Q5), then pivot to formalized epics with full
user stories + acceptance criteria epic-by-epic. Trump declined
deepening rounds — the depth happened during the epic walks instead.
Each epic close-out involved 1-11 inline edge resolutions; Trump
answered all with reasoning depth roughly proportional to risk
class (highest density on Risk Gates and Module Contract). 7 epics,
~40 stories, ~75 inline edges resolved.

**Five scope-opens resolved:**
- *Q1 combined unauth+auth scans:* Trump returned `auth_strategy`
  field on BaseModule (`unauth_always` / `follow` / `auth_required`),
  with `--scan-both` for explicit double-pass. Refined "follow"
  semantic mid-conversation: "follow" means "unauth by default; if
  --scan-both is also set, run a second time with session attached"
  — NOT auto-switch when --auth-form is provided. This refinement
  preserved the 47-req acceptance image budget.
- *Q2 module-fire ordering:* α ordering (all v1 unauth → login →
  auth modules), throwaway sub-session for `session` module,
  back-to-back per-module --scan-both ordering for debuggability.
- *Q3 sitemap/robots/auth:* Tagged URL pool with per-module
  `source_filter` parallel to `auth_strategy` — same declare-and-
  dispatch contract pattern. Fail-loud on auth-gated sitemap with
  302→login detection (not just 401). Wildcard trim + INFO finding.
- *Q4 JSON schema:* Versioned envelope (v2.0), semver rules locked
  (MAJOR/MINOR/PATCH bump triggers), always-present-null field
  stability, engine-side --scan-both dedup with
  `seen_in: ["unauth", "authed"]`, evidence_hash as identity tuple.
- *Q5 banner/help:* Defer wording to /build, but pin `--help` flag
  taxonomy (5 categories) in /prd as source of truth that doubles
  as epic spine. OPERATIONAL_RISK chip extension to v2 (gated
  module enumeration + gate flag audit trail) pinned in /prd, not
  deferred.

**Six design patterns that emerged this sprint** (Trump asked these
be surfaced for /reflect and Sprint 3 propagation):

1. **`capability-axis-single-helper`** (Story 6.5.E1). When extending
   a helper to cover a new variation of the same capability, extend
   the existing helper file with a backward-compatible signature
   change rather than splitting into a parallel helper. Splitting
   encodes implementation history as a permanent file boundary;
   future readers can't infer "why does X use _common but Y uses
   _auth_common" beyond "because of when each was added."
2. **`friction-as-binding`** (Story 5.5.E1). When a flag's purpose is
   authorization assertion, value-taking-with-validation
   (`--i-own-this-target=<hostname>` matching target) is dominant
   over bare-flag-with-typed-name. Bare flag decouples assertion
   from target identity (wrapper script can hardcode it forever);
   value-taking with target-match auto-invalidates on target
   change. Friction without binding is security theater.
3. **`no-false-alarm vs no-false-confidence`** (Story 7.1.E2). Two
   distinct disciplines, both required: (a) don't claim coverage
   you didn't achieve → INFO finding documenting the gap; (b)
   don't claim findings you can't confirm → skip emission, document
   in COVERAGE summary. False alarms erode scanner trust faster than
   missed findings; the pair gives the scanner an honest voice in
   both directions.
4. **`owner=epic-that-declares-the-dataclass`** (Q1+(c) decision).
   When a field touches multiple epics (Authentication generates,
   Output renders), the epic that *declares the dataclass*
   (Module Contract) owns it. Forward-compatible rule for future
   Finding extensions (`confidence_score`, `cwe_id`, `related_cve`).
5. **`miss-this-scan-hint-for-next-scan`** (Story 2.5.E1). When the
   scanner detects something out of pool that it cannot probe in
   this scan, emit INFO with explicit upgrade hint for next scan
   ("redirect target /dashboard not in URL pool; consider --url-list
   for full coverage in next scan"). Honest about capability gaps,
   actionable rather than silent.
6. **`Sprint-3-promise-as-INFO-text-for-auto-carryover`** (Story
   2.1.E1). When a feature is deferred but the deferral has a known
   trigger condition, embed the future-flag promise into the INFO
   finding text the user sees: "Sprint 3 will add --sitemap-cap <N>
   for explicit override." This makes the carryover automatic
   (becomes Sprint 3 /scope input) and informs the user during
   v2 use that the gap is acknowledged. Counter-pattern to the more
   common "PRD lists deferrals; user discovers gaps cold."

**Two patterns extending Sprint 1 disciplines:**

- **`empirical-validation-before-escape-hatch`** (Story 1.1.E2 lock).
  `--auth-user-field` / `--auth-pass-field` deferred until the
  auto-discovery field-name heuristic is validated against ≥3 real
  testbeds. Tightens the usual "ship the flag, then see" pattern —
  forces empirical observation before adding speculative flexibility.
- **`audit-trail-records-user-typed-form-not-normalized`** (Story
  3.4 + 5.5). `risk_gates_asserted` records exactly what user typed
  (case preserved, no normalization). Audit trail's purpose is
  evidence-of-action; normalization discards evidence.

**Pushback received and how Trump handled it.**

- *Q1 (a)/(b)/(c)/(d) framing:* picked (d) and refined into a
  per-module declarative system. The agent's options were
  presentation-axis splits; Trump returned a contract design that
  unified them. Same pattern as scope's Q2 (single-vs-multi
  session — agent presented (a)/(b)/(c), Trump returned a unified
  shape that resolved (b)/(c) as presentation problem, not
  structural).
- *"follow" auto-switching ambiguity (Q1 self-correction):* Trump
  caught an ambiguity in his own Q1 answer. The agent didn't notice
  initially. The clarification ("follow" does NOT mean auto-switch;
  it means unauth-by-default with --scan-both for second pass)
  preserved the 47-req acceptance image as a live constraint.
- *Epic 6 fold vs split (a):* agent proposed 6 epics with detection
  modules folded into Module Contract; Trump split to 7 epics on
  atomicity-over-symmetry grounds. Each epic must be an independently
  closeable unit — Module Contract closes when contract works
  end-to-end with a dummy module; module stories close
  independently. Atomicity wins.
- *--severity-min status (Epic 4):* agent surfaced as ambiguity;
  Trump cut from Sprint 2 with rationale (consumer-side concern;
  Sprint 3 templates handle it; `jq` solves ad-hoc).
- *Epic 5 csrf gating (Story 7.3.E1):* Trump elevated csrf to
  --i-own-this-target-gated mid-Epic-7. State-mutating risk is
  structurally equivalent to brute_force's lockout risk — Q5(b)'s
  initial framing missed this; Trump caught and corrected by
  retroactively updating Epic 5 stories rather than treating as
  Epic 7-local concern. Cross-epic correction handled cleanly.
- *Mode enum proliferation (Story 3.1.E2):* agent suggested
  "Cookie-attached, dual-session" variant; Trump locked Mode to
  exactly 4 values with explicit reasoning ("Mode is taxonomy, not
  provenance; auth_context carries provenance at finding-level").
  Avoided enum proliferation that would propagate into JSON schema.

**"What if" moments that surprised the agent.**

- *Story 1.3.E1 same-user IDOR false-negative.* The catastrophic
  silent-failure shape ("looks secure, is untested") wasn't visible
  until agent explicitly framed the question. Trump's named-cookie
  comparison detection (PHPSESSID, laravel_session, etc.) is a
  mature security-tool detection pattern.
- *Story 5.4.E1 testbed detection.* Agent's instinct was simple
  host+port match; Trump escalated to dedicated `/__webprobe_testbed__/
  health` endpoint with multi-field validation. The longer-term
  failure (developer running CakePHP dev on port 9999, gates
  silently bypassed, brute_force hammers the dev server) was the
  exact OPERATIONAL_RISK gates exist to prevent. +1 HTTP request
  cost = negligible against safety guarantee.
- *Story 7.4.E1 stack-trace observation.* Agent proposed shared
  response cache (cross-cutting); Trump rejected on architectural
  grounds (breaks Story 6.3's frozen-pool pattern, introduces
  grow-only mutable engine state, recurring "read from cache or
  fetch fresh" cognitive tax on every future module). Trump's
  alternative: error_leakage makes its own curated probe set.
  Active detection > passive observation.

**Active shaping.** As actively-shaped as Sprint 1's /prd, possibly
more so. Trump drove:

- The `auth_strategy` declarative class-attribute pattern from Q1
  (agent had presented imperative-flag-conditional options).
- The `source_filter` pattern in Q3, parallel to `auth_strategy`,
  unifying the contract design.
- The semver rules in Q4 with explicit MAJOR/MINOR/PATCH triggers,
  forcing forward-compatible JSON schema discipline.
- The 7-epic split (atomicity over symmetry) with explicit reasoning.
- The csrf elevation to gated module mid-conversation, with
  retroactive Epic 5 update.
- The capability-axis-single-helper rule for `_common.py` extension.
- The friction-as-binding decision for `--i-own-this-target`.
- The cookie-equality detection list for same-user IDOR.
- The testbed detection escalation to dedicated endpoint with
  multi-field validation.
- The error_leakage own-probe-set decision rejecting shared cache.
- All ten cohort detection rules (admin signals, lockout signals,
  stack-trace signatures, login-redirect patterns, named session
  cookies, etc.).

Agent led: 5 scope-opens framing, the option a/b/c presentation
shape on most edges, the epic structure draft (push-back-on-shape
mode), surfacing edges per story (~75 total).

**Deepening rounds: zero.** Trump declined explicitly with rationale
("Sprint 2 scope is dense enough; the locked epics give /spec
sufficient detail to derive implementation contracts"). Same
declining-discipline pattern as Sprint 1 /spec — the conversation's
mandatory-beats-as-deepening was sufficient because the scope had
already done the upstream work that deepening rounds normally surface.

**Carryover for /sprint-2/spec.**

- 7 epics, ~40 stories, all with acceptance criteria pre-locked.
  /spec walks down each epic and produces implementation contracts.
- 11 named architectural patterns from /spec carryovers list:
  `capability-axis-single-helper`, `friction-as-binding`,
  `no-false-alarm` vs `no-false-confidence`, `owner=epic-that-
  declares-the-dataclass`, `miss-this-scan-hint-for-next-scan`,
  `Sprint-3-promise-as-INFO-text-for-auto-carryover`,
  `empirical-validation-before-escape-hatch`,
  `audit-trail-records-user-typed-form`, plus three Sprint 1
  carryovers (no-false-confidence, 50-line module cap, defer ≠ kill).
- Open questions explicitly carried to /spec: throwaway sub-session
  mechanism, `Target.urls` data shape, `scan_coverage` JSON internal
  shape, HTML rendering shape for FIT3048 + auth-context badges,
  --scan-both dedup implementation owner.
- Sprint 3 carryover list (12 items) embedded in PRD's "What We'd
  Add With More Time" — pre-built /sprint-3/scope.md input.
- Locked PRD Invariants section at PRD bottom — must survive /spec
  and /build (8 items including --auth-role decorative-only,
  Mode enum value lock, evidence_hash formula, csrf gating).
- The literal acceptance terminal output from scope.md is the
  acceptance test for output-renderer items; /spec must not
  invent alternative shapes for the rendering of FINDINGS or
  COVERAGE blocks.

**Trump-supplied /spec heuristics for the two △-flagged items**
(captured at /prd close-out so they survive /clear):

- *`Target.urls` data shape:* default to `List[Tuple[str, Source]]`
  unless any of the 6 use sites needs forward-compat fields (Sprint
  3+ might add `discovered_at`, `http_status`). Forward-compat
  need → dataclass `List[ProbeURL]`; otherwise tuple is sufficient.
- *Throwaway sub-session mechanism:* prefer dedicated
  `ephemeral_login_form()` helper. Modifying `session_factory`'s
  signature pollutes all callers; vanilla second `login_form()`
  leaves ephemerality as a calling convention rather than a named
  concept. Helper is cleanest.

## Sprint 2 — /spec

**Spec-entry state.** Most pre-resolved entry of any conversation in
this project. /scope locked multi-session, double-flag brute_force,
testbed, SCAN COVERAGE, two-endpoint Done, literal acceptance terminal
output. /prd locked 7 epics × ~40 stories × ~75 inline edges × 8 PRD
invariants × 11 named architectural patterns. Two △-flagged items
(Target.urls shape, throwaway sub-session) carried explicit Trump
heuristics from /prd close-out. Spec's job: translate acceptance
criteria into implementation contracts (class signatures, function
interfaces, file boundaries, phase ordering).

**Conversation shape.** Mandatory beats walked epic-by-epic in PRD
order with one merge (Epic 4+5 folded — both engine-level filter logic
with cross-flag interaction). Per-epic format: 2-4 architectural
surfaces explicitly flagged for Trump confirm; 4-7 implementation
patterns marked bake-in. Consistent with Sprint 1 /spec's
"mandatory-beats-as-deepening-rounds" shape — each beat surfaced
proposals with deliberately-flagged sub-decisions, Trump confirmed or
counter-proposed on each. Six epic walks (Epic 6 first because it locks
types everything else uses, then PRD order: Epic 1 → 2 → 3 → 4+5 → 7).

**Decisions made in /spec (not inherited from PRD):**

*Module Contract (Epic 6):*
- `run() -> None` (drops v1 `-> list[Finding]`). PRD-vs-actual
  ambiguity resolved on invariant-enforceability grounds: engine-wrapped
  callback is the ONLY path that injects auth_context, sets seen_in,
  computes evidence_hash, acquires stdout lock, participates in dedup.
  Module return-list bypasses every Sprint 2 invariant. Single-channel
  discipline.
- `finding_type` added as new Finding field. v1's `category`
  (module-identity slug) ≠ FIT3048_CATEGORY_MAP keys
  (per-finding-type slugs). Single-responsibility per dataclass field.
  v1 retrofit extracts existing implicit type slugs at /spec, codifies
  as map keys. Spec-locked, not /build-tunable.
- `Source` enum at `webprobe/findings.py` with scope constraint:
  pure type-definition module (dataclasses, enums, validation).
  NOT permitted: I/O, processing, helpers acting on findings. Cross-sprint
  scope discipline preventing junk-drawer expansion.
- `Finding.fit3048_category: Optional[int] = None` during construction;
  engine wrapper guarantees non-None at storage. Same pattern for
  `auth_context` and `seen_in` (context-dependent). `evidence_hash`
  is exception (self-contained, auto-computed in `__post_init__`).
  Categorization rule: self-contained → __post_init__; context-dependent
  → engine wrapper.
- Engine state for auth_context: closure capture per-dispatch over
  immutable values + designed-for-concurrency primitives
  (_stdout_lock, GIL-atomic list.append). Avoids "current_X attribute"
  thread-safety footgun. Spec note for Sprint 3+ multiprocessing
  invalidation.
- Three-phase engine pipeline: dispatch → dedup → render. Resolves
  apparent contradiction between Story 3.2 inline-tease (twice for
  --scan-both) vs Story 3.4 JSON dedup (once with merged seen_in).
  Both correct because they occur at different phases.
- `_common.py` final shape: 3 public functions (send, inject_param,
  compare_responses) + DEFAULT_TIMEOUT module-level constant + v1
  carryover build_units. v1's `send` renamed to `inject_param`;
  Sprint 2 PRD-locked `send(url, *, session=None, **kwargs)` takes
  canonical name. Capability-axis-single-helper discipline (3+ callers
  → promote to _common).

*Authentication & Session Setup (Epic 1):*
- v1 thread-local `session.py` retired. v2 `session.py` is ~6 lines:
  eager session-list factory. Three named retirement reasons (paths.py
  unauth = no race surface; auth modules serial; threading.local()
  doesn't survive fork → Sprint 3+ multiprocessing path invalidates).
  v1 → v2 simplification is /spec doing its job.
- `webprobe/auth.py` single file (subpackage premature for ~5 functions /
  ~30-50 lines). Sprint 3+ SSO refactors to `auth/` subpackage.
- `setup_form_login(verbose=False)` parameter added — caught the
  scan-stream UX bug where ephemeral session would print confusing
  duplicate "[+] Login confirmed" mid-scan. /prd didn't anticipate this.
- Three private helpers in auth.py (_discover_login_form,
  _build_login_payload, _validate_login_response) with testability
  constraint: pure functions, must be unit-testable without mocking
  requests.Session. Network I/O lives in setup_form_login main body.
- `ephemeral_login_form()` resolves /prd △ for throwaway sub-session.
  Reuses setup_form_login(verbose=False); session_factory signature
  stays unchanged from v1 (no ephemeral=True parameter pollution).
- ConfigurationError as third custom exception. Inter-flag invariants
  live in consuming functions (auth.setup_baseline,
  filter.validate_module_flags, discovery.validate_discovery_flags),
  NOT in argparse. Engine catches at top level, exit code 2.
- Phase 5 sub-phase abort/continue table explicit (5a/5b/5c/5f abort,
  5d/5e continue). Each sub-phase's failure mode documented.

*Discovery (Epic 2):*
- `Target.urls = tuple[tuple[str, Source], ...]` resolves /prd △.
  Trump's heuristic confirmed after use-site count (no use-site needs
  forward-compat fields). Tuple, not list — Python's type system
  enforces "MUST NOT mutate" via AttributeError on append.
- `webprobe/discovery.py` single file with target.py refactor. target.py
  keeps form/query_params discovery (v1 contract preserved); discovery.py
  owns URL pool composition. Naming convention: `discover_<source>` for
  metadata-rich Result objects (sitemap, robots); `discover_<source>_pairs`
  for pure URL emitters (url_list, dynamic, curated).
- Curated paths v1→v2 architectural shift (largest spec-level change in
  Epic 2). PRD didn't make explicit; /spec derived from source_filter
  contract + Story 6.3 "module body MUST NOT introspect engine state".
  paths.py loses curated.txt loading; engine URL pool gains it. Four
  payoff points (contract uniformity, file shrinks, COVERAGE accuracy,
  cross-source dedup). PRD-implicit, spec-explicit.
- Phase 0.5 inter-flag validation introduced. Phase 4.5 / 5f
  authed-sitemap-discovery split (--use-sitemap-authed needs auth setup
  complete). Phase ordering grows from v1's 6 phases to v2's 10+.
- URL canonicalization scope lock: dedup-key only. Lowercase scheme/
  netloc + path "/" if empty. NO query-string normalization. Stored URL
  is user-typed form, not normalized variant. Audit-trail discipline
  parallel to Story 5.5.

*Output (Epic 3):*
- ScanCoverage + 5 sub-dataclasses at `webprobe/coverage.py` (peer to
  ScanMetadata for the JSON `scan` block). dataclass shape == JSON shape
  via dataclasses.asdict(). Renderers + serialization both consume.
- sha256 16-char canonical (Story 3.4.E1) / 8-char display split.
  Renderer truncation; storage canonical. Data layer owns canonical
  form; render layer owns display form.
- ScanCoverage mutable during scan, frozen by convention after Phase 7.
  Phase 8 read-only invariant. Engine asserts coverage.duration_seconds
  + modules_fired populated before render starts.
- HTML structure: `<article>` + `<header>` + `<dl>` semantic per finding
  card (upgrade from v1 div-based pattern). OPERATIONAL_RISK chip in
  `<header class="report-header">` ABOVE SCAN COVERAGE — screenshot-
  readable critical signal. IDOR-conditional render expression in
  exactly two locations (terminal.py + html.py), grep-verifiable.
- `--json-out -` mode: terminal output routes to stderr (Unix
  convention). Engine `_terminal_stream` attribute set in __init__.
  colorama init with strip=not stream.isatty() handles 3 pipe scenarios.
  Lock 6: NEVER bare print() in renderer code.
- argparse argument_groups MUST use PRD-locked taxonomy verbatim.
  /build can tune flag wording but MUST NOT rename groups.

*Filtering & Risk Gates (Epic 4+5):*
- `webprobe/filter.py` (not dispatch.py — filter is pre-dispatch
  decision logic). 7 public functions, ~80-120 lines.
- `webprobe/registry.py` + `@register` decorator — module discovery
  pattern formalization. v1's hardcoded MODULES manifest replaced.
  Auto-extends to Sprint 3+ additions: add module file with @register +
  import in modules/__init__.py.
- Multi-error gate-validation reporting. Lists ALL missing gate flags at
  once (not first-error-wins). Extends Sprint 1 actionable-error
  pattern: user fixes once, retries once.
- Phase ordering Phase 2 / Phase 3.6 split (user-flag filtering vs
  risk-gate filtering). Real ordering insight: risk-gate filtering
  depends on testbed detection which requires HTTP, therefore must run
  after Phase 3 connectivity check. Cross-flag gated-module-in-include
  validation runs in Phase 0.5.
- Testbed-bypass-replaces-risk-gates-NOT-hostname-validation invariant.
  Two mechanisms orthogonal — validation checks user-input consistency,
  testbed detection checks target-environment safety. Build mustn't
  conflate.
- `_matches_testbed_url_pattern` (precision rename from
  `_looks_like_testbed_convention`). Deterministic URL pattern check,
  NOT fuzzy heuristic.
- `--i-own-this-target` rejects URL path/query in assertion shape
  (input-shape validation before semantic). Wrapper script can't
  silently "work" with wrong assertion shape.
- Risk-gate banner with box-drawing frame for visual delimitation.
- difflib.get_close_matches case-insensitive with explicit "Module names
  are case-sensitive" hint. Strict accept + helpful suggestion.

*Detection Modules (Epic 7):*
- DATA_FILES class attribute on BaseModule + auto-load in `__init__`
  + Phase 1 validation. Symmetrical with auth_strategy /
  FIT3048_CATEGORY_MAP class-attribute pattern. Base loads canonical
  form (stripped non-comment lines); module-specific post-processing
  (regex compile, case folding) in module's own __init__ after
  super().__init__(args) call.
- DATA_FILES distinction: user-editable external files (extension
  mechanism) vs module-internal frozensets (code constants, spec-locked).
- Helper file extraction REACTIVE not pre-allocated. /build creates
  `_<module>_helpers.py` only when module body crosses 50-line cap.
  Estimated likely-helper-needed: error_leakage, session. Estimated
  likely-fits: access_control, idor, csrf, brute_force.
- Five cross-module module-body Locks: Lock 1 Finding kw_only=True
  dataclass discipline; Lock 2 urljoin (no string concat); Lock 3
  RequestException via _on_request_error hook (no bare except); Lock 4
  args uniform injection (no per-module asymmetry); Lock 5 zero print()
  in module bodies (grep-verifiable).
- Edge case: `<form action="">` (CakePHP convention) means submit to
  current URL — discover_dynamic_pairs MUST add target.url to dynamic
  source list, NOT skip empty action. Team 157 form-bearing pages depend
  on this.
- v1 module retrofit checklist 9 steps × 6 modules. Step 9 (audit v1
  print() calls — REMOVE ALL) was missing from initial draft; Trump
  added it. v2 module bodies are pure Finding emitters; engine routes
  all user-visible output through report_finding callback.

**What was confident vs uncertain.**

Trump was confident on essentially everything:
- Stack additions (Flask, pyproject.toml + console_scripts) accepted
  without pushback.
- Spec architectural decisions (file locations, module boundaries,
  dataclass shapes) confirmed with refinements that *strengthened*
  the proposal rather than reframed it. Across ~30 spec surfaces,
  zero rejections — refinements only.
- Spec-vs-build line internalized from /prd entry. Throughout the
  walk, Trump consistently deferred build-time tunables (wording,
  thresholds, line counts) while pinning architectural invariants.

Trump deliberately deferred (no uncertainty, just discipline):
- Banner exact text + --help wording + verbose line format → /build.
- paths.py pool sizing → /build Checkpoint B verification beat.
- v1 internal type slugs → extracted at /spec walk, locked, not
  /build-tunable.

**Pushback received and how Trump handled it.**

- *(Epic 1 (1F) argparse layer assumption.)* Agent spec'd
  mutually-exclusive flag check in argparse layer; Trump pushed back
  with named principle ("argparse expresses single-flag presence
  cleanly but inter-flag relationships poorly"). Counter-proposal:
  flag-combination invariants live in consuming module
  (auth.setup_baseline, filter.validate_module_flags, etc.), not
  argparse. Same pattern extended to discovery, brute_force, csrf
  gates. ConfigurationError as third custom exception, exit code 2.
- *(Epic 2 (2J) authed-sitemap ordering surfaced inline.)* Agent
  initially put --use-sitemap-authed in Phase 4 alongside other
  discovery; surfaced the ordering question inline. Trump confirmed
  Phase 4 / Phase 4.5 split with abort/continue table.
- *(Epic 3 (3F) print() routing.)* Agent proposed routing terminal
  output to stderr in --json-out - mode; Trump confirmed with colorama
  isatty-strip detail handling 3 pipe scenarios cleanly.
- *(Epic 6 (F) dedup phase boundary.)* Agent wrote "engine teardown
  (post-dispatch)"; Trump pushed back ("engine teardown is too
  vague — spans inline-tease end through render"). Counter-proposal:
  three explicit phases (dispatch → dedup → render). Resolved the
  apparent inline-tease-twice vs deduped-once contradiction by phase
  separation.
- *(Epic 7 (7C) helper file pre-allocation.)* Agent proposed
  inventory listing helper files for all 6 new modules; Trump pushed
  back ("helper files are reactive extraction outcome, NOT pre-
  allocated structure"). Counter-proposal: inventory marks "if needed"
  for likely-helper modules (error_leakage, session); other 4 modules
  no helper file unless /build observes overflow. Sprint 1's reactive-
  helper discipline carried forward verbatim.
- *(Epic 7 (7D) args injection asymmetry.)* Agent proposed
  session/brute_force-only args injection; Trump pushed back with
  Lock 4 (args uniform injection across ALL modules). Modules ignore
  args if not needed; uniform dispatch beats selective injection.
  Sprint 3+ adding modules doesn't reopen the question.
- *(Epic 7 (7E) v1 print() audit.)* Agent's retrofit checklist had
  8 steps; Trump added step 9 (audit existing v1 print() calls —
  REMOVE ALL). Strengthens partial-scan philosophy: in v2, boundary
  between "this is a finding" and "this is progress chatter" is fully
  resolved — everything user-visible IS a finding. Module bodies
  become pure Finding emitters. Build verification: grep -rn "print("
  webprobe/modules/ returns zero matches.

**Drift correction (Epic 3 / Epic 6):** Agent's (3G) confirm
language conflated `evidence_hash` (self-contained — auto-computes in
__post_init__ from constructor args) with `auth_context` / `seen_in` /
`fit3048_category` (context-dependent — engine-wrapper-injected).
Trump caught and corrected. Categorization rule locked: self-contained
fields auto-compute in __post_init__; context-dependent fields are
engine-wrapper-injected. evidence_hash NOT in engine-injected list.

**Deepening rounds: zero (declined explicitly).** Same discipline as
Sprint 1 /spec — mandatory beats themselves did the work of deepening
rounds. Each beat surfaced proposals with 2-4 deliberately-flagged
sub-decisions; Trump confirmed/refined/counter-proposed on each.
Trump's framing: *"PRD has already done architectural depth work
(8 locked invariants, 11 named patterns, 12 Sprint 3 carryovers).
Spec's job is translating acceptance criteria into implementation
contracts — class signatures, function interfaces, file boundaries,
test plans. Not surfacing new design decisions. If any epic exposes
PRD-level under-specification during spec walk, the response is to
flag it back to /prd as a △."* PRD/spec boundary discipline.

This is consistent with Sprint 1's payoff: deep PRD → leaner /spec
conversation. Sprint 2's PRD was even deeper than Sprint 1's, so
Sprint 2's /spec was correspondingly even leaner relative to its
scope (7 epics vs 5).

**Active shaping.** As actively-shaped as Sprint 1 /spec, possibly
more so given Sprint 2's larger surface. Trump drove:

- The auth-aware send() rename strategy (v1 send → inject_param;
  PRD-locked send takes canonical name) with cost analysis (6-12
  total send() calls across sqli/xss/traversal — single sed-style
  rename pass).
- The auth.py function inventory with PRD story attributions.
- The ScanCoverage dataclass scope (mutable during scan, frozen by
  convention; Phase 8 read-only assertion).
- The findings.py scope constraint (pure type-definition module;
  cross-sprint discipline preventing junk-drawer expansion).
- The argparse-layer pushback with named principle ("inter-flag
  relationships poorly expressed"); counter-proposal of consuming-
  module ownership pattern. Extended to all gate validators.
- The dedup phase boundary pushback ("engine teardown is too vague")
  with three-phase explicit pin.
- The 5 cross-module module-body Locks (kw_only Finding, urljoin,
  _on_request_error, args uniform injection, zero print). Each Lock
  came with named architectural principle.
- The DATA_FILES uniform contract (base loads canonical form, modules
  post-process; super().__init__ discipline; user-editable vs internal
  constant distinction).
- The reactive-helper-extraction pushback (inventory marks "if
  needed", not pre-allocated).
- The step-9 v1 print() audit addition to retrofit checklist.
- The evidence_hash drift correction (categorizing self-contained vs
  context-dependent fields).
- The multi-error gate-validation pattern (lists ALL missing at once,
  extends actionable-error discipline).
- The testbed-bypass-orthogonality invariant (testbed bypass replaces
  risk gates NOT hostname validation).
- The path/query rejection in --i-own-this-target assertion (input-
  shape validation before semantic).
- The box-drawing frame for risk-gate banner.
- The case-insensitive Levenshtein with case-sensitive note hint.

The agent led: PRD ambiguity surfacing (run() return type, Story 6.2
construction-vs-serialization, FIT3048 lookup mechanism), 7-phase →
10-phase ordering proposal (with sub-phases for testbed/risk-gates/
authed-sitemap), the (a)/(b)/(c) framing for most architectural
choices, the v1 code survey for retrofit slugs.

**Spec → /build line, made explicit (carried from /prd).** Same
framing as Sprint 1 /spec: "an LLM agent could implement this without
making arbitrary choices about architecture" — not "every literal
constant is fixed." Trump preserved the line consistently across all
seven epics. Items deferred to /build (~7 items in Open Issues
section): SQLi DIFF_THRESHOLD, banner/help wording, paths.py pool
sizing, verbose [.] line format, module-error tips, --scan-both mode-
line flavor, HTML CSS palette refinement.

**Carryover for /checklist.**

- Walk down spec's section list and produce one checklist item per
  granular subsection. Spec written with /checklist addressability in
  mind — every subsection is a candidate item.
- Decide build mode (step-by-step vs autonomous) up front; Sprint 1
  /reflect pattern (autonomous + named checkpoints) likely applies
  given Sprint 2's larger surface.
- Pre-build verification: BaseModule contract test (instantiate every
  module class, validate class attributes, dispatch a no-op Target,
  assert no exceptions) is worth its own checklist item.
- 50-line constraint is checklist verification step (Checkpoint B),
  not build-time aspiration.
- Build-time grep verifications worth their own checklist items:
  Lock 5 (zero print() in modules); IDOR-conditional render
  expression in exactly two locations.
- Phase 0.5 / Phase 5 abort tables are /checklist verification beats.
- Testbed item (3.5) precedes Sprint 2 detection module items —
  testbed is acceptance harness for v2 module validation.
- v1 module retrofit checklist (Epic 7 (E), 9 steps × 6 modules) =
  6 atomic /checklist items.
- v1→v2 architectural shift items (curated paths move, session.py
  rewrite, target.py contract preservation) are atomic /checklist
  items, not folded into module retrofits.
- 21 PRD loop-backs / spec additions documented at spec.md tail —
  /reflect should propagate back to a PRD amendment if Sprint 2 PRD
  is re-published.

**One real spec-level risk observed and named, not eliminated.**

Sprint 2 /spec adds substantial new framework code beyond v1: auth.py,
discovery.py, filter.py, registry.py, coverage.py, output/json_render.py,
testbed/. Plus Engine class refactor + 6 new detection modules + v1
module retrofit. Sprint 1 /spec was ~1500 lines and produced ~830 lines
of code. Sprint 2 /spec is ~2600 lines and likely produces ~1500-2000
lines of code. /checklist must size atomic items conservatively;
/build estimate from /scope (13-16 hr) may need re-evaluation at
/checklist.

This is observed, named, and has the explicit recovery path /scope set:
P1 cuts (drop items 7, 9, 18, 26-28 in priority order if hitting hour
12 with P0 incomplete). Trump set the estimate himself with eyes open;
the recovery path is in place.

**Trump-supplied /checklist heuristics (captured at /spec close-out so
they survive /clear):**

*Build mode:* autonomous + named checkpoints, sustaining Sprint 1
pattern. Estimated 14-16 checkpoints (vs Sprint 1's ~10). /checklist
derives count from natural verification gates already embedded in
spec: Phase 0.5/Phase 5 abort tables, 50-line wc -l audit, Lock 5
zero-print() grep, IDOR-conditional render exactly-2-locations grep,
Module retrofit 9-step × 6 modules.

*Sequencing primitive — refined first 5 checkpoints (corrects /spec
handoff's initial slice proposal):*

1. **Foundation: Module Contract dataclasses.** findings.py
   (Source enum + ALL_SOURCES, Finding kw_only=True), coverage.py
   (ScanCoverage + sub-dataclasses), registry.py (MODULE_REGISTRY +
   @register decorator).
2. **BaseModule refactor.** DATA_FILES + auto-load, args uniform
   injection (BaseModule.__init__(args=None)), _on_request_error
   helper, Phase 1 validation extension.
3. **Engine class refactor + auth.py.** Engine module-functions →
   class. auth.py 4 setup functions + 3 helpers. Phase ordering
   0/0.5/1/2/3/3.5/3.6/3.7/4/4.5/5(5a-5f)/6/7/8/9 implementation.
4. **Testbed harness.** Flask app + /__webprobe_testbed__/health
   endpoint. Cookie-mode acceptance fixture for session module's
   throwaway sub-session test. filter.detect_testbed() validation.
5. **First vertical slice: access_control module.** Simplest
   auth_required module (Story 7.1). Validates Module Contract
   end-to-end (auth_strategy, FIT3048_CATEGORY_MAP, DATA_FILES,
   run()->None). Validates testbed bypass (Story 5.4). First
   end-to-end Finding emission with engine-injected auth_context +
   seen_in + fit3048_category.

After first vertical slice:
- 6-8: Epic 2 (discovery) + Epic 3 (output) + Epic 4+5 (filter + gates)
- 9-12: Remaining 5 new modules in PRD complexity order: idor → csrf
  → error_leakage → session → brute_force (brute_force last because
  most operational risk + needs lockout_signals.txt testbed validation)
- 13-15: v1 module retrofit × 6 (parallelizable; one checkpoint per 2
  modules)
- 16: Integration test + run-end summary completeness check

**Critical sequencing insight (caught at /spec close-out):**
Module Contract dataclasses MUST precede auth.py. auth.py builds
requests.Session AND constructs setup functions whose return values
flow into Finding(auth_context=...) and ScanCoverage. Without Module
Contract types in place, auth.py would be written against placeholder
types and require two-pass touching. Single-write discipline.

*PRD amendment decision: DON'T amend now. /reflect at end of Sprint 2
build decides.*

Categorization of the 21 /spec loop-backs:
- ~15 implementation specifics (registry pattern, @register, kw_only,
  urljoin, RequestException uniform, reactive helpers, naming
  refinements, DEFAULT_TIMEOUT, etc.). PRD is product-behavior doc,
  not implementation-pattern doc — these stay spec-level.
- ~3 user-visible behavior refinements (cross-flag lists ALL missing
  gates vs first-error-wins, banner box-drawing frame,
  --i-own-this-target rejects path/query). MAY be PRD-worthy but need
  empirical validation in /build first — pattern #7 from /prd carryover
  (`empirical-validation-before-escape-hatch`).
- ~3 architectural decisions (testbed-bypass-orthogonality truth
  table, evidence_hash self-contained __post_init__-computed,
  DATA_FILES uniform contract). Spec-level appropriate; not PRD
  material even after build.

Cost of amending PRD now: doubles edit work + introduces PRD↔spec sync
risk. /reflect post-build is the right gate — empirical /build evidence
determines which user-visible refinements actually improved UX (worth
promoting) vs which were neutral/cosmetic (stay spec-level).

**△ flag handling at close-out (Trump validated both):**
- △1 build estimate vs scope mismatch: real, recovery path (P1 cuts)
  in place, decision deferred to /checklist sequencing.
- △2 closure-capture GIL atomicity: real but Sprint 3+ concern,
  inline-documented spec note is correct move (named risk captured for
  future-Trump). Sprint 2 doesn't need to act.

## Sprint 2 — /checklist

**Checklist-entry state.** The most pre-resolved /checklist entry on
this project: /spec close-out handed over (a) build-mode pre-commit
(autonomous + named checkpoints, sustaining Sprint 1 pattern), (b)
estimated checkpoint count (14-16), (c) full first-five sequencing
slice, (d) outline of items 6-16, (e) critical sequencing insight
(Module Contract dataclasses MUST precede auth.py — single-write
discipline), (f) named △ risk (Sprint 2 ~70% larger than Sprint 1) with
recovery path (drop P1 items 7/9/18/26-28). /checklist's job: confirm
those carryovers, fill in the contract details (spec ref, acceptance,
verify) per item, sanity-check the count vs the build budget, lock in
git/verification cadence.

**Conversation shape.** Five mandatory questions (sequencing logic /
build mode + checkpoint density / git cadence / Devpost submission /
walk through items), one deepening round (modified Q1 + Q2 + Q3 lock
+ Q4/Q5 deferred). Each mandatory question Trump elected to make
substantively richer than my initial framing — not "yes/no" but
"yes/no with refinement and named architectural principle." Six real
pushbacks landed in /checklist (vs ~4-5 in /spec), each one tightening
a framing where I'd presented a shallow trade-off.

**Decisions made in /checklist (not inherited from /spec):**

*Sequencing primitive — first vertical slice and Output ordering (Q1):*
- Confirmed (a) integration-before-presentation: items 6-8 (discovery /
  output / filter+gates) build AFTER item 9 first-vertical-slice
  (access_control end-to-end against testbed). Stateful pipelines must
  work before stateless transformations are built; otherwise
  transformations build against placeholder data and break when real
  data emerges (two-pass risk). Trump's hidden-cost enumeration:
  hand-constructed Finding fixtures drift from real module emissions;
  ScanCoverage fixtures re-implement parts of auth.py; "done but needs
  retouch" checkpoints distort progress tracking.
- Refinement: debug-print verification artifact at item 9 — engine
  wrapper instruments `print(json.dumps(asdict(f), indent=2),
  file=self._terminal_stream)` after injection, before
  `self._findings.append(f)`. Removed at item 13 when json_render
  ships. Validates Module Contract types + engine wrapper injection +
  evidence_hash __post_init__ correctness without prematurely
  building visual surface. Lock 5 preserved (debug-print is wrapper
  code, NOT module body code).
- Considered (c) hybrid (mini JSON renderer in item 5/9), rejected by
  Trump — would inflate item beyond atomic, conflates integration
  test with presentation.

*Checkpoint density + dual role for B (Q2):*
- 5 checkpoints (A through E), density 2x Sprint 1's (5/16 vs 3/17 =
  ~3 items/gap vs ~6 items/gap). Density scales inversely with defect
  blast radius, which scales with surface increase per /spec △1.
- Trump's renumbering-robust pushback: anchor checkpoints to
  architectural phase boundaries, NOT item numbers. "Checkpoint after
  item 5" becomes ambiguous if /build splits item 5 into 5a/5b/5c;
  "Checkpoint after first vertical slice complete" is robust. Item
  numbers in checklist serve as `Roughly: after item N` hints, not
  binding anchors.
- Checkpoint B explicit dual role (most important gate of Sprint 2):
  Role 1 INTEGRATION ACCEPTANCE (inspect debug-print JSON for contract
  shape correctness) + Role 2 HOUR BUDGET REVIEW (compute actual hours
  vs proportional estimate; if >×1.5 trigger P1 cut dropping items
  17/18/19). Role 2 placement: P1 cut decision needs empirical
  evidence (actual hours), available first at Checkpoint B AND latest
  safe point to cut (items 17-19 not yet started). Operationalizes
  /spec △1 named recovery path with concrete trigger condition.

*Git commits + atomic boundary + bisectability (Q3):*
- (β) one-commit-per-atomic-acceptance-unit, NOT one-commit-per-item-
  number. Renumbering-robust principle threaded across checkpoints
  AND commits AND item splits — single architectural axis.
- Trump's bisectability operational reframing: my comparison "(α)
  cosmetic git log; (β) tidy revert blast radius" understated (β)'s
  case. Real (β) Pros: bisect precision (single failing commit =
  single atomic work unit, narrow debug context); revert blast radius
  = defect blast radius; renumbering-robust consistent with checkpoint
  anchor. (α)'s "log mirrors checklist 1:1" is cosmetic preference,
  not operational.
- New `refactor:` commit prefix for v1 module retrofit (semantically
  exact match per Conventional Commits — code structure changes,
  behavior unchanged). Sustains Sprint 1's `feat:`/`chore:`/`docs:`
  taxonomy. Enables `/reflect`-time `git log --grep='^refactor:'` to
  surface all v1 migrations distinctly from `feat:` v2 net-new.
- Atomic-commit boundary documented as semantic (atomic acceptance
  unit), NOT syntactic (file count). Three rules: every commit leaves
  repo importable; every commit completes single verification step
  end-to-end; multi-file commits correct when files mutually dependent.

*Devpost (p)/(q) shape + scope amendment + process-notes template (Q4):*
- (p) confirmed: /build phase ends deterministically at engineering
  completion, decoupled from Iteration 2 deployment. Endpoint A is the
  final checklist item; Endpoint B becomes a `/schedule` candidate
  routine (post-curriculum follow-up).
- (α) confirmed for semver: tag v2.0.0 directly at Endpoint A (NOT
  v2.0.0-rc.1). Trump named the principle: rc.1 anchor (release-
  candidate-pending-validation) loses its referent under (p) shape;
  testbed-validated IS the validation gate. /scope amendment captured
  at scope.md tail (Amendment 1 — semver progression supersession),
  parallel to /spec's 21 loop-backs at spec.md tail. Amendment, not
  silent drift.
- (γ) confirmed for process-notes: /build owns autonomous-completion
  summary. Trump added 3-part template specification — "What got
  built" (factual scope summary) + "Notable decisions during build"
  (with checkpoint refs) + "Open at end of /build" (input pile for
  /reflect). Without template, prerequisite passes vacuously while
  starving /reflect.

*Five-field format + estimated time + foundation 3-way split (Q5):*
- Estimated time field added per item; cumulative sum in checklist
  header for sanity-check vs /scope budget. Q1 split discretion
  upgraded from MAY to MUST when estimate >30 min.
- Trump's foundation-pairing pushback: my Item 1+2 pairing (findings.py
  + coverage.py + registry.py paired) was syntactic-similarity-driven
  (both "foundation shells"), NOT semantic-dependency-driven (coverage
  and registry are mutually independent — neither imports the other).
  Violates Q3's bisectability principle. Split to 3 separate items.
  Net: 16 → 17 items.
- Per-item refinements: Item 1 SEVERITY_ORDER values explicit + cap
  clarification ("informational, not hard cap"); Item 2 TYPE_CHECKING
  rationale documented; Item 4 (renumbered) tempfile-based verify
  command (no repo pollution from prior `mkdir webprobe/data/_smoke`
  approach), full DATA_FILES integration deferred to Item 10
  (access_control with real fixtures).

*MUST SPLIT discipline + 23-item count emergence:*
- After applying MUST SPLIT rule across items 5/6/10/11/12/14/17/18,
  count grew from /spec carryover's rough 16 to /checklist's empirical
  23. Trump confirmed 23 (rejected both my fold proposals to compress
  back to 22). Reasoning: folding 5+7 (Engine + auth-wiring)
  conflates three architectural phases into one commit, violates Q3
  single-architectural-concern-per-commit principle. Folding v1
  retrofit to 6 single-module items wastes commit ceremony on
  ~10-15 min mechanical work below atomic floor.
- Cumulative time: 820 min lower bound + 160 min split overhead +
  100 min checkpoint overhead = 18.0 hr lower bound. Trump's
  realism note: ×1.3-1.5 estimation overhead → 23-27 hr realistic.
  P1-cut form: ~22.2 hr realistic. Both fit revised 24-32 hr budget.

*Q1 deepening — testbed fixture completeness audit (9 gaps + cross-
cutting):*
- Trump named the silent failure category: "module ran clean but
  couldn't fire because testbed lacked differentiating fixture."
  Eliminates the failure category by deliberate per-module testbed
  endpoint specification.
- 9 gaps surfaced and resolved: csrf form discovery (Gap 1), user
  enumeration differential (Gap 2), stack-trace own-probe-set
  endpoint (Gap 3), post-logout cookie replay endpoint (Gap 4),
  session fixation mechanism (Gap 5), logout URL discovery scope
  (Gap 6), curated path testbed exposure (Gap 7), traversal vuln
  exposure (Gap 8), discovery dynamic-source empty-action edge case
  (Gap 9). Plus cross-cutting (γ): SESSION_COOKIE_NAME='PHPSESSID'
  via custom SessionInterface, mimics real-target landscape (PHP/
  CakePHP/Laravel) per /scope FIT3047 anchor.
- Trump's named pattern: testbed-shape-mimics-target-not-implementation.
  Testbed's choice of Flask is implementation detail; testbed's
  exposed surface mimics real target ecosystem. (δ) "add 'session' to
  the frozenset" deferred to Sprint 3 PRD-level scope question.
- Gap 5 binary call (i)/(ii). Trump considered (iii) third option
  ("rely on Flask default behavior to expose fixation"), worked it
  through, found impossible — Flask's signed-cookie session is
  fixation-resistant by accident (cookie value is sha256-signed over
  payload, so payload change naturally rotates cookie). Real fixation
  requires server-side session storage with stable session ID across
  auth boundaries.
- Locked Gap 5 (i): build custom FixationVulnerableSessionInterface
  (~25 lines including bonus coverage). Single implementation closes
  3 module fixtures: session.session_fixation + headers.cookie_no_httponly
  (httponly=False intentionally exposes cookie no-HttpOnly flag) +
  auth.detect_shared_session (PHPSESSID cookie name in
  _SHARED_SESSION_COOKIE_NAMES frozenset). Bonus-coverage observation
  is the kind of /spec-level architectural insight that makes the
  testbed a genuinely complete fixture, not a sketch.
- Item 8 splits to 8a (stateless endpoints, 15 min) + 8b (stateful
  endpoints + custom session interface, 30 min) per atomic-boundary
  call. Bisect precision on testbed bugs improves: stateless route
  bugs vs session-management bugs land in different commits.

*Q2 helpers wording lock:*
- "Likely needed" wording in items 15/17/18 was drift — contradicts
  spec.md's "REACTIVE not pre-allocated" discipline. Replaced with
  "extracted IF AND ONLY IF module body exceeds 50 lines after run()
  implementation" + "informational reference, not commitment"
  qualifier on the likely-extraction estimate.

*Q3 Sprint 1 acceptance reproduction lock:*
- Tier 1/2/3 fallback chain at Checkpoint E. Tier 3 (testbed-only v2
  acceptance) always available, never blocks on external dependency.
  Tier 1 enabled by Item 8a/8b's complete fixture surface — testbed
  becomes acceptance fixture for ALL 12 modules (6 v1 + 6 v2), not
  just the 6 v2 modules. Item 8 reframed: "build Flask app whose
  endpoints constitute acceptance fixtures for ALL detection modules,"
  not "build Flask app."

*Q4/Q5 defer:*
- Q4 (dedup tuple precision vs minimalism) defer to /build/reflect —
  implementation-detail readability call, not spec architectural gap.
- Q5 (Lock 5 grep verification fragility) defer to /build — verification
  step refinement that build naturally surfaces if false-positive
  appears. AST upgrade is the precise version; grep suffices until
  observed insufficient.

**Total artifacts produced:**
- `docs/sprint-2/checklist.md` — 23 items, five-field format with
  Estimated time, 5 named checkpoints anchored to architectural
  boundaries, header documenting build mode + commit cadence + atomic-
  commit boundary + MUST SPLIT rule + 3-part process-notes template +
  cumulative time tally + P1 cut decision logic + extensive notes for
  build agent (testbed-fixture-grade, debug-print at item 9 removed
  at item 13, Lock 5 grep verification, helper extraction reactive,
  Tier 1/2/3 fallback for v1 acceptance).
- `docs/sprint-2/scope.md` Amendment 1 (semver progression
  supersession) appended at scope.md tail.

**What was confident vs uncertain.**

Trump was confident on essentially everything substantive:
- Build mode autonomous + checkpoints (pre-locked from /spec
  carryover, no surprise).
- All 9 testbed gaps + cross-cutting (γ) accepted as proposed.
- 23-item count + both fold rejections + retrofit pairing structure.

Trump's uncertainty surfaced exactly once and was substantive: Gap 5
(SessionInterface scope). He surfaced (iii) third option, worked
through it, ruled it impossible, then locked (i) with concrete
SessionInterface implementation. Demonstrates the checklist-level
discipline of "considered alternatives" not as performative but as
real engineering judgment.

Trump deliberately deferred (no uncertainty, just discipline):
- Q4 dedup tuple precision → /build's call
- Q5 grep AST upgrade → /build's call when surfaced
- (δ) Flask 'session' cookie name → Sprint 3 PRD scope question

**Pushback received and how Trump handled it.**

Six real pushbacks across /checklist's mandatory + deepening rounds:

- *(Q1 first vertical slice framing.)* Agent presented (a) vs (b) with
  shallow trade-off; Trump deepened the (a) argument with named
  principle "integration-before-presentation," enumerated hidden
  costs of (b) beyond what I'd flagged (fixture drift, fixture
  complexity, progress-tracking distortion), proposed and rejected
  (c) hybrid himself, locked (a) with debug-print verification
  artifact refinement.
- *(Q2 checkpoint anchor framing.)* Agent proposed checkpoints "at
  items N/M/...". Trump pushed back: "Checkpoint after item 5 becomes
  ambiguous if /build splits item 5 into 5a/5b/5c. Checkpoint after
  first vertical slice complete is renumbering-robust." Counter-
  proposal: anchor checkpoints to architectural phase boundaries,
  item numbers are advisory hints. This principle then propagated to
  Q3 commits and Q5 item splits — single architectural axis.
- *(Q2 Checkpoint B dual role.)* Agent didn't surface Role 2 hour-
  budget review. Trump added it explicitly with concrete trigger
  condition (actual > expected × 1.5 → drop items 17/18/19),
  operationalizing /spec △1's named recovery path.
- *(Q3 bisectability framing.)* Agent's (α)/(β) trade-off framing
  understated (β)'s case as "tidy revert blast radius" (cosmetic-
  sounding). Trump reframed as bisectability + revert blast radius
  = defect blast radius + renumbering-robust consistency — operational
  Pros, not preference Pros. Plus added `refactor:` prefix taxonomy
  for v1 retrofit + atomic-commit boundary documented as semantic
  (acceptance-unit) not syntactic (file count).
- *(Q4 semver deviation.)* Agent surfaced (α)/(β) trade-off but
  framed as "deviation." Trump pushed back: "deviation drift accumulates;
  amendment captures supersession." Counter-proposal: edit scope.md
  tail with Amendment 1 explicitly. Same pattern as /spec's 21 loop-
  backs at spec.md tail. Plus 3-part process-notes template (γ
  refinement) — "without template, prerequisite passes vacuously
  while starving /reflect."
- *(Q5 Item 1+2 pairing.)* Agent's foundation-pairing was syntactic-
  similarity-driven (both "foundation shells"); Trump pushed back
  with semantic dependency check (coverage and registry are mutually
  independent — neither imports the other). Counter-proposal: split
  to 3 separate items. Plus refinements per item (SEVERITY_ORDER
  values, TYPE_CHECKING rationale, tempfile verify command).

**Drift correction (Q5 helpers wording):** Agent's items 15/17/18
contained "Helpers likely needed in `_<module>_helpers.py`" — drift
from spec.md's REACTIVE-not-pre-allocated discipline. Trump caught
during Q2 deepening lock and replaced wording with "extracted IF AND
ONLY IF module body exceeds 50 lines" + "informational reference, not
commitment" qualifier on the likely-extraction estimate. Spec
discipline preserved through wording precision.

**Deepening rounds: one (Q1 modified — Q2 + Q3 lock now, Q4 + Q5
deferred).** Trump's asymmetric handling per-question was its own
discipline: Q1 architectural (testbed surface for items 15/17/18,
silent failure category) gets full deep walk; Q2 mechanical fix
(spec wording drift); Q3 mechanical fallback chain (Tier 1/2/3); Q4
implementation readability call → /build/reflect; Q5 verification
fragility → /build. Same discipline as /spec close-out: "if any epic
exposes PRD-level under-specification during spec walk, the response
is to flag it back to /prd as a △." /checklist applied the analog:
"if any item exposes spec-level under-specification, flag it back to
/spec OR resolve at /checklist with explicit amendment captured at
spec.md/scope.md tail." Q1 result: 9 gaps + cross-cutting + Gap 5 (i)
SessionInterface implementation, all locked into Item 8a/8b spec.

**Active shaping.** Most actively-shaped /checklist of any project so
far. Trump drove:

- The renumbering-robust principle (Q2), then propagated it to commits
  (Q3) and item splits (Q5) as single architectural axis.
- The Checkpoint B dual role with concrete trigger condition (Q2)
  operationalizing /spec △1.
- The bisectability operational reframing (Q3) with `refactor:`
  prefix taxonomy + atomic-commit boundary semantic definition.
- The /scope amendment vs drift discipline (Q4) with concrete
  Amendment 1 text supplied.
- The 3-part process-notes template (Q4) preventing vacuous
  prerequisite pass.
- The Estimated time field + MUST SPLIT hard rule (Q5) + the
  Item 1+2 syntactic-vs-semantic-pairing pushback.
- The testbed-shape-mimics-target-not-implementation pattern (Q1
  cross-cutting γ) with named architectural principle.
- The Gap 5 (i) SessionInterface concrete spec with bonus-coverage
  observation (one implementation closes 3 module fixtures).
- The Item 8a/8b atomic-boundary split (stateless endpoints
  separately from stateful + sessions) for bisect precision on
  testbed bugs.
- The realistic vs lower-bound time estimation framing (×1.3-1.5
  overhead).
- The "likely needed" → "if and only if + informational reference"
  helpers wording fix (Q2 deepening).
- The Tier 1/2/3 fallback chain for Sprint 1 acceptance reproduction
  (Q3 deepening) with Tier 3 always-available guarantee.

The agent led: (a)/(b) framing on most architectural choices, item
walkthrough five-field format proposal, cumulative time math,
testbed gap enumeration (Trump confirmed 9-of-9 + added Gap 5
SessionInterface concrete spec).

**One real /checklist-level risk observed and named, not eliminated.**

23 items with 8 MUST SPLIT annotations means /build will accumulate
30+ commits across items 5/6/10/11/12/14/17/18 splits. Bisect remains
precise per Q3 (β), but reading the commit log requires patience —
git log without filtering will show ~30+ commits across ~24 hr build.
`/reflect` should evaluate whether commit-density was operationally
useful (bisects fired, blast radius matched defects) or cosmetically
heavy (no bisect needed, log just longer to scan).

This is observed, named, and accepted — the trade-off favors bisect
precision over log density when defect-cost scales with surface
increase per /spec △1.

**Carryover for /build.**

- Use the /scope Amendment 1 — tag v2.0.0 (NOT v2.0.0-rc.1) at
  Endpoint A. Iteration 2 audit produces v2.0.1 patches if needed,
  never blocks v2.0.0.
- Item 8a/8b is the load-bearing testbed harness — testbed IS the
  integration acceptance fixture for ALL 12 modules (silent failure
  category defended against by deliberate per-module endpoint
  specification).
- Checkpoint B is the most important gate — Role 1 inspects
  debug-print JSON; Role 2 computes hour budget vs proportional
  estimate, decides P1 cut formally if actual > expected × 1.5.
- Process-notes `## Sprint 2 — /build` section follows 3-part
  template strictly: "What got built" (factual) + "Notable decisions"
  (with checkpoint refs) + "Open at end of /build" (input pile for
  /reflect). Vacuous "build done" passes the prerequisite but starves
  /reflect.
- Renumbering-robust framing throughout: when /build splits item N
  into Na/Nb/Nc, checkpoints reference architectural completeness
  ("after Module Contract foundation locked"), item numbers are
  advisory hints. Each split sub-item gets its own commit per (β).
- Lock 5 grep verification at item 22 ALWAYS sweeps all 12 module
  bodies (final integration check before Checkpoint E).

---

## Sprint 2 — /build (deviations accumulator, /reflect input pile)

Final 3-part template (What got built / Notable decisions / Open at end of /build) lands at Item 23. Until then, /build deviations accumulate here for /reflect.

**Build deviation #1 — colorama 0.4.6 API mismatch (Item 5a).**
Spec writes `colorama.init(wrap_stdout=False, strip=...)`; real API uses `wrap=False` and rejects mixed-arg combinations (`ValueError: wrap=False conflicts with any other arg=True`). Engine `__init__` uses TTY-conditional `colorama.init(...)` to preserve spec intent. Spec wording should update; behavior unchanged.

**Build deviation #2 — `_LoginForm` private dataclass (Item 6a).**
v1 `Form` (in `findings.py`) has a single `fields: dict[str, str]` and isn't shaped for the auth pipeline's user/pass/hidden split. Auth-internal `_LoginForm` dataclass in `auth.py` solves this without polluting `findings.Form`. Architectural decision; spec didn't mandate either approach.

**Build deviation #3 — `fit3048_category=1` for engine-emitted findings (Item 7).**
Engine-emitted INFO findings (Phase 5d shared-session, Phase 5e session-ambiguous, Phase 4 wildcard-intents) inject `fit3048_category` directly because no `FIT3048_CATEGORY_MAP` exists for engine-level findings. Picked Category 1 (operational/observability bucket). Defensible; spec silent on engine-emitted finding category mapping.

**Build deviation #4 — `_common.send` rename to `inject_param` (Item 9).**
v2 `send(url, *, session=None)` collides with v1's `send(session, url, ...)` positional signature. Renamed v1 `send` → `inject_param`. v1 sqli/xss/traversal still *import* `send` (atomic-import gate passes) but their call sites break if exercised. Items 20-22 retrofit repairs. v2 path verified working.

**Build deviation #5 — `_LoginForm` POST GET handler added to testbed (Item 8b/9 boundary).**
`setup_form_login` does a `GET login_url` first to discover the form. Original Item 8b only spec'd `POST /login`. Added `GET /login` returning a minimal HTML form. Folded into the Item 9 entry-point commit. Testbed acceptance shape unchanged; agent decision.

**Build deviation #6 — Phase 0.5 vs Phase 3.5/3.6 ordering (Item 14a → Checkpoint C fix).**
Item 14a placed gated-module-in-include validation in `validate_module_flags` at Phase 0.5 — but Phase 0.5 is HTTP-blind, so it raised `ConfigurationError` before Phase 3.5 could probe `/__webprobe_testbed__/health` and bypass risk gates. The vertical slice from Item 9 (`python3 -m webprobe http://localhost:9999 --include-modules access_control`) broke at Checkpoint C: testbed not detected, gated-include rejected.

Surfaced by Trump at Checkpoint C with exact repro: testbed health endpoint serves `200 OK + {"webprobe_testbed": true}` correctly, but webprobe never gets to probe it because Phase 0.5 fires first.

**Fix A applied** (Trump's preferred — clean semantic separation):
- `validate_module_flags` becomes flag-shape coherence only (mutex, name validation, parse). No HTTP needed.
- Gated-module-in-include check moves into `filter_modules_by_risk_gates` (Phase 3.6), AFTER `is_testbed` is known.
  - Testbed → bypass returns `(modules, [])` silently.
  - Non-testbed → multi-error `ConfigurationError` listing all missing gate flags at once (extends-actionable-error pattern preserved per Story 4.1 / Q5 lock).
- Engine `run_pipeline` wraps `_phase_3_6` in try/except `ConfigurationError` → `sys.exit(2)` matching the previous Phase 0.5 hard-error contract.

**Fix B (deferred error queue) rejected:** would have kept Phase 0.5 surface signature unchanged but introduced "deferred error queue" mechanics — awkward control flow and a new state-tracking concern.

Re-verification (post-fix):
- Test 1 (vertical slice on testbed): `evidence_hash e52ebb5e21f8a161` matches Item 9 exactly. Item 9 vertical slice fully restored. ✓
- Test 2 (non-testbed banner against `https://example.com`): `ERROR: ...access_control: requires --i-own-this-target=<hostname>` emits as expected. ✓
- Test 3 (multi-error against synthetic 3-module set): all 3 modules listed in single error message; testbed bypass keeps all 3 silently. ✓ (Direct unit test against `filter_modules_by_risk_gates` because `brute_force`/`csrf` aren't yet `@register`'d — Items 16/19 land them; the end-to-end CLI test will then work without modification.)

**Lesson for /reflect:** "Phase boundary = HTTP capability boundary" should be a Module Contract lock, not just an emergent property. Phase 0.5 (no HTTP), Phase 3 (connectivity required), Phase 3.5+ (testbed-aware) is a layered capability cake — putting validation in the wrong layer creates impossible logic gates. Add to spec.md Module-Body Invariants as a documented invariant.

### Named pattern (Sprint 2 — surfaced at Checkpoint C, 9th+ named pattern of Sprint 2)

**phase-boundary-as-capability-boundary**

Engine phase ordering is not just a sequencing decision — it's a capability-boundary decision. Each phase has an implicit capability budget:

| Phase   | Capability budget                                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------------------------|
| 0 / 0.5 | argparse + flag-shape coherence. **NO HTTP, NO file I/O, NO subprocess, NO state derivation requiring runtime probing.**           |
| 1       | module enumeration + class-attr validation. **NO HTTP**; file I/O OK for DATA_FILES auto-load via `importlib.resources`.           |
| 2       | user-flag module filtering. **No new capabilities**; works on Phase 1 enumeration result.                                          |
| 3       | target connectivity probe. **HTTP allowed for the first time** (single GET → `target.base_response`).                              |
| 3.5     | testbed detection. **HTTP + caches result on engine state** (`self._is_testbed`).                                                  |
| 3.6     | risk-gate filtering. **Uses Phase 3.5 cached testbed status, NO new HTTP.**                                                        |
| 3.7     | risk-gate banner emission. **Terminal stream write, no HTTP.**                                                                     |
| 4       | URL pool resolution. **HTTP allowed for sitemap/robots discovery**; cap-hit / wildcard-intent INFO findings appended.              |
| 5       | auth setup. **HTTP allowed for login/baseline/session-check probes.**                                                              |
| 6       | module dispatch. **HTTP allowed via `_common.send` per module body**; one closure-captured `report_finding` per (module, pass).    |
| 7       | dedup + render + sink writes. **No HTTP**; output only.                                                                            |

**Validations must be placed in the phase whose capability budget can satisfy them.** Phase 0.5 trying to do gated-include validation requiring HTTP-derived testbed knowledge — impossible at Phase 0.5 — is what surfaced as the Item 14 risk-gate bug at Checkpoint C.

**Build agent mechanical check:** before placing any validation, ask "this validation requires capability X — is X in this phase's budget?" If not, defer to the earliest phase whose budget admits it.

**Sprint 3 implications:**
- /spec phase-ordering documentation should explicit-list each phase's capability budget (table above is the canonical source).
- Sprint 3 may choose to promote to PRD invariant: **"Engine phases declare capability budgets; validations placed by capability fit."**
- The lock is testable by inspection: walk each phase's body and confirm only listed capabilities are exercised.

This is the 9th+ named architectural pattern of Sprint 2. Earlier ones (from /scope, /prd, /spec, /checklist phases): renumbering-robust commits, atomic-acceptance commit boundary, MUST SPLIT ≤30min cap, testbed-shape-mimics-target-not-implementation (cross-cutting γ), checkpoint dual-role (Checkpoint B integration + hour budget), 3-tier acceptance fallback, /scope amendment vs drift, integration-before-presentation, helper extraction reactive (50-line cap trigger). Add this one at /reflect.

