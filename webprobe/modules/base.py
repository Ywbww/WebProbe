from abc import ABC, abstractmethod
from typing import Callable

from requests import Session

from webprobe.findings import Finding, Target


class BaseModule(ABC):
    """Every detection module subclasses this. ≤50 lines per concrete module."""

    name: str       # class attribute, e.g. "sqli". Used in CLI --only and tease lines.
    category: str   # short slug. Often equals `name`; differs only for headers,
                    # which produces both "headers" and "cookies" categories
                    # at the per-Finding level (severity differs by source).

    @abstractmethod
    def run(
        self,
        target: Target,
        session_factory: Callable[[], Session],
        report_finding: Callable[[Finding], None],
    ) -> list[Finding]:
        """
        Run this module against `target`.

        - `session_factory()` returns a thread-local requests.Session. Sequential
          modules call once and reuse; threaded modules call inside each worker.
        - `report_finding(f)` emits the inline [SEVERITY] tease line at the
          moment of detection. Engine wraps this in a stdout lock — modules
          can call from worker threads safely.
        - Returns the same findings the module reported via the callback,
          in module-internal order. The engine uses the return value for
          per-module accounting; the callback drives real-time output.

        Both channels are populated. Redundant by design — they serve
        different consumers.
        """
