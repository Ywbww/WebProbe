"""sqli — v1 retrofit. Spec: spec.md > v1 module retrofit checklist."""
from __future__ import annotations

from requests.exceptions import RequestException

from webprobe.findings import Source
from webprobe.modules._common import build_units, inject_param
from webprobe.modules._sqli_helpers import (
    DIFF_PAIRS, PAYLOADS, detect_error, diff_finding, diff_hit, err_finding,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class SqliModule(BaseModule):
    name = "sqli"
    auth_strategy = "follow"
    source_filter = frozenset({Source.DYNAMIC, Source.URL_LIST})
    FIT3048_CATEGORY_MAP = {"sqli_error_string": 3, "sqli_boolean_diff": 3}

    def run(self, target, session_factory, report_finding) -> None:
        sess = session_factory()[0]
        for url, method, param, base in build_units(target, self.source_filter):
            resps, hit = {}, False
            for p in PAYLOADS:
                try:
                    r = inject_param(sess, url, method, param, p, base)
                except RequestException as exc:
                    self._on_request_error(url, exc)
                    continue
                resps[p] = r
                fp = detect_error(r.text.lower())
                if fp and not hit:
                    report_finding(err_finding(url, param, p, fp))
                    hit = True
            if hit:
                continue
            for tp, fp in DIFF_PAIRS:
                tr, fr = resps.get(tp), resps.get(fp)
                if tr and fr and diff_hit(tr, fr):
                    report_finding(diff_finding(url, param, tp, fp, tr, fr))
                    break
