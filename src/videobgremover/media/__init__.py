"""Media module for video processing and composition."""

from .video import Video
from .backgrounds import Background
from .foregrounds import Foreground
from .composition import Composition, LayerHandle
from .encoders import EncoderProfile
from .remove_bg import RemoveBGOptions, Prefer, Model
from .context import MediaContext, default_context, set_default_context

__all__ = [
    "Video",
    "Background",
    "Foreground",
    "Composition",
    "LayerHandle",
    "EncoderProfile",
    "RemoveBGOptions",
    "Prefer",
    "Model",
    "MediaContext",
    "default_context",
    "set_default_context",
]
