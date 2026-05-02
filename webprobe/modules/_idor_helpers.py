"""Helpers for idor module — extracted to keep the module body under the
50-line cap (spec.md > 50-Line Cap). Patterns per spec.md > idor.py:
`/<resource>/<int_id>`, `/<resource>/view/<int_id>`, `?id=N`,
`?<resource>_id=N`."""
from __future__ import annotations

import re
from hashlib import sha256
from urllib.parse import urlsplit, parse_qs

from requests import Response

from webprobe.findings import Finding

# Path-segment integer ID: /resource/47 or /resource/view/47.
_PATH_ID = re.compile(r"/([^/?#]+)/(?:view/)?(\d+)(?:/|$|\?)")
# Query-string integer ID: ?id=47 or ?<resource>_id=47.
_QUERY_ID_KEYS = re.compile(r"^(?:id|[A-Za-z][A-Za-z0-9]*_id)$")
# RFC 4122 UUID shape (8-4-4-4-12 hex).
_UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def id_bearing(url: str) -> bool:
    parts = urlsplit(url)
    if _PATH_ID.search(parts.path or ""):
        return True
    qs = parse_qs(parts.query or "")
    for key, values in qs.items():
        if _QUERY_ID_KEYS.match(key) and values and values[0].isdigit():
            return True
    return False


def uuid_in(url: str) -> bool:
    return bool(_UUID.search(url))


def extract_resource_id(url: str) -> tuple[str, str]:
    """Return (resource_label, id_value) for the first matched id-bearing
    pattern, or ("resource", "?") as a defensive fallback."""
    parts = urlsplit(url)
    m = _PATH_ID.search(parts.path or "")
    if m:
        return m.group(1), m.group(2)
    qs = parse_qs(parts.query or "")
    for key, values in qs.items():
        if _QUERY_ID_KEYS.match(key) and values and values[0].isdigit():
            return key, values[0]
    return "resource", "?"


def baseline_missing_finding(target_url: str) -> Finding:
    return Finding(
        severity="INFO", category="idor",
        finding_type="idor_baseline_missing",
        name="IDOR detection requires --idor-baseline or --idor-baseline-form",
        url=target_url,
        evidence="dual-session unavailable; falling back to single-session "
                 "shape skips the cross-account probe",
        remediation="Pass --idor-baseline-form <login-url> with "
                    "--idor-baseline-user / --idor-baseline-pass.",
    )


def uuid_finding(target_url: str, uuid_paths: list[str]) -> Finding:
    return Finding(
        severity="INFO", category="idor",
        finding_type="uuid_not_supported",
        name="UUID-based resource IDs detected; not enumerated in v2",
        url=target_url,
        evidence=f"{len(uuid_paths)} UUID-shaped path(s); "
                 "Sprint 3+ candidate",
        remediation="Manual testing required for UUID-shaped resource IDs.",
    )


def cross_account_finding(url: str, resp_a: Response, resp_b: Response) -> Finding:
    sha_a = sha256(resp_a.content).hexdigest()
    sha_b = sha256(resp_b.content).hexdigest()
    resource, baseline_id = extract_resource_id(url)
    return Finding(
        severity="HIGH", category="idor",
        finding_type="cross_account_leak",
        name="IDOR — primary user can read baseline-owned resource",
        url=url,
        evidence=(f"Primary GET sha256={sha_a[:16]} == baseline GET "
                  f"sha256={sha_b[:16]}, both HTTP 200"),
        remediation=f"Add ownership check on {resource}.",
        baseline_context=f"baseline owns id={baseline_id}",
    )
