"""Shared HTTP helpers used by detection modules.

Sprint 1 shipped a single `send(sess, url, method, param, payload, base)`
per-injectable helper used by sqli/xss/traversal. The v2 contract adds a
new `send(url, *, session=None, **kwargs)` for anonymous-or-authed single
GETs (consumed by access_control / idor / csrf / error_leakage / session
/ brute_force). The v1 callable is renamed to `inject_param` to avoid
the collision; v1 modules import the new name from here.
"""
from __future__ import annotations

from hashlib import sha256

import requests
from requests import Response

from webprobe.findings import Target

# v1 shipped a 5s timeout per request. Spec.md > _common.py final shape
# bumps the v2 single-GET helper to 10s (matches Phase 5e/connectivity
# budget). Sprint 1 callers (sqli/xss/traversal) keep the original 5s
# via inject_param's hard-coded literal.
DEFAULT_TIMEOUT: float = 10.0


def send(url: str, *, session=None, **kwargs) -> Response:
    """v2 anonymous-or-authed single GET.

    Used by access_control, idor, csrf, error_leakage, session,
    brute_force. Keyword-only `session` parameter (`*` prevents
    positional misuse). `session=None` uses module-level requests.get
    for an anonymous fetch.
    """
    if session is None:
        return requests.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
    return session.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)


def compare_responses(resp_a: Response, resp_b: Response) -> bool:
    """sha256 body match. v2 callers: idor (cross-account), session
    (logout test), error_leakage (user-enum baseline diff)."""
    return (sha256(resp_a.content).hexdigest()
            == sha256(resp_b.content).hexdigest())


def build_units(target: Target) -> list[tuple[str, str, str, dict]]:
    """v1 carryover. Per-injectable surface enumerator. Used by
    sqli/xss/traversal (per-param injection)."""
    units: list[tuple[str, str, str, dict]] = [
        (target.url, "GET", k, {}) for k in target.query_params
    ]
    for fm in target.forms:
        for k in fm.fields:
            base = {f: v for f, v in fm.fields.items() if f != k}
            units.append((fm.action, fm.method, k, base))
    return units


def inject_param(sess, url: str, method: str, param: str,
                 payload: str, base: dict[str, str]) -> Response:
    """v1 carryover (renamed from `send`). Per-param injection helper
    used by sqli/xss/traversal. 5s timeout preserved from Sprint 1."""
    d = {**base, param: payload}
    if method.upper() == "POST":
        return sess.post(url, data=d, timeout=5, allow_redirects=True)
    return sess.get(url, params=d, timeout=5, allow_redirects=True)
