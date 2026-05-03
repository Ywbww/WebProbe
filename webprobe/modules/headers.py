"""headers — v1 retrofit. Spec: spec.md > v1 module retrofit checklist."""
from __future__ import annotations

from webprobe.findings import ALL_SOURCES
from webprobe.modules._headers_helpers import (
    HEADER_CHECKS, cookie_checks, cookie_finding, hdr_finding,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class HeadersModule(BaseModule):
    name = "headers"
    auth_strategy = "follow"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"missing_csp": 4, "missing_hsts": 4,
                            "missing_x_frame_options": 4, "cookie_no_secure": 4,
                            "cookie_no_httponly": 4, "cookie_no_samesite": 4}

    def run(self, target, session_factory, report_finding) -> None:
        h, url = target.base_response.headers, target.url
        https = url.lower().startswith("https://")
        for slug, sev, hdr in HEADER_CHECKS:
            if hdr not in h:
                report_finding(hdr_finding(slug, sev, hdr, url))
        if https and "Strict-Transport-Security" not in h:
            report_finding(hdr_finding(
                "missing_hsts", "HIGH", "Strict-Transport-Security", url))
        for c in target.base_response.cookies:
            for slug, attr, sev in cookie_checks(c, https):
                report_finding(cookie_finding(slug, sev, attr, c.name, url))
