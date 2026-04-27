from typing import Callable

from requests import Session

from webprobe.findings import Finding, Target
from webprobe.modules.base import BaseModule

HINTS = {
    "Content-Security-Policy": "Add Content-Security-Policy header restricting allowed sources.",
    "X-Frame-Options": "Set X-Frame-Options: DENY or SAMEORIGIN to prevent clickjacking.",
    "Strict-Transport-Security": "Add Strict-Transport-Security with at least max-age=31536000 on HTTPS.",
    "X-Content-Type-Options": "Set X-Content-Type-Options: nosniff.",
    "Referrer-Policy": "Set Referrer-Policy to limit leaked URL info.",
    "HttpOnly": "Mark cookie HttpOnly to block JavaScript access.",
    "Secure": "Mark cookie Secure on HTTPS to prevent plaintext transmission.",
    "SameSite": "Set SameSite=Strict or Lax to mitigate CSRF.",
}


class HeadersModule(BaseModule):
    name = "headers"
    category = "headers"

    def _mk(self, sev, cat, name, url, fc, ev, rem):
        return Finding(sev, cat, name, url, None, None, ev, None, rem, fc)

    def run(self, target: Target, session_factory: Callable[[], Session],
            report_finding: Callable[[Finding], None]) -> list[Finding]:
        h, url = target.base_response.headers, target.url
        https = url.lower().startswith("https://")
        checks = [("Content-Security-Policy", "MEDIUM"), ("X-Frame-Options", "MEDIUM"),
                  ("X-Content-Type-Options", "LOW"), ("Referrer-Policy", "LOW")]
        if https:
            checks.append(("Strict-Transport-Security", "HIGH"))
        out: list[Finding] = []
        for hdr, sev in checks:
            if hdr not in h:
                out.append(self._mk(sev, "headers", f"Missing {hdr}", url, 5,
                                    "header absent on response", HINTS[hdr]))
        for c in target.base_response.cookies:
            for attr, sev, cond in (("HttpOnly", "MEDIUM", not c.has_nonstandard_attr("HttpOnly")),
                                    ("Secure", "HIGH", https and not c.secure),
                                    ("SameSite", "LOW", not c.get_nonstandard_attr("SameSite"))):
                if cond:
                    out.append(self._mk(sev, "cookies", f"Cookie '{c.name}' missing {attr}",
                                        url, 4, f"no {attr} attribute on cookie '{c.name}'", HINTS[attr]))
        for f in out:
            report_finding(f)
        return out
