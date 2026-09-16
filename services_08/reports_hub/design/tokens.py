"""Дизайн-токены Reports Hub (спека §6.1, H3).

Apple-стиль, mobile-first: light + dark через CSS-переменные,
переключатель темы в шапке + `prefers-color-scheme`. Без градиентов,
glassmorphism, glow (anti-slop-design-system.md).
"""

from __future__ import annotations

#: Акцент по умолчанию (системный синий Apple, светлая тема).
DEFAULT_ACCENT_LIGHT = "#0071e3"

#: Акцент по умолчанию (тёмная тема).
DEFAULT_ACCENT_DARK = "#0a84ff"


def build_css(accent_light: str = DEFAULT_ACCENT_LIGHT, accent_dark: str = DEFAULT_ACCENT_DARK) -> str:
    """Сгенерировать самодостаточный CSS отчёта (inline, без внешних CDN).

    Args:
        accent_light: акцентный цвет светлой темы.
        accent_dark: акцентный цвет тёмной темы.

    Returns:
        CSS-текст с light/dark токенами, mobile-first сеткой, timeline,
        карточками библиотеки, таблицами-этапами (карточки на мобильном).
    """
    return f""":root{{color-scheme:light dark;--bg:#ffffff;--bg-secondary:#f5f5f7;--card:#ffffff;--text:#1d1d1f;--text-secondary:#6e6e73;--separator:#d2d2d7;--accent:{accent_light};--good:#34c759;--warn:#ff9f0a;--bad:#ff3b30;--radius:16px;--font:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif}}
[data-theme="dark"]{{--bg:#000000;--bg-secondary:#1d1d1f;--card:#1d1d1f;--text:#f5f5f7;--text-secondary:#86868b;--separator:#424245;--accent:{accent_dark}}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#000000;--bg-secondary:#1d1d1f;--card:#1d1d1f;--text:#f5f5f7;--text-secondary:#86868b;--separator:#424245;--accent:{accent_dark}}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);font-size:16px;line-height:1.5}}
.topbar{{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 80%,transparent);backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid var(--separator)}}
.topbar-inner{{max-width:960px;margin:0 auto;padding:12px 16px;display:flex;gap:12px;align-items:center}}
.topbar-title{{font-size:17px;font-weight:600;flex:1}}
.theme-btn{{min-height:44px;padding:8px 14px;border:1px solid var(--separator);border-radius:999px;background:var(--card);color:var(--text);font-size:14px}}
.wrap{{max-width:960px;margin:0 auto;padding:20px 16px 96px}}
.large-title{{font-size:32px;font-weight:700;letter-spacing:-.02em;margin:8px 0 4px}}
.subtitle{{color:var(--text-secondary);font-size:14px;margin:0 0 16px}}
.metrics{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}}
.metric{{background:var(--card);border:1px solid var(--separator);border-radius:var(--radius);padding:14px}}
.metric-label{{font-size:13px;color:var(--text-secondary)}}
.metric-value{{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}}
.section-title{{font-size:21px;font-weight:600;margin:28px 0 12px}}
.timeline{{border-left:2px solid var(--separator);margin:0 0 0 8px;padding:0 0 0 20px;list-style:none}}
.timeline li{{position:relative;margin:0 0 16px}}
.timeline li::before{{content:"";position:absolute;left:-29px;top:6px;width:12px;height:12px;border-radius:50%;background:var(--accent)}}
.commit-chip{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;background:var(--bg-secondary);border:1px solid var(--separator);border-radius:6px;padding:2px 6px;white-space:nowrap}}
.status-open{{color:var(--warn)}}.status-done{{color:var(--good)}}.status-todo{{color:var(--text-secondary)}}
details.card{{background:var(--card);border:1px solid var(--separator);border-radius:var(--radius);padding:12px 14px;margin:0 0 12px}}
details.card summary{{cursor:pointer;min-height:44px;font-weight:600}}
.doc-grid{{display:grid;grid-template-columns:1fr;gap:12px}}
.doc-card{{display:block;background:var(--card);border:1px solid var(--separator);border-radius:var(--radius);padding:14px;text-decoration:none;color:inherit}}
.doc-card h3{{margin:0 0 4px;font-size:17px}}
.doc-card p{{margin:4px 0;font-size:14px;color:var(--text-secondary)}}
.badge-new{{display:inline-block;background:var(--good);color:#fff;font-size:12px;font-weight:700;border-radius:6px;padding:2px 8px}}
.diff-block{{background:var(--card);border:1px solid var(--separator);border-left:3px solid var(--good);border-radius:var(--radius);padding:12px 16px;margin:0 0 16px;font-size:14px}}
table.stages{{width:100%;border-collapse:collapse;font-size:14px}}
table.stages th,table.stages td{{text-align:left;padding:10px;border-bottom:1px solid var(--separator);vertical-align:top}}
@media (max-width:719px){{table.stages thead{{display:none}}table.stages tr{{display:block;border:1px solid var(--separator);border-radius:var(--radius);margin:0 0 12px;padding:8px 12px}}table.stages td{{display:block;border:0;padding:4px 0}}}}
@media (min-width:720px){{.doc-grid{{grid-template-columns:1fr 1fr}}.metrics{{grid-template-columns:repeat(4,1fr)}}.large-title{{font-size:34px}}}}
.diag{{font-size:13px;color:var(--text-secondary)}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
.topbar,.metric,.doc-card,details.card{{transition:opacity .18s ease-out,transform .18s ease-out}}
"""


def theme_script() -> str:
    """JS переключателя темы (системная/светлая/тёмная, localStorage)."""
    return """(function(){var k="rh-theme";function apply(t){var r=document.documentElement;if(t==="system"){r.removeAttribute("data-theme");}else{r.setAttribute("data-theme",t);}var b=document.getElementById("theme-btn");if(b){b.textContent=t==="dark"?"Тёмная":t==="light"?"Светлая":"Авто";}}function next(){var r=document.documentElement;var cur=r.getAttribute("data-theme")||"system";var n=cur==="system"?"light":cur==="light"?"dark":"system";try{localStorage.setItem(k,n);}catch(e){}apply(n);}try{var s=localStorage.getItem(k);if(s){apply(s);}else{apply("system");}}catch(e){apply("system");}document.addEventListener("click",function(e){if(e.target&&e.target.id==="theme-btn"){next();}});})();"""
