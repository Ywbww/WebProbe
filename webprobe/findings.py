from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from requests import Response

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


@dataclass
class Finding:
    severity: str
    category: str
    name: str
    url: str
    parameter: Optional[str]
    payload: Optional[str]
    evidence: str
    poc_url: Optional[str]
    remediation: str
    fit3048_category: int

    def __post_init__(self):
        assert self.severity in SEVERITY_ORDER, \
            f"invalid severity: {self.severity}"
        assert 1 <= self.fit3048_category <= 10, \
            f"fit3048_category out of range: {self.fit3048_category}"


@dataclass
class Form:
    action: str
    method: str
    fields: dict[str, str]


@dataclass
class Target:
    url: str
    base_response: Response
    forms: list[Form]
    query_params: dict[str, str]
    profile: Optional[str]
