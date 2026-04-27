"""Shared per-param request helpers used by sqli/xss/traversal."""
from __future__ import annotations
from webprobe.findings import Target

DEFAULT_TIMEOUT = 5


def build_units(target: Target) -> list[tuple[str, str, str, dict]]:
    """Yield (url, method, param, base_data) tuples for every injectable surface."""
    units: list[tuple[str, str, str, dict]] = [
        (target.url, "GET", k, {}) for k in target.query_params
    ]
    for fm in target.forms:
        for k in fm.fields:
            base = {f: v for f, v in fm.fields.items() if f != k}
            units.append((fm.action, fm.method, k, base))
    return units


def send(sess, url: str, method: str, param: str, payload: str, base: dict[str, str]):
    d = {**base, param: payload}
    if method.upper() == "POST":
        return sess.post(url, data=d, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    return sess.get(url, params=d, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
