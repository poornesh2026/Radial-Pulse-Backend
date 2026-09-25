from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.errors import ServiceUnavailableError
from app.integrations.storage import ObjectStorage, S3ObjectStorage
from app.jobs.queue import DatabaseJobQueue, JobQueue, SqsJobQueue


def settings_dependency() -> Settings:
    return get_settings()


@lru_cache
def get_storage() -> ObjectStorage:
    settings = get_settings()
    if not settings.s3_assets_bucket:
        raise ServiceUnavailableError("Asset storage is not configured (S3_ASSETS_BUCKET)")
    return S3ObjectStorage(bucket=settings.s3_assets_bucket, region=settings.aws_region)


@lru_cache
def get_job_queue() -> JobQueue:
    settings = get_settings()
    if settings.job_queue_backend == "sqs" and settings.job_queue_url:
        return SqsJobQueue(settings.job_queue_url, settings.aws_region)
    if settings.job_queue_backend == "database":
        return DatabaseJobQueue()
    raise ServiceUnavailableError("Background jobs are not configured (JOB_QUEUE_BACKEND)")
