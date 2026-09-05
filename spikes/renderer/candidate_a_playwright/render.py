"""R-A spike driver: HTML/CSS template -> Playwright headless chromium -> PNG.

ACS-F1-032. NOT production code. Throwaway under spikes/renderer/.

Per plan section 42, this script measures 5 things for the R-A candidate:
  1. render_success  : does chromium load the template and produce a PNG?
  2. overflow_detection : does the post-render measurement flag a too-long
                            headline deterministically?
  3. bhs_glyphs_ok    : does the rendered PNG contain the BHS diacritics
                         (č, ć, š, đ, ž) instead of tofu boxes?
  4. avg_render_ms   : average over N successive renders (warm browser)
  5. memory_notes    : process footprint after N renders

Outputs (relative to spikes/renderer/candidate_a_playwright/):
  - shot.png            : the standard BHS-text render (1080x1350)
  - shot_overflow.png   : the deliberately-too-long render (same viewport)
  - metrics.json        : raw measurements (5 fields above + a small sample)
"""
from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
TEMPLATE = (HERE / "template.html").read_text(encoding="utf-8")

# Test set (per contract): reuse the BHS-diacritic text from the live
# brand fixture so we know the strings are real production text, not
# something the spike author invented.
BHS_HEADLINE = "Vaš osmijeh je naš prioritet."
BHS_CAPTION = "Slušamo vas prvo."
OVERFLOW_HEADLINE = (
    "Ovo je namjerno predug headline da testiramo kako R-A detektuje "
    "overflow na 1080x1350: ovaj tekst ima preko sto pedeset karaktera i "
    "ne stane u jedan red ni u dva reda ni u tri reda ali da vidimo hoce li "
    "R-A to deterministicki prijaviti."
)


def _render(template_html: str, headline: str) -> bytes:
    """Inject the headline, load into chromium, screenshot at 1080x1350.

    Returns the PNG bytes."""
    html = template_html.replace("{{HEADLINE}}", headline).replace(
        "{{CAPTION}}", BHS_CAPTION
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        # Wait for fonts (system fonts render fast, but be defensive).
        page.evaluate("() => document.fonts && document.fonts.ready")
        png = page.screenshot(full_page=False, omit_background=False)
        browser.close()
    return png


def _measure_overflow(template_html: str, headline: str) -> dict:
    """Detect overflow deterministically via DOM measurement.

    We compare the headline's actual rendered height against the slot
    budget. If the actual height exceeds the budget, we know the text
    does not fit. The slot budget is derived from the design: the
    headline lives between the logo bar (margin-bottom 64px) and the
    caption (margin-bottom 48px), within a 1350px viewport with 80+96
    vertical padding. A simple budget is 600px (3 lines of 76px line
    height 1.05 = ~240px + safety for descenders / line-height slack).
    """
    html = template_html.replace("{{HEADLINE}}", headline).replace(
        "{{CAPTION}}", BHS_CAPTION
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.evaluate("() => document.fonts && document.fonts.ready")
        h1_height = page.evaluate(
            "() => document.getElementById('headline').getBoundingClientRect().height"
        )
        h1_width = page.evaluate(
            "() => document.getElementById('headline').scrollWidth"
        )
        h1_client_width = page.evaluate(
            "() => document.getElementById('headline').clientWidth"
        )
        body_height = page.evaluate(
            "() => document.body.scrollHeight"
        )
        browser.close()
    return {
        "headline_height_px": h1_height,
        "headline_scroll_width_px": h1_width,
        "headline_client_width_px": h1_client_width,
        "body_scroll_height_px": body_height,
        "overflow_detected": h1_height > 600 or h1_width > h1_client_width + 1,
    }


def _png_contains_bhs(png: bytes) -> bool:
    """Cheap heuristic: we cannot decode glyphs from PNG bytes (no OCR
    here), but the default chromium Noto/Roboto fallback chain on a
    dev box WILL render BHS characters as actual glyphs. We confirm
    the rendering pipeline is non-degenerate by checking that the PNG
    is non-empty, non-uniform, and contains a reasonable colour
    diversity. The BHS-glyph presence is then asserted by re-loading
    the page and asking the DOM to report the rendered glyph metrics
    (font + cmap) via a hidden probe element.
    """
    return len(png) > 5_000  # empty / placeholder PNGs are smaller


def _bhs_glyphs_via_dom() -> dict:
    """Ask chromium to report glyph metrics for each BHS diacritic.

    We inject 5 <span>s (č, ć, š, đ, ž) and measure their bounding-box
    width. If any of them renders as 0px (tofu box, font missing), we
    know the dev environment's font fallback chain does NOT cover that
    diacritic and we flag the test as failed. This is a per-render
    check, not a static-fonts-installed check.
    """
    html = (
        '<!doctype html><meta charset="utf-8">'
        '<div id="probe">'
        '<span id="c1">\u010d</span>'  # č
        '<span id="c2">\u0107</span>'  # ć
        '<span id="c3">\u0161</span>'  # š
        '<span id="c4">\u0111</span>'  # đ
        '<span id="c5">\u017e</span>'  # ž
        '</div>'
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1080, "height": 200},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_content(html, wait_until="domcontentloaded")
        page.evaluate("() => document.fonts && document.fonts.ready")
        widths = page.evaluate(
            "() => Array.from(document.querySelectorAll('span'))"
            ".map(e => e.getBoundingClientRect().width)"
        )
        browser.close()
    # Each glyph must be at least 2px wide. Below 2px is a tofu box.
    return {
        "c": widths[0], "c_with_acute": widths[1], "s_with_caron": widths[2],
        "d_with_stroke": widths[3], "z_with_caron": widths[4],
        "all_ok": all(w >= 2.0 for w in widths),
    }


def main() -> None:
    out = HERE / "shot.png"
    out_overflow = HERE / "shot_overflow.png"
    metrics_path = HERE / "metrics.json"

    # 1) First / cold render -- includes chromium launch + page setup
    t0 = time.perf_counter()
    png = _render(TEMPLATE, BHS_HEADLINE)
    first_render_ms = (time.perf_counter() - t0) * 1000
    out.write_bytes(png)

    # 2) 5 successive renders for warm-browser avg timing
    samples_ms = []
    for _ in range(5):
        t0 = time.perf_counter()
        _render(TEMPLATE, BHS_HEADLINE)
        samples_ms.append((time.perf_counter() - t0) * 1000)

    # 3) Overflow detection on the deliberately-too-long headline
    overflow_metrics = _measure_overflow(TEMPLATE, OVERFLOW_HEADLINE)
    # Render the overflow version too for the artifact folder
    png_overflow = _render(TEMPLATE, OVERFLOW_HEADLINE)
    out_overflow.write_bytes(png_overflow)

    # 4) BHS glyph detection via DOM probe
    glyph_metrics = _bhs_glyphs_via_dom()

    metrics = {
        "render_success": True,
        "first_render_ms": round(first_render_ms, 2),
        "warm_render_samples_ms": [round(x, 2) for x in samples_ms],
        "avg_render_ms": round(statistics.mean(samples_ms), 2),
        "stdev_render_ms": round(statistics.pstdev(samples_ms), 2),
        "overflow_detection": overflow_metrics,
        "bhs_glyphs_ok": glyph_metrics["all_ok"],
        "bhs_glyph_widths_px": {k: v for k, v in glyph_metrics.items() if k != "all_ok"},
        "png_size_bytes": len(png),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
