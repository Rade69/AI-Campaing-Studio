"""Framework-neutral UI data-transfer objects (P0.21).

Owns the immutable ``NotificationUiModel`` and ``ProviderStatusUiModel`` DTOs
shared by the future PySide6/pywebview frontends. No Qt model classes, no
signals, no bridge objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class NotificationLevel(StrEnum):
    """Severity of a UI notification."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class NotificationUiModel:
    """A single user-facing notification."""

    level: NotificationLevel
    message_key: str
    params: dict[str, str] = field(default_factory=dict)
    technical_details: str | None = None


@dataclass(frozen=True)
class ProviderStatusUiModel:
    """Provider status shown in settings UI."""

    provider_code: str
    display_name: str
    configured: bool
    validated: bool
    model_count: int


@dataclass(frozen=True)
class CampaignPlanResultUiModel:
    """Result of a "Sačuvaj i napravi plan" click (ACS-GUI-005 bridge,
    extended in ACS-GUI-008 with ``plan_id``).

    Returned by ``CampaignBridgeApi.create_campaign_and_generate_plan``.
    Converted to a plain ``dict`` before crossing the pywebview ``js_api``
    boundary (``js_api`` is required to return JSON-serializable values,
    so the bridge calls ``dataclasses.asdict`` on this model). Every
    field is JSON-safe by construction — no ``SecretStore`` content,
    no traceback strings, no file paths.

    ACS-GUI-008 added ``plan_id`` so the JS caller can forward it to
    ``generate_campaign_content`` on the next step (Studio sadržaja
    screen), removing the need for the bridge to do raw SQL to look
    up "the current plan for this campaign". The new field is added
    AFTER the existing ones (aditive — old fields and old test
    expectations stay untouched).
    """

    ok: bool
    campaign_id: str | None
    plan_id: str | None
    plan_item_count: int | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class ProviderConfigResultUiModel:
    """Result of a "Sačuvaj" click on the Podešavanja → AI provajderi
    panel (ACS-GUI-007 bridge).

    Returned by ``CampaignBridgeApi.configure_provider``. Converted to
    a plain ``dict`` before crossing the pywebview ``js_api`` boundary.
    **NEVER carries the API key** — neither the input key, nor an
    echoed/masked/preview copy. The ``provider_code`` is the
    normalized UPPERCASE registry code (e.g. ``"OPENAI"``); it is not
    a secret.
    """

    ok: bool
    provider_code: str | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True)
class GenerateContentResultUiModel:
    """Result of a "Generiši sadržaj" click on the Studio sadržaja
    screen (ACS-GUI-008 bridge).

    Returned by ``CampaignBridgeApi.generate_campaign_content``.
    Converted to a plain ``dict`` before crossing the pywebview
    ``js_api`` boundary.

    Semantics of the success fields:

    - ``ok=True`` when ``generated_count > 0`` — at least one piece
      was successfully created. A PARTIAL success (some pieces
      succeeded, others failed) is still ``ok=True`` because the user
      can see the generated pieces and retry for the rest. The
      ``failed_count`` makes the partial nature explicit so the JS
      can show a "N of M uspjelo" toast.
    - ``ok=False`` only when ``generated_count == 0`` — either every
      piece failed, or no provider was configured, or the campaign
      was not found, or the bridge itself errored.
    - ``content_piece_ids`` is the list of pieces that landed in the
      database (only populated on success; the order matches the
      ``plan.items`` order, not the per-item retry order).
    """

    ok: bool
    campaign_id: str | None
    generated_count: int
    failed_count: int
    content_piece_ids: tuple[str, ...]
    error_code: str | None
    error_message: str | None
