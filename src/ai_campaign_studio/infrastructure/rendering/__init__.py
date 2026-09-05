"""Rendering infrastructure adapters (A14 dio 2).

The selected renderer (currently ``PillowRenderer``) implements
``RendererPort`` and is the ONLY rendering technology wired up in
Slice 1. Future A14 tasks (or a follow-up if a real SVG library is
adopted) can add additional adapters without changing the port or
``RenderPost`` -- the application layer talks to the port, not the
adapter.
"""

from ai_campaign_studio.infrastructure.rendering.selected_renderer import (
    PillowRenderer,
)

__all__ = ["PillowRenderer"]
