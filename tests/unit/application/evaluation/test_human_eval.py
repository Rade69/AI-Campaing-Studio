"""Unit tests for the human-eval blind package (A16, §49)."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict
from pathlib import Path

from ai_campaign_studio.application.evaluation.evaluation_post import EvaluationPost
from ai_campaign_studio.application.evaluation.human_eval import (
    RUBRIC_CRITERIA,
    HumanEvalPackage,
    build_human_eval_package,
    write_human_eval_files,
)


def _post(
    headline: str, *, role: str | None = "EDUCATION", topic: str | None = "topic"
) -> EvaluationPost:
    return EvaluationPost(
        role=role,
        topic=topic,
        headline=headline,
        caption=f"caption-{headline}",
        hook="hook",
        body="body",
        cta="cta",
        hashtags=("tag1", "tag2"),
        platform_code="INSTAGRAM",
        format_code="FEED_POST",
        claims=(),
    )


def _control_a() -> tuple[EvaluationPost, ...]:
    return (_post("A1", role=None, topic=None), _post("A2", role=None, topic=None))


def _system_b() -> tuple[EvaluationPost, ...]:
    return (_post("B1"), _post("B2"))


def test_rubric_criteria_match_section_49_exactly() -> None:
    assert RUBRIC_CRITERIA == (
        "Brand fit",
        "Language naturalness",
        "Campaign coherence",
        "Post diversity",
        "Usefulness",
        "Visual consistency",
    )


def test_package_is_deterministic_for_same_seed() -> None:
    p1, r1 = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(7)
    )
    p2, r2 = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(7)
    )
    assert p1 == p2
    assert r1 == r2


def test_randomization_covers_both_outcomes() -> None:
    outcomes: set[str] = set()
    for seed in range(100):
        _, reveal = build_human_eval_package(
            _control_a(), _system_b(), rng=random.Random(seed)
        )
        outcomes.add(reveal["Campaign X"])
    assert outcomes == {"control_a", "system_b"}


def test_blind_package_does_not_leak_identity() -> None:
    package, _ = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(0)
    )
    serialized = json.dumps(asdict(package), ensure_ascii=False)
    # role/topic/claims/platform_code/format_code must never appear in the
    # blind package (System B has roles, Control A does not — leaking any of
    # these would reveal which run is which).
    for forbidden in ("role", "topic", "claims", "platform_code", "format_code"):
        assert forbidden not in serialized
    assert "EDUCATION" not in serialized


def test_human_eval_post_has_only_display_fields() -> None:
    package, _ = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(0)
    )
    post = package.campaigns[0].posts[0]
    assert set(post.__dataclass_fields__) == {
        "headline",
        "caption",
        "hook",
        "body",
        "cta",
        "hashtags",
    }


def test_reveal_is_separate_return_value() -> None:
    package, reveal = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(0)
    )
    # reveal is never a field on the package itself.
    assert "reveal" not in package.__dataclass_fields__
    assert set(reveal.keys()) == {"Campaign X", "Campaign Y"}
    assert set(reveal.values()) == {"control_a", "system_b"}
    assert reveal["Campaign X"] != reveal["Campaign Y"]


def test_write_human_eval_files_writes_three_files(tmp_path: Path) -> None:
    package, reveal = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(0)
    )
    out = tmp_path / "eval"
    write_human_eval_files(package, reveal, out)
    assert (out / "human_eval_content.json").is_file()
    assert (out / "human_eval_scoring_template.csv").is_file()
    assert (out / "human_eval_reveal.json").is_file()


def test_scoring_csv_is_an_empty_template(tmp_path: Path) -> None:
    package, reveal = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(0)
    )
    out = tmp_path / "eval"
    write_human_eval_files(package, reveal, out)

    with (out / "human_eval_scoring_template.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert [row["Campaign"] for row in rows] == ["Campaign X", "Campaign Y"]
    for row in rows:
        for criterion in RUBRIC_CRITERIA:
            assert row[criterion] == ""
        assert row["Comments"] == ""


def test_reveal_file_contains_warning_and_mapping(tmp_path: Path) -> None:
    package, reveal = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(0)
    )
    out = tmp_path / "eval"
    write_human_eval_files(package, reveal, out)

    data = json.loads((out / "human_eval_reveal.json").read_text(encoding="utf-8"))
    assert data["reveal"] == reveal
    assert "WARNING" in data


def test_build_package_is_pure_no_io() -> None:
    # build_human_eval_package takes only tuples + rng and returns in-memory
    # objects; there is no Path/disk in its signature. Import smoke-test the
    # return types without touching disk.
    package, reveal = build_human_eval_package(
        _control_a(), _system_b(), rng=random.Random(1)
    )
    assert isinstance(package, HumanEvalPackage)
    assert isinstance(reveal, dict)
