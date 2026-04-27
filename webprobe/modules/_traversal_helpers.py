"""Traversal-specific helpers: path-segment surface + finding factory."""
from __future__ import annotations
from urllib.parse import urlparse, urlunparse
from webprobe.findings import Finding, Target

PAYLOADS = [
    "../../../etc/passwd",
    "..%2f..%2f..%2fetc%2fpasswd",
    "....//....//....//etc/passwd",
    "..\\..\\..\\windows\\win.ini",
    "/etc/passwd",
]
DEGRADATION_THRESHOLD = 3
SIGNATURES = ("root:x:0:0:", "[fonts]", "[extensions]")
REMEDIATION = (
    "Canonicalise file paths server-side; reject `..`/`%2f` traversal "
    "sequences before file-system access."
)
DEGRADED_MSG = ("[!] Target appears degraded — 3 consecutive failures.\n"
                "    Completing remaining modules with reduced confidence.")


def path_segment_urls(target: Target, payload: str) -> list[str]:
    """Build candidate URLs replacing each path segment with payload."""
    parts = urlparse(target.url)
    segs = [s for s in parts.path.split("/") if s]
    out: list[str] = []
    for i in range(len(segs)):
        new_segs = list(segs)
        new_segs[i] = payload  # raw — payloads carry their own encoding
        new_path = "/" + "/".join(new_segs)
        out.append(urlunparse(parts._replace(path=new_path)))
    return out


def matched_signature(body: str) -> str | None:
    return next((s for s in SIGNATURES if s in body), None)


def mk_finding(url: str, param: str | None, payload: str, sig: str) -> Finding:
    return Finding(
        severity="CRITICAL", category="traversal",
        name="Path traversal — file disclosure",
        url=url, parameter=param, payload=payload,
        evidence=f"signature {sig!r} found in response body",
        poc_url=url, remediation=REMEDIATION, fit3048_category=3,
    )
