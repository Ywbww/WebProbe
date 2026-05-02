"""Helpers for session module — extracted to keep the module body under
the 50-line cap (spec.md > 50-Line Cap).

Item 18a: post-logout cookie replay (`test_post_logout`,
`post_logout_finding`, `cookie_mode_skip_finding`). Item 18b layers
on session-fixation + logout-URL discovery helpers.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Optional
from urllib.parse import urljoin

from requests import Session
from requests.exceptions import RequestException

from webprobe.findings import Finding
from webprobe.modules._common import DEFAULT_TIMEOUT


# Surface markers for the "still-authenticated" overlap heuristic. We
# cast a wide net — any of these on both pre- and post-logout response
# bodies tilts toward "session was not invalidated". Lowercased on
# comparison to absorb framework casing differences.
_AUTHED_MARKERS: tuple[str, ...] = (
    "logout", "sign out", "log out", "my account",
    "dashboard", "welcome,", "welcome ", "profile",
)


def _shape(resp) -> tuple[int, str]:
    return resp.status_code, sha256(resp.content).hexdigest()


def _overlap_markers(body_a: str, body_b: str) -> list[str]:
    a_low = (body_a or "").lower()
    b_low = (body_b or "").lower()
    return [m for m in _AUTHED_MARKERS if m in a_low and m in b_low]


def cookie_mode_skip_finding(target_url: str) -> Finding:
    return Finding(
        severity="INFO", category="session",
        finding_type="session_skipped_cookie_mode",
        name="Session detection skipped (cookie-mode)",
        url=target_url,
        evidence=("Ephemeral sub-session creation requires --auth-form for "
                  "fresh login attempts; --cookie reuses an existing "
                  "session and cannot be safely re-authenticated."),
        remediation=("Pass --auth-form (with --auth-user / --auth-pass) "
                     "to enable post-logout cookie-replay + fixation tests, "
                     "or accept that logout-correctness is not tested in "
                     "this scan."),
    )


def post_logout_finding(protected_url: str, pre_shape: tuple[int, str],
                        post_shape: tuple[int, str],
                        overlap: list[str]) -> Finding:
    detail = (
        f"pre-logout {pre_shape[0]}/{pre_shape[1][:8]}, "
        f"post-logout {post_shape[0]}/{post_shape[1][:8]}"
    )
    if pre_shape[1] == post_shape[1]:
        detail += " — body sha256 IDENTICAL"
    elif overlap:
        detail += f" — overlap markers: {', '.join(overlap)}"
    return Finding(
        severity="HIGH", category="session",
        finding_type="session_persists_post_logout",
        name="Session cookie still valid after logout",
        url=protected_url,
        evidence=("Authed page rendered identically before and after a "
                  "logout request: " + detail + "."),
        remediation=("Invalidate session server-side on logout (call "
                     "session.clear() / session.invalidate() / equivalent); "
                     "do not rely on client-side cookie deletion alone."),
    )


def test_post_logout(target_url: str, login_url: str, logout_candidates: list[str],
                     ephemeral: Session) -> Optional[tuple[str, tuple[int, str], tuple[int, str], list[str]]]:
    """Phase 1: GET protected URL, POST/GET logout, GET protected URL again.
    Returns (protected_url, pre_shape, post_shape, overlap_markers) when
    persistence detected; None on no-divergence (session correctly
    invalidated). Raises RequestException on network failure — caller
    routes through _on_request_error.

    Protected URL is target.url itself: it's the URL the engine has
    already proven returns content under the primary session.
    """
    protected_url = target_url
    resp_pre = ephemeral.get(protected_url, timeout=DEFAULT_TIMEOUT,
                              allow_redirects=True)
    pre_shape = _shape(resp_pre)
    pre_body = resp_pre.text or ""
    # Try each logout candidate; first 2xx/3xx wins.
    fired = False
    for candidate in logout_candidates:
        try:
            r = ephemeral.post(candidate, timeout=DEFAULT_TIMEOUT,
                                allow_redirects=False)
        except RequestException:
            continue
        if 200 <= r.status_code < 400:
            fired = True
            break
        # Some apps expose GET /logout that 302s — accept either verb.
        try:
            r2 = ephemeral.get(candidate, timeout=DEFAULT_TIMEOUT,
                                allow_redirects=False)
        except RequestException:
            continue
        if 200 <= r2.status_code < 400:
            fired = True
            break
    if not fired:
        return None
    resp_post = ephemeral.get(protected_url, timeout=DEFAULT_TIMEOUT,
                               allow_redirects=True)
    post_shape = _shape(resp_post)
    post_body = resp_post.text or ""
    overlap = _overlap_markers(pre_body, post_body)
    same_sha = pre_shape[1] == post_shape[1]
    both_200 = pre_shape[0] == 200 and post_shape[0] == 200
    if same_sha or (both_200 and overlap):
        return protected_url, pre_shape, post_shape, overlap
    return None


def default_logout_candidates(target_url: str,
                              explicit: Optional[str]) -> list[str]:
    """Logout-URL list. Explicit --logout-url first; then heuristic
    paths in order of how often we see them in the wild."""
    if explicit:
        return [explicit]
    return [
        urljoin(target_url, "/logout"),
        urljoin(target_url, "/signout"),
        urljoin(target_url, "/users/logout"),
        urljoin(target_url, "/sessions/destroy"),
        urljoin(target_url, "/logout/"),
    ]
