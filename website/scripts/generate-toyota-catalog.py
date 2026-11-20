"""Generate grade-level catalog data from the scraped Toyota configurator dump.

Reads  website/src/data/toyota-trim-colors.json  (produced by
scrape-toyota-configurator.py) and writes:

  website/src/data/toyota-catalog.json
      Current-lineup models with per-grade color palettes (union of the
      grade's factory trims — palettes differ across a grade's trims only
      for a handful of truck drivetrain configs, so the union is exact or
      a strict superset).

  agent/src/car_agent/data/toyota_color_buckets.json
      Marketing color name -> MarketCheck `base_ext_color` buckets actually
      observed on live listings of that exact color (see
      marketcheck-color-buckets-observed.json, refreshed by querying
      MarketCheck with exterior_color=<name> + a base_ext_color facet).
      An empty list means MarketCheck leaves listings of that color
      unbucketed — filtering by any base color would drop them, so the
      agent must omit the base filter when such a color is requested.

Run:  python3 website/scripts/generate-toyota-catalog.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SOURCE = REPO / "website/src/data/toyota-trim-colors.json"
OBSERVED = REPO / "website/scripts/marketcheck-color-buckets-observed.json"
CATALOG_OUT = REPO / "website/src/data/toyota-catalog.json"
BUCKETS_OUT = REPO / "agent/src/car_agent/data/toyota_color_buckets.json"

# Only offer the current lineup: series whose latest configurator year is
# older than this are discontinued or merged into another series.
MIN_MODEL_YEAR = 2026


def clean_name(name: str) -> str:
    """Collapse whitespace (Toyota data mixes non-breaking spaces into some
    two-tone color names)."""
    return " ".join(name.split())


def observed_buckets() -> dict[str, list[str]]:
    """Buckets MarketCheck actually assigned, keeping only buckets that cover
    a meaningful share of that color's listings (stray mis-tagged listings
    would otherwise add junk buckets)."""
    if not OBSERVED.exists():
        return {}
    raw = json.loads(OBSERVED.read_text())
    out = {}
    for name, obs in raw.items():
        found = obs.get("num_found") or 0
        buckets = obs.get("buckets") or []
        if found <= 0 or not isinstance(buckets, list):
            continue
        out[clean_name(name)] = [
            b for b, count in buckets if count >= max(2, 0.02 * found)
        ]
    return out


def display_name(series_name: str) -> str:
    return series_name.removeprefix("Toyota ").strip()


def main() -> None:
    src = json.loads(SOURCE.read_text())["models"]

    # Current lineup only.
    kept = {n: m for n, m in src.items() if m["year"] >= MIN_MODEL_YEAR}

    # Drop powertrain sub-series ("Tacoma i-FORCE MAX", "Corolla Hybrid", …)
    # whose grades the parent series already covers. Only powertrain suffixes
    # qualify — a distinct vehicle like "Crown Signia" can coincidentally have
    # a grade list that is a subset of "Crown"'s and must be kept.
    POWERTRAIN_SUFFIXES = (" i-FORCE MAX", " Hybrid")
    drop = set()
    for name, m in kept.items():
        for suffix in POWERTRAIN_SUFFIXES:
            parent = name.removesuffix(suffix)
            if parent != name and parent in kept:
                if set(m["grades"]) <= set(kept[parent]["grades"]):
                    drop.add(name)
    kept = {n: m for n, m in kept.items() if n not in drop}

    observed = observed_buckets()
    catalog: dict = {}
    buckets: dict[str, list[str]] = {}
    for name in sorted(kept):
        m = kept[name]
        grades = {}
        for grade, trims in m["grades"].items():
            colors: dict[str, dict] = {}
            for t in trims:
                for c in t["colors"]:
                    cname = clean_name(c["name"])
                    colors.setdefault(
                        cname,
                        {
                            "name": cname,
                            "hex": c["hex"],
                            "extraCost": c["extraCost"],
                            "msrp": int(c["msrp"]) if c.get("msrp") else 0,
                        },
                    )
                    buckets.setdefault(cname, observed.get(cname, []))
            grades[grade] = {"colors": list(colors.values())}
        catalog[display_name(name)] = {
            "seriesId": m["seriesId"],
            "year": m["year"],
            "grades": grades,
        }

    CATALOG_OUT.write_text(
        json.dumps(
            {"generatedAt": time.strftime("%Y-%m-%d"), "models": catalog},
            indent=1,
        )
        + "\n"
    )
    BUCKETS_OUT.parent.mkdir(parents=True, exist_ok=True)
    BUCKETS_OUT.write_text(
        json.dumps(dict(sorted(buckets.items())), indent=1) + "\n"
    )

    n_grades = sum(len(m["grades"]) for m in catalog.values())
    print(f"catalog: {len(catalog)} models, {n_grades} grades -> {CATALOG_OUT}")
    print(f"buckets: {len(buckets)} colors -> {BUCKETS_OUT}")
    print("dropped as stale:", sorted(n for n, m in src.items() if m['year'] < MIN_MODEL_YEAR))
    print("dropped as sub-series:", sorted(drop))


if __name__ == "__main__":
    main()
