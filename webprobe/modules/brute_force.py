"""brute_force — Story 7.6. Spec: spec.md > brute_force.py.

Risk-gated DOUBLE per Story 5.1: requires --include-brute-force AND
--i-own-this-target=<host> on non-testbed targets. Testbed-default
bypasses both flags (Phase 3.6).
"""
from __future__ import annotations

from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES
from webprobe.modules._brute_force_helpers import (
    collect_responses, matches_lockout_signal, no_lockout_finding,
    weak_lockout_finding,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class BruteForceModule(BaseModule):
    name = "brute_force"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"no_lockout": 7, "weak_lockout": 7}
    DATA_FILES = frozenset({"lockout_signals.txt"})

    def run(self, target, session_factory, report_finding) -> None:
        login_url = getattr(self.args, "auth_form", None)
        user = getattr(self.args, "auth_user", None)
        if not login_url or not user:
            return
        try:
            shapes, last_text = collect_responses(login_url, user)
        except RequestException as exc:
            self._on_request_error(login_url, exc)
            return
        if len(set(shapes)) == 1:
            report_finding(no_lockout_finding(login_url))
            return
        if matches_lockout_signal(last_text, self._data["lockout_signals"]):
            return
        report_finding(weak_lockout_finding(login_url))
