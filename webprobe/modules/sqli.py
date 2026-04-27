"""SQL injection detection: error-string + boolean-differential."""
from __future__ import annotations
from typing import Callable
from requests import Session
from requests.exceptions import RequestException

from webprobe.findings import Finding, Target
from webprobe.modules.base import BaseModule
from webprobe.modules._sqli_helpers import (
    PAYLOADS, DIFF_PAIRS, DEGRADATION_THRESHOLD, DEGRADED_MSG,
    build_units, send, detect_error, diff_hit, err_finding, diff_finding)


class SqliModule(BaseModule):
    name = "sqli"
    category = "sqli"
    degraded = False  # engine ORs this into args.partial after run()

    def run(self, target: Target, session_factory: Callable[[], Session],
            report_finding: Callable[[Finding], None]) -> list[Finding]:
        sess, out, streak = session_factory(), [], 0
        for url, method, param, base in build_units(target):
            resps, hit = {}, False
            for p in PAYLOADS:
                try:
                    r = send(sess, url, method, param, p, base)
                except RequestException:
                    streak = self._fail(streak); continue
                streak = self._fail(streak) if r.status_code >= 500 else 0
                resps[p] = r
                fp = detect_error(r.text.lower())
                if fp and not hit:
                    f = err_finding(url, param, p, fp)
                    out.append(f); report_finding(f); hit = True
            if hit: continue
            for tp, fp in DIFF_PAIRS:
                tr, fr = resps.get(tp), resps.get(fp)
                if tr and fr and diff_hit(tr, fr):
                    f = diff_finding(url, param, tp, fp, tr, fr)
                    out.append(f); report_finding(f); break
        return out

    def _fail(self, streak: int) -> int:
        streak += 1
        if streak >= DEGRADATION_THRESHOLD and not self.degraded:
            print(DEGRADED_MSG); self.degraded = True
        return streak
