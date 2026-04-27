from typing import Callable

from bs4 import BeautifulSoup, Comment
from requests import Session

from webprobe.findings import Finding, Target
from webprobe.modules.base import BaseModule

URL_HINTS = ("http://", "https://", "localhost", "192.168.", "10.", "172.16.")
HEADERS = (("Server", "Suppress or generic-ize the Server header to avoid version disclosure."),
           ("X-Powered-By", "Remove the X-Powered-By header to hide framework details."))
STACK = (("Traceback (most recent call last)", "Python traceback"),
         ("at java.lang.", "Java stack trace"), ("Stack trace:", "PHP/generic stack trace"))
LINE_PREFIX = (("Warning: ", "PHP warning"), ("Notice: ", "PHP notice"))
TRACE_REM = "Disable verbose error output in production; route exceptions to logs."
COMMENT_REM = "Strip developer comments from production HTML."
_trunc = lambda s, n=120: s if len(s) <= n else s[:n] + "..."


class InfoDisclosureModule(BaseModule):
    name = "info-disclosure"
    category = "info-disclosure"

    def _mk(self, sev, name, url, ev, rem):
        return Finding(sev, "info-disclosure", name, url, None, None, ev, None, rem, 3)

    def run(self, target: Target, session_factory: Callable[[], Session],
            report_finding: Callable[[Finding], None]) -> list[Finding]:
        h, url, text = target.base_response.headers, target.url, target.base_response.text
        out: list[Finding] = []
        for hdr, rem in HEADERS:
            if hdr in h:
                out.append(self._mk("LOW", f"{hdr} header disclosed", url, f"{hdr}: {h[hdr]}", rem))
        for c in BeautifulSoup(text, "html.parser").find_all(string=lambda s: isinstance(s, Comment)):
            txt = str(c).strip()
            if any(k in txt for k in ("TODO", "FIXME")) or any(u in txt for u in URL_HINTS):
                out.append(self._mk("MEDIUM", "Sensitive HTML comment", url, _trunc(txt), COMMENT_REM))
        for marker, label in STACK:
            if marker in text:
                i = text.find(marker)
                out.append(self._mk("MEDIUM", f"{label} in response", url, _trunc(text[i:i+120]), TRACE_REM))
        for marker, label in LINE_PREFIX:
            for line in text.splitlines():
                if line.startswith(marker):
                    out.append(self._mk("MEDIUM", f"{label} in response", url, _trunc(line), TRACE_REM))
                    break
        for f in out:
            report_finding(f)
        return out
