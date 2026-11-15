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
import hashlib
import html
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://xn----dtbhcl5bjjfg.xn--p1ai"   # питер-свет.рф в punycode
EXCLUDE = {"404.html"}
# Разделы блога: название → адрес-якорь. Новый раздел добавляется сюда.
SECTIONS = {
    "Электрика под ключ": "pod-klyuch",
    "Замена проводки": "zamena-provodki",
    "Штробление": "shtroblenie",
    "Розетки и выключатели": "rozetki",
    "Щиты и автоматы": "shchity",
}
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
            "section": meta(text, "article:section") or "Электрика под ключ",
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def card(p, heading="h2"):
    sec_slug = SECTIONS.get(p["section"], "")
    return (
        f'        <a class="tile post-card" data-tile data-section="{sec_slug}" href="/blog/{p["slug"]}/">\n'
        f'          <span class="post-card__meta"><span class="post-card__section">{html.escape(p["section"])}</span>'
        f'<time class="post-card__date" datetime="{p["date"]}">{human_date(p["date"])}</time></span>\n'
        f'          <{heading} class="post-card__title">{html.escape(p["title"])}</{heading}>\n'
        f'          <p class="post-card__text">{html.escape(p["excerpt"])}</p>\n'
        f'          <span class="post-card__more">Читать →</span>\n'
        f'        </a>'
    )


def replace_block(text, name, content):
    """Заменяет содержимое между <!-- NAME:START ... --> и <!-- NAME:END -->."""
    return re.sub(r"(<!-- %s:START[^>]*-->\n).*?(\s*<!-- %s:END -->)" % (name, name),
                  lambda m: m.group(1) + (content + "\n" if content else "") + m.group(2).lstrip(), text, flags=re.S)


def build_blog_index(posts):
    idx = ROOT / "blog" / "index.html"
    text = idx.read_text(encoding="utf-8")
    counts = {}
    for p in posts:
        counts[p["section"]] = counts.get(p["section"], 0) + 1
    chips = [f'        <button type="button" class="pill" data-filter="" aria-pressed="true">Все <span>{len(posts)}</span></button>']
    for name, slug in SECTIONS.items():
        n = counts.get(name, 0)
        if n:
            chips.append(f'        <button type="button" class="pill" data-filter="{slug}" aria-pressed="false">{html.escape(name)} <span>{n}</span></button>')
    new = replace_block(text, "SECTIONS", "\n".join(chips))
    new = replace_block(new, "POSTS", "\n".join(card(p) for p in posts))
    if new != text:
        idx.write_text(new, encoding="utf-8")
    print(f"blog/index.html: статей — {len(posts)}, разделов — {len(counts)}")


def build_article_nav(posts):
    """В каждую статью: раздел над заголовком, «Ещё в разделе», кнопки «Все статьи / Предыдущая / Следующая»."""
    n = len(posts)
    for i, p in enumerate(posts):
        f = ROOT / "blog" / p["slug"] / "index.html"
        text = f.read_text(encoding="utf-8")
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < n else None
        same = [q for q in posts if q["section"] == p["section"] and q["slug"] != p["slug"]][:3]
        if len(same) < 3:
            same += [q for q in posts if q["slug"] != p["slug"] and q not in same][: 3 - len(same)]
        sec_slug = SECTIONS.get(p["section"], "")
        parts = ['      <nav class="tile article-nav" data-tile aria-label="Навигация по статьям">']
        if same:
            parts.append(f'        <h2 class="article-nav__title">Ещё по теме</h2>')
            parts.append('        <ul class="article-nav__list">')
            for q in same:
                parts.append(f'          <li><a href="/blog/{q["slug"]}/"><span>{html.escape(q["section"])}</span>{html.escape(q["title"])}</a></li>')
            parts.append('        </ul>')
        parts.append('        <div class="article-nav__buttons">')
        parts.append('          <a class="btn btn--ghost" href="/blog/">Все статьи</a>')
        parts.append(f'          <a class="btn btn--ghost" href="/blog/#{sec_slug}">Раздел «{html.escape(p["section"])}»</a>')
        if newer:
            parts.append(f'          <a class="btn btn--ghost" href="/blog/{newer["slug"]}/" rel="prev">← Предыдущая</a>')
        if older:
            parts.append(f'          <a class="btn btn--accent" href="/blog/{older["slug"]}/" rel="next">Следующая статья →</a>')
        parts.append('        </div>')
        parts.append('      </nav>')
        nav = "\n".join(parts)
        if "<!-- NAV:START" not in text:
            text = text.replace('      <aside class="tile article-cta"', "<!-- NAV:START — собирается tools/build.py -->\n<!-- NAV:END -->\n\n      <aside class=\"tile article-cta\"", 1)
        new = replace_block(text, "NAV", nav)
        label = f'<a class="article__section" href="/blog/#{sec_slug}">{html.escape(p["section"])}</a>'
        if 'class="article__section"' in new:
            new = re.sub(r'<a class="article__section"[^>]*>.*?</a>', label, new, count=1)
        else:
            new = new.replace('        <h1>', f'        {label}\n        <h1>', 1)
        if new != text:
            f.write_text(new, encoding="utf-8")
    print(f"навигация обновлена в статьях: {n}")


TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a","b","v","g","d","e","e","zh","z","i","y","k","l","m","n","o","p","r","s","t","u","f","h","c","ch","sh","sch","","y","","e","yu","ya"]))


def slugify(text):
    t = "".join(TRANSLIT.get(c, c) for c in re.sub(r"<[^>]+>", "", text).lower())
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:48] or "razdel"


def build_toc_and_checks(posts):
    """Оглавление по заголовкам h2 в каждой статье + проверка, что есть инфографика."""
    for p in posts:
        f = ROOT / "blog" / p["slug"] / "index.html"
        text = f.read_text(encoding="utf-8")
        a = text.find('<article class="tile article"')
        b = text.find("</article>", a)
        if a < 0 or b < 0:
            continue
        art = text[a:b]
        used = set()

        def add_id(m):
            attrs, inner = m.group(1), m.group(2)
            hid = re.search(r'id="([^"]+)"', attrs)
            sid = hid.group(1) if hid else slugify(inner)
            base, i = sid, 2
            while sid in used:
                sid = f"{base}-{i}"; i += 1
            used.add(sid)
            if not hid:
                attrs = attrs + f' id="{sid}"'
            return f"<h2{attrs}>{inner}</h2>"

        art = re.sub(r"<h2([^>]*)>(.*?)</h2>", add_id, art)
        heads = re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>', art)
        heads = [(i, h) for i, h in heads if "Коротко" not in h]
        toc = ""
        if len(heads) >= 3:
            items = "\n".join(f'            <li><a href="#{i}">{re.sub(r"<[^>]+>", "", h)}</a></li>' for i, h in heads)
            toc = ('        <nav class="toc" aria-label="Содержание">\n          <div class="toc__title">Содержание</div>\n'
                   f"          <ol>\n{items}\n          </ol>\n        </nav>")
        if "<!-- TOC:START" not in art:
            art = re.sub(r'(<p class="article__meta">.*?</p>\n)', r"\1<!-- TOC:START — собирается tools/build.py -->\n<!-- TOC:END -->\n", art, count=1, flags=re.S)
        art = replace_block(art, "TOC", toc)
        new = text[:a] + art + text[b:]
        # разметка FAQPage по блоку «Частые вопросы»
        qa = re.findall(r'<details class="ig-faq__item"><summary>(.*?)</summary><div class="ig-faq__a">(.*?)</div></details>', art, re.S)
        strip = lambda x: html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
        ld = ""
        if qa:
            import json
            data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a_)}} for q, a_ in qa]}
            ld = '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"
        if "<!-- FAQLD:START" not in new:
            new = new.replace("</head>", "<!-- FAQLD:START — собирается tools/build.py -->\n<!-- FAQLD:END -->\n</head>", 1)
        new = replace_block(new, "FAQLD", ld)
        if new != text:
            f.write_text(new, encoding="utf-8")
        n = len(re.findall(r'class="ig[ -]|class="ig-', art))
        blocks = len(set(re.findall(r'class="(ig-(?:facts|steps|cards|compare|flow|bars|callout|summary|table|check|faq))', art)))
        _txt = " ".join(re.sub(r"<[^>]+>", " ", x) for x in re.findall(r"<p[^>]*>(.*?)</p>", art, flags=re.S))
        _sent = [x for x in re.split(r"(?<=[.!?])\s+", _txt) if len(x.split()) > 2]
        if _sent:
            _avg = sum(len(x.split()) for x in _sent) / len(_sent)
            if _avg > 17:
                print(f"! {p['slug']}: в среднем {_avg:.0f} слов в предложении — по образцу нужно 12–15", file=sys.stderr)
        if "₽" in art:
            print(f"! в статье {p['slug']} есть цена (₽) — в статьях цен быть не должно", file=sys.stderr)
        if blocks < 4:
            print(f"! мало инфографики в {p['slug']}: {blocks} типов блоков (нужно не меньше 4)", file=sys.stderr)


