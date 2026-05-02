"""idor — Story 7.2. Spec: spec.md > idor.py."""
from __future__ import annotations

from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES
from webprobe.modules._common import compare_responses, send
from webprobe.modules._idor_helpers import (
    baseline_missing_finding, cross_account_finding, id_bearing,
    uuid_finding, uuid_in,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class IdorModule(BaseModule):
    name = "idor"
    auth_strategy = "auth_required"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {
        "cross_account_leak": 2,
        "idor_baseline_missing": 2,
        "uuid_not_supported": 2,
    }

    def run(self, target, session_factory, report_finding) -> None:
        sessions = session_factory()
        if len(sessions) < 2:
            report_finding(baseline_missing_finding(target.url))
            return
        s_a, s_b = sessions[0], sessions[1]
        candidates = [u for u, _ in target.urls if id_bearing(u)]
        uuids = [u for u, _ in target.urls if uuid_in(u)]
        if uuids:
            report_finding(uuid_finding(target.url, uuids))
        for url in candidates:
            try:
                resp_a, resp_b = send(url, session=s_a), send(url, session=s_b)
            except RequestException as exc:
                self._on_request_error(url, exc)
                continue
            if (resp_a.status_code == 200 and resp_b.status_code == 200
                    and compare_responses(resp_a, resp_b)):
                report_finding(cross_account_finding(url, resp_a, resp_b))
