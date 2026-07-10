/*!
 * i18n.js — minimal runtime i18n for static sites (KO/EN baseline, one-URL toggle).
 *
 * Pattern (gettext-style): Korean text stays inline in HTML as the source AND the default,
 * so there is no flash for Korean users and the source lives in exactly one place. Mark
 * nodes with data-i18n* attributes; provide an English dictionary keyed by the Korean
 * source string. No build step, no dependencies. Generalizes to N languages.
 *
 *   Text node:      <h1 data-i18n>나의 비전하우스</h1>
 *   Placeholder:    <input data-i18n-ph placeholder="홍길동">
 *   aria-label:     <nav data-i18n-al aria-label="진행 단계">
 *   title / alt:    data-i18n-ti / data-i18n-alt
 *   Inner markup:   <p data-i18n-html="hero.desc">...<br>...</p>   (keyed, ko+en in config.html)
 *
 *   Dynamic JS strings: I18n.t('한국어 원문')  -> English when active, Korean otherwise.
 *   Toggle markup:      <button class="lang-btn" data-lang="ko">한국어</button>
 *
 * Storage stays locale-neutral on purpose: store ids / 'ko'-style keys, not translated
 * display text, so exports and downstream consumers do not break across languages.
 *
 * Wire it (define render functions first, then init once):
 *   I18n.init({
 *     langs: ['ko', 'en'], default: 'ko', storageKey: 'app_lang',
 *     dict: { en: { '저장됨': 'Saved', '시작하기': 'Start' } },
 *     html: { 'hero.desc': { ko: 'A<br>B', en: 'A<br>B' } },
 *     meta: { ko: { description: '...', ogLocale: 'ko_KR', ogTitle: '...' },
 *             en: { description: '...', ogLocale: 'en_US', ogTitle: '...' } },
 *     onApply: function (lang) { renderDynamic(); }  // (re)render dynamic content in `lang`
 *   });
 * Put i18n.js BEFORE app code so I18n.t / I18n.lang are available; do all dynamic rendering
 * inside onApply (it fires on init and on every language change).
 */
(function (global) {
  'use strict';

  var cfg = {};
  var DEFAULT = 'ko';
  var LANGS = ['ko'];
  var STORE_KEY = 'app_lang';
  var lang = 'ko';

  function dictFor(l) { return (cfg.dict && cfg.dict[l]) || null; }

  function matchLang(raw) {
    if (!raw) return null;
    var normalized = String(raw).trim().toLowerCase().replace(/_/g, '-');
    if (!normalized) return null;
    for (var i = 0; i < LANGS.length; i += 1) {
      if (String(LANGS[i]).toLowerCase() === normalized) return LANGS[i];
    }
    var base = normalized.split('-')[0];
    for (var j = 0; j < LANGS.length; j += 1) {
      if (String(LANGS[j]).toLowerCase().split('-')[0] === base) return LANGS[j];
    }
    return null;
  }

  function browserLang() {
    var prefs = [];
    try {
      if (global.navigator) {
        if (Array.isArray(global.navigator.languages)) prefs = prefs.concat(global.navigator.languages);
        if (global.navigator.language) prefs.push(global.navigator.language);
        if (global.navigator.userLanguage) prefs.push(global.navigator.userLanguage);
      }
    } catch (e) {}
    for (var i = 0; i < prefs.length; i += 1) {
      var supported = matchLang(prefs[i]);
      if (supported) return supported;
    }
    return (prefs.length && LANGS.indexOf('en') >= 0) ? 'en' : DEFAULT;
  }

  function resolve() {
    try {
      var p = matchLang(new URLSearchParams(location.search).get('lang'));
      if (p) return p;
      var s = localStorage.getItem(STORE_KEY);
      var stored = matchLang(s);
      if (stored) return stored;
    } catch (e) {}
    return browserLang();
  }

  // Dynamic JS strings. Source string is the key; returns source on default/missing.
  function t(src) {
    var d = dictFor(lang);
    return (d && d[src] != null) ? d[src] : src;
  }

  function applyStatic() {
    var d = dictFor(lang);
    var tr = function (s) { return (d && d[s] != null) ? d[s] : s; };
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      if (el.__i18nSrc == null) el.__i18nSrc = el.textContent;     // capture source once
      el.textContent = tr(el.__i18nSrc.trim());
    });
    [['data-i18n-ph', 'placeholder', '__i18nPh'], ['data-i18n-al', 'aria-label', '__i18nAl'],
     ['data-i18n-ti', 'title', '__i18nTi'], ['data-i18n-alt', 'alt', '__i18nAlt']].forEach(function (c) {
      document.querySelectorAll('[' + c[0] + ']').forEach(function (el) {
        if (el[c[2]] == null) el[c[2]] = el.getAttribute(c[1]) || '';
        el.setAttribute(c[1], tr(el[c[2]].trim()));
      });
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var pack = cfg.html && cfg.html[el.getAttribute('data-i18n-html')];
      if (pack) el.innerHTML = (pack[lang] != null) ? pack[lang] : (pack[DEFAULT] || el.innerHTML);
    });
  }

  function applyMeta() {
    document.documentElement.setAttribute('lang', lang);
    var m = (cfg.meta && cfg.meta[lang]) || {};
    function set(sel, v) { if (v == null) return; var n = document.querySelector(sel); if (n) n.setAttribute('content', v); }
    set('meta[name="description"]', m.description);
    set('meta[property="og:description"]', m.description);
    set('meta[name="twitter:description"]', m.description);
    set('meta[property="og:locale"]', m.ogLocale);
    set('meta[property="og:title"]', m.ogTitle);
    set('meta[name="twitter:title"]', m.ogTitle);
  }

  function updateToggle() {
    document.querySelectorAll('.lang-btn').forEach(function (b) {
      var on = b.getAttribute('data-lang') === lang;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function set(l) {
    if (LANGS.indexOf(l) < 0 || l === lang) return;
    lang = l;
    try { localStorage.setItem(STORE_KEY, lang); } catch (e) {}
    try { var u = new URL(location.href); u.searchParams.set('lang', lang); history.replaceState(null, '', u); } catch (e) {}
    applyMeta(); applyStatic(); updateToggle();
    if (typeof cfg.onApply === 'function') cfg.onApply(lang);
  }

  function bind() {
    document.querySelectorAll('.lang-btn').forEach(function (b) {
      if (b.__i18nBound) return;
      b.__i18nBound = true;
      b.addEventListener('click', function () { set(b.getAttribute('data-lang')); });
    });
  }

  function init(userCfg) {
    cfg = userCfg || global.I18N || {};
    DEFAULT = cfg.default || 'ko';
    LANGS = cfg.langs || [DEFAULT];
    STORE_KEY = cfg.storageKey || 'app_lang';
    lang = resolve();
    bind();
    applyMeta(); applyStatic(); updateToggle();
    if (typeof cfg.onApply === 'function') cfg.onApply(lang);
    return I18n;
  }

  var I18n = {
    init: init,
    set: set,
    t: t,
    refresh: function () { applyMeta(); applyStatic(); updateToggle(); },
    get lang() { return lang; },
    isDefault: function () { return lang === DEFAULT; }
  };

  global.I18n = I18n;
})(window);
