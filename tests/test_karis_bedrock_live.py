"""Explicit opt-in synthetic M9 check; excluded from normal pytest."""

import pytest

from clover_v_sopra_steria_hackathon.core.config import get_settings
from clover_v_sopra_steria_hackathon.providers.llm.bedrock import BedrockLLMProvider
from clover_v_sopra_steria_hackathon.providers.llm.contracts import JournalAnalysisContext


@pytest.mark.aws_live
def test_live_bedrock_analysis_is_validated_without_fallback():
    settings = get_settings()
    if not settings.aws_default_region or not settings.aws_bedrock_model_id:
        pytest.skip("Set AWS_DEFAULT_REGION and AWS_BEDROCK_MODEL_ID for the live M9 check")
    settings = settings.model_copy(update={"llm_fallback_to_mock": False})
    provider = BedrockLLMProvider(settings=settings)
    result = provider.analyze_journal(
        text="Marie a mangé une soupe au déjeuner. Sophie est passée cet après-midi.",
        context=JournalAnalysisContext(care_recipient_first_name="Marie", caregiver_first_name="Thomas"),
    )
    assert result.short_summary
    assert len(result.questions) <= 3
    assert result.provider_metadata.provider_used == "bedrock"
    assert result.provider_metadata.fallback_used is False
