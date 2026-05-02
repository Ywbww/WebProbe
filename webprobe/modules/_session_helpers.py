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

import requests
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


def find_logout_url(target_url: str, explicit: Optional[str],
                    ephemeral: Session) -> Optional[str]:
    """Resolve the logout URL. Explicit --logout-url wins. Otherwise
    probe heuristic paths via GET (HEAD/OPTIONS isn't reliably routed
    by Flask test apps); first 2xx/3xx response wins. Returns None
    when no candidate responds positively."""
    if explicit:
        return explicit
    candidates = [
        urljoin(target_url, p) for p in (
            "/logout", "/signout", "/users/logout",
            "/sessions/destroy", "/logout/",
        )
    ]
    for candidate in candidates:
        try:
            r = ephemeral.get(candidate, timeout=DEFAULT_TIMEOUT,
                              allow_redirects=False)
        except RequestException:
            continue
        if 200 <= r.status_code < 400:
            return candidate
    return None


def test_post_logout(target_url: str, logout_url: str, ephemeral: Session
                     ) -> Optional[tuple[str, tuple[int, str],
                                         tuple[int, str], list[str]]]:
    """Phase 1: GET protected URL, POST (then GET) logout, GET protected
    URL again. Returns (protected_url, pre_shape, post_shape,
    overlap_markers) when persistence detected; None on correct
    invalidation. Protected URL is target.url itself (engine has
    already proven the primary session gets authed content there).
    """
    resp_pre = ephemeral.get(target_url, timeout=DEFAULT_TIMEOUT,
                             allow_redirects=True)
    pre_shape = _shape(resp_pre)
    pre_body = resp_pre.text or ""
    try:
        ephemeral.post(logout_url, timeout=DEFAULT_TIMEOUT,
                       allow_redirects=False)
    except RequestException:
        # POST may 405 on GET-only logouts — fall back to GET.
        ephemeral.get(logout_url, timeout=DEFAULT_TIMEOUT,
                      allow_redirects=False)
    resp_post = ephemeral.get(target_url, timeout=DEFAULT_TIMEOUT,
                              allow_redirects=True)
    post_shape = _shape(resp_post)
    post_body = resp_post.text or ""
    overlap = _overlap_markers(pre_body, post_body)
    same_sha = pre_shape[1] == post_shape[1]
    both_200 = pre_shape[0] == 200 and post_shape[0] == 200
    if same_sha or (both_200 and overlap):
        return target_url, pre_shape, post_shape, overlap
    return None


def logout_not_found_finding(target_url: str) -> Finding:
    return Finding(
        severity="INFO", category="session",
        finding_type="logout_endpoint_not_found",
        name="Logout endpoint not auto-discovered",
        url=target_url,
        evidence=("Heuristic GET probes against /logout, /signout, "
                  "/users/logout, /sessions/destroy, /logout/ all "
                  "returned no 2xx/3xx response."),
        remediation=("Pass --logout-url=<path> if logout exists at a "
                     "non-standard URL; without it, post-logout cookie-"
                     "replay cannot be tested."),
    )


# Session-fixation: well-known cookie names whose value should rotate
# across an authentication state transition. Mirrors auth._SHARED_
# SESSION_COOKIE_NAMES but local-private to keep import boundaries clean.
_FIXATION_COOKIE_NAMES: tuple[str, ...] = (
    "PHPSESSID", "JSESSIONID", "laravel_session", "sessionid",
    "ASP.NET_SessionId", "ci_session", "connect.sid",
    "_session_id", "session", "_session", "CAKEPHP",
)


def test_session_fixation(target_url: str, login_url: str, user: str,
                          password: str
                          ) -> Optional[tuple[str, str, str]]:
    """Phase 2: anonymous GET login URL captures Set-Cookie. Login with
    that cookie attached. If the post-login cookie value matches the
    pre-login value for any well-known session-cookie name → fixation.
    Returns (cookie_name, pre_value, post_value) on hit; None otherwise.
    Network errors propagate to the caller."""
    pre_sess = requests.Session()
    pre_sess.get(login_url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    pre_cookies = {c.name: c.value for c in pre_sess.cookies
                   if c.name in _FIXATION_COOKIE_NAMES}
    if not pre_cookies:
        return None
    # We can't use setup_form_login (it allocates a fresh Session,
    # discarding our pre-cookie). Re-use the pure form-discovery + payload
    # builders from auth, then POST through pre_sess directly so the
    # pre-cookie travels with the login request.
    from webprobe.auth import (
        LoginDiscoveryError, _build_login_payload, _discover_login_form,
    )
    try:
        resp = pre_sess.get(login_url, timeout=DEFAULT_TIMEOUT,
                            allow_redirects=True)
        form, action_url = _discover_login_form(resp, login_url)
    except LoginDiscoveryError:
        return None
    payload = _build_login_payload(form, user, password)
    pre_sess.post(action_url, data=payload,
                  timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    post_cookies = {c.name: c.value for c in pre_sess.cookies
                    if c.name in _FIXATION_COOKIE_NAMES}
    for name, pre_val in pre_cookies.items():
        post_val = post_cookies.get(name)
        if post_val is not None and post_val == pre_val:
            return name, pre_val, post_val
    return None


def run_logout_phase(target_url: str, explicit_logout: Optional[str],
                     ephemeral: Session, report_finding) -> None:
    """Phase 1 coordinator: discover logout URL, replay session, emit
    HIGH session_persists_post_logout on persistence; INFO
    logout_endpoint_not_found when discovery fails. RequestException
    inside test_post_logout is the caller's problem (post-discovery
    failures suggest the logout URL itself is broken)."""
    logout_url = find_logout_url(target_url, explicit_logout, ephemeral)
    if logout_url is None:
        report_finding(logout_not_found_finding(target_url))
        return
    try:
        result = test_post_logout(target_url, logout_url, ephemeral)
    except RequestException:
        return
    if result is not None:
        report_finding(post_logout_finding(*result))


def run_fixation_phase(target_url: str, login_url: str, user: str,
                       password: str, report_finding) -> None:
    """Phase 2 coordinator. Network errors swallowed: fixation detection
    is best-effort and shouldn't crash the module on a flaky login URL."""
    try:
        fix = test_session_fixation(target_url, login_url, user, password)
    except RequestException:
        return
    if fix is not None:
        report_finding(fixation_finding(login_url, *fix))


def fixation_finding(login_url: str, cookie_name: str,
                     pre_val: str, post_val: str) -> Finding:
    return Finding(
        severity="MEDIUM", category="session",
        finding_type="session_fixation",
        name="Session ID not regenerated on login",
        url=login_url,
        evidence=(f"Pre-login cookie {cookie_name}={pre_val[:8]}; "
                  f"post-login cookie {cookie_name}={post_val[:8]}; "
                  "identical."),
        remediation=("Regenerate session ID on authentication state "
                     "transition (login/logout). Most frameworks have "
                     "a session.regenerate() / session.regenerate_id() "
                     "helper."),
    )
