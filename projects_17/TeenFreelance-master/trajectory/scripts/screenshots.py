"""
Playwright browser pass over the deployed Freeстарт presentation (:8022).

Runs on whimco (python playwright + chromium cache):
    python3 scripts/screenshots.py

Produces: /opt/teenfreelance/frontend/freestart/shots/*.png
Report:   console errors, page errors, failed requests, video autoplay state.
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8022"
OUT = "/opt/teenfreelance/frontend/freestart/shots"
os.makedirs(OUT, exist_ok=True)

report = {"console": [], "pageErrors": [], "requestFailed": [], "video": {}, "shots": []}


def watch(page, label):
    page.on(
        "console",
        lambda msg, l=label: report["console"].append(f"[{l}] {msg.text}")
        if msg.type == "error"
        else None,
    )
    page.on("pageerror", lambda e, l=label: report["pageErrors"].append(f"[{l}] {e}"))
    page.on(
        "requestfailed",
        lambda r, l=label: report["requestFailed"].append(f"[{l}] {r.url} → {r.failure}"),
    )


def shot(page, name):
    page.screenshot(path=f"{OUT}/{name}.png", full_page=False)
    report["shots"].append(name)
    print("shot:", name)


with sync_playwright() as pw:
    # no-user-gesture flag: headless default blocks even muted autoplay,
    # which would report a false negative for the hero video
    browser = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])

    # ---------- DESKTOP ----------
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    watch(page, "desktop")

    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(1200)
    shot(page, "01-desktop-intro-top")

    # video state (autoplay muted loop)
    report["video"] = page.evaluate(
        """() => {
        const v = document.querySelector('video');
        if (!v) return { present: false };
        return {
            present: true,
            paused: v.paused,
            muted: v.muted,
            readyState: v.readyState,
            duration: v.duration,
            poster: v.poster !== '',
            currentTime: v.currentTime,
        };
    }"""
    )

    # let the video advance, then prove motion by comparing currentTime
    page.wait_for_timeout(1500)
    report["video_second_read"] = page.evaluate(
        "() => { const v = document.querySelector('video'); return v ? { paused: v.paused, currentTime: v.currentTime } : null; }"
    )

    page.evaluate("document.querySelector('#concept-diagnosis')?.scrollIntoView()")
    page.wait_for_timeout(600)
    shot(page, "02-desktop-diagnosis")

    page.evaluate("document.querySelector('#skill-score')?.scrollIntoView()")
    page.wait_for_timeout(400)
    shot(page, "03-desktop-skill-score")

    page.evaluate("document.querySelector('#open-questions')?.scrollIntoView()")
    page.wait_for_timeout(400)
    shot(page, "04-desktop-open-questions")

    page.evaluate("window.location.hash = 'dashboard'")
    page.wait_for_timeout(900)
    shot(page, "05-desktop-dashboard")

    # ---------- MOBILE ----------
    mob = browser.new_page(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2
    )
    watch(mob, "mobile")

    mob.goto(BASE + "/", wait_until="networkidle")
    mob.wait_for_timeout(1200)
    shot(mob, "06-mobile-intro")

    mob.evaluate("window.location.hash = 'dashboard'")
    mob.wait_for_timeout(900)
    shot(mob, "07-mobile-dashboard")

    browser.close()

print("---REPORT---")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0)
