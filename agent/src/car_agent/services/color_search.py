"""Two-tier color search: recall-safe MarketCheck base-color filtering plus
exact marketing-name post-filtering.

Dealers enter free-text exterior colors ("Supersonic Red 1", "Wind Chill
Pearl With Midnight Black Metallic Roof"), so filtering the MarketCheck API
by exact marketing name misses ~25% of matching inventory. Instead we:

  Tier 1 — query with `base_ext_color` (MarketCheck's normalized bucket,
  e.g. Red/White/Gray) derived from toyota_color_buckets.json, which maps
  each Toyota marketing color to the buckets observed on live listings.
  Colors with an empty bucket list are ones MarketCheck leaves unbucketed
  (e.g. Everest, Dark Cosmos) — any base filter would drop those listings,
  so when one is requested we omit the filter entirely.

  Tier 2 — post-filter the returned listings by normalized prefix match
  against the requested marketing names.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BUCKETS_PATH = Path(__file__).resolve().parent.parent / "data" / "toyota_color_buckets.json"


@lru_cache(maxsize=1)
def _bucket_map() -> dict[str, list[str]]:
    try:
        raw = json.loads(_BUCKETS_PATH.read_text())
        return {_normalize(name): buckets for name, buckets in raw.items()}
    except Exception:
        logger.exception("Failed to load %s; base-color filtering disabled", _BUCKETS_PATH)
        return {}


def _normalize(color: str) -> str:
    """Lowercase, collapse punctuation/whitespace, expand the 'w/' shorthand
    dealers use for two-tone roofs."""
    s = re.sub(r"[^a-z0-9]+", " ", color.lower()).strip()
    return re.sub(r"\bw\b", "with", s)


def base_color_buckets(colors: list[str] | None) -> list[str] | None:
    """MarketCheck `base_ext_color` values covering the requested marketing
    colors, or None when the base filter must be omitted (no colors requested,
    or any requested color is unbucketed/unknown in MarketCheck).
    """
    if not colors:
        return None
    buckets: list[str] = []
    for color in colors:
        found = _bucket_map().get(_normalize(color))
        if not found:
            logger.info("Color %r has no reliable base bucket; skipping base_ext_color filter", color)
            return None
        buckets.extend(b for b in found if b not in buckets)
    return buckets


def color_matches(listing_color: str | None, requested: list[str]) -> bool:
    """True if a dealer-entered color string is one of the requested marketing
    colors, tolerating dealer suffixes ("Supersonic Red 1", "… [extra_cost_color]",
    "… With Midnight Black Metallic Roof")."""
    if not listing_color:
        return False
    normalized = _normalize(listing_color)
    return any(normalized.startswith(_normalize(r)) for r in requested if r)


def filter_by_color(
    listings: list[dict[str, Any]],
    requested: list[str] | None,
) -> tuple[list[dict[str, Any]], bool]:
    """Keep listings whose exterior_color matches a requested marketing color.

    Returns (listings, exact) where exact=False means no listing matched
    exactly and the input is returned unchanged — base-bucket near matches
    (same color family) beat an empty result, and the LLM scorer sees each
    listing's actual color downstream.
    """
    if not requested:
        return listings, False
    matched = [l for l in listings if color_matches(l.get("exterior_color"), requested)]
    if matched:
        return matched, True
    return listings, False
