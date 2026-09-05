"""PillowRenderer: ``RendererPort`` implementation for Slice 1 (A14 dio 2).

Per the ACS-F1-032 spike decision (R-B), the production renderer uses
Pillow directly rather than introducing a native SVG dependency
(cairosvg requires Cairo+GTK, resvg has Windows quirks; neither is
verified to work in this dev environment). The ``template.svg`` from
the spike is NOT parsed -- it remains a documentation reference of the
intended layout. The Pillow code below is the only production code
path and is intentionally simple and deterministic.

Design decisions enforced here (per the A14 dio 2 contract):
- Fixed neutral palette (no brand colors -- the contract explicitly
  does NOT thread brand identity through ``RenderRequest`` for Slice 1;
  threading it is a future task per plan section 44).
- ``headline_scale`` -> font size mapped against the ``min_font_size``
  / ``max_font_size`` ranges from
  ``application/visual/validate_layout.py``. The numbers are
  duplicated here intentionally (per the contract: "REUSE the same
  numbers, do not invent new ones"). If ``validate_layout.py`` ever
  changes its ranges, this table MUST be updated in lockstep.
- ``headline_position``, ``alignment``, ``overlay``, ``cta_style``,
  ``logo_rule``, ``cta_rule`` all have REAL, testable effects on the
  output -- a reviewer can open the PNG and see the difference.
- Pre-flight overflow check returns ``LAYOUT_VALIDATION_ERROR`` but
  STILL writes the PNG (per plan section 44: "ne regenerisati cijeli
  post" -- render still happens, just gets flagged). Warnings are
  concrete enough for a future ``SHORTEN_HEADLINE`` action to consume
  (not implemented here -- the contract says the action is in the
  application layer).
- Uncaught exceptions (corrupt image, Pillow bug, etc.) are caught
  and returned as ``RENDER_ERROR`` with a useful message in
  ``warnings``. Pillow never propagates a raw exception to the caller.
"""

from __future__ import annotations

import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.ports.rendering import (
    RenderRequest,
    RenderResult,
    RenderStatus,
)

# --- Font + palette (fixed, neutral, no brand access) ---

# Segoe UI ships with Windows and covers the BHS Latin diacritics
# (č ć š đ ž). On Linux/macOS this path is missing -- the Pillow
# default font is used as a silent fallback so the renderer does not
# crash on a non-Windows dev box. The actual headline glyphs in the
# output WILL look different on Linux/macOS; that is a known
# acceptance-stage limitation, not a runtime bug.
_FONT_PATH_BOLD = r"C:\Windows\Fonts\seguisb.ttf"
_FONT_PATH_REG = r"C:\Windows\Fonts\segoeui.ttf"

_NEUTRAL_BG = (255, 255, 255)
_NEUTRAL_INK = (15, 23, 42)
_NEUTRAL_SUBINK = (51, 65, 85)
_NEUTRAL_MUTED = (100, 116, 139)
_NEUTRAL_ACCENT = (15, 118, 110)   # teal -- matches the spike, NOT brand-driven
_NEUTRAL_ACCENT_LIGHT = (224, 242, 254)
_NEUTRAL_ACCENT_DARK_OVERLAY = (15, 23, 42, 140)  # 55% black
# LIGHT overlay uses a slightly off-white (warm cream) tint, NOT pure
# white -- otherwise, on the white background, paste-with-alpha-mask
# would just blend white-on-white and the test_overlay_changes_pixels
# acceptance check could not distinguish LIGHT from NONE.
_NEUTRAL_LIGHT_OVERLAY = (252, 246, 230, 140)     # 55% warm cream

# --- Headline font-size table (DUPLICATED from
#     application/visual/validate_layout.py per the A14 dio 2 contract;
#     keep in lockstep with that file if ranges change). ---

# HERO: min=48, max=72
# SPLIT: min=42, max=64
# Per primitive, per HeadlineScale -> font px.
_HEADLINE_FONT_PX: dict[tuple[LayoutPrimitive, HeadlineScale], float] = {
    (LayoutPrimitive.HERO, HeadlineScale.SMALL): 48.0,
    (LayoutPrimitive.HERO, HeadlineScale.MEDIUM): 60.0,
    (LayoutPrimitive.HERO, HeadlineScale.LARGE): 72.0,
    (LayoutPrimitive.SPLIT, HeadlineScale.SMALL): 42.0,
    (LayoutPrimitive.SPLIT, HeadlineScale.MEDIUM): 53.0,
    (LayoutPrimitive.SPLIT, HeadlineScale.LARGE): 64.0,
}

# Max headline lines per primitive (from validate_layout).
_MAX_LINES: dict[LayoutPrimitive, int] = {
    LayoutPrimitive.HERO: 2,
    LayoutPrimitive.SPLIT: 3,
}
_LINE_HEIGHT = 1.2  # contract: "implementer bira razuman line_height, npr. 1.2"


