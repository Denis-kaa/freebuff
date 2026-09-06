"""
Layout/UX audit of the deployed Freeстарт prototype (:8022).

Clicks through every view at desktop + mobile widths and measures real
defects: horizontal overflow, broken images, anchor landing under the
sticky header, nav interactions. Output: JSON report to stdout.

Run on whimco:  python3 scripts/layout_audit.py
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8022"
VIEWS = ["intro", "dashboard", "team", "review", "parent"]

report = {"console": [], "pageErrors": [], "views": {}, "interactions": {}, "anchor": {}}


def watch(page, label):
    page.on(
        "console",
        lambda msg, l=label: report["console"].append(f"[{l}] {msg.text}")
        if msg.type == "error"
        else None,
    )
    page.on("pageerror", lambda e, l=label: report["pageErrors"].append(f"[{l}] {e}"))


def audit_view(page, view):
    page.evaluate(f"window.location.hash = '{view}'")
    page.wait_for_timeout(800)
    m = page.evaluate(
        """() => {
        const de = document.documentElement;
        const overflowX = Math.max(0, de.scrollWidth - window.innerWidth);
        // widest offender: any element extending beyond viewport
        let worst = null;
        document.querySelectorAll('body *').forEach((el) => {
            const r = el.getBoundingClientRect();
            if (r.right > window.innerWidth + 1 && r.width > 40) {
                if (!worst || r.right > worst.right) {
                    worst = { tag: el.tagName.toLowerCase(), cls: (el.className || '').toString().slice(0, 60), right: Math.round(r.right), w: Math.round(r.width) };
                }
            }
        });
        const brokenImgs = [...document.images].filter((i) => i.complete && i.naturalWidth === 0).length;
        return { overflowX, worst, brokenImgs };
    }"""
    )
    report["views"][view] = m
    print(f"  {view:10} overflowX={m['overflowX']:>4}px  brokenImgs={m['brokenImgs']}  worst={m['worst']}")


with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    # ---------- DESKTOP ----------
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    watch(page, "desktop")
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(1000)

    print("desktop 1440x900")
    for v in VIEWS:
        audit_view(page, v)

    # interactions: hero CTA + nav links
    page.evaluate("window.location.hash = 'intro'")
    page.wait_for_timeout(500)
    page.get_by_text("Пропустить → демо-дашборд").click()
    page.wait_for_timeout(600)
    report["interactions"]["hero_skip"] = page.evaluate("window.location.hash")
    page.click("nav.header-nav >> text=Драфт")
    page.wait_for_timeout(600)
    report["interactions"]["nav_draft"] = page.evaluate("window.location.hash")

    # anchor: «Читать концепцию» must land below the sticky header
    page.evaluate("window.location.hash = 'intro'")
    page.wait_for_timeout(500)
    page.get_by_text("Читать концепцию").click()
    page.wait_for_timeout(1200)
    report["anchor"] = page.evaluate(
        "() => { const el = document.querySelector('#concept-diagnosis'); if (!el) return {found: false}; const r = el.getBoundingClientRect(); return {found: true, top: Math.round(r.top)}; }"
    )

    # ---------- MOBILE ----------
    mob = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    watch(mob, "mobile")
    mob.goto(BASE + "/", wait_until="networkidle")
    mob.wait_for_timeout(1000)

    print("mobile 390x844")
    for v in VIEWS:
        audit_view(mob, v)

    browser.close()

print("---REPORT---")
print(json.dumps(report, ensure_ascii=False, indent=2))
bad = (
    any(v["overflowX"] > 2 for v in report["views"].values())
    or report["anchor"].get("top", 0) < 0
    or report["anchor"].get("top", 99) > 95
)
sys.exit(1 if bad else 0)
