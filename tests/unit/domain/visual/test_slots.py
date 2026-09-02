"""Visual domain tests (A3 — enums, slots)."""

from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CaseStyle,
    LayoutPrimitive,
    OverflowPolicy,
    SlotName,
)
from ai_campaign_studio.domain.visual.slots import BoundingBox, ContentSlotContract


def test_layout_primitive_members() -> None:
    assert {m.value for m in LayoutPrimitive} == {"HERO", "SPLIT"}


def test_slot_name_members() -> None:
    assert {m.value for m in SlotName} == {"HEADLINE", "CTA"}


def test_content_slot_contract_fields_are_typed() -> None:
    slot = ContentSlotContract(
        slot_name=SlotName.HEADLINE,
        target_chars=30,
        max_chars=60,
        max_lines=2,
        preferred_case=CaseStyle.TITLE,
        allow_wrap=True,
        font_family="Inter",
        min_font_size=24.0,
        max_font_size=48.0,
        bounding_box=BoundingBox(x=0, y=0, width=1080, height=200),
        line_height=1.2,
        alignment=Alignment.LEFT,
        overflow_policy=OverflowPolicy.ELLIPSIS,
    )

    assert slot.slot_name is SlotName.HEADLINE
    assert slot.preferred_case is CaseStyle.TITLE
    assert slot.alignment is Alignment.LEFT
    assert slot.overflow_policy is OverflowPolicy.ELLIPSIS
    assert isinstance(slot.bounding_box, BoundingBox)
