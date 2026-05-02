"""access_control — Story 7.1. Spec: spec.md > access_control.py."""
from __future__ import annotations

from urllib.parse import urljoin
from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES
from webprobe.modules._access_control_helpers import (
    ambiguous_summary_finding, match_admin_signal, role_violation_finding,
)
from webprobe.modules._common import send
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class AccessControlModule(BaseModule):
    name = "access_control"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"role_violation": 2, "ambiguous_200_summary": 2}
    DATA_FILES = frozenset({"admin_paths.txt", "admin_signals.txt"})

    def __init__(self, args=None) -> None:
        super().__init__(args)
        self._signals_lower = [s.lower() for s in self._data["admin_signals"]]

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        ambiguous: list[str] = []
        for path in self._data["admin_paths"]:
            url = urljoin(target.url, path)
            try:
                resp = send(url, session=s)
            except RequestException as exc:
                self._on_request_error(url, exc)
                continue
            if resp.status_code != 200:
                continue
            matched = match_admin_signal(
                resp.text, self._data["admin_signals"], self._signals_lower)
            if matched is not None:
                report_finding(role_violation_finding(path, url, matched))
            else:
                ambiguous.append(path)
        if ambiguous:
            report_finding(ambiguous_summary_finding(target.url, ambiguous))
