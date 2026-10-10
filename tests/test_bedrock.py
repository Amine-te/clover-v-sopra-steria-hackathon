"""Invoke Amazon Nova Pro (already confirmed working with this workshop role)."""
import os
import pytest

pytestmark = pytest.mark.aws_live


def test_bedrock_converse(aws_session):
    client = aws_session.client("bedrock-runtime")
    model_id = os.getenv("BEDROCK_TEST_MODEL", "amazon.nova-pro-v1:0")
    result = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": "Reply with one short greeting in French."}]}],
        inferenceConfig={"maxTokens": 100, "temperature": 0.1},
    )
    content = result["output"]["message"]["content"]
    text = " ".join(block.get("text", "") for block in content).strip()
    print("Bedrock response:", text)
    assert text
