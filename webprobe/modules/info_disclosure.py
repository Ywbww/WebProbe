"""info_disclosure — v1 retrofit. Spec: spec.md > v1 module retrofit checklist."""
from __future__ import annotations

from webprobe.findings import ALL_SOURCES
from webprobe.modules._info_disclosure_helpers import (
    scan_comment_creds, scan_emails, scan_internal_ips, scan_meta_generator,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class InfoDisclosureModule(BaseModule):
    name = "info_disclosure"
    auth_strategy = "follow"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"email_in_html": 6, "internal_ip_in_html": 6,
                            "comment_with_credential": 6, "meta_generator": 6}

    def run(self, target, session_factory, report_finding) -> None:
        url, text = target.url, target.base_response.text
        for scan in (scan_emails, scan_internal_ips,
                     scan_comment_creds, scan_meta_generator):
            for f in scan(text, url):
                report_finding(f)