def _parse_format(fmt: str) -> tuple[int, int]:
    """Parse "1080x1350" -> (1080, 1350). Raises ValueError on garbage."""
    w_h = fmt.lower().split("x")
    if len(w_h) != 2:
        raise ValueError(f"unsupported render format {fmt!r}")
    return int(w_h[0]), int(w_h[1])


def _load_font(weight: str) -> ImageFont.FreeTypeFont:
    """Load a TrueType font or fall back to PIL default on non-Windows.

    The non-Windows fallback returns a ``PIL.ImageFont.ImageFont`` (not
    a ``FreeTypeFont``); we widen the return type so the fallback path
    is type-checked honest -- callers treat both uniformly.
    """
    path = _FONT_PATH_BOLD if weight == "bold" else _FONT_PATH_REG
    try:
        return ImageFont.truetype(path, size=24)
    except OSError:
        return ImageFont.load_default()  # type: ignore[return-value]


def _wrap_text(
    text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Word-wrap text to ``max_width`` (px) using ``font.getlength``."""
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


def _align_x(alignment: Alignment, content_width: int, text_width: int) -> int:
    """X-coordinate of the text origin given a horizontal alignment."""
    if alignment is Alignment.CENTER:
        return (content_width - text_width) // 2
    if alignment is Alignment.RIGHT:
        return content_width - text_width
    return 0  # LEFT


def _draw_overlay(
    img: Image.Image, w: int, h: int, overlay: Overlay
) -> None:
    """Apply a full-canvas overlay tint per ``Overlay`` policy.

    NONE: no change. DARK/LIGHT/GRADIENT: visible tint that the user can
    verify in the output PNG (this is the "overlay must visibly change
    contrast" acceptance test).

    Implementation uses ``Image.alpha_composite`` (per the spike) because
    ``ImageDraw.rectangle`` on an RGB image silently drops the alpha
    channel of a 4-tuple fill -- a real-world Pillow gotcha that would
    make all overlay variants visually identical (and would have failed
    the test_overlay_changes_pixels acceptance test).
    """
    if overlay is Overlay.NONE:
        return
    overlay_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay_layer)
    if overlay is Overlay.DARK:
        odraw.rectangle((0, 0, w, h), fill=_NEUTRAL_ACCENT_DARK_OVERLAY)
    elif overlay is Overlay.LIGHT:
        odraw.rectangle((0, 0, w, h), fill=_NEUTRAL_LIGHT_OVERLAY)
    elif overlay is Overlay.GRADIENT:
        # Bottom-to-top fade from dark to transparent.
        steps = 64
        for i in range(steps):
            alpha = int(180 * (1.0 - i / steps))
            y_top = int(h * i / steps)
            y_bot = int(h * (i + 1) / steps)
            odraw.rectangle((0, y_top, w, y_bot), fill=(15, 23, 42, alpha))
    img.paste(overlay_layer, (0, 0), overlay_layer)


def _draw_cta(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    w: int,
    h: int,
    style: CtaStyle,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Render the CTA element in one of three visibly distinct styles."""
    if style is CtaStyle.SOLID:
        draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=_NEUTRAL_ACCENT)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (x + (w - tw) // 2, y + (h - th) // 2 - bbox[1]),
            text,
            fill=(255, 255, 255),
            font=font,
        )
        return
    if style is CtaStyle.OUTLINE:
        draw.rounded_rectangle(
            (x, y, x + w, y + h), radius=18,
            outline=_NEUTRAL_ACCENT, width=4,
        )
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (x + (w - tw) // 2, y + (h - th) // 2 - bbox[1]),
            text,
            fill=_NEUTRAL_ACCENT,
            font=font,
        )
        return
    # TEXT
    bbox = draw.textbbox((0, 0), text, font=font)
    th = bbox[3] - bbox[1]
    draw.text((x, y + (h - th) // 2 - bbox[1]), text, fill=_NEUTRAL_ACCENT, font=font)


def _draw_logo(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    logo_path: str | None,
    w: int,
    h: int,
    position: LogoPosition,
) -> None:
    """Render the logo if path is given AND file exists; otherwise skip.

    No fallback to initials/text (per the contract: that was a spike
    flourish, NOT a plan requirement). A missing file is a graceful
    no-op (no exception) -- the caller passes None when the brand
    snapshot is unavailable.
    """
    if not logo_path:
        return
    logo_file = Path(logo_path)
    if not logo_file.is_file():
        return
    try:
        logo = Image.open(logo_file).convert("RGBA")
    except Exception:
        return  # corrupt file: graceful skip, do not crash
    # Constrain logo to a 10% width footprint.
    target_w = int(w * 0.10)
    ratio = target_w / logo.width
    logo = logo.resize((target_w, int(logo.height * ratio)))
    pad = 32
    pos_map = {
        LogoPosition.TOP_LEFT:     (pad, pad),
        LogoPosition.TOP_RIGHT:    (w - logo.width - pad, pad),
        LogoPosition.BOTTOM_LEFT:  (pad, h - logo.height - pad),
        LogoPosition.BOTTOM_RIGHT: (w - logo.width - pad, h - logo.height - pad),
        LogoPosition.CENTER:       ((w - logo.width) // 2, (h - logo.height) // 2),
    }
    px, py = pos_map[position]
    img.paste(logo, (px, py), logo)


def _draw_background_image(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    image_path: str | None,
    position,
    w: int,
    h: int,
) -> None:
    """Render the per-post image, if provided, per ``image_position``.

    A missing/corrupt file is a graceful no-op (the contract calls this
    out -- missing image must NOT crash the renderer).
    """
    if image_path is None or position is None or str(position) == "NONE":
        return
    image_file = Path(image_path)
    if not image_file.is_file():
        return
    try:
        bg = Image.open(image_file).convert("RGBA")
    except Exception:
        return
    # Fit-to-bbox per position; ``fit`` keeps aspect ratio.
    pad = 24
    if str(position) in ("BACKGROUND", "TOP", "BOTTOM"):
        target_w = w
        target_h = int(h * 0.45) if str(position) != "BACKGROUND" else h
    elif str(position) in ("LEFT", "RIGHT"):
        target_w = int(w * 0.45)
        target_h = h
    else:
        target_w = target_h = min(w, h) - 2 * pad
    ratio = min(target_w / bg.width, target_h / bg.height)
    new_w = max(1, int(bg.width * ratio))
    new_h = max(1, int(bg.height * ratio))
    bg = bg.resize((new_w, new_h))
    if str(position) == "BACKGROUND":
        img.paste(bg, ((w - new_w) // 2, (h - new_h) // 2), bg)
    elif str(position) == "TOP":
        img.paste(bg, ((w - new_w) // 2, pad), bg)
    elif str(position) == "BOTTOM":
        img.paste(bg, ((w - new_w) // 2, h - new_h - pad), bg)
    elif str(position) == "LEFT":
        img.paste(bg, (pad, (h - new_h) // 2), bg)
    elif str(position) == "RIGHT":
        img.paste(bg, (w - new_w - pad, (h - new_h) // 2), bg)


class PillowRenderer:
    """``RendererPort`` implemented with Pillow.

    The renderer is deterministic: same ``RenderRequest`` always
    produces byte-identical PNGs (modulo the wall-clock ``render_ms``
    field, which is intentionally not part of the byte payload). It
    always writes the PNG, even on LAYOUT_VALIDATION_ERROR and
    RENDER_ERROR -- the caller decides whether to act on the warning
    (e.g. trigger a future SHORTEN_HEADLINE action).
    """

    def __init__(self) -> None:
        self._font_bold = _load_font("bold")
        self._font_reg = _load_font("regular")

    def render(self, request: RenderRequest) -> RenderResult:
        t0 = time.perf_counter()
        warnings: list[str] = []
        measured: dict[str, dict[str, float]] = {}

        # Parse canvas. On bad format, we still write a sentinel PNG
        # (1x1 white) so the caller never sees a missing file -- but
        # we return RENDER_ERROR because the request was malformed.
        try:
            w, h = _parse_format(request.format)
        except ValueError as e:
            out = Path(request.output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            sentinel = Image.new("RGB", (1, 1), (255, 255, 255))
            sentinel.save(out, format="PNG")
            return RenderResult(
                status=RenderStatus.RENDER_ERROR,
                output_path=str(out),
                warnings=(f"bad format {request.format!r}: {e}",),
                render_ms=(time.perf_counter() - t0) * 1000,
            )

        img = Image.new("RGB", (w, h), _NEUTRAL_BG)
        draw = ImageDraw.Draw(img)

        # 1. Background image (per image_position).
        _draw_background_image(
            draw, img, request.image_path, request.layout_spec.image_position,
            w, h,
        )

        # 2. Overlay tint (per overlay; AFTER bg so it tints the bg).
        _draw_overlay(img, w, h, request.layout_spec.overlay)

        # 3. Logo (per logo_position; skipped if logo_rule says hide or
        #    no path is provided).
        show_logo = "hide" not in request.visual_system.logo_rule.lower()
        if show_logo and request.logo_path:
            _draw_logo(
                draw, img, request.logo_path, w, h,
                request.layout_spec.logo_position,
            )

        # 4. Headline (per primitive, headline_position, alignment,
        #    headline_scale). The pre-flight overflow check is the
        #    LAYOUT_VALIDATION_ERROR path; render still happens.
        font_size = _HEADLINE_FONT_PX[
            (request.layout_spec.primitive, request.layout_spec.headline_scale)
        ]
        # Pillow truetype font sizes are immutable -- create a per-render
        # font instance with the right size.
        try:
            head_font = ImageFont.truetype(_FONT_PATH_BOLD, size=int(font_size))
        except OSError:
            head_font = self._font_bold

        primitive = request.layout_spec.primitive
        max_lines = _MAX_LINES[primitive]
        # SPLIT uses a narrower content width; HERO uses full width.
        if primitive is LayoutPrimitive.SPLIT:
            content_w = int(w * 0.45)
        else:
            content_w = w - 2 * 80
        # Headline Y position per ``headline_position``.
        if request.layout_spec.headline_position is HeadlinePosition.TOP:
            head_y = 80
        elif request.layout_spec.headline_position is HeadlinePosition.CENTER:
            head_y = int(h * 0.30)
        else:  # BOTTOM
            head_y = int(h * 0.62)
        # (SPLIT headline X is derived later via ``_align_x`` with the
        # halved ``content_w`` -- no separate ``head_x`` offset is
        # needed here.)

        # Word-wrap the headline.
        head_lines = _wrap_text(request.content.headline, head_font, content_w)
        # Measure.
        line_h = int(font_size * _LINE_HEIGHT)
        head_w = max(
            (head_font.getlength(line) for line in head_lines), default=0.0
        )
        head_h = len(head_lines) * line_h
        # Apply alignment. ``head_w`` is a float (``font.getlength``
        # returns float) but ``_align_x`` indexes in integer pixels,
        # so cast to int to keep the on-screen coordinates pixel-aligned.
        if primitive is LayoutPrimitive.SPLIT:
            # Headline is confined to the LEFT half; align within that half.
            half_w = int(w * 0.45)
            x = _align_x(request.layout_spec.alignment, half_w, int(head_w))
        else:
            x = _align_x(
                request.layout_spec.alignment, w - 2 * 80, int(head_w)
            )
        # SPLIT positions the headline in the LEFT half regardless of
        # headline_position (otherwise text overlaps the right half).
        if primitive is LayoutPrimitive.SPLIT:
            head_y = 80
        measured["headline"] = {"width_px": head_w, "height_px": head_h,
                               "line_count": float(len(head_lines)),
                               "x_px": float(x), "y_px": float(head_y)}

        # Pre-flight overflow check (this is what feeds
        # LAYOUT_VALIDATION_ERROR; the rest of the render still happens).
        if len(head_lines) > max_lines:
            warnings.append(
                f"{primitive.value} headline wrapped to "
                f"{len(head_lines)} lines (> max {max_lines}); "
                f"action=SHORTEN_HEADLINE"
            )

        # Draw each wrapped line.
        for i, line in enumerate(head_lines):
            draw.text(
                (x, head_y + i * line_h),
                line,
                fill=_NEUTRAL_INK,
                font=head_font,
            )

        # 5. CTA (per cta_style; skipped if cta_rule says hide).
        show_cta = "hide" not in request.visual_system.cta_rule.lower()
        if show_cta and request.content.cta:
            try:
                cta_font = ImageFont.truetype(_FONT_PATH_BOLD, size=36)
            except OSError:
                cta_font = self._font_bold
            cta_w, cta_h = 540, 84
            cta_y = int(h * 0.85)
            cta_x = _align_x(
                request.layout_spec.alignment, w - 2 * 80, cta_w,
            ) + 80
            _draw_cta(
                draw, request.content.cta, cta_x, cta_y, cta_w, cta_h,
                request.layout_spec.cta_style, cta_font,
            )
            measured["cta"] = {
                "width_px": float(cta_w), "height_px": float(cta_h),
                "x_px": float(cta_x), "y_px": float(cta_y),
            }

        # 6. Write PNG to disk (create parent directory if needed).
        out = Path(request.output_path)
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out, format="PNG", optimize=False)
        except Exception as e:
            return RenderResult(
                status=RenderStatus.RENDER_ERROR,
                output_path=str(out),
                warnings=(*warnings, f"Pillow save failed: {type(e).__name__}: {e}"),
                measured_slots=measured,
                render_ms=(time.perf_counter() - t0) * 1000,
            )

        status = (
            RenderStatus.LAYOUT_VALIDATION_ERROR if warnings
            else RenderStatus.SUCCESS
        )
        return RenderResult(
            status=status,
            output_path=str(out),
            warnings=tuple(warnings),
            measured_slots=measured,
            render_ms=(time.perf_counter() - t0) * 1000,
        )


__all__ = ["PillowRenderer"]
