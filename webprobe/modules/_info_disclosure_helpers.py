"""Helpers for info_disclosure module: header/HTML scanners + finding factories."""
from __future__ import annotations

import re

from webprobe.findings import Finding

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
INTERNAL_IP_RE = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
)
META_GEN_RE = re.compile(
    r'<meta[^>]+name=[\'"]generator[\'"][^>]+content=[\'"]([^\'"]+)[\'"]',
    re.IGNORECASE,
)
CRED_HINTS = ("password", "passwd", "secret", "api_key", "apikey", "token",
              "DB password", "AWS_SECRET")
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)

REM_BODY = "Strip sensitive data from production HTML/responses; route to logs."


def _trunc(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


def mk(slug: str, sev: str, name: str, url: str, evidence: str) -> Finding:
    return Finding(severity=sev, category="info_disclosure", finding_type=slug,
                   name=name, url=url, evidence=evidence, remediation=REM_BODY)


def scan_emails(text: str, url: str):
    for m in EMAIL_RE.findall(text):
        yield mk("email_in_html", "LOW", "Email address in HTML body",
                 url, f"matched: {m}")


def scan_internal_ips(text: str, url: str):
    for m in INTERNAL_IP_RE.findall(text):
        yield mk("internal_ip_in_html", "LOW",
                 "Internal IP address in HTML body", url, f"matched: {m}")


def scan_comment_creds(text: str, url: str):
    for c in COMMENT_RE.findall(text):
        body = c.strip()
        if any(h.lower() in body.lower() for h in CRED_HINTS):
            yield mk("comment_with_credential", "MEDIUM",
                     "Sensitive HTML comment", url, _trunc(body))


def scan_meta_generator(text: str, url: str):
    m = META_GEN_RE.search(text)
    if m:
        yield mk("meta_generator", "LOW",
                 "Meta generator disclosed", url, f"generator: {m.group(1)}")
