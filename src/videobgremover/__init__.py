"""VideoBGRemover Python SDK - Remove video backgrounds with AI and compose videos with FFmpeg."""

from .client import VideoBGRemoverClient
from .media import (
    Video,
    Background,
    Foreground,
    Composition,
    EncoderProfile,
    RemoveBGOptions,
    Prefer,
    MediaContext,
    default_context,
    set_default_context,
)
from .core import (
    BackgroundType,
    TransparentFormat,
    ModelSize,
    Anchor,
    SizeMode,
)

__version__ = "0.1.0"

__all__ = [
    "VideoBGRemoverClient",
    "Video",
    "Background",
    "Foreground",
    "Composition",
    "EncoderProfile",
    "RemoveBGOptions",
    "Prefer",
    "MediaContext",
    "default_context",
    "set_default_context",
    "BackgroundType",
    "TransparentFormat",
    "ModelSize",
    "Anchor",
    "SizeMode",
]
