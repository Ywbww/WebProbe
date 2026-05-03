"""xss — v1 retrofit. Spec: spec.md > v1 module retrofit checklist."""
from __future__ import annotations

import html

from requests.exceptions import RequestException

from webprobe.findings import Source
from webprobe.modules._common import build_units, inject_param
from webprobe.modules._xss_helpers import PAYLOADS, reflected_finding
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class XssModule(BaseModule):
    name = "xss"
    auth_strategy = "follow"
    source_filter = frozenset({Source.DYNAMIC, Source.URL_LIST, Source.CURATED})
    FIT3048_CATEGORY_MAP = {"reflected_xss": 3, "stored_xss_candidate": 3}

    def run(self, target, session_factory, report_finding) -> None:
        sess = session_factory()[0]
        for url, method, param, base in build_units(target, self.source_filter):
            for payload in PAYLOADS:
                try:
                    r = inject_param(sess, url, method, param, payload, base)
                except RequestException as exc:
                    self._on_request_error(url, exc)
                    continue
                if r.status_code >= 500:
                    continue
                if payload in r.text and html.escape(payload) not in r.text:
                    report_finding(reflected_finding(url, param, payload))
                    break
