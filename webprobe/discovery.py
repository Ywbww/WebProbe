"""URL discovery (Epic 2).

PRD ref: prd.md > Epic 2.
Spec ref: spec.md > URL Discovery + Sitemap.

This module is intentionally a stub at Item 5b. Concrete bodies for
`resolve_url_pool`, sitemap/robots/url_list/dynamic/curated source helpers,
and `_dedup_by_priority` land in Item 10 (split into 10a/10b).
"""
from __future__ import annotations


class SitemapDiscoveryError(Exception):
    """Auth-fetched sitemap fetch failed (Phase 5f abort barrier)."""


def validate_discovery_flags(args) -> None:
    """Phase 0.5 inter-flag validator.

    Item 10 will implement:
      - --use-sitemap-authed needs --use-sitemap
      - --use-sitemap-authed needs --auth-form OR --cookie
    """
    return None
