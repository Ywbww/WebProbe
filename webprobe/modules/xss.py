"""Reflected XSS detection: payload appears unescaped in response body."""
from __future__ import annotations
import html
from typing import Callable
from requests import Session
from requests.exceptions import RequestException

from webprobe.findings import Finding, Target
from webprobe.modules.base import BaseModule
from webprobe.modules._common import build_units, send
from webprobe.modules._xss_helpers import (
    PAYLOADS, DEGRADATION_THRESHOLD, DEGRADED_MSG, mk_finding,
)


class XssModule(BaseModule):
    name = "xss"
    category = "xss"
    degraded = False  # engine ORs this into args.partial after run()

    def run(self, target: Target, session_factory: Callable[[], Session],
            report_finding: Callable[[Finding], None]) -> list[Finding]:
        sess, out, streak = session_factory(), [], 0
        for url, method, param, base in build_units(target):
            for payload in PAYLOADS:
                try:
                    r = send(sess, url, method, param, payload, base)
                except RequestException:
                    streak = self._fail(streak); continue
                if r.status_code >= 500:
                    streak = self._fail(streak); continue
                streak = 0
                if payload in r.text and html.escape(payload) not in r.text:
                    f = mk_finding(url, param, payload)
                    out.append(f); report_finding(f)
                    break  # one finding per param
        return out

    def _fail(self, streak: int) -> int:
        streak += 1
        if streak >= DEGRADATION_THRESHOLD and not self.degraded:
            print(DEGRADED_MSG); self.degraded = True
        return streak
