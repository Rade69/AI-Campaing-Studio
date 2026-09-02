"""Prompt repository port (A7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class PromptDefinition:
    """Full metadata for one prompt version.

    ``PromptDefinition`` is defined here (not in ``ports/ai.py``) because it
    is the prompt repository's value object, not a text-generation model.
    """

    name: str
    version: str
    purpose: str
    input_contract: str
    output_contract: str
    language_support: str
    instructions: str
    examples: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class PromptRepositoryPort(Protocol):
    """Lookup of prompt definitions by name + version."""

    def get(self, name: str, version: str) -> PromptDefinition: ...
