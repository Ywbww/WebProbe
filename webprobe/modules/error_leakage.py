"""error_leakage — Story 7.4. Spec: spec.md > error_leakage.py.

Phase 1 (17a): user-enumeration probe vs `--auth-form`.
Phase 2 (17b): own probe set per Story 7.4.E1 (NOT target.urls).
"""
from __future__ import annotations
from requests.exceptions import RequestException
from webprobe.findings import ALL_SOURCES
from webprobe.modules._common import send
from webprobe.modules._error_leakage_helpers import (
    build_probe_set, match_stack_trace, probe_user_enumeration,
    stack_trace_finding, user_enum_finding,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class ErrorLeakageModule(BaseModule):
    name = "error_leakage"
    auth_strategy = "follow"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {
        "username_enumeration_login": 7, "stack_trace_leakage": 1}
    DATA_FILES = frozenset({"stack_trace_patterns.txt"})

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        login_url = getattr(self.args, "auth_form", None)
        user = getattr(self.args, "auth_user", None)
        if login_url and user:
            try:
                result = probe_user_enumeration(login_url, user)
            except RequestException as exc:
                self._on_request_error(login_url, exc)
            else:
                if result is not None:
                    axes, a, b = result
                    report_finding(user_enum_finding(login_url, user, axes, a, b))
        for probe in build_probe_set(target.url, login_url):
            try:
                resp = send(probe, session=s)
            except RequestException as exc:
                self._on_request_error(probe, exc)
                continue
            m = match_stack_trace(resp.text or "", self._data["stack_trace_patterns"])
            if m is not None:
                report_finding(stack_trace_finding(probe, m[0], m[1]))
