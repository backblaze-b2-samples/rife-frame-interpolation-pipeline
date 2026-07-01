"""B2 data-access helpers for the interpolation pipeline.

Confined to repo/ alongside b2_client.py so boto3 never leaks into higher
layers. Covers the read/write surface the pipeline needs beyond the file-
management basics in b2_client.py:

- get_object_bytes(key)            -> download a source clip for local processing
- put_json(key, obj) / get_json    -> write/read job manifests
- multipart_upload_file(path, key) -> boto3 managed transfer for LARGE renders
                                       (the write-amplification payload)
- list_keys(prefix)                -> bare key listing for jobs / library / sources
- head_size(key)                   -> byte size for the amplification ratio
- get_object_stats(prefix)         -> object count + total bytes under a prefix
- delete_prefix(prefix)            -> SCOPED bulk delete of a job's own prefix

Every delete is scoped to a renders/<clip_id>/<multiplier>/ prefix — never
bucket-wide — so a delete can never wipe other apps' data sharing the bucket.
"""

import json

from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client

# Managed multipart: switch to multipart above 8 MiB, 8 MiB parts. boto3's
# upload_file handles the create/upload-part/complete dance automatically —
# exactly what a large slow-mo render needs (the write-amplification story).
_MULTIPART = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,
    multipart_chunksize=8 * 1024 * 1024,
    use_threads=True,
)


def get_object_bytes(key: str) -> bytes:
    """Download an object's full body. Raises RuntimeError on S3 failure."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return response["Body"].read()
    except ClientError as e:
        raise RuntimeError(f"B2 get_object failed for '{key}': {e}") from e


def download_to_file(key: str, dest_path: str) -> None:
    """Stream an object to a local path (source clips can be large)."""
    client = get_s3_client()
    try:
        client.download_file(settings.b2_bucket_name, key, dest_path)
    except ClientError as e:
        raise RuntimeError(f"B2 download failed for '{key}': {e}") from e


def multipart_upload_file(path: str, key: str, content_type: str) -> int:
    """Upload a local file to B2 via boto3's managed multipart transfer.

    Returns the uploaded byte size. Used for RENDER OUTPUT, which is large — the
    write-amplification payload boto3 chunks into multipart parts automatically.
    """
    import os

    client = get_s3_client()
    try:
        client.upload_file(
            path,
            settings.b2_bucket_name,
            key,
            ExtraArgs={"ContentType": content_type},
            Config=_MULTIPART,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 multipart upload failed for '{key}': {e}") from e
    return os.path.getsize(path)


def put_json(key: str, obj: dict) -> None:
    """Serialize and store a JSON manifest. Raises RuntimeError on failure."""
    body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e


def get_json(key: str) -> dict | None:
    """Read a JSON manifest. Returns None if the key does not exist."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return json.loads(response["Body"].read())


def list_keys(prefix: str = "", max_keys: int = 1000) -> list[str]:
    """Return bare object keys under a prefix, paginating through all pages."""
    client = get_s3_client()
    keys: list[str] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": prefix,
        "MaxKeys": max_keys,
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            keys.extend(obj["Key"] for obj in response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for prefix '{prefix}': {e}") from e
    return keys


def head_size(key: str) -> int | None:
    """Return an object's byte size, or None if it doesn't exist."""
    client = get_s3_client()
    try:
        response = client.head_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return response["ContentLength"]


def get_object_stats(prefix: str = "") -> dict:
    """Aggregate object count + total bytes under a prefix (paginated)."""
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": prefix,
        "MaxKeys": 1000,
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 stats query failed for '{prefix}': {e}") from e
    return {
        "total_objects": len(contents),
        "total_size_bytes": sum(obj["Size"] for obj in contents),
    }


def delete_prefix(prefix: str) -> int:
    """Delete every object under a prefix. Returns the count deleted.

    SAFETY: callers must pass a job-scoped prefix (renders/<clip_id>/<mult>/).
    Refuses an empty / root / bare render_prefix so a bug can never wipe the
    whole bucket or another job's renders.
    """
    if not prefix or prefix in ("/", settings.render_prefix):
        raise ValueError(f"Refusing unscoped delete for prefix '{prefix}'")

    client = get_s3_client()
    keys = list_keys(prefix)
    deleted = 0
    # delete_objects takes up to 1000 keys per request.
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        if not batch:
            continue
        try:
            client.delete_objects(
                Bucket=settings.b2_bucket_name, Delete={"Objects": batch}
            )
        except ClientError as e:
            raise RuntimeError(f"B2 delete_objects failed for '{prefix}': {e}") from e
        deleted += len(batch)
    return deleted
