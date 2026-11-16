#!/usr/bin/env python3
"""Выгрузка Яндекс Метрики в docs/metrika.json — для отчётов. Токен из YANDEX_TOKEN, только чтение."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

T = os.environ["YANDEX_TOKEN"].strip()
C = 114262207
API = "https://api-metrika.yandex.net"
START = "2026-10-01"


def get(path, **p):
    url = API + path + ("?" + urllib.parse.urlencode(p, doseq=True) if p else "")
    req = urllib.request.Request(url, headers={"Authorization": f"OAuth {T}"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read()[:300].decode("utf-8", "replace")}


def stat(dims, metrics="ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:avgVisitDurationSeconds,ym:s:pageDepth", **kw):
    p = dict(ids=C, metrics=metrics, date1=START, date2="today", limit=50, lang="ru", accuracy="full")
    if dims:
        p["dimensions"] = dims
    p.update(kw)
    return get("/stat/v1/data", **p)


def slim(v):
    if isinstance(v, dict) and "data" in v:
        return {"metrics": v.get("query", {}).get("metrics"), "totals": v.get("totals"),
                "rows": [{"d": [x.get("name") for x in r["dimensions"]], "m": r["metrics"]} for r in v["data"]]}
    return v


counter = get(f"/management/v1/counter/{C}").get("counter", {})
goals = get(f"/management/v1/counter/{C}/goals").get("goals", [])
gm = ",".join(f"ym:s:goal{g['id']}reaches" for g in goals[:20]) or "ym:s:sumGoalReachesAny"
out = {
    "generated": date.today().isoformat(),
    "period_start": START,
    "counter": {k: counter.get(k) for k in ("id", "name", "site", "create_time", "code_status")},
    "goals": [{"id": g["id"], "name": g["name"], "type": g.get("type")} for g in goals],
    "totals": stat(None),
    "by_day": stat("ym:s:date", sort="ym:s:date", limit=100),
    "sources": stat("ym:s:lastTrafficSource"),
    "engines": stat("ym:s:lastSearchEngine"),
    "search_phrases": stat("ym:s:lastSearchPhrase"),
    "referers": stat("ym:s:lastReferalSource"),
    "pages_entry": stat("ym:s:startURL"),
    "pages_views": get("/stat/v1/data", ids=C, metrics="ym:pv:pageviews,ym:pv:users", dimensions="ym:pv:URL",
                       date1=START, date2="today", limit=50, lang="ru", accuracy="full"),
    "devices": stat("ym:s:deviceCategory"),
    "regions": stat("ym:s:regionCity"),
    "goals_total": stat(None, metrics=gm),
    "goals_by_source": stat("ym:s:lastTrafficSource", metrics=gm),
}
out = {k: slim(v) for k, v in out.items()}
Path(__file__).resolve().parent.parent.joinpath("docs/metrika.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out["totals"], ensure_ascii=False))
