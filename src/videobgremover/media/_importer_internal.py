"""Internal importer for API orchestration and format handling.

This module is internal and should not be used directly by SDK users.
"""

import os
import subprocess
import mimetypes
import requests
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Callable, Literal, cast
from pydantic import HttpUrl

from .video import Video
from .foregrounds import Foreground
from ..client.api import VideoBGRemoverClient
from ..client.models import (
    CreateJobFileUpload,
    CreateJobUrlDownload,
    StartJobRequest,
    BackgroundOptions,
    JobStatus,
)
from ..core.types import BackgroundType, TransparentFormat
from .remove_bg import RemoveBGOptions, Prefer
from .context import MediaContext


class Importer:
    """Internal importer for handling API operations."""

    def __init__(self, ctx: MediaContext):
        """Initialize with media context."""
        self.ctx = ctx

    def remove_background(
        self,
        video: Video,
        client: VideoBGRemoverClient,
        options: RemoveBGOptions,
        wait_poll_seconds: float,
        on_status: Optional[Callable[[str], None]],
        webhook_url: Optional[str] = None,
    ) -> Foreground:
        """
        Remove background from video using the API.

        Args:
            video: Video to process
            client: API client
            options: Processing options
            wait_poll_seconds: Polling interval
            on_status: Status callback (receives status strings)

        Returns:
            Foreground with transparent background
        """
        # Choose transparent format
        transparent_format = self._choose_format(options)
        self.ctx.logger.info(f"Using transparent format: {transparent_format}")

        # Create job
        job_id = self._create_job(video, client)
        self.ctx.logger.info(f"Created job: {job_id}")

        # Start job with transparent background
        start_request = StartJobRequest(
            background=BackgroundOptions(
                type=BackgroundType.TRANSPARENT,
                transparent_format=TransparentFormat(transparent_format),
            ),
            model=options.model,
            webhook_url=webhook_url,
        )

        client.start_job(job_id, start_request)
        self.ctx.logger.info("Job started, waiting for completion...")

        # Wait for completion
        status = client.wait(
            job_id, poll_seconds=wait_poll_seconds, on_status=on_status
        )

        if status.status != "completed":
            raise RuntimeError(status.message or "Background removal failed")

        self.ctx.logger.info("Job completed, downloading result...")

        # Convert API response to Foreground
        return self._from_endpoint(status)

    def _choose_format(self, options: RemoveBGOptions) -> str:
        """Choose the best transparent format based on options and system capabilities."""
        if options.prefer != Prefer.AUTO:
            return options.prefer.value

        # Auto-detect best format
        try:
            # Check for VP9 encoder and yuva420p pixel format support
            enc_result = subprocess.run(
                [self.ctx.ffmpeg, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            pix_result = subprocess.run(
                [self.ctx.ffmpeg, "-hide_banner", "-pix_fmts"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if (
                enc_result.returncode == 0
                and pix_result.returncode == 0
                and "libvpx-vp9" in enc_result.stdout
                and "yuva420p" in pix_result.stdout
            ):
                self.ctx.logger.debug("WebM VP9 support detected")
                return "webm_vp9"

        except Exception as e:
            self.ctx.logger.warning(f"Error checking FFmpeg capabilities: {e}")

        # Fall back to stacked video (universal compatibility)
        self.ctx.logger.debug("Using stacked video format for universal compatibility")
        return "stacked_video"

    def _create_job(self, video: Video, client: VideoBGRemoverClient) -> str:
        """Create a job for the video."""
        if video.kind == "url" and self._public_url_ok(str(video.src)):
            # Use URL download
            response = client.create_job_url(
                CreateJobUrlDownload(video_url=HttpUrl(str(video.src)))
            )
            return response["id"]
        else:
            # Use file upload
            content_type, _ = mimetypes.guess_type(str(video.src))
            if content_type not in {"video/mp4", "video/mov", "video/webm"}:
                content_type = "video/mp4"  # Default

            # Extract filename from URL or file path using proper parsing
            if video.kind == "url":
                try:
                    parsed_url = urlparse(str(video.src))
                    filename = Path(parsed_url.path).name or "video.mp4"
                except Exception:
                    filename = "video.mp4"  # Fallback
            else:
                filename = Path(str(video.src)).name

            # Create upload job
            response = client.create_job_file(
                CreateJobFileUpload(
                    filename=filename,
                    content_type=cast(
                        Literal["video/mp4", "video/mov", "video/webm"], content_type
                    ),
                )
            )

            # Upload file to signed URL
            self._signed_put(response["upload_url"], str(video.src), content_type)

            return response["id"]

    def _public_url_ok(self, url: str) -> bool:
        """Check if URL is publicly accessible and within size limits."""
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)

            if response.status_code not in (200, 204):
                return False

            # Check content length (1GB limit)
            content_length = response.headers.get("Content-Length")
            if content_length:
                size = int(content_length)
                if size > 1_000_000_000:  # 1GB
                    return False

            return True

        except Exception as e:
            self.ctx.logger.debug(f"URL check failed for {url}: {e}")
            return False

    def _signed_put(self, url: str, file_path: str, content_type: str) -> None:
        """Upload file to signed URL."""
        try:
            with open(file_path, "rb") as f:
                response = requests.put(
                    url,
                    data=f,
                    headers={"Content-Type": content_type},
                    timeout=300,  # 5 minute timeout for uploads
                )
                response.raise_for_status()

        except Exception as e:
            raise RuntimeError(f"Failed to upload file: {e}")

    def _from_endpoint(self, status: JobStatus) -> Foreground:
        """
        Download processed video from API response and create Foreground.

        Args:
            status: Completed job status

        Returns:
            Foreground instance with local file paths
        """
        if not status.processed_video_url:
            raise RuntimeError("No processed video URL in job status")

        # Determine file extension from URL using best practices
        url_str = str(status.processed_video_url)
        suffix = self._get_file_extension_from_url(url_str)

        # Download the processed video
        video_path = self._download_file(url_str, self.ctx.temp_path(suffix=suffix))

        # Handle ZIP files (pro bundle with multiple formats)
        if video_path.endswith(".zip"):
            return self._handle_zip_bundle(video_path)

        # For all other formats, use simple file detection
        return Foreground.from_file(video_path)

    def _download_file(self, url: str, local_path: str) -> str:
        """Download file from URL to local path."""
        try:
            response = requests.get(url, timeout=300)  # 5 minute timeout
            response.raise_for_status()

            with open(local_path, "wb") as f:
                f.write(response.content)

            return local_path

        except Exception as e:
            raise RuntimeError(f"Failed to download {url}: {e}")

    def _get_file_extension_from_url(self, url_str: str) -> str:
        """
        Get file extension from URL using best practices.

        Uses urllib.parse and pathlib to reliably extract file extension,
        avoiding false matches in domain names (e.g., "mov" in "videobgremover.com").

        Args:
            url_str: Full URL string

        Returns:
            File extension with dot (e.g., ".mp4", ".webm", ".mov", ".zip")
        """
        try:
            # Method 1: Parse URL properly using standard library
            parsed_url = urlparse(url_str)
            extension = Path(parsed_url.path).suffix.lower()

            # Validate it's a known extension
            if extension in [".mp4", ".mov", ".webm", ".zip"]:
                return extension

        except Exception:
            pass

        try:
            # Fallback: Extract filename from URL path only
            url_base = url_str.split("?")[0]  # Remove query parameters
            filename = url_base.split("/")[-1]  # Get filename only

            if "." in filename:
                extension = "." + filename.split(".")[-1].lower()
                if extension in [".mp4", ".mov", ".webm", ".zip"]:
                    return extension

        except Exception:
            pass

        # Ultimate fallback for stacked video format
        return ".mp4"

    def _is_stacked_video(self, video_path: str) -> bool:
        """Check if video is in stacked format (height is double width aspect ratio)."""
        try:
            result = subprocess.run(
                [
                    self.ctx.ffprobe,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_streams",
                    "-select_streams",
                    "v:0",
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return False

            import json

            data = json.loads(result.stdout)

            if not data.get("streams"):
                return False

            stream = data["streams"][0]
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))

            # Stacked video should have height roughly double the width
            # (allowing for some tolerance)
            if width > 0 and height > 0:
                aspect_ratio = height / width
                return 1.8 <= aspect_ratio <= 2.2  # Allow some tolerance

            return False

        except Exception as e:
            self.ctx.logger.warning(f"Error checking if video is stacked: {e}")
            return False

    def _handle_zip_bundle(self, zip_path: str) -> Foreground:
        """
        Handle Pro Bundle ZIP containing color.mp4, alpha.mp4, audio.m4a, and manifest.json.

        The pro bundle contains:
        - color.mp4 - Normalized foreground video
        - alpha.mp4 - 8-bit grayscale matte
        - audio.m4a - Audio track (if present)
        - manifest.json - Technical specifications

        Args:
            zip_path: Path to downloaded pro bundle ZIP file

        Returns:
            Foreground instance with RGB + mask pair
        """
        try:
            # Create extraction directory
            import tempfile

            extract_dir = tempfile.mkdtemp(prefix="pro_bundle_", dir=self.ctx.tmp)

            # Extract ZIP contents
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            self.ctx.logger.info(f"Extracted pro bundle to {extract_dir}")

            # Look for the expected pro bundle files
            color_path = os.path.join(extract_dir, "color.mp4")
            alpha_path = os.path.join(extract_dir, "alpha.mp4")
            audio_path = os.path.join(extract_dir, "audio.m4a")

            if not os.path.exists(color_path):
                raise RuntimeError("color.mp4 not found in pro bundle")

            if not os.path.exists(alpha_path):
                raise RuntimeError("alpha.mp4 not found in pro bundle")

            # Check for audio file (optional)
            if os.path.exists(audio_path):
                self.ctx.logger.info(
                    "Found color.mp4, alpha.mp4, and audio.m4a in pro bundle"
                )
                return Foreground.from_video_and_mask(
                    color_path, alpha_path, audio_path
                )
            else:
                self.ctx.logger.info(
                    "Found color.mp4 and alpha.mp4 in pro bundle (no audio)"
                )
                return Foreground.from_video_and_mask(color_path, alpha_path)

        except Exception as e:
            raise RuntimeError(f"Failed to process pro bundle: {e}")
