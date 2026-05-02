"""v2 type definitions: Source enum, Finding/Form/Target dataclasses.

Pure type-definition module. Permitted contents: dataclasses, enums,
type-level constants, validation invariants. NOT permitted: I/O, processing
logic, helpers acting on findings.

Import scope lock: ONLY {dataclasses, enum, hashlib, typing}. Third-party
modules (e.g. requests.Response) live elsewhere; Target.base_response uses
a forward reference so this module stays self-contained.
"""
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Literal, Optional

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


class Source(str, Enum):
    """URL discovery source taxonomy. str mixin for cheap JSON serialization."""
    SITEMAP = "sitemap"
    ROBOTS = "robots"
    URL_LIST = "url_list"
    DYNAMIC = "dynamic"
    CURATED = "curated"


ALL_SOURCES: frozenset[Source] = frozenset(Source)


@dataclass(kw_only=True)
class Finding:
    """v2 finding. kw_only=True forbids positional construction — readability
    discipline so module body always reads as
    Finding(severity="HIGH", category="csrf", finding_type=..., ...).
    """
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    category: str                                  # module-identity slug
    finding_type: str                              # FIT3048_CATEGORY_MAP key
    name: str                                      # human-readable title
    url: str
    evidence: str
    remediation: str

    # Optional user-content fields (module sets if relevant):
    payload: Optional[str] = None
    poc_url: Optional[str] = None
    parameter: Optional[str] = None                # v1 carryover

    # Engine-injected fields (None at construction; wrapper fills before render):
    auth_context: Optional[str] = None             # context-dependent
    baseline_context: Optional[str] = None         # IDOR-only, module-set
    seen_in: list[str] = field(default_factory=list)  # ["unauth"] or ["authed"] or both
    fit3048_category: Optional[int] = None         # context-dependent (lookup)
    evidence_hash: Optional[str] = None            # self-contained, auto-computed below

    def __post_init__(self) -> None:
        # Severity validation (always)
        assert self.severity in SEVERITY_ORDER, f"invalid severity: {self.severity}"

        # finding_type non-empty (always)
        assert self.finding_type, "finding_type must be non-empty"

        # fit3048_category range (only if set; engine wrapper guarantees non-None at storage)
        if self.fit3048_category is not None:
            if not 1 <= self.fit3048_category <= 10:
                raise ValueError(
                    f"fit3048_category must be 1..10, got {self.fit3048_category}. "
                    f"See FIT3048_CATEGORY_MAP in module class."
                )

        # evidence_hash auto-computed from constructor args (self-contained)
        if self.evidence_hash is None:
            self.evidence_hash = sha256(
                f"{self.category}:{self.url}:{self.evidence}".encode()
            ).hexdigest()[:16]


@dataclass
class Form:                                        # v1 + v2 hidden_fields
    action: str
    method: str
    fields: dict[str, str]
    # v2 addition: names of <input type="hidden"> entries in the form. CSRF
    # module strips these per Story 7.3 ("strip ALL hidden inputs"). v1
    # callers ignore the field; default = empty list keeps v1 construction
    # `Form(action, method, fields)` working positionally.
    hidden_fields: list[str] = field(default_factory=list)


@dataclass
class Target:                                      # v1 + v2 urls field
    url: str
    base_response: Any                             # requests.Response (no import: type-only module)
    forms: list[Form]
    query_params: dict[str, str]
    profile: Optional[str]
    urls: tuple[tuple[str, Source], ...] = ()      # frozen URL pool (Phase 4 freeze)
