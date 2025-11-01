"""VideoBGRemover Python SDK - Remove video backgrounds with AI and compose videos with FFmpeg."""

from .__version__ import __version__
from .client import VideoBGRemoverClient
from .media import (
    Video,
    Background,
    Foreground,
    Composition,
    EncoderProfile,
    RemoveBGOptions,
    Prefer,
    Model,
    MediaContext,
    default_context,
    set_default_context,
)
from .core import (
    BackgroundType,
    TransparentFormat,
    Anchor,
    SizeMode,
)


__all__ = [
    "__version__",
    "VideoBGRemoverClient",
    "Video",
    "Background",
    "Foreground",
    "Composition",
    "EncoderProfile",
    "RemoveBGOptions",
    "Prefer",
    "Model",
    "MediaContext",
    "default_context",
    "set_default_context",
    "BackgroundType",
    "TransparentFormat",
    "Anchor",
    "SizeMode",
]
