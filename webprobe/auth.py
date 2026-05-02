"""Authentication & Session Setup (Epic 1).

PRD ref: prd.md > Epic 1 > Stories 1.1, 1.2, 1.3, 1.4, 1.5.
Spec ref: spec.md > Authentication & Session Setup (Epic 1).

Concrete bodies for `setup_form_login` + 3 private helpers landed at Item 6a.
The remaining helpers (`setup_cookie_session`, `setup_baseline`,
`ephemeral_login_form`, `resolve_password`, `detect_shared_session`,
`validate_auth_flags`) land at Item 6b.

Constraint per spec: the 3 private helpers (`_discover_login_form`,
`_build_login_payload`, `_validate_login_response`) MUST NOT instantiate
or call requests.Session. Network I/O lives in `setup_form_login`'s main
body. This keeps the form-discovery heuristic and field-naming logic
unit-testable without integration test fixtures.
"""
from __future__ import annotations

import getpass
import os
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from typing import Optional
from urllib.parse import urljoin

import requests
from requests import Response, Session

from webprobe.findings import Finding


# --- Custom Exception Hierarchy ------------------------------------------
# Per spec.md > Custom Exception Hierarchy.

class LoginDiscoveryError(Exception):
    """Form not found, multi-step login detected, etc.

    Message MUST be user-actionable (full sentence with remediation).
    Engine prints message verbatim to stderr before sys.exit(1).
    """


class LoginValidationError(Exception):
    """POST succeeded but login didn't (form re-rendered)."""


class PasswordResolutionError(Exception):
    """No flag, no env var, no TTY available."""


class ConfigurationError(Exception):
    """Inter-flag invariant violated (mutex / required-with).

    Engine catches at top level, exits with code 2.
    """


# --- Internal login-form representation ----------------------------------
# Auth-internal dataclass distinct from webprobe.findings.Form (which is the
# v1 generic form record consumed by detection modules). The login form
# carries extra structure — explicit user_field / pass_field / hidden_fields
# — so helpers can stay pure functions over data.

@dataclass
class _LoginForm:
    action: str
    method: str
    user_field: str
    pass_field: str
    hidden_fields: dict[str, str] = field(default_factory=dict)


# Field-name priority lists (Story 1.1 heuristic).
_USER_FIELD_NAME_PRIORITY = ("email", "username", "login", "user", "userid", "user_id")


# --- _discover_login_form ------------------------------------------------

class _FormParser(HTMLParser):
    """Minimal HTML parser to extract <form> elements + <input> children.

    We don't pull in BeautifulSoup; stdlib html.parser handles the
    well-formed login pages we care about and keeps this module
    dependency-light.
    """

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self._current: Optional[dict] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag.lower() == "form":
            self._current = {
                "action": a.get("action", ""),
                "method": (a.get("method", "GET") or "GET").upper(),
                "inputs": [],
            }
            self.forms.append(self._current)
        elif tag.lower() == "input" and self._current is not None:
            self._current["inputs"].append({
                "type": (a.get("type", "text") or "text").lower(),
                "name": a.get("name", ""),
                "value": a.get("value", ""),
            })

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form":
            self._current = None


