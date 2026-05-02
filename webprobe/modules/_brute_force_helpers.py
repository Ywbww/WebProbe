"""Helpers for brute_force module — extracted to keep the module body
under the 50-line cap (spec.md > 50-Line Cap)."""
from __future__ import annotations

import time
from hashlib import sha256

import requests
from requests import Response

from webprobe.findings import Finding
from webprobe.modules._common import DEFAULT_TIMEOUT


def post_login_attempt(login_url: str, user: str, wrong_pw: str) -> Response:
    """Single POST to the login endpoint with a synthesized wrong password.
    Uses an ephemeral Session per attempt so cookie-based throttles based
    on cookie identity don't latch us into a fixed slot."""
    sess = requests.Session()
    return sess.post(
        login_url,
        data={"user": user, "username": user,
              "password": wrong_pw, "pass": wrong_pw},
        timeout=DEFAULT_TIMEOUT,
        allow_redirects=False,
    )


def collect_responses(login_url: str, user: str) -> tuple[list[tuple[int, str]], str]:
    """Run 6 wrong-password attempts with 1s pauses; return (shapes,
    last_response_text). `shapes` is a list of (status, body_sha256) tuples
    used for identical-response detection."""
    shapes: list[tuple[int, str]] = []
    last_text = ""
    for i in range(1, 7):
        wrong_pw = f"webprobe_brute_test_{i}"
        resp = post_login_attempt(login_url, user, wrong_pw)
        last_text = resp.text or ""
        shapes.append((resp.status_code, sha256(resp.content).hexdigest()))
        if i < 6:
            time.sleep(1)
    return shapes, last_text


def matches_lockout_signal(body: str, signals: list[str]) -> bool:
    body_lower = (body or "").lower()
    return any(s.lower() in body_lower for s in signals if s)


def no_lockout_finding(login_url: str) -> Finding:
    return Finding(
        severity="MEDIUM", category="brute_force",
        finding_type="no_lockout",
        name="No lockout detected after 6 wrong-password attempts",
        url=login_url,
        evidence=("6 sequential POSTs with synthesized wrong passwords "
                  "(1s apart) returned identical (status, body sha256)."),
        remediation="Implement account lockout, rate limiting, or "
                    "progressive delays after repeated failures.",
    )


def weak_lockout_finding(login_url: str) -> Finding:
    return Finding(
        severity="INFO", category="brute_force",
        finding_type="weak_lockout",
        name="Responses vary across attempts but no clear lockout signal",
        url=login_url,
        evidence=("Possible weak rate limiting; lockout-signal pattern "
                  "match returned no hit on the final response."),
        remediation="Verify lockout policy; consider tightening threshold "
                    "or adding an explicit lockout banner.",
    )