# ---------------------------------------------------------------- общее для всех страниц
NAV_HTML = ('<nav class="nav" aria-label="Разделы"><a href="/uslugi/">Услуги</a><a href="/#works">Работы</a>'
            '<a href="/kalkulyator/">Калькулятор</a><a href="/blog/">Статьи</a><a href="/#contact">Контакты</a></nav>')
FOOT_HTML = ('<nav aria-label="Нижнее меню"><a href="/uslugi/">Услуги</a><a href="/kalkulyator/">Цены</a><a href="/blog/">Статьи</a>'
             '<a href="/privacy/">Конфиденциальность</a><a href="tel:+79601604425">+7 960 160-44-25</a></nav>')
LOGO_OLD = '<img class="logo__img" src="/assets/img/logo-96.webp" alt=""'
LOGO_NEW = '<img class="logo__img" src="/assets/img/logo-96.webp" alt="Питер-Свет"'


def build_chrome():
    """Одинаковое меню, подвал и alt логотипа на всех страницах."""
    n = 0
    for f in ROOT.rglob("*.html"):
        if any(part.startswith(".") for part in f.relative_to(ROOT).parts) or f.relative_to(ROOT).parts[0] in {"tools", "node_modules"}:
            continue
        text = f.read_text(encoding="utf-8")
        new = re.sub(r'<nav class="nav" aria-label="Разделы">.*?</nav>', NAV_HTML, text, count=1, flags=re.S)
        new = re.sub(r'<nav aria-label="Нижнее меню">.*?</nav>', FOOT_HTML, new, count=1, flags=re.S)
        new = new.replace(LOGO_OLD, LOGO_NEW)
        if new != text:
            f.write_text(new, encoding="utf-8"); n += 1
    print(f"меню и подвал обновлены в файлах: {n}")


# ---------------------------------------------------------------- автор и ссылка на услугу в статьях
AUTHOR = {"name": "Алексей Лебедев", "job": "Мастер-электрик, руководитель бригады «Питер-Света», опыт более 6 лет",
          "photo": "/assets/img/author.webp"}   # фото появится — положить файл, блок подхватит сам
SERVICE_LINKS = [  # (условие, адрес, название) — первая подходящая строка
    (lambda p: "hrushch" in p["slug"], "/uslugi/zamena-provodki-v-hrushchevke-spb/", "Замена проводки в хрущевке в СПб"),
    (lambda p: "novostro" in p["slug"], "/uslugi/elektrika-v-novostroyke-spb/", "Электрика в новостройке в СПб"),
    (lambda p: "shchit" in p["slug"] or p["section"] == "Щиты и автоматы", "/uslugi/sborka-elektroshchita-spb/", "Сборка электрощита в СПб"),
    (lambda p: p["section"] in ("Электрика под ключ", "Розетки и выключатели", "Штробление"),
     "/uslugi/elektrika-pod-klyuch-spb/", "Электрика под ключ в СПб"),
    (lambda p: True, "/uslugi/zamena-provodki-v-kvartire-spb/", "Замена проводки в квартире в СПб"),
]


