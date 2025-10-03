"""Tests for the VideoBGRemover API client."""

import pytest
import responses
from unittest.mock import patch
from videobgremover.client import (
    VideoBGRemoverClient,
    CreateJobFileUpload,
    CreateJobUrlDownload,
    StartJobRequest,
    BackgroundOptions,
    JobStatus,
    ApiError,
    InsufficientCreditsError,
    JobNotFoundError,
)
from videobgremover.core import BackgroundType, TransparentFormat


class TestVideoBGRemoverClient:
    """Test the API client."""

    def test_init(self):
        """Test client initialization."""
        client = VideoBGRemoverClient("test_key")
        assert client.base_url == "https://api.videobgremover.com"
        assert client.session.headers["X-Api-Key"] == "test_key"
        assert "videobgremover-python" in client.session.headers["User-Agent"]

    def test_init_custom_url(self):
        """Test client with custom base URL."""
        client = VideoBGRemoverClient("test_key", base_url="https://custom.api.com/")
        assert client.base_url == "https://custom.api.com"

    @responses.activate
    def test_create_job_file_success(self):
        """Test successful file job creation."""
        responses.add(
            responses.POST,
            "https://api.videobgremover.com/v1/jobs",
            json={
                "id": "job_123",
                "upload_url": "https://storage.googleapis.com/signed-url",
                "expires_at": "2024-01-01T12:00:00Z",
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        req = CreateJobFileUpload(filename="test.mp4", content_type="video/mp4")

        result = client.create_job_file(req)

        assert result["id"] == "job_123"
        assert "upload_url" in result

    @responses.activate
    def test_create_job_url_success(self):
        """Test successful URL job creation."""
        responses.add(
            responses.POST,
            "https://api.videobgremover.com/v1/jobs",
            json={
                "id": "job_456",
                "status": "uploaded",
                "message": "Video downloaded successfully",
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        req = CreateJobUrlDownload(video_url="https://example.com/video.mp4")

        result = client.create_job_url(req)

        assert result["id"] == "job_456"
        assert result["status"] == "uploaded"

    @responses.activate
    def test_start_job_success(self):
        """Test successful job start."""
        responses.add(
            responses.POST,
            "https://api.videobgremover.com/v1/jobs/job_123/start",
            json={
                "id": "job_123",
                "status": "processing",
                "credits_used": 10,
                "video_length_seconds": 10.0,
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        req = StartJobRequest(
            background=BackgroundOptions(
                type=BackgroundType.TRANSPARENT,
                transparent_format=TransparentFormat.WEBM_VP9,
            ),
        )

        result = client.start_job("job_123", req)

        assert result["id"] == "job_123"
        assert result["status"] == "processing"
        assert result["credits_used"] == 10

    @responses.activate
    def test_status_success(self):
        """Test successful status check."""
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/jobs/job_123/status",
            json={
                "id": "job_123",
                "status": "completed",
                "filename": "test.mp4",
                "created_at": "2024-01-01T10:00:00Z",
                "length_seconds": 10.0,
                "processed_video_url": "https://example.com/processed.webm",
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        status = client.status("job_123")

        assert isinstance(status, JobStatus)
        assert status.id == "job_123"
        assert status.status == "completed"
        assert status.length_seconds == 10.0

    @responses.activate
    def test_wait_success(self):
        """Test successful wait for completion."""
        # First call: processing
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/jobs/job_123/status",
            json={
                "id": "job_123",
                "status": "processing",
                "filename": "test.mp4",
                "created_at": "2024-01-01T10:00:00Z",
            },
            status=200,
        )

        # Second call: completed
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/jobs/job_123/status",
            json={
                "id": "job_123",
                "status": "completed",
                "filename": "test.mp4",
                "created_at": "2024-01-01T10:00:00Z",
                "processed_video_url": "https://example.com/processed.webm",
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")

        with patch("time.sleep"):  # Speed up test
            status = client.wait("job_123", poll_seconds=0.1)

        assert status.status == "completed"

    @responses.activate
    def test_wait_timeout(self):
        """Test wait timeout."""
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/jobs/job_123/status",
            json={
                "id": "job_123",
                "status": "processing",
                "filename": "test.mp4",
                "created_at": "2024-01-01T10:00:00Z",
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")

        with patch("time.sleep"):  # Speed up test
            with pytest.raises(TimeoutError):
                client.wait("job_123", poll_seconds=0.1, timeout=0.2)

    @responses.activate
    def test_credits_success(self):
        """Test successful credits check."""
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/credits",
            json={
                "user_id": "user_123",
                "total_credits": 100.0,
                "remaining_credits": 50.0,
                "used_credits": 50.0,
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        credits = client.credits()

        assert credits.user_id == "user_123"
        assert credits.total_credits == 100.0
        assert credits.remaining_credits == 50.0

    @responses.activate
    def test_api_error_401(self):
        """Test 401 authentication error."""
        responses.add(
            responses.GET, "https://api.videobgremover.com/v1/credits", status=401
        )

        client = VideoBGRemoverClient("test_key")

        with pytest.raises(ApiError) as exc_info:
            client.credits()

        assert "Invalid API key" in str(exc_info.value)
        assert exc_info.value.status_code == 401

    @responses.activate
    def test_api_error_402(self):
        """Test 402 insufficient credits error."""
        responses.add(
            responses.POST,
            "https://api.videobgremover.com/v1/jobs/job_123/start",
            json={"error": "Insufficient credits"},
            status=402,
        )

        client = VideoBGRemoverClient("test_key")

        with pytest.raises(InsufficientCreditsError) as exc_info:
            client.start_job("job_123")

        assert exc_info.value.status_code == 402

    @responses.activate
    def test_api_error_404(self):
        """Test 404 job not found error."""
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/jobs/nonexistent/status",
            json={"error": "Job not found"},
            status=404,
        )

        client = VideoBGRemoverClient("test_key")

        with pytest.raises(JobNotFoundError) as exc_info:
            client.status("nonexistent")

        assert exc_info.value.status_code == 404


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_background_options_color_validation(self):
        """Test background options validation for color type."""
        # Valid color background
        bg = BackgroundOptions(type=BackgroundType.COLOR, color="#FF0000")
        assert bg.type == BackgroundType.COLOR
        assert bg.color == "#FF0000"

        # Invalid: color type without color
        with pytest.raises(ValueError, match="color required"):
            BackgroundOptions(type=BackgroundType.COLOR)

    def test_background_options_transparent_validation(self):
        """Test background options validation for transparent type."""
        # Valid transparent background
        bg = BackgroundOptions(
            type=BackgroundType.TRANSPARENT,
            transparent_format=TransparentFormat.WEBM_VP9,
        )
        assert bg.type == BackgroundType.TRANSPARENT
        assert bg.transparent_format == TransparentFormat.WEBM_VP9

        # Invalid: transparent type without format
        with pytest.raises(ValueError, match="transparent_format required"):
            BackgroundOptions(type=BackgroundType.TRANSPARENT)

    def test_create_job_file_upload(self):
        """Test file upload model."""
        job = CreateJobFileUpload(filename="test.mp4", content_type="video/mp4")
        assert job.filename == "test.mp4"
        assert job.content_type == "video/mp4"

    def test_start_job_request_defaults(self):
        """Test start job request defaults."""
        req = StartJobRequest()
        assert req.format == "mp4"
        assert req.background is None

    @responses.activate
    def test_start_job_with_webhook_url(self):
        """Test starting job with webhook_url."""
        responses.add(
            responses.POST,
            "https://api.videobgremover.com/v1/jobs/job_123/start",
            json={
                "id": "job_123",
                "status": "processing",
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        req = StartJobRequest(
            webhook_url="https://example.com/webhooks",
            background=BackgroundOptions(
                type=BackgroundType.TRANSPARENT,
                transparent_format=TransparentFormat.WEBM_VP9,
            ),
        )

        result = client.start_job("job_123", req)

        assert result["id"] == "job_123"
        assert result["status"] == "processing"

        # Verify webhook_url was sent in request
        assert len(responses.calls) == 1
        import json

        request_body = json.loads(responses.calls[0].request.body)
        assert request_body["webhook_url"] == "https://example.com/webhooks"

    @responses.activate
    def test_webhook_deliveries(self):
        """Test getting webhook delivery history."""
        responses.add(
            responses.GET,
            "https://api.videobgremover.com/v1/webhooks/deliveries?video_id=job_123",
            json={
                "video_id": "job_123",
                "total_deliveries": 2,
                "deliveries": [
                    {
                        "event_type": "job.started",
                        "webhook_url": "https://example.com/webhooks",
                        "attempt_number": 1,
                        "delivery_status": "delivered",
                        "http_status_code": 200,
                        "error_message": None,
                        "scheduled_at": "2025-10-02T10:00:00Z",
                        "delivered_at": "2025-10-02T10:00:01Z",
                        "payload": {"event": "job.started"},
                        "created_at": "2025-10-02T10:00:00Z",
                    },
                    {
                        "event_type": "job.completed",
                        "webhook_url": "https://example.com/webhooks",
                        "attempt_number": 1,
                        "delivery_status": "delivered",
                        "http_status_code": 200,
                        "error_message": None,
                        "scheduled_at": "2025-10-02T10:05:00Z",
                        "delivered_at": "2025-10-02T10:05:01Z",
                        "payload": {"event": "job.completed"},
                        "created_at": "2025-10-02T10:05:00Z",
                    },
                ],
            },
            status=200,
        )

        client = VideoBGRemoverClient("test_key")
        deliveries = client.webhook_deliveries("job_123")

        assert deliveries["video_id"] == "job_123"
        assert deliveries["total_deliveries"] == 2
        assert len(deliveries["deliveries"]) == 2
        assert deliveries["deliveries"][0]["event_type"] == "job.started"
        assert deliveries["deliveries"][1]["event_type"] == "job.completed"
