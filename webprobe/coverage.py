"""ScanCoverage + sub-dataclasses + ScanMetadata.

Single source of truth for Story 3.4 JSON envelope target and Story 3.1
terminal/HTML target. Architecture Decision 11: dataclass-shape == JSON-shape
contract — `dataclasses.asdict(coverage)` produces a dict whose key shape
matches the JSON envelope.

Mutable during scan (engine fills incrementally Phase 3.5 -> Phase 7).
Frozen by convention after Phase 7. Phase 8 (render) MUST NOT mutate.
"""
from dataclasses import dataclass, field
from typing import Optional

# Mode invariant lock (Story 3.4 / Item 14b alignment). The four exact
# strings the engine emits into ScanCoverage.mode. Renderers and JSON
# consumers may match against this tuple directly.
MODE_VALUES: tuple[str, ...] = (
    "Unauthenticated",
    "Authenticated, single-session",
    "Authenticated, dual-session",
    "Cookie-session",
)


@dataclass
class LoginProbeResult:
    confirmed: bool
    sessions: list[str]                            # ["coach_a", "coach_b"]
    timestamp: str                                 # "HH:MM:SS"


@dataclass
class SessionCheckResult:
    probe_url: str
    session_attached: bool                         # False -> ambiguous, INFO emitted
    sha256_unauth: str                             # 16-char canonical (Story 3.4.E1)
    sha256_authed: str                             # 16-char canonical
    # Renderers truncate to 8 char for terminal/HTML "Sessions:" line display.
    # Dataclass field and JSON envelope always store 16-char canonical.


@dataclass
class LogoutTestResult:
    cookie_rejected_after_logout: bool
    finding_severity: Optional[str] = None         # "HIGH" if persisted; None if rejected


@dataclass
class PerModuleSourceFilter:
    module_name: str
    accepted_sources: list[str]                    # ["curated", "robots", "url_list"]
    accepted_count: int
    pool_total: int


@dataclass
class WildcardIntents:
    pattern_count: int
    info_finding_id: str                           # cross-ref to consolidated INFO


@dataclass
class ScanCoverage:
    """Story 3.4 JSON envelope target; Story 3.1 terminal/HTML target.

    Engine asserts coverage.duration_seconds and modules_fired are populated
    before render starts.
    """
    mode: str                                      # exactly 4 enum values per Mode invariant
    sessions: list[str]
    urls_probed: dict                              # {"total": 47, "by_source": {...}}
    modules_fired: dict                            # {"scheduled": 10, "completed": 10, "errored": 0}
    duration_seconds: float
    login_probe: Optional[LoginProbeResult] = None
    session_check: Optional[SessionCheckResult] = None
    logout_test: Optional[LogoutTestResult] = None
    per_module_source_filter: list[PerModuleSourceFilter] = field(default_factory=list)
    wildcard_intents: Optional[WildcardIntents] = None


@dataclass
class ScanMetadata:
    """Story 3.4 JSON envelope's `scan` block."""
    target: str
    started_at: str                                # ISO8601 with TZ offset
    completed_at: str
    duration_seconds: float
    exit_code: int
    errored_modules: list[str]
    risk_gates_asserted: list[str]                 # user-typed argv form, case preserved
