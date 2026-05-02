"""csrf — Story 7.3. Spec: spec.md > csrf.py.

Known limitation: Rails forms sometimes use a hidden `_method` field to
override POST transport into PATCH/PUT/DELETE. This module does NOT
auto-detect that override and treats every form with `method="POST"` at
the markup level as a POST endpoint. Manual review required for Rails
apps. (Story 7.3.E2 lock.)
"""
from __future__ import annotations

from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES
from webprobe.modules._common import DEFAULT_TIMEOUT
from webprobe.modules._csrf_helpers import (
    build_payload, csrf_indeterminate_finding, csrf_missing_finding, is_on_host,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class CsrfModule(BaseModule):
    name = "csrf"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"csrf_missing": 2, "csrf_indeterminate": 2}

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        for form in target.forms:
            if form.method.upper() != "POST":
                continue
            if not is_on_host(form.action, target.url):
                continue
            payload = build_payload(form)
            try:
                resp = s.post(form.action, data=payload,
                              allow_redirects=False, timeout=DEFAULT_TIMEOUT)
            except RequestException as exc:
                self._on_request_error(form.action, exc)
                continue
            status = resp.status_code
            if status in (403, 419):
                continue
            if status in (200, 302, 204):
                report_finding(csrf_missing_finding(form.action, status))
            elif 400 <= status < 500:
                report_finding(csrf_indeterminate_finding(form.action, status))
