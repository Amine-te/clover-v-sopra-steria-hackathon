"""Verify AWS profile credentials and identity."""
import pytest

pytestmark = pytest.mark.aws_live


def test_aws_identity(aws_session):
    identity = aws_session.client("sts").get_caller_identity()
    assert identity["Account"]
    assert identity["Arn"].startswith("arn:aws:")
    print(f"AWS identity: {identity['Arn']}")
