"""Media runtime context for FFmpeg operations and temporary file management."""

import tempfile
import logging
import os
import subprocess
from typing import Optional


class MediaContext:
    """Context for media operations with FFmpeg and temporary file management."""

    def __init__(
        self,
        ffmpeg: str = "ffmpeg",
        ffprobe: str = "ffprobe",
        tmp_root: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize media context.

        Args:
            ffmpeg: Path to ffmpeg binary
            ffprobe: Path to ffprobe binary
            tmp_root: Root directory for temporary files
            logger: Logger instance for debugging
        """
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.logger = logger or logging.getLogger(__name__)

        # Create temporary directory
        self._tmp = tempfile.TemporaryDirectory(dir=tmp_root)
        self.tmp = self._tmp.name

        # Verify FFmpeg is available
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        """Verify that FFmpeg binaries are available."""
        try:
            # Check ffmpeg
            result = subprocess.run(
                [self.ffmpeg, "-version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg not working: {result.stderr}")

            # Check ffprobe
            result = subprocess.run(
                [self.ffprobe, "-version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"FFprobe not working: {result.stderr}")

            self.logger.debug("FFmpeg binaries verified successfully")

        except FileNotFoundError as e:
            raise RuntimeError(f"FFmpeg not found. Please install FFmpeg: {e}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg verification timed out")

    def temp_path(self, suffix: str = "", prefix: str = "vbr_") -> str:
        """
        Generate a temporary file path.

        Args:
            suffix: File suffix/extension (e.g., ".mp4")
            prefix: File prefix

        Returns:
            Temporary file path
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=self.tmp)
        os.close(fd)  # Close file descriptor, we just need the path
        return path

    def check_webm_support(self) -> bool:
        """
        Check if FFmpeg supports WebM VP9 alpha channels.

        Returns:
            True if libvpx-vp9 decoder is available
        """
        try:
            result = subprocess.run(
                [self.ffmpeg, "-decoders"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                has_libvpx_vp9 = "libvpx-vp9" in result.stdout
                self.logger.debug(f"WebM VP9 support: {has_libvpx_vp9}")
                return has_libvpx_vp9
            else:
                self.logger.warning("Could not check WebM support")
                return False

        except Exception as e:
            self.logger.warning(f"Error checking WebM support: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            self._tmp.cleanup()
            self.logger.debug("Temporary files cleaned up")
        except Exception as e:
            self.logger.warning(f"Error cleaning up temporary files: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# Global default context
_DEFAULT_CTX: Optional[MediaContext] = None


def default_context() -> MediaContext:
    """
    Get the default media context.

    Returns:
        Default MediaContext instance
    """
    global _DEFAULT_CTX
    if _DEFAULT_CTX is None:
        _DEFAULT_CTX = MediaContext()
    return _DEFAULT_CTX


def set_default_context(ctx: MediaContext) -> None:
    """
    Set the default media context.

    Args:
        ctx: MediaContext to use as default
    """
    global _DEFAULT_CTX
    _DEFAULT_CTX = ctx
