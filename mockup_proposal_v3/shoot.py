"""shoot_v3.py -- capture v3 Početna dashboard."""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright

BASE = pathlib.Path(__file__).resolve().parent
TARGETS = ["pocetna"]
WIDTH, HEIGHT = 1440, 900

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        ctx = await browser.new_context(viewport={"width": WIDTH, "height": HEIGHT})
        page = await ctx.new_page()
        for name in TARGETS:
            html = BASE / name / "index.html"
            png = BASE / name / "screenshot.png"
            if not html.exists():
                print(f"MISSING: {html}")
                continue
            await page.goto(html.resolve().as_uri(), wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(500)
            await page.screenshot(path=str(png), full_page=False)
            print(f"OK: {name} ({png.stat().st_size} bytes)")
        await browser.close()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
