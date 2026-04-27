"""Directory traversal detection (opt-in via --include-traversal)."""
from __future__ import annotations
from typing import Callable
from requests import Session
from requests.exceptions import RequestException

from webprobe.findings import Finding, Target
from webprobe.modules.base import BaseModule
from webprobe.modules._common import build_units, send
from webprobe.modules._traversal_helpers import (
    PAYLOADS, DEGRADATION_THRESHOLD, DEGRADED_MSG,
    path_segment_urls, matched_signature, mk_finding,
)


class TraversalModule(BaseModule):
    name = "traversal"
    category = "traversal"
    degraded = False  # engine ORs this into args.partial after run()

    def run(self, target: Target, session_factory: Callable[[], Session],
            report_finding: Callable[[Finding], None]) -> list[Finding]:
        sess, out, streak = session_factory(), [], 0
        for url, method, param, base in build_units(target):  # query + form fields
            for p in PAYLOADS:
                try: r = send(sess, url, method, param, p, base)
                except RequestException: streak = self._fail(streak); continue
                if r.status_code >= 500: streak = self._fail(streak); continue
                streak = 0
                sig = matched_signature(r.text)
                if sig:
                    f = mk_finding(url, param, p, sig)
                    out.append(f); report_finding(f); break  # one per (url, param)
        for p in PAYLOADS:                                      # path-segment surface
            for u in path_segment_urls(target, p):
                try: r = sess.get(u, timeout=5, allow_redirects=True)
                except RequestException: streak = self._fail(streak); continue
                if r.status_code >= 500: streak = self._fail(streak); continue
                streak = 0
                sig = matched_signature(r.text)
                if sig:
                    f = mk_finding(u, None, p, sig)
                    out.append(f); report_finding(f)
        return out

    def _fail(self, streak: int) -> int:
        streak += 1
        if streak >= DEGRADATION_THRESHOLD and not self.degraded:
            print(DEGRADED_MSG); self.degraded = True
        return streak
