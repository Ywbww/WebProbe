"""session — Story 7.5. Spec: spec.md > session.py.

Phase 1 (18a): post-logout cookie replay via ephemeral sub-session.
Phase 2 (18b): session-fixation + heuristic logout-URL discovery.
Distinct namespace from webprobe/session.py (engine factory).
"""
from __future__ import annotations
from requests.exceptions import RequestException
from webprobe.findings import ALL_SOURCES
from webprobe.modules._session_helpers import (
    cookie_mode_skip_finding, run_fixation_phase, run_logout_phase,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class SessionModule(BaseModule):
    name = "session"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {
        "session_persists_post_logout": 5, "session_fixation": 5,
        "session_skipped_cookie_mode": 5, "logout_endpoint_not_found": 5,
    }

    def run(self, target, session_factory, report_finding) -> None:
        login_url = getattr(self.args, "auth_form", None)
        if not login_url:
            report_finding(cookie_mode_skip_finding(target.url))
            return
        from webprobe.auth import ephemeral_login_form, LoginValidationError
        try:
            ephemeral = ephemeral_login_form(
                target.url, login_url,
                self.args.auth_user, self.args.auth_pass)
        except (LoginValidationError, RequestException) as exc:
            self._on_request_error(login_url, exc)
            return
        run_logout_phase(target.url,
                         getattr(self.args, "logout_url", None),
                         ephemeral, report_finding)
        run_fixation_phase(target.url, login_url,
                           self.args.auth_user, self.args.auth_pass,
                           report_finding)
