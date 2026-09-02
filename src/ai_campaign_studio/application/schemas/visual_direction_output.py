"""Pydantic boundary schema for visual direction LLM output (A4)."""

from pydantic import BaseModel, ConfigDict, Field

from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaRule,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    ImageTreatment,
    LayoutPrimitive,
    LogoPosition,
    LogoRule,
    Overlay,
)


class CampaignVisualSystemCandidate(BaseModel):
    """A candidate visual system for one campaign."""

    model_config = ConfigDict(frozen=True)

    primary_layout_family: LayoutPrimitive
    secondary_layout_family: LayoutPrimitive | None = None
    headline_scale: HeadlineScale
    image_treatment: ImageTreatment
    logo_rule: LogoRule
    cta_rule: CtaRule
    alignment: Alignment
    style: list[str] = Field(default_factory=list)


class LayoutSpecCandidate(BaseModel):
    """A candidate raster layout specification."""

    model_config = ConfigDict(frozen=True)

    primitive: LayoutPrimitive
    image_position: ImagePosition
    headline_position: HeadlinePosition
    headline_scale: HeadlineScale
    overlay: Overlay
    logo_position: LogoPosition
    cta_style: CtaStyle
    alignment: Alignment
    format: str


class VisualDirectionOutput(BaseModel):
    """LLM output shape for a visual direction (system + layout)."""

    model_config = ConfigDict(frozen=True)

    campaign_visual_system: CampaignVisualSystemCandidate
    layout_spec: LayoutSpecCandidate
