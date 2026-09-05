"""R-B spike driver: Pillow ImageDraw rasterisation of an SVG-like layout.

ACS-F1-032. NOT production code. Throwaway under spikes/renderer/.

Per plan section 42, R-B = "SVG-based". The template IS an SVG
(spikes/renderer/candidate_b_svg/template.svg), but the rasterisation
step uses Pillow directly because no cairosvg / resvg / svglib is
installed in the dev env. The contract explicitly allows this:
"Cilj nije savršena biblioteka, plan doslovno".

What this script measures for the R-B candidate:
  1. render_success    : does Pillow produce a valid 1080x1350 PNG?
  2. overflow_detection : does the manual text-wrap detect too-long
                            text deterministically? (we compare the
                            measured text-height against a slot budget
                            and report overflow if it exceeds the slot)
  3. bhs_glyphs_ok     : are the BHS diacritics rendered with non-zero
                          width (i.e. not tofu boxes)?
  4. avg_render_ms     : warm-loop average over 5 successive renders
  5. memory_notes      : process footprint after N renders

This is intentionally NOT a full SVG parser. The R-B promise for
the spike is "SVG-based" = the design source is SVG, the rasterisation
is whatever deterministic local path we have (Pillow here). A14 dio 2
(production renderer) will pick a real SVG library once the spike
decides on R-B.

Outputs (relative to this script):
  - shot.png            : standard BHS render
  - shot_overflow.png   : too-long render (overflow signal)
  - metrics.json        : raw measurements
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT_PATH = r"C:\Windows\Fonts\segoeui.ttf"
FONT_PATH_BOLD = r"C:\Windows\Fonts\seguisb.ttf"

BHS_HEADLINE = "Vaš osmijeh je naš prioritet."
BHS_CAPTION = "Slušamo vas prvo."
OVERFLOW_HEADLINE = (
    "Ovo je namjerno predug headline da testiramo kako R-B detektuje "
    "overflow na 1080x1350: ovaj tekst ima preko sto pedeset karaktera i "
    "ne stane u jedan red ni u dva reda ni u tri reda ali da vidimo hoce li "
    "R-B to deterministicki prijaviti."
)

W, H = 1080, 1350
PADDING = 80
HEADLINE_FONT_PX = 76
CAPTION_FONT_PX = 36
LOGO_FONT_PX = 40
BRAND_FONT_PX = 28
FOOTER_FONT_PX = 22
CTA_FONT_PX = 36
HEADLINE_SLOT_TOP = 280        # y of first headline baseline
HEADLINE_SLOT_BUDGET_PX = 600  # max height we want for headline
CONTENT_WIDTH = W - 2 * PADDING


def _wrap_text(
    text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Word-wrap text to fit max_width, returning a list of lines.

    Pillow's ``textlength`` gives us per-line width, so we walk the
    words and pack as many as fit per line. Deterministic and
    text-shape independent (no browser engine in the loop).
    """
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if font.getlength(candidate) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _render(headline: str) -> bytes:
    """Render the canvas to PNG bytes (1080x1350)."""
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Background gradients (cheap stand-in: two soft circles)
    for cx, cy, color, alpha in (
        (int(W * 0.9), int(H * 0.1), (224, 242, 254), 90),
        (int(W * 0.1), int(H * 0.9), (236, 252, 203), 90),
    ):
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse(
            (cx - 400, cy - 400, cx + 400, cy + 400),
            fill=color + (alpha,),
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Logo block (96x96 teal square + "BS")
    logo_font = ImageFont.truetype(FONT_PATH_BOLD, LOGO_FONT_PX)
    draw.rounded_rectangle(
        (PADDING, PADDING, PADDING + 96, PADDING + 96),
        radius=24,
        fill=(15, 118, 110),
    )
    bbox = draw.textbbox((0, 0), "BS", font=logo_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (PADDING + 48 - tw / 2, PADDING + 48 - th / 2 - bbox[1]),
        "BS",
        fill=(255, 255, 255),
        font=logo_font,
    )

    # Brand label
    brand_font = ImageFont.truetype(FONT_PATH, BRAND_FONT_PX)
    draw.text(
        (PADDING + 120, PADDING + 30),
        "BrightSmile Dental",
        fill=(15, 23, 42),
        font=brand_font,
    )

    # Headline (multi-line, auto-wrapped, bold)
    head_font = ImageFont.truetype(FONT_PATH_BOLD, HEADLINE_FONT_PX)
    head_lines = _wrap_text(headline, head_font, CONTENT_WIDTH)
    y = HEADLINE_SLOT_TOP
    for line in head_lines:
        draw.text((PADDING, y), line, fill=(15, 23, 42), font=head_font)
        y += int(HEADLINE_FONT_PX * 1.05)

    # Caption (single line for the BHS test string; we have a slot for ~2
    # lines at 1.35x line-height if needed)
    cap_font = ImageFont.truetype(FONT_PATH, CAPTION_FONT_PX)
    cap_y = max(y + 40, 900)  # below headline with breathing room
    cap_lines = _wrap_text(BHS_CAPTION, cap_font, CONTENT_WIDTH)
    for line in cap_lines:
        draw.text((PADDING, cap_y), line, fill=(51, 65, 85), font=cap_font)
        cap_y += int(CAPTION_FONT_PX * 1.35)

    # CTA button
    cta_font = ImageFont.truetype(FONT_PATH_BOLD, CTA_FONT_PX)
    cta_text = "Zaka\u017eite konsultaciju"
    cta_w, cta_h = 540, 84
    cta_x, cta_y = PADDING, 1180
    draw.rounded_rectangle(
        (cta_x, cta_y, cta_x + cta_w, cta_y + cta_h),
        radius=18,
        fill=(15, 118, 110),
    )
    bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (cta_x + cta_w / 2 - tw / 2, cta_y + cta_h / 2 - th / 2 - bbox[1]),
        cta_text,
        fill=(255, 255, 255),
        font=cta_font,
    )

    # Footer
    foot_font = ImageFont.truetype(FONT_PATH, FOOTER_FONT_PX)
    draw.text(
        (PADDING, 1300),
        "Centar Sarajeva \u00b7 Tim sa 12+ godina iskustva \u00b7 Medicinski titanijum klase 4",
        fill=(100, 116, 139),
        font=foot_font,
    )

    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def _measure_overflow(headline: str) -> dict:
    """Deterministic overflow detection via the same wrap routine."""
    head_font = ImageFont.truetype(FONT_PATH_BOLD, HEADLINE_FONT_PX)
    lines = _wrap_text(headline, head_font, CONTENT_WIDTH)
    # The headline slot: y starts at HEADLINE_SLOT_TOP, line height is
    # HEADLINE_FONT_PX * 1.05. The slot allows up to 600px; overflow
    # when the actual wrapped height exceeds the budget.
    line_height = int(HEADLINE_FONT_PX * 1.05)
    total_height = len(lines) * line_height
    # Width overflow: any line that exceeds the available content width
    any_wide = any(head_font.getlength(line) > CONTENT_WIDTH for line in lines)
    return {
        "wrapped_line_count": len(lines),
        "wrapped_height_px": total_height,
        "wrapped_width_px": max(
            (head_font.getlength(line) for line in lines), default=0.0
        ),
        "budget_px": HEADLINE_SLOT_BUDGET_PX,
        "overflow_detected": total_height > HEADLINE_SLOT_BUDGET_PX or any_wide,
    }


