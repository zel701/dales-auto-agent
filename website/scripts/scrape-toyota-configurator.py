"""Scrape Toyota US configurator (orchestrator.configurator.toyota.com/graphql)
into model -> grade -> trim -> exterior colors JSON."""

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://orchestrator.configurator.toyota.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.toyota.com",
    "Referer": "https://www.toyota.com/configurator/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
}
REGION = {"zipCode": "90210"}

SERIES_QUERY = """
query S($brand: Brand!, $region: Region!) {
  getSeries(brand: $brand, region: $region) {
    seriesData {
      id name shortName
      yearSpecificData { year grades { gradeName } }
    }
  }
}
"""

CONFIG_QUERY = """
query C($c: ConfigInputGrade!) {
  getConfigByGrade(configInputGrade: $c) {
    seriesId seriesName year
    grade {
      gradeName
      trims { code title exteriorColorIds }
    }
    exteriorColors { id code title hexCode isExtraCostColor msrp { value } }
  }
}
"""


def gql(query: str, variables: dict, retries: int = 3) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL, data=payload, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                out = json.loads(resp.read())
            if out.get("data"):
                return out
            last = out.get("errors")
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(1 + attempt)
    return {"errors": last}


def clean_title(t: str) -> str:
    # strip disclaimer tokens like "[extra_cost_color]"
    import re
    return re.sub(r"\s*\[[a-z0-9_]+\]\s*", " ", t).strip()


def fetch_grade(series_id: str, year: int, grade_name: str) -> dict:
    v = {"c": {
        "brand": "TOYOTA", "region": REGION, "year": year,
        "seriesId": series_id, "gradeName": grade_name,
    }}
    out = gql(CONFIG_QUERY, v)
    cfg = (out.get("data") or {}).get("getConfigByGrade")
    if not cfg:
        return {"series": series_id, "year": year, "grade": grade_name,
                "error": str(out.get("errors"))[:300]}
    colors = {c["id"]: c for c in (cfg.get("exteriorColors") or [])}
    trims = []
    for t in ((cfg.get("grade") or {}).get("trims") or []):
        tcolors = []
        for cid in (t.get("exteriorColorIds") or []):
            c = colors.get(cid)
            if not c:
                continue
            tcolors.append({
                "name": clean_title(c["title"]),
                "code": c["code"],
                "hex": "#" + c["hexCode"][0] if c.get("hexCode") else None,
                "extraCost": bool(c.get("isExtraCostColor")),
                "msrp": (c.get("msrp") or {}).get("value"),
            })
        trims.append({"code": t["code"], "title": t["title"], "colors": tcolors})
    return {"series": series_id, "seriesName": cfg.get("seriesName"),
            "year": year, "grade": grade_name, "trims": trims}


def main() -> None:
    out = gql(SERIES_QUERY, {"brand": "TOYOTA", "region": REGION})
    series = out["data"]["getSeries"]["seriesData"]
    jobs = []
    for s in series:
        ys = [y for y in (s.get("yearSpecificData") or []) if y.get("grades")]
        if not ys:
            continue
        latest = max(ys, key=lambda y: y["year"])
        for g in latest["grades"]:
            jobs.append((s["id"], s["name"], latest["year"], g["gradeName"]))

    print(f"{len(series)} series, {len(jobs)} (series, grade) jobs")
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fetch_grade, sid, yr, gn): (sid, nm, yr, gn)
                for sid, nm, yr, gn in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            r["seriesName"] = r.get("seriesName") or futs[f][1]
            results.append(r)
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)} done")

    # model -> {year, grades: {grade: {trims: [...]}}}
    data: dict = {}
    errors = []
    for r in sorted(results, key=lambda r: (r["seriesName"], r["grade"])):
        if r.get("error"):
            errors.append(r)
            continue
        m = data.setdefault(r["seriesName"], {"seriesId": r["series"], "year": r["year"], "grades": {}})
        m["grades"][r["grade"]] = r["trims"]

    with open("toyota_trim_colors.json", "w") as fh:
        json.dump({"scrapedAt": time.strftime("%Y-%m-%d"), "zipCode": REGION["zipCode"],
                   "models": data, "errors": errors}, fh, indent=1)

    n_grades = sum(len(m["grades"]) for m in data.values())
    n_trims = sum(len(ts) for m in data.values() for ts in m["grades"].values())
    print(f"OK: {len(data)} models, {n_grades} grades, {n_trims} trims, {len(errors)} errors")
    for e in errors[:10]:
        print("  ERR", e["series"], e["year"], e["grade"], e["error"][:120])


if __name__ == "__main__":
    main()
