"""
AWS S3 Service
Handles bucket creation, listing, and deletion via boto3
"""

import boto3
import os
import random
import string
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

AWS_ACCESS_KEY     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY     = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# ── Client & region caches (created once, reused forever) ────────────────────
_client_cache: dict = {}          # (access_key, region) -> boto3 client
_region_cache: dict = {}          # bucket_name -> region string
_probe_cache:  dict = {}          # access_key -> probe client


def _get_probe_client(access_key: str = None, secret_key: str = None):
    """Return a singleton probe client used for region detection."""
    ak = access_key or AWS_ACCESS_KEY
    sk = secret_key or AWS_SECRET_KEY
    if ak not in _probe_cache:
        _probe_cache[ak] = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
        )
    return _probe_cache[ak]


def get_s3_client(region: str = "us-east-1", access_key: str = None, secret_key: str = None):
    """Return a cached boto3 S3 client pinned to the correct regional endpoint."""
    ak = access_key or AWS_ACCESS_KEY
    sk = secret_key or AWS_SECRET_KEY
    cache_key = (ak, region)
    if cache_key not in _client_cache:
        if region == "us-east-1":
            endpoint_url = "https://s3.amazonaws.com"
        else:
            endpoint_url = f"https://s3.{region}.amazonaws.com"
        _client_cache[cache_key] = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=ak,
            aws_secret_access_key=sk
        )
    return _client_cache[cache_key]


