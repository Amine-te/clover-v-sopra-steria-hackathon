"""Optional Converse provider: strict validation, one repair, explicit fallback."""

import json
import logging
import time
from threading import Lock
from typing import Any, Callable, TypeVar

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ValidationError

from ...core.config import Settings, get_settings
from ...domain.privacy import RecipientContext
from ...domain.report import WeeklyReportContext
from ..base import (
    JournalAnalysisResult, ProviderMetadata, RecipientMessageDraft, WeeklyReportDraft,
)
from . import prompts
from .contracts import JournalAnalysisContext, JournalEntryAnalysis, MessageOutput, ReportOutput
from .mock import MockLLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMProviderError(RuntimeError):
    """Safe for API presentation; never contains raw AWS or model response text."""

    def __init__(self, code: str, detail: str, metadata: ProviderMetadata | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.metadata = metadata


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON numbers are forbidden")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _generation_schema(model: type[BaseModel]) -> dict[str, Any]:
    # Bedrock's constrained-decoding subset omits these validation keywords.
    # They remain enforced by Pydantic after generation, including on repair.
    omitted = {"default", "minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum"}

    def simplify(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: simplify(item) for key, item in value.items() if key not in omitted}
        if isinstance(value, list):
            return [simplify(item) for item in value]
        return value

    return simplify(model.model_json_schema())


class BedrockLLMProvider:
    def __init__(self, *, settings: Settings | None = None, client: Any = None):
        self.settings = settings or get_settings()
        self._client = client
        self._client_lock = Lock()
        self._mock = MockLLMProvider()

    def _runtime(self) -> Any:
        if not self.settings.aws_default_region.strip() or not self.settings.aws_bedrock_model_id.strip():
            raise LLMProviderError(
                "missing_configuration",
                "Bedrock nécessite AWS_DEFAULT_REGION et AWS_BEDROCK_MODEL_ID.",
            )
        with self._client_lock:
            if self._client is None:
                try:
                    self._client = boto3.Session(region_name=self.settings.aws_default_region).client(
                        "bedrock-runtime",
                        config=Config(
                            connect_timeout=5, read_timeout=60,
                            retries={"total_max_attempts": 2, "mode": "adaptive"},
                        ),
                    )
                except (BotoCoreError, ClientError):
                    raise self._unavailable() from None
        return self._client

    def analyze_journal(
        self, *, text: str, context: JournalAnalysisContext | None = None
    ) -> JournalAnalysisResult:
        if context is not None and not isinstance(context, JournalAnalysisContext):
            raise LLMProviderError("invalid_context", "Contexte d’analyse invalide.")
        payload = {"text": text}
        if context is not None:
            payload.update(context.model_dump(mode="json"))
        return self._operate(
            "analyze_journal", payload, prompts.ANALYSIS, JournalEntryAnalysis,
            lambda value: JournalAnalysisResult(**value.model_dump(), provider="bedrock"),
            lambda: self._mock.analyze_journal(text=text),
        )

    def generate_recipient_message(
        self, *, recipient_name: str, context: RecipientContext | dict[str, Any]
    ) -> RecipientMessageDraft:
        # M8's protocol serializes RecipientContext. Revalidate that exact contract,
        # including nested extra fields, BEFORE any prompt or fallback is built.
        allowed = self._typed_context(context, RecipientContext)
        if recipient_name != allowed.recipient_name:
            raise LLMProviderError("invalid_context", "Destinataire incohérent.")
        payload = allowed.model_dump(mode="json")
        return self._operate(
            "generate_recipient_message", payload, prompts.MESSAGE, MessageOutput,
            lambda value: RecipientMessageDraft(
                recipient=allowed.recipient_name, text=value.text, provider="bedrock",
            ),
            lambda: self._mock.generate_recipient_message(
                recipient_name=allowed.recipient_name, context=payload,
            ),
        )

    def generate_weekly_report(
        self, *, context: WeeklyReportContext | dict[str, Any]
    ) -> WeeklyReportDraft:
        evidence = self._typed_context(context, WeeklyReportContext)
        payload = evidence.model_dump(mode="json")
        return self._operate(
            "generate_weekly_report", payload, prompts.REPORT, ReportOutput,
            lambda value: WeeklyReportDraft(**value.model_dump(), provider="bedrock"),
            lambda: self._mock.generate_weekly_report(context=payload),
        )

    @staticmethod
    def _typed_context(context: Any, model: type[T]) -> T:
        if not isinstance(context, (model, dict)):
            raise LLMProviderError("invalid_context", "Contexte LLM invalide.")
        try:
            # JSON round-trip revalidates even mutated/constructed Pydantic objects.
            data = context.model_dump(mode="json") if isinstance(context, model) else context
            return model.model_validate_json(json.dumps(data), extra="forbid")
        except (ValidationError, TypeError, ValueError):
            raise LLMProviderError("invalid_context", "Contexte LLM invalide.") from None

    def _operate(
        self, operation: str, payload: dict[str, Any], system: str,
        output_model: type[T], convert: Callable[[T], Any], fallback: Callable[[], Any],
    ) -> Any:
        started = time.monotonic()
        retry_count = 0
        try:
            client = self._runtime()
            value, retry_count = self._generate(client, payload, system, output_model, operation)
            result = convert(value)
        except LLMProviderError as error:
            retry_count = error.metadata.validation_retry_count if error.metadata else 0
            metadata = self._metadata(started, retry_count)
            self._log(operation, metadata, "failure", error.code)
            if not self.settings.llm_fallback_to_mock:
                error.metadata = metadata
                raise error from None
            result = fallback()
            metadata.provider_used = "mock-fallback"
            metadata.fallback_used = True
            metadata.latency_ms = int((time.monotonic() - started) * 1000)
            result.provider = "mock-fallback"
            result.provider_metadata = metadata
            self._log(operation, metadata, "mock-fallback", error.code)
            return result
        metadata = self._metadata(started, retry_count)
        result.provider_metadata = metadata
        self._log(operation, metadata, "success")
        return result

    @staticmethod
    def _unavailable(retry_count: int = 0) -> LLMProviderError:
        return LLMProviderError(
            "aws_unavailable",
            "Bedrock indisponible : vérifiez les identifiants AWS, la région et l’accès au modèle.",
            ProviderMetadata(provider_used="bedrock", validation_retry_count=retry_count),
        )

    def _generate(
        self, client: Any, payload: dict, system: str, output_model: type[T], operation: str,
    ) -> tuple[T, int]:
        schema = _generation_schema(output_model)
        system += "\nSchéma JSON :\n" + json.dumps(schema, ensure_ascii=False)
        # An old SDK can still use strict JSON prompting with local validation.
        structured = "outputConfig" in client.meta.service_model.operation_model("Converse").input_shape.members
        for attempt in range(2):
            instruction = ""
            if attempt:
                instruction = (
                    "\nRéparation : la réponse précédente était invalide. Régénère un objet JSON "
                    "complet respectant le schéma et toutes les règles métier, notamment les "
                    "questions (3 maximum, avec raisons), la confidentialité et le traitement rapporté."
                )
            request = {
                "modelId": self.settings.aws_bedrock_model_id,
                "system": [{"text": system + instruction}],
                "messages": [{"role": "user", "content": [{"text": json.dumps(payload, ensure_ascii=False)}]}],
                "inferenceConfig": {"maxTokens": 3000},
            }
            if structured:
                request["outputConfig"] = {
                    "textFormat": {"type": "json_schema", "structure": {"jsonSchema": {
                        "name": output_model.__name__, "schema": json.dumps(schema),
                    }}},
                }
            try:
                try:
                    response = client.converse(**request)
                except ClientError as error:
                    if not structured or not self._unsupported_format(error):
                        raise
                    # Capability negotiation is not a validation repair. Only an
                    # explicit unsupported-format response can downgrade this call.
                    structured = False
                    request.pop("outputConfig")
                    response = client.converse(**request)
            except (BotoCoreError, ClientError):
                raise self._unavailable(attempt) from None
            try:
                if response.get("stopReason") not in {"end_turn", "stop_sequence"}:
                    raise ValueError("Incomplete or blocked output")
                blocks = response["output"]["message"]["content"]
                text = "".join(block["text"] for block in blocks if "text" in block)
                data = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_unique_object)
                return output_model.model_validate(data), attempt
            except (ValidationError, ValueError, KeyError, TypeError):
                logger.warning(
                    "llm operation=%s provider=bedrock model_id=%s validation=failure repair_count=%s",
                    operation, self.settings.aws_bedrock_model_id, attempt,
                )
        raise LLMProviderError(
            "invalid_output", "Bedrock a retourné une réponse invalide après une tentative de réparation.",
            ProviderMetadata(provider_used="bedrock", validation_retry_count=1),
        )

    @staticmethod
    def _unsupported_format(error: ClientError) -> bool:
        details = error.response.get("Error", {})
        message = details.get("Message", "").lower()
        return details.get("Code") == "ValidationException" and (
            any(term in message for term in ("outputconfig", "output config", "structured output", "textformat", "json_schema"))
            and any(term in message for term in ("not support", "unsupported", "not available"))
        )

    def _metadata(self, started: float, retry_count: int) -> ProviderMetadata:
        return ProviderMetadata(
            provider_used="bedrock", model_id=self.settings.aws_bedrock_model_id or None,
            latency_ms=int((time.monotonic() - started) * 1000), validation_retry_count=retry_count,
        )

    @staticmethod
    def _log(operation: str, metadata: ProviderMetadata, validation: str, error_code: str = "") -> None:
        log = logger.warning if validation == "failure" or metadata.fallback_used else logger.info
        log(
            "llm operation=%s provider=%s model_id=%s latency_ms=%s validation=%s "
            "validation_retry_count=%s fallback_used=%s error_code=%s",
            operation, metadata.provider_used, metadata.model_id, metadata.latency_ms,
            validation, metadata.validation_retry_count, metadata.fallback_used, error_code,
        )
