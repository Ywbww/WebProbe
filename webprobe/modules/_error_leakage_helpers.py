"""Helpers for error_leakage module — extracted to keep the module body
under the 50-line cap (spec.md > 50-Line Cap).

Item 17a: user-enumeration probe (`probe_user_enumeration`,
`user_enum_finding`). Item 17b adds stack-trace probe-set construction
and pattern matching.
"""
from __future__ import annotations

import re
import secrets
from hashlib import sha256
from typing import Optional
from urllib.parse import urljoin

import requests
from requests import Response

from webprobe.findings import Finding
from webprobe.modules._common import DEFAULT_TIMEOUT


# Heuristic regex: capture the visible body of <div class="error">…</div>
# (or any first-rendered short error fragment). Used to decide whether
# the rendered error message itself differs across the two probes.
_ERROR_BLOCK_RE = re.compile(
    r"<div\b[^>]*class\s*=\s*[\"']?[^\"'>]*\berror\b[^\"'>]*[\"']?[^>]*>"
    r"\s*([^<]{1,200})",
    re.IGNORECASE,
)


def _post_login(login_url: str, user: str, password: str) -> Response:
    sess = requests.Session()
    return sess.post(
        login_url,
        data={"user": user, "username": user,
              "password": password, "pass": password},
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=True,
    )


def _extract_error_text(body: str) -> str:
    """First heuristic: <div class="error">…</div> body. Fallback: first
    non-empty line of the response (covers `Unknown user` / `Invalid
    password` plain-text bodies)."""
    if not body:
        return ""
    m = _ERROR_BLOCK_RE.search(body)
    if m:
        return m.group(1).strip()
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


def probe_user_enumeration(
    login_url: str, real_user: str
) -> Optional[tuple[list[str], str, str]]:
    """Run the 2-probe diff. Returns (axes_differing, evidence_a,
    evidence_b) when ANY axis differs; None when the responses look
    identical on all 4 axes (status, final URL, body sha256, error text).
    A None return on RequestException is the caller's contract.
    """
    suffix = secrets.token_hex(4)
    fake_user = f"webprobe_nonexistent_xyz_{suffix}@test.invalid"
    resp_a = _post_login(login_url, real_user, "webprobe_probe_a")
    resp_b = _post_login(login_url, fake_user, "webprobe_probe_b")
    body_a, body_b = resp_a.text or "", resp_b.text or ""
    err_a, err_b = _extract_error_text(body_a), _extract_error_text(body_b)
    sha_a = sha256(resp_a.content).hexdigest()
    sha_b = sha256(resp_b.content).hexdigest()
    axes: list[str] = []
    if resp_a.status_code != resp_b.status_code:
        axes.append(f"status ({resp_a.status_code} vs {resp_b.status_code})")
    if (resp_a.url or "") != (resp_b.url or ""):
        axes.append(f"final URL ({resp_a.url} vs {resp_b.url})")
    if sha_a != sha_b:
        axes.append("body sha256")
    if err_a != err_b:
        axes.append(f"error text ({err_a!r} vs {err_b!r})")
    if not axes:
        return None
    return axes, f"real user → HTTP {resp_a.status_code} {err_a!r}", \
        f"unknown user → HTTP {resp_b.status_code} {err_b!r}"


def user_enum_finding(login_url: str, real_user: str,
                      axes: list[str], ev_a: str, ev_b: str) -> Finding:
    return Finding(
        severity="HIGH", category="error_leakage",
        finding_type="username_enumeration_login",
        name="Login response differs for known vs unknown username",
        url=login_url,
        evidence=(f"Probed as user={real_user!r} (real) and a synthesized "
                  f"unknown user; differing axes: {', '.join(axes)}. "
                  f"{ev_a}; {ev_b}."),
        remediation=("Return identical response shape regardless of whether "
                     "the username exists; both should fail with a generic "
                     "'Invalid credentials' message."),
    )


def build_probe_set(target_url: str, login_url: Optional[str]) -> list[str]:
    """Story 7.4.E1: own probe set, NOT target.urls. Five fixed shapes
    that flush dev-mode error pages on common stacks (Python tracebacks,
    PHP warnings, generic 500s)."""
    probes = [
        urljoin(target_url, "/"),
        urljoin(target_url, "/admin/__webprobe_404_trigger__"),
        urljoin(target_url, "/?id='%20OR%201=1"),
        urljoin(target_url, "/search?q='"),
    ]
    if login_url:
        probes.insert(1, login_url)
    return probes


def match_stack_trace(body: str,
                      patterns: list[str]) -> Optional[tuple[str, str]]:
    """Substring-match patterns against `body`. Returns (pattern, excerpt)
    on first match; None if no pattern fires. Excerpt is up to 200 chars
    starting at the match position."""
    if not body:
        return None
    for p in patterns:
        idx = body.find(p)
        if idx >= 0:
            excerpt = body[idx:idx + 200].replace("\n", " ").strip()
            return p, excerpt
    return None


def stack_trace_finding(probe_url: str, pattern: str, excerpt: str) -> Finding:
    return Finding(
        severity="MEDIUM", category="error_leakage",
        finding_type="stack_trace_leakage",
        name=f"Stack trace leakage on {probe_url}",
        url=probe_url,
        evidence=(f"Pattern {pattern!r} found in response body. "
                  f"First 200 chars of leak: {excerpt}"),
        remediation=("Configure framework to suppress stack traces in "
                     "production; route exceptions to a generic error page."),
    )
