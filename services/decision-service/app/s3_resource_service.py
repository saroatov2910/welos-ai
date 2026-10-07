from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - optional until dependencies are installed
    boto3 = None
    BotoCoreError = Exception
    ClientError = Exception


load_dotenv()


def save_add_recode(bucket_name: str, key: str, data: str | bytes) -> None:
    client = get_s3_client()
    client.put_object(Bucket=bucket_name, Key=key, Body=data)


@dataclass(frozen=True)
class S3Settings:
    region: str | None
    access_key_id: str | None
    secret_access_key: str | None
    session_token: str | None


def get_s3_settings() -> S3Settings:
    return S3Settings(
        region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def get_s3_client():
    if boto3 is None:
        raise RuntimeError("boto3 is not installed")

    settings = get_s3_settings()
    client_kwargs: dict[str, Any] = {}

    if settings.region:
        client_kwargs["region_name"] = settings.region

    if settings.access_key_id and settings.secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.access_key_id
        client_kwargs["aws_secret_access_key"] = settings.secret_access_key
        if settings.session_token:
            client_kwargs["aws_session_token"] = settings.session_token

    return boto3.client("s3", **client_kwargs)


def check_s3_connection(bucket_name: str | None = None) -> dict[str, Any]:
    client = get_s3_client()

    try:
        if bucket_name:
            client.head_bucket(Bucket=bucket_name)
            return {"connected": True, "bucket_name": bucket_name}

        client.list_buckets()
        return {"connected": True, "bucket_name": None}
    except (ClientError, BotoCoreError) as exc:
        return {"connected": False, "bucket_name": bucket_name, "error": str(exc)}


def list_s3_files(bucket_name: str, prefix: str = "") -> list[str]:
    client = get_s3_client()
    paginator = client.get_paginator("list_objects_v2")
    keys: list[str] = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix or ""):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if isinstance(key, str):
                keys.append(key)

    return keys
