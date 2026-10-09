"""Amazon Bedrock smoke test: invoke a foundation model with a prompt.

Uses the Bedrock Converse API, which gives a single, model-agnostic request
shape across Anthropic Claude, Amazon Nova/Titan, Meta Llama, etc.

Usage:
    python bedrock_sample.py
    python bedrock_sample.py --list                 # list available models
    python bedrock_sample.py --model amazon.nova-lite-v1:0
    python bedrock_sample.py --prompt "Write a haiku about hackathons"
"""

import argparse
import os

import common

DEFAULT_PROMPT = "In one sentence, what is AWS Game Day?"


def list_models():
    bedrock = common.client("bedrock")
    print("Foundation models visible to your account/region:\n")
    resp = bedrock.list_foundation_models()
    for m in sorted(resp.get("modelSummaries", []), key=lambda x: x["modelId"]):
        modalities = ",".join(m.get("outputModalities", []))
        print(f"  {m['modelId']:<45} ({m.get('providerName', '?')}) -> {modalities}")
    print(
        "\nNote: a model listed here still needs 'Model access' enabled in the "
        "Bedrock console before you can invoke it."
    )


def invoke(model_id: str, prompt: str, max_tokens: int = 300,
           save_as: str = "bedrock_response.txt") -> str:
    """Invoke a model with prompt via Converse; print, save, and return the text."""
    # Converse lives on the bedrock-runtime client.
    runtime = common.client("bedrock-runtime")

    print(f"Model  : {model_id}")
    print(f"Region : {common.region()}")
    print(f"Prompt : {prompt}\n")

    resp = runtime.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.7},
    )

    text = resp["output"]["message"]["content"][0]["text"].strip()
    usage = resp.get("usage", {})
    print("Response:")
    print("-" * 60)
    print(text)
    print("-" * 60)
    print(
        f"tokens: in={usage.get('inputTokens')} "
        f"out={usage.get('outputTokens')} total={usage.get('totalTokens')}"
    )

    if save_as:
        out_path = common.write_output(save_as, text)
        print(f"Saved response -> {out_path}")
    print("✅ Bedrock sample completed successfully.")
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Bedrock smoke test")
    parser.add_argument("--list", action="store_true", help="list foundation models")
    parser.add_argument(
        "--model",
        default=os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
        help="Bedrock model id (default: env BEDROCK_MODEL_ID or amazon.nova-lite-v1:0)",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="prompt text")
    args = parser.parse_args()

    try:
        if args.list:
            list_models()
        else:
            invoke(args.model, args.prompt)
    except Exception as err:  # noqa: BLE001
        common.handle_aws_error(err)
