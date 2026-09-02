"""shoot.py -- capture 1440x900 PNGs of all mockup_proposal_v2 screens.

Uses Playwright with the system-installed Microsoft Edge (channel=msedge)
to avoid the ~300MB chromium download.
"""

import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

BASE = pathlib.Path(__file__).resolve().parent
SCREENS = ["brand", "brief", "plan", "pregled", "settings", "studio", "language"]
WIDTH, HEIGHT = 1440, 900


async def main() -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        ctx = await browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = await ctx.new_page()
        ok = 0
        for name in SCREENS:
            html = BASE / name / "index.html"
            png = BASE / name / "screenshot.png"
            if not html.exists():
                print(f"MISSING: {html}")
                continue
            await page.goto(html.resolve().as_uri(), wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(png), full_page=False)
            print(f"OK: {name} -> {png.name} ({png.stat().st_size} bytes)")
            ok += 1
        await browser.close()
        return 0 if ok == len(SCREENS) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
