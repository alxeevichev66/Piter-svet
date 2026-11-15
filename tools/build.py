#!/usr/bin/env python3
"""
Сборка служебных файлов сайта Питер-Свет. Без зависимостей, только стандартный Python 3.

Что делает:
  1. Находит статьи в blog/<адрес>/index.html и пересобирает список карточек в blog/index.html
     (между метками POSTS:START и POSTS:END), новые сверху.
  2. Пересобирает sitemap.xml по всем страницам сайта.

Как добавить статью: создать папку blog/<адрес-латиницей>/ с index.html по образцу
существующей статьи (обязательны <title>, meta article:published и article:excerpt) и запустить
  python3 tools/build.py
При автодеплое на GitHub скрипт запускается сам.
"""
import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://xn----dtbhcl5bjjfg.xn--p1ai"   # питер-свет.рф в punycode
EXCLUDE = {"404.html"}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]


def meta(text: str, name: str) -> str:
    m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(name), text)
    return html.unescape(m.group(1)) if m else ""


def title(text: str) -> str:
    m = re.search(r"<title>(.*?)</title>", text, re.S)
    t = html.unescape(m.group(1).strip()) if m else ""
    return re.sub(r"\s+—\s+Питер-Свет$", "", t)


def human_date(iso: str) -> str:
    y, mth, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS[mth - 1]} {y}"


def collect_posts():
    posts = []
    for f in sorted((ROOT / "blog").glob("*/index.html")):
        text = f.read_text(encoding="utf-8")
        published = meta(text, "article:published")
        if not published:
            print(f"! пропущена {f.relative_to(ROOT)}: нет meta article:published", file=sys.stderr)
            continue
        posts.append({
            "slug": f.parent.name,
            "title": title(text),
            "excerpt": meta(text, "article:excerpt") or meta(text, "description"),
            "date": published,
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def build_blog_index(posts):
    idx = ROOT / "blog" / "index.html"
    text = idx.read_text(encoding="utf-8")
    cards = []
    for p in posts:
        cards.append(
            f'        <a class="tile post-card" data-tile href="/blog/{p["slug"]}/">\n'
            f'          <time class="post-card__date" datetime="{p["date"]}">{human_date(p["date"])}</time>\n'
            f'          <h2 class="post-card__title">{html.escape(p["title"])}</h2>\n'
            f'          <p class="post-card__text">{html.escape(p["excerpt"])}</p>\n'
            f'          <span class="post-card__more">Читать →</span>\n'
            f'        </a>'
        )
    new = re.sub(r"(<!-- POSTS:START[^>]*-->\n).*?(<!-- POSTS:END -->)",
                 lambda m: m.group(1) + ("\n".join(cards) + "\n" if cards else "") + m.group(2),
                 text, flags=re.S)
    if new != text:
        idx.write_text(new, encoding="utf-8")
    print(f"blog/index.html: статей — {len(posts)}")


def build_sitemap(posts):
    today = date.today().isoformat()
    pages = []
    for f in sorted(ROOT.rglob("index.html")):
        rel = f.relative_to(ROOT)
        if any(part.startswith(".") for part in rel.parts) or rel.parts[0] in {"tools", "api", "node_modules"}:
            continue
        text = f.read_text(encoding="utf-8")
        if 'name="robots" content="noindex' in text:
            continue
        url_path = "/" if rel.parent == Path(".") else "/" + rel.parent.as_posix() + "/"
        lastmod = meta(text, "article:modified") or meta(text, "article:published") or today
        prio = "1.0" if url_path == "/" else ("0.8" if url_path.startswith("/blog/") else "0.3")
        pages.append((url_path, lastmod, prio))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod, prio in pages:
        lines.append(f"  <url><loc>{BASE}{path}</loc><lastmod>{lastmod}</lastmod><priority>{prio}</priority></url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml: страниц — {len(pages)}")


def check_placeholders():
    warn = []
    for f in ROOT.rglob("*.html"):
        if "{{" in f.read_text(encoding="utf-8"):
            warn.append(str(f.relative_to(ROOT)))
    for w in warn:
        print(f"! незаполненный шаблон {{{{...}}}} в {w}", file=sys.stderr)


if __name__ == "__main__":
    posts = collect_posts()
    build_blog_index(posts)
    build_sitemap(posts)
    check_placeholders()
