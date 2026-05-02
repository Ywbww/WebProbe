"""Session factory (Module Contract — eager-list factory).

PRD ref: prd.md > Epic 6 > Story 6.4. Spec ref: spec.md > session.py.

v2 contract: `make_session_factory(sessions)` returns a closure that
returns the same list every call. Modules consume via
`session_factory()[0]` (auth_required / unauth_always) or iterate
(IDOR's two-session contract).

The v1 thread-local factory is retired (see spec rationale: 5/6 v2
detection modules dispatch serially, paths is unauth_always with no
shared-state risk, and threading.local doesn't survive multiprocessing
fork). The Sprint 1 `Session` re-export is preserved so v1 modules
that still `from webprobe.session import Session` keep working until
Items 20-22 retrofit them.
"""
from __future__ import annotations

from typing import Callable

import requests
from requests import Session  # noqa: F401  (re-exported for v1 modules)


def make_session_factory(
    sessions: list[requests.Session],
) -> Callable[[], list[requests.Session]]:
    """Identity-shape factory. Returns the same list every call.

    Engine constructs `sessions` during Phase 5; this wraps for module
    consumption. The closure captures `sessions` by reference, so any
    Phase 5 mutation before module dispatch is visible to modules. Once
    Phase 6 begins, the engine treats the list as frozen by convention.
    """
    def factory() -> list[requests.Session]:
        return sessions
    return factory
