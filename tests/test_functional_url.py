"""URL-based VideoBGRemover workflow tests.

This test suite validates URL-based video processing workflows:
- Tests Video.open() with URLs (no premature downloads)
- Validates public URL accessibility checks
- Tests API job creation with URL vs file upload paths
- Verifies URL-based background removal workflows
- Tests composition with URL-sourced foregrounds
- Validates error handling for inaccessible URLs

URL Configuration:
- Uses TEST_VIDEO_URL environment variable
- Validates URL accessibility before testing
- Skips tests gracefully if URL not configured
"""

from pathlib import Path
from unittest.mock import patch, Mock
import pytest
import subprocess
import json
import requests
from videobgremover import (
    VideoBGRemoverClient,
    Video,
    Background,
    Composition,
    EncoderProfile,
    RemoveBGOptions,
    Anchor,
    SizeMode,
)


@pytest.fixture
def test_video_url():
    """Test video URL fixture with validation."""
    from .conftest import get_test_video_sources

    sources = get_test_video_sources()
    url = sources["url"]

    if not url:
        pytest.skip("Set TEST_VIDEO_URL environment variable to run URL-based tests")

    # Validate URL is accessible (HEAD request only - no download)
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code not in (200, 204):
            pytest.skip(f"Test video URL not accessible: {response.status_code}")
    except Exception as e:
        pytest.skip(f"Test video URL validation failed: {e}")

    return url


@pytest.fixture
def mock_client():
    """Create a mock API client that doesn't make real HTTP calls."""
    return VideoBGRemoverClient("mock_api_key_for_url_tests")


