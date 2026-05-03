"""paths — v1 retrofit (curated-paths shift). Spec: spec.md > v1 retrofit."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from requests.exceptions import RequestException

from webprobe.findings import Source
from webprobe.modules._paths_helpers import FLAGGED_STATUS, mk_finding
from webprobe.modules.base import BaseModule
from webprobe.registry import register

MAX_WORKERS = 20


@register
class PathsModule(BaseModule):
    name = "paths"
    auth_strategy = "unauth_always"
    source_filter = frozenset({Source.CURATED, Source.ROBOTS, Source.URL_LIST})
    FIT3048_CATEGORY_MAP = {"sensitive_path_exposed_high": 1,
                            "sensitive_path_exposed_medium": 1,
                            "sensitive_path_exposed_low": 1}

    def run(self, target, session_factory, report_finding) -> None:
        s = session_factory()[0]
        urls = [u for u, src in target.urls if src in self.source_filter]
        lock = Lock()

        def probe(url: str) -> None:
            try:
                r = s.get(url, timeout=5, allow_redirects=False)
            except RequestException as exc:
                self._on_request_error(url, exc)
                return
            if r.status_code in FLAGGED_STATUS:
                with lock:
                    report_finding(mk_finding(url, r.status_code))

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            list(pool.map(probe, urls))
