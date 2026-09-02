"""YAML prompt repository (A7)."""

from __future__ import annotations

from pathlib import Path

import yaml  # type: ignore[import-untyped]

from ai_campaign_studio.ports.prompts import PromptDefinition, PromptRepositoryPort

_REQUIRED_FIELDS = (
    "name",
    "version",
    "purpose",
    "input_contract",
    "output_contract",
    "language_support",
    "instructions",
    "examples",
)


class YamlPromptRepository(PromptRepositoryPort):
    """Loads prompt definitions from ``resources/prompts/<name>/<version>.yaml``."""

    def __init__(self, prompts_dir: Path) -> None:
        self._prompts_dir = prompts_dir

    @classmethod
    def from_bundled_resources(cls) -> YamlPromptRepository:
        return cls(Path(__file__).resolve().parents[4] / "resources" / "prompts")

    def get(self, name: str, version: str) -> PromptDefinition:
        path = self._prompts_dir / name / f"v{version}.yaml"
        if not path.exists():
            raise ValueError(f"prompt not found: {name}/{version}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"prompt file must be a mapping: {path}")

        for field in _REQUIRED_FIELDS:
            if field not in raw or raw[field] is None:
                raise ValueError(f"prompt {name}/{version} missing field: {field}")

        examples = raw["examples"]
        if not isinstance(examples, list):
            raise ValueError(f"prompt {name}/{version} examples must be a list")

        return PromptDefinition(
            name=raw["name"],
            version=raw["version"],
            purpose=raw["purpose"],
            input_contract=raw["input_contract"],
            output_contract=raw["output_contract"],
            language_support=raw["language_support"],
            instructions=raw["instructions"],
            examples=tuple(examples),
        )
