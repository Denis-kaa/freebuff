"""
Dashboard → Skill Graph link probe (followup: link-card on the dashboard).

Checks on the live :8022:
  1. The skills-card button («Граф навыков: …») exists on #dashboard.
  2. Clicking it lands on #skills with the graph view rendered.
  3. The teaser card explains effective-vs-stored (anti-gamification note).

Run on whimco:  python3 scripts/probe_dashboard_link.py
Exit 0 = all green.
"""
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8022"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        page.goto(f"{BASE}/#dashboard", wait_until="networkidle")
        page.wait_for_timeout(600)

        sidebar_btn = page.locator(".skill-graph-link")
        if sidebar_btn.count() != 1:
            print(f"FAIL sidebar button count = {sidebar_btn.count()}")
            return 1
        btn_text = sidebar_btn.inner_text()
        if "Граф навыков" not in btn_text:
            print(f"FAIL sidebar button text: {btn_text!r}")
            return 1

        teaser = page.locator(".skill-graph-teaser")
        if teaser.count() != 1:
            print(f"FAIL teaser card count = {teaser.count()}")
            return 1
        if "эффективный" not in teaser.inner_text():
            print("FAIL teaser does not explain effective-vs-stored")
            return 1

        sidebar_btn.click()
        page.wait_for_timeout(500)
        if page.url.split("#")[-1] != "skills":
            print(f"FAIL navigation landed on {page.url}")
            return 1
        if not page.locator("svg").count():
            print("FAIL no SVG graph on #skills")
            return 1
        if "Граф навыков" not in page.locator("main").inner_text():
            print("FAIL #skills heading missing")
            return 1

        browser.close()
        if errors:
            print(f"FAIL console/page errors: {errors[:3]}")
            return 1
        print(f"PASS sidebar '{btn_text.strip()}' → #skills renders graph, teaser present, 0 console errors")
        return 0


if __name__ == "__main__":
    sys.exit(main())
