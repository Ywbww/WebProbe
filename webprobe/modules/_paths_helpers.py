"""Helpers for the paths module: classifier, finding factory."""
from __future__ import annotations

from urllib.parse import urlparse

from webprobe.findings import Finding

FLAGGED_STATUS = (200, 301, 302, 403)
HIGH_PATTERNS = ("/.env", "/.git/", "/.htaccess", "/.htpasswd", "/.ssh",
                 "/config/app_local.php", "/backup.sql", "/db.sql",
                 "/wp-config.php", "/id_rsa")
MEDIUM_PATTERNS = ("/cpanel", "/admin", "/backup", "/wp-admin",
                   "/phpinfo.php", "/info.php", "/debug-kit/",
                   "/webroot/debug_kit/", "/phpmyadmin", "/.svn", "/.bzr")
LOW_SUFFIXES = (".bak", ".old", ".save", "~", ".swp", "/test", "/demo")
REMEDIATION = ("Block public access to this path; remove the file or "
               "restrict via web-server config / .gitignore.")


def classify(path: str) -> tuple[str, str]:
    """Return (severity, slug) tuple."""
    if any(p in path for p in HIGH_PATTERNS):
        return "HIGH", "sensitive_path_exposed_high"
    if any(p in path for p in MEDIUM_PATTERNS):
        return "MEDIUM", "sensitive_path_exposed_medium"
    if path.endswith(LOW_SUFFIXES) or any(low in path for low in LOW_SUFFIXES):
        return "LOW", "sensitive_path_exposed_low"
    return "MEDIUM", "sensitive_path_exposed_medium"


def url_to_path(url: str) -> str:
    return urlparse(url).path or "/"


def mk_finding(url: str, status: int) -> Finding:
    path = url_to_path(url)
    sev, slug = classify(path)
    return Finding(severity=sev, category="paths", finding_type=slug,
                   name=f"Exposed path: {path}", url=url,
                   evidence=f"HTTP {status} on {path}",
                   poc_url=url, remediation=REMEDIATION)
