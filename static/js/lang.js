/* ============================================================
   AgroConnect — Language System
   Saves to localStorage forever.
   Supports: English (en), Marathi (mr), Hindi (hi)
============================================================ */

var AGRO_LANG_KEY = 'agro_lang';
var SUPPORTED = ['en', 'mr', 'hi'];

/* ── Get current language ── */
function getLang() {
    var stored = localStorage.getItem(AGRO_LANG_KEY);
    return (stored && SUPPORTED.indexOf(stored) !== -1) ? stored : null;
}

/* ── Set language and apply ── */
function setLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) return;
    localStorage.setItem(AGRO_LANG_KEY, lang);
    applyLang(lang);
    updateNavPill(lang);
}

/* ── Apply language to entire page ── */
function applyLang(lang) {
    // Translate all elements with data-en / data-mr / data-hi
    document.querySelectorAll('[data-en]').forEach(function(el) {
        var text = el.getAttribute('data-' + lang) || el.getAttribute('data-en');
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
            el.placeholder = text;
        } else if (el.tagName === 'OPTION') {
            el.textContent = text;
        } else {
            el.innerHTML = text;
        }
    });

    // Update html lang attribute for accessibility
    document.documentElement.lang = lang === 'mr' ? 'mr' : lang === 'hi' ? 'hi' : 'en';

    // Update page direction (all 3 are LTR)
    document.documentElement.dir = 'ltr';
}

/* ── Update active state of navbar language pill ── */
function updateNavPill(lang) {
    ['en', 'mr', 'hi'].forEach(function(l) {
        var btn = document.getElementById('lang-btn-' + l);
        if (!btn) return;
        if (l === lang) {
            btn.style.background = '#4aad6f';
            btn.style.color = 'white';
            btn.style.fontWeight = '800';
        } else {
            btn.style.background = 'transparent';
            btn.style.color = 'rgba(255,255,255,0.4)';
            btn.style.fontWeight = '600';
        }
    });
}

/* ── Auto-run on every page load ── */
document.addEventListener('DOMContentLoaded', function() {
    var lang = getLang();
    if (lang) {
        applyLang(lang);
        updateNavPill(lang);
    }
    // else — no language set yet, splash will handle it
});