def _discover_login_form(response: Response, login_url: str) -> tuple[_LoginForm, str]:
    """Pure function: parse <form> with type=password input. Story 1.1.E1
    multi-step detection raises LoginDiscoveryError.

    Returns (form, absolute_action_url). action_url falls back to
    `login_url` when the form's action attribute is empty (HTML default).
    """
    parser = _FormParser()
    try:
        parser.feed(response.text or "")
    except Exception as exc:  # malformed HTML → wrap
        raise LoginDiscoveryError(
            f"Could not parse login page at {login_url} ({type(exc).__name__}). "
            "Verify the URL serves an HTML login form, or override field "
            "selection with --auth-user-field / --auth-pass-field."
        )

    # Find the first form with a password input.
    chosen: Optional[dict] = None
    for f in parser.forms:
        if any(i["type"] == "password" and i.get("name") for i in f["inputs"]):
            chosen = f
            break

    if chosen is None:
        raise LoginDiscoveryError(
            f"No login form with <input type=password> found at {login_url}. "
            "If this page uses a multi-step login or JavaScript-rendered form, "
            "WebProbe cannot auto-discover it; supply a cookie via --cookie."
        )

    inputs = chosen["inputs"]
    pass_input = next(i for i in inputs if i["type"] == "password" and i["name"])
    pass_field = pass_input["name"]

    # User-field heuristic: input[type=text|email] immediately preceding password.
    pass_idx = inputs.index(pass_input)
    user_field: Optional[str] = None
    for i in reversed(inputs[:pass_idx]):
        if i["type"] in ("text", "email") and i["name"]:
            user_field = i["name"]
            break

    # Fallback 1: sole non-password text/email input.
    if user_field is None:
        text_inputs = [
            i for i in inputs if i["type"] in ("text", "email") and i["name"]
        ]
        if len(text_inputs) == 1:
            user_field = text_inputs[0]["name"]

    # Fallback 2: priority-named field (email, username, ...).
    if user_field is None:
        for candidate in _USER_FIELD_NAME_PRIORITY:
            for i in inputs:
                if i["name"].lower() == candidate and i["type"] in ("text", "email"):
                    user_field = i["name"]
                    break
            if user_field is not None:
                break

    if user_field is None:
        raise LoginDiscoveryError(
            f"Found a password input at {login_url} but could not identify "
            "the username field. Override with --auth-user-field <name>."
        )

    # Hidden fields preserved verbatim (CakePHP _csrfToken, Django
    # csrfmiddlewaretoken, Rails authenticity_token, Laravel _token).
    hidden_fields = {
        i["name"]: i["value"]
        for i in inputs
        if i["type"] == "hidden" and i["name"]
    }

    action = chosen["action"] or ""
    action_url = urljoin(login_url, action) if action else login_url

    form = _LoginForm(
        action=action,
        method=chosen["method"],
        user_field=user_field,
        pass_field=pass_field,
        hidden_fields=hidden_fields,
    )
    return form, action_url


# --- _build_login_payload ------------------------------------------------

def _build_login_payload(form: _LoginForm, user: str, password: str) -> dict[str, str]:
    """Pure function: apply Story 1.1 field heuristic. Preserve all
    <input type=hidden> verbatim.

    Pure over data; no I/O. Hidden fields go in first so user/pass can
    overwrite if a server reuses a hidden name (defensive — shouldn't
    happen, but predictable last-write-wins beats undefined order).
    """
    payload: dict[str, str] = {}
    payload.update(form.hidden_fields)
    payload[form.user_field] = user
    payload[form.pass_field] = password
    return payload


# --- _validate_login_response --------------------------------------------

_PASSWORD_INPUT_RE = re.compile(
    r"<input\b[^>]*\btype\s*=\s*[\"']?password[\"']?", re.IGNORECASE
)


def _validate_login_response(response: Response, login_url: str, user: str) -> None:
    """Pure function: redirect away from login_url = success;
    same URL with form re-rendered = failure.

    Heuristic per spec: if final URL still resolves to the login URL AND
    body still contains an <input type=password>, the server re-rendered
    the form → credential rejection. Otherwise treat as success.
    """
    final_url = response.url or ""
    same_url = final_url.rstrip("/") == login_url.rstrip("/")
    body = response.text or ""
    form_re_rendered = bool(_PASSWORD_INPUT_RE.search(body))

    if same_url and form_re_rendered:
        raise LoginValidationError(
            f"Login as {user!r} at {login_url} failed: server re-rendered the "
            "login form (credentials likely rejected). If the username/password "
            "fields were misidentified, override with --auth-user-field "
            "and/or --auth-pass-field."
        )


# --- setup_form_login ----------------------------------------------------

