"""traversal — v1 retrofit. Spec: spec.md > v1 module retrofit checklist."""
from __future__ import annotations

from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES
from webprobe.modules._common import build_units, inject_param
from webprobe.modules._traversal_helpers import (
    PAYLOADS, matched_signature, mk_finding, path_segment_urls,
)
from webprobe.modules.base import BaseModule
from webprobe.registry import register


@register
class TraversalModule(BaseModule):
    name = "traversal"
    auth_strategy = "follow"
    source_filter = ALL_SOURCES
    FIT3048_CATEGORY_MAP = {"path_traversal_unix": 3, "path_traversal_windows": 3}

    def run(self, target, session_factory, report_finding) -> None:
        sess = session_factory()[0]
        for url, method, param, base in build_units(target, self.source_filter):
            for p in PAYLOADS:
                try:
                    r = inject_param(sess, url, method, param, p, base)
                except RequestException as exc:
                    self._on_request_error(url, exc)
                    continue
                if r.status_code >= 500:
                    continue
                hit = matched_signature(r.text)
                if hit:
                    slug, sig = hit
                    report_finding(mk_finding(url, param, p, slug, sig))
                    break
        for p in PAYLOADS:
            for u in path_segment_urls(target, p):
                try:
                    r = sess.get(u, timeout=5, allow_redirects=True)
                except RequestException as exc:
                    self._on_request_error(u, exc)
                    continue
                if r.status_code >= 500:
                    continue
                hit = matched_signature(r.text)
                if hit:
                    slug, sig = hit
                    report_finding(mk_finding(u, None, p, slug, sig))
