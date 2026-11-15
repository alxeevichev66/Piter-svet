/* Питер-Свет — скрипты сайта. Без библиотек. */
(function () {
  'use strict';

  /* ---------- Настройки ---------- */
  var CONFIG = {
    pricePerM2: 1500,                         // базовая цена, ₽/м²
    typeK: { flat: 1, house: 1.2, office: 1.1 }, // наценка за тип объекта
    scopeK: { rough: 1, full: 1.3 },            // черновой / черновой + чистовой
    metrikaId: 114262207                       // номер счётчика Яндекс.Метрики (0 — выключено)
  };

  /* ---------- Яндекс.Метрика (включается, когда указан номер) ---------- */
  function goal(name) {
    if (CONFIG.metrikaId && window.ym) window.ym(CONFIG.metrikaId, 'reachGoal', name);
  }
  if (CONFIG.metrikaId) {
    (function (m, e, t, r, i, k, a) {
      m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
      m[i].l = 1 * new Date();
      for (var j = 0; j < document.scripts.length; j++) { if (document.scripts[j].src === r) { return; } }
      k = e.createElement(t); a = e.getElementsByTagName(t)[0];
      k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
    })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js?id=' + CONFIG.metrikaId, 'ym');
    window.ym(CONFIG.metrikaId, 'init', { ssr: true, webvisor: true, clickmap: true, ecommerce: 'dataLayer',
      referrer: document.referrer, url: location.href, accurateTrackBounce: true, trackLinks: true });
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="tel:"]');
    if (a) goal('call');
  });

  /* ---------- Кабель-гирлянда между плитками ---------- */
  var page = document.querySelector('.page');
  var svg = document.querySelector('.cable');
  var plugsBox = document.querySelector('.plugs');
  var P = 13;  // радиус коннектора
  var G = 5;   // зазор между плиткой и коннектором
  var R = 14;  // скругление поворотов

  function rounded(pts) {
    var d = 'M' + pts[0][0] + ' ' + pts[0][1];
    for (var i = 1; i < pts.length - 1; i++) {
      var p0 = pts[i - 1], p1 = pts[i], p2 = pts[i + 1];
      var d1 = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]), d2 = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
      if (d1 < 0.5 || d2 < 0.5) continue;
      var k = Math.min(R, d1 / 2, d2 / 2);
      d += 'L' + (p1[0] - (p1[0] - p0[0]) / d1 * k).toFixed(1) + ' ' + (p1[1] - (p1[1] - p0[1]) / d1 * k).toFixed(1) +
           'Q' + p1[0] + ' ' + p1[1] + ' ' + (p1[0] + (p2[0] - p1[0]) / d2 * k).toFixed(1) + ' ' + (p1[1] + (p2[1] - p1[1]) / d2 * k).toFixed(1);
    }
    var e = pts[pts.length - 1];
    return d + 'L' + e[0] + ' ' + e[1];
  }

  function plug(side, x, y) {
    var s = { left: 0, top: 0, width: 2 * P, height: P, r: '' };
    if (side === 'top')    { s.left = x - P; s.top = y - P - G; s.r = P + 'px ' + P + 'px 0 0'; }
    if (side === 'bottom') { s.left = x - P; s.top = y + G;     s.r = '0 0 ' + P + 'px ' + P + 'px'; }
    if (side === 'left')   { s.left = x - P - G; s.top = y - P; s.width = P; s.height = 2 * P; s.r = P + 'px 0 0 ' + P + 'px'; }
    if (side === 'right')  { s.left = x + G;     s.top = y - P; s.width = P; s.height = 2 * P; s.r = '0 ' + P + 'px ' + P + 'px 0'; }
    return '<span class="plug" style="left:' + s.left + 'px;top:' + s.top + 'px;width:' + s.width + 'px;height:' + s.height + 'px;border-radius:' + s.r + '"></span>';
  }

  var lastKey = '';
  function layoutCable() {
    if (!page || !svg || !plugsBox) return;
    var rb = page.getBoundingClientRect();
    var tiles = Array.prototype.map.call(page.querySelectorAll('[data-tile]'), function (el) {
      var b = el.getBoundingClientRect();
      var t = { l: b.left - rb.left, r: b.right - rb.left, t: b.top - rb.top, b: b.bottom - rb.top };
      t.x = Math.round((t.l + t.r) / 2);
      return t;
    }).filter(function (t) { return t.r - t.l > 0; });
    if (tiles.length < 2) return;
    var d = '', html = '';
    for (var i = 0; i < tiles.length - 1; i++) {
      var a = tiles[i], n = tiles[i + 1];
      var sameRow = n.l >= a.r - 1 && n.t < a.b - 16 && n.b > a.t + 16;
      if (sameRow) {                                   // следующая справа
        var y = Math.round((Math.max(a.t, n.t) + Math.min(a.b, n.b)) / 2);
        html += plug('right', a.r, y) + plug('left', n.l, y);
        d += rounded([[a.r + G + P, y], [n.l - G - P, y]]);
      } else {                                         // следующая ниже
        html += plug('bottom', a.x, a.b) + plug('top', n.x, n.t);
        var y0 = a.b + G + P, y1 = n.t - G - P;
        if (Math.abs(a.x - n.x) < 2) d += rounded([[a.x, y0], [n.x, y1]]);
        else {
          var ym = Math.round(y1 - y0 < 90 ? (y0 + y1) / 2 : y1 - 16);
          d += rounded([[a.x, y0], [a.x, ym], [n.x, ym], [n.x, y1]]);
        }
      }
    }
    var key = d + rb.width + 'x' + rb.height;
    if (key === lastKey) return;
    lastKey = key;
    svg.setAttribute('width', rb.width);
    svg.setAttribute('height', rb.height);
    svg.innerHTML = '<path d="' + d + '"/>';
    plugsBox.innerHTML = html;
  }
  var raf = 0;
  function scheduleCable() { cancelAnimationFrame(raf); raf = requestAnimationFrame(layoutCable); }
  window.addEventListener('resize', scheduleCable);
  window.addEventListener('load', scheduleCable);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(scheduleCable);
  if (window.ResizeObserver && page) new ResizeObserver(scheduleCable).observe(page);
  scheduleCable();

  /* ---------- Калькулятор ---------- */
  var calc = document.getElementById('calc-form');
  if (calc) {
    var state = { type: 'flat', scope: 'full', area: 60 };
    var areaInput = document.getElementById('calc-area');
    var areaOut = document.getElementById('calc-area-out');
    var priceOut = document.getElementById('calc-price');
    var shown = null, anim = 0;

    function target() {
      var raw = CONFIG.pricePerM2 * CONFIG.typeK[state.type] * CONFIG.scopeK[state.scope] * state.area;
      return Math.round(raw / 1000) * 1000;
    }
    function fmt(n) { return (Math.round(n / 1000) * 1000).toLocaleString('ru-RU'); }
    function render() {
      areaOut.textContent = state.area + ' м²';
      var to = target();
      var from = shown == null ? to : shown;
      cancelAnimationFrame(anim);
      var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (from === to || reduce) { shown = to; priceOut.textContent = '≈ ' + fmt(to) + ' ₽'; return; }
      var t0 = performance.now(), dur = 450;
      (function step(now) {
        var k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        shown = from + (to - from) * e;
        priceOut.textContent = '≈ ' + fmt(shown) + ' ₽';
        if (k < 1) anim = requestAnimationFrame(step);
      })(t0);
    }
    calc.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-group]');
      if (!b) return;
      var group = b.getAttribute('data-group');
      state[group] = b.getAttribute('data-value');
      calc.querySelectorAll('button[data-group="' + group + '"]').forEach(function (x) {
        x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
      });
      render();
    });
    areaInput.addEventListener('input', function () { state.area = Number(areaInput.value); render(); });
    render();

    // передать расчёт в форму заявки
    var toForm = document.getElementById('calc-to-form');
    if (toForm) toForm.addEventListener('click', function () {
      var names = { flat: 'квартира', house: 'дом', office: 'офис' };
      var area = document.getElementById('lead-area');
      if (area && !area.value) area.value = String(state.area);
      var typeMap = { flat: 'Квартира', house: 'Дом', office: 'Коммерческое' };
      var radio = document.querySelector('#lead-form input[name="type"][value="' + typeMap[state.type] + '"]');
      if (radio) radio.checked = true;
      var calcField = document.getElementById('lead-calc');
      if (calcField) calcField.value = names[state.type] + ', ' + state.area + ' м², ' +
        (state.scope === 'full' ? 'черновой + чистовой' : 'черновой') + ', ≈ ' + fmt(target()) + ' ₽';
      goal('calc_to_form');
    });
  }

  /* ---------- Фильтр статей по разделам ---------- */
  var filter = document.querySelector('.blog-filter');
  if (filter) {
    var applyFilter = function (slug) {
      filter.querySelectorAll('button[data-filter]').forEach(function (b) {
        b.setAttribute('aria-pressed', b.getAttribute('data-filter') === slug ? 'true' : 'false');
      });
      document.querySelectorAll('.posts .post-card').forEach(function (c) {
        c.hidden = !!slug && c.getAttribute('data-section') !== slug;
      });
      scheduleCable();
    };
    filter.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-filter]');
      if (!b) return;
      var slug = b.getAttribute('data-filter');
      history.replaceState(null, '', slug ? '#' + slug : location.pathname);
      applyFilter(slug);
    });
    var initial = location.hash.slice(1);
    if (initial && filter.querySelector('button[data-filter="' + initial + '"]')) applyFilter(initial);
  }

  /* ---------- Форма заявки ---------- */
  var form = document.getElementById('lead-form');
  if (form) {
    var status = form.querySelector('.form__status');
    var btn = form.querySelector('button[type="submit"]');
    var phone = form.querySelector('input[name="phone"]');
    var ts = form.querySelector('input[name="ts"]');
    if (ts) ts.value = String(Date.now());

    // комментарий: высота как у полей, растёт по мере ввода
    var comment = form.querySelector('textarea[name="comment"]');
    function grow() {
      comment.style.height = 'auto';
      comment.style.height = Math.min(comment.scrollHeight + 2, 220) + 'px';
      comment.style.overflowY = comment.scrollHeight > 218 ? 'auto' : 'hidden';
    }
    if (comment) { comment.addEventListener('input', grow); }

    phone.addEventListener('input', function () {
      var dg = phone.value.replace(/\D/g, '');
      if (!dg) { phone.value = ''; return; }
      if (dg[0] === '8') dg = '7' + dg.slice(1);
      if (dg[0] !== '7') dg = '7' + dg;
      dg = dg.slice(0, 11);
      var o = '+7';
      if (dg.length > 1) o += ' ' + dg.slice(1, 4);
      if (dg.length > 4) o += ' ' + dg.slice(4, 7);
      if (dg.length > 7) o += '-' + dg.slice(7, 9);
      if (dg.length > 9) o += '-' + dg.slice(9, 11);
      phone.value = o;
    });

    function setStatus(text, ok) {
      status.textContent = text;
      status.className = 'form__status ' + (ok ? 'form__status--ok' : 'form__status--err');
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (phone.value.replace(/\D/g, '').length < 11) { setStatus('Проверьте номер телефона — нужно 11 цифр.', false); phone.focus(); return; }
      if (!form.querySelector('input[name="consent"]').checked) { setStatus('Нужно согласие на обработку данных.', false); return; }
      btn.disabled = true;
      setStatus('Отправляем…', true);
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'Accept': 'application/json' } })
        .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
        .then(function (res) {
          if (res && res.ok) {
            setStatus('Спасибо! Заявка принята — перезвоним в ближайшее время.', true);
            form.reset();
            if (comment) grow();
            goal('lead');
          } else {
            setStatus((res && res.error) || 'Не получилось отправить. Позвоните: +7 960 160-44-25', false);
          }
        })
        .catch(function () { setStatus('Нет связи с сервером. Позвоните: +7 960 160-44-25', false); })
        .then(function () { btn.disabled = false; });
    });
  }
})();
