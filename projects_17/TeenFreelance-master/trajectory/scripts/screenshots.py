"""
Playwright browser pass over the deployed Freeстарт presentation (:8022).

Runs on whimco (python playwright + chromium cache):
    python3 scripts/screenshots.py                    # human output
    python3 scripts/screenshots.py --report PATH      # JSON report to file (for cron)
    python3 scripts/screenshots.py --strict           # exit 1 on console/page errors,
                                                      # failed requests, or video not advancing

Produces: /opt/teenfreelance/frontend/freestart/shots/*.png
Report:   console errors, page errors, failed requests, video autoplay state.
"""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8022"
OUT = "/opt/teenfreelance/frontend/freestart/shots"
os.makedirs(OUT, exist_ok=True)

_parser = argparse.ArgumentParser(description="Playwright browser pass over :8022")
_parser.add_argument("--report", metavar="PATH", help="write the JSON report to PATH")
_parser.add_argument("--strict", action="store_true", help="exit 1 on errors / video not advancing")
ARGS = _parser.parse_args()

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

    # smooth-scroll CSS makes scrollIntoView animate; shots caught mid-scroll.
    # Force instant scrolling for deterministic captures.
    page.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
    page.evaluate("document.querySelector('#concept-diagnosis')?.scrollIntoView({ behavior: 'instant', block: 'start' })")
    page.wait_for_timeout(600)
    shot(page, "02-desktop-diagnosis")

    page.evaluate("document.querySelector('#skill-score')?.scrollIntoView({ behavior: 'instant', block: 'start' })")
    page.wait_for_timeout(500)
    shot(page, "03-desktop-skill-score")

    page.evaluate("document.querySelector('#open-questions')?.scrollIntoView({ behavior: 'instant', block: 'start' })")
    page.wait_for_timeout(500)
    shot(page, "04-desktop-open-questions")

    page.evaluate("window.location.hash = 'dashboard'")
    page.wait_for_timeout(900)
    shot(page, "05-desktop-dashboard")

    # two-pane demo views (fixed to collapse on mobile — show desktop form)
    page.evaluate("window.location.hash = 'team'")
    page.wait_for_timeout(900)
    shot(page, "08-desktop-team")

    page.evaluate("window.location.hash = 'review'")
    page.wait_for_timeout(900)
    shot(page, "09-desktop-review")

    # Skill Graph (Этап 3.1)
    page.evaluate("window.location.hash = 'skills'")
    page.wait_for_timeout(900)
    shot(page, "12-desktop-skills")

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

    # the two views that had the pane-crush bug (single column now)
    mob.evaluate("window.location.hash = 'team'")
    mob.wait_for_timeout(900)
    shot(mob, "10-mobile-team")

    mob.evaluate("window.location.hash = 'review'")
    mob.wait_for_timeout(900)
    shot(mob, "11-mobile-review")

    browser.close()

if ARGS.report:
    with open(ARGS.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

print("---REPORT---")
print(json.dumps(report, ensure_ascii=False, indent=2))

if ARGS.strict:
    problems = []
    if report["console"]:
        problems.append(f"console errors: {report['console']}")
    if report["pageErrors"]:
        problems.append(f"page errors: {report['pageErrors']}")
    if report["requestFailed"]:
        problems.append(f"failed requests: {report['requestFailed']}")
    v1, v2 = report.get("video", {}), report.get("video_second_read") or {}
    if not v1.get("present"):
        problems.append("video missing")
    elif v1.get("paused") or (v2 or {}).get("paused"):
        problems.append("video paused (autoplay blocked?)")
    elif v2.get("currentTime", 0) <= v1.get("currentTime", 0):
        problems.append(f"video not advancing: {v1.get('currentTime')} → {v2.get('currentTime')}")
    if len(report["shots"]) < 12:
        problems.append(f"expected 12 shots, got {len(report['shots'])}")
    if problems:
        print("---STRICT: FAIL---")
        for p in problems:
            print("  *", p)
        sys.exit(1)
    print("---STRICT: PASS---")

sys.exit(0)
