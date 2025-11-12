"""Client module for VideoBGRemover API."""

from .api import VideoBGRemoverClient
from .models import (
    CreateJobFileUpload,
    CreateJobUrlDownload,
    BackgroundOptions,
    StartJobRequest,
    JobStatus,
    CreditBalance,
    ApiError,
    InsufficientCreditsError,
    JobNotFoundError,
    ProcessingError,
)

__all__ = [
    "VideoBGRemoverClient",
    "CreateJobFileUpload",
    "CreateJobUrlDownload",
    "BackgroundOptions",
    "StartJobRequest",
    "JobStatus",
    "CreditBalance",
    "ApiError",
    "InsufficientCreditsError",
    "JobNotFoundError",
    "ProcessingError",
]
