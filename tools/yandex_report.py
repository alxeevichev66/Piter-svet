#!/usr/bin/env python3
"""Еженедельный отчёт по Яндекс Вебмастеру и Метрике.

Берёт токен из переменной YANDEX_TOKEN (секрет GitHub), собирает:
страницы в поиске, проблемы сайта, топ запросов (показы, клики, позиция), визиты из поиска и заявки.
Пишет отчёт в docs/seo-report.md и печатает его. Ничего на сайте не меняет — токен только на чтение.
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import date, timedelta
from pathlib import Path

TOKEN = os.environ.get("YANDEX_TOKEN", "").strip()
COUNTER = 114262207
HOST_PART = "xn----dtbhcl5bjjfg"
WM = "https://api.webmaster.yandex.net/v4"
MT = "https://api-metrika.yandex.net"


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"Authorization": f"OAuth {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    if not TOKEN:
        print("ОШИБКА: секрет YANDEX_TOKEN не найден"); return 2
    out, errors = [], []
    today = date.today()
    out.append(f"# SEO-отчёт питер-свет.рф — {today.isoformat()}\n")

    # ---------- Вебмастер
    try:
        uid = get(f"{WM}/user")["user_id"]
        hosts = get(f"{WM}/user/{uid}/hosts")["hosts"]
        host = next((h for h in hosts if HOST_PART in h["host_id"] and h["host_id"].startswith("https")), None) \
            or next((h for h in hosts if HOST_PART in h["host_id"]), None)
        if not host:
            errors.append("Вебмастер: сайт не найден среди сайтов аккаунта: " + ", ".join(h["host_id"] for h in hosts))
        else:
            hid = urllib.parse.quote(host["host_id"], safe="")
            s = get(f"{WM}/user/{uid}/hosts/{hid}/summary")
            out.append("## Яндекс Вебмастер")
            out.append(f"- Страниц в поиске: **{s.get('searchable_pages_count', '—')}**, исключено: {s.get('excluded_pages_count', '—')}")
            out.append(f"- ИКС: {s.get('sqi', '—')}")
            probs = s.get("site_problems") or {}
            out.append("- Проблемы сайта: " + (", ".join(f"{k} — {v}" for k, v in probs.items() if v) or "нет"))
            d1, d2 = (today - timedelta(days=8)).isoformat(), (today - timedelta(days=1)).isoformat()
            q = get(f"{WM}/user/{uid}/hosts/{hid}/search-queries/popular", {
                "order_by": "TOTAL_SHOWS", "query_indicator": ["TOTAL_SHOWS", "TOTAL_CLICKS", "AVG_SHOW_POSITION"],
                "date_from": d1, "date_to": d2, "limit": 20})
            rows = q.get("queries", [])
            out.append(f"\n### Запросы за {d1} — {d2}")
            if not rows:
                out.append("Показов в поиске пока нет.")
            else:
                out.append("| Запрос | Показы | Клики | Позиция |\n|---|---|---|---|")
                for r in rows:
                    i = r.get("indicators", {})
                    pos = i.get("AVG_SHOW_POSITION")
                    out.append(f"| {r['query_text']} | {int(i.get('TOTAL_SHOWS') or 0)} | {int(i.get('TOTAL_CLICKS') or 0)} | {pos:.1f} |" if pos else
                               f"| {r['query_text']} | {int(i.get('TOTAL_SHOWS') or 0)} | {int(i.get('TOTAL_CLICKS') or 0)} | — |")
    except urllib.error.HTTPError as e:
        errors.append(f"Вебмастер: HTTP {e.code} — {e.read()[:200].decode('utf-8', 'replace')}")
    except Exception as e:  # noqa
        errors.append(f"Вебмастер: {e}")

    # ---------- Метрика
    try:
        d = get(f"{MT}/stat/v1/data", {"ids": COUNTER, "metrics": "ym:s:visits,ym:s:sumGoalReachesAny",
                                         "dimensions": "ym:s:lastTrafficSource", "date1": "7daysAgo", "date2": "today", "lang": "ru"})
        out.append("\n## Яндекс Метрика — последние 7 дней")
        tv, tg = d["totals"]
        out.append(f"- Всего визитов: **{int(tv)}**, достигнуто целей (заявки, звонки, калькулятор): **{int(tg)}**")
        for r in d.get("data", []):
            out.append(f"- {r['dimensions'][0]['name']}: визитов {int(r['metrics'][0])}, целей {int(r['metrics'][1])}")
        goals = get(f"{MT}/management/v1/counter/{COUNTER}/goals").get("goals", [])
        if goals:
            ids = [g["id"] for g in goals]
            g = get(f"{MT}/stat/v1/data", {"ids": COUNTER, "metrics": ",".join(f"ym:s:goal{i}reaches" for i in ids[:20]),
                                           "date1": "7daysAgo", "date2": "today"})
            out.append("- По целям: " + ", ".join(f"{gg['name']} — {int(v)}" for gg, v in zip(goals, g["totals"])))
    except urllib.error.HTTPError as e:
        errors.append(f"Метрика: HTTP {e.code} — {e.read()[:200].decode('utf-8', 'replace')}")
    except Exception as e:  # noqa
        errors.append(f"Метрика: {e}")

    if errors:
        out.append("\n## Ошибки\n" + "\n".join(f"- {x}" for x in errors))
    text = "\n".join(out) + "\n"
    print(text)
    Path(__file__).resolve().parent.parent.joinpath("docs/seo-report.md").write_text(text, encoding="utf-8")
    bad_auth = any("HTTP 401" in x or "HTTP 403" in x for x in errors)
    return 1 if bad_auth else 0


if __name__ == "__main__":
    sys.exit(main())
