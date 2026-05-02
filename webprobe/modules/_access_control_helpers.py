"""Helpers for access_control module — extracted to keep the module body
under the 50-line cap (spec.md > 50-Line Cap)."""
from __future__ import annotations

from typing import Optional

from webprobe.findings import Finding


def match_admin_signal(body: str, signals: list[str],
                       signals_lower: list[str]) -> Optional[str]:
    """Return the first admin signal whose lowercase form appears in the
    body, or None. Caller pre-computes `signals_lower` for hot loops.
    """
    body_lower = (body or "").lower()
    for sig, low in zip(signals, signals_lower):
        if low in body_lower:
            return sig
    return None


def role_violation_finding(path: str, url: str, signal: str) -> Finding:
    return Finding(
        severity="HIGH",
        category="access_control",
        finding_type="role_violation",
        name=f"Admin-shape page reachable: {path}",
        url=url,
        evidence=f"HTTP 200 with admin-shaped HTML (contains {signal!r}).",
        remediation=f"Add an admin role check on {path}.",
    )


def ambiguous_summary_finding(target_url: str,
                              ambiguous_paths: list[str]) -> Finding:
    return Finding(
        severity="INFO",
        category="access_control",
        finding_type="ambiguous_200_summary",
        name="Admin-shape paths returned 200 without confirming signal",
        url=target_url,
        evidence=f"{len(ambiguous_paths)} path(s): "
                 f"{', '.join(ambiguous_paths[:3])}",
        remediation="Review URLs manually — possible false negatives.",
    )