def setup_form_login(
    target_url: str,
    login_url: str,
    user: str,
    password: str,
    *,
    verbose: bool = True,
) -> Session:
    """Story 1.1 form-login auto-discovery + POST + validation.

    Composition: GET login_url -> _discover_login_form -> _build_login_payload
    -> POST -> _validate_login_response -> return Session.

    `verbose=False` suppresses the scan-stream "[*] Logging in as ..." line
    so ephemeral_login_form() can keep ephemeral sessions truly ephemeral
    (no scan-stream footprint, only target-side auth log entry).
    """
    sess = requests.Session()
    try:
        resp = sess.get(login_url, allow_redirects=True, timeout=10)
    except requests.RequestException as exc:
        raise LoginDiscoveryError(
            f"Could not GET login page {login_url} ({type(exc).__name__}: {exc}). "
            "Verify --auth-form points at the login page URL, not the form's "
            "POST action."
        )

    form, action_url = _discover_login_form(resp, login_url)

    payload = _build_login_payload(form, user, password)

    if verbose:
        print(f"[*] Logging in as {user}...", file=sys.stderr)

    try:
        login_resp = sess.post(action_url, data=payload, allow_redirects=True, timeout=10)
    except requests.RequestException as exc:
        raise LoginValidationError(
            f"POST to login form action {action_url} failed "
            f"({type(exc).__name__}: {exc})."
        )

    try:
        _validate_login_response(login_resp, login_url, user)
    except LoginValidationError:
        if verbose:
            print(f"[-] Login as {user} failed", file=sys.stderr)
        raise

    if verbose:
        print(f"[+] Login confirmed", file=sys.stderr)

    return sess


# --- setup_cookie_session ------------------------------------------------

def setup_cookie_session(cookie_string: str) -> Session:
    """Story 1.2: parse RFC 6265 Cookie header form, attach to Session.

    `cookie_string` is the same shape browsers send in the Cookie header:
    `name=value; name2=value2; ...`. http.cookies.SimpleCookie covers the
    common case; we strip leading whitespace per RFC 6265 §5.2.
    """
    sess = requests.Session()
    if not cookie_string or not cookie_string.strip():
        return sess
    jar = SimpleCookie()
    jar.load(cookie_string)
    for name, morsel in jar.items():
        sess.cookies.set(name, morsel.value)
    return sess


# --- resolve_password ----------------------------------------------------

def resolve_password(
    flag_value: Optional[str],
    env_var_name: str,
    prompt_text: str,
) -> str:
    """Story 1.5 priority chain: explicit flag -> env var -> getpass prompt.

    Raises PasswordResolutionError on non-interactive TTY + no flag + no env.
    `stream=sys.stderr` per getpass docs — keeps prompt off stdout (critical
    for `--json-out -` mode).
    """
    if flag_value is not None:
        return flag_value
    env = os.environ.get(env_var_name)
    if env is not None:
        return env
    if not sys.stdin.isatty():
        raise PasswordResolutionError(
            f"password resolution failed: no flag set, no {env_var_name} "
            "env var, no TTY available; use --auth-pass or set the env var"
        )
    return getpass.getpass(prompt=prompt_text, stream=sys.stderr)


# --- setup_baseline ------------------------------------------------------

def setup_baseline(args, target_url: str) -> Optional[Session]:
    """Story 1.3 multi-session contract. Owns inter-flag invariants:
    --idor-baseline / --idor-baseline-form mutex; --idor-baseline-form
    requires --idor-baseline-user. Raises ConfigurationError on violation.
    """
    idor_baseline = getattr(args, "idor_baseline", None)
    idor_baseline_form = getattr(args, "idor_baseline_form", None)
    idor_baseline_user = getattr(args, "idor_baseline_user", None)
    idor_baseline_pass = getattr(args, "idor_baseline_pass", None)

    if idor_baseline and idor_baseline_form:
        raise ConfigurationError(
            "--idor-baseline and --idor-baseline-form are mutually exclusive. "
            "Pick cookie-based baseline (--idor-baseline) or form-based "
            "baseline (--idor-baseline-form), not both."
        )
    if idor_baseline_form and not idor_baseline_user:
        raise ConfigurationError(
            "--idor-baseline-form requires --idor-baseline-user."
        )
    if idor_baseline:
        return setup_cookie_session(idor_baseline)
    if idor_baseline_form:
        pw = resolve_password(
            idor_baseline_pass,
            "WEBPROBE_IDOR_BASELINE_PASS",
            f"[Password for {idor_baseline_user}]: ",
        )
        return setup_form_login(
            target_url, idor_baseline_form, idor_baseline_user, pw
        )
    return None


# --- ephemeral_login_form ------------------------------------------------

