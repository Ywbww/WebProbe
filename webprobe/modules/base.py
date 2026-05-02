"""BaseModule v2 contract.

PRD ref: prd.md > Epic 6 > Story 6.1.
Spec ref: spec.md > Module Contract > BaseModule — extended class-level contract.

Every detection module subclasses this. ≤50 lines per concrete module.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from importlib.resources import files
from typing import Callable, Literal

from requests import Session
from requests.exceptions import RequestException

from webprobe.findings import ALL_SOURCES, Finding, Source, Target


class BaseModule(ABC):
    """Every detection module subclasses this. ≤50 lines per concrete module."""

    # Required class attributes (Phase 1 validation enforces presence):
    name: str                                          # slug, e.g. "access_control"
    auth_strategy: Literal["unauth_always", "follow", "auth_required"]
    FIT3048_CATEGORY_MAP: dict[str, int]               # finding_type → 1..10

    # Optional class attributes (defaults below):
    source_filter: frozenset[Source] = ALL_SOURCES
    DATA_FILES: frozenset[str] = frozenset()           # filenames under webprobe/data/<name>/

    def __init__(self, args=None) -> None:
        """Args injected uniformly per Lock 4. Modules that don't need args
        ignore self.args; modules that do (session, brute_force) read from it.

        Subclass overrides MUST call super().__init__(args) first. Override
        pattern is post-process self._data, NOT replace base loading logic.

        Data files are loaded from `webprobe.data.<self.name>` package via
        importlib.resources. Canonical parsed form: stripped, comment-`#`-skip,
        blank-skip. Keyed by filename without `.txt` extension.
        """
        self.args = args
        self._data: dict[str, list[str]] = {}
        for filename in self.DATA_FILES:
            text = (files("webprobe.data") / self.name / filename).read_text(encoding="utf-8")
            key = filename[:-4] if filename.endswith(".txt") else filename
            self._data[key] = [
                line.strip() for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]

    @abstractmethod
    def run(
        self,
        target: Target,
        session_factory: Callable[[], list[Session]],
        report_finding: Callable[[Finding], None],
    ) -> None:
        """Run this module against `target`.

        - `session_factory()` returns list[Session]. Length 1 in unauth phase
          and unauth_always modules. Length 1-2 in auth phase. IDOR is the
          sole consumer of len > 1; other modules use sessions[0].
        - `report_finding(f)` emits the inline tease at moment of detection.
          Engine wraps this callback per dispatch (per module, per pass) to
          inject auth_context, seen_in, fit3048_category and acquire stdout
          lock. Module body is thread-naive.

        v2 INVARIANT: `run()` returns None. Engine accounting goes through
        the wrapped report_finding callback only, NOT return value. v1's
        `-> list[Finding]` return is dropped.
        """

    def _on_request_error(self, url: str, exception: RequestException) -> None:
        """Default RequestException handler: silent skip. Subclass may override.

        v2 INVARIANT: module body MUST handle RequestException via this hook,
        NOT bare `except Exception` (swallows programmer bugs) or bare
        `except:` (swallows KeyboardInterrupt). Per-request errors flow
        through this hook (Lock 3).
        """
        return None
