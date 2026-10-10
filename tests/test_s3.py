"""Upload/read/delete a uniquely named object in an existing test bucket."""
import uuid
import pytest

pytestmark = pytest.mark.aws_live


def test_s3_roundtrip(aws_session, bucket):
    s3 = aws_session.client("s3")
    key = f"clover-aws-tests/{uuid.uuid4().hex}.txt"
    payload = b"Clover AWS integration test\n"
    uploaded = False
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=payload, ContentType="text/plain")
        uploaded = True
        response = s3.get_object(Bucket=bucket, Key=key)
        assert response["Body"].read() == payload
    finally:
        if uploaded:
            s3.delete_object(Bucket=bucket, Key=key)
