from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError
from app.integrations.storage import ObjectStorage, S3ObjectStorage


def settings_dependency() -> Settings:
    return get_settings()


@lru_cache
def get_storage() -> ObjectStorage:
    settings = get_settings()
    if not settings.s3_assets_bucket:
        raise ServiceUnavailableError("Asset storage is not configured (S3_ASSETS_BUCKET)")
    return S3ObjectStorage(bucket=settings.s3_assets_bucket, region=settings.aws_region)
