"""YAML prompt repository tests (A7)."""

import pytest

from ai_campaign_studio.infrastructure.prompts.yaml_prompt_repository import (
    YamlPromptRepository,
)
from ai_campaign_studio.ports.prompts import PromptRepositoryPort


def test_repository_is_a_prompt_repository_port() -> None:
    repo = YamlPromptRepository.from_bundled_resources()

    assert isinstance(repo, PromptRepositoryPort)


def test_loads_all_five_prompts() -> None:
    repo = YamlPromptRepository.from_bundled_resources()

    for name in (
        "campaign_plan",
        "post_generation",
        "revision",
        "visual_direction",
        "ab_control",
    ):
        definition = repo.get(name, "1")
        assert definition.name == name
        assert definition.instructions


def test_missing_field_raises(tmp_path) -> None:
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "v1.yaml").write_text(
        "name: bad\n"
        'version: "1"\n'
        "purpose: p\n"
        "input_contract: i\n"
        "language_support: l\n"
        "instructions: inst\n"
        "examples: []\n",
        encoding="utf-8",
    )
    repo = YamlPromptRepository(tmp_path)

    with pytest.raises(ValueError):
        repo.get("bad", "1")


def test_unknown_version_raises() -> None:
    repo = YamlPromptRepository.from_bundled_resources()

    with pytest.raises(ValueError):
        repo.get("campaign_plan", "99")


def test_ab_control_has_no_campaign_role_info() -> None:
    repo = YamlPromptRepository.from_bundled_resources()
    definition = repo.get("ab_control", "1")

    text = definition.instructions + " ".join(definition.examples)
    for role in (
        "PROBLEM",
        "EDUCATION",
        "INSIGHT",
        "PROOF",
        "OBJECTION",
        "BENEFIT",
        "OFFER",
        "ACTION",
    ):
        assert role not in text
