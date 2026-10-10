# Clover AWS integration tests

Copy the `tests/` folder and `pytest.ini` into your repository root, alongside `pyproject.toml` and `samples/`.

```fish
uv add --dev pytest
uv add boto3
set -gx AWS_PROFILE hackathon
set -gx AWS_REGION us-east-1
# Use an already-authorized S3 bucket for S3 and Transcribe tests:
set -gx GAMEDAY_BUCKET YOUR_EXISTING_BUCKET
```

Run without making any live AWS requests:

```fish
uv run pytest -v
```

Run individual **live** integration tests:

```fish
uv run pytest -v -s --aws-live tests/test_aws_identity.py
uv run pytest -v -s --aws-live tests/test_bedrock.py
uv run pytest -v -s --aws-live tests/test_s3.py
uv run pytest -v -s --aws-live tests/test_textract.py
uv run pytest -v -s --aws-live tests/test_transcribe.py
```

Or run all live tests with `uv run pytest -v -s --aws-live`.

The Transcribe test uses `samples/audio/Enregistrement.mp3`; Textract uses `samples/OCR/ordonnance.png`. Override with `TEST_AUDIO_PATH` / `TEST_DOCUMENT_PATH` environment variables. For Bedrock, change `BEDROCK_TEST_MODEL` to a permitted model ID if necessary. All tests are skipped unless `--aws-live` is passed. Most tests incur potential AWS charges. The S3 and Transcribe tests create temporary resources in the existing bucket and attempt cleanup afterward. If a test is interrupted, check `clover-aws-tests/` in S3 and Transcribe jobs beginning `clover-aws-test-` and remove only those test resources.

Permission errors reflect IAM policies or resource access and are not fixed by Python configuration alone. These tests do not create IAM users, policies, or S3 buckets. The OCR sample looks like a prescription: use synthetic/redacted images for testing rather than real personal medical data.
