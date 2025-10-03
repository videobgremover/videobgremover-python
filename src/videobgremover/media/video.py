"""Video class for loading and processing videos."""

from pydantic import BaseModel, HttpUrl, FilePath
from typing import Union, Optional, Literal, Callable, cast
from urllib.parse import urlparse
from ..client.api import VideoBGRemoverClient
from .remove_bg import RemoveBGOptions
from .foregrounds import Foreground
from .context import MediaContext, default_context


class Video(BaseModel):
    """Video representation that can be loaded from file or URL."""

    kind: Literal["file", "url"]
    src: Union[FilePath, HttpUrl, str]

    @staticmethod
    def open(src: Union[str, FilePath, HttpUrl]) -> "Video":
        """
        Open a video from file path or URL.

        Args:
            src: Video source (file path or URL)

        Returns:
            Video instance (no download occurs yet)
        """
        src_str = str(src)

        # Use proper URL parsing instead of string matching
        try:
            parsed = urlparse(src_str)
            kind = "url" if parsed.scheme in ("http", "https") else "file"
        except Exception:
            # Fallback to original method if URL parsing fails
            kind = (
                "url"
                if (src_str.startswith("http://") or src_str.startswith("https://"))
                else "file"
            )
        return Video(kind=cast(Literal["file", "url"], kind), src=src_str)

    def remove_background(
        self,
        client: "VideoBGRemoverClient",
        options: RemoveBGOptions,
        on_status: Optional[Callable[[str], None]] = None,
        wait_poll_seconds: float = 2.0,
        ctx: Optional[MediaContext] = None,
        webhook_url: Optional[str] = None,
    ) -> Foreground:
        """
        Remove background from video using the API.

        Args:
            client: VideoBGRemover API client
            options: Background removal configuration options
            on_status: Optional callback for status updates
            wait_poll_seconds: Polling interval for job status
            ctx: Optional media context (uses default if not provided)
            webhook_url: Optional webhook URL for job notifications

        Returns:
            Foreground video with transparent background
        """
        # Import here to avoid circular imports
        from ._importer_internal import Importer

        context = ctx or default_context()
        importer = Importer(context)

        return importer.remove_background(
            self, client, options, wait_poll_seconds, on_status, webhook_url
        )