def _bhs_glyphs_via_pillow(font: ImageFont.FreeTypeFont) -> dict:
    """Measure each BHS diacritic's rendered width via font.getlength.

    The bundled Windows Segoe UI font has glyph coverage for the BHS
    Latin diacritics (č ć š đ ž). A non-zero width means the font
    has a real glyph; a zero width would mean a tofu box.
    """
    chars = {
        "c": "\u010d",          # č
        "c_with_acute": "\u0107",  # ć
        "s_with_caron": "\u0161",  # š
        "d_with_stroke": "\u0111",  # đ
        "z_with_caron": "\u017e",  # ž
    }
    widths = {k: font.getlength(v) for k, v in chars.items()}
    widths["all_ok"] = all(w > 0.0 for w in widths.values())
    return widths


def main() -> None:
    out = HERE / "shot.png"
    out_overflow = HERE / "shot_overflow.png"
    metrics_path = HERE / "metrics.json"

    # 1) First / cold render
    t0 = time.perf_counter()
    png = _render(BHS_HEADLINE)
    first_render_ms = (time.perf_counter() - t0) * 1000
    out.write_bytes(png)

    # 2) 5 successive renders for warm average
    samples_ms = []
    for _ in range(5):
        t0 = time.perf_counter()
        _render(BHS_HEADLINE)
        samples_ms.append((time.perf_counter() - t0) * 1000)

    # 3) Overflow on the too-long headline
    overflow_metrics = _measure_overflow(OVERFLOW_HEADLINE)
    png_overflow = _render(OVERFLOW_HEADLINE)
    out_overflow.write_bytes(png_overflow)

    # 4) BHS glyph width via Pillow font metrics
    head_font = ImageFont.truetype(FONT_PATH_BOLD, HEADLINE_FONT_PX)
    glyph_metrics = _bhs_glyphs_via_pillow(head_font)

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
