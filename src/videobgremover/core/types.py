"""Core types and enums for the VideoBGRemover SDK."""

from enum import Enum
from typing import Optional, Callable

# Status callback type: receives status strings ("created", "uploaded", "processing", "completed")
StatusCb = Optional[Callable[[str], None]]

# Legacy alias for backward compatibility
ProgressCb = StatusCb


class BackgroundType(str, Enum):
    """Background type for video processing."""

    COLOR = "color"
    TRANSPARENT = "transparent"


class TransparentFormat(str, Enum):
    """Transparent video format options."""

    WEBM_VP9 = "webm_vp9"
    MOV_PRORES = "mov_prores"
    PNG_SEQUENCE = "png_sequence"
    PRO_BUNDLE = "pro_bundle"
    STACKED_VIDEO = "stacked_video"


class Anchor(str, Enum):
    """Anchor positions for video overlay."""

    CENTER = "center"
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    CENTER_LEFT = "center-left"
    CENTER_RIGHT = "center-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"


class SizeMode(str, Enum):
    """Size modes for video scaling."""

    CONTAIN = "contain"  # Fit within bounds, maintain aspect ratio
    COVER = "cover"  # Fill bounds, maintain aspect ratio, may crop
    PX = "px"  # Exact pixel dimensions
    CANVAS_PERCENT = "canvas_percent"  # Percentage of canvas size
    SCALE = "scale"  # Scale factor relative to original video size
    FIT_WIDTH = "fit_width"  # Scale to match canvas width
    FIT_HEIGHT = "fit_height"  # Scale to match canvas height
