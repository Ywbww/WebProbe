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
scanner himself against the my FIT3047 team FIT3047 CakePHP project at
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
  quality, not a calibration miss: the my FIT3047 team stack uses CakePHP 5
  ORM (parameterised queries by default) + `h()` auto-escaping +
  FormHelper CSRF tokens. Detector silence on a defended login form is
  the detector telling the truth. Trump explicitly declined to lower
  `DIFF_THRESHOLD` from 0.30 to 0.15 — that would manufacture false
  positives without specific knowledge of a missed defect, and the
  spec carryover loop-back protocol was scoped to known-vulnerability
  cases.
- The two HIGH findings (csrfToken Secure flag, HSTS) are genuinely
  actionable items being routed to a my FIT3047 team Iteration 2 backlog
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

- The my FIT3047 team audit is a real artifact, not a demo. Two HIGH
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
