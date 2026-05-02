"""URL discovery (Epic 2).

PRD ref: prd.md > Epic 2 (Stories 2.1-2.5).
Spec ref: spec.md > Discovery (Epic 2).

Naming convention (per spec):
  - `discover_<source>(...)` returns a metadata-rich Result dataclass when
    the source has side-channel info (sitemap, robots).
  - `discover_<source>_pairs(...)` returns a plain list[tuple[str, Source]]
    for pure URL emitters (url_list, dynamic, curated).

Item 10a body (this file): SitemapDiscoveryResult, RobotsDiscoveryResult,
discover_sitemap, discover_robots. Item 10b adds url_list/dynamic/curated +
_dedup_by_priority + resolve_url_pool + Engine wiring (Phase 4 / 5f).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import requests

DEFAULT_TIMEOUT = 10
SITEMAP_CAP_DEFAULT = 500


# --- Exception types -----------------------------------------------------

class SitemapDiscoveryError(Exception):
    """Sitemap fetch/parse failed loudly per Story 2.1.

    Wraps:
      - xml.etree.ElementTree.ParseError on malformed XML
      - 200-OK responses whose body is HTML (auth-gated login redirects)
      - 401 / non-/sitemap.xml redirects to /users/login etc.
    """


# --- Result dataclasses --------------------------------------------------

@dataclass
class SitemapDiscoveryResult:
    """Phase 4 / Phase 5f sitemap result.

    `urls` is stored as a tuple to keep the result immutable once Phase 4
    has frozen the URL pool. The engine builds a list internally and
    converts to tuple at end-of-phase per spec.

    `cap_hit` and `cap` together feed the INFO emission on overflow:
    when cap_hit is True, exactly `cap` entries were retained.
    `advertised_via_robots` feeds Story 2.2.E1's three-branch INFO logic.
    """
    urls: tuple[tuple[str, "Source"], ...]  # forward ref to avoid circular import at top
    cap: int
    cap_hit: bool
    advertised_via_robots: bool


@dataclass
class RobotsDiscoveryResult:
    """Phase 4 robots result.

    Fields per spec.md > Robots discovery:
      - urls: (path-as-URL, Source.ROBOTS) pairs from Disallow directives,
        wildcard-trimmed per Story 2.3 (e.g. `/admin/*` -> `/admin/`).
      - wildcard_intents: original wildcard patterns recorded for Story 2.3
        consolidated INFO finding (e.g. ["/admin/*", "*.bak", "/api/v*"]).
      - sitemap_url_advertised: Sitemap: directive URL for Story 2.2.E1
        cross-check (None when not advertised).
    """
    urls: tuple[tuple[str, "Source"], ...]
    wildcard_intents: tuple[str, ...]
    sitemap_url_advertised: Optional[str]


# --- Sitemap discovery ---------------------------------------------------

def discover_sitemap(
    target_or_url,
    authed_session: Optional[requests.Session] = None,
    *,
    cap: int = SITEMAP_CAP_DEFAULT,
    advertised_via_robots: bool = False,
) -> SitemapDiscoveryResult:
    """GET <target>/sitemap.xml; parse <urlset> or <sitemapindex>.

    Per Story 2.1 acceptance:
      - 404/410: silent skip, return empty result.
      - 200 with valid XML: extract <loc> entries, same-origin filter,
        cap at `cap`.
      - 200 with HTML body (auth-gated login page): raise
        SitemapDiscoveryError with PRD-locked message.
      - Malformed XML: raise SitemapDiscoveryError.

    `target_or_url` may be a Target (with .url) or a bare URL string.
    Engine Phase 4 passes Target; tests pass strings — both are stable.
    """
    # Local import keeps `findings` out of module-level hot path imports
    # so coverage.py / findings.py stay independently importable.
    from webprobe.findings import Source

    target_url = getattr(target_or_url, "url", target_or_url)
    sess = authed_session if authed_session is not None else requests.Session()
    sitemap_url = urljoin(target_url, "/sitemap.xml")

    try:
        resp = sess.get(sitemap_url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        raise SitemapDiscoveryError(
            f"sitemap.xml fetch failed at {sitemap_url}: {exc}. "
            f"Use --no-use-sitemap to skip sitemap discovery."
        ) from exc

    # Silent skip: 404 / 410 (RFC: gone). Return empty result.
    if resp.status_code in (404, 410):
        return SitemapDiscoveryResult(
            urls=(),
            cap=cap,
            cap_hit=False,
            advertised_via_robots=advertised_via_robots,
        )

    # 401 / 3xx-to-login: fail loud per Story 2.1 lock.
    if resp.status_code == 401:
        raise SitemapDiscoveryError(
            f"sitemap.xml at {sitemap_url} returned 401 (auth-gated). "
            f"Use --no-use-sitemap to skip sitemap discovery."
        )

    # 200 but body is HTML (login redirect that returned 200, or generic
    # SPA shell). Heuristic: leading-stripped body must start with '<' and
    # the first tag must NOT be 'html' or 'HTML'.
    body = (resp.text or "").lstrip()
    if not body:
        return SitemapDiscoveryResult(
            urls=(),
            cap=cap,
            cap_hit=False,
            advertised_via_robots=advertised_via_robots,
        )
    if _looks_like_html(body):
        raise SitemapDiscoveryError(
            f"sitemap.xml at {sitemap_url} returned HTML (likely auth-gated). "
            f"Use --no-use-sitemap to skip sitemap discovery."
        )

    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise SitemapDiscoveryError(
            f"sitemap.xml at {sitemap_url} returned invalid XML.\n"
            f"Use --no-use-sitemap to skip sitemap discovery."
        ) from exc

    locs = _extract_sitemap_locs(root, sess, recursion_remaining=1)

    # Same-origin filter (off-host filtered silently per spec).
    target_netloc = urlparse(target_url).netloc.lower()
    same_origin: list[str] = []
    for loc in locs:
        if not loc:
            continue
        loc = loc.strip()
        if not loc:
            continue
        if urlparse(loc).netloc.lower() == target_netloc:
            same_origin.append(loc)

    cap_hit = len(same_origin) > cap
    if cap_hit:
        same_origin = same_origin[:cap]

    pairs = tuple((u, Source.SITEMAP) for u in same_origin)
    return SitemapDiscoveryResult(
        urls=pairs,
        cap=cap,
        cap_hit=cap_hit,
        advertised_via_robots=advertised_via_robots,
    )


def _extract_sitemap_locs(
    root: ET.Element, session: requests.Session, recursion_remaining: int
) -> list[str]:
    """Handle <urlset> (direct) and <sitemapindex> (one-level recursion).

    XML namespace stripped via local-name (`tag.split('}')[-1]`) so
    namespaced sitemaps (`xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"`)
    parse without explicit namespace bookkeeping.
    """
    local_name = root.tag.split('}')[-1]
    if local_name == "urlset":
        return [
            (elem.text or "")
            for elem in root.iter()
            if elem.tag.split('}')[-1] == "loc"
        ]
    if local_name == "sitemapindex" and recursion_remaining > 0:
        urls: list[str] = []
        for elem in root.iter():
            if elem.tag.split('}')[-1] != "loc":
                continue
            child_url = (elem.text or "").strip()
            if not child_url:
                continue
            try:
                child_resp = session.get(child_url, timeout=DEFAULT_TIMEOUT)
            except requests.RequestException:
                # Skip a broken child sitemap quietly; fail-loud only on
                # the entry-point sitemap per Story 2.1 lock.
                continue
            child_body = (child_resp.text or "").lstrip()
            if not child_body or _looks_like_html(child_body):
                continue
            try:
                child_root = ET.fromstring(child_body)
            except ET.ParseError:
                continue
            urls.extend(
                _extract_sitemap_locs(child_root, session, recursion_remaining - 1)
            )
        return urls
    return []


def _looks_like_html(body: str) -> bool:
    """Heuristic: body whose first non-whitespace tag is <html or <!DOCTYPE
    HTML is HTML, not XML. We deliberately do NOT trust Content-Type — many
    auth-gated apps return HTML with Content-Type: application/xml.
    """
    head = body[:200].lower().lstrip()
    if head.startswith("<!doctype html"):
        return True
    if head.startswith("<html"):
        return True
    return False


# --- Robots discovery ----------------------------------------------------

def discover_robots(
    target_or_url,
    session: Optional[requests.Session] = None,
) -> RobotsDiscoveryResult:
    """GET <target>/robots.txt; custom directive parser per spec.

    Per Story 2.3 acceptance:
      - 404: silent skip, empty result.
      - 200: parse Disallow directives across ALL User-agent: blocks
        (union, no per-bot filtering).
      - Wildcard handling:
          /admin/*  -> probed as /admin/, original recorded
          *.bak     -> not probed, original recorded
          /api/v*   -> probed as /api/v, original recorded
      - Empty Disallow: skipped (RFC: means "allow everything").
      - Allow: directives ignored.
      - Sitemap: directive URL captured for Story 2.2.E1 cross-check.

    Auth-gated robots.txt is NOT special-cased like sitemap — the spec
    only fail-louds robots.txt on Story 2.1 pattern when intent is clear;
    treat any non-2xx other than 404 as silent skip to keep robots a
    best-effort source.
    """
    from webprobe.findings import Source

    target_url = getattr(target_or_url, "url", target_or_url)
    sess = session if session is not None else requests.Session()
    robots_url = urljoin(target_url, "/robots.txt")

    try:
        resp = sess.get(robots_url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return RobotsDiscoveryResult(urls=(), wildcard_intents=(), sitemap_url_advertised=None)

    if resp.status_code != 200:
        return RobotsDiscoveryResult(urls=(), wildcard_intents=(), sitemap_url_advertised=None)

    disallow_paths, wildcard_intents, sitemap_advertised = _parse_robots_txt(resp.text or "")

    # Convert disallow paths to absolute same-origin URLs tagged ROBOTS.
    pairs = tuple((urljoin(target_url, p), Source.ROBOTS) for p in disallow_paths)
    return RobotsDiscoveryResult(
        urls=pairs,
        wildcard_intents=tuple(wildcard_intents),
        sitemap_url_advertised=sitemap_advertised,
    )


def _parse_robots_txt(text: str) -> tuple[list[str], list[str], Optional[str]]:
    """Custom robots.txt parser (~25 lines, no urllib.RobotFileParser).

    Returns (disallow_paths, wildcard_intents, sitemap_url_advertised).

    Behaviour:
      - Disallow lines from ALL User-agent blocks union into one list.
      - Wildcards: `/path*` -> `/path` (trimmed, original recorded).
        `*` at start (e.g. `*.bak`) -> recorded only, not probed.
      - Empty Disallow ignored.
      - Allow ignored.
      - Sitemap: captures the LAST advertised URL if multiple appear.
      - Comments (#) and blank lines skipped.
    """
    disallow: list[str] = []
    wildcards: list[str] = []
    sitemap: Optional[str] = None
    seen: set[str] = set()

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        directive, _, value = line.partition(":")
        directive = directive.strip().lower()
        value = value.strip()
        if directive == "sitemap" and value:
            sitemap = value
            continue
        if directive != "disallow":
            continue
        if not value:
            # Empty Disallow == allow-all per RFC; skip.
            continue
        if "*" in value:
            wildcards.append(value)
            if value.startswith("*"):
                # Suffix wildcards (*.bak): recorded but not probed.
                continue
            # Prefix-style wildcard: trim trailing wildcard segment.
            trimmed = value.split("*", 1)[0]
            if trimmed and trimmed not in seen:
                seen.add(trimmed)
                disallow.append(trimmed)
            continue
        if value not in seen:
            seen.add(value)
            disallow.append(value)
    return disallow, wildcards, sitemap


# --- Phase 0.5 inter-flag validation -------------------------------------

def validate_discovery_flags(args) -> None:
    """Phase 0.5 inter-flag validator (sitemap/robots/url-list).

    Story 2.4 lock: --use-sitemap-authed needs --use-sitemap AND auth flag.
    Story 2.4: --url-list path must exist (file-not-found is fail-loud at
    Phase 4, but Phase 0.5 surfaces obviously-broken paths so the user
    fails before any HTTP). For Item 10's scope this is permissive
    (we only fail-loud on auth-mode misconfig).
    """
    # Local import: avoid circular when auth.py imports discovery for type
    # references in Sprint 3+ (defensive).
    from webprobe.auth import ConfigurationError

    use_sitemap = bool(getattr(args, "use_sitemap", False))
    use_sitemap_authed = bool(getattr(args, "use_sitemap_authed", False))
    auth_form = getattr(args, "auth_form", None)
    cookie = getattr(args, "cookie", None)

    if use_sitemap_authed and not use_sitemap:
        raise ConfigurationError(
            "--use-sitemap-authed requires --use-sitemap."
        )
    if use_sitemap_authed and not (auth_form or cookie):
        raise ConfigurationError(
            "--use-sitemap-authed requires --auth-form or --cookie."
        )
    return None


# --- URL list discovery (Story 2.4) --------------------------------------

def discover_url_list_pairs(
    target_or_url, path: str
) -> list[tuple[str, "Source"]]:
    """Read `<path>` line-by-line and emit (url, Source.URL_LIST) pairs.

    Per Story 2.4 acceptance:
      - `#`-comment lines and blank lines skipped.
      - Relative URLs resolved against target.
      - Absolute same-host URLs kept verbatim.
      - Absolute different-host URLs filtered silently here (engine prints
        the warning per Phase 4 contract; Item 14b wires the actual
        skip-warning UX).
      - File-not-found is fail-loud at the open() call (FileNotFoundError
        propagates; engine Phase 4 catches and surfaces).

    Empty / all-comments file returns []; engine Phase 4 emits the
    "url-list contained no probe-able URLs" INFO finding (the INFO logic
    lives in the engine since it requires Finding construction, not in
    discovery).
    """
    from webprobe.findings import Source

    target_url = getattr(target_or_url, "url", target_or_url)
    target_netloc = urlparse(target_url).netloc.lower()

    pairs: list[tuple[str, Source]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("http://") or line.startswith("https://"):
                # Absolute: keep iff same-host.
                if urlparse(line).netloc.lower() == target_netloc:
                    pairs.append((line, Source.URL_LIST))
                # else: silent filter (engine emits skip-warning UX in Item 14b)
                continue
            # Relative path: resolve against target.
            pairs.append((urljoin(target_url, line), Source.URL_LIST))
    return pairs


# --- Dynamic source extraction (Story 2.5.E1) ----------------------------

def discover_dynamic_pairs(target) -> list[tuple[str, "Source"]]:
    """Extract same-origin URLs from base_response HTML.

    Sources scanned per spec:
      - <a href="...">
      - <form action="...">  (empty action means submit-to-current-URL,
        per Phase 1 Q1 Gap 9 — add target.url itself)
      - <script src="...">

    Filtered to same-origin (parsed netloc == target netloc). De-duplicated
    within source (set semantics) before returning; cross-source dedup
    happens later via _dedup_by_priority.
    """
    from bs4 import BeautifulSoup
    from webprobe.findings import Source

    target_url = target.url
    target_netloc = urlparse(target_url).netloc.lower()
    found: set[str] = set()

    body = getattr(target.base_response, "text", "") or ""
    try:
        soup = BeautifulSoup(body, "html.parser")
    except Exception:
        # Defensive: malformed HTML shouldn't abort discovery.
        return []

    def _consider(raw: Optional[str]) -> None:
        if raw is None:
            return
        # Empty action="" -> submit-to-current-URL (CakePHP edge case).
        if raw == "":
            found.add(target_url)
            return
        absolute = urljoin(target_url, raw)
        # Strip fragment (#anchor) — anchors don't change probe target.
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https"):
            return  # mailto:, javascript:, tel:, etc.
        if parts.netloc.lower() != target_netloc:
            return
        defragged = urlunsplit((parts.scheme, parts.netloc, parts.path or "/",
                                parts.query, ""))
        found.add(defragged)

    for tag in soup.find_all("a"):
        _consider(tag.get("href"))
    for tag in soup.find_all("form"):
        action = tag.get("action")
        # Distinguish "no attribute" (None) from "empty attribute" ("").
        if action is None and tag.has_attr("action"):
            action = ""
        _consider(action)
    for tag in soup.find_all("script"):
        _consider(tag.get("src"))

    return [(u, Source.DYNAMIC) for u in found]


# --- Curated discovery (v1->v2 architectural shift) ----------------------

def discover_curated_pairs(target_or_url) -> list[tuple[str, "Source"]]:
    """Load curated.txt + profile paths; emit (url, Source.CURATED) pairs.

    v1->v2 SHIFT: paths.py NO LONGER loads curated.txt internally. Engine
    Phase 4 calls this; URL pool is single source of truth for which URLs
    get probed. Future v2 paths module reads filtered Target.urls like
    every other module.

    Profile composition: CAKEPHP_PATHS unconditional in v2 — profile
    flags scope module activation (filter.py), not the curated pool. The
    curated pool stays comprehensive; the cost is one extra entry in the
    URL pool's by_source breakdown when profile=None.
    """
    from importlib.resources import files
    from webprobe.findings import Source
    from webprobe.profiles import CAKEPHP_PATHS

    target_url = getattr(target_or_url, "url", target_or_url)
    target_netloc = urlparse(target_url).netloc.lower()

    text = (files("webprobe.data.paths") / "curated.txt").read_text(encoding="utf-8")
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)

    composed: list[str] = lines + list(CAKEPHP_PATHS)

    pairs: list[tuple[str, Source]] = []
    seen: set[str] = set()
    for entry in composed:
        if entry.startswith("http://") or entry.startswith("https://"):
            if urlparse(entry).netloc.lower() != target_netloc:
                continue
            url = entry
        else:
            url = urljoin(target_url, entry)
        if url in seen:
            continue
        seen.add(url)
        pairs.append((url, Source.CURATED))
    return pairs


# --- Source priority dedup (Story 2.4.E1 lock) ---------------------------

# Lock: url_list > robots > curated > sitemap > dynamic
# Lower number = higher priority (wins ties).
def _build_source_priority() -> dict:
    from webprobe.findings import Source
    return {
        Source.URL_LIST: 0,
        Source.ROBOTS:   1,
        Source.CURATED:  2,
        Source.SITEMAP:  3,
        Source.DYNAMIC:  4,
    }


_SOURCE_PRIORITY: dict = _build_source_priority()


def _canonicalize_url(url: str) -> str:
    """Dedup-key form. Lowercase scheme + netloc; preserve path/query
    verbatim; collapse empty path to '/' and strip a single trailing '/'
    on non-root paths. NO query-string normalization (Sprint 3+ candidate).
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def _dedup_by_priority(
    pairs: list[tuple[str, "Source"]]
) -> list[tuple[str, "Source"]]:
    """Keep the highest-priority (url, source) per canonicalized URL.

    Stable order: first-seen wins among ties (within same priority).
    Returned URLs are in their original (non-canonicalized) form —
    canonicalization is dedup-key-only per spec audit-trail discipline.
    """
    priority = _SOURCE_PRIORITY
    best: dict[str, tuple[str, "Source"]] = {}
    for url, source in pairs:
        key = _canonicalize_url(url)
        if key not in best:
            best[key] = (url, source)
            continue
        cur_url, cur_source = best[key]
        if priority[source] < priority[cur_source]:
            best[key] = (url, source)
    return list(best.values())


# --- Phase 4 / 5f composition --------------------------------------------

def resolve_url_pool(
    args, target, sessions: Optional[list[requests.Session]] = None,
) -> tuple[tuple[str, "Source"], ...]:
    """Compose all enabled sources, dedup by priority, freeze as tuple.

    Engine Phase 4 entry. SitemapDiscoveryError propagates to engine for
    the per-spec Phase 4 abort handler.

    Source order in the input list does not affect output (dedup is
    order-independent), but matches user mental model: explicit >
    intent-declared > heuristic > bulk > incidental.

    Sitemap discovery here is the UNAUTH path (sessions=None or
    pre-auth). Phase 5f re-runs sitemap discovery with the authed session
    and merges + re-dedups, so the unauth sitemap result is not lost.
    """
    from webprobe.findings import Source  # noqa: F401  (re-exported via pairs)

    primary = sessions[0] if sessions else None
    pairs: list[tuple[str, Source]] = []

    if getattr(args, "url_list", None):
        pairs.extend(discover_url_list_pairs(target, args.url_list))

    robots_advertises_sitemap = False
    if getattr(args, "use_robots", False):
        robots_result = discover_robots(target, session=primary)
        pairs.extend(robots_result.urls)
        # Engine inspects this for Story 2.2.E1 cross-check; we cache it
        # on args for now to avoid an out-of-band channel (the engine
        # wraps this resolver, so it can read args back).
        args._discovery_robots_result = robots_result
        robots_advertises_sitemap = robots_result.sitemap_url_advertised is not None

    if getattr(args, "use_sitemap", False) and not getattr(args, "use_sitemap_authed", False):
        # Unauth sitemap (authed sitemap path lives in Phase 5f).
        sitemap_result = discover_sitemap(
            target, advertised_via_robots=robots_advertises_sitemap,
        )
        pairs.extend(sitemap_result.urls)
        args._discovery_sitemap_result = sitemap_result

    # Dynamic + curated always.
    pairs.extend(discover_dynamic_pairs(target))
    pairs.extend(discover_curated_pairs(target))

    deduped = _dedup_by_priority(pairs)
    return tuple(deduped)


def merge_authed_sitemap(
    target,
    existing_pool: tuple[tuple[str, "Source"], ...],
    authed_session: requests.Session,
    advertised_via_robots: bool = False,
) -> tuple[tuple[tuple[str, "Source"], ...], SitemapDiscoveryResult]:
    """Phase 5f helper. Re-fetch sitemap with authed session, merge into
    existing pool, re-dedup. Returns (new_pool, sitemap_result) so the
    engine can update both target.urls and its result-cache references.
    """
    sitemap_result = discover_sitemap(
        target,
        authed_session=authed_session,
        advertised_via_robots=advertised_via_robots,
    )
    merged = list(existing_pool) + list(sitemap_result.urls)
    new_pool = tuple(_dedup_by_priority(merged))
    return new_pool, sitemap_result