def build_author_and_service(posts):
    import json
    has_photo = (ROOT / AUTHOR["photo"].lstrip("/")).exists()
    ava = (f'<img class="author__photo" src="{AUTHOR["photo"]}" alt="{AUTHOR["name"]}" width="56" height="56" loading="lazy">' if has_photo
           else '<span class="author__photo author__photo--initials" aria-hidden="true">АЛ</span>')
    for p in posts:
        f = ROOT / "blog" / p["slug"] / "index.html"
        text = f.read_text(encoding="utf-8")
        mod = meta(text, "article:modified")
        upd = f' · обновлено <time datetime="{mod}">{human_date(mod)}</time>' if mod and mod != p["date"] else ""
        block = (f'        <div class="author">{ava}<div><b>{AUTHOR["name"]}</b><span>{AUTHOR["job"]}</span>'
                 + (f'<span>Обновлено <time datetime="{mod}">{human_date(mod)}</time></span>' if upd else '') + '</div></div>')
        new = text
        if "<!-- AUTHOR:START" not in new:
            new = re.sub(r'(<p class="article__meta">.*?</p>\n)', r"\1<!-- AUTHOR:START — собирается tools/build.py -->\n<!-- AUTHOR:END -->\n", new, count=1, flags=re.S)
        new = replace_block(new, "AUTHOR", block)
        url, name = next((u, n) for cond, u, n in SERVICE_LINKS if cond(p))
        svc = (f'        <p class="service-link">{"Услуга по теме"}: <a href="{url}">{name}</a> — этапы, гарантия и расчёт стоимости.</p>')
        if "<!-- SERVICE:START" not in new:
            i = new.find("      </article>")
            new = new[:i] + "<!-- SERVICE:START — собирается tools/build.py -->\n<!-- SERVICE:END -->\n" + new[i:]
        new = replace_block(new, "SERVICE", svc)
        person = {"@type": "Person", "name": AUTHOR["name"], "jobTitle": AUTHOR["job"], "worksFor": {"@type": "Organization", "name": "Питер-Свет"}}
        new = re.sub(r'"author": \{[^{}]*(\{[^{}]*\}[^{}]*)*\}', '"author": ' + json.dumps(person, ensure_ascii=False), new, count=1)
        if mod:
            new = re.sub(r'"dateModified": "[^"]*"', f'"dateModified": "{mod}"', new, count=1)
        if new != text:
            f.write_text(new, encoding="utf-8")


def build_home_faq_ld():
    """Разметка FAQPage для блока «Частые вопросы» на главной."""
    import json
    f = ROOT / "index.html"
    text = f.read_text(encoding="utf-8")
    sec = re.search(r'<section class="section" id="faq">.*?</section>', text, re.S).group(0)
    qa = re.findall(r'<summary>(.*?)</summary>\s*<p[^>]*>(.*?)</p>', sec, re.S)
    strip = lambda x: html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in qa]}
    ld = '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"
    if "<!-- FAQLD:START" not in text:
        text2 = text.replace("</head>", "<!-- FAQLD:START — собирается tools/build.py -->\n<!-- FAQLD:END -->\n</head>", 1)
    else:
        text2 = text
    new = replace_block(text2, "FAQLD", ld)
    if new != text:
        f.write_text(new, encoding="utf-8")
    print(f"вопросов на главной: {len(qa)}")


def build_home_latest(posts):
    f = ROOT / "index.html"
    text = f.read_text(encoding="utf-8")
    new = replace_block(text, "LATEST", "\n".join(card(p, "h3") for p in posts[:3]))
    if new != text:
        f.write_text(new, encoding="utf-8")


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
        prio = "1.0" if url_path == "/" else ("0.9" if url_path.startswith(("/uslugi/", "/kalkulyator/")) else ("0.8" if url_path.startswith("/blog/") else "0.3"))
        pages.append((url_path, lastmod, prio))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod, prio in pages:
        lines.append(f"  <url><loc>{BASE}{path}</loc><lastmod>{lastmod}</lastmod><priority>{prio}</priority></url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sitemap.xml: страниц — {len(pages)}")


def bust_cache():
    """Добавляет к ссылкам на style.css и main.js метку версии (?v=хеш содержимого).
    Изменился файл — изменилась метка, и браузер посетителя скачает новую версию,
    а не возьмёт старую из кэша."""
    assets = ["/assets/css/style.css", "/assets/js/main.js"]
    tags = {a: hashlib.md5((ROOT / a.lstrip("/")).read_bytes()).hexdigest()[:8] for a in assets}
    changed = 0
    for f in ROOT.rglob("*.html"):
        if any(part.startswith(".") for part in f.relative_to(ROOT).parts):
            continue
        text = f.read_text(encoding="utf-8")
        new = text
        for a, h in tags.items():
            new = re.sub(re.escape(a) + r'(\?v=[0-9a-f]+)?"', f'{a}?v={h}"', new)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
    print(f"метки версий CSS/JS обновлены в файлах: {changed}")


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
    build_article_nav(posts)
    build_toc_and_checks(posts)
    build_author_and_service(posts)
    build_home_latest(posts)
    build_home_faq_ld()
    build_chrome()
    build_sitemap(posts)
    bust_cache()
    check_placeholders()
