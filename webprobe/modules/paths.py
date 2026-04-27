"""Sensitive paths probe: parallel GET against curated path list."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from urllib.parse import urljoin
from requests.exceptions import RequestException

from webprobe.findings import Finding
from webprobe.modules.base import BaseModule
from webprobe.modules._paths_helpers import (
    MAX_WORKERS, DEGRADATION_THRESHOLD, FLAGGED_STATUS,
    DEGRADED_MSG, mk_finding, load_default_paths,
)

__all__ = ["PathsModule", "load_default_paths"]


class PathsModule(BaseModule):
    name, category, degraded = "paths", "paths", False

    def __init__(self, path_list: list[str]):
        self.path_list = path_list

    def run(self, target, session_factory, report_finding) -> list[Finding]:
        base_url = urljoin(target.url, "/")
        findings, lock, streak = [], Lock(), [0]

        def probe(path: str):
            url = urljoin(base_url, path.lstrip("/"))
            try:
                r = session_factory().get(url, timeout=5, allow_redirects=False)
                fail = r.status_code >= 500
            except RequestException:
                r, fail = None, True
            with lock:
                streak[0] = streak[0] + 1 if fail else 0
                if streak[0] >= DEGRADATION_THRESHOLD and not self.degraded:
                    print(DEGRADED_MSG); self.degraded = True
            if r is not None and r.status_code in FLAGGED_STATUS:
                f = mk_finding(path, url, r.status_code)
                with lock:
                    report_finding(f); findings.append(f)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            list(pool.map(probe, self.path_list))
        return findings