def create_s3_bucket(
    bucket_name: str,
    region: str,
    access_level: str,
    versioning: bool,
    tags: dict,
    owner_email: str,
    access_key: str = None,
    secret_key: str = None,
) -> dict:
    """
    Create an S3 bucket with optional versioning, tags, and ACL.
    - If you already own the bucket → treat as success.
    - If name is globally taken → auto-retry with a random suffix (up to 3 times).
    Returns dict with success flag, bucket URL, or error.
    """
    MAX_RETRIES = 3
    original_name = bucket_name

    for attempt in range(MAX_RETRIES + 1):
        try:
            client = get_s3_client(region, access_key=access_key, secret_key=secret_key)

            create_params = {"Bucket": bucket_name}
            if region != "us-east-1":
                create_params["CreateBucketConfiguration"] = {
                    "LocationConstraint": region
                }

            client.create_bucket(**create_params)

            warnings = []

            # ── ACL / Public Access ──────────────────────────
            if access_level == "public-read":
                try:
                    client.put_public_access_block(
                        Bucket=bucket_name,
                        PublicAccessBlockConfiguration={
                            "BlockPublicAcls": False,
                            "IgnorePublicAcls": False,
                            "BlockPublicPolicy": False,
                            "RestrictPublicBuckets": False,
                        }
                    )
                    client.put_bucket_acl(Bucket=bucket_name, ACL="public-read")
                except ClientError as acl_err:
                    warnings.append(f"ACL skipped: {acl_err.response['Error']['Code']}")

            # ── Versioning ───────────────────────────────────
            if versioning:
                try:
                    client.put_bucket_versioning(
                        Bucket=bucket_name,
                        VersioningConfiguration={"Status": "Enabled"}
                    )
                except ClientError as ver_err:
                    warnings.append(f"Versioning skipped: {ver_err.response['Error']['Code']}")

            # ── Tags ─────────────────────────────────────────
            try:
                default_tags = {
                    "CreatedBy": "AWS-AutoNation",
                    "Owner": owner_email,
                    "CreatedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                }
                merged_tags = {**default_tags, **(tags or {})}
                client.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={
                        "TagSet": [{"Key": k, "Value": v} for k, v in merged_tags.items()]
                    }
                )
            except ClientError as tag_err:
                warnings.append(f"Tags skipped: {tag_err.response['Error']['Code']}")

            if bucket_name != original_name:
                warnings.append(f"Renamed from '{original_name}' (name was taken)")

            # ── Bucket URL ───────────────────────────────────
            if region == "us-east-1":
                bucket_url = f"https://{bucket_name}.s3.amazonaws.com"
            else:
                bucket_url = f"https://{bucket_name}.s3.{region}.amazonaws.com"

            return {
                "success": True,
                "bucket_name": bucket_name,
                "bucket_url": bucket_url,
                "region": region,
                "warnings": warnings
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            # You already own this bucket → treat as success
            if error_code == "BucketAlreadyOwnedByYou":
                if region == "us-east-1":
                    bucket_url = f"https://{bucket_name}.s3.amazonaws.com"
                else:
                    bucket_url = f"https://{bucket_name}.s3.{region}.amazonaws.com"
                return {
                    "success": True,
                    "bucket_name": bucket_name,
                    "bucket_url": bucket_url,
                    "region": region,
                    "warnings": ["Bucket already owned by you — reusing existing bucket."]
                }

            # Globally taken by someone else → retry with random suffix
            if error_code == "BucketAlreadyExists" and attempt < MAX_RETRIES:
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                # Truncate base name if needed (S3 max 63 chars)
                base = original_name[:56]
                bucket_name = f"{base}-{suffix}"
                continue

            # All retries exhausted or different error
            error_map = {
                "BucketAlreadyExists":          f"Bucket name '{original_name}' is taken globally. Tried {MAX_RETRIES} random suffixes but all failed.",
                "InvalidBucketName":            "Invalid bucket name. Use lowercase letters, numbers, and hyphens.",
                "TooManyBuckets":               "AWS account bucket limit (100) reached.",
                "AuthFailure":                  "AWS credentials are invalid or expired.",
                "AllAccessDisabled":            "AWS account access is disabled.",
            }
            return {"success": False, "error": error_map.get(error_code, str(e))}

        except NoCredentialsError:
            return {"success": False, "error": "AWS credentials not configured. Check your .env file."}

        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Failed to create bucket '{original_name}' after retries."}


def list_user_buckets(access_key: str = None, secret_key: str = None) -> dict:
    """Return all S3 buckets in the AWS account."""
    try:
        client = get_s3_client(access_key=access_key, secret_key=secret_key)
        response = client.list_buckets()
        buckets = [
            {
                "name": b["Name"],
                "created_at": b["CreationDate"].strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            for b in response.get("Buckets", [])
        ]
        return {"success": True, "count": len(buckets), "buckets": buckets}

    except NoCredentialsError:
        return {"success": False, "error": "AWS credentials not configured."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _detect_bucket_region(bucket_name: str, access_key: str = None, secret_key: str = None) -> str:
    """
    Reliably detect a bucket's region — cached so each bucket is probed only once.
    Uses head_bucket against the global endpoint (AWS always returns
    the x-amz-bucket-region header even on redirects).
    """
    if bucket_name in _region_cache:
        return _region_cache[bucket_name]

    probe = _get_probe_client(access_key=access_key, secret_key=secret_key)
    try:
        resp = probe.head_bucket(Bucket=bucket_name)
        region = resp["ResponseMetadata"]["HTTPHeaders"].get("x-amz-bucket-region", "")
        if region:
            _region_cache[bucket_name] = region
            return region
    except ClientError as e:
        region = e.response.get("ResponseMetadata", {}).get("HTTPHeaders", {}).get(
            "x-amz-bucket-region", ""
        )
        if region:
            _region_cache[bucket_name] = region
            return region

    # Final fallback: get_bucket_location
    try:
        loc = probe.get_bucket_location(Bucket=bucket_name)
        region = loc.get("LocationConstraint") or "us-east-1"
        _region_cache[bucket_name] = region
        return region
    except Exception:
        return AWS_DEFAULT_REGION or "us-east-1"


def delete_s3_bucket(bucket_name: str, region: str = "", access_key: str = None, secret_key: str = None) -> dict:
    """
    Delete an S3 bucket. Auto-detects region if not provided.
    Empties the bucket (objects + versions) before deleting.
    """
    try:
        # Step 1: always detect region reliably — never trust caller-supplied region
        # (caller may pass "us-east-1" default even for ap-south-1 buckets)
        region = _detect_bucket_region(bucket_name, access_key=access_key, secret_key=secret_key)

        client = get_s3_client(region, access_key=access_key, secret_key=secret_key)

        # Step 2: delete all versioned objects and delete markers
        try:
            ver_paginator = client.get_paginator("list_object_versions")
            delete_list = []
            for page in ver_paginator.paginate(Bucket=bucket_name):
                for obj in page.get("Versions", []):
                    delete_list.append({"Key": obj["Key"], "VersionId": obj["VersionId"]})
                for obj in page.get("DeleteMarkers", []):
                    delete_list.append({"Key": obj["Key"], "VersionId": obj["VersionId"]})
            for i in range(0, len(delete_list), 1000):
                client.delete_objects(Bucket=bucket_name, Delete={"Objects": delete_list[i:i+1000]})
        except ClientError:
            pass  # versioning disabled – nothing to purge

        # Step 3: delete any remaining non-versioned objects
        try:
            obj_paginator = client.get_paginator("list_objects_v2")
            for page in obj_paginator.paginate(Bucket=bucket_name):
                objects = [{"Key": o["Key"]} for o in page.get("Contents", [])]
                if objects:
                    client.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})
        except ClientError:
            pass

        # Step 4: delete the bucket itself
        client.delete_bucket(Bucket=bucket_name)

        return {"success": True, "message": f"Bucket '{bucket_name}' deleted successfully."}

    except ClientError as e:
        return {"success": False, "error": str(e)}
    except NoCredentialsError:
        return {"success": False, "error": "AWS credentials not configured."}
    except Exception as e:
        return {"success": False, "error": str(e)}
