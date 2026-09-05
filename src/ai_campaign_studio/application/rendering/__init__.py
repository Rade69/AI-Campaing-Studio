"""Rendering application layer (A14 dio 2).

The ``RenderPost`` use-case is the SINGLE entry point that turns a
content piece into a rendered PNG. The application layer is the
right place for this orchestration -- it knows how to look up the
content piece, the layout spec (most recent), the visual system, and
the renderer; it does not itself draw anything.
"""

from ai_campaign_studio.application.rendering.render_post import RenderPost

__all__ = ["RenderPost"]
