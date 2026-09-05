"""Human evaluation blind package (A16, §49).

Owns turning Control A / System B ``EvaluationPost`` tuples into a blind
"Campaign X"/"Campaign Y" package for human scoring, plus a thin disk writer
(JSON content + empty CSV scoring template + a separate reveal JSON). Does
NOT own the rubric definition (that is §49's fixed 6-criteria list), the A/B
runners, or metric computation — it only consumes ``EvaluationPost``.
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

from ai_campaign_studio.application.evaluation.evaluation_post import EvaluationPost


@dataclass(frozen=True)
class HumanEvalPost:
    """One post as shown to the human evaluator (identity-free)."""

    headline: str
    caption: str
    hook: str
    body: str
    cta: str
    hashtags: tuple[str, ...]


@dataclass(frozen=True)
class BlindCampaign:
    """One blind campaign bucket ("Campaign X" or "Campaign Y")."""

    label: str
    posts: tuple[HumanEvalPost, ...]


# §49 fixed rubric, exact text and order. "Comments" is a free-text column,
# not a 1-5 criterion, so it lives in the CSV writer only, not here.
RUBRIC_CRITERIA: tuple[str, ...] = (
    "Brand fit",
    "Language naturalness",
    "Campaign coherence",
    "Post diversity",
    "Usefulness",
    "Visual consistency",
)


@dataclass(frozen=True)
class HumanEvalPackage:
    """The blind package an evaluator reads (NO reveal mapping inside)."""

    campaigns: tuple[BlindCampaign, BlindCampaign]
    rubric_criteria: tuple[str, ...] = RUBRIC_CRITERIA


def build_human_eval_package(
    control_a_posts: tuple[EvaluationPost, ...],
    system_b_posts: tuple[EvaluationPost, ...],
    rng: random.Random | None = None,
) -> tuple[HumanEvalPackage, dict[str, str]]:
    """Build a blind "Campaign X"/"Campaign Y" package plus a reveal mapping.

    The reveal dict maps "Campaign X"/"Campaign Y" back to "control_a"/
    "system_b" and is returned SEPARATELY (never embedded in the package),
    so it cannot be accidentally serialized into the file the evaluator
    reads. ``rng`` is an injectable seam; ``None`` uses a fresh
    ``random.Random()`` in production. The X/Y assignment is randomized per
    call so an evaluator doing multiple runs cannot learn a fixed A=X/B=Y
    pattern.
    """
    if rng is None:
        rng = random.Random()

    x_is_control_a = rng.random() < 0.5
    if x_is_control_a:
        x_posts = _to_human_eval_posts(control_a_posts)
        y_posts = _to_human_eval_posts(system_b_posts)
        reveal = {"Campaign X": "control_a", "Campaign Y": "system_b"}
    else:
        x_posts = _to_human_eval_posts(system_b_posts)
        y_posts = _to_human_eval_posts(control_a_posts)
        reveal = {"Campaign X": "system_b", "Campaign Y": "control_a"}

    package = HumanEvalPackage(
        campaigns=(
            BlindCampaign(label="Campaign X", posts=x_posts),
            BlindCampaign(label="Campaign Y", posts=y_posts),
        )
    )
    return package, reveal


def _to_human_eval_posts(
    posts: tuple[EvaluationPost, ...],
) -> tuple[HumanEvalPost, ...]:
    """Map to the identity-free display shape.

    Deliberately drops ``role``/``topic``/``claims``/``platform_code``/
    ``format_code`` — any of those could reveal which run produced the text
    (e.g. System B has roles while Control A does not).
    """
    return tuple(
        HumanEvalPost(
            headline=post.headline,
            caption=post.caption,
            hook=post.hook,
            body=post.body,
            cta=post.cta,
            hashtags=post.hashtags,
        )
        for post in posts
    )


def write_human_eval_files(
    package: HumanEvalPackage,
    reveal: dict[str, str],
    output_dir: Path,
) -> None:
    """Write the three §49 artifacts into ``output_dir``.

    - ``human_eval_content.json`` — readable content of both blind campaigns.
    - ``human_eval_scoring_template.csv`` — empty template, one row per
      campaign, columns = 6 criteria + Comments, all values blank.
    - ``human_eval_reveal.json`` — the reveal mapping ONLY, in a separate
      file with an explicit "do not open before scoring" warning.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_content_json(package, output_dir / "human_eval_content.json")
    _write_scoring_csv(package, output_dir / "human_eval_scoring_template.csv")
    _write_reveal_json(reveal, output_dir / "human_eval_reveal.json")


def _write_content_json(package: HumanEvalPackage, path: Path) -> None:
    payload = {
        "rubric_criteria": list(package.rubric_criteria),
        "campaigns": [
            {
                "label": campaign.label,
                "posts": [
                    {
                        "headline": post.headline,
                        "caption": post.caption,
                        "hook": post.hook,
                        "body": post.body,
                        "cta": post.cta,
                        "hashtags": list(post.hashtags),
                    }
                    for post in campaign.posts
                ],
            }
            for campaign in package.campaigns
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _write_scoring_csv(package: HumanEvalPackage, path: Path) -> None:
    fieldnames = ["Campaign", *package.rubric_criteria, "Comments"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for campaign in package.campaigns:
            writer.writerow(
                {
                    "Campaign": campaign.label,
                    **{criterion: "" for criterion in package.rubric_criteria},
                    "Comments": "",
                }
            )


def _write_reveal_json(reveal: dict[str, str], path: Path) -> None:
    payload = {
        "WARNING": "do not open before scoring is complete",
        "reveal": reveal,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
