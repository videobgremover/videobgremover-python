"""Background removal options and configuration."""

from enum import Enum
from pydantic import BaseModel


class Prefer(str, Enum):
    """Preferred transparent format for background removal (matches API transparent_format values)."""

    AUTO = "auto"
    WEBM_VP9 = "webm_vp9"
    MOV_PRORES = "mov_prores"
    PNG_SEQUENCE = "png_sequence"
    STACKED_VIDEO = "stacked_video"
    PRO_BUNDLE = "pro_bundle"

    # Backward compatibility aliases (deprecated)
    WEBM = "webm_vp9"  # Deprecated: use WEBM_VP9
    PRORES = "mov_prores"  # Deprecated: use MOV_PRORES
    PNGSEQ = "png_sequence"  # Deprecated: use PNG_SEQUENCE
    STACKED = "stacked_video"  # Deprecated: use STACKED_VIDEO


class Model(str, Enum):
    """AI model for background removal."""

    VIDEOBGREMOVER_ORIGINAL = "videobgremover-original"
    VIDEOBGREMOVER_LIGHT = "videobgremover-light"


class RemoveBGOptions(BaseModel):
    """Options for background removal processing."""

    prefer: Prefer = Prefer.AUTO
    model: str | None = None
