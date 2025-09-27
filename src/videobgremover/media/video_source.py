"""Base class for video sources (files, URLs, streams) with format detection."""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from pydantic import BaseModel
from .context import MediaContext


class VideoSource(BaseModel):
    """Base class for video sources (files, URLs, streams) with format detection."""

    # Common fields
    _video_info: Optional[Dict[str, Any]] = None
    _source_path: Optional[str] = None  # Can be file path OR URL

    model_config = {"arbitrary_types_allowed": True}

    def _probe_and_store(self, source: str, ctx: MediaContext) -> None:
        """Probe video source (file or URL) once and store info."""
        self._source_path = source
        self._video_info = self._probe_video_info(source, ctx)

    def _probe_video_info(self, source: str, ctx: MediaContext) -> Dict[str, Any]:
        """Probe video source - works with files AND URLs."""
        try:
            cmd = [
                ctx.ffprobe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_entries",
                "stream=codec_name,codec_type,pix_fmt,width,height,duration:format=duration",
                "-probesize",
                "1M",  # Limit probe to 1MB of data
                "-analyzeduration",
                "5M",  # Analyze max 5 seconds of content
                source,
            ]

            # Longer timeout for URLs
            timeout = 10 if self._detect_source_type(source) == "url" else 5
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )

            if result.returncode != 0:
                ctx.logger.warning(f"ffprobe failed for {source}: {result.stderr}")
                return self._fallback_info(source)

            data = json.loads(result.stdout)
            if not data.get("streams"):
                ctx.logger.warning(f"No video streams found in {source}")
                return self._fallback_info(source)

            # Find the first video stream for main properties
            video_stream = None
            for stream in data["streams"]:
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break

            if not video_stream:
                ctx.logger.warning(f"No video streams found in {source}")
                return self._fallback_info(source)

            # Try to get duration from stream first, then format
            duration = video_stream.get("duration")
            if not duration and "format" in data:
                duration = data["format"].get("duration")

            return {
                "codec_name": video_stream.get("codec_name", "unknown"),
                "pix_fmt": video_stream.get("pix_fmt", "unknown"),
                "has_alpha": self._pix_fmt_has_alpha(video_stream.get("pix_fmt")),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "duration": duration,
                "source_type": self._detect_source_type(source),
                "original_source": source,
                "needs_vp9_decoder": self._needs_vp9_decoder(video_stream),
                "streams": data[
                    "streams"
                ],  # Preserve full streams array for audio detection
            }

        except subprocess.TimeoutExpired:
            ctx.logger.warning(f"Video probing timed out for {source}")
            return self._fallback_info(source)
        except Exception as e:
            ctx.logger.warning(f"Video probing failed for {source}: {e}")
            return self._fallback_info(source)

    def _detect_source_type(self, source: str) -> str:
        """Detect if source is file, URL, or stream using proper URL parsing."""
        try:
            parsed = urlparse(source)
            if parsed.scheme in ("http", "https", "ftp"):
                return "url"
            elif parsed.scheme in ("rtsp", "rtmp", "udp", "tcp"):
                return "stream"
            elif (
                parsed.scheme and len(parsed.scheme) > 1
            ):  # Has a real scheme (not Windows drive letter)
                return "stream"  # Default to stream for unknown schemes
            else:
                return "file"  # No scheme or single letter (Windows drive) = local file
        except Exception:
            # Fallback to original string-based detection
            if source.startswith(("http://", "https://", "ftp://")):
                return "url"
            elif source.startswith(("rtsp://", "rtmp://", "udp://", "tcp://")):
                return "stream"
            else:
                return "file"

    def _pix_fmt_has_alpha(self, pix_fmt: Optional[str]) -> bool:
        """Check if pixel format has alpha channel."""
        if not pix_fmt:
            return False
        alpha_formats = {
            "yuva420p",
            "yuva422p",
            "yuva444p",
            "rgba",
            "bgra",
            "argb",
            "abgr",
        }
        return pix_fmt in alpha_formats

    def _needs_vp9_decoder(self, stream: dict) -> bool:
        """Check if stream needs VP9 decoder."""
        codec = stream.get("codec_name", "")
        pix_fmt = stream.get("pix_fmt", "")
        return codec == "vp9" and self._pix_fmt_has_alpha(pix_fmt)

    def _fallback_info(self, source: str) -> Dict[str, Any]:
        """Fallback info when probing fails."""
        source_type = self._detect_source_type(source)

        if source_type == "file":
            ext = Path(source).suffix.lower()
            has_alpha_guess = ext in {".webm", ".mov"}
            needs_vp9_guess = ext == ".webm"
        elif source_type == "url":
            # Extract extension from URL path using proper parsing
            try:
                parsed_url = urlparse(source)
                ext = Path(parsed_url.path).suffix.lower()
                has_alpha_guess = ext in {".webm", ".mov"}
                needs_vp9_guess = ext == ".webm"
            except Exception:
                # Fallback to conservative string matching
                has_alpha_guess = ".webm" in source.lower()
                needs_vp9_guess = ".webm" in source.lower()
        else:
            # For streams, be conservative
            has_alpha_guess = ".webm" in source.lower()
            needs_vp9_guess = ".webm" in source.lower()

        return {
            "codec_name": "unknown",
            "pix_fmt": "unknown",
            "has_alpha": has_alpha_guess,
            "source_type": source_type,
            "original_source": source,
            "needs_vp9_decoder": needs_vp9_guess,
        }

    # Public methods that both Foreground and Background can use
    def needs_webm_decoder(self) -> bool:
        """Check if needs WebM VP9 decoder."""
        if not self._video_info:
            return False
        return self._video_info.get("needs_vp9_decoder", False)

    def get_decoder_args(self, ctx: MediaContext) -> list[str]:
        """Get decoder arguments based on stored video info."""
        if self.needs_webm_decoder() and ctx.check_webm_support():
            ctx.logger.debug(f"Using libvpx-vp9 decoder for: {self._source_path}")
            return ["-c:v", "libvpx-vp9"]
        return []

    def get_video_info(self) -> Optional[Dict[str, Any]]:
        """Get stored video information."""
        return self._video_info

    def is_url(self) -> bool:
        """Check if source is a URL."""
        return bool(self._video_info and self._video_info.get("source_type") == "url")

    def is_file(self) -> bool:
        """Check if source is a local file."""
        return bool(self._video_info and self._video_info.get("source_type") == "file")

    def is_stream(self) -> bool:
        """Check if source is a stream."""
        return bool(
            self._video_info and self._video_info.get("source_type") == "stream"
        )