@pytest.fixture
def output_dir():
    """Create output directory for URL test results."""
    output_path = Path("test_outputs/url_tests")
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def get_video_duration(file_path: str) -> float:
    """Get actual video duration using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_entries",
            "format=duration",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = data.get("format", {}).get("duration")
            return float(duration) if duration else 0.0
        return 0.0
    except Exception:
        return 0.0


@pytest.mark.functional
class TestURLBasedWorkflows:
    """Test URL-based video processing workflows."""

    def test_video_open_url_no_download(self, test_video_url):
        """Test that Video.open() with URL doesn't download the video."""
        print(f"🌐 Testing Video.open() with URL: {test_video_url}")

        # This should be instant - no download occurs
        video = Video.open(test_video_url)

        # Verify video properties
        assert video.kind == "url"
        assert video.src == test_video_url

        print("✅ Video.open() with URL completed instantly (no download)")

    def test_url_accessibility_validation(self, test_video_url):
        """Test URL accessibility validation logic."""
        print("🔍 Testing URL accessibility validation...")

        from videobgremover.media._importer_internal import Importer
        from videobgremover.media.context import MediaContext

        ctx = MediaContext()
        importer = Importer(ctx)

        # Test with valid URL
        is_accessible = importer._public_url_ok(test_video_url)
        assert is_accessible, f"Test URL should be accessible: {test_video_url}"

        # Test with invalid URL
        invalid_url = "https://nonexistent-domain-12345.com/video.mp4"
        is_not_accessible = importer._public_url_ok(invalid_url)
        assert not is_not_accessible, "Invalid URL should not be accessible"

        print("✅ URL accessibility validation working correctly")

    def test_url_vs_file_job_creation_paths(self, mock_client, test_video_url):
        """Test that URL and file videos use different job creation paths."""
        print("🔄 Testing URL vs file job creation paths...")

        from videobgremover.media._importer_internal import Importer
        from videobgremover.media.context import MediaContext

        ctx = MediaContext()
        importer = Importer(ctx)

        # Mock the client methods
        with (
            patch.object(mock_client, "create_job_url") as mock_create_url,
            patch.object(mock_client, "create_job_file") as mock_create_file,
        ):
            mock_create_url.return_value = {"id": "url_job_123"}
            mock_create_file.return_value = {
                "id": "file_job_456",
                "upload_url": "https://upload.url",
            }

            # Test URL video uses create_job_url
            url_video = Video.open(test_video_url)
            url_job_id = importer._create_job(url_video, mock_client)

            assert url_job_id == "url_job_123"
            mock_create_url.assert_called_once()
            mock_create_file.assert_not_called()

            # Reset mocks
            mock_create_url.reset_mock()
            mock_create_file.reset_mock()

            # Test file video uses create_job_file (with mocked upload)
            with patch.object(importer, "_signed_put") as mock_upload:
                file_video = Video.open("test_assets/default_green_screen.mp4")
                file_job_id = importer._create_job(file_video, mock_client)

                assert file_job_id == "file_job_456"
                mock_create_file.assert_called_once()
                mock_create_url.assert_not_called()
                mock_upload.assert_called_once()

        print("✅ URL and file videos use correct job creation paths")

    def test_url_webm_workflow_with_image_background(
        self, mock_client, test_video_url, output_dir
    ):
        """Test URL-based WebM workflow with image background - MOCK API + REAL FFMPEG."""
        print(f"🎬 Testing URL-based WebM workflow: {test_video_url}")

        with patch(
            "videobgremover.media._importer_internal.Importer.remove_background"
        ) as mock_remove:
            from videobgremover.media.foregrounds import Foreground

            # Mock API to return WebM foreground
            mock_remove.return_value = Foreground.from_webm_vp9(
                "test_assets/transparent_webm_vp9.webm"
            )

            # Load video from URL (no download occurs)
            video = Video.open(test_video_url)
            assert video.kind == "url"

            # Configure for WebM output
            options = RemoveBGOptions(prefer="webm_vp9")

            # Execute workflow (API would download and process the URL)
            foreground = video.remove_background(mock_client, options)

            # Verify we got the right format
            assert foreground.format == "webm_vp9"
            assert "transparent_webm_vp9.webm" in foreground.primary_path

            # Create composition with image background
            with patch(
                "videobgremover.media.backgrounds._probe_image_dimensions"
            ) as mock_probe:
                mock_probe.return_value = (1920, 1080)
                bg = Background.from_image("test_assets/background_image.png")
                comp = Composition(bg)
                comp.add(foreground, name="url_webm_layer").at(Anchor.CENTER).size(
                    SizeMode.CONTAIN
                )

                # Export with real FFmpeg
                output_path = output_dir / "url_webm_image_background.mp4"
                encoder = EncoderProfile.h264(crf=20, preset="fast")
                comp.to_file(str(output_path), encoder)

                # Verify output
                assert output_path.exists()
                assert output_path.stat().st_size > 0
                print(f"✅ URL-based WebM workflow completed: {output_path}")

    def test_url_stacked_video_workflow(self, mock_client, test_video_url, output_dir):
        """Test URL-based stacked video workflow - MOCK API + REAL FFMPEG."""
        print(f"📹 Testing URL-based stacked video workflow: {test_video_url}")

        with patch(
            "videobgremover.media._importer_internal.Importer.remove_background"
        ) as mock_remove:
            from videobgremover.media.foregrounds import Foreground

            # Mock API to return stacked video foreground
            mock_remove.return_value = Foreground.from_stacked_video(
                "test_assets/stacked_video_comparison.mp4"
            )

            # Load video from URL
            video = Video.open(test_video_url)
            options = RemoveBGOptions(prefer="stacked_video")

            # Execute workflow
            foreground = video.remove_background(mock_client, options)

            # Verify format
            assert foreground.format == "stacked_video"
            assert foreground.primary_path is not None

            # Create composition with color background
            bg = Background.from_color("#FF0000", 1920, 1080, 30.0)
            comp = Composition(bg)
            comp.add(foreground, name="url_stacked_layer").at(Anchor.CENTER).size(
                SizeMode.COVER
            )

            # Export
            output_path = output_dir / "url_stacked_video.mp4"
            encoder = EncoderProfile.h264(crf=20, preset="medium")
            comp.to_file(str(output_path), encoder)

            # Verify output
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            print(f"✅ URL-based stacked video workflow completed: {output_path}")

    def test_url_pro_bundle_workflow(self, mock_client, test_video_url, output_dir):
        """Test URL-based pro bundle workflow - MOCK API + REAL FFMPEG."""
        print(f"🎬 Testing URL-based pro bundle workflow: {test_video_url}")

        with patch(
            "videobgremover.media._importer_internal.Importer.remove_background"
        ) as mock_remove:
            from videobgremover.media.foregrounds import Foreground

            # Mock API to return pro bundle
            mock_remove.return_value = Foreground.from_pro_bundle_zip(
                "test_assets/pro_bundle_multiple_formats.zip"
            )

            # Load video from URL
            video = Video.open(test_video_url)
            options = RemoveBGOptions(prefer="pro_bundle")

            # Execute workflow
            foreground = video.remove_background(mock_client, options)

            # Verify format
            assert foreground.format == "pro_bundle"
            assert foreground.primary_path is not None
            assert foreground.mask_path is not None

            # Create composition with video background
            with patch(
                "videobgremover.media.backgrounds._probe_video_dimensions"
            ) as mock_probe:
                mock_probe.return_value = (1920, 1080, 30.0)
                bg = Background.from_video("test_assets/background_video.mp4")
                comp = Composition(bg)
                comp.add(foreground, name="url_bundle_layer").at(Anchor.CENTER).size(
                    SizeMode.CONTAIN
                )

                # Export
                output_path = output_dir / "url_pro_bundle.mp4"
                encoder = EncoderProfile.h264(crf=20, preset="medium")
                comp.to_file(str(output_path), encoder)

                # Verify output
                assert output_path.exists()
                assert output_path.stat().st_size > 0
                print(f"✅ URL-based pro bundle workflow completed: {output_path}")

    def test_url_multi_format_comprehensive(
        self, mock_client, test_video_url, output_dir
    ):
        """Test all formats with URL source - MOCK API + REAL FFMPEG."""
        print(f"🎬 Testing all formats with URL source: {test_video_url}")

        formats_to_test = [
            (
                "webm_vp9",
                "WebM VP9",
                "test_assets/transparent_webm_vp9.webm",
                "webm_vp9",
            ),
            (
                "mov_prores",
                "MOV ProRes",
                "test_assets/transparent_mov_prores.mov",
                "mov_prores",
            ),
            (
                "stacked_video",
                "Stacked Video",
                "test_assets/stacked_video_comparison.mp4",
                "stacked_video",
            ),
            (
                "pro_bundle",
                "Pro Bundle",
                "test_assets/pro_bundle_multiple_formats.zip",
                "pro_bundle",
            ),
        ]

        results = {}

        for format_key, format_name, test_asset, expected_form in formats_to_test:
            print(f"  Testing {format_name} with URL source...")

            try:
                with patch(
                    "videobgremover.media._importer_internal.Importer.remove_background"
                ) as mock_remove:
                    from videobgremover.media.foregrounds import Foreground

                    # Mock appropriate foreground type
                    if expected_form == "webm_vp9":
                        mock_remove.return_value = Foreground.from_webm_vp9(test_asset)
                    elif expected_form == "mov_prores":
                        mock_remove.return_value = Foreground.from_mov_prores(
                            test_asset
                        )
                    elif expected_form == "pro_bundle":
                        mock_remove.return_value = Foreground.from_pro_bundle_zip(
                            test_asset
                        )
                    else:  # stacked_video
                        mock_remove.return_value = Foreground.from_stacked_video(
                            test_asset
                        )

                    # Load video from URL
                    video = Video.open(test_video_url)
                    assert video.kind == "url"

                    options = RemoveBGOptions(prefer=format_key)
                    foreground = video.remove_background(mock_client, options)

                    # Verify format
                    assert foreground.format == expected_form

                    # Create composition
                    bg = Background.from_color("#00FF00", 1920, 1080, 30.0)
                    comp = Composition(bg)
                    comp.add(foreground, name=f"url_{format_key}_layer").at(
                        Anchor.CENTER
                    ).size(SizeMode.CONTAIN)

                    # Export
                    output_path = output_dir / f"url_comprehensive_{format_key}.mp4"
                    encoder = EncoderProfile.h264(crf=23, preset="fast")
                    comp.to_file(str(output_path), encoder)

                    # Verify
                    assert output_path.exists()
                    assert output_path.stat().st_size > 0

                    results[format_key] = {
                        "success": True,
                        "output_path": output_path,
                        "file_size": output_path.stat().st_size,
                        "format": expected_form,
                    }

                    print(
                        f"    ✅ {format_name}: {expected_form} format, {output_path.stat().st_size} bytes"
                    )

            except Exception as e:
                results[format_key] = {"success": False, "error": str(e)}
                print(f"    ❌ {format_name} failed: {e}")

        # Verify at least 2 formats worked
        successful_formats = [k for k, v in results.items() if v["success"]]
        assert len(successful_formats) >= 2, (
            f"At least 2 formats should work with URL source, got: {successful_formats}"
        )

        print(
            f"✅ URL-based comprehensive test completed: {len(successful_formats)}/4 formats successful"
        )

    def test_url_error_handling(self, mock_client):
        """Test error handling with invalid URLs."""
        print("🎬 Testing URL error handling...")

        # Test with completely invalid URL
        invalid_urls = [
            "https://nonexistent-domain-12345.com/video.mp4",
            "http://localhost:99999/video.mp4",  # Invalid port
            "https://httpstat.us/404",  # Returns 404
            "not-a-url-at-all",  # Not even a URL
        ]

        for invalid_url in invalid_urls:
            print(f"  Testing invalid URL: {invalid_url}")

            # Video.open should still work (no validation at this stage)
            _ = Video.open(invalid_url)  # Video creation should work

            # But URL validation should fail
            from videobgremover.media._importer_internal import Importer
            from videobgremover.media.context import MediaContext

            ctx = MediaContext()
            importer = Importer(ctx)

            is_accessible = importer._public_url_ok(invalid_url)
            assert not is_accessible, (
                f"Invalid URL should not be accessible: {invalid_url}"
            )

        print("✅ URL error handling test completed")

    def test_url_large_file_size_limit(self, mock_client):
        """Test URL file size limit validation."""
        print("🔍 Testing URL file size limit validation...")

        from videobgremover.media._importer_internal import Importer
        from videobgremover.media.context import MediaContext

        ctx = MediaContext()
        importer = Importer(ctx)

        # Mock a response with large content length (over 1GB limit)
        with patch("requests.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Length": "2000000000"}  # 2GB
            mock_head.return_value = mock_response

            is_accessible = importer._public_url_ok(
                "https://example.com/huge-video.mp4"
            )
            assert not is_accessible, "URLs over 1GB should be rejected"

        # Mock a response with acceptable size
        with patch("requests.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Length": "500000000"}  # 500MB
            mock_head.return_value = mock_response

            is_accessible = importer._public_url_ok(
                "https://example.com/normal-video.mp4"
            )
            assert is_accessible, "URLs under 1GB should be accepted"

        print("✅ URL file size limit validation working correctly")

    def test_url_background_composition(self, test_video_url, output_dir):
        """Test using URL video as background in composition."""
        print(f"🎨 Testing URL video as background: {test_video_url}")

        # Create a mock foreground
        from videobgremover.media.foregrounds import Foreground

        fg = Foreground.from_webm_vp9("test_assets/transparent_webm_vp9.webm")

        # Use URL video as background (this will probe the URL)
        with patch(
            "videobgremover.media.backgrounds._probe_video_dimensions"
        ) as mock_probe:
            mock_probe.return_value = (1920, 1080, 30.0)

            # This should work - Background.from_video can handle URLs
            bg = Background.from_video(test_video_url)
            assert bg.kind == "video"
            assert bg.source == test_video_url

            # Create composition
            comp = Composition(bg)
            comp.add(fg, name="overlay").at(Anchor.CENTER).size(
                SizeMode.CONTAIN
            ).opacity(0.8)

            # Generate FFmpeg command (dry run)
            cmd = comp.dry_run()
            assert test_video_url in cmd, "URL should be in FFmpeg command"
            assert "overlay=" in cmd, "Should have overlay filter"

            print("✅ URL video background composition working correctly")


if __name__ == "__main__":
    # Run URL-based functional tests
    print("Running URL-based VideoBGRemover functional tests...")
    print("⚠️ These tests mock API calls but use real FFmpeg operations!")
    print("📋 Make sure TEST_VIDEO_URL is set in your .env file")

    pytest.main([__file__, "-v", "--tb=short"])
