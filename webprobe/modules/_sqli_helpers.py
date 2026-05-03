"""SQLi module helpers: payloads, fingerprints, constants, detection logic."""
from __future__ import annotations

from urllib.parse import quote

from webprobe.findings import Finding

PAYLOADS = ["'", '"', "1'", "1' OR '1'='1", "1' AND '1'='2", "1 AND 1=1", "1 AND 1=2"]
DIFF_PAIRS = [("1' OR '1'='1", "1' AND '1'='2"), ("1 AND 1=1", "1 AND 1=2")]
SQL_ERRORS = ("SQLSTATE", "mysql_fetch_array", "MariaDB", "ORA-",
              "SQLite3::", "PostgreSQL", "unclosed quotation mark",
              "you have an error in your sql syntax",
              "warning: mysql", "syntax error", "near \"'\"")
DIFF_THRESHOLD = 0.30
REM = "Use parameterised queries / prepared statements; never concatenate user input into SQL."


def detect_error(text_lower: str):
    return next((e for e in SQL_ERRORS if e.lower() in text_lower), None)


def diff_hit(tr, fr) -> bool:
    return (abs(len(tr.content) - len(fr.content)) / max(len(tr.content), 1) >= DIFF_THRESHOLD
            or tr.status_code != fr.status_code)


def err_finding(url, param, payload, fp) -> Finding:
    return Finding(severity="HIGH", category="sqli",
                   finding_type="sqli_error_string",
                   name="Error-based SQL injection", url=url,
                   parameter=param, payload=payload,
                   evidence=f"{fp!r} found in response body for payload {payload!r}",
                   poc_url=f"{url}?{param}={quote(payload)}",
                   remediation=REM)


def diff_finding(url, param, tp, fp, tr, fr) -> Finding:
    return Finding(severity="HIGH", category="sqli",
                   finding_type="sqli_boolean_diff",
                   name="Boolean-differential SQL injection", url=url,
                   parameter=param, payload=tp,
                   evidence=f"{tp!r} returned {len(tr.content)}B; {fp!r} returned {len(fr.content)}B",
                   poc_url=f"{url}?{param}={quote(tp)}",
                   remediation=REM)
