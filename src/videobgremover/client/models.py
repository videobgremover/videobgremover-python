"""Pydantic models for VideoBGRemover API client."""

from pydantic import BaseModel, HttpUrl, constr, field_validator
from typing import Optional, Literal, TypeAlias, Annotated
from ..core.types import BackgroundType, TransparentFormat

# Hex color pattern for validation - using Annotated for proper type alias
HexColor: TypeAlias = Annotated[
    str, constr(pattern=r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
]


class CreateJobFileUpload(BaseModel):
    """Request model for creating a job with file upload."""

    filename: str
    content_type: Literal["video/mp4", "video/mov", "video/webm"]


class CreateJobUrlDownload(BaseModel):
    """Request model for creating a job with URL download."""

    video_url: HttpUrl


class BackgroundOptions(BaseModel):
    """Background options for video processing."""

    type: BackgroundType
    color: Optional[HexColor] = None
    transparent_format: Optional[TransparentFormat] = None

    @field_validator("color")
    @classmethod
    def need_color_for_color(cls, v, info):
        """Validate that color is provided when type is 'color'."""
        if (
            hasattr(info, "data")
            and info.data.get("type") == BackgroundType.COLOR
            and not v
        ):
            raise ValueError("color required when type='color'")
        return v

    @field_validator("transparent_format")
    @classmethod
    def need_fmt_for_transparent(cls, v, info):
        """Validate that transparent_format is provided when type is 'transparent'."""
        if (
            hasattr(info, "data")
            and info.data.get("type") == BackgroundType.TRANSPARENT
            and not v
        ):
            raise ValueError("transparent_format required when type='transparent'")
        return v

    def model_post_init(self, __context):
        """Post-initialization validation."""
        if self.type == BackgroundType.COLOR and not self.color:
            raise ValueError("color required when type='color'")
        if self.type == BackgroundType.TRANSPARENT and not self.transparent_format:
            raise ValueError("transparent_format required when type='transparent'")


class StartJobRequest(BaseModel):
    """Request model for starting a job."""

    format: Literal["mp4"] = "mp4"
    model: Optional[str] = None
    background: Optional[BackgroundOptions] = None
    webhook_url: Optional[str] = None


class JobStatus(BaseModel):
    """Job status response model."""

    id: str
    status: Literal["created", "uploaded", "processing", "completed", "failed"]
    filename: str
    created_at: str
    length_seconds: Optional[float] = None
    thumbnail_url: Optional[HttpUrl] = None
    transparent_thumbnail_url: Optional[HttpUrl] = None
    processed_video_url: Optional[HttpUrl] = None
    processed_mask_url: Optional[HttpUrl] = None
    message: Optional[str] = None
    background: Optional[BackgroundOptions] = None
    output_format: Optional[str] = None
    export_id: Optional[str] = None


class CreditBalance(BaseModel):
    """Credit balance response model."""

    user_id: str
    total_credits: float
    remaining_credits: float
    used_credits: float


class ApiError(Exception):
    """Custom exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class InsufficientCreditsError(ApiError):
    """Exception raised when user has insufficient credits."""

    pass


class JobNotFoundError(ApiError):
    """Exception raised when job is not found."""

    pass


class ProcessingError(ApiError):
    """Exception raised when video processing fails."""

    pass
