"""Shared test fixtures and configuration."""

import pytest
import tempfile
import os

# Auto-load .env file for tests
try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file automatically
except ImportError:
    pass  # dotenv not available, use regular env vars


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


# Removed mock_ffmpeg fixture - we shouldn't mock FFmpeg in unit tests
# FFmpeg command generation is core business logic that must be tested properly


@pytest.fixture
def sample_video_path(temp_dir):
    """Create a sample video file path (empty file for testing)."""
    video_path = os.path.join(temp_dir, "sample.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake video data")
    return video_path


@pytest.fixture
def sample_image_path(temp_dir):
    """Create a sample image file path (empty file for testing)."""
    image_path = os.path.join(temp_dir, "sample.jpg")
    with open(image_path, "wb") as f:
        f.write(b"fake image data")
    return image_path


# Simple test configuration helpers
def get_test_api_key():
    """Get API key for testing."""
    env = os.getenv("VIDEOBGREMOVER_ENV", "local").lower()

    if env == "prod":
        return os.getenv("VIDEOBGREMOVER_PROD_API_KEY")
    else:
        return os.getenv("VIDEOBGREMOVER_LOCAL_API_KEY")


def get_test_base_url():
    """Get base URL for testing."""
    env = os.getenv("VIDEOBGREMOVER_ENV", "local").lower()

    if env == "prod":
        return os.getenv(
            "VIDEOBGREMOVER_PROD_BASE_URL", "https://api.videobgremover.com"
        )
    else:
        base_url = os.getenv("VIDEOBGREMOVER_LOCAL_BASE_URL", "http://localhost:3000")
        # Ensure we have /api in the path for local development
        # Note: Don't add /v1 here as the API client adds it automatically
        if base_url == "http://localhost:3000":
            base_url = "http://localhost:3000/api"
        return base_url


def get_test_video_sources():
    """Get test video sources."""
    return {
        "local_path": os.getenv("TEST_VIDEO_LOCAL_PATH"),
        "url": os.getenv("TEST_VIDEO_URL"),
    }


def get_test_backgrounds():
    """Get test background assets."""
    return {
        "video": os.getenv("TEST_BACKGROUND_VIDEO", "test_assets/background_video.mp4"),
        "image": os.getenv("TEST_BACKGROUND_IMAGE", "test_assets/background_image.png"),
    }
