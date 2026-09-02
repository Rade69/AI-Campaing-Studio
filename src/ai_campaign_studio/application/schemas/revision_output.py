"""Pydantic boundary schema for partial content revision (A4).

Partial-update semantics: a field absent from the input is "not sent", while a
field explicitly set (to ``""`` or ``None``) is "sent". The distinction is
exposed through ``model_fields_set`` (Pydantic's set of explicitly-provided
fields), so a revision that changes only ``headline`` never touches
``caption`` unless ``caption`` was itself present in the input.
"""

from pydantic import BaseModel, ConfigDict


class RevisionOutput(BaseModel):
    """Partial-field revision shape (only fields that change)."""

    model_config = ConfigDict(frozen=True)

    headline: str | None = None
    caption: str | None = None
    hook: str | None = None
    body: str | None = None
    cta: str | None = None
    hashtags: list[str] | None = None

    @property
    def changed_fields(self) -> frozenset[str]:
        """Field names explicitly present in the input (not defaults)."""
        return frozenset(self.model_fields_set)
