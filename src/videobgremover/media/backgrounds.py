"""Background classes for video composition with clean separation by type."""

import subprocess
import json
import requests
import os
from mimetypes import guess_extension
from urllib.parse import urlparse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Union, List, Tuple
from abc import ABC, abstractmethod
from .video import Video
from .video_source import VideoSource
from .context import MediaContext, default_context


class BaseBackground(BaseModel, ABC):
    """Abstract base class for all background types."""

    width: int
    height: int
    fps: float
    audio_enabled: bool = False  # Audio disabled by default for backgrounds
    audio_volume: float = 1.0  # Full volume when enabled

    model_config = {"frozen": True}

    @property
    def kind(self) -> str:
        """Get background type from class name."""
        return self.__class__.__name__.lower().replace("background", "")

    @abstractmethod
    def controls_duration(self) -> bool:
        """Whether this background type controls composition duration."""
        pass

    @abstractmethod
    def get_ffmpeg_input_args(
        self,
        canvas_width: int,
        canvas_height: int,
        canvas_fps: float,
        ctx: MediaContext,
    ) -> List[str]:
        """Get FFmpeg input arguments for this background type."""
        pass

    def audio(self, enabled: bool = True, volume: float = 1.0) -> "BaseBackground":
        """
        Set audio properties for this background (immutable).

        Args:
            enabled: Whether to include audio from this background
            volume: Audio volume (0.0 to 1.0, where 1.0 is full volume)

        Returns:
            New background instance with updated audio settings
        """
        # Create new instance with same properties but different audio settings
        new_instance = self.__class__(
            **{
                **self.model_dump(),
                "audio_enabled": enabled,
                "audio_volume": max(0.0, min(1.0, volume)),  # Clamp volume to 0.0-1.0
            }
        )

        # Copy the probed video info if it exists (same pattern as subclip())
        # This is needed for has_audio() to work correctly on the new instance
        if hasattr(self, "_video_info"):
            setattr(new_instance, "_video_info", getattr(self, "_video_info"))

        return new_instance

    def has_audio(self) -> bool:
        """Check if this background type can have audio."""
        return False  # Most backgrounds don't have audio

    def get_audio_input_key(self) -> Optional[str]:
        """Get the input key for audio from this background."""
        if self.has_audio():
            return "background"
        return None


class ColorBackground(BaseBackground):
    """Solid color background."""

    color: str

    def controls_duration(self) -> bool:
        """Color backgrounds let foreground control duration."""
        return False

    def get_ffmpeg_input_args(
        self,
        canvas_width: int,
        canvas_height: int,
        canvas_fps: float,
        ctx: MediaContext,
    ) -> List[str]:
        """Generate color background with FFmpeg lavfi."""
        return [
            "-f",
            "lavfi",
            "-i",
            f"color=c={self.color}:size={canvas_width}x{canvas_height}:rate={canvas_fps}",
        ]


class ImageBackground(BaseBackground):
    """Image background (looped)."""

    source: str

    def controls_duration(self) -> bool:
        """Image backgrounds let foreground control duration."""
        return False

    def get_ffmpeg_input_args(
        self,
        canvas_width: int,
        canvas_height: int,
        canvas_fps: float,
        ctx: MediaContext,
    ) -> List[str]:
        """Loop image as background."""
        return ["-loop", "1", "-i", self.source]


class VideoBackground(BaseBackground, VideoSource):
    """Video background with format detection and decoder support."""

    source: str
    source_trim: Optional[Tuple[float, Optional[float]]] = (
        None  # (start, end) for trimming
    )

    def get_duration(self) -> Optional[float]:
        """Get video duration from probed info."""
        if self._video_info:
            duration = self._video_info.get("duration")
            return float(duration) if duration else None
        return None

    def controls_duration(self) -> bool:
        """Video backgrounds control composition duration."""
        return True

    def has_audio(self) -> bool:
        """Check if this video background actually has audio streams."""
        if hasattr(self, "_video_info") and self._video_info:
            # Check if there are any audio streams in the probed info
            streams = self._video_info.get("streams", [])
            return any(stream.get("codec_type") == "audio" for stream in streams)
        return False

    def get_ffmpeg_input_args(
        self,
        canvas_width: int,
        canvas_height: int,
        canvas_fps: float,
        ctx: MediaContext,
    ) -> List[str]:
        """Get video input with optional trimming - video controls duration."""
        decoder_args = self.get_decoder_args(ctx)

        # Add trimming if specified
        if self.source_trim:
            start, end = self.source_trim
            args = decoder_args + ["-ss", str(start)]
            if end is not None:
                args.extend(["-t", str(end - start)])
            args.extend(["-i", self.source])
            return args
        else:
            # No trimming - video background controls final duration
            return decoder_args + ["-i", self.source]

    def subclip(self, start: float, end: Optional[float] = None) -> "VideoBackground":
        """
        Create a new VideoBackground with source trimming.

        Args:
            start: Start time in source video (seconds)
            end: End time in source video (seconds, None = use until end)

        Returns:
            New VideoBackground instance with trimming applied
        """
        # Create a new instance with the same properties but different trim
        new_bg = VideoBackground(
            source=self.source,
            width=self.width,
            height=self.height,
            fps=self.fps,
            source_trim=(start, end),
            audio_enabled=self.audio_enabled,  # Preserve audio settings
            audio_volume=self.audio_volume,
        )
        # Copy the probed video info
        if hasattr(self, "_video_info"):
            new_bg._video_info = self._video_info
        return new_bg


