"""S3 smoke test: ensure bucket -> upload -> list -> download -> (optional) delete.

Confirms your AK/SK can read & write objects in GAMEDAY_BUCKET, creating the
bucket first if it doesn't exist yet.

Usage:
    python s3_sample.py
    python s3_sample.py --keep     # don't delete the test object afterwards
"""

import argparse
import datetime
import os

from botocore.exceptions import ClientError

import common


def ensure_bucket(s3, bucket: str, region: str):
    """Create the bucket if it doesn't already exist."""
    try:
        s3.head_bucket(Bucket=bucket)
        print("      bucket already exists.")
        return
    except ClientError as err:
        code = err.response.get("Error", {}).get("Code", "")
        # 404/NoSuchBucket -> create it. 403 means it exists but isn't ours.
        if code in ("403", "AccessDenied"):
            common.fail(
                f"Bucket '{bucket}' exists but you don't have access to it. "
                "S3 bucket names are globally unique — pick a different "
                "GAMEDAY_BUCKET name in your .env."
            )
        if code not in ("404", "NoSuchBucket", "NoSuchKey"):
            raise  # unexpected error — let the top-level handler report it

    print("      bucket not found, creating it ...")
    # us-east-1 must NOT send a LocationConstraint; every other region must.
    if region == "us-east-1":
        s3.create_bucket(Bucket=bucket)
    else:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    s3.get_waiter("bucket_exists").wait(Bucket=bucket)
    print("      bucket created.")


def main(keep: bool):
    s3 = common.client("s3")
    bucket = common.bucket()
    region = common.region()

    key = "gameday-samples/hello.txt"
    body = (
        "Hello from the game day S3 sample!\n"
        f"Written at {datetime.datetime.utcnow().isoformat()}Z\n"
    ).encode("utf-8")

    print(f"Bucket : {bucket}")
    print(f"Region : {region}\n")

    # 1. Ensure the bucket exists
    print(f"[1/5] Checking bucket '{bucket}' ...")
    ensure_bucket(s3, bucket, region)

    # 2. Upload
    print(f"[2/5] Uploading s3://{bucket}/{key} ...")
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/plain")
    print("      done.")

    # 3. List
    print("[3/5] Listing objects under 'gameday-samples/' ...")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="gameday-samples/")
    for obj in resp.get("Contents", []):
        print(f"      - {obj['Key']} ({obj['Size']} bytes)")

    # 4. Download
    print("[4/5] Downloading the object back ...")
    out_dir = os.path.join(os.path.dirname(__file__), "_downloads")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "hello.txt")
    s3.download_file(bucket, key, out_path)
    with open(out_path, "r", encoding="utf-8") as fh:
        print("      content:")
        for line in fh.read().splitlines():
            print(f"        | {line}")

    # 5. Clean up
    if keep:
        print("[5/5] --keep set, leaving the test object in place.")
    else:
        print("[5/5] Deleting the test object ...")
        s3.delete_object(Bucket=bucket, Key=key)
        print("      done.")

    print("\n✅ S3 sample completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S3 smoke test")
    parser.add_argument(
        "--keep", action="store_true", help="keep the uploaded test object"
    )
    args = parser.parse_args()
    try:
        main(args.keep)
    except Exception as err:  # noqa: BLE001
        common.handle_aws_error(err)