def ephemeral_login_form(
    target_url: str,
    login_url: str,
    user: str,
    password: str,
) -> Session:
    """Story 1.4: build a one-shot disposable Session via fresh form-login.

    Used by Story 7.5's session module for post-logout cookie-replay test.
    Returned Session is independent of primary/baseline list — destruction
    by logout does not affect sessions[0] or sessions[1]. Caller is
    responsible for using-then-discarding; engine never stores ephemeral
    Sessions.

    Side effect to document in README per Story 7.5: throwaway session is
    +1 login event in target's auth log.
    """
    return setup_form_login(target_url, login_url, user, password, verbose=False)


# --- detect_shared_session -----------------------------------------------

# Story 1.3.E1: module-private constant. NOT user-configurable via CLI flag —
# detection heuristic must be predictable. User-configurable list is
# Sprint 3+ candidate. Append at /build if Team 157 testbed shape uses an
# unusual session cookie name.
_SHARED_SESSION_COOKIE_NAMES: frozenset[str] = frozenset({
    "PHPSESSID",
    "laravel_session",
    "_session_id",
    "connect.sid",
    "JSESSIONID",
    "ci_session",
    "sessionid",
    "ASP.NET_SessionId",
    "session",
    "_session",
    "CAKEPHP",
})


def detect_shared_session(sessions: list[Session]) -> Optional[Finding]:
    """Story 1.3.E1: cookie equality check across sessions.

    Returns INFO Finding if two sessions share the same value for any
    well-known session cookie name (suggests baseline session and primary
    session both authenticated as the same user — multi-session IDOR
    cross-checks would yield false negatives). None if no overlap.
    """
    if len(sessions) < 2:
        return None
    # Compare sessions pairwise. With sessions[0] (primary) and sessions[1]
    # (baseline) being the only expected shape today, this is O(1) in
    # practice; loop kept generic.
    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            shared = _shared_named_cookies(sessions[i], sessions[j])
            if shared:
                names = ", ".join(sorted(shared))
                return Finding(
                    severity="INFO",
                    category="auth",
                    finding_type="shared_session_detected",
                    name="Primary and baseline sessions share a session cookie",
                    url="(local)",
                    evidence=(
                        f"Sessions {i} and {j} share identical session cookie "
                        f"value(s) for: {names}. The baseline credential may "
                        "have authenticated as the same user as the primary "
                        "credential, defeating multi-session IDOR cross-checks."
                    ),
                    remediation=(
                        "Verify --idor-baseline / --idor-baseline-form points "
                        "at a distinct user account from the primary --auth-* "
                        "credentials."
                    ),
                )
    return None


def _shared_named_cookies(a: Session, b: Session) -> set[str]:
    """Return the set of well-known session cookie names where `a` and `b`
    have the same value. Pure helper over Session.cookies."""
    a_cookies = {c.name: c.value for c in a.cookies if c.name in _SHARED_SESSION_COOKIE_NAMES}
    b_cookies = {c.name: c.value for c in b.cookies if c.name in _SHARED_SESSION_COOKIE_NAMES}
    return {
        name for name, val in a_cookies.items()
        if name in b_cookies and b_cookies[name] == val
    }


# --- validate_auth_flags -------------------------------------------------

def validate_auth_flags(args) -> None:
    """Phase 0.5 inter-flag validator. Raises ConfigurationError on conflict.

    Invariants:
      - mutex: --cookie / --auth-form
      - required-with: --auth-form needs --auth-user
      - password chain feasibility (delegated to resolve_password at
        Phase 5a — we don't pre-resolve here since resolve_password may
        prompt a TTY and Phase 0.5 must stay non-interactive).

    --idor-baseline / --idor-baseline-form mutex lives in setup_baseline()
    per spec (Phase 5c); we do NOT duplicate it here so failure surfaces
    at the consuming phase.
    """
    cookie = getattr(args, "cookie", None)
    auth_form = getattr(args, "auth_form", None)
    auth_user = getattr(args, "auth_user", None)

    if cookie and auth_form:
        raise ConfigurationError(
            "--cookie and --auth-form are mutually exclusive. Pick "
            "cookie-based auth (--cookie) or form-based auth (--auth-form), "
            "not both."
        )
    if auth_form and not auth_user:
        raise ConfigurationError(
            "--auth-form requires --auth-user."
        )
