"""Revision output boundary schema tests (A4)."""

from ai_campaign_studio.application.schemas.revision_output import RevisionOutput


def test_changed_fields_only_includes_sent_fields() -> None:
    revision = RevisionOutput.model_validate({"headline": "new"})

    assert revision.changed_fields == frozenset({"headline"})


def test_empty_string_is_distinct_from_not_sent() -> None:
    revision = RevisionOutput.model_validate({"headline": ""})

    assert revision.changed_fields == frozenset({"headline"})


def test_no_fields_sent() -> None:
    revision = RevisionOutput.model_validate({})

    assert revision.changed_fields == frozenset()
