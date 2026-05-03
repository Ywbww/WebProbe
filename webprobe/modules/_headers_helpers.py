"""Helpers for headers module: hint table + finding factories."""
from __future__ import annotations

from webprobe.findings import Finding

HINTS = {
    "missing_csp": "Add Content-Security-Policy header restricting allowed sources.",
    "missing_x_frame_options": "Set X-Frame-Options: DENY or SAMEORIGIN to prevent clickjacking.",
    "missing_hsts": "Add Strict-Transport-Security with at least max-age=31536000 on HTTPS.",
    "cookie_no_httponly": "Mark cookie HttpOnly to block JavaScript access.",
    "cookie_no_secure": "Mark cookie Secure on HTTPS to prevent plaintext transmission.",
    "cookie_no_samesite": "Set SameSite=Strict or Lax to mitigate CSRF.",
}

HEADER_CHECKS = (("missing_csp", "MEDIUM", "Content-Security-Policy"),
                 ("missing_x_frame_options", "MEDIUM", "X-Frame-Options"))


def hdr_finding(slug: str, sev: str, hdr: str, url: str) -> Finding:
    return Finding(severity=sev, category="headers", finding_type=slug,
                   name=f"Missing {hdr}", url=url,
                   evidence=f"{hdr} header absent on response",
                   remediation=HINTS[slug])


def cookie_finding(slug: str, sev: str, attr: str, cname: str, url: str) -> Finding:
    return Finding(severity=sev, category="cookies", finding_type=slug,
                   name=f"Cookie '{cname}' missing {attr}", url=url,
                   evidence=f"no {attr} attribute on cookie '{cname}'",
                   remediation=HINTS[slug])


def cookie_checks(c, https: bool):
    """Yield (slug, attr, severity) tuples for missing cookie attrs."""
    if not c.has_nonstandard_attr("HttpOnly"):
        yield ("cookie_no_httponly", "HttpOnly", "MEDIUM")
    if https and not c.secure:
        yield ("cookie_no_secure", "Secure", "HIGH")
    if not c.get_nonstandard_attr("SameSite"):
        yield ("cookie_no_samesite", "SameSite", "LOW")
