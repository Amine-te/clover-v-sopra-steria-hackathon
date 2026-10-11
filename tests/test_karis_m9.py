"""M9 offline Converse contracts, privacy boundaries, and API state preservation."""

import copy
import json
import logging
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.session import get_session
from fastapi.testclient import TestClient
from pydantic import ValidationError

from clover_v_sopra_steria_hackathon.api.deps import get_llm_provider
from clover_v_sopra_steria_hackathon.core.config import Settings
from clover_v_sopra_steria_hackathon.domain.privacy import RecipientContext
from clover_v_sopra_steria_hackathon.domain.report import WeeklyReportContext
from clover_v_sopra_steria_hackathon.main import create_app
from clover_v_sopra_steria_hackathon.providers.base import LLMProvider
from clover_v_sopra_steria_hackathon.providers.llm.bedrock import BedrockLLMProvider, LLMProviderError
from clover_v_sopra_steria_hackathon.providers.llm.contracts import JournalEntryAnalysis
from clover_v_sopra_steria_hackathon.providers.llm.mock import MockLLMProvider

DEMO_TEXT = (
    "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle "
    "n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé."
)


class FakeConverseClient:
    """Records actual wire requests, with no credentials or network access."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.meta = SimpleNamespace(service_model=get_session().get_service_model("bedrock-runtime"))

    def converse(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return {
            "stopReason": "end_turn",
            "output": {"message": {"role": "assistant", "content": [{
                "text": response if isinstance(response, str) else json.dumps(response),
            }]}},
        }


def _analysis():
    return MockLLMProvider().analyze_journal(text=DEMO_TEXT).model_dump(
        exclude={"provider", "provider_metadata"},
    )


def _provider(responses, *, fallback=False):
    client = FakeConverseClient(responses)
    provider = BedrockLLMProvider(
        settings=Settings(
            _env_file=None, aws_default_region="us-east-1",
            aws_bedrock_model_id="demo-model", llm_fallback_to_mock=fallback,
        ), client=client,
    )
    return provider, client


def _recipient_context():
    return RecipientContext(
        recipient_id=uuid4(), recipient_name="Sophie", role="family_caregiver",
        journal_entry_id=uuid4(),
        allowed_observations=[{"id": uuid4(), "category": "nutrition", "description": "Marie a peu mangé."}],
    )


def _weekly_context():
    return WeeklyReportContext(
        care_recipient_name="Marie", period_start=date(2026, 9, 7), period_end=date(2026, 9, 13),
        source_entry_count=6, structured_item_count=11, reportable_item_count=8,
        excluded_private_count=9,
        recurring_observations={"nutrition_low": {
            "count": 3, "dates": ["2026-09-08", "2026-09-09", "2026-09-10"],
        }},
    )


def test_mock_analysis_and_messages_remain_deterministic():
    mock = MockLLMProvider()
    result = mock.analyze_journal(text=DEMO_TEXT)
    assert result == mock.analyze_journal(text=DEMO_TEXT, context=None)
    assert result.provider == "mock"
    assert len(result.questions) == 2
    assert result.caregiver_feelings == [{"description": "Thomas se dit vraiment fatigué", "visibility": "private"}]
    assert result.observations[2]["description"] == "Traitement déclaré comme pris"
    payload = _recipient_context().model_dump(mode="json")
    assert mock.generate_recipient_message(recipient_name="Sophie", context=payload) == (
        mock.generate_recipient_message(recipient_name="Sophie", context=payload)
    )


def test_provider_protocol_and_successful_validated_converse_output():
    provider, client = _provider([_analysis()])
    assert isinstance(provider, LLMProvider)
    result = provider.analyze_journal(text=DEMO_TEXT)
    assert result.short_summary == _analysis()["short_summary"]
    validated = JournalEntryAnalysis.model_validate(result.model_dump(exclude={"provider", "provider_metadata"}))
    assert validated.caregiver_feelings[0].visibility == "private"
    assert client.requests[0]["inferenceConfig"]["maxTokens"] == 3000
    output_config = client.requests[0]["outputConfig"]["textFormat"]
    assert output_config["type"] == "json_schema"
    assert json.loads(output_config["structure"]["jsonSchema"]["schema"])["additionalProperties"] is False
    metadata = result.provider_metadata.model_dump()
    assert metadata == {
        "provider_used": "bedrock", "model_id": "demo-model", "latency_ms": metadata["latency_ms"],
        "validation_retry_count": 0, "fallback_used": False,
    }
    assert metadata["latency_ms"] >= 0


@pytest.mark.parametrize("invalid", [
    "not JSON", "```json\n{}\n```", '{"short_summary":"one","short_summary":"two"}',
    '{"short_summary":NaN}', {},
])
def test_invalid_json_or_schema_triggers_exactly_one_repair(invalid):
    provider, client = _provider([invalid, _analysis()])
    result = provider.analyze_journal(text=DEMO_TEXT)
    assert result.provider_metadata.validation_retry_count == 1
    assert len(client.requests) == 2
    assert "Réparation" in client.requests[1]["system"][0]["text"]
    assert client.requests[0]["messages"] == client.requests[1]["messages"]


@pytest.mark.parametrize("change", [
    {"caregiver_feelings": [{"description": "Privé", "visibility": "circle"}]},
    {"questions": ["a", "b", "c", "d"], "clarification_reasons": ["r"] * 4},
    {"observations": [{"category": "medication", "description": "Bonne observance"}]},
    {"observations": [{"category": "fatigue", "description": "Aidant fatigué", "subject": "caregiver"}]},
    {"actions": [{"description": "Une tâche", "status": "invalid"}]},
    {"clarification_needed": False},
])
def test_domain_invalid_output_is_repaired_before_return(change):
    invalid = _analysis() | change
    with pytest.raises(ValidationError):
        JournalEntryAnalysis.model_validate(invalid)
    provider, client = _provider([invalid, _analysis()])
    assert provider.analyze_journal(text=DEMO_TEXT).provider_metadata.validation_retry_count == 1
    assert len(client.requests) == 2


def test_second_invalid_output_produces_controlled_failure_without_private_data(caplog):
    provider, client = _provider(["PRIVATE_BAD_OUTPUT", "PRIVATE_BAD_OUTPUT"])
    with caplog.at_level(logging.INFO), pytest.raises(LLMProviderError) as raised:
        provider.analyze_journal(text="PRIVATE_JOURNAL")
    assert raised.value.code == "invalid_output"
    assert raised.value.metadata.validation_retry_count == 1
    assert len(client.requests) == 2
    assert "PRIVATE" not in str(raised.value)
    assert "PRIVATE" not in caplog.text
    assert "operation=analyze_journal" in caplog.text
    assert "validation=failure" in caplog.text


def test_fallback_preserves_mock_result_and_reports_failure_truthfully(caplog):
    provider, client = _provider(["invalid", "invalid"], fallback=True)
    with caplog.at_level(logging.INFO):
        result = provider.analyze_journal(text=DEMO_TEXT)
    mock = MockLLMProvider().analyze_journal(text=DEMO_TEXT)
    assert result.model_dump(exclude={"provider", "provider_metadata"}) == (
        mock.model_dump(exclude={"provider", "provider_metadata"})
    )
    assert result.provider == "mock-fallback"
    assert result.provider_metadata.provider_used == "mock-fallback"
    assert result.provider_metadata.fallback_used is True
    assert result.provider_metadata.validation_retry_count == 1
    assert len(client.requests) == 2
    assert "fallback_used=True" in caplog.text
    assert DEMO_TEXT not in caplog.text


@pytest.mark.parametrize("fallback", [True, False])
def test_missing_config_is_lazy_and_controlled(fallback, monkeypatch):
    monkeypatch.setattr("boto3.Session", lambda **kwargs: pytest.fail("No AWS client should be created"))
    provider = BedrockLLMProvider(settings=Settings(
        _env_file=None, aws_default_region="", aws_bedrock_model_id="", llm_fallback_to_mock=fallback,
    ))
    assert isinstance(provider, LLMProvider)
    if fallback:
        assert provider.analyze_journal(text=DEMO_TEXT).provider == "mock-fallback"
    else:
        with pytest.raises(LLMProviderError, match="AWS_DEFAULT_REGION.*AWS_BEDROCK_MODEL_ID"):
            provider.analyze_journal(text=DEMO_TEXT)


@pytest.mark.parametrize("error", [
    NoCredentialsError(),
    ClientError({"Error": {"Code": "AccessDeniedException", "Message": "SECRET_RAW_AWS"}}, "Converse"),
])
def test_aws_failure_is_controlled_without_validation_retry_or_secret_logging(error, caplog):
    provider, client = _provider([error])
    with caplog.at_level(logging.INFO), pytest.raises(LLMProviderError) as raised:
        provider.analyze_journal(text="PRIVATE_INPUT")
    assert raised.value.code == "aws_unavailable"
    assert len(client.requests) == 1
    assert raised.value.metadata.validation_retry_count == 0
    assert "SECRET_RAW_AWS" not in caplog.text + str(raised.value)
    assert "PRIVATE_INPUT" not in caplog.text


def test_unsupported_structured_output_downgrades_to_strict_json():
    unsupported = ClientError({"Error": {
        "Code": "ValidationException", "Message": "This model does not support structured output outputConfig",
    }}, "Converse")
    provider, client = _provider([unsupported, _analysis()])
    result = provider.analyze_journal(text=DEMO_TEXT)
    assert "outputConfig" in client.requests[0]
    assert "outputConfig" not in client.requests[1]
    assert "Schéma JSON" in client.requests[1]["system"][0]["text"]
    assert result.provider_metadata.validation_retry_count == 0


def test_unrelated_validation_exception_does_not_downgrade_or_retry():
    error = ClientError({"Error": {"Code": "ValidationException", "Message": "Invalid modelId"}}, "Converse")
    provider, client = _provider([error])
    with pytest.raises(LLMProviderError):
        provider.analyze_journal(text=DEMO_TEXT)
    assert len(client.requests) == 1


def test_recipient_prompt_is_exactly_recipient_context():
    context = _recipient_context()
    provider, client = _provider([{"text": "Bonjour Sophie, Marie a peu mangé."}])
    result = provider.generate_recipient_message(recipient_name="Sophie", context=context.model_dump(mode="json"))
    request = client.requests[0]
    payload = json.loads(request["messages"][0]["content"][0]["text"])
    assert payload == context.model_dump(mode="json")
    assert result.recipient == "Sophie"
    for forbidden in ("original_text", "caregiver_feelings", "caregiver_vocal_affect", "caregiver_wearable"):
        assert forbidden not in payload


@pytest.mark.parametrize("forbidden", ["original_text", "caregiver_feelings", "caregiver_vocal_affect", "caregiver_wearable"])
def test_unfiltered_recipient_context_is_rejected_before_prompt_or_fallback(forbidden):
    provider, client = _provider([], fallback=True)
    context = _recipient_context().model_dump(mode="json") | {forbidden: "PRIVATE"}
    with pytest.raises(LLMProviderError) as raised:
        provider.generate_recipient_message(recipient_name="Sophie", context=context)
    assert raised.value.code == "invalid_context"
    assert client.requests == []


def test_private_extra_nested_field_is_rejected():
    provider, client = _provider([])
    context = _recipient_context().model_dump(mode="json")
    context["allowed_observations"][0]["original_text"] = "PRIVATE"
    with pytest.raises(LLMProviderError):
        provider.generate_recipient_message(recipient_name="Sophie", context=context)
    assert client.requests == []


def test_weekly_report_receives_only_deterministic_context_and_preserves_counts():
    context = _weekly_context()
    before = context.model_dump(mode="json")
    provider, client = _provider([{"title": "Semaine de Marie", "markdown": "Faible alimentation rapportée trois fois."}])
    result = provider.generate_weekly_report(context=before)
    payload = json.loads(client.requests[0]["messages"][0]["content"][0]["text"])
    assert payload == before
    assert context.model_dump(mode="json") == before
    assert payload["recurring_observations"]["nutrition_low"]["count"] == 3
    assert "Ne compte pas les événements bruts" in client.requests[0]["system"][0]["text"]
    assert result.provider_metadata.provider_used == "bedrock"
    with pytest.raises(LLMProviderError):
        provider.generate_weekly_report(context=before | {"journal_entries": [{"original_text": "PRIVATE"}]})
    assert len(client.requests) == 1


def test_message_and_report_use_same_validation_retry_and_fallback():
    provider, _ = _provider([{"text": 7}, {"text": "Bonjour Sophie."}])
    result = provider.generate_recipient_message(recipient_name="Sophie", context=_recipient_context())
    assert result.provider_metadata.validation_retry_count == 1
    provider, _ = _provider([NoCredentialsError()], fallback=True)
    report = provider.generate_weekly_report(context=_weekly_context())
    assert report.provider == "mock-fallback"
    assert report.provider_metadata.fallback_used is True


def _api_entry():
    app = create_app()
    client = TestClient(app)
    recipient = client.get("/api/care-recipients").json()[0]
    response = client.post("/api/journal", json={
        "care_recipient_id": recipient["id"], "input_type": "text", "original_text": DEMO_TEXT,
    })
    assert response.status_code == 201
    return app, client, response.json()["id"], recipient["id"]


def test_api_fallback_returns_metadata_and_keeps_original_journal_state():
    app, client, entry_id, _ = _api_entry()
    provider, _ = _provider([NoCredentialsError()], fallback=True)
    app.dependency_overrides[get_llm_provider] = lambda: provider
    response = client.post(f"/api/journal/{entry_id}/analyze")
    assert response.status_code == 200
    body = response.json()
    assert body["original_text"] == DEMO_TEXT
    assert body["provider_metadata"]["provider_used"] == "mock-fallback"
    assert body["provider_metadata"]["fallback_used"] is True
    assert body["caregiver_feelings"][0]["visibility"] == "private"


def test_api_invalid_output_preserves_previous_analysis_and_clarification_answers():
    app, client, entry_id, _ = _api_entry()
    before = client.post(f"/api/journal/{entry_id}/analyze").json()
    provider, _ = _provider(["invalid", "invalid", "invalid", "invalid"])
    app.dependency_overrides[get_llm_provider] = lambda: provider
    failed = client.post(f"/api/journal/{entry_id}/analyze")
    assert failed.status_code == 502
    assert failed.json()["code"] == "invalid_output"
    after = client.get(f"/api/journal/{entry_id}").json()
    assert after["observations"] == before["observations"]
    assert after["original_text"] == DEMO_TEXT
    response = client.post(f"/api/journal/{entry_id}/clarifications", json={"answers": [
        {"clarification_id": item["id"], "answer": "Oui"} for item in before["clarifications"]
    ]})
    assert response.status_code == 502
    saved = client.get(f"/api/journal/{entry_id}").json()
    assert all(item["answer"] == "Oui" for item in saved["clarifications"])
    assert saved["observations"] == before["observations"]


def test_api_bedrock_recipient_requests_exclude_all_owner_private_sources():
    app, client, entry_id, _ = _api_entry()
    assert client.post(f"/api/journal/{entry_id}/analyze").status_code == 200
    assert client.post(f"/api/journal/{entry_id}/multimodal/enrich").status_code == 200
    provider, wire = _provider([{"text": "Brouillon de coordination."}] * 5)
    app.dependency_overrides[get_llm_provider] = lambda: provider
    response = client.post(f"/api/journal/{entry_id}/messages/generate")
    assert response.status_code == 200
    assert wire.requests
    for request in wire.requests:
        payload = json.loads(request["messages"][0]["content"][0]["text"])
        RecipientContext.model_validate_json(json.dumps(payload), extra="forbid")
        serialized = json.dumps(payload, ensure_ascii=False)
        for secret in (DEMO_TEXT, "Thomas se dit vraiment fatigué", "tension_like", "heart_rate_avg_bpm", "original_text"):
            assert secret not in serialized
    assert all(draft["provider_metadata"]["provider_used"] == "bedrock" for draft in response.json()["drafts"])


def test_api_owner_analysis_receives_separate_contextual_signals_without_previous_analysis():
    app, client, entry_id, _ = _api_entry()
    assert client.post(f"/api/journal/{entry_id}/multimodal/enrich").status_code == 200
    provider, wire = _provider([_analysis()])
    app.dependency_overrides[get_llm_provider] = lambda: provider
    response = client.post(f"/api/journal/{entry_id}/analyze")
    assert response.status_code == 200
    payload = json.loads(wire.requests[0]["messages"][0]["content"][0]["text"])
    assert payload["care_recipient_first_name"] == "Marie"
    assert payload["caregiver_first_name"] == "Thomas"
    assert payload["caregiver_vocal_affect"]["visibility"] == "private"
    assert payload["caregiver_wearable"]["subject_type"] == "caregiver"
    assert payload["care_recipient_wearable"]["subject_type"] == "care_recipient"
    assert "semantic_analysis" not in payload


def test_api_weekly_report_metadata_and_deterministic_evidence():
    app, client, _, recipient_id = _api_entry()
    provider, wire = _provider([{"title": "Rapport", "markdown": "Aucune information sur cette période."}])
    app.dependency_overrides[get_llm_provider] = lambda: provider
    response = client.post(f"/api/care-recipients/{recipient_id}/reports/weekly/generate", json={
        "period_start": "2020-01-06", "period_end": "2020-01-12",
    })
    assert response.status_code == 200
    assert response.json()["provider_metadata"]["provider_used"] == "bedrock"
    payload = json.loads(wire.requests[0]["messages"][0]["content"][0]["text"])
    assert payload["source_entry_count"] == 0
    assert "original_text" not in payload


def test_registry_bedrock_selection_and_health_require_no_credentials(monkeypatch):
    from clover_v_sopra_steria_hackathon.providers import registry
    monkeypatch.setattr(registry, "get_settings", lambda: Settings(_env_file=None, llm_provider="bedrock"))
    monkeypatch.setattr("boto3.Session", lambda **kwargs: pytest.fail("No client on startup"))
    registry.get_llm_provider.cache_clear()
    try:
        assert isinstance(registry.get_llm_provider(), BedrockLLMProvider)
        assert TestClient(create_app()).get("/api/health").status_code == 200
    finally:
        registry.get_llm_provider.cache_clear()