class EmptyBackground(BaseBackground):
    """Empty/transparent background."""

    def controls_duration(self) -> bool:
        """Empty backgrounds let foreground control duration."""
        return False

    def get_ffmpeg_input_args(
        self,
        canvas_width: int,
        canvas_height: int,
        canvas_fps: float,
        ctx: MediaContext,
    ) -> List[str]:
        """Generate transparent background."""
        return [
            "-f",
            "lavfi",
            "-i",
            f"color=c=black@0.0:size={canvas_width}x{canvas_height}:rate={canvas_fps}",
        ]


def _download_image_to_temp(image_url: str, ctx: MediaContext) -> str:
    """
    Download an image from a URL to a temporary local file.
    Determines file extension from Content-Type header or URL path.

    Args:
        image_url: URL to download image from
        ctx: Media context for temp file creation and logging

    Returns:
        Path to downloaded temporary file
    """
    ctx.logger.debug(f"Downloading image from URL: {image_url}")

    try:
        response = requests.get(image_url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download image from {image_url}: {e}")

    # 1. Determine file extension from Content-Type header (most reliable)
    extension = ".tmp"  # Default temporary extension
    content_type = response.headers.get("Content-Type")
    if content_type:
        # Remove any charset or other parameters
        content_type = content_type.split(";")[0].strip()
        guessed_ext = guess_extension(content_type)
        if guessed_ext:
            extension = guessed_ext
            ctx.logger.debug(f"Guessed extension from Content-Type: {extension}")

    # 2. Fallback: Determine from URL path, ignoring query parameters
    if extension == ".tmp" or extension == ".bin":  # If generic or not found yet
        parsed_url = urlparse(image_url)
        path_without_query = parsed_url.path
        _, path_ext = os.path.splitext(path_without_query)
        if path_ext:
            extension = path_ext
            ctx.logger.debug(f"Extracted extension from URL path: {extension}")

    # 3. Final fallback: If still no good extension, default to .png
    if not extension or extension == ".tmp" or extension == ".bin":
        extension = ".png"
        ctx.logger.debug(f"Defaulting to extension: {extension}")

    # Create a temporary file with the determined extension
    temp_file_path = ctx.temp_path(suffix=extension, prefix="downloaded_image_")

    # Write the downloaded content to the temp file
    try:
        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except IOError as e:
        raise RuntimeError(f"Failed to write downloaded image to {temp_file_path}: {e}")

    ctx.logger.info(f"Downloaded {image_url} to {temp_file_path}")
    return temp_file_path


def _probe_image_dimensions(image_path: str, ctx: MediaContext) -> Tuple[int, int]:
    """Probe image dimensions using ffprobe."""
    try:
        cmd = [
            ctx.ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            image_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to probe image {image_path}: {result.stderr}")

        data = json.loads(result.stdout)
        if not data.get("streams"):
            raise RuntimeError(f"No video streams found in image {image_path}")

        stream = data["streams"][0]
        width = stream.get("width")
        height = stream.get("height")

        if width is None or height is None:
            raise RuntimeError(f"Could not determine dimensions for image {image_path}")

        return int(width), int(height)

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout while probing image {image_path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid ffprobe output for image {image_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to probe image dimensions for {image_path}: {e}")


def _probe_video_dimensions(
    video_path: str, ctx: MediaContext
) -> Tuple[int, int, float]:
    """Probe video dimensions and FPS using ffprobe, accounting for rotation."""
    try:
        cmd = [
            ctx.ffprobe,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,rotation:stream_tags=rotate:format=duration",
            video_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to probe video {video_path}: {result.stderr}")

        data = json.loads(result.stdout)
        if not data.get("streams"):
            raise RuntimeError(f"No video streams found in video {video_path}")

        stream = data["streams"][0]

        # Get basic dimensions
        width = stream.get("width")
        height = stream.get("height")

        if width is None or height is None:
            raise RuntimeError(f"Could not determine video dimensions for {video_path}")

        width, height = int(width), int(height)

        # Check for rotation metadata (actual display dimensions)
        rotation = 0

        # Check stream-level rotation field
        if "rotation" in stream and stream["rotation"]:
            rotation = abs(int(float(stream["rotation"])))

        # Check stream tags for rotate metadata (common in mobile videos)
        elif "tags" in stream and stream["tags"] and "rotate" in stream["tags"]:
            rotation = abs(int(stream["tags"]["rotate"]))

        # If rotated 90° or 270°, swap width and height for actual display dimensions
        if rotation in [90, 270]:
            width, height = height, width
            ctx.logger.debug(
                f"Video has {rotation}° rotation, swapped dimensions to {width}x{height}"
            )

        # Get FPS
        fps = 30.0  # Default fallback
        r_frame_rate = stream.get("r_frame_rate")
        if r_frame_rate and "/" in r_frame_rate:
            try:
                num, den = r_frame_rate.split("/")
                fps = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                pass  # Keep default

        return width, height, fps

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout while probing video {video_path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid ffprobe output for video {video_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to probe video dimensions for {video_path}: {e}")


class Background:
    """Factory class for creating background instances (maintains same public API)."""

    @staticmethod
    def from_color(
        hex_color: str, width: int, height: int, fps: float
    ) -> ColorBackground:
        """
        Create a solid color background.

        Args:
            hex_color: Color in hex format (e.g., "#FF0000")
            width: Background width in pixels
            height: Background height in pixels
            fps: Frame rate

        Returns:
            ColorBackground instance
        """
        return ColorBackground(color=hex_color, width=width, height=height, fps=fps)

    @staticmethod
    def from_image(
        path_or_url: Union[str, HttpUrl],
        fps: float = 30.0,
        ctx: Optional[MediaContext] = None,
    ) -> ImageBackground:
        """
        Create a background from an image with automatic dimension detection.

        Args:
            path_or_url: Path or URL to image file
            fps: Frame rate (default: 30.0)
            ctx: Media context for probing

        Returns:
            ImageBackground instance with actual image dimensions
        """
        ctx = ctx or default_context()
        source = str(path_or_url)

        # Check if source is a URL (starts with http:// or https://)
        is_url = source.startswith("http://") or source.startswith("https://")

        if is_url:
            # Download to temporary local file first (fixes slow FFmpeg -loop with URLs)
            ctx.logger.info(
                "Image background is a URL, downloading to local temp file..."
            )
            source = _download_image_to_temp(source, ctx)
            ctx.logger.info(f"Using local image file: {source}")

        # Auto-detect dimensions from image
        width, height = _probe_image_dimensions(source, ctx)

        return ImageBackground(source=source, width=width, height=height, fps=fps)

    @staticmethod
    def from_video(
        path_or_url_or_video: Union[str, HttpUrl, Video],
        ctx: Optional[MediaContext] = None,
    ) -> VideoBackground:
        """
        Create a background from a video with automatic dimension detection.

        Args:
            path_or_url_or_video: Path, URL, or Video instance
            ctx: Media context for format detection

        Returns:
            VideoBackground instance with actual video dimensions
        """
        ctx = ctx or default_context()

        # Handle Video instance (extract source)
        if isinstance(path_or_url_or_video, Video):
            source = str(path_or_url_or_video.src)
        else:
            source = str(path_or_url_or_video)

        # Auto-detect dimensions from video
        width, height, fps = _probe_video_dimensions(source, ctx)

        # Create video background with actual dimensions
        bg = VideoBackground(
            source=source,
            width=width,
            height=height,
            fps=fps,
            audio_enabled=True,  # Enable audio by default for video backgrounds
        )

        # Probe and store full video format information for decoder support
        bg._probe_and_store(source, ctx)

        return bg

    @staticmethod
    def empty(width: int, height: int, fps: float) -> EmptyBackground:
        """
        Create an empty/transparent background.

        Args:
            width: Background width in pixels
            height: Background height in pixels
            fps: Frame rate

        Returns:
            EmptyBackground instance
        """
        return EmptyBackground(width=width, height=height, fps=fps)
