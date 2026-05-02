"""Versioned JSON envelope renderer (Story 3.4).

Single source of truth for the machine-readable scan report. Architecture
Decision 11: dataclass-shape == JSON-shape contract — `dataclasses.asdict`
on ScanCoverage / ScanMetadata produces dicts whose key shape matches the
JSON envelope's `scan_coverage` / `scan` blocks verbatim.

Optional-fields-always-present rule (Q4 Story 3.4): every optional Finding
field is rendered as `null` when absent — never omitted. Sprint 3+ consumers
can rely on key presence and only have to test for null.

Semver rules (Story 3.4 lock):
  - MAJOR bump: field deletion, type change, semantic change
  - MINOR bump: field addition (consumers MUST ignore unknown fields)
  - PATCH bump: enum value addition

`ensure_ascii=False` for unicode signal text (Mandarin/Japanese lockout
strings, etc.).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from webprobe.findings import Finding

ENVELOPE_VERSION = "2.0"


def render_json(findings: list[Finding], coverage, metadata, args) -> str:
    """Story 3.4 versioned envelope.

    Returns a JSON document string (UTF-8 ready, no ASCII escapes). The
    `scan` block is `asdict(metadata)`; the `scan_coverage` block is
    `asdict(coverage)`. Findings are projected through `_finding_to_dict`
    to enforce the optional-fields-always-present rule.
    """
    envelope: dict[str, Any] = {
        "version": ENVELOPE_VERSION,
        "tool": {"name": "webprobe", "version": ENVELOPE_VERSION},
        "scan": asdict(metadata),
        "scan_coverage": asdict(coverage),
        "findings": [_finding_to_dict(f) for f in findings],
    }
    return json.dumps(envelope, indent=2, ensure_ascii=False, default=str)


def _finding_to_dict(f: Finding) -> dict[str, Any]:
    """Serialize a Finding with the optional-fields-always-present rule.

    Optional fields (`payload`, `poc_url`, `parameter`, `auth_context`,
    `baseline_context`, `fit3048_category`) appear with value `null` when
    None — never omitted. `seen_in` always appears as a list (empty list
    if no passes attached). `evidence_hash` always appears as a 16-char
    string (Finding.__post_init__ guarantees non-None).
    """
    return {
        "severity": f.severity,
        "category": f.category,
        "finding_type": f.finding_type,
        "name": f.name,
        "url": f.url,
        "payload": f.payload,                          # null when None
        "evidence": f.evidence,
        "evidence_hash": f.evidence_hash,              # 16-char canonical
        "poc_url": f.poc_url,                          # null when None
        "parameter": f.parameter,                      # null when None
        "remediation": f.remediation,
        "fit3048_category": f.fit3048_category,        # null when not set
        "auth_context": f.auth_context,                # null for unauth_always
        "baseline_context": f.baseline_context,        # null except IDOR
        "seen_in": list(f.seen_in or []),              # always list
    }
