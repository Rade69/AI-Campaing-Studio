"""Unit tests for ``PillowRenderer`` (A14 dio 2).

These tests do NOT use fake ports -- ``PillowRenderer`` is pure
I/O (Pillow + filesystem) and is easier to test by constructing a
real ``RenderRequest`` and checking the output PNG. The point is
to verify the BEHAVIOUR contract (HERO and SPLIT visibly different,
overflow detected, alignment / overlay / cta_style have real effect,
logo and image paths gracefully skip when missing / corrupt).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    PostId,
    VisualSystemId,
)
from ai_campaign_studio.domain.content.entities import SocialPostPayload
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.infrastructure.rendering import PillowRenderer
from ai_campaign_studio.infrastructure.rendering.selected_renderer import (
    _NEUTRAL_ACCENT,
    _NEUTRAL_BG,
)
from ai_campaign_studio.ports.rendering import (
    RenderRequest,
    RenderStatus,
)


def _dt() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _make_layout(
    primitive: LayoutPrimitive = LayoutPrimitive.HERO,
    alignment: Alignment = Alignment.LEFT,
    overlay: Overlay = Overlay.NONE,
    cta_style: CtaStyle = CtaStyle.SOLID,
    headline_position: HeadlinePosition = HeadlinePosition.TOP,
    headline_scale: HeadlineScale = HeadlineScale.MEDIUM,
    image_position: ImagePosition = ImagePosition.NONE,
    logo_position: LogoPosition = LogoPosition.TOP_LEFT,
    fmt: str = "200x200",
) -> LayoutSpec:
    return LayoutSpec(
        primitive=primitive,
        image_position=image_position,
        headline_position=headline_position,
        headline_scale=headline_scale,
        overlay=overlay,
        logo_position=logo_position,
        cta_style=cta_style,
        alignment=alignment,
        format=fmt,
    )


def _make_visual_system(
    logo_rule: str = "",
    cta_rule: str = "",
) -> CampaignVisualSystem:
    return CampaignVisualSystem(
        id=VisualSystemId("vs-1"),
        campaign_id=CampaignId("c-1"),
        primary_layout_family=LayoutPrimitive.HERO,
        headline_scale=HeadlineScale.MEDIUM,
        image_treatment="",
        logo_rule=logo_rule,
        cta_rule=cta_rule,
        alignment=Alignment.LEFT,
        created_at=_dt(),
    )


def _make_payload(
    headline: str = "Kratki headline",
    cta: str = "Zakažite konsultaciju",
) -> SocialPostPayload:
    return SocialPostPayload(
        headline=headline,
        caption="Caption",
        hook="Hook",
        body="Body",
        cta=cta,
    )


def _make_request(
    tmp_path: Path,
    *,
    layout: LayoutSpec | None = None,
    visual_system: CampaignVisualSystem | None = None,
    payload: SocialPostPayload | None = None,
    image_path: str | None = None,
    logo_path: str | None = None,
    fmt: str = "200x200",
) -> RenderRequest:
    out = tmp_path / "out.png"
    return RenderRequest(
        content_piece_id=PostId("p-1"),
        format=fmt,
        layout_spec=layout or _make_layout(fmt=fmt),
        content=payload or _make_payload(),
        visual_system=visual_system or _make_visual_system(),
        output_path=str(out),
        image_path=image_path,
        logo_path=logo_path,
    )


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- happy paths ---


def test_short_headline_returns_success_and_writes_png(tmp_path: Path) -> None:
    r = PillowRenderer()
    req = _make_request(tmp_path)
    result = r.render(req)
    assert result.status is RenderStatus.SUCCESS
    assert result.warnings == ()
    assert result.output_path == str(tmp_path / "out.png")
    assert Path(result.output_path).is_file()
    assert Path(result.output_path).stat().st_size > 0
    # Headline slot was measured.
    assert "headline" in result.measured_slots
    assert "width_px" in result.measured_slots["headline"]
    assert "height_px" in result.measured_slots["headline"]


def test_render_is_deterministic_same_input_same_png(tmp_path: Path) -> None:
    """The renderer must be byte-deterministic for the same input.

    (Modulo wall-clock ``render_ms``, which is NOT part of the file
    bytes.) This is the contract for plan section 45 ("deterministic
    PNG export") and is what makes downstream tooling (hash-based
    dedup, regression tests) possible.
    """
    r = PillowRenderer()
    out1 = tmp_path / "a.png"
    out2 = tmp_path / "b.png"
    req1 = _make_request(tmp_path, layout=_make_layout(fmt="200x200"))
    req1 = dataclasses_replace(req1, output_path=str(out1))
    req2 = _make_request(tmp_path, layout=_make_layout(fmt="200x200"))
    req2 = dataclasses_replace(req2, output_path=str(out2))
    r.render(req1)
    r.render(req2)
    assert _hash(out1) == _hash(out2)


def dataclasses_replace(obj, **changes):
    import dataclasses
    return dataclasses.replace(obj, **changes)


# --- primitive visual difference: HERO vs SPLIT ---


def test_hero_and_split_produce_visibly_different_pngs(tmp_path: Path) -> None:
    """HERO and SPLIT must produce visually different layouts -- not
    just cosmetically. The contract calls this out explicitly. We
    assert the PNG bytes differ (byte-inequality), and additionally
    check the measured slot heights differ (HERO uses a narrower
    content width in SPLIT mode -> different wrap).
    """
    r = PillowRenderer()
    out_hero = tmp_path / "hero.png"
    out_split = tmp_path / "split.png"
    hero_layout = _make_layout(
        primitive=LayoutPrimitive.HERO, fmt="400x400",
    )
    split_layout = _make_layout(
        primitive=LayoutPrimitive.SPLIT, fmt="400x400",
    )
    res_hero = r.render(_make_request(
        tmp_path, layout=hero_layout,
    ).__class__(  # rebuild with new layout
        content_piece_id=PostId("p-1"),
        format="400x400",
        layout_spec=hero_layout,
        content=_make_payload(),
        visual_system=_make_visual_system(),
        output_path=str(out_hero),
    ))
    res_split = r.render(_make_request(
        tmp_path, layout=split_layout,
    ).__class__(
        content_piece_id=PostId("p-1"),
        format="400x400",
        layout_spec=split_layout,
        content=_make_payload(),
        visual_system=_make_visual_system(),
        output_path=str(out_split),
    ))
    assert res_hero.status is RenderStatus.SUCCESS
    assert res_split.status is RenderStatus.SUCCESS
    # Different byte content.
    assert out_hero.read_bytes() != out_split.read_bytes()
    # Different measured slot (SPLIT uses a narrower content width).
    assert (
        res_hero.measured_slots["headline"]["width_px"]
        != res_split.measured_slots["headline"]["width_px"]
    )


# --- alignment / headline_position / overlay / cta_style ---


def test_alignment_changes_headline_x(tmp_path: Path) -> None:
    """LEFT/CENTER/RIGHT must produce visually distinct x positions
    for the headline block. We check this via measured_slots."""
    r = PillowRenderer()
    for align in (Alignment.LEFT, Alignment.CENTER, Alignment.RIGHT):
        layout = _make_layout(alignment=align, fmt="400x200")
        res = r.render(_make_request(
            tmp_path, layout=layout,
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="400x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=_make_visual_system(),
            output_path=str(tmp_path / f"a_{align.value}.png"),
        ))
        assert "headline" in res.measured_slots
        # The x_px value is a real, non-zero number (we just verify it
        # is computed; the relative difference is verified by the
        # three calls returning three different values below).
    # Sample one more cross-check: all three output PNGs are
    # byte-distinct (alignment visibly moves text).
    hashes = set()
    for align in (Alignment.LEFT, Alignment.CENTER, Alignment.RIGHT):
        out = tmp_path / f"a_{align.value}.png"
        hashes.add(_hash(out))
    assert len(hashes) == 3, "alignment should produce 3 distinct PNGs"


def test_cta_style_changes_pixels(tmp_path: Path) -> None:
    """SOLID/OUTLINE/TEXT must look visibly different. We verify by
    checking that the three outputs are byte-distinct."""
    r = PillowRenderer()
    hashes = set()
    for style in (CtaStyle.SOLID, CtaStyle.OUTLINE, CtaStyle.TEXT):
        layout = _make_layout(cta_style=style, fmt="200x200")
        out = tmp_path / f"cta_{style.value}.png"
        res = r.render(_make_request(
            tmp_path, layout=layout,
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=_make_visual_system(),
            output_path=str(out),
        ))
        assert res.status is RenderStatus.SUCCESS
        hashes.add(_hash(out))
    assert len(hashes) == 3, "cta_style should produce 3 distinct PNGs"


def test_overlay_changes_pixels(tmp_path: Path) -> None:
    """NONE/DARK/LIGHT/GRADIENT must be visibly different. Check
    that 3 of the 4 produce byte-distinct PNGs (DARK and LIGHT use
    a flat rectangle, GRADIENT uses a 64-step vertical fade)."""
    r = PillowRenderer()
    hashes = set()
    for ov in (Overlay.NONE, Overlay.DARK, Overlay.LIGHT, Overlay.GRADIENT):
        layout = _make_layout(overlay=ov, fmt="200x200")
        out = tmp_path / f"ov_{ov.value}.png"
        res = r.render(_make_request(
            tmp_path, layout=layout,
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=_make_visual_system(),
            output_path=str(out),
        ))
        assert res.status is RenderStatus.SUCCESS
        hashes.add(_hash(out))
    assert len(hashes) == 4, "overlay should produce 4 distinct PNGs"


# --- overflow / LAYOUT_VALIDATION_ERROR ---


def test_long_headline_returns_layout_validation_error_but_writes_png(
    tmp_path: Path,
) -> None:
    """A headline that wraps past the per-primitive max_lines returns
    LAYOUT_VALIDATION_ERROR, but the PNG is STILL written (the caller
    can decide to act on the warning)."""
    r = PillowRenderer()
    long_headline = " ".join(["predugacka"] * 60)  # 12-word "predugacka" x 60
    layout = _make_layout(primitive=LayoutPrimitive.HERO, fmt="200x100")
    res = r.render(
        _make_request(
            tmp_path, layout=layout,
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x100",
            layout_spec=layout,
            content=_make_payload(headline=long_headline),
            visual_system=_make_visual_system(),
            output_path=str(tmp_path / "long.png"),
        )
    )
    assert res.status is RenderStatus.LAYOUT_VALIDATION_ERROR
    assert res.warnings, "expected at least one warning"
    assert any("SHORTEN_HEADLINE" in w for w in res.warnings)
    # The PNG is STILL on disk.
    assert Path(res.output_path).is_file()
    assert Path(res.output_path).stat().st_size > 0


# --- logo_rule / cta_rule "hide" ---


def test_logo_rule_hide_skips_logo(tmp_path: Path) -> None:
    """``logo_rule`` containing 'hide' (case-insensitive) skips logo
    rendering entirely. We can't visually diff against the no-logo
    case (the logo path is None anyway in this test) -- so the
    functional check is that no exception is raised, and the PNG is
    produced."""
    r = PillowRenderer()
    layout = _make_layout(logo_position=LogoPosition.TOP_LEFT, fmt="200x200")
    vs = _make_visual_system(logo_rule="hide")
    res = r.render(
        _make_request(
            tmp_path, layout=layout, visual_system=vs,
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=vs,
            output_path=str(tmp_path / "nologo.png"),
        )
    )
    assert res.status is RenderStatus.SUCCESS
    assert Path(res.output_path).is_file()


def test_cta_rule_hide_skips_cta(tmp_path: Path) -> None:
    r = PillowRenderer()
    layout = _make_layout(cta_style=CtaStyle.SOLID, fmt="200x200")
    vs = _make_visual_system(cta_rule="hide")
    res = r.render(
        _make_request(
            tmp_path, layout=layout, visual_system=vs,
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=vs,
            output_path=str(tmp_path / "nocta.png"),
        )
    )
    assert res.status is RenderStatus.SUCCESS
    # CTA slot is NOT measured when hidden.
    assert "cta" not in res.measured_slots


# --- missing / corrupt files ---


def test_missing_logo_path_does_not_crash(tmp_path: Path) -> None:
    """``logo_path`` pointing to a non-existent file is a graceful
    skip, NOT an exception. The contract calls this out."""
    r = PillowRenderer()
    layout = _make_layout(logo_position=LogoPosition.TOP_LEFT, fmt="200x200")
    res = r.render(
        _make_request(
            tmp_path, layout=layout,
            logo_path=str(tmp_path / "does-not-exist.png"),
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=_make_visual_system(),
            output_path=str(tmp_path / "misslogo.png"),
            logo_path=str(tmp_path / "does-not-exist.png"),
        )
    )
    assert res.status is RenderStatus.SUCCESS


def test_missing_image_path_does_not_crash(tmp_path: Path) -> None:
    r = PillowRenderer()
    layout = _make_layout(image_position=ImagePosition.BACKGROUND,
                           fmt="200x200")
    res = r.render(
        _make_request(
            tmp_path, layout=layout,
            image_path=str(tmp_path / "no-image.png"),
        ).__class__(
            content_piece_id=PostId("p-1"),
            format="200x200",
            layout_spec=layout,
            content=_make_payload(),
            visual_system=_make_visual_system(),
            output_path=str(tmp_path / "missimg.png"),
            image_path=str(tmp_path / "no-image.png"),
        )
    )
    assert res.status is RenderStatus.SUCCESS


# --- bad format ---


def test_bad_format_returns_render_error_with_sentinel_png(tmp_path: Path) -> None:
    """An unparseable format string returns RENDER_ERROR but still
    writes a sentinel PNG (1x1 white) so the caller never sees a
    missing file."""
    r = PillowRenderer()
    res = r.render(
        _make_request(tmp_path, fmt="not-a-format")
    )
    assert res.status is RenderStatus.RENDER_ERROR
    assert "bad format" in res.warnings[0].lower()
    # Sentinel PNG still on disk.
    assert Path(res.output_path).is_file()


# --- CTA overflow (ACS-F1-035) ---------------------------------------------
# The original ``_draw_cta`` centred the text with ``(w - tw) // 2``.
# When ``tw > w`` (full-sentence CTA, as returned by the live AI in the
# A19 vertical slice), that arithmetic pushed the text origin LEFT of
# the button, so glyph pixels ended up at the canvas's left edge.
# The fix pre-wraps the text with ``_wrap_text`` before drawing -- each
# line is then guaranteed to fit inside the button. The two tests
# below pin BOTH the bug fix and the regression (short CTA must
# still produce the original 84px button).


def test_long_cta_text_wraps_instead_of_clipping(tmp_path: Path) -> None:
    """Reproduce the EXACT A19 live case: the AI returned the full
    sentence ``"Zakažite konsultaciju i otkrijte mogućnosti za vaš
    osmeh."`` (57 characters) as the CTA text. The original code
    would have written text glyphs at the canvas's left edge
    (X=0..10ish). After the fix, ``_wrap_text`` breaks the sentence
    into multiple lines that fit inside the 540px button -- so the
    canvas's left edge stays the background colour.

    We assert two things:

    1. The button GROWS in height past the one-line 84px minimum
       (proves the wrap is actually happening).
    2. The canvas's leftmost 20 columns inside the CTA Y-range
       contain ZERO accent-coloured pixels (proves the wrapped text
       stays inside the button).
    """
    r = PillowRenderer()
    long_cta = "Zakažite konsultaciju i otkrijte mogućnosti za vaš osmeh."
    assert len(long_cta) == 57  # the exact AI-returned length
    layout = _make_layout(
        cta_style=CtaStyle.SOLID,
        fmt="1080x1350",
    )
    payload = _make_payload(cta=long_cta)
    req = _make_request(
        tmp_path, layout=layout, payload=payload, fmt="1080x1350"
    )
    res = r.render(req)
    assert res.status is RenderStatus.SUCCESS

    # 1. The button height grew past the 84px minimum -- the wrap
    #    actually happened (more than one line of text).
    assert res.measured_slots["cta"]["height_px"] > 84

    # 2. The canvas's leftmost 20 columns inside the CTA Y-range
    #    contain NO accent pixels -- the button (and its text) is
    #    fully inside the canvas.
    img = Image.open(req.output_path)
    cta_y = int(res.measured_slots["cta"]["y_px"])
    cta_h = int(res.measured_slots["cta"]["height_px"])
    bg = _NEUTRAL_BG  # local alias for the assertion loop
    accent = _NEUTRAL_ACCENT
    # The button starts at ``cta_x`` (left edge of the button). Any
    # accent pixel AT or BEFORE ``cta_x - 1`` would mean the text
    # overflowed the button on the left. The canvas's first 20
    # columns (X in [0, 19]) are well to the left of the button for
    # every alignment we use in this test (CTA button is at
    # ``cta_x >= 80`` for LEFT-aligned or ``cta_x > 200`` for
    # CENTER-aligned, given the 80px headline margin).
    for y in range(cta_y, cta_y + cta_h):
        for x in range(0, 20):
            pixel = img.getpixel((x, y))
            assert pixel != accent, (
                f"accent-coloured pixel at ({x}, {y}) -- CTA text "
                f"overflowed the left edge of the canvas"
            )
            assert pixel == bg, (
                f"unexpected non-background pixel at ({x}, {y}) -- "
                f"value {pixel!r}, expected {_NEUTRAL_BG!r}"
            )


def test_short_cta_button_height_unchanged(tmp_path: Path) -> None:
    """REGRESSION: a short CTA like ``"Zakažite"`` must still produce
    the original 84px-tall button at the original Y position. The
    ACS-F1-035 fix is allowed to grow the button when the text
    overflows -- but it MUST NOT change anything for one-line text.
    """
    r = PillowRenderer()
    layout = _make_layout(cta_style=CtaStyle.SOLID, fmt="1080x1350")
    payload = _make_payload(cta="Zakažite")
    req = _make_request(
        tmp_path, layout=layout, payload=payload, fmt="1080x1350"
    )
    res = r.render(req)
    assert res.status is RenderStatus.SUCCESS
    # The 84px minimum is the original one-line button height.
    assert res.measured_slots["cta"]["height_px"] == 84
    # Y position is anchored at ``int(h * 0.85)`` -- 1147 for a
    # 1350-tall canvas. Pin this so a future refactor that
    # accidentally moves the button vertically is caught.
    assert res.measured_slots["cta"]["y_px"] == int(1350 * 0.85)
