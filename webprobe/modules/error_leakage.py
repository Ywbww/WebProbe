"""error_leakage — Story 7.4. Spec: spec.md > error_leakage.py.

Item 17a: Phase 1 user-enumeration probe (real-user vs synthesized
nonexistent-user POST against `--auth-form`). Item 17b layers in the
Phase 2 stack-trace own probe set + pattern matching.
"""
from __future__ import annotations

from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES
from webprobe.modules._error_leakage_helpers import (
    probe_user_enumeration, user_enum_finding,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class ErrorLeakageModule(BaseModule):
    name = "error_leakage"
    auth_strategy = "follow"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {
        "username_enumeration_login": 7,
        "stack_trace_leakage": 1,
    }
    DATA_FILES = frozenset({"stack_trace_patterns.txt"})

    def run(self, target, session_factory, report_finding) -> None:
        # Phase 1: user-enumeration (Cat 7). Requires --auth-form +
        # --auth-user. Skip silently if either is absent — Phase 2 still
        # runs (it doesn't depend on auth flags).
        login_url = getattr(self.args, "auth_form", None)
        user = getattr(self.args, "auth_user", None)
        if login_url and user:
            try:
                result = probe_user_enumeration(login_url, user)
            except RequestException as exc:
                self._on_request_error(login_url, exc)
            else:
                if result is not None:
                    axes, ev_a, ev_b = result
                    report_finding(
                        user_enum_finding(login_url, user, axes, ev_a, ev_b))
