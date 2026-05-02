"""Helpers for csrf module — extracted to keep the module body under the
50-line cap (spec.md > 50-Line Cap)."""
from __future__ import annotations

from urllib.parse import urlsplit

from webprobe.findings import Finding, Form

_EMAIL_PLACEHOLDER = "webprobe@test.invalid"
_USER_PLACEHOLDER = "webprobe-csrf-test"
_ID_PLACEHOLDER = "1"


def fill_field(name: str) -> str:
    """Map a form-field name to a placeholder per spec.md > csrf.py."""
    low = name.lower()
    if "email" in low:
        return _EMAIL_PLACEHOLDER
    if low == "id" or low.endswith("_id"):
        return _ID_PLACEHOLDER
    return _USER_PLACEHOLDER


def is_on_host(form_action: str, target_url: str) -> bool:
    return urlsplit(form_action).netloc.lower() == urlsplit(target_url).netloc.lower()


def build_payload(form: Form) -> dict[str, str]:
    """Strip ALL <input type=hidden> (CSRF tokens are typically hidden) and
    fill remaining fields with placeholders per spec.md > csrf.py."""
    hidden = set(form.hidden_fields)
    return {n: fill_field(n) for n in form.fields if n not in hidden}


def csrf_missing_finding(action: str, status: int) -> Finding:
    return Finding(
        severity="HIGH", category="csrf",
        finding_type="csrf_missing",
        name=f"CSRF accepted without token — POST {action}",
        url=action,
        evidence=("POST without _csrfToken/csrfmiddlewaretoken/"
                  f"authenticity_token returned HTTP {status}"),
        remediation="Add CSRF token validation to POST endpoint.",
    )


def csrf_indeterminate_finding(action: str, status: int) -> Finding:
    return Finding(
        severity="INFO", category="csrf",
        finding_type="csrf_indeterminate",
        name=f"POST returned unexpected status: HTTP {status}",
        url=action,
        evidence="cannot infer CSRF protection from this status",
        remediation="Manual review.",
    )
