"""
Edge-probe: find elements touching viewport edges (clipped-text suspects),
measure header height per viewport, check mobile anchor landing under the
wrapped header. Complements layout_audit.py (which ignores narrow elements).

Run on whimco:  python3 scripts/probe_edge.py
"""
import json

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8022"
VIEWS = ["dashboard", "team", "review"]

PROBE = """
() => {
  const W = window.innerWidth;
  const out = [];
  document.querySelectorAll('body *').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    if (r.right > W - 5 || r.left < 5) {
      out.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className || '').toString().slice(0, 50),
        left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width),
        text: (el.textContent || '').trim().slice(0, 30),
      });
    }
  });
  const header = document.querySelector('.app-header');
  return { W, headerH: header ? Math.round(header.getBoundingClientRect().height) : null, edge: out.slice(0, 14) };
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for label, kw in (
        ("desktop", dict(viewport={"width": 1440, "height": 900})),
        ("mobile", dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)),
    ):
        p = b.new_page(**kw)
        p.goto(BASE + "/", wait_until="networkidle")
        p.wait_for_timeout(800)
        for view in VIEWS:
            p.evaluate("window.location.hash = '" + view + "'")
            p.wait_for_timeout(700)
            r = p.evaluate(PROBE)
            print("== %s %s: W=%s headerH=%s" % (label, view, r["W"], r["headerH"]))
            for e in r["edge"]:
                print("   ", json.dumps(e, ensure_ascii=False))
        if label == "mobile":
            p.evaluate("window.location.hash = 'intro'")
            p.wait_for_timeout(500)
            p.get_by_text("Читать концепцию").click()
            p.wait_for_timeout(1500)
            top = p.evaluate(
                "() => { const el = document.querySelector('#concept-diagnosis'); return el ? Math.round(el.getBoundingClientRect().top) : null; }"
            )
            hh = p.evaluate("() => Math.round(document.querySelector('.app-header').getBoundingClientRect().height)")
            print("== mobile anchor: top=%s headerH=%s" % (top, hh))
        p.close()
    b.close()
