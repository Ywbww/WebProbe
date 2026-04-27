# Learner Profile

## Who They Are
Goes by "Trump." University student studying cybersecurity. Comfortable
intermediate developer who codes regularly as part of their degree. Coming
into this hackathon to build a web vulnerability detection tool
("WebProbe") that they can use against their own CakePHP university
project (FIT3047). This is their second project using the
hackathon-in-a-plugin spec-driven workflow — the first was ReconKit, a
CLI recon tool, completed end-to-end through scope → PRD → spec →
checklist → build.

## Technical Experience
**Level:** Comfortable intermediate, with strong domain depth in
cybersecurity. Has a published research paper on deepfake attacks on
biometric systems — can hold their own in technical conversation.

**Languages:** Python, C, Java, PHP (CakePHP 5), SQL (MariaDB).

**Tools:** Git, GNS3, Wireshark, Claude Code.

**Recent build:** ReconKit — a CLI recon tool using Python threading,
urllib, and socket. Familiar with network programming basics, concurrency,
and HTTP-level work. Has shipped a non-trivial Python project end-to-end
with this workflow.

**AI coding agent experience:** Active Claude Code user. Just completed
ReconKit using the full hackathon-in-a-plugin curriculum — does not need
process re-explanation.

**Areas they want to explore:** How web vulnerability scanners decide
something is an XSS or SQLi candidate at the implementation level — the
detection logic Burp Suite uses, reimplemented from scratch.

## Learning Goals
> "I want to get better at building tools that actually find real
> vulnerabilities — not just theory, but something I can run against my
> own CakePHP web app and get actionable results. Specifically I want to
> understand how web vulnerability detection works under the hood — how
> tools like Burp Suite decide something is an XSS or SQLi candidate, and
> how to implement that logic myself."

**Win condition:** Run WebProbe against the FIT3047 CakePHP project's
login page and report page, and have it catch a real vulnerability they
didn't know was there.

This is a meaningful goal — it tests whether the tool works on a target
the learner actually owns and understands. It also implies the tool needs
to produce *actionable* findings (not just noise), which should shape
scoping and detection-confidence design.

## Creative Sensibility
**Mentioned:** Currently into CTFs (HackTheBox, TryHackMe) and listening
to Mandopop. Light on bandwidth for other media due to uni assignments.

**Signals to use:**
- CTF aesthetic — terminal-forward, dark, satisfying "pop" moments when
  something is found. Output should feel like a CTF flag drop, not a
  corporate report.
- Mandopop softness offsets the harsh-hacker default — readable,
  unhurried, calm. Not aggressive. Not green-on-black-90s-hacker-movie.
- Combined: clean terminal output, color used sparingly and intentionally,
  good information hierarchy, satisfying-to-scan results.

## Prior SDD Experience
**Yes — direct, recent, hands-on.** This is their second project using
this exact plugin workflow. Just shipped ReconKit, going through scope →
PRD → spec → checklist → build. Their description of how the spec worked
in that project — *"defined every function signature, data structure, and
edge case before writing a single line of code"* — shows a real
internalization of why SDD matters.

**Calibration implications:**
- `/reflect` quiz can target advanced material. Skip "what is a spec" and
  go to nuance: trade-offs in spec depth, when to deviate, how to
  iterate after `/build`.
- Process explanations across all commands can be terse. Don't re-teach
  context rot, flipped interaction, or the command chain — they already
  live this loop.
- Move faster through interview phases. The learner can give substantive,
  pre-structured answers (the responses in /onboard already showed that).
- Push on craft and judgment, not mechanics.
