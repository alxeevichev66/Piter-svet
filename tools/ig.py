"""Помощники для инфографики в статьях Питер-Свет (см. docs/ARTICLES.md, раздел «Инфографика»).

Пример:
    import sys; sys.path.insert(0, "tools")
    from ig import *
    set_body("adres-stati", p("Вступление…") + facts([...], "Главное за 10 секунд") + h2("…") + steps([...]) + summary([...]))
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def I(name):
    return f'<svg class="ico" aria-hidden="true"><use href="/assets/img/icons.svg#{name}"/></svg>'


def title(t):
    return f'          <p class="ig__title">{t}</p>\n' if t else ''


def facts(items, t=None):
    rows = "\n".join(
        f'            <div class="ig-fact">{I(ic)}<span class="ig-fact__value">{v}</span><span class="ig-fact__label">{l}</span></div>'
        for ic, v, l in items)
    return f'        <div class="ig">\n{title(t)}          <div class="ig-facts">\n{rows}\n          </div>\n        </div>\n'


def steps(items, t=None):
    rows = []
    for it in items:
        tt, tx = it[0], it[1]
        meta = f'<span class="ig-step__meta">{I(it[2][0])}{it[2][1]}</span>' if len(it) > 2 else ''
        rows.append(f'            <li class="ig-step"><div class="ig-step__body"><div class="ig-step__title">{tt}</div><div class="ig-step__text">{tx}</div>{meta}</div></li>')
    return f'        <div class="ig">\n{title(t)}          <ol class="ig-steps">\n' + "\n".join(rows) + '\n          </ol>\n        </div>\n'


def cards(items, t=None, danger=False):
    cls = 'ig-cards ig-cards--danger' if danger else 'ig-cards'
    rows = "\n".join(
        f'            <div class="ig-card"><span class="ig-card__icon">{I(ic)}</span><div><div class="ig-card__title">{tt}</div>'
        + (f'<div class="ig-card__text">{tx}</div>' if tx else '') + '</div></div>'
        for ic, tt, tx in items)
    return f'        <div class="ig">\n{title(t)}          <div class="{cls}">\n{rows}\n          </div>\n        </div>\n'


def compare(bad_title, bad, good_title, good, t=None):
    b = "\n".join(f'                <li>{I("cross")}<span>{x}</span></li>' for x in bad)
    g = "\n".join(f'                <li>{I("check")}<span>{x}</span></li>' for x in good)
    return (f'        <div class="ig">\n{title(t)}          <div class="ig-compare">\n'
            f'            <div class="ig-col ig-col--bad"><div class="ig-col__head">{I("cross")}{bad_title}</div><ul>\n{b}\n              </ul></div>\n'
            f'            <div class="ig-col ig-col--good"><div class="ig-col__head">{I("check")}{good_title}</div><ul>\n{g}\n              </ul></div>\n'
            '          </div>\n        </div>\n')


def flow(items, t=None):
    parts = []
    for i, (ic, tt, tx) in enumerate(items):
        if i:
            parts.append(f'            <span class="ig-flow__arrow">{I("arrow")}</span>')
        parts.append(f'            <div class="ig-node">{I(ic)}<span class="ig-node__title">{tt}</span><span class="ig-node__text">{tx}</span></div>')
    return f'        <div class="ig">\n{title(t)}          <div class="ig-flow">\n' + "\n".join(parts) + '\n          </div>\n        </div>\n'


def bars(items, t=None):
    mx = max(v for _, v, _ in items)
    rows = "\n".join(
        f'            <div class="ig-bar"><span>{l}</span><div class="ig-bar__track"><div class="ig-bar__fill" style="width:{v / mx * 100:.0f}%"></div></div><span class="ig-bar__value">{lab}</span></div>'
        for l, v, lab in items)
    return f'        <div class="ig">\n{title(t)}          <div class="ig-bars">\n{rows}\n          </div>\n        </div>\n'


def callout(kind, text):
    ic = {'warn': 'warn', 'tip': 'bulb', 'pro': 'tool'}[kind]
    return f'        <div class="ig-callout ig-callout--{kind}">{I(ic)}<div>{text}</div></div>\n'


def summary(items):
    rows = "\n".join(f'          <li>{I("check")}<span>{x}</span></li>' for x in items)
    return f'        <h2>Коротко</h2>\n        <ul class="ig-summary">\n{rows}\n        </ul>\n'


def p(text):
    return f'        <p>{text}</p>\n'


def h2(text):
    return f'        <h2>{text}</h2>\n'


def set_body(slug, body):
    f = ROOT / 'blog' / slug / 'index.html'
    s = f.read_text(encoding='utf-8')
    m = re.search(r'(<p class="article__meta">.*?</p>\n)(.*?)(      </article>)', s, re.S)
    assert m, slug
    s = s[:m.start(2)] + body + s[m.end(2):]
    s = re.sub(r'· \d+ минут[аы]? чтения', '· ' + read_time(body), s, count=1)
    f.write_text(s, encoding='utf-8')
    print('ok', slug, len(re.sub(r'<[^>]+>', ' ', body).split()), 'слов')


def read_time(body):
    n = len(re.sub(r'<[^>]+>', ' ', body).split())
    m = max(3, round(n / 170))
    return f'{m} минут чтения' if m >= 5 else f'{m} минуты чтения'
