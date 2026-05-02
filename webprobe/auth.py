"""Authentication & Session Setup (Epic 1).

PRD ref: prd.md > Epic 1 > Stories 1.1, 1.2, 1.3, 1.4, 1.5.
Spec ref: spec.md > Authentication & Session Setup (Epic 1).

Concrete bodies for `setup_form_login` + 3 private helpers land at Item 6a.
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

import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin

import requests
from requests import Response, Session


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


# --- Stub validators (concrete bodies land in Item 6b) -------------------

def validate_auth_flags(args) -> None:
    """Phase 0.5 inter-flag validator. Concrete body lands at Item 6b."""
    return None
