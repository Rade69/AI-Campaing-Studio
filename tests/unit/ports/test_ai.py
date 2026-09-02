"""AI port model tests (A7)."""

from dataclasses import is_dataclass

from ai_campaign_studio.ports.ai import AIMessage, AIRequest, AIResponse, AITelemetry


def test_models_are_dataclasses() -> None:
    assert is_dataclass(AIMessage)
    assert is_dataclass(AIRequest)
    assert is_dataclass(AIResponse)
    assert is_dataclass(AITelemetry)


def test_aimessage_role_and_content() -> None:
    message = AIMessage(role="user", content="Hello")

    assert message.role == "user"
    assert message.content == "Hello"


def test_airequest_builds() -> None:
    request = AIRequest(
        purpose="campaign_plan",
        prompt_name="campaign_plan",
        prompt_version="1",
        system_text="system",
        user_text="user",
        json_schema={},
        metadata={"key": "value"},
    )

    assert request.prompt_name == "campaign_plan"
    assert request.metadata == {"key": "value"}
