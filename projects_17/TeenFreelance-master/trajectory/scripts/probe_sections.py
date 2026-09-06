"""
Section-probe: what is actually visible in the viewport at the concept
section anchor positions (diagnosis / skill-score / open-questions) and
in the review view. Explains text-less screenshot captures.

Run on whimco:  python3 scripts/probe_sections.py
"""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8022"

VISIBLE = """
() => {
  const sy = Math.round(window.scrollY);
  const picks = {};
  for (const [name, x, y] of [["center", 720, 400], ["at200", 720, 200], ["at120", 720, 120]]) {
    const el = document.elementFromPoint(x, y);
    picks[name] = el
      ? el.tagName + "." + ((el.className || "") + "").slice(0, 30) + " :: " + (el.textContent || "").trim().slice(0, 50)
      : null;
  }
  return { scrollY: sy, docH: document.documentElement.scrollHeight, ...picks };
}
"""

with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(viewport={"width": 1440, "height": 900})
    p.goto(BASE + "/", wait_until="networkidle")
    p.wait_for_timeout(1000)
    p.evaluate("document.documentElement.style.scrollBehavior = 'auto'")

    for sid in ("concept-diagnosis", "skill-score", "open-questions"):
        p.evaluate(
            "document.querySelector('#" + sid + "')?.scrollIntoView({ behavior: 'instant', block: 'start' })"
        )
        p.wait_for_timeout(400)
        print(sid, p.evaluate(VISIBLE))

    # diagnosis section content sanity
    stats = p.evaluate(
        """() => {
        const el = document.querySelector('#concept-diagnosis');
        if (!el) return { found: false };
        const r = el.getBoundingClientRect();
        return {
          found: true,
          htmlLen: el.innerHTML.length,
          cards: el.querySelectorAll('.diag-card').length,
          textLen: (el.textContent || '').trim().length,
          absY: Math.round(r.top + window.scrollY),
          h: Math.round(r.height),
        };
    }"""
    )
    print("diagnosis-section:", stats)

    # review view content
    p.evaluate("window.location.hash = 'review'")
    p.wait_for_timeout(800)
    rv = p.evaluate(
        """() => {
        const main = document.querySelector('main');
        return {
          textLen: main ? (main.textContent || '').trim().length : -1,
          queueCards: document.querySelectorAll('aside button.card').length,
          firstText: main ? (main.textContent || '').trim().slice(0, 80) : null,
        };
    }"""
    )
    print("review-view:", rv)

    b.close()
