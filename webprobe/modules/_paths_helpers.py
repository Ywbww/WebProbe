"""Helpers for the paths module: curated-list loader, classifier, finding factory."""
from __future__ import annotations
import importlib.resources
from webprobe.findings import Finding

MAX_WORKERS = 20
DEGRADATION_THRESHOLD = 3
FLAGGED_STATUS = (200, 301, 302, 403)
HIGH_PATTERNS = ("/.env", "/.git/", "/config/app_local.php",
                 "/backup.sql", "/db.sql")
MEDIUM_PATTERNS = ("/phpinfo.php", "/info.php",
                   "/debug-kit/", "/webroot/debug_kit/")
LOW_SUFFIXES = (".bak", ".old")
REMEDIATION = ("Block public access to this path; remove the file or "
               "restrict via web-server config / .gitignore.")
DEGRADED_MSG = ("[!] Target appears degraded — 3 consecutive failures.\n"
                "    Completing remaining modules with reduced confidence.")


def load_default_paths() -> list[str]:
    text = (importlib.resources.files("webprobe")
            .joinpath("data/paths/curated.txt").read_text())
    return [line.strip() for line in text.splitlines() if line.strip()]


def classify(path: str) -> str:
    if any(p in path for p in HIGH_PATTERNS): return "HIGH"
    if any(p in path for p in MEDIUM_PATTERNS): return "MEDIUM"
    if path.endswith(LOW_SUFFIXES): return "LOW"
    return "MEDIUM"


def mk_finding(path: str, url: str, status: int) -> Finding:
    return Finding(severity=classify(path), category="paths",
                   name=f"Exposed path: {path}", url=url,
                   parameter=None, payload=None,
                   evidence=f"HTTP {status} on {path}",
                   poc_url=url, remediation=REMEDIATION,
                   fit3048_category=3)
