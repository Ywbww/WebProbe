"""Discover forms + query params from the connectivity-check response."""
from typing import Optional
from urllib.parse import urlparse, parse_qs, urljoin

from bs4 import BeautifulSoup
from requests import Response

from webprobe.findings import Form, Target


def discover_target(url: str, response: Response, profile: Optional[str]) -> Target:
    """Build a Target from the response of the connectivity GET."""
    parsed = urlparse(url)
    raw_qs = parse_qs(parsed.query, keep_blank_values=True)
    query_params = {k: (v[0] if v else "") for k, v in raw_qs.items()}

    forms: list[Form] = []
    try:
        soup = BeautifulSoup(response.text, "html.parser")
        for f in soup.find_all("form"):
            action = urljoin(url, f.get("action") or url)
            method = (f.get("method") or "GET").upper()
            fields: dict[str, str] = {}
            hidden: list[str] = []
            for inp in f.find_all(["input", "textarea", "select"]):
                itype = (inp.get("type") or "").lower()
                if itype in ("submit", "button", "image"):
                    continue
                name = inp.get("name")
                if not name:
                    continue
                fields[name] = inp.get("value") or ""
                if itype == "hidden":
                    hidden.append(name)
            forms.append(Form(action=action, method=method,
                              fields=fields, hidden_fields=hidden))
    except Exception as e:
        print(f"[!] form discovery failed ({type(e).__name__}) — proceeding with no forms")

    return Target(url=url, base_response=response, forms=forms,
                  query_params=query_params, profile=profile)
