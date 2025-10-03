"""VideoBGRemover API client."""

import time
import requests
from typing import Optional, Dict, Any, Callable
from ..__version__ import __version__
from .models import (
    CreateJobFileUpload,
    CreateJobUrlDownload,
    StartJobRequest,
    JobStatus,
    CreditBalance,
    ApiError,
    InsufficientCreditsError,
    JobNotFoundError,
    ProcessingError,
)


class VideoBGRemoverClient:
    """Client for interacting with the VideoBGRemover API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.videobgremover.com",
        session: Optional[requests.Session] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the API client.

        Args:
            api_key: Your VideoBGRemover API key
            base_url: Base URL for the API (default: production)
            session: Optional requests session to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

        # Set up authentication header
        self.session.headers.update(
            {"X-Api-Key": api_key, "User-Agent": f"videobgremover-python/{__version__}"}
        )

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the API with error handling."""
        url = f"{self.base_url}{endpoint}"

        # Set timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        try:
            response = self.session.request(method, url, **kwargs)

            # Handle different error status codes
            if response.status_code == 401:
                raise ApiError("Invalid API key", response.status_code)
            elif response.status_code == 402:
                raise InsufficientCreditsError(
                    "Insufficient credits",
                    response.status_code,
                    response.json() if response.content else None,
                )
            elif response.status_code == 404:
                raise JobNotFoundError(
                    "Resource not found",
                    response.status_code,
                    response.json() if response.content else None,
                )
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get(
                        "error", f"HTTP {response.status_code}"
                    )
                except (ValueError, requests.exceptions.JSONDecodeError):
                    error_message = f"HTTP {response.status_code}"

                if (
                    "processing" in error_message.lower()
                    or "failed" in error_message.lower()
                ):
                    raise ProcessingError(
                        error_message,
                        response.status_code,
                        error_data if "error_data" in locals() else None,
                    )
                else:
                    raise ApiError(
                        error_message,
                        response.status_code,
                        error_data if "error_data" in locals() else None,
                    )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise ApiError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise ApiError("Failed to connect to the API")
        except requests.exceptions.RequestException as e:
            raise ApiError(f"Request failed: {str(e)}")

    def create_job_file(self, req: CreateJobFileUpload) -> Dict[str, Any]:
        """
        Create a job for file upload.

        Args:
            req: File upload request parameters

        Returns:
            Job creation response with upload URL
        """
        return self._request("POST", "/v1/jobs", json=req.model_dump())

    def create_job_url(self, req: CreateJobUrlDownload) -> Dict[str, Any]:
        """
        Create a job for URL download.

        Args:
            req: URL download request parameters

        Returns:
            Job creation response
        """
        return self._request("POST", "/v1/jobs", json=req.model_dump(mode="json"))

    def start_job(
        self, job_id: str, req: Optional[StartJobRequest] = None
    ) -> Dict[str, Any]:
        """
        Start processing a job.

        Args:
            job_id: The job ID to start
            req: Optional job configuration

        Returns:
            Job start response
        """
        data = req.model_dump() if req else {}
        return self._request("POST", f"/v1/jobs/{job_id}/start", json=data)

    def status(self, job_id: str) -> JobStatus:
        """
        Get job status.

        Args:
            job_id: The job ID to check

        Returns:
            Current job status
        """
        response = self._request("GET", f"/v1/jobs/{job_id}/status")
        return JobStatus.model_validate(response)

    def wait(
        self,
        job_id: str,
        poll_seconds: float = 2.0,
        timeout: Optional[float] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> JobStatus:
        """
        Wait for a job to complete.

        Args:
            job_id: The job ID to wait for
            poll_seconds: Polling interval in seconds
            timeout: Maximum time to wait (None for no timeout)
            on_status: Status callback function (receives status strings)

        Returns:
            Final job status

        Raises:
            TimeoutError: If timeout is reached
            ProcessingError: If job fails
        """
        start_time = time.time()
        last_status = None

        while True:
            status = self.status(job_id)

            if status.status == "completed":
                return status
            elif status.status == "failed":
                raise ProcessingError(
                    status.message or "Job processing failed",
                    response_data={"job_id": job_id, "status": status.model_dump()},
                )

            # Check timeout
            if timeout and time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Job {job_id} did not complete within {timeout} seconds"
                )

            # Call status callback only when status changes
            if on_status and status.status != last_status:
                on_status(status.status)
                last_status = status.status

            time.sleep(poll_seconds)

    def credits(self) -> CreditBalance:
        """
        Get current credit balance.

        Returns:
            Current credit information
        """
        response = self._request("GET", "/v1/credits")
        return CreditBalance.model_validate(response)

    def webhook_deliveries(self, video_id: str) -> Dict[str, Any]:
        """
        Get webhook delivery history for a job.

        Args:
            video_id: The video/job ID to get delivery history for

        Returns:
            Webhook delivery history with all attempts
        """
        response = self._request("GET", f"/v1/webhooks/deliveries?video_id={video_id}")
        return response
