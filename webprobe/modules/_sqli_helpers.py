"""SQLi module helpers: payloads, fingerprints, constants, detection logic."""
from __future__ import annotations
from urllib.parse import quote
from requests.exceptions import RequestException
from webprobe.findings import Finding
from webprobe.modules._common import build_units, send  # noqa: F401 (re-exported)

PAYLOADS = ["'", '"', "1'", "1' OR '1'='1", "1' AND '1'='2", "1 AND 1=1", "1 AND 1=2"]
DIFF_PAIRS = [("1' OR '1'='1", "1' AND '1'='2"), ("1 AND 1=1", "1 AND 1=2")]
SQL_ERRORS = ("SQLSTATE", "mysql_fetch_array", "MariaDB", "ORA-",
              "SQLite3::", "PostgreSQL", "unclosed quotation mark")
DIFF_THRESHOLD = 0.30                # 30% length delta or status change -> hit (auditable)
DEGRADATION_THRESHOLD = 3
REM = "Use parameterised queries / prepared statements; never concatenate user input into SQL."
DEGRADED_MSG = ("[!] Target appears degraded — 3 consecutive failures.\n"
                "    Completing remaining modules with reduced confidence.")


def mk(name, url, param, payload, ev, poc) -> Finding:
    return Finding("HIGH", "sqli", name, url, param, payload, ev, poc, REM, 5)


def detect_error(text_lower: str):
    return next((e for e in SQL_ERRORS if e.lower() in text_lower), None)


def diff_hit(tr, fr) -> bool:
    return (abs(len(tr.content) - len(fr.content)) / max(len(tr.content), 1) >= DIFF_THRESHOLD
            or tr.status_code != fr.status_code)


def err_finding(url, param, payload, fp):
    return mk("Error-based SQL injection", url, param, payload,
              f"{fp!r} found in response body for payload {payload!r}", f"{url}?{param}={quote(payload)}")


def diff_finding(url, param, tp, fp, tr, fr):
    return mk("Boolean-differential SQL injection", url, param, tp,
              f"{tp!r} returned {len(tr.content)}B; {fp!r} returned {len(fr.content)}B",
              f"{url}?{param}={quote(tp)}")


_RequestException = RequestException